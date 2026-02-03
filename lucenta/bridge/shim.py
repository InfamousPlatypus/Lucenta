import os
import re
import yaml
from typing import Dict, Any, List

class OpenClawShim:
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            self.skills_dir = os.path.expanduser("~/.openclaw/skills")
        else:
            self.skills_dir = skills_dir

        self.skills = {}

    def load_skills(self):
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            return

        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                skill_md = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_md):
                    self.skills[skill_name] = self.parse_skill(skill_md)

    def parse_skill(self, filepath: str) -> Dict[str, Any]:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract YAML frontmatter
        frontmatter = {}
        yaml_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if yaml_match:
            try:
                frontmatter = yaml.safe_load(yaml_match.group(1))
            except Exception as e:
                print(f"Error parsing YAML in {filepath}: {e}")

        # Extract Commands
        commands = []
        commands_section = re.search(r'## Commands\s*\n(.*?)(?:\n##|$)', content, re.DOTALL)
        if commands_section:
            cmd_text = commands_section.group(1)
            # Find lines starting with - `command`
            matches = re.findall(r'-\s+`(.*?)`', cmd_text)
            for cmd in matches:
                commands.append(self._to_mcp_tool(cmd))

        return {
            "name": frontmatter.get("name", os.path.basename(os.path.dirname(filepath))),
            "dependencies": frontmatter.get("dependencies", []),
            "commands": commands,
            "path": os.path.dirname(filepath)
        }

    def _to_mcp_tool(self, command_str: str) -> Dict[str, Any]:
        # Extraction of placeholders like {message}
        placeholders = list(set(re.findall(r'\{(.*?)\}', command_str)))

        # More robust name extraction: use the first word but sanitize it
        # and append a hash of the command to avoid collisions
        import hashlib
        base_name = re.sub(r'[^a-zA-Z0-9_]', '_', command_str.split()[0])
        cmd_hash = hashlib.md5(command_str.encode()).hexdigest()[:6]
        tool_name = f"{base_name}_{cmd_hash}"

        # Convert to a structured tool definition compatible with MCP
        return {
            "name": tool_name,
            "description": f"Executes the shell command: {command_str}",
            "command_template": command_str,
            "parameters": {
                "type": "object",
                "properties": {p: {"type": "string", "description": f"Value for {p}"} for p in placeholders},
                "required": placeholders
            }
        }

if __name__ == "__main__":
    shim = OpenClawShim()
    # For testing, we might want to point to a local test directory
    print("OpenClaw Shim initialized.")
