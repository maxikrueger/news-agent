"""Groq API integration for digest generation - using OpenAI SDK with Groq endpoint"""

import logging
import os

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str | None = None):
        """Initialize Groq client using OpenAI SDK with Groq's OpenAI-compatible endpoint"""
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured")

        # Use OpenAI SDK with Groq's OpenAI-compatible endpoint (proven reliable)
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=self.api_key)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def create_completion(
        self,
        messages: list,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Call Groq API with simple retry logic"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
