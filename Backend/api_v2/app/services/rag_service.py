# Backend/api_v2/app/services/rag_service.py
#
# Currently a plain LLM chat service.
# The retrieval pipeline will be added here later without touching anything else.

from typing import AsyncGenerator, Dict, List, Optional
 
from .llm_service import stream_chat_response

async def run_rag_query(
    *,
    question: str,
    history_messages: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Build the message list and call the LLM.
 
    `history_messages` must already include the current user turn as its last
    entry (chat_service adds it before calling here).
 
    Later: retrieved document chunks will be injected between the system
    prompt and the conversation history.
    """
    messages: List[Dict[str, str]] = []
 
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
 
    if history_messages:
        messages.extend(history_messages)
 
    async for chunk in stream_chat_response(messages):
        yield chunk
 