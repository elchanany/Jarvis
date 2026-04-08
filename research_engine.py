"""
JARVIS Research Engine - Smart Web Research with Vector Search
===============================================================
Pipeline:
1. Query Expansion - Generate 5 search queries from user intent
2. Web Search - DuckDuckGo search for each query
3. Parallel Scraping - Fetch all URLs simultaneously
4. Chunking - Split content into 500-char chunks
5. Local Embeddings - sentence-transformers (FREE!)
6. DuckDB Vector Store - In-memory semantic search
7. Smart Summarization - LLM answers with citations
"""

import os
import re
import time
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Will be lazy-loaded to avoid slow startup
_embedding_model = None
_db_connection = None


@dataclass
class Chunk:
    """A chunk of text with metadata."""
    text: str
    url: str
    index: int


@dataclass
class SearchResult:
    """A search result with title, body, and URL."""
    title: str
    body: str
    url: str


def get_embedding_model():
    """Lazy load the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        print("[RESEARCH] Loading embedding model (first time only)...")
        try:
            from sentence_transformers import SentenceTransformer
            # Small, fast model - 80MB, runs locally
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[RESEARCH] ✅ Embedding model ready!")
        except ImportError:
            print("[RESEARCH] ❌ Install: pip install sentence-transformers")
            return None
    return _embedding_model


def get_db_connection():
    """Get or create DuckDB in-memory connection."""
    global _db_connection
    if _db_connection is None:
        try:
            import duckdb
            _db_connection = duckdb.connect(":memory:")
            # Install and load VSS extension for vector search
            _db_connection.execute("INSTALL vss; LOAD vss;")
            print("[RESEARCH] ✅ DuckDB Vector ready!")
        except ImportError:
            print("[RESEARCH] ❌ Install: pip install duckdb")
            return None
        except Exception as e:
            print(f"[RESEARCH] ⚠️ DuckDB VSS not available: {e}")
            # Still usable without VSS, just slower
    return _db_connection


# ============================================
# STEP 1: Query Expansion
# ============================================

def expand_query(user_query: str, llm_func=None) -> List[str]:
    """
    Generate search queries from user intent.
    Focus on English queries for better DDG results.
    """
    print(f"[RESEARCH] 📝 Expanding query: '{user_query}'")
    
    base = user_query.strip()
    
    # Detect if Hebrew
    is_hebrew = any('\u0590' <= c <= '\u05FF' for c in base)
    
    if is_hebrew:
        queries = [
            base,
            f"{base} חדשות",
            f"{base} עדכון",
        ]
    else:
        queries = [
            base,
            f"{base} latest",
            f"{base} today 2025",
        ]
    
    # Remove duplicates
    queries = list(dict.fromkeys([q for q in queries if q.strip()]))[:5]
    
    print(f"[RESEARCH] 🔍 Generated {len(queries)} queries")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")
    
    return queries


# ============================================
# STEP 2: Web Search
# ============================================

def search_web(query: str, max_results: int = 5) -> List[SearchResult]:
    """Search DuckDuckGo with region preference and filter bad domains."""
    try:
        from duckduckgo_search import DDGS
        
        # Bad domains to filter out
        bad_domains = ['baidu.com', 'zhidao.baidu', 'weibo.com', 'qq.com', 
                       'yandex.ru', 'vk.com', 'mail.ru']
        
        # Try with wt-wt region (worldwide English)
        results = DDGS().text(query, region='wt-wt', max_results=max_results)
        
        filtered = []
        for r in results:
            url = r.get('href', '')
            # Skip bad domains
            if any(bad in url for bad in bad_domains):
                continue
            filtered.append(SearchResult(
                title=r.get('title', ''),
                body=r.get('body', ''),
                url=url
            ))
        
        return filtered
    except Exception as e:
        print(f"[RESEARCH] ⚠️ Search error: {e}")
        return []


def multi_search(queries: List[str]) -> List[SearchResult]:
    """Search multiple queries and combine unique results."""
    print(f"[RESEARCH] 🔍 Searching {len(queries)} queries...")
    
    all_results = []
    seen_urls = set()
    
    for query in queries:
        results = search_web(query, max_results=5)
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append(r)
    
    print(f"[RESEARCH] ✅ Found {len(all_results)} unique URLs")
    return all_results[:10]  # Max 10 URLs


# ============================================
# STEP 3: Parallel Scraping
# ============================================

def scrape_url(url: str) -> Tuple[str, str]:
    """Scrape a single URL with multiple fallback methods."""
    
    # Method 1: trafilatura (best quality)
    try:
        import trafilatura
        
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(
                downloaded, 
                include_comments=False, 
                include_tables=False
            )
            if text and len(text) > 100:
                return url, text
    except Exception:
        pass
    
    # Method 2: requests + BeautifulSoup (fallback)
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove junk
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())  # Clean whitespace
        
        if len(text) > 100:
            return url, text[:5000]  # Limit to 5000 chars
    except Exception as e:
        print(f"[RESEARCH] ❌ Scrape failed: {url[:50]}... ({e})")
    
    return url, ""


def parallel_scrape(urls: List[str], max_workers: int = 5) -> Dict[str, str]:
    """Scrape multiple URLs in parallel."""
    print(f"[RESEARCH] 🕷️ Scraping {len(urls)} URLs in parallel...")
    start = time.time()
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_url, url): url for url in urls}
        
        for future in as_completed(futures):
            url, text = future.result()
            if text:
                results[url] = text
                print(f"[RESEARCH] ✅ {url[:60]}... ({len(text)} chars)")
    
    elapsed = time.time() - start
    print(f"[RESEARCH] ⏱️ Scraped {len(results)} pages in {elapsed:.1f}s")
    
    return results


# ============================================
# STEP 4: Chunking
# ============================================

def chunk_text(text: str, url: str, chunk_size: int = 500, overlap: int = 50) -> List[Chunk]:
    """Split text into overlapping chunks."""
    chunks = []
    
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    
    start = 0
    index = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text.rfind('.')
            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk_text = text[start:end]
        
        if len(chunk_text.strip()) > 50:  # Minimum chunk size
            chunks.append(Chunk(
                text=chunk_text.strip(),
                url=url,
                index=index
            ))
            index += 1
        
        start = end - overlap
    
    return chunks


def chunk_all_documents(documents: Dict[str, str]) -> List[Chunk]:
    """Chunk all scraped documents."""
    print("[RESEARCH] ✂️ Chunking documents...")
    
    all_chunks = []
    
    for url, text in documents.items():
        chunks = chunk_text(text, url)
        all_chunks.extend(chunks)
    
    print(f"[RESEARCH] ✅ Created {len(all_chunks)} chunks from {len(documents)} documents")
    return all_chunks


# ============================================
# STEP 5: Local Embeddings
# ============================================

def embed_chunks(chunks: List[Chunk]) -> List[Tuple[Chunk, List[float]]]:
    """Create embeddings for all chunks using local model."""
    print(f"[RESEARCH] 🧠 Embedding {len(chunks)} chunks...")
    start = time.time()
    
    model = get_embedding_model()
    if model is None:
        # Fallback: return empty embeddings
        return [(c, []) for c in chunks]
    
    texts = [c.text for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False)
    
    elapsed = time.time() - start
    print(f"[RESEARCH] ✅ Embedded in {elapsed:.1f}s")
    
    return list(zip(chunks, embeddings.tolist()))


# ============================================
# STEP 6: Vector Store (DuckDB)
# ============================================

def store_in_duckdb(embedded_chunks: List[Tuple[Chunk, List[float]]]) -> str:
    """Store chunks with embeddings in DuckDB."""
    if not embedded_chunks:
        return ""
    
    db = get_db_connection()
    if db is None:
        return ""
    
    # Create unique table name
    table_name = f"chunks_{int(time.time())}"
    
    # Get embedding dimension
    if embedded_chunks[0][1]:
        dim = len(embedded_chunks[0][1])
    else:
        dim = 384  # Default for all-MiniLM-L6-v2
    
    try:
        # Create table
        db.execute(f"""
            CREATE TABLE {table_name} (
                id INTEGER,
                url TEXT,
                chunk_text TEXT,
                embedding FLOAT[{dim}]
            )
        """)
        
        # Insert data
        for i, (chunk, emb) in enumerate(embedded_chunks):
            if emb:
                db.execute(f"""
                    INSERT INTO {table_name} VALUES (?, ?, ?, ?)
                """, [i, chunk.url, chunk.text, emb])
        
        print(f"[RESEARCH] 💾 Stored {len(embedded_chunks)} chunks in DuckDB")
        return table_name
        
    except Exception as e:
        print(f"[RESEARCH] ⚠️ DuckDB store error: {e}")
        return ""


def semantic_search(query: str, table_name: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
    """
    Search for most relevant chunks using vector similarity.
    Returns list of (url, chunk_text, score).
    """
    if not table_name:
        return []
    
    db = get_db_connection()
    model = get_embedding_model()
    
    if db is None or model is None:
        return []
    
    # Embed query
    query_embedding = model.encode([query])[0].tolist()
    
    try:
        # Vector search using cosine similarity
        results = db.execute(f"""
            SELECT url, chunk_text,
                   array_cosine_similarity(embedding, ?::FLOAT[{len(query_embedding)}]) as score
            FROM {table_name}
            ORDER BY score DESC
            LIMIT {top_k}
        """, [query_embedding]).fetchall()
        
        return results
        
    except Exception as e:
        print(f"[RESEARCH] ⚠️ Vector search error: {e}")
        # Fallback: return first chunks without scoring
        try:
            results = db.execute(f"""
                SELECT url, chunk_text, 1.0 as score
                FROM {table_name}
                LIMIT {top_k}
            """).fetchall()
            return results
        except:
            return []


# ============================================
# STEP 7: Compile Research Report
# ============================================

def compile_research_report(
    query: str,
    relevant_chunks: List[Tuple[str, str, float]]
) -> str:
    """
    Compile a research report from relevant chunks.
    Format for LLM consumption with citations.
    """
    if not relevant_chunks:
        return "SYSTEM: No relevant information found."
    
    report = f"### RESEARCH REPORT: {query} ###\n\n"
    report += "Below are the most relevant excerpts from web sources:\n\n"
    
    # Group by URL for citations
    url_to_citation = {}
    citation_num = 1
    
    for url, text, score in relevant_chunks:
        if url not in url_to_citation:
            url_to_citation[url] = citation_num
            citation_num += 1
        
        cit = url_to_citation[url]
        report += f"[{cit}] (Relevance: {score:.2f})\n{text}\n\n"
    
    report += "--- SOURCES ---\n"
    for url, cit in url_to_citation.items():
        report += f"[{cit}] {url}\n"
    
    report += "\n--- END OF REPORT ---"
    
    return report


# ============================================
# MAIN RESEARCH FUNCTION
# ============================================

def smart_research(user_query: str) -> str:
    """
    Full research pipeline:
    1. Expand query into multiple search terms
    2. Search web for all queries
    3. Scrape URLs in parallel
    4. Chunk content
    5. Embed with local model
    6. Store in vector DB
    7. Semantic search for relevant chunks
    8. Compile report with citations
    """
    print(f"\n{'='*60}")
    print(f"[RESEARCH] 🚀 SMART RESEARCH ENGINE")
    print(f"[RESEARCH] Query: '{user_query}'")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        # Step 1: Query Expansion
        queries = expand_query(user_query)
        
        # Step 2: Multi-Search
        search_results = multi_search(queries)
        
        if not search_results:
            return "SYSTEM: No search results found. Try a different query."
        
        # Step 3: Parallel Scraping
        urls = [r.url for r in search_results]
        documents = parallel_scrape(urls)
        
        # FALLBACK: If scraping fails, use search snippets
        if not documents:
            print("[RESEARCH] ⚠️ Scraping failed! Using search snippets as fallback...")
            for r in search_results:
                if r.body and len(r.body) > 50:
                    documents[r.url] = f"{r.title}. {r.body}"
            if documents:
                print(f"[RESEARCH] ✅ Using {len(documents)} search snippets")
        
        # Step 4: Chunking
        chunks = chunk_all_documents(documents)
        
        if not chunks:
            return "SYSTEM: Failed to process content."
        
        # Step 5: Embedding
        embedded_chunks = embed_chunks(chunks)
        
        # Step 6: Vector Store
        table_name = store_in_duckdb(embedded_chunks)
        
        # Step 7: Semantic Search
        relevant = semantic_search(user_query, table_name, top_k=5)
        
        # Fallback if vector search failed
        if not relevant and chunks:
            # Just use first chunks
            relevant = [(c.url, c.text, 1.0) for c in chunks[:5]]
        
        # Step 8: Compile Report
        report = compile_research_report(user_query, relevant)
        
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"[RESEARCH] ✅ COMPLETED in {elapsed:.1f}s")
        print(f"[RESEARCH] 📊 {len(search_results)} URLs → {len(documents)} scraped → {len(chunks)} chunks → {len(relevant)} relevant")
        print(f"{'='*60}\n")
        
        return report
        
    except Exception as e:
        print(f"[RESEARCH] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"SYSTEM ERROR: {e}"


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    # Test the research engine
    result = smart_research("מה קורה עם הביטקוין היום")
    print(result)
