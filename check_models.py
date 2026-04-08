# check_models.py
# ================
# Check which Gemini models are available for your API key

import google.generativeai as genai

# PASTE YOUR KEY HERE
api_key = "PASTE_KEY_HERE"

genai.configure(api_key=api_key)
print("Checking available models for your key...")
print()

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
