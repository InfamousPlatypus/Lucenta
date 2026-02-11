import os
import logging
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel

from lucenta.core.provider import ProviderFactory, ModelProvider

class ModelResponse(BaseModel):
    thought: str
    content: str

class ModelManager:
    def __init__(self):
        self._default_provider: Optional[ModelProvider] = None
        self._step_up_provider: Optional[ModelProvider] = None # For High Complexity Tasks
        self._load_models()

    def _load_models(self):
        """Loads models from .env based on configuration."""
        # 1. Load Default Model (Local preferred)
        provider_type = os.getenv("LOCAL_PROVIDER", "ollama")
        try:
            kwargs = {}
            if provider_type == "ollama":
                kwargs = {
                    "model": os.getenv("DEFAULT_MODEL_NAME", "llama3"),
                    "base_url": os.getenv("DEFAULT_MODEL_BASE_URL", "http://localhost:11434")
                }
            elif provider_type == "llamacpp":
                kwargs = {
                    "binary_path": os.getenv("LLAMACPP_BINARY", "llama-cli"),
                    "model_path": os.getenv("LLAMACPP_MODEL_PATH", "")
                }
            # Add other provider configs as needed
            
            self._default_provider = ProviderFactory.get_provider(provider_type, **kwargs)
            logging.info(f"Loaded Default Model: {provider_type}")
        except Exception as e:
            logging.error(f"Failed to load Default Model: {e}")

        # 2. Load Step-Up Model (High Complexity)
        step_up_type = os.getenv("STEP_UP_PROVIDER", "openai")
        step_up_model = os.getenv("STEP_UP_MODEL_NAME", "gpt-4o")
        step_up_key = os.getenv("STEP_UP_API_KEY")

        if step_up_key and step_up_key != "your-key-here":
            try:
                kwargs = {"api_key": step_up_key, "model": step_up_model}
                self._step_up_provider = ProviderFactory.get_provider(step_up_type, **kwargs)
                logging.info(f"Loaded Step-Up Model: {step_up_type} ({step_up_model})")
            except Exception as e:
                logging.error(f"Failed to load Step-Up Model: {e}")
                self._step_up_provider = None # Explicitly None for fallback logic
        else:
            logging.info("No Step-Up Model configured (STEP_UP_API_KEY missing).")


    def generate(self, prompt: str, system_prompt: str = None, complexity: str = "low") -> ModelResponse:
        """
        Generates a response from the appropriate model based on complexity.
        Returns a structured ModelResponse with 'thought' and 'content'.
        """
        # Default policy: Use Default (Local) model unless complexity is "high" 
        # AND Step-Up is explicitly configured.
        provider = self._default_provider

        # --- Step-Up Logic (Consent Remote Execution) ---
        if complexity.lower() == "high" and self._step_up_provider:
            logging.info("Complexity HIGH: Stepping up to Remote Model (Conserving Local Compute).")
            provider = self._step_up_provider
        
        if not provider:
             # Critical Fallback: If everything failed, try to reload defaults
             if not self._default_provider:
                 self._load_models()
             provider = self._default_provider
             
        if not provider:
            return ModelResponse(thought="System Error", content="No model provider available.")

        try:
            raw_response = provider.generate(prompt, system_prompt=system_prompt)
            return self._parse_response(raw_response)
        except Exception as e:
            logging.error(f"Generation Error: {e}")
            if provider == self._step_up_provider and self._default_provider:
                 logging.warning("Step-Up Model failed. Retrying with Default Model...")
                 try:
                     raw_response = self._default_provider.generate(prompt, system_prompt=system_prompt)
                     return self._parse_response(raw_response)
                 except Exception as ex:
                      logging.error(f"Fallback Generation Error: {ex}")
                      return ModelResponse(thought="Error", content=f"Both models failed: {ex}")

            return ModelResponse(thought="Error", content=f"Generation failed: {e}")

    def _parse_response(self, text: str) -> ModelResponse:
        """
        Parses raw LLM output into Thought/Content structure.
        Expects format:
        Thought: ...
        Content: ... (or Final Answer: ...)
        """
        thought = ""
        content = text

        # Basic parsing logic (can be made more robust with regex)
        if "Thought:" in text:
            parts = text.split("Thought:", 1)[1]
            if "Final Answer:" in parts:
                t, c = parts.split("Final Answer:", 1)
                thought = t.strip()
                content = c.strip()
            elif "Content:" in parts: # Supporting alternative tag
                t, c = parts.split("Content:", 1)
                thought = t.strip()
                content = c.strip()
            else:
                # If thought exists but no clear separator, treat whole thing as content or try to split by newline if applicable
                # For safety, just assume the rest is content but maybe log a warning
                pass
        
        return ModelResponse(thought=thought, content=content)
