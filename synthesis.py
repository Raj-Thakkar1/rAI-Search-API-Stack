import asyncio
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator, List, Optional

logger = logging.getLogger("Synthesis")

SYNTHESIS_SYSTEM_PROMPT = """You are a factual answer synthesis engine.

Rules:
1) Use ONLY the provided context snippets. Do not use prior knowledge.
2) If the context is insufficient to answer, say: \"I don't know based on the provided sources.\"
3) Every factual claim must include an inline citation like [1], [2], etc.
4) Citations must refer to the source ids provided in the context. Do not invent citations.
5) Keep the answer concise, neutral, and directly responsive.
6) If comparing items, use a compact structure (bullets or short paragraphs) and cite each comparison point.
""" 


@dataclass(frozen=True)
class SynthesisChunk:
    source_id: int
    source_url: str
    source_title: str
    text: str
    score: Optional[float] = None


class SynthesisProvider(ABC):
    @abstractmethod
    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        raise NotImplementedError

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class GeminiSynthesisProvider(SynthesisProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def _run_stream_in_thread(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        try:
            import google.generativeai as genai
        except Exception as e:
            raise RuntimeError("google-generativeai is required for Gemini synthesis") from e

        if not self.api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY for Gemini synthesis")

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def producer():
            try:
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model)
                prompt = system_prompt + "\n\n" + user_prompt
                stream = model.generate_content(prompt, stream=True)
                for chunk in stream:
                    text = getattr(chunk, "text", None)
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as ex:
                loop.call_soon_threadsafe(queue.put_nowait, f"\n[ERROR] {ex}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        producer_task = asyncio.create_task(asyncio.to_thread(producer))
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            try:
                await producer_task
            except Exception:
                pass

    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        async for token in self._run_stream_in_thread(system_prompt, user_prompt):
            yield token

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import google.generativeai as genai
        except Exception as e:
            raise RuntimeError("google-generativeai is required for Gemini synthesis") from e

        if not self.api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY for Gemini synthesis")

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        prompt = system_prompt + "\n\n" + user_prompt
        resp = await asyncio.to_thread(lambda: model.generate_content(prompt))
        text = getattr(resp, "text", None)
        return text or ""


class OpenAISynthesisProvider(SynthesisProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        try:
            from openai import AsyncOpenAI
        except Exception as e:
            raise RuntimeError("openai package is required for OpenAI synthesis") from e

        if not self.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY for OpenAI synthesis")

        client = AsyncOpenAI(api_key=self.api_key)
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.2,
        )

        async for event in resp:
            delta = event.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
        except Exception as e:
            raise RuntimeError("openai package is required for OpenAI synthesis") from e

        if not self.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY for OpenAI synthesis")

        client = AsyncOpenAI(api_key=self.api_key)
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


class ZaiSynthesisProvider(SynthesisProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.z.ai/api/paas/v4/"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        try:
            from openai import AsyncOpenAI
        except Exception as e:
            raise RuntimeError("openai package is required for Z.ai synthesis") from e

        if not self.api_key:
            raise RuntimeError("Missing ZAI_API_KEY for Z.ai synthesis")

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.2,
        )

        async for event in resp:
            delta = event.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
        except Exception as e:
            raise RuntimeError("openai package is required for Z.ai synthesis") from e

        if not self.api_key:
            raise RuntimeError("Missing ZAI_API_KEY for Z.ai synthesis")

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


class SynthesisService:
    def __init__(
        self,
        provider: SynthesisProvider,
        system_prompt: str = SYNTHESIS_SYSTEM_PROMPT,
    ):
        self.provider = provider
        self.system_prompt = system_prompt

    def build_context(self, chunks: List[SynthesisChunk], max_chars: int = 24000) -> str:
        lines: List[str] = []
        used = 0
        for ch in chunks:
            header = f"[Source {ch.source_id}] {ch.source_title} ({ch.source_url})\n"
            body = ch.text.strip()
            block = header + body + "\n\n"
            if used + len(block) > max_chars:
                break
            lines.append(block)
            used += len(block)
        return "".join(lines)

    def build_user_prompt(self, query: str, chunks: List[SynthesisChunk]) -> str:
        context = self.build_context(chunks)
        return (
            f"Question: {query}\n\n"
            f"Context snippets (cite sources by number):\n\n{context}\n"
            "Write the answer now."
        )

    async def stream_answer(self, query: str, chunks: List[SynthesisChunk]) -> AsyncGenerator[str, None]:
        user_prompt = self.build_user_prompt(query, chunks)
        async for token in self.provider.stream(self.system_prompt, user_prompt):
            yield token

    async def generate_answer(self, query: str, chunks: List[SynthesisChunk]) -> str:
        user_prompt = self.build_user_prompt(query, chunks)
        return await self.provider.generate(self.system_prompt, user_prompt)

    async def deconstruct_query(self, query: str, max_subqueries: int = 3) -> List[str]:
        prompt = (
            "Convert the user question into a small set of focused web search queries. "
            f"Return ONLY a JSON array of strings, length 1 to {max_subqueries}.\n\n"
            f"User question: {query}"
        )

        text = await self.provider.generate(
            system_prompt="You output only valid JSON.",
            user_prompt=prompt,
        )

        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                queries = [str(x).strip() for x in data if str(x).strip()]
                if queries:
                    return queries[:max_subqueries]
        except Exception:
            pass

        return [query]
