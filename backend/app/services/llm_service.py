"""
LLM service for interacting with AI models (async clients only).
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover
    try:
        # Older anthropic SDKs may only expose sync Anthropic
        from anthropic import Anthropic as _SyncAnthropic  # noqa: F401

        AsyncAnthropic = None  # type: ignore
    except ImportError:
        AsyncAnthropic = None  # type: ignore


class LLMService:
    """Service for interacting with Large Language Models via async clients."""

    def __init__(self) -> None:
        self.primary_model = settings.LLM_PRIMARY_MODEL or "claude-sonnet-4-20250514"
        self.fallback_model = settings.LLM_FALLBACK_MODEL or "gpt-4.1-mini"

        self.anthropic = None
        self.openai = None

        if settings.ANTHROPIC_API_KEY and AsyncAnthropic is not None:
            self.anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        if settings.OPENAI_API_KEY and AsyncOpenAI is not None:
            self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @property
    def available(self) -> bool:
        return bool(self.anthropic or self.openai)

    def provider_status(self) -> Dict[str, str]:
        return {
            "anthropic": "configured" if self.anthropic else "unavailable",
            "openai": "configured" if self.openai else "unavailable",
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        use_fallback: bool = True,
    ) -> Dict[str, Any]:
        """Get chat completion from LLM. Never awaits a sync client."""
        start_time = time.time()
        model = model or self.primary_model

        if not self.available:
            return {
                "content": "",
                "model": model,
                "tokens_used": 0,
                "cost": 0.0,
                "error": "No LLM API keys configured (ANTHROPIC_API_KEY / OPENAI_API_KEY)",
                "processing_time": time.time() - start_time,
            }

        try:
            result = await self._dispatch(messages, model, temperature, max_tokens)
            result["processing_time"] = time.time() - start_time
            return result
        except Exception as primary_error:
            if not use_fallback:
                raise

            fallback = (
                self.fallback_model
                if not model.startswith("gpt")
                else self.primary_model
            )
            # Prefer the other provider when possible
            if model.startswith("claude"):
                fallback = self.fallback_model if self.fallback_model.startswith("gpt") else "gpt-4.1-mini"
            elif model.startswith("gpt"):
                fallback = self.primary_model if self.primary_model.startswith("claude") else "claude-sonnet-4-20250514"

            try:
                result = await self._dispatch(messages, fallback, temperature, max_tokens)
                result["processing_time"] = time.time() - start_time
                result["used_fallback"] = True
                result["primary_error"] = str(primary_error)
                return result
            except Exception:
                raise primary_error from None

    async def _dispatch(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        if model.startswith("claude"):
            if not self.anthropic:
                raise RuntimeError("Anthropic client not configured or AsyncAnthropic unavailable")
            return await self._call_claude(messages, model, temperature, max_tokens)
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            if not self.openai:
                raise RuntimeError("OpenAI client not configured")
            return await self._call_openai(messages, model, temperature, max_tokens)
        # Default: try OpenAI-compatible name, else Claude
        if self.openai:
            return await self._call_openai(messages, model, temperature, max_tokens)
        if self.anthropic:
            return await self._call_claude(messages, model, temperature, max_tokens)
        raise ValueError(f"Unsupported model or no clients: {model}")

    async def _call_claude(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Call Claude via AsyncAnthropic only."""
        system_message = None
        user_messages: List[Dict[str, str]] = []

        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages or [{"role": "user", "content": ""}],
        }
        if system_message:
            kwargs["system"] = system_message

        response = await self.anthropic.messages.create(**kwargs)

        text = ""
        if response.content:
            block = response.content[0]
            text = getattr(block, "text", str(block))

        input_tokens = getattr(response.usage, "input_tokens", 0) or 0
        output_tokens = getattr(response.usage, "output_tokens", 0) or 0

        return {
            "content": text,
            "model": model,
            "tokens_used": input_tokens + output_tokens,
            "cost": self._calculate_claude_cost(input_tokens, output_tokens, model),
        }

    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Call OpenAI via AsyncOpenAI only."""
        response = await self.openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0

        return {
            "content": response.choices[0].message.content or "",
            "model": model,
            "tokens_used": total_tokens,
            "cost": self._calculate_openai_cost(prompt_tokens, completion_tokens, model),
        }

    def _calculate_claude_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Approximate Claude API cost."""
        if "haiku" in model:
            input_cost_per_1k, output_cost_per_1k = 0.00025, 0.00125
        elif "opus" in model:
            input_cost_per_1k, output_cost_per_1k = 0.015, 0.075
        else:
            # Sonnet-class default
            input_cost_per_1k, output_cost_per_1k = 0.003, 0.015

        return (input_tokens / 1000) * input_cost_per_1k + (output_tokens / 1000) * output_cost_per_1k

    def _calculate_openai_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Approximate OpenAI API cost."""
        if "gpt-4.1-mini" in model or "gpt-4o-mini" in model:
            input_cost_per_1k, output_cost_per_1k = 0.00015, 0.0006
        elif "gpt-4.1" in model or "gpt-4o" in model:
            input_cost_per_1k, output_cost_per_1k = 0.0025, 0.01
        elif "gpt-4-turbo" in model:
            input_cost_per_1k, output_cost_per_1k = 0.01, 0.03
        elif "gpt-4" in model:
            input_cost_per_1k, output_cost_per_1k = 0.03, 0.06
        else:
            input_cost_per_1k, output_cost_per_1k = 0.001, 0.002

        return (prompt_tokens / 1000) * input_cost_per_1k + (completion_tokens / 1000) * output_cost_per_1k

    async def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured data from text."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a data extraction specialist. Extract the requested "
                    "information from the provided text and return it in the exact JSON format specified."
                ),
            },
            {
                "role": "user",
                "content": f"Extract the following information from this text:\n\n{text}\n\nSchema: {schema}",
            },
        ]

        result = await self.chat_completion(messages, model=model or self.primary_model)
        if result.get("error"):
            return {"error": result["error"]}

        try:
            content = result.get("content") or ""
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        return {"error": "Could not extract structured data"}
