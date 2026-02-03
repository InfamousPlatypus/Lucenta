import psutil
from lucenta.core.provider import ProviderFactory, ModelProvider

class TriageEngine:
    def __init__(self,
                 local_config: dict,
                 external_config: dict,
                 cpu_threshold: float = 70.0,
                 mem_threshold: float = 70.0):
        """
        local_config: dict with 'binary_path' and 'args'
        external_config: dict with 'provider' (openai, anthropic, gemini) and 'kwargs' (api_key, model)
        """
        self.local_config = local_config
        self.external_config = external_config
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold

        # We might not want to initialize them immediately if we don't have all keys,
        # but for Phase 1 this is fine.
        try:
            self.local_provider = ProviderFactory.get_provider(
                local_config.get("provider", "local"),
                **local_config.get("kwargs", {})
            )
        except Exception:
            self.local_provider = None

        try:
            self.external_provider = ProviderFactory.get_provider(
                external_config.get("provider", "openai"),
                **external_config.get("kwargs", {})
            )
        except Exception:
            self.external_provider = None

    def get_system_load(self):
        # interval=None is non-blocking
        return psutil.cpu_percent(interval=0.1), psutil.virtual_memory().percent

    def is_system_struggling(self) -> bool:
        cpu, mem = self.get_system_load()
        return cpu > self.cpu_threshold or mem > self.mem_threshold

    def select_provider(self, task_type: str) -> ModelProvider:
        if task_type == "Thought" and self.is_system_struggling():
            if self.external_provider:
                return self.external_provider

        return self.local_provider if self.local_provider else self.external_provider

    def generate(self, prompt: str, task_type: str = "Thought", system_prompt: str = None) -> str:
        provider = self.select_provider(task_type)
        if not provider:
            return "Error: No model provider available."
        return provider.generate(prompt, system_prompt=system_prompt)
