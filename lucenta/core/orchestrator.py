import asyncio
import logging
import re
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from lucenta.core.triage import TriageEngine
from lucenta.gateway.session import SessionManager
from lucenta.plugins.mcp_manager import MCPServerManager
from lucenta.core.memory import ProjectMemory
from lucenta.core.scheduler import TaskRunner

class Orchestrator:
    """
    The central intelligence core for Lucenta. 
    Decouples reasoning logic from I/O gateways (CLI, Telegram, Email).
    """
    def __init__(self, triage: TriageEngine, session: SessionManager, mcp_manager: MCPServerManager = None, 
                 memory: ProjectMemory = None, scheduler: TaskRunner = None):
        self.triage = triage
        self.session = session
        self.mcp_manager = mcp_manager
        self.memory = memory
        self.scheduler = scheduler
        self.current_project = "global"

    async def process_message(self, user_input: str, history: List[str], sink: Callable[[str], None]) -> str:
        """
        Main entry point for any gateway. 
        Processes input, executes tools, and updates memory.
        
        Args:
            user_input: The raw message from the user.
            history: Current session chat history.
            sink: A callback function to send intermediate status updates (e.g. "Thinking...")
        
        Returns:
            The final response string.
        """
        # --- 1. INTENT TRIAGE ---
        intent = self.triage.get_intent(user_input)
        
        # --- 2. FAST PATH HANDLERS ---
        if intent == "greeting" or user_input.lower().strip() in ["hello", "hi", "hey"]:
            mcp_info = ""
            if self.mcp_manager:
                servers = self.mcp_manager.get_server_info()
                mcp_info = "\n\n**Enabled MCP Servers:**\n" + "\n".join([f"- {s['name']} ({s['tool_count']} tools)" for s in servers])
            
            return (
                "Hello! I am **Lucenta**, your Advanced Agentic Research Assistant.\n\n"
                "I specialize in:\n"
                "- 🔬 **Deep Research**: Multi-step investigation with source anchoring and full-paper parsing.\n"
                "- 🛡️ **Autonomous Auditing**: Security scanning of tools and code.\n"
                "- 🌍 **Real-time Tools**: Live tracking (ISS, Weather) and MCP integration.\n"
                "- 🧠 **Persistent Memory**: Remembering facts and project context over time."
                f"{mcp_info}"
            )

        if intent == "track_iss":
            sink("(Fast Path: Track ISS) [Executing Tool: get_iss_location]")
            result = await self.mcp_manager.smart_call_tool("get_iss_location", {})
            coords_match = re.search(r"latitude\":\s*([-+]?\d*\.\d+|\d+),\s*\"longitude\":\s*([-+]?\d*\.\d+|\d+)", str(result))
            if coords_match:
                lat, lon = coords_match.group(1), coords_match.group(2)
                geo_result = await self.mcp_manager.smart_call_tool("reverse_geocode", {"latitude": float(lat), "longitude": float(lon)})
                return f"The ISS is currently at ({lat}, {lon}), over: {geo_result}"
            return str(result)

        elif intent == "get_weather":
            city_match = re.search(r"(in|for|at) ([a-zA-Z\s]+)", user_input, re.I)
            city = city_match.group(2).strip() if city_match else "London"
            sink(f"(Fast Path: Weather) [Locating {city}...]")
            geo = await self.mcp_manager.smart_call_tool("geocode", {"q": city})
            coords = re.search(r"lat\":\s*\"([-+]?\d*\.\d+|\d+)\",\s*\"lon\":\s*\"([-+]?\d*\.\d+|\d+)\"", str(geo))
            if coords:
                lat, lon = coords.group(1), coords.group(2)
                weather = await self.mcp_manager.smart_call_tool("get_current_weather", {"latitude": float(lat), "longitude": float(lon)})
                return f"Current weather in {city}: {weather}"
            return "Could not geocode the city for weather."

        elif intent in ["research", "deep_research"]:
            mode = "Deep Research" if intent == "deep_research" else "Research"
            depth = "deep" if intent == "deep_research" else "standard"
            sink(f"({mode} Mode Activated)")
            
            from lucenta.core.workflow.boss_worker import Boss
            boss = Boss(mcp_manager=self.mcp_manager)
            
            try:
                context = "\n".join(history[-5:])
                sink(f"Phase 1: Planning {depth} strategy...")
                plan = boss.plan_task(user_input, context=context, complexity="low", depth=depth)
                
                if not plan:
                    return "Could not generate a research plan."

                sink(f"Phase 2: Validating plan ({len(plan)} steps)...")
                if not boss.validate_plan(user_input, plan, complexity="low"):
                    return "Plan validation failed."

                sink("Phase 3: Executing multi-worker plan...")
                results = await boss.execute_plan(plan)
                
                sink("Phase 4: Synthesizing results...")
                summary, file_path = boss.synthesize(user_input, results, complexity="low", depth=depth)
                
                return f"{summary}\n\n[Full report saved to {file_path}]"
            finally:
                boss.cleanup()

        # --- 3. REASONING LOOP (GENERAL REASONING) ---
        sink("thinking...")
        chat_history = "\n".join(history[-10:])
        long_term_context = ""
        if self.memory:
            long_term_context = self.memory.get_project_context(self.current_project)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        tool_prompt = ""
        memory_inst = ""
        if self.memory:
            memory_inst = f"""
LONG-TERM MEMORY (Project: {self.current_project}):
{long_term_context if long_term_context else "No prior knowledge stored."}

LOCAL ACTIONS:
- remember({{"key": "subject", "content": "data"}}): Store a fact permanently.
- recall({{"query": "subject"}}): Retrieve a specific stored fact.
- schedule({{"task_name": "id", "payload": {{}}, "delay": 60}}): Schedule a task (delay in seconds).
"""

        if self.mcp_manager:
            tool_prompt = f"""
AVAILABLE MCP TOOLS:
{self.mcp_manager.get_tools_system_prompt()}

CORE INSTRUCTIONS:
1. You can chain tools together. Use result from one as input for another.
2. Use 'remember' to save information the user might need later.
3. If the user asks to "do X in 5 minutes", use 'schedule'.
4. To use a tool, use the format below on a new line.

PATTERN:
Thought: I need to check the ISS location.
...
Action: get_iss_location({{}})
Observation: {{"latitude": 51.5, "longitude": -0.1}}
FINAL ANSWER: The ISS is currently over London.
"""

        system_prompt = f"""You are Lucenta, a local AI orchestrator. 
Current time is {current_time}. 
You have access to real-time tools. Do not simulate actions. 
Check your memory for context.
{memory_inst}
{tool_prompt}
Stop generating after 'Action:' and wait for the result.
"""

        current_context = f"{chat_history}\nUser: {user_input}"
        final_msg = ""
        
        for turn in range(6):
            response = self.triage.generate(current_context, system_prompt=system_prompt)
            
            # --- TOOL EXECUTION LOGIC ---
            action_match = re.search(r"Action:\s*([a-zA-Z0-9_-]+)\s*\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1).strip()
                args_str = action_match.group(2).strip()
                
                try:
                    if not args_str or args_str in ["{}", "()"]:
                        args = {}
                    else:
                        json_match = re.search(r"(\{.*\})", args_str)
                        args = json.loads(json_match.group(1)) if json_match else {}

                    sink(f"[Executing Tool: {tool_name}]")
                    if tool_name == "remember" and self.memory:
                        key = args.get("key", "fact")
                        content = args.get("content", "")
                        if not isinstance(content, str):
                            content = json.dumps(content)
                        self.memory.store_result(self.current_project, f"{key.strip().lower()}.txt", content)
                        result = f"Successfully remembered {key}."
                    elif tool_name == "recall" and self.memory:
                        query = args.get("query", "")
                        result = self.memory.retrieve_result(self.current_project, f"{query.strip().lower()}.txt")
                        if not result:
                            result = f"No information found for {query}."
                    elif tool_name == "schedule" and self.scheduler:
                        name = args.get("task_name", "llm_task")
                        payload = args.get("payload", {})
                        delay = int(args.get("delay", 0))
                        self.scheduler.add_task(name, payload, delay)
                        result = f"Task '{name}' scheduled with {delay}s delay."
                    else:
                        result = await self.mcp_manager.smart_call_tool(tool_name, args)
                    
                    sink(f"[Observation: {str(result)[:200]}...]")
                    current_context += f"\nAssistant: {response}\nObservation: {result}"
                    if turn == 5:
                        current_context += "\nSystem: Please provide your final answer now."
                except Exception as e:
                    sink(f"Error: {e}")
                    current_context += f"\nAssistant: {response}\nObservation: Error: {e}"
            else:
                final_msg = response.replace("Final Answer:", "").strip()
                break
        
        # --- 4. MEMORY REFLECTION ---
        if self.memory and final_msg:
            current_memories = self.memory.get_project_context(self.current_project, max_chars=1000)
            reflect_prompt = f"""Update Memory Model based on:
User: "{user_input}"
Assistant: "{final_msg}"
Current Knowledge: {current_memories if current_memories else "None"}

Format:
STORE: key={{id}} content={{data}}
UPDATE: key={{id}} content={{new_data}}
DELETE: key={{id}}
Response 'NONE' if no changes."""
            
            reflection = self.triage.generate(reflect_prompt, system_prompt="You are Lucenta's Memory Architect.")
            for line in reflection.split('\n'):
                if "STORE:" in line or "UPDATE:" in line:
                    match = re.search(r"(?:STORE|UPDATE): key=(.*) content=(.*)", line, re.IGNORECASE)
                    if match:
                        k, c = match.group(1).strip().lower(), match.group(2).strip()
                        self.memory.store_result(self.current_project, f"{k}.txt", c)
            
        return final_msg
