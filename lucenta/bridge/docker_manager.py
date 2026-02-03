import os
import subprocess
import tempfile
import logging

class DockerLocker:
    def __init__(self):
        self.logger = logging.getLogger("DockerLocker")

    def run_skill_command(self, skill_path: str, command: str, dependencies: list, approval_hook=None):
        """
        Runs a command in a sandboxed Docker container.
        """
        # 1. HIL Guard Check
        if approval_hook:
            if not approval_hook(command):
                self.logger.warning(f"Command rejected by HIL: {command}")
                return None

        # Determine base image based on dependencies
        base_image = "python:3.9-slim"
        if "npm" in dependencies or "node" in dependencies:
            base_image = "node:18-slim"
        elif "gh" in dependencies:
            base_image = "alpine:latest"

        # Unique tag based on dependencies and base image
        tag_suffix = "-".join(sorted(dependencies)) if dependencies else "default"
        tag = f"lucenta-runtime-{base_image.replace(':', '-')}-{tag_suffix}"

        # Check if image already exists
        img_check = subprocess.run(["docker", "images", "-q", tag], capture_output=True, text=True)

        if not img_check.stdout.strip():
            # Build the container only if it doesn't exist
            with tempfile.TemporaryDirectory() as tmpdir:
                dockerfile_content = f"""
FROM {base_image}
WORKDIR /app
{self._get_dependency_setup(dependencies)}
"""
                dockerfile_path = os.path.join(tmpdir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                self.logger.info(f"Building sandbox image: {tag}...")
                subprocess.run(["docker", "build", "-t", tag, tmpdir], check=True)
        else:
            self.logger.info(f"Using existing sandbox image: {tag}")

        # Run the command with Read-Only mount
        # We mount the skill path to /app in the container
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{os.path.abspath(skill_path)}:/app:ro",
            tag,
            "sh", "-c", command
        ]

        self.logger.info(f"Executing in sandbox: {command}")
        result = subprocess.run(docker_cmd, capture_output=True, text=True)

        # Log security profile (simple version)
        self._log_security_profile(skill_path, command, result)

        return result

    def _get_dependency_setup(self, dependencies: list) -> str:
        setup = ""
        if "gh" in dependencies:
            setup += "RUN apk add --no-cache github-cli\n"
        return setup

    def _log_security_profile(self, skill_path: str, command: str, result):
        profile_path = os.path.join(skill_path, "security_profile.json")

        egress_detected = "http" in command or "curl" in command or "wget" in command

        profile = {
            "last_command": command,
            "exit_code": result.returncode,
            "network_egress": egress_detected,
            "timestamp": ""
        }

        try:
            import json
            from datetime import datetime
            profile["timestamp"] = datetime.now().isoformat()

            existing = {}
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    existing = json.load(f)

            if "history" not in existing:
                existing["history"] = []
            existing["history"].append(profile)
            existing["last_egress"] = egress_detected or existing.get("last_egress", False)

            with open(profile_path, 'w') as f:
                json.dump(existing, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to log security profile: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    locker = DockerLocker()
    print("Docker Locker initialized.")
