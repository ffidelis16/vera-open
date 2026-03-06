"""LLMProvider — interface abstrata para provedores de LLM."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Interface para provedores de LLM."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Gera texto a partir de prompt."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 1000,
    ) -> dict:
        """Gera resposta estruturada (JSON). Para scoring, avaliações, etc."""
        ...
