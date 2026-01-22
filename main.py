""" 
Deep Search & Extraction API v3.0
=================================

Generative Answer Engine:
- Query deconstruction (sub-queries)
- Discovery: DuckDuckGo
- Acquisition: tiered HTTP fetch + Playwright fallback
- Extraction: Trafilatura + LXML (assets)
- Intelligence: semantic reranking + chunking
- Synthesis: RAG generation with inline citations
- Streaming: Server-Sent Events (status/token/final)

Author: Deep Search Team
Date: 2026-01-21
"""

import asyncio
import json
import logging
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional, Literal, Union

import uvicorn
import trafilatura
from trafilatura.settings import use_config
from duckduckgo_search import DDGS
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from lxml import html as lhtml
from starlette.responses import StreamingResponse
from starlette.responses import JSONResponse
from starlette.responses import FileResponse
from contextlib import asynccontextmanager

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from config import load_config, Config
from browser_fallback import TieredFetcher
from cache_manager import FileBasedCache, CacheStats
from rag_chunker import RAGChunker, Chunk
from reranker import SemanticReranker
from synthesis import SynthesisChunk, SynthesisService, GeminiSynthesisProvider, OpenAISynthesisProvider, ZaiSynthesisProvider

# Windows Event Loop Policy for Playwright compatibility
# This must be set BEFORE any event loop is created (including by uvicorn)
# Note: Playwright requires WindowsProactorEventLoopPolicy for subprocess support
if sys.platform.startswith("win"):
    try:
        # Import nest_asyncio to allow nested event loops on Windows
        import nest_asyncio
        nest_asyncio.apply()
        
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger_temp = logging.getLogger("DeepSearchAPI")
        logger_temp.info("Set WindowsProactorEventLoopPolicy with nest_asyncio for Playwright compatibility")
    except ImportError:
        # Fallback if nest_asyncio is not installed
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger_temp = logging.getLogger("DeepSearchAPI")
            logger_temp.warning("nest_asyncio not found - Playwright may have issues. Install with: pip install nest-asyncio")
        except Exception as e:
            logger_temp = logging.getLogger("DeepSearchAPI")
            logger_temp.warning(f"Failed to set WindowsProactorEventLoopPolicy: {e}")
    except Exception as e:
        logger_temp = logging.getLogger("DeepSearchAPI")
        logger_temp.warning(f"Failed to configure event loop for Playwright: {e}")

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DeepSearchAPI")

# Load config
config = load_config()

# Trafilatura config
traf_config = use_config()
traf_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "5")

# --- DATA MODELS ---

class MediaAsset(BaseModel):
    type: str  # image, video, iframe, audio
    src: str
    alt: Optional[str] = None

class FileDownload(BaseModel):
    text: str
    url: str
    extension: str

class SiteNode(BaseModel):
    url: str
    text: str

class ChunkMetadata(BaseModel):
    """Metadata about chunking operation."""
    success: bool
    strategy: str
    total_chunks: int
    total_tokens: int
    message: str

class RichDocument(BaseModel):
    # Metadata
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    sitename: Optional[str] = None
    fingerprint: Optional[str] = None  # SimHash
    
    # Core Content
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None
    
    # Visuals & Structure
    images: List[MediaAsset] = []
    videos: List[MediaAsset] = []
    tables: List[str] = []
    downloads: List[FileDownload] = []
    
    # Navigation
    internal_link_tree: List[SiteNode] = []
    external_links: List[str] = []
    
    # RAG Chunking
    chunks: Optional[List[Chunk]] = None
    chunking_metadata: Optional[ChunkMetadata] = None
    
    # Reranking score (if reranked)
    reranking_score: Optional[float] = None

