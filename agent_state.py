# agent_state.py
# ===============
# State definition for Jarvis LangGraph Agent
# Uses TypedDict for structured state management

from typing import TypedDict, List, Optional, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    The state of the Jarvis agent.
    
    Attributes:
        messages: The conversation history (list of messages)
        next_step: The LLM's decision - 'call_tool', 'reply_user', or 'end'
        tool_calls: Queue of tool calls to execute
        tool_results: Results from executed tools
    """
    # Conversation history - messages are appended
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # The next action to take
    next_step: str
    
    # Pending tool calls (from LLM decision)
    tool_calls: List[dict]
    
    # Results from tool execution
    tool_results: List[str]
    
    # Whether user input was originally in Hebrew
    original_hebrew: bool


def create_initial_state() -> AgentState:
    """Create an empty initial state."""
    return {
        "messages": [],
        "next_step": "brain",
        "tool_calls": [],
        "tool_results": [],
        "original_hebrew": False,
    }
