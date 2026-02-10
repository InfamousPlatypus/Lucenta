import json
import os
import logging
import re

class Firewall:
    def __init__(self, config_path: str = "settings.json"):
        self.config_path = config_path
        self.logger = logging.getLogger("LucentaFirewall")
        self.safe_domains = self._load_whitelist()

    def _load_whitelist(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return config.get("safe_domains", [])
            except Exception as e:
                self.logger.error(f"Failed to load config.json: {e}")
        return []

    def validate_command_egress(self, command: str) -> bool:
        """
        Heuristic check for potential network egress in a command.
        Returns True if safe (no egress or whitelisted), False if blocked.
        """
        # Look for URLs or hostnames in the command
        urls = re.findall(r'https?://([a-zA-Z0-9.-]+)', command)

        for domain in urls:
            if domain not in self.safe_domains:
                self.logger.warning(f"Blocked access to non-whitelisted domain: {domain}")
                return False

        # Check for other network tools if any domain is present
        # This is a very basic Phase 1 implementation.
        return True

    def get_firewall_status(self):
        return {
            "policy": "Strict Whitelist",
            "safe_domains_count": len(self.safe_domains),
            "safe_domains": self.safe_domains
        }

if __name__ == "__main__":
    fw = Firewall()
    print(fw.get_firewall_status())