class SearchRequest(BaseModel):
    """Extended search request with new parameters."""
    query: str
    max_results: int = Field(5, le=20)
    deep_extract: bool = True
    stream: bool = False
 
    # Query deconstruction
    deconstruct_query: bool = True
    max_subqueries: int = Field(3, ge=1, le=5)
 
    # Synthesis options
    enable_synthesis: bool = True
    synthesis_top_k_chunks: int = Field(12, ge=1, le=50)
    
    # Reranking options
    enable_reranking: bool = False
    rerank_top_k: Optional[int] = None  # Rerank only top-k results
    
    # Chunking options
    enable_chunking: bool = True
    chunking_strategy:  Literal["markdown", "semantic", "hybrid"] = "hybrid"
    target_chunk_size: int = 350

class SourceItem(BaseModel):
    id: int
    url: str
    title: Optional[str] = None
    score: Optional[float] = None


class GraphPoint(BaseModel):
    x: Union[str, int, float]
    y: Optional[float] = None
    note: Optional[str] = None


class GraphSeries(BaseModel):
    name: str
    unit: Optional[str] = None
    points: List[GraphPoint]


class GraphSpec(BaseModel):
    id: str
    title: str
    type: Literal["line", "bar", "scatter", "table", "comparison"]
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    series: List[GraphSeries]
    citations: List[int]


class AnswerEngineResponse(BaseModel):
    query: str
    subqueries: List[str]
    answer: Optional[str] = None
    sources: List[SourceItem]
    total_results: int
    results: List[RichDocument]

    graphs: Optional[List[GraphSpec]] = None

    # Metadata
    search_timestamp: str
    search_duration_seconds: float

    # Reranking metadata
    reranking_enabled: bool
    reranking_status: Optional[str] = None

    # Caching metadata
    cache_hit: bool

class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    stats: CacheStats
    timestamp: str

# --- CORE SERVICES ---

class SearchService:
    """DuckDuckGo search wrapper."""

    def search_sync(self, query: str, max_results: int) -> List[dict]:
        """Synchronous DDG search."""
        results = []
        try:
            ddgs = DDGS()
            ddg_gen = ddgs.text(query, max_results=max_results)
            if ddg_gen:
                results = list(ddg_gen)
        except Exception as e:
            logger.error(f"DDG search failed: {e}")
        return results

class ExtractionWorker:
    """Heavy HTML parsing (static methods for multiprocessing)."""
    
    @staticmethod
    def _extract_assets_and_tree(html_content: str, base_url: str) -> dict:
        """Extract visuals, files, and navigation tree from HTML."""
        if not html_content:
            return {}

        try:
            tree = lhtml.fromstring(html_content)
            tree.make_links_absolute(base_url)
        except Exception: 
            return {}

        assets = {
            "images": [],
            "videos": [],
            "tables": [],
            "downloads": [],
            "internal_tree": [],
            "external_links": []
        }

        # Extract Images
        for img in tree.xpath('//img'):
            src = img.get('src')
            if src:
                assets['images'].append({
                    "type": "image",
                    "src": src,
                    "alt": img.get('alt', '')
                })

        # Extract Videos/Iframes
        for vid in tree.xpath('//video | //iframe | //embed | //object'):
            src = vid.get('src')
            if src:
                tag = vid.tag
                assets['videos'].append({
                    "type": "video" if tag == "video" else "iframe",
                    "src": src,
                    "alt": "Embedded Media"
                })

        # Extract Tables
        for tbl in tree.xpath('//table'):
            assets['tables'].append(lhtml.tostring(tbl, encoding='unicode'))

        # Extract Links
        from urllib.parse import urlparse
        base_domain = urlparse(base_url).netloc
        file_extensions = {'.pdf', '.zip', '.csv', '.xlsx', '.docx', '.json', '.xml'}

        for a in tree.xpath('//a'):
            href = a.get('href')
            text = (a.text_content() or "").strip()
            
            if not href:
                continue

            parsed_href = urlparse(href)
            path = parsed_href.path.lower()
            
            # File Downloads
            if any(path.endswith(ext) for ext in file_extensions):
                ext = path.split('.')[-1]
                assets['downloads'].append({
                    "text": text or "Download",
                    "url": href,
                    "extension": ext
                })
                continue

            # Internal vs External
            if parsed_href.netloc == base_domain or parsed_href.netloc == "": 
                if href != base_url and text:
                    assets['internal_tree'].append({"url": href, "text": text})
            else:
                if not href.startswith("javascript") and not href.startswith("mailto"):
                    assets['external_links'].append(href)

        # Deduplicate tree
        seen_urls = set()
        unique_tree = []
        for node in assets['internal_tree']: 
            if node['url'] not in seen_urls: 
                seen_urls.add(node['url'])
                unique_tree.append(node)
        assets['internal_tree'] = unique_tree

        return assets

    @staticmethod
    def parse_html(html_content: str, url: str) -> Optional[dict]:
        """Master parsing:  Trafilatura (text) + LXML (assets)."""
        if not html_content:
            return None

        # Trafilatura extraction
        bare_content = trafilatura.extract(
            html_content,
            include_comments=True,
            include_tables=True,
            include_images=True,
            include_links=True,
            output_format='markdown',
            config=traf_config
        )
        
        if not bare_content:
            bare_content = ""

        metadata = trafilatura.extract_metadata(html_content)
        
        # Custom asset extraction
        assets = ExtractionWorker._extract_assets_and_tree(html_content, url)
        
        # SimHash fingerprint
        fingerprint = None
        if bare_content:
            try:
                from trafilatura.hashing import Simhash
                fingerprint = Simhash(bare_content).to_hex()
            except Exception as e:
                logger.debug(f"SimHash failed: {e}")

        return {
            "url": url,
            "metadata": metadata.as_dict() if metadata else {},
            "content": bare_content,
            "assets": assets,
            "fingerprint": fingerprint
        }

