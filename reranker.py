"""
Semantic reranking orchestrator.  
Coordinates cloud embeddings (Gemini) with local fallbacks (cross-encoder, Gemma).
"""

import asyncio
import logging
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel

from embeddings import (
    GoogleGeminiEmbedding,
    LocalCrossEncoderEmbedding,
    GemmaFallbackReranker
)
from config import RerankerConfig, GoogleEmbeddingConfig, GoogleFallbackConfig

logger = logging.getLogger("Reranker")

class RerankerStatus(Enum):
    """Status of reranking operation."""
    SUCCESS = "success"
    FAILED_CLOUD_FALLBACK_LOCAL = "failed_cloud_used_local"
    FAILED_ALL_USED_ORIGINAL = "failed_all_returned_original"

class RerankerResponse(BaseModel):
    """Response from reranking operation."""
    status: RerankerStatus
    reranked_documents: List[tuple]
    message: str

class SemanticReranker:
    """Multi-tier reranking with graceful fallback."""
    
    def __init__(
        self,
        embedding_config: GoogleEmbeddingConfig,
        fallback_config: GoogleFallbackConfig,
        reranker_config: RerankerConfig
    ):
        self.embedding_config = embedding_config
        self.fallback_config = fallback_config
        self.reranker_config = reranker_config
        
        self.gemini_embedder:  Optional[GoogleGeminiEmbedding] = None
        self. local_cross_encoder: Optional[LocalCrossEncoderEmbedding] = None
        self.gemma_fallback:  Optional[GemmaFallbackReranker] = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize all reranking backends."""
        try:
            if self.reranker_config.use_cloud:  
                self.gemini_embedder = GoogleGeminiEmbedding(
                    api_key=self.embedding_config.api_key,
                    model=self.embedding_config.model
                )
                logger.info("Initialized Google Gemini embedder")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini embedder: {e}")
        
        try:
            self.local_cross_encoder = LocalCrossEncoderEmbedding(
                model_name=self.reranker_config.local_fallback_model
            )
            logger.info(f"Initialized local cross-encoder")
        except Exception as e:  
            logger.warning(f"Failed to initialize local cross-encoder: {e}")
        
        try:  
            self.gemma_fallback = GemmaFallbackReranker(
                api_key=self.fallback_config.api_key,
                model=self.fallback_config.model
            )
            logger.info("Initialized Gemma fallback reranker")
        except Exception as e: 
            logger.warning(f"Failed to initialize Gemma fallback:  {e}")
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> RerankerResponse:
        """Rerank documents with multi-tier fallback."""
        if not documents:
            return RerankerResponse(
                status=RerankerStatus.FAILED_ALL_USED_ORIGINAL,
                reranked_documents=[(doc, 1.0) for doc in documents],
                message="No documents to rerank"
            )
        
        docs_to_rerank = documents[:top_k] if top_k else documents
        remaining_docs = documents[top_k:] if top_k else []
        
        # Tier 1: Try Google Gemini embeddings
        if self.gemini_embedder:
            try:
                logger.info(f"Reranking {len(docs_to_rerank)} docs with Gemini embeddings")
                scores = await self.gemini_embedder.rerank(query, docs_to_rerank)
                
                if scores and len(scores) == len(docs_to_rerank):
                    reranked = list(zip(docs_to_rerank, scores))
                    reranked.sort(key=lambda x: x[1], reverse=True)
                    
                    if remaining_docs:
                        reranked.extend([(doc, 0.0) for doc in remaining_docs])
                    
                    return RerankerResponse(
                        status=RerankerStatus.SUCCESS,
                        reranked_documents=reranked,
                        message=f"Successfully reranked using Gemini embeddings"
                    )
            except Exception as e:
                logger.warning(f"Gemini reranking failed: {e}")
        
        # Tier 2: Fallback to local cross-encoder
        if self.local_cross_encoder:
            try:
                logger.info(f"Reranking {len(docs_to_rerank)} docs with local cross-encoder")
                scores = await self.local_cross_encoder.rerank(query, docs_to_rerank)
                
                if scores and len(scores) == len(docs_to_rerank):
                    reranked = list(zip(docs_to_rerank, scores))
                    reranked.sort(key=lambda x: x[1], reverse=True)
                    
                    if remaining_docs:
                        reranked.extend([(doc, 0.0) for doc in remaining_docs])
                    
                    return RerankerResponse(
                        status=RerankerStatus. FAILED_CLOUD_FALLBACK_LOCAL,
                        reranked_documents=reranked,
                        message=f"Cloud failed, used local cross-encoder fallback"
                    )
            except Exception as e:
                logger.warning(f"Local cross-encoder reranking failed: {e}")
        
        # Tier 3: Return original order
        logger.warning("All reranking backends failed, returning original order")
        return RerankerResponse(
            status=RerankerStatus. FAILED_ALL_USED_ORIGINAL,
            reranked_documents=[(doc, 1.0) for doc in documents],
            message="All reranking backends failed, returned original DDG order"
        )
    
    async def shutdown(self):
        """Cleanup resources."""
        if self.gemini_embedder:
            await self.gemini_embedder. close()
        if self.gemma_fallback:
            await self.gemma_fallback. close()