import json
import time
from typing import List, Dict, Any
from openai import AsyncOpenAI, APIError
from .interfaces import ILLMProvider
from .config import settings
from .logger import get_logger

logger = get_logger(__name__)

__all__ = ["LLMProvider"]


class LLMProvider(ILLMProvider):
    """LLM Provider supporting Ollama (local) and OpenAI (cloud)."""

    def __init__(self):
        self.provider_type = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.api_key = self._get_api_key()
        self.base_url = self._get_base_url()

        logger.info(
            "llm_config",
            provider=self.provider_type,
            model=self.model,
            base_url=self.base_url,
        )

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    def _get_api_key(self) -> str:
        if self.provider_type == "openai":
            return settings.OPENAI_API_KEY
        return "ollama"  # Ollama doesn't need a real key

    def _get_base_url(self) -> str:
        if self.provider_type == "openai":
            return "https://api.openai.com/v1"
        return settings.OLLAMA_BASE_URL

    async def chat(
        self, messages: List[Dict[str, str]], temperature: float = 0.7
    ) -> str:
        start_time = time.time()
        logger.info("llm_request_start", model=self.model, message_count=len(messages))

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=temperature,
                stream=False,
            )
            elapsed = time.time() - start_time
            logger.info("llm_request_success", duration=elapsed)
            return response.choices[0].message.content or ""
        except APIError as e:
            elapsed = time.time() - start_time
            logger.error("llm_request_failed", duration=elapsed, error=str(e))
            raise e

    async def json_chat(
        self, messages: List[Dict[str, str]], schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("llm_json_request_start", model=self.model)

        json_instruction = "\n\nIMPORTANT: You must respond with valid JSON only. No markdown, no explanation."
        if schema:
            json_instruction += f" Follow this schema:\n{json.dumps(schema, indent=2)}"

        msgs_to_send = [dict(m) for m in messages]

        if msgs_to_send and msgs_to_send[0]["role"] == "system":
            msgs_to_send[0]["content"] += json_instruction
        else:
            msgs_to_send.insert(0, {"role": "system", "content": json_instruction})

        try:
            request_kwargs = {
                "model": self.model,
                "messages": msgs_to_send,
                "temperature": 0.0,
                "stream": False,
            }

            # OpenAI supports native JSON mode
            if schema and self.provider_type == "openai":
                request_kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**request_kwargs)
            content = response.choices[0].message.content or ""
            elapsed = time.time() - start_time
            logger.info("llm_json_request_success", duration=elapsed)

            # Strip markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.rsplit("```", 1)[0]

            return json.loads(content.strip())
        except (APIError, json.JSONDecodeError) as e:
            elapsed = time.time() - start_time
            logger.error("llm_json_request_failed", duration=elapsed, error=str(e))
            return {}