class PipelineOrchestrator:
    """Main pipeline orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.search_service = SearchService()
        
        # Initialize fetcher with browser fallback
        self.fetcher = TieredFetcher(config.playwright)
        
        # Initialize cache
        self.cache = FileBasedCache(config.cache)
        
        # Initialize reranker
        self.reranker = SemanticReranker(
            embedding_config=config.google_embedding,
            fallback_config=config.google_fallback,
            reranker_config=config.reranker
        )
        
        # Initialize chunker
        self.chunker_default = RAGChunker(
            strategy=config.chunking.strategy,
            target_chunk_size=config.chunking.target_chunk_size,
            overlap_tokens=config.chunking.overlap_tokens
        )

        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._process_pool_task_count: int = 0
        self._process_pool_recycle_tasks: int = int(os.getenv("EXTRACTION_POOL_RECYCLE_TASKS", "500"))

        self.synthesis_service: Optional[SynthesisService] = None
        
        logger.info("PipelineOrchestrator initialized")
    
    async def initialize(self):
        """Async initialization (browser pool, etc)."""
        await self.fetcher.initialize()
        self._process_pool = ProcessPoolExecutor(
            max_workers=int(os.getenv("EXTRACTION_WORKERS", "4"))
        )
        self._process_pool_task_count = 0

        provider = self._init_synthesis_provider()
        if provider:
            self.synthesis_service = SynthesisService(provider=provider)
        logger.info("Fetcher initialized")

    def _init_synthesis_provider(self):
        provider_name = os.getenv("SYNTHESIS_PROVIDER", "gemini").strip().lower()
        if provider_name == "zai":
            api_key = os.getenv("ZAI_API_KEY", "").strip()
            model = (os.getenv("ZAI_MODEL") or "").strip() or "glm-4.7-flash"
            base_url = (os.getenv("ZAI_BASE_URL") or "").strip() or "https://api.z.ai/api/paas/v4/"
            if not api_key:
                logger.warning("ZAI_API_KEY missing; synthesis disabled")
                return None
            return ZaiSynthesisProvider(api_key=api_key, model=model, base_url=base_url)

        if provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
            if not api_key:
                logger.warning("OPENAI_API_KEY missing; synthesis disabled")
                return None
            return OpenAISynthesisProvider(api_key=api_key, model=model)

        api_key = (self.config.google_fallback.api_key or "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        if not api_key:
            logger.warning("GOOGLE_API_KEY missing; synthesis disabled")
            return None
        return GeminiSynthesisProvider(api_key=api_key, model=model)

    def _heuristic_deconstruct_query(self, query: str, max_subqueries: int) -> List[str]:
        q = (query or "").strip()
        if not q:
            return [""]

        m = re.match(r"^\s*compare\s+(?P<a>.+?)\s+and\s+(?P<b>.+?)(?:\s+(?P<t>.+))?\s*$", q, flags=re.IGNORECASE)
        if m:
            a = (m.group("a") or "").strip()
            b = (m.group("b") or "").strip()
            t = (m.group("t") or "").strip()
            t_part = f" {t}" if t else ""
            qs = [
                f"{a}{t_part} specs",
                f"{b}{t_part} specs",
                f"{a} vs {b}{t_part} comparison",
            ]
            return qs[:max_subqueries]

        m = re.match(r"^\s*(?P<a>.+?)\s+(?:vs|versus)\s+(?P<b>.+?)(?:\s+(?P<t>.+))?\s*$", q, flags=re.IGNORECASE)
        if m:
            a = (m.group("a") or "").strip()
            b = (m.group("b") or "").strip()
            t = (m.group("t") or "").strip()
            t_part = f" {t}" if t else ""
            qs = [
                f"{a}{t_part} specs",
                f"{b}{t_part} specs",
                f"{a} vs {b}{t_part} comparison",
            ]
            return qs[:max_subqueries]

        return [q]
    
    async def _generate_cache_key(self, query: str, params: dict) -> str:
        """Generate cache key for search."""
        import hashlib
        key_str = f"{query}:{params}"
        return f"search:{hashlib.sha256(key_str.encode()).hexdigest()}"
    
    async def _fetch_urls_async(self, urls: List[str]) -> List[Optional[str]]:
        """Fetch URLs with tiered fallback (fast -> Playwright)."""
        tasks = [self.fetcher.fetch_url(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def _search_many(self, queries: List[str], max_results: int) -> List[dict]:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(None, self.search_service.search_sync, q, max_results)
            for q in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: List[dict] = []
        for r in results:
            if isinstance(r, Exception) or not r:
                continue
            merged.extend(r)
        return merged

    def _dedupe_results(self, raw_results: List[dict], limit: int) -> List[dict]:
        seen: set[str] = set()
        deduped: List[dict] = []
        for r in raw_results:
            href = (r.get("href") or "").strip()
            if not href:
                continue
            if href in seen:
                continue
            seen.add(href)
            deduped.append(r)
            if len(deduped) >= limit:
                break
        return deduped

    async def _parse_html_batch(self, html_contents: List[Optional[str]], urls: List[str]) -> List[dict]:
        if not self._process_pool:
            raise RuntimeError("Process pool not initialized")

        if self._process_pool_recycle_tasks > 0 and self._process_pool_task_count >= self._process_pool_recycle_tasks:
            try:
                self._process_pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._process_pool = ProcessPoolExecutor(
                max_workers=int(os.getenv("EXTRACTION_WORKERS", "4"))
            )
            self._process_pool_task_count = 0

        loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(int(os.getenv("EXTRACTION_MAX_IN_FLIGHT", "8")))

        async def run_one(html: str, url: str):
            async with semaphore:
                return await loop.run_in_executor(
                    self._process_pool,
                    ExtractionWorker.parse_html,
                    html,
                    url,
                )

        tasks = []
        for html, url in zip(html_contents, urls):
            if html:
                tasks.append(run_one(html, url))
        if not tasks:
            return []

        self._process_pool_task_count += len(tasks)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception) and r]

    def _sse(self, event: str, data) -> str:
        if isinstance(data, str):
            payload = {"event": event, "data": data}
        else:
            payload = data
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _try_parse_number(self, s: str) -> Optional[float]:
        v = (s or "").strip()
        if not v:
            return None
        v = v.replace(",", "")
        v = re.sub(r"\s+", " ", v)
        v = v.replace("%", "")
        try:
            return float(v)
        except Exception:
            return None

    def _table_to_graphs(
        self,
        table_html: str,
        source_id: int,
        graph_id_prefix: str,
        graph_title: str,
        max_rows: int,
    ) -> List[GraphSpec]:
        if not table_html:
            return []

        try:
            el = lhtml.fromstring(table_html)
        except Exception:
            return []

        rows = el.xpath(".//tr")
        if not rows:
            return []

        table: List[List[str]] = []
        for r in rows[: max_rows + 1]:
            cells = r.xpath("./th|./td")
            if not cells:
                continue
            vals = [" ".join((c.text_content() or "").split()) for c in cells]
            if any(v for v in vals):
                table.append(vals)

        if len(table) < 2:
            return []

        header = table[0]
        data_rows = table[1:]

        width = max(len(r) for r in table)
        header = (header + [""] * width)[:width]
        norm_rows = [((r + [""] * width)[:width]) for r in data_rows]
        if width < 2:
            return []

        numeric_cols: List[int] = []
        for col in range(1, width):
            hits = 0
            checked = 0
            for r in norm_rows[:max_rows]:
                checked += 1
                if self._try_parse_number(r[col]) is not None:
                    hits += 1
            if checked > 0 and hits >= max(2, int(0.5 * checked)):
                numeric_cols.append(col)

        graphs: List[GraphSpec] = []
        if numeric_cols:
            series: List[GraphSeries] = []
            for col in numeric_cols[:6]:
                name = (header[col] or f"col_{col}").strip() or f"col_{col}"
                points: List[GraphPoint] = []
                for r in norm_rows[:max_rows]:
                    x_label = (r[0] or "").strip() or "row"
                    y_val = self._try_parse_number(r[col])
                    if y_val is None:
                        continue
                    points.append(GraphPoint(x=x_label, y=y_val, note=None))
                if points:
                    series.append(GraphSeries(name=name, unit=None, points=points))

            if series:
                graphs.append(
                    GraphSpec(
                        id=f"{graph_id_prefix}-numeric",
                        title=graph_title,
                        type="bar",
                        x_label=header[0] or None,
                        y_label=None,
                        series=series,
                        citations=[source_id],
                    )
                )
        else:
            points: List[GraphPoint] = []
            for r in norm_rows[:max_rows]:
                x_label = (r[0] or "").strip() or "row"
                note = " | ".join([c for c in r[1:] if c]) or None
                points.append(GraphPoint(x=x_label, y=None, note=note))

            graphs.append(
                GraphSpec(
                    id=f"{graph_id_prefix}-table",
                    title=graph_title,
                    type="table",
                    x_label=header[0] or None,
                    y_label=None,
                    series=[GraphSeries(name="table", unit=None, points=points)],
                    citations=[source_id],
                )
            )

        return graphs

    def _build_graphs(
        self,
        rich_documents: List[RichDocument],
        source_id_by_url: Dict[str, int],
        max_graphs: int = 3,
        max_rows: int = 30,
    ) -> List[GraphSpec]:
        graphs: List[GraphSpec] = []
        for doc in rich_documents:
            if len(graphs) >= max_graphs:
                break
            if not doc.url:
                continue
            sid = source_id_by_url.get(doc.url)
            if not sid:
                continue
            if not doc.tables:
                continue

            title = (doc.title or doc.sitename or doc.url).strip()
            for idx, table_html in enumerate(doc.tables[:5]):
                if len(graphs) >= max_graphs:
                    break
                graph_id_prefix = f"src{sid}-t{idx+1}"
                graph_title = f"{title} (Table {idx+1})"
                graphs.extend(
                    self._table_to_graphs(
                        table_html=table_html,
                        source_id=sid,
                        graph_id_prefix=graph_id_prefix,
                        graph_title=graph_title,
                        max_rows=max_rows,
                    )
                )
        return graphs[:max_graphs]

    async def stream_answer_engine(self, request: SearchRequest) -> AsyncGenerator[str, None]:
        start_time = datetime.utcnow()
        cache_hit = False
        reranking_status: Optional[str] = None

        cache_key = await self._generate_cache_key(
            request.query,
            {
                "max_results": request.max_results,
                "deep_extract": request.deep_extract,
                "enable_reranking": request.enable_reranking,
                "deconstruct_query": request.deconstruct_query,
                "enable_synthesis": request.enable_synthesis,
                "chunking_strategy": request.chunking_strategy,
                "target_chunk_size": request.target_chunk_size,
            },
        )

        if self.config.cache.enabled:
            cached = await self.cache.get(cache_key)
            if cached:
                cache_hit = True
                yield self._sse("status", "Cache hit")
                yield self._sse("final", cached)
                return

        yield self._sse("status", "Deconstructing query...")
        subqueries = [request.query]
        if request.deconstruct_query:
            if self.synthesis_service:
                try:
                    subqueries = await self.synthesis_service.deconstruct_query(
                        request.query,
                        max_subqueries=request.max_subqueries,
                    )
                except Exception as e:
                    logger.warning(f"Query deconstruction failed: {e}")
                    subqueries = self._heuristic_deconstruct_query(request.query, request.max_subqueries)
            else:
                subqueries = self._heuristic_deconstruct_query(request.query, request.max_subqueries)

        yield self._sse("status", "Searching web...")
        raw_results = await self._search_many(subqueries, request.max_results)
        raw_results = self._dedupe_results(raw_results, request.max_results)

        if not request.deep_extract or not raw_results:
            simple_docs = [
                RichDocument(
                    url=r.get("href"),
                    title=r.get("title"),
                    content_markdown=r.get("body"),
                )
                for r in raw_results
            ]
            final = AnswerEngineResponse(
                query=request.query,
                subqueries=subqueries,
                answer=None,
                sources=[
                    SourceItem(id=i + 1, url=d.url, title=d.title)
                    for i, d in enumerate(simple_docs)
                    if d.url
                ],
                total_results=len(simple_docs),
                results=simple_docs,
                search_timestamp=datetime.utcnow().isoformat(),
                search_duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                reranking_enabled=False,
                reranking_status=None,
                cache_hit=cache_hit,
            )

            final_data = final.model_dump()
            if self.config.cache.enabled:
                await self.cache.set(cache_key, final_data)
            yield self._sse("final", final_data)
            return

        urls = [r.get("href") for r in raw_results if r.get("href")]
        yield self._sse("status", f"Reading {len(urls)} pages...")
        html_contents = await self._fetch_urls_async(urls)

        yield self._sse("status", "Extracting content...")
        parsed_data_list = await self._parse_html_batch(html_contents, urls)

        reranked_scores: Dict[str, float] = {}
        if request.enable_reranking and parsed_data_list:
            yield self._sse("status", "Reranking sources...")
            doc_texts = [
                (data.get("content") or "")[:500]
                or (data.get("metadata") or {}).get("title", "")
                for data in parsed_data_list
            ]

            reranker_response = await self.reranker.rerank(
                query=request.query,
                documents=doc_texts,
                top_k=request.rerank_top_k,
            )
            reranking_status = reranker_response.status.value

            score_by_text: Dict[str, float] = {
                text: float(score)
                for text, score in reranker_response.reranked_documents
                if isinstance(text, str)
            }

            def score_for_doc(data: dict) -> float:
                txt = (data.get("content") or "")[:500] or (data.get("metadata") or {}).get("title", "")
                return score_by_text.get(txt, 0.0)

            parsed_data_list.sort(key=score_for_doc, reverse=True)
            for data in parsed_data_list:
                url = data.get("url")
                if url:
                    reranked_scores[url] = score_for_doc(data)

        yield self._sse("status", "Chunking content...")
        chunker = (
            RAGChunker(
                strategy=request.chunking_strategy,
                target_chunk_size=request.target_chunk_size,
                overlap_tokens=self.config.chunking.overlap_tokens,
            )
            if request.enable_chunking
            else None
        )

        rich_documents: List[RichDocument] = []
        for data in parsed_data_list:
            meta = data.get("metadata", {})
            assets = data.get("assets", {})
            content_md = data.get("content")

            chunks = None
            chunking_metadata = None
            if chunker and content_md:
                chunking_result = await chunker.chunk(content_md)
                chunks = chunking_result.chunks if chunking_result.success else None
                chunking_metadata = ChunkMetadata(
                    success=chunking_result.success,
                    strategy=request.chunking_strategy,
                    total_chunks=len(chunking_result.chunks),
                    total_tokens=chunking_result.total_tokens,
                    message=chunking_result.message,
                )

            url = data.get("url")
            doc = RichDocument(
                url=url,
                title=meta.get("title"),
                author=meta.get("author"),
                date=meta.get("date"),
                sitename=meta.get("sitename"),
                fingerprint=data.get("fingerprint"),
                content_markdown=content_md,
                images=[MediaAsset(**img) for img in assets.get("images", [])],
                videos=[MediaAsset(**vid) for vid in assets.get("videos", [])],
                tables=assets.get("tables", []),
                downloads=[FileDownload(**dl) for dl in assets.get("downloads", [])],
                internal_link_tree=[SiteNode(**node) for node in assets.get("internal_tree", [])],
                external_links=assets.get("external_links", []),
                chunks=chunks,
                chunking_metadata=chunking_metadata,
                reranking_score=reranked_scores.get(url) if url else None,
            )
            rich_documents.append(doc)

        sources: List[SourceItem] = []
        source_id_by_url: Dict[str, int] = {}
        for doc in rich_documents:
            if not doc.url:
                continue
            if doc.url in source_id_by_url:
                continue
            sid = len(sources) + 1
            source_id_by_url[doc.url] = sid
            sources.append(
                SourceItem(
                    id=sid,
                    url=doc.url,
                    title=doc.title,
                    score=doc.reranking_score,
                )
            )

        graphs: Optional[List[GraphSpec]] = None
        try:
            built = self._build_graphs(rich_documents, source_id_by_url)
            graphs = built or None
        except Exception as e:
            logger.debug(f"Graph building failed: {e}")

        answer_text: Optional[str] = None
        if request.enable_synthesis and self.synthesis_service and sources:
            yield self._sse("status", "Generating answer...")
            synthesis_chunks: List[SynthesisChunk] = []
            for doc in rich_documents:
                if not doc.url:
                    continue
                sid = source_id_by_url.get(doc.url)
                if not sid:
                    continue
                title = doc.title or doc.sitename or doc.url
                if doc.chunks:
                    for ch in doc.chunks:
                        text = (ch.text or "").strip()
                        if not text:
                            continue
                        synthesis_chunks.append(
                            SynthesisChunk(
                                source_id=sid,
                                source_url=doc.url,
                                source_title=title,
                                text=text[:2000],
                                score=doc.reranking_score,
                            )
                        )
                        if len(synthesis_chunks) >= request.synthesis_top_k_chunks:
                            break
                else:
                    text = (doc.content_markdown or "").strip()
                    if text:
                        synthesis_chunks.append(
                            SynthesisChunk(
                                source_id=sid,
                                source_url=doc.url,
                                source_title=title,
                                text=text[:2000],
                                score=doc.reranking_score,
                            )
                        )
                if len(synthesis_chunks) >= request.synthesis_top_k_chunks:
                    break

            token_acc: List[str] = []
            try:
                async for tok in self.synthesis_service.stream_answer(request.query, synthesis_chunks):
                    token_acc.append(tok)
                    yield self._sse("token", tok)
                answer_text = "".join(token_acc).strip() or None
            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
                answer_text = None

        final = AnswerEngineResponse(
            query=request.query,
            subqueries=subqueries,
            answer=answer_text,
            sources=sources,
            total_results=len(rich_documents),
            results=rich_documents,
            graphs=graphs,
            search_timestamp=datetime.utcnow().isoformat(),
            search_duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            reranking_enabled=request.enable_reranking,
            reranking_status=reranking_status,
            cache_hit=cache_hit,
        )

        final_data = final.model_dump()
        if self.config.cache.enabled:
            try:
                await self.cache.set(cache_key, final_data)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

        yield self._sse("final", final_data)
    
    async def shutdown(self):
        """Cleanup resources."""
        await self.fetcher.shutdown()
        await self.reranker.shutdown()
        if self._process_pool:
            self._process_pool.shutdown(wait=False, cancel_futures=True)
        logger.info("PipelineOrchestrator shut down")

# --- API SETUP ---

# Global orchestrator instance
orchestrator: Optional[PipelineOrchestrator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global orchestrator
    # Startup
    orchestrator = PipelineOrchestrator(config)
    await orchestrator.initialize()
    logger.info("API started")
    
    yield
    
    # Shutdown
    if orchestrator:
        await orchestrator.shutdown()
    logger.info("API shut down")

app = FastAPI(
    title="Deep Search & Extraction API v3.0",
    description="Generative Answer Engine with deconstruction, reranking, chunking, synthesis, and SSE streaming",
    version="3.0.0",
    lifespan=lifespan
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

@app.post("/search", response_model=AnswerEngineResponse)
@limiter.limit(os.getenv("RATE_LIMIT", "30/minute"))
async def search(request: Request, payload: SearchRequest, background_tasks: BackgroundTasks):
    """
    Comprehensive search with optional reranking, chunking, and caching.
    
    Parameters:
    - query: Search query
    - max_results: Max results to fetch (1-20)
    - deep_extract:  Enable full HTML extraction
    - enable_reranking: Enable semantic reranking
    - rerank_top_k: Rerank only top-k results (None = all)
    - enable_chunking: Enable RAG chunking
    - chunking_strategy: "markdown", "semantic", or "hybrid"
    - target_chunk_size: Target chunk size in tokens
    """
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    try:
        if payload.stream:
            async def gen():
                async for evt in orchestrator.stream_answer_engine(payload):
                    yield evt

            return StreamingResponse(
                gen(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        async def run_non_stream() -> AnswerEngineResponse:
            chunks: List[str] = []
            final_obj: Optional[dict] = None
            async for evt in orchestrator.stream_answer_engine(payload):
                chunks.append(evt)
                if evt.startswith("event: final"):
                    try:
                        data_line = [l for l in evt.splitlines() if l.startswith("data: ")][0]
                        final_obj = json.loads(data_line.replace("data: ", "", 1))
                    except Exception:
                        final_obj = None
            if not final_obj:
                raise RuntimeError("Failed to produce final response")
            return AnswerEngineResponse(**final_obj)

        result = await asyncio.wait_for(
            run_non_stream(),
            timeout=config.search.search_timeout_seconds,
        )
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"Search timeout for query: {payload.query}")
        raise HTTPException(
            status_code=504,
            detail=f"Search exceeded {config.search.search_timeout_seconds}s timeout"
        )
    except Exception as e:
        logger.exception("Search pipeline error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get cache statistics."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    try:
        stats = await orchestrator.cache.get_stats()
        return CacheStatsResponse(
            stats=stats,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear")
async def clear_cache():
    """Clear all cache entries."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    try:
        success = await orchestrator.cache.clear()
        if success:
            return {"message": "Cache cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear cache")
    except Exception as e: 
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "cache_enabled": config.cache.enabled,
            "reranking_enabled": config.reranker.enabled,
            "browser_fallback_enabled": True
        }
    }


@app.get("/schemas/answer-engine-response")
async def get_answer_engine_schema():
    schema_path = os.path.join(os.path.dirname(__file__), "schemas", "answer-engine-response.schema.json")
    if not os.path.exists(schema_path):
        raise HTTPException(status_code=404, detail="Schema not found")
    return FileResponse(schema_path, media_type="application/schema+json")

if __name__ == "__main__":
    # Event loop policy is set at module level for Windows/Playwright compatibility
    # On Windows, we disable reload mode due to Playwright subprocess limitations with Python 3.12+
    # See: https://github.com/microsoft/playwright-python/issues/2014
    
    import sys
    is_windows = sys.platform.startswith("win")
    
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,  # Re-enabled reload as sync playwright fix makes it stable
        log_level="info", 
        loop="asyncio"
    )
