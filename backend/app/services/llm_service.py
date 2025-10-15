"""
LLM service for interacting with AI models.
"""

import time
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from openai import AsyncOpenAI
from app.core.config import settings


class LLMService:
    """Service for interacting with Large Language Models."""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
        self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.1,
        max_tokens: int = 1000,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """Get chat completion from LLM."""
        start_time = time.time()
        
        try:
            # Try primary model (Claude)
            if model.startswith("claude") and self.anthropic:
                result = await self._call_claude(messages, model, temperature, max_tokens)
            elif model.startswith("gpt") and self.openai:
                result = await self._call_openai(messages, model, temperature, max_tokens)
            else:
                raise ValueError(f"Unsupported model: {model}")
            
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            return result
            
        except Exception as e:
            if use_fallback:
                # Try fallback model
                fallback_model = "gpt-4-turbo-preview" if model.startswith("claude") else "claude-3-5-sonnet-20241022"
                if fallback_model.startswith("claude") and self.anthropic:
                    result = await self._call_claude(messages, fallback_model, temperature, max_tokens)
                elif fallback_model.startswith("gpt") and self.openai:
                    result = await self._call_openai(messages, fallback_model, temperature, max_tokens)
                else:
                    raise e
                
                processing_time = time.time() - start_time
                result["processing_time"] = processing_time
                result["used_fallback"] = True
                return result
            else:
                raise e
    
    async def _call_claude(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call Claude API."""
        # Convert messages format for Claude
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)
        
        response = await self.anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_message or "",
            messages=user_messages
        )
        
        return {
            "content": response.content[0].text,
            "model": model,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "cost": self._calculate_claude_cost(response.usage.input_tokens, response.usage.output_tokens, model)
        }
    
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        response = await self.openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            "content": response.choices[0].message.content,
            "model": model,
            "tokens_used": response.usage.total_tokens,
            "cost": self._calculate_openai_cost(response.usage.prompt_tokens, response.usage.completion_tokens, model)
        }
    
    def _calculate_claude_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate Claude API cost."""
        # Claude 3.5 Sonnet pricing (as of October 2024)
        if "claude-3-5-sonnet" in model:
            input_cost_per_1k = 0.003
            output_cost_per_1k = 0.015
        else:
            input_cost_per_1k = 0.0025
            output_cost_per_1k = 0.0125
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        return input_cost + output_cost
    
    def _calculate_openai_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calculate OpenAI API cost."""
        # GPT-4 Turbo pricing (as of October 2024)
        if "gpt-4-turbo" in model:
            input_cost_per_1k = 0.01
            output_cost_per_1k = 0.03
        elif "gpt-4" in model:
            input_cost_per_1k = 0.03
            output_cost_per_1k = 0.06
        else:
            input_cost_per_1k = 0.001
            output_cost_per_1k = 0.002
        
        input_cost = (prompt_tokens / 1000) * input_cost_per_1k
        output_cost = (completion_tokens / 1000) * output_cost_per_1k
        return input_cost + output_cost
    
    async def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        model: str = "claude-3-5-sonnet-20241022"
    ) -> Dict[str, Any]:
        """Extract structured data from text using function calling."""
        messages = [
            {
                "role": "system",
                "content": "You are a data extraction specialist. Extract the requested information from the provided text and return it in the exact JSON format specified."
            },
            {
                "role": "user",
                "content": f"Extract the following information from this text:\n\n{text}\n\nSchema: {schema}"
            }
        ]
        
        # For now, we'll use regular completion and parse JSON
        # In production, you'd use function calling
        result = await self.chat_completion(messages, model)
        
        # Simple JSON extraction (in production, use proper JSON parsing)
        try:
            import json
            # Extract JSON from the response
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
        except:
            pass
        
        return {"error": "Could not extract structured data"}
