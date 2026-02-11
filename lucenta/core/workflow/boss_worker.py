import logging
import os
import json
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple

from lucenta.core.model_manager import ModelManager, ModelResponse
from lucenta.core.worker import DoclingWorker, DuckDuckGoWorker
from lucenta.plugins.mcp_manager import MCPServerManager
from urllib.parse import urlparse

class Boss:
    """
    The Orchestrator.
    Manages complex workflows by decomposing tasks, assigning them to specialized Workers, Therefore
    and synthesizing results using the Tiered Model Manager.
    """
    def __init__(self, model_manager: ModelManager = None, mcp_manager: MCPServerManager = None):
        self.model_manager = model_manager or ModelManager()
        self.mcp_manager = mcp_manager
        self.workers = {
            "docling": DoclingWorker(),
            "ddg": DuckDuckGoWorker()
        }
        self.max_steps = 10 
        self.session_approved = False # HIL override for current session
        self.config_dir = os.path.join("lucenta-shared", "config")
        self.trusted_domains_file = os.path.join(self.config_dir, "trusted_domains.json")
        self.trusted_domains = self._load_trusted_domains()

    def _load_trusted_domains(self) -> List[str]:
        """Loads trusted domains from file or returns defaults."""
        defaults = ["arxiv.org", "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "wikipedia.org", "cnn.com"]
        if os.path.exists(self.trusted_domains_file):
            try:
                with open(self.trusted_domains_file, "r") as f:
                    return json.load(f)
            except Exception:
                return defaults
        return defaults

    def _save_trusted_domains(self):
        """Saves current trusted domains to persistent file."""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.trusted_domains_file, "w") as f:
            json.dump(self.trusted_domains, f, indent=2)

    def cleanup(self):
        """Clean up all workers."""
        for worker in self.workers.values():
            worker.cleanup()

    def plan_task(self, goal: str, context: str = "", complexity: str = "low", depth: str = "standard") -> List[Dict[str, Any]]:
        """
        Decomposes a goal into a plan. 'depth' can be 'standard' or 'deep'.
        """
        if depth == "standard":
            depth_inst = "Create a focused plan with 3-5 distinct search queries to cover different angles of the topic."
        else:
            depth_inst = "Create an exhaustive, multi-step plan with 7+ steps. Use multiple search engines/tools and deep-dive into the results."

        # Discover tool names to help the planner
        available_tools = ""
        if self.mcp_manager:
            server_info = self.mcp_manager.get_server_info()
            available_tools = "\n".join([f"- {s['name']}: {', '.join(s['tools'][:5])}" for s in server_info])

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = f"""
        You are the Planning Intelligence. 
        CURRENT DATE: {current_time}
        Goal: {goal}
        Context: {context}
        Depth Mode: {depth.upper()} - {depth_inst}
        
        Available Workers:
        - DoclingWorker (action: parse_url, parse_file)
        - DuckDuckGoWorker (action: search, args: {{"query": "...", "num": 5, "search_type": "web"}})
        
        Available MCP Tools:
        {available_tools}

        INSTRUCTIONS:
        1. Don't be shallow. For broad topics, use multiple 'ddg' or 'mcp' search steps with DIFFERENT keywords.
        2. Sequence: Usually 'search' -> 'parse_url' (Docling) -> 'synthesize'.
        3. Be diverse. Cover news, academic (arxiv/pubmed), and technical (huggingface) if relevant.

        Format your response as a JSON list of tasks. Each task needs:
        - "worker": "docling" OR "mcp" OR "ddg"
        - "action": the specific tool/action name (e.g. "search_arxiv", "get_pubmed_abstracts", "parse_url", "search")
        - "args": dict of arguments
        - "description": "Reason for this step"

        Structure:
        Thought: ...
        Content: [ ...JSON List... ]
        """
        response: ModelResponse = self.model_manager.generate(prompt, complexity=complexity)
        
        try:
            json_match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(0))
                # For deep research, if the plan is short, we might want to prompt for more steps, 
                # but for now we trust the model.
                return plan
            else:
                logging.warning("Planner failed to return JSON list.")
                return []
        except Exception as e:
            logging.error(f"Planning Error: {e}")
            return []

    def validate_plan(self, goal: str, plan: List[Dict[str, Any]], complexity: str = "low") -> bool:
        """
        Reflection Step: The Boss analyzes the plan for logic gaps.
        """
        plan_str = json.dumps(plan, indent=2)
        prompt = f"""
        Goal: {goal}
        Proposed Plan:
        {plan_str}

        Analyze this plan for logic gaps, missing steps, or infinite loops.
        If the plan is good, respond with exactly "VALID".
        If it has issues, explain them briefly.
        """
        response = self.model_manager.generate(prompt, complexity=complexity)
        
        if "VALID" in response.content.upper():
            logging.info("Plan validated successfully.")
            return True
        else:
            logging.warning(f"Plan validation failed: {response.content}")
            return False

    async def execute_plan(self, plan: List[Dict[str, Any]]) -> List[str]:
        """
        Executes the plan. Now async and parallelized for parsing.
        """
        loop = asyncio.get_event_loop()
        results = []
        parsing_tasks = []

        async def _parse_background(title: str, link: str):
            """Helper to run docling in a separate thread and return formatted result."""
            print(f"Lucenta > [Background] Starting parse: {title}...")
            docling = self.workers.get("docling")
            # Run the synchronous docling call in the executor pool
            page_md = await loop.run_in_executor(None, lambda: docling.parse_url(link))
            print(f"Lucenta > [Background] Finished parsing: {title}")
            return f"Source ({title}) [Link: {link}]:\n{page_md}"

        for step in plan:
            # SAFETY CHECK: Ensure step is a dictionary
            if not isinstance(step, dict):
                logging.warning(f"Boss: Skipping invalid plan step (expected dict, got {type(step).__name__}): {step}")
                continue

            worker_name = step.get("worker")
            action = step.get("action")
            args = step.get("args", {})

            # SAFETY CHECK: Ensure args is a dictionary
            if not isinstance(args, dict):
                logging.warning(f"Boss: Step '{action}' has invalid args (expected dict, got {type(args).__name__}). Attempting to recover...")
                if isinstance(args, list) and len(args) > 0:
                    if action in ["parse_url", "search"]:
                        args = {"query" if action=="search" else "url": args[0]}
                    else:
                        args = {"data": args}
                else:
                    args = {}

            if worker_name == "mcp" and self.mcp_manager:
                logging.info(f"Boss: Calling MCP tool {action}...")
                try:
                    res = await self.mcp_manager.smart_call_tool(action, args)
                    
                    # HIL: Approve the results of the search/tool before adding to context
                    include_in_context = True
                    if not self.session_approved and ("search" in action or "get" in action):
                        print(f"\n📋 Results from {action}:")
                        # Show a snippet of the result
                        snippet = str(res)[:1000] + "..." if len(str(res)) > 1000 else str(res)
                        print(snippet)
                        
                        choice = await loop.run_in_executor(
                            None, lambda: input(f"Lucenta > Include these {action} results in the research context? [Y/n]: ").strip().lower()
                        )
                        if choice == 'n':
                            include_in_context = False
                    
                    if include_in_context:
                        results.append(f"Source ({action}): {res}")
                        
                        # --- "Step Into" Academic Papers Logic ---
                        if "search_arxiv" in action or "search_pubmed" in action:
                            academic_links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', str(res))
                            pdf_links = [l for l in academic_links if l.endswith('.pdf') or 'arxiv.org/pdf' in l]
                            
                            if pdf_links:
                                print(f"\n📄 Lucenta found {len(pdf_links)} full papers in {action} results.")
                                for link in pdf_links[:2]:
                                    allowed = False
                                    is_trusted = any(domain in link for domain in self.trusted_domains)
                                    
                                    if is_trusted:
                                        print(f"Lucenta > Auto-approving academic paper from trusted domain: {link}")
                                        allowed = True
                                    elif not self.session_approved:
                                        choice = await loop.run_in_executor(
                                            None, lambda: input(f"Lucenta > 'Step into' this paper? (Read full PDF): {link} [Y/n]: ").strip().lower()
                                        )
                                        if choice != 'n':
                                            allowed = True
                                    else:
                                        allowed = True

                                    if allowed:
                                        # DISPATCH TO BACKGROUND
                                        parsing_tasks.append(asyncio.create_task(_parse_background(f"Academic Paper: {link}", link)))

                except Exception as e:
                    results.append(f"Error ({action}): {e}")

            elif worker_name == "ddg":
                worker = self.workers.get("ddg")
                num = args.get("num", 5)
                search_type = args.get("search_type", "web")
                query = args.get("query")
                
                if not query:
                    logging.warning(f"Boss: Skipping DDG search with no query. Args: {args}")
                    continue

                # Perform the search
                if search_type == "news":
                    search_results = worker.news(query, num)
                else:
                    search_results = worker.search(query, num)
                
                print(f"\n🔍 DuckDuckGo found {len(search_results)} results (Query: {query}).")
                
                if not self.session_approved and search_results:
                    approve_all = await loop.run_in_executor(
                        None, lambda: input("Lucenta > Approve all links for this research session? [y/N/all]: ").strip().lower()
                    )
                    if approve_all == 'all':
                        self.session_approved = True

                for i, item in enumerate(search_results):
                    link = item.get("link")
                    title = item.get("title")
                    
                    allowed = True
                    # Check safe list auto-approval
                    if any(domain in link for domain in self.trusted_domains):
                        allowed = True
                    elif not self.session_approved:
                        print(f"[{i+1}] {title}\n    Link: {link}")
                        choice = await loop.run_in_executor(
                            None, lambda: input(f"Lucenta > Visit this link? [Y/n/stop/trust]: ").strip().lower()
                        )
                        if choice == 'n':
                            allowed = False
                        elif choice == 'stop':
                            break
                        elif choice == 'trust':
                            domain = urlparse(link).netloc
                            if domain and domain not in self.trusted_domains:
                                self.trusted_domains.append(domain)
                                self._save_trusted_domains()
                                print(f"Lucenta > Added {domain} to Safe List (Persisted).")
                            allowed = True
                    
                    if allowed:
                        # DISPATCH TO BACKGROUND
                        parsing_tasks.append(asyncio.create_task(_parse_background(title, link)))
            
            elif worker_name == "docling":
                # Direct docling calls can also be backgrounded
                action = step.get("action")
                if action == "parse_url":
                    url = args.get("url")
                    if url:
                        parsing_tasks.append(asyncio.create_task(_parse_background(f"Manual Parse: {url}", url)))
                elif action == "parse_file":
                    file_path = args.get("file_path")
                    if file_path:
                        # Since file parsing is usually local and fast, but still blocking, we'll background it too
                        async def _parse_file_bg(path):
                            print(f"Lucenta > [Background] Parsing file: {path}...")
                            docling = self.workers.get("docling")
                            res = await loop.run_in_executor(None, lambda: docling.parse_file(path))
                            return f"Source ({path}):\n{res}"
                        parsing_tasks.append(asyncio.create_task(_parse_file_bg(file_path)))

        # Wait for all background parsing to complete
        if parsing_tasks:
            print(f"\nLucenta > Waiting for {len(parsing_tasks)} background parsing tasks to complete...")
            background_results = await asyncio.gather(*parsing_tasks)
            results.extend(background_results)

        return results

    def synthesize(self, goal: str, execution_results: List[str], complexity: str = "low", depth: str = "standard") -> Tuple[str, str]:
        """
        Synthesizes results into a Summary and a Full Report.
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context = "\n\n".join(execution_results)
        
        # 1. Generate Full Report
        report_prompt = f"""
        Goal: {goal}
        CURRENT DATE: {current_time}
        Depth Mode: {depth.upper()}
        
        Data Sources:
        {context}

        Task: Produce a comprehensive research document in Markdown format.
        You MUST include the exact source links provided for every major claim or data point.
        Structure:
        - Executive Summary
        - Detailed Findings (with [Source Name](URL) citations)
        - List of All Sources (with clickable links)
        
        If DEEP mode, provide extensive detail and critical analysis of each source.
        """
        full_report_res = self.model_manager.generate(report_prompt, complexity=complexity)
        full_report = full_report_res.content

        # 2. Generate Concise Summary
        summary_prompt = f"""
        Research Goal: {goal}
        Full Report: {full_report[:2000]}... (truncated)

        Task: Provide a 2-3 sentence executive summary of the findings.
        """
        summary_res = self.model_manager.generate(summary_prompt, complexity="low")
        summary = summary_res.content

        # 3. Save to file
        file_path = self.save_report(goal, full_report)

        return summary, file_path

    def save_report(self, goal: str, content: str) -> str:
        """Saves report to lucenta-shared/research/"""
        save_dir = os.path.join("lucenta-shared", "research")
        os.makedirs(save_dir, exist_ok=True)
        
        filename = re.sub(r'[^\w\s-]', '', goal).strip().replace(' ', '_').lower()[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"{filename}_{timestamp}.md")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Research Report: {goal}\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(content)
            
        return filepath
