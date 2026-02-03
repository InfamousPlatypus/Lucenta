import unittest
import os
import json
from lucenta.core.provider import ProviderFactory, LocalCLIProvider
from lucenta.core.triage import TriageEngine
from lucenta.gateway.session import SessionManager

class TestLucentaCore(unittest.TestCase):
    def test_provider_factory(self):
        provider = ProviderFactory.get_provider("local", binary_path="echo", args=["test"])
        self.assertIsInstance(provider, LocalCLIProvider)
        res = provider.generate("hello")
        self.assertIn("hello", res)

    def test_triage_engine(self):
        local_config = {"binary_path": "echo", "args": ["local"]}
        external_config = {"provider": "openai", "kwargs": {"api_key": "test"}}
        engine = TriageEngine(local_config, external_config)
        # Should default to local if not struggling
        provider = engine.select_provider("Thought")
        self.assertIsInstance(provider, LocalCLIProvider)

    def test_session_manager(self):
        sm = SessionManager(lease_duration=1)
        self.assertFalse(sm.is_authorized("user1"))
        sm.grant_lease("user1")
        self.assertTrue(sm.is_authorized("user1"))
        import time
        time.sleep(1.1)
        self.assertFalse(sm.is_authorized("user1"))

if __name__ == '__main__':
    unittest.main()
