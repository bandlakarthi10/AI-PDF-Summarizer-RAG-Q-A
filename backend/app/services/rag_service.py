"""
RAG service — orchestrates retrieval + LLM generation with vector store guards.

Key design principle: citations are ALWAYS constructed from retrieval
metadata. The LLM is never asked to produce or parse source references.
"""
from __future__ import annotations

from app.core.logging_config import logger
from app.models.schemas import ChatRequest, ChatResponse, Citation
from app.prompts.rag_prompts import RAG_SYSTEM, RAG_USER_TEMPLATE
from app.services.conversation_service import conversation_service
from app.services.llm_service import llm_service
from app.services.retrieval_service import retrieval_service
from app.services.vector_store_service import vector_store_service


class RAGService:
    async def answer(self, request: ChatRequest) -> ChatResponse:
        cid = conversation_service.get_or_create(request.conversation_id)

        # 0. Check if FAISS vector store has any indexed documents
        if vector_store_service.total_vectors == 0:
            answer_text = (
                "⚠️ Chat is currently unavailable because no indexed document vectors were found. "
                "Please upload a PDF document or use 'Rebuild Index' to sync the vector store."
            )
            conversation_service.add_turn(cid, request.question, answer_text)
            return ChatResponse(answer=answer_text, sources=[], conversation_id=cid)

        # 1. Retrieve relevant chunks
        citations = retrieval_service.retrieve(
            query=request.question,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )

        # 2. Build context from retrieval metadata
        context = retrieval_service.build_context(citations)

        # 3. If no context found, respond without calling the LLM
        if not citations:
            answer_text = (
                "The information requested was not found in the specified document context."
            )
            conversation_service.add_turn(cid, request.question, answer_text)
            return ChatResponse(answer=answer_text, sources=[], conversation_id=cid)

        # 4. Build prompt with conversation history
        history = conversation_service.format_history(cid)
        user_prompt = RAG_USER_TEMPLATE.format(
            context=context,
            history=history,
            question=request.question,
        )

        # 5. Call LLM — propagate errors clearly to the caller
        try:
            answer_text = await llm_service.generate(
                prompt=user_prompt,
                system=RAG_SYSTEM,
                temperature=0.1,
            )
        except Exception as exc:
            raise RuntimeError(f"LLM generation failed: {exc}") from exc

        # 6. Store turn in conversation memory
        conversation_service.add_turn(cid, request.question, answer_text)

        return ChatResponse(answer=answer_text, sources=citations, conversation_id=cid)


# ── singleton ─────────────────────────────────────────────────
rag_service = RAGService()
