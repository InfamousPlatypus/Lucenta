import os
import subprocess
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import psutil

class ModelProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

class LocalCLIProvider(ModelProvider):
    def __init__(self, binary_path: str, args: Optional[List[str]] = None):
        self.binary_path = binary_path
        self.args = args or []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        # This is a placeholder for actual local binary execution logic
        # It depends on how the binary expects the input (stdin or arg)
        try:
            cmd = [self.binary_path] + self.args + [full_prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            return f"Error running local model: {e}"

class OpenAIProvider(ModelProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

class AnthropicProvider(ModelProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

class GeminiProvider(ModelProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Gemini handles system instructions differently in the model constructor or via content
        # For simplicity here, we'll prepended it if present
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = self.model.generate_content(full_prompt)
        return response.text

class ProviderFactory:
    @staticmethod
    def get_provider(provider_type: str, **kwargs) -> ModelProvider:
        if provider_type == "openai":
            return OpenAIProvider(**kwargs)
        elif provider_type == "anthropic":
            return AnthropicProvider(**kwargs)
        elif provider_type == "gemini":
            return GeminiProvider(**kwargs)
        elif provider_type == "local":
            return LocalCLIProvider(**kwargs)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
