"""
Google Gemini Embedding API integration for semantic reranking. 
Provides both cloud (Gemini) and local (Gemma) embedding capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import json

import httpx
from pydantic import BaseModel

logger = logging.getLogger("Embeddings")

class EmbeddingResponse(BaseModel):
    """Response from embedding API."""
    query: str
    embeddings: List[List[float]]
    model: str
    success: bool

class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> EmbeddingResponse:
        """Generate embeddings for a list of texts."""
        pass
    
    @abstractmethod
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """Return relevance scores (0-1) for each document relative to query."""
        pass

class GoogleGeminiEmbedding(EmbeddingProvider):
    """Google Gemini Embedding API (Primary)."""
    
    def __init__(self, api_key:  str, model: str = "models/embedding-001"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResponse: 
        """
        Call Google Gemini Embedding API.
        API:  https://ai.google.dev/api/embedding-api
        """
        if not texts:
            return EmbeddingResponse(
                query="",
                embeddings=[],
                model=self.model,
                success=False
            )
        
        try:
            # Batch embedding request
            request_body = {
                "requests": [
                    {"text": text} for text in texts
                ]
            }
            
            url = f"{self.base_url}/{self.model}: batchEmbedContents? key={self.api_key}"
            
            response = await self.client.post(url, json=request_body)
            response.raise_for_status()
            
            data = response.json()
            embeddings = [
                item["embedding"]["values"] 
                for item in data. get("embeddings", [])
            ]
            
            logger.info(f"Successfully embedded {len(embeddings)} texts via Gemini")
            
            return EmbeddingResponse(
                query="batch",
                embeddings=embeddings,
                model=self.model,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            return EmbeddingResponse(
                query="batch",
                embeddings=[],
                model=self.model,
                success=False
            )
    
    async def rerank(self, query: str, documents:  List[str]) -> List[float]:
        """
        Rerank documents using Gemini embeddings via cosine similarity.
        
        Strategy: 
        1. Embed query
        2. Embed all documents
        3. Compute cosine similarity between query and each document
        4. Return normalized scores [0, 1]
        """
        if not documents:
            return []
        
        try:
            # Embed query + all documents in one batch
            all_texts = [query] + documents
            embedding_response = await self.embed_texts(all_texts)
            
            if not embedding_response. success or len(embedding_response.embeddings) <= 1:
                logger.warning("Gemini embedding failed for reranking")
                return []
            
            embeddings = embedding_response.embeddings
            query_embedding = embeddings[0]
            doc_embeddings = embeddings[1:]
            
            # Cosine similarity
            import numpy as np
            query_vec = np.array(query_embedding)
            scores = []
            
            for doc_vec in doc_embeddings:
                doc_vec = np.array(doc_vec)
                similarity = np.dot(query_vec, doc_vec) / (
                    np.linalg. norm(query_vec) * np.linalg.norm(doc_vec) + 1e-8
                )
                # Normalize to [0, 1]
                normalized_score = (similarity + 1) / 2
                scores.append(float(normalized_score))
            
            logger.info(f"Reranked {len(documents)} documents via Gemini")
            return scores
            
        except Exception as e:
            logger. error(f"Gemini reranking failed: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()

class LocalCrossEncoderEmbedding(EmbeddingProvider):
    """Local Cross-Encoder for fallback reranking."""
    
    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self.model_name = model_name
            logger.info(f"Loaded local cross-encoder:  {model_name}")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder: {e}")
            self.model = None
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResponse: 
        """Not implemented for cross-encoder (use rerank instead)."""
        return EmbeddingResponse(
            query="",
            embeddings=[],
            model=self.model_name,
            success=False
        )
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        Rerank using local cross-encoder model.
        Much faster than cloud for small batches, no API calls. 
        """
        if not self.model or not documents:
            return []
        
        try:
            # Cross-encoder expects [[query, doc1], [query, doc2], ...]
            query_doc_pairs = [[query, doc] for doc in documents]
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None,
                self.model.predict,
                query_doc_pairs
            )
            
            # Normalize to [0, 1]
            import numpy as np
            min_score = float(np.min(scores))
            max_score = float(np.max(scores))
            
            if max_score == min_score: 
                normalized = [0.5] * len(scores)
            else:
                normalized = [
                    (score - min_score) / (max_score - min_score)
                    for score in scores
                ]
            
            logger. info(f"Reranked {len(documents)} documents via local cross-encoder")
            return normalized
            
        except Exception as e:
            logger.error(f"Local cross-encoder reranking failed: {e}")
            return []

class GemmaFallbackReranker:
    """
    Google Gemma-3 27B fallback reranker (via Hugging Face Inference API or similar).
    Used if both Gemini embeddings and local cross-encoder fail.
    """
    
    def __init__(self, api_key: str, model: str = "google/gemma-3-27b"):
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def rerank(self, query: str, documents: List[str], top_k: int = 10) -> List[float]:
        """
        Rerank using Gemma LLM.
        Asks the model to score relevance for each document.
        """
        if not documents:
            return []
        
        try: 
            # Create a prompt asking the model to rate relevance
            prompt = self._build_reranking_prompt(query, documents[: top_k])
            
            # Call via Hugging Face Inference API or similar
            # This is pseudo-code; adjust based on actual API
            url = f"https://api-inference.huggingface.co/models/{self.model}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 100,
                    "temperature": 0.3,
                }
            }
            
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Parse output (expects JSON with scores)
            # This is pseudo-code and needs adjustment based on actual output
            result = response.json()
            scores = self._extract_scores(result, len(documents))
            
            logger.info(f"Reranked {len(documents)} documents via Gemma")
            return scores
            
        except Exception as e:
            logger.error(f"Gemma reranking failed: {e}")
            return []
    
    def _build_reranking_prompt(self, query: str, documents: List[str]) -> str:
        """Build a prompt for the Gemma model to score document relevance."""
        prompt = f"""
Query: {query}

Please rate the relevance of each document to the query on a scale of 0 to 1. 
Return a JSON object with scores. 

Documents:
"""
        for i, doc in enumerate(documents, 1):
            prompt += f"\n{i}. {doc[: 200]}..."
        
        prompt += "\n\nReturn JSON:  {\"scores\": [...]}"
        return prompt
    
    def _extract_scores(self, result: Dict[str, Any], num_docs: int) -> List[float]:
        """Extract scores from Gemma output."""
        try:
            # Pseudo-code; adjust based on actual API response
            if isinstance(result, list) and len(result) > 0:
                text = result[0]. get("generated_text", "")
                # Parse JSON from text
                import json
                json_str = text[text.find('{'):text.rfind('}')+1]
                data = json.loads(json_str)
                scores = data.get("scores", [0.5] * num_docs)
                return scores[: num_docs]
        except Exception as e:
            logger.error(f"Failed to parse Gemma scores: {e}")
        
        return [0.5] * num_docs
    
    async def close(self):
        await self.client.aclose()