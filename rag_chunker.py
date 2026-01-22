"""
RAG-ready semantic chunking for LLM context windows. 
Supports markdown, semantic similarity, and hybrid strategies.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Literal
import re

try:
    import tiktoken
except ImportError:
    tiktoken = None

from pydantic import BaseModel

logger = logging.getLogger("RAGChunker")

class Chunk(BaseModel):
    """Single text chunk for RAG."""
    id: int
    text: str
    token_count: int
    start_char:  int
    end_char: int
    source_section: Optional[str] = None  # e.g., "## Introduction"

class ChunkingResult(BaseModel):
    """Result of chunking operation."""
    success: bool
    chunks: List[Chunk]
    total_tokens: int
    message: str  # Success or error message

class RAGChunker:
    """
    Intelligent text chunker for RAG pipelines.
    Strategies:  markdown (header-based), semantic (similarity), hybrid. 
    """
    
    def __init__(
        self,
        strategy: Literal["markdown", "semantic", "hybrid"] = "hybrid",
        target_chunk_size: int = 350,
        overlap_tokens: int = 50,
    ):
        self.strategy = strategy
        self.target_chunk_size = target_chunk_size
        self.overlap_tokens = overlap_tokens
        
        # Initialize tokenizer
        self.tokenizer = self._init_tokenizer()
        
        logger.info(
            f"RAGChunker initialized:  strategy={strategy}, "
            f"target_size={target_chunk_size} tokens"
        )
    
    def _init_tokenizer(self):
        """Initialize tiktoken or fallback."""
        try:
            if tiktoken is not None:
                return tiktoken. get_encoding("gpt2")
            else:
                logger.warning("tiktoken not available, using word-based tokenization")
                return None
        except Exception as e: 
            logger.warning(f"Failed to initialize tiktoken: {e}")
            return None
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            try:
                return len(self. tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed: {e}")
        
        # Fallback:  rough estimation (1 token ≈ 4 chars or 0.75 words)
        return len(text) // 4
    
    def _split_by_headers(self, text: str) -> List[tuple[str, str]]:
        """
        Split text by markdown headers.
        Returns: [(header, content), ...]
        """
        # Match headers:  # ## ### etc. 
        header_pattern = r'^(#{1,6})\s+(.+)$'
        lines = text.split('\n')
        
        sections = []
        current_header = "Introduction"
        current_content = []
        
        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # Save previous section
                if current_content:
                    sections.append((
                        current_header,
                        '\n'.join(current_content).strip()
                    ))
                
                # Start new section
                current_header = match.group(2)
                current_content = [line]
            else:
                current_content.append(line)
        
        # Save last section
        if current_content: 
            sections.append((
                current_header,
                '\n'. join(current_content).strip()
            ))
        
        return sections
    
    async def _chunk_by_markdown(self, text: str) -> List[Chunk]:
        """
        Split text by markdown headers, then further split large sections.
        """
        chunks = []
        chunk_id = 0
        total_chars = 0
        
        sections = self._split_by_headers(text)
        
        for section_header, section_content in sections: 
            if not section_content:
                continue
            
            section_tokens = self._count_tokens(section_content)
            
            # If section fits in one chunk
            if section_tokens <= self.target_chunk_size:
                chunk = Chunk(
                    id=chunk_id,
                    text=section_content,
                    token_count=section_tokens,
                    start_char=total_chars,
                    end_char=total_chars + len(section_content),
                    source_section=section_header
                )
                chunks.append(chunk)
                chunk_id += 1
                total_chars += len(section_content) + 1
            else:
                # Split large section by sentences
                sentences = re.split(r'(?<=[.!?])\s+', section_content)
                current_chunk_text = ""
                current_chunk_tokens = 0
                
                for sentence in sentences: 
                    sentence_tokens = self._count_tokens(sentence)
                    
                    if current_chunk_tokens + sentence_tokens > self.target_chunk_size:
                        # Save current chunk
                        if current_chunk_text:
                            chunk = Chunk(
                                id=chunk_id,
                                text=current_chunk_text. strip(),
                                token_count=current_chunk_tokens,
                                start_char=total_chars,
                                end_char=total_chars + len(current_chunk_text),
                                source_section=section_header
                            )
                            chunks.append(chunk)
                            chunk_id += 1
                            total_chars += len(current_chunk_text) + 1
                        
                        # Start new chunk with overlap
                        current_chunk_text = sentence
                        current_chunk_tokens = sentence_tokens
                    else:
                        current_chunk_text += " " + sentence if current_chunk_text else sentence
                        current_chunk_tokens += sentence_tokens
                
                # Save last chunk
                if current_chunk_text:
                    chunk = Chunk(
                        id=chunk_id,
                        text=current_chunk_text.strip(),
                        token_count=current_chunk_tokens,
                        start_char=total_chars,
                        end_char=total_chars + len(current_chunk_text),
                        source_section=section_header
                    )
                    chunks.append(chunk)
                    chunk_id += 1
        
        return chunks
    
    async def _chunk_by_semantic_similarity(self, text: str) -> List[Chunk]:
        """
        Split text by semantic similarity using sentence embeddings.
        Requires sentence-transformers (optional dependency).
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.warning("sentence-transformers not available, falling back to markdown")
            return await self._chunk_by_markdown(text)
        
        try:
            # Split into sentences
            sentences = re.split(r'(?<=[.! ?])\s+', text)
            if not sentences:
                return []
            
            # Load embedding model
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embeddings = await asyncio.to_thread(model. encode, sentences)
            
            # Compute similarity between consecutive sentences
            import numpy as np
            breakpoints = [0]
            
            for i in range(len(embeddings) - 1):
                similarity = np.dot(embeddings[i], embeddings[i + 1]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1]) + 1e-8
                )
                
                # If similarity drops below threshold, create breakpoint
                if similarity < 0.5:  # Tunable threshold
                    breakpoints.append(i + 1)
            
            breakpoints.append(len(sentences))
            
            # Create chunks from breakpoints
            chunks = []
            chunk_id = 0
            total_chars = 0
            
            for i in range(len(breakpoints) - 1):
                start = breakpoints[i]
                end = breakpoints[i + 1]
                
                chunk_sentences = sentences[start:end]
                chunk_text = " ".join(chunk_sentences)
                chunk_tokens = self._count_tokens(chunk_text)
                
                # If chunk still too large, split further
                if chunk_tokens > self.target_chunk_size:
                    # Recursively chunk this section
                    sub_chunks = await self._chunk_by_markdown(chunk_text)
                    for sub_chunk in sub_chunks: 
                        sub_chunk. id = chunk_id
                        chunks.append(sub_chunk)
                        chunk_id += 1
                else:
                    chunk = Chunk(
                        id=chunk_id,
                        text=chunk_text. strip(),
                        token_count=chunk_tokens,
                        start_char=total_chars,
                        end_char=total_chars + len(chunk_text),
                        source_section=None
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                
                total_chars += len(chunk_text) + 1
            
            return chunks
        
        except Exception as e: 
            logger.error(f"Semantic chunking failed: {e}, falling back to markdown")
            return await self._chunk_by_markdown(text)
    
    async def chunk(self, text: str) -> ChunkingResult:
        """
        Main chunking method.
        Handles all strategies and error cases gracefully.
        """
        if not text or not text.strip():
            return ChunkingResult(
                success=False,
                chunks=[],
                total_tokens=0,
                message="Empty text provided"
            )
        
        try:
            chunks = []
            
            if self.strategy == "markdown": 
                chunks = await self._chunk_by_markdown(text)
            elif self.strategy == "semantic": 
                chunks = await self._chunk_by_semantic_similarity(text)
            elif self.strategy == "hybrid": 
                # Try semantic first, fall back to markdown
                try:
                    chunks = await self._chunk_by_semantic_similarity(text)
                except Exception as e:
                    logger.warning(f"Semantic chunking failed in hybrid mode: {e}")
                    chunks = await self._chunk_by_markdown(text)
            
            if not chunks:
                return ChunkingResult(
                    success=False,
                    chunks=[],
                    total_tokens=0,
                    message="No chunks generated"
                )
            
            total_tokens = sum(chunk.token_count for chunk in chunks)
            
            return ChunkingResult(
                success=True,
                chunks=chunks,
                total_tokens=total_tokens,
                message=f"Successfully chunked into {len(chunks)} chunks "
                        f"({total_tokens} total tokens) using {self.strategy} strategy"
            )
        
        except Exception as e: 
            logger.error(f"Chunking failed: {e}")
            return ChunkingResult(
                success=False,
                chunks=[],
                total_tokens=0,
                message=f"Chunking failed: {str(e)}"
            )