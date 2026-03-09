# RAG System

The Retrieval Augmented Generation (RAG) system enriches LLM prompts
with relevant contextual information retrieved from stored documents.

## Purpose

RAG improves answer quality by allowing the LLM to reference external
knowledge.

Instead of relying only on model training data, the system retrieves
relevant documents and injects them into the prompt.

## Pipeline

1.  User question is received
2.  Embeddings are generated
3.  Relevant information is retrieved from (global) documents
    (Optional: local documents can be injected also via RAG for better context awareness)
4.  Information is injected into prompt
5.  LLM generates answer

## Implementation

The RAG logic is implemented in:

Backend/api_v2/app/services/rag_service.py

It provides:

- embedding generation
- document retrieval
- LLM abstraction layer
- provider/model switching

## Supported Providers

- OpenRouter API
- Ollama local models

This abstraction allows switching providers without modifying
higher-level services.
