import json
import os
from typing import Dict, Any, List
from lucenta.core.triage import TriageEngine

class SecurityAuditor:
    def __init__(self, triage_engine: TriageEngine):
        self.triage_engine = triage_engine

    def scan_code(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Scans a single file for security smells using the TriageEngine.
        """
        system_prompt = """
        You are a security auditor specializing in static analysis of source code.
        Your task is to perform a 'Smell Test' on the provided code and identify security risks.
        Specifically, look for:
        1. Unauthorized Egress: Hardcoded IPs, sockets, or fetch/requests/axios calls.
        2. Filesystem Escapes: Access to sensitive paths like /etc, /proc, /var/log, or Windows System32.
        3. Obfuscation: High-entropy strings, base64 encoded payloads, or eval() blocks.

        Output your findings in valid JSON format ONLY. Do not include any other text.
        Structure:
        {
            "file": "path/to/file",
            "risk_score": 0-10,
            "findings": [
                {"category": "Egress|Filesystem|Obfuscation", "description": "...", "severity": "High|Medium|Low"}
            ],
            "is_safe": true|false,
            "recommendation": "..."
        }
        """

        prompt = f"Analyze this file for security risks:\nFile: {file_path}\n\nContent:\n{content}"

        response = self.triage_engine.generate(prompt, task_type="Thought", system_prompt=system_prompt)

        return self._parse_json_response(response, file_path)

    def _parse_json_response(self, response: str, file_path: str) -> Dict[str, Any]:
        try:
            # Find the first { and last }
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON object found in response")
        except Exception as e:
            return {
                "file": file_path,
                "risk_score": 10,
                "findings": [{"category": "Error", "description": f"Failed to parse auditor response: {e}", "severity": "High"}],
                "is_safe": False,
                "recommendation": "Check the raw response for issues.",
                "raw_response": response
            }

    def scan_directory(self, directory_path: str, extensions: List[str] = ['.py', '.cpp', '.js', '.rs']) -> List[Dict[str, Any]]:
        results = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', errors='ignore') as f:
                        content = f.read()
                    results.append(self.scan_code(full_path, content))
        return results

    def get_security_label(self, scan_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates results into a single Security Label for HIL approval.
        """
        if not scan_results:
            return {"status": "No files found to scan", "is_safe": True}

        overall_risk = max(r.get('risk_score', 0) for r in scan_results)
        all_findings = []
        for r in scan_results:
            for f in r.get('findings', []):
                f['file'] = r.get('file')
                all_findings.append(f)

        is_safe = all(r.get('is_safe', False) for r in scan_results) and overall_risk < 5

        return {
            "overall_risk_score": overall_risk,
            "findings_summary": all_findings,
            "is_safe_auto_approve": is_safe,
            "label": "SECURE" if is_safe else "WARNING" if overall_risk < 8 else "DANGER"
        }
