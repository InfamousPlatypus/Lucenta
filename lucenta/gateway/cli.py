import os
import asyncio
import sys
import logging
import re
import json
from lucenta.core.triage import TriageEngine
from lucenta.gateway.session import SessionManager
from lucenta.plugins.mcp_manager import MCPServerManager

from typing import List
from lucenta.core.memory import ProjectMemory
from lucenta.core.scheduler import TaskRunner

class CLIGateway:
    def __init__(self, triage: TriageEngine, session: SessionManager, mcp_manager: MCPServerManager = None, memory: ProjectMemory = None, scheduler: TaskRunner = None):
        self.triage = triage
        self.session = session
        self.mcp_manager = mcp_manager
        self.memory = memory
        self.scheduler = scheduler
        self.running = True
        self.history: List[str] = [] # Short-term memory buffer
        self.current_project = "global"



    async def start(self):
        print("\n" + "="*50)
        print("   Lucenta CLI Gateway - Interactive Mode")
        print("   Type 'exit' or 'quit' to stop.")
        print("   Type 'tools' to see available MCP tools.")
        print("   Type 'clear' to reset conversation memory.")
        print("="*50 + "\n")

        while self.running:
            try:
                # Use run_in_executor to handle blocking input()
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("You > ").strip()
                )

                if user_input.lower() in ['exit', 'quit']:
                    self.running = False
                    break
                
                if user_input.lower() == 'clear':
                    self.history = []
                    print("Memory cleared.")
                    continue

                if not user_input:
                    continue

                # --- SEMANTIC FAST PATH: Trivial Intent Filter ---
                # This uses the triage engine to check for trivial tasks before waking the LLM.
                intent = self.triage.get_intent(user_input)
                fast_path_handled = False
                
                if intent == "track_iss":
                    print("Lucenta > (Fast Path: Track ISS) [Executing Tool: get_iss_location]")
                    result = await self.mcp_manager.smart_call_tool("get_iss_location", {})
                    coords_match = re.search(r"latitude\":\s*([-+]?\d*\.\d+|\d+),\s*\"longitude\":\s*([-+]?\d*\.\d+|\d+)", str(result))
                    if coords_match:
                        lat, lon = coords_match.group(1), coords_match.group(2)
                        geo_result = await self.mcp_manager.smart_call_tool("reverse_geocode", {"latitude": float(lat), "longitude": float(lon)})
                        result_str = f"The ISS is currently at ({lat}, {lon}), over: {geo_result}"
                        print(f"Lucenta > {result_str}\n")
                        # Add to history so LLM knows context (e.g. for "what's the weather *there*?")
                        self.history.append(f"User: {user_input}")
                        self.history.append(f"Assistant: {result_str}")
                    else:
                        print(f"Lucenta > {result}\n")
                        self.history.append(f"User: {user_input}")
                        self.history.append(f"Assistant: {result}")
                    fast_path_handled = True

                elif intent == "track_hubble":
                    print("Lucenta > (Fast Path: Track Hubble) Hubble tracking tool is not yet integrated. Need Arxiv search?")
                    fast_path_handled = True

                elif intent == "get_weather":
                    # Extract city using a more flexible pattern
                    city_match = re.search(r"(in|for|at) ([a-zA-Z\s]+)", user_input, re.I)
                    city = city_match.group(2).strip() if city_match else "London"
                    print(f"Lucenta > (Fast Path: Weather) [Locating {city}...]")
                    geo = await self.mcp_manager.smart_call_tool("geocode", {"q": city})
                    coords = re.search(r"lat\":\s*\"([-+]?\d*\.\d+|\d+)\",\s*\"lon\":\s*\"([-+]?\d*\.\d+|\d+)\"", str(geo))
                    if coords:
                        lat, lon = coords.group(1), coords.group(2)
                        weather = await self.mcp_manager.smart_call_tool("get_current_weather", {"latitude": float(lat), "longitude": float(lon)})
                        weather_res = f"Current weather in {city}: {weather}"
                        print(f"Lucenta > {weather_res}\n")
                        self.history.append(f"User: {user_input}")
                        self.history.append(f"Assistant: {weather_res}")
                        fast_path_handled = True

                if fast_path_handled:
                    continue



                if user_input.lower() == 'tools':

                    if self.mcp_manager:
                        tools_info = self.mcp_manager.get_server_info()
                        print("\n--- Available MCP Tools ---")
                        for info in tools_info:
                            print(f"[{info['name']}] {', '.join(info['tools'][:10])}{'...' if len(info['tools']) > 10 else ''}")
                        print("---------------------------\n")
                    else:
                        print("MCP Manager not initialized.")
                    continue

                # Prepare context from history and long-term memory
                chat_history = "\n".join(self.history[-10:])
                long_term_context = ""
                if self.memory:
                    long_term_context = self.memory.get_project_context(self.current_project)
                
                # Prepare system prompt with clear Thought/Action/Observation pattern
                from datetime import datetime
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
4. If a calculation or complex logic is needed, write a PYTHON BLOCK (```python ... ```).
5. To use a tool, use the format below on a new line.

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


                print("Lucenta > thinking...")
                
                # Reasoning loop to handle multi-step thinking
                current_context = f"{chat_history}\nUser: {user_input}"
                final_msg = ""
                
                for turn in range(6): # Increased to 6 turns
                    response = self.triage.generate(current_context, system_prompt=system_prompt)
                    
                    # --- SAFE PYTHON EXECUTION (HIL) ---
                    # Check for Python code blocks
                    python_match = re.search(r"```python(.*?)```", response, re.DOTALL)
                    if python_match:
                        code = python_match.group(1).strip()
                        print("\n" + "="*40)
                        print("🤖 PROPOSED PYTHON CODE:")
                        print(code)
                        print("="*40)
                        approval = input("\nLucenta > Run this code? [y/N]: ").strip().lower()
                        
                        if approval == 'y':
                            try:
                                # Capture stdout
                                from io import StringIO
                                import contextlib
                                
                                output_buffer = StringIO()
                                with contextlib.redirect_stdout(output_buffer):
                                    exec_locals = {}
                                    exec(code, {}, exec_locals)
                                
                                exec_output = output_buffer.getvalue()
                                result = f"Code Executed Successfully.\nOutput:\n{exec_output}\nLocals: {exec_locals}"
                                tool_name = "python_exec" # pseudo-tool for logging
                            except Exception as e:
                                result = f"Code Execution Error: {e}"
                                tool_name = "python_error"
                            
                            print(f"Lucenta > [Observation: {result.strip()}]")
                            current_context += f"\nAssistant: {response}\nObservation: {result}"
                            # Guide the LLM to finish
                            current_context += "\nSystem: Code execution complete. Use this data to provide your Final Answer. Do not re-run."
                            print("Lucenta > processing result...")
                            continue # Skip standard tool parsing if code was run

                    # Search for standard tool calls
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

                            print(f"Lucenta > [Executing Tool: {tool_name}]")
                            if tool_name == "remember" and self.memory:
                                key = args.get("key", "fact")
                                content = args.get("content", "")
                                # FIX: Ensure content is a string
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
                            
                            print(f"Lucenta > [Observation: {result}]")
                            
                            # Add the tool's output to the context and continue the loop
                            current_context += f"\nAssistant: {response}\nObservation: {result}"
                            print("Lucenta > processing result...")


                            
                            # If this was the last allowed turn, we must force a final answer next
                            if turn == 5:
                                current_context += "\nSystem: Please provide your final answer now based on the observations."
                        except Exception as e:
                            print(f"Lucenta > Error: {e}")
                            current_context += f"\nAssistant: {response}\nObservation: Error: {e}"
                    else:
                        # Clean up the final response and exit the loop
                        final_msg = response.replace("Final Answer:", "").strip()
                        print(f"Lucenta > {final_msg}\n")
                        break
                
                # Persistence: Dynamic Implicit Learning (Reflection with Staleness/Updates)
                if self.memory and final_msg:
                    # Show the LLM what it currently knows so it can update it
                    current_memories = self.memory.get_project_context(self.current_project, max_chars=1000)
                    
                    reflect_prompt = f"""Current Memory Profile:
{current_memories if current_memories else "None"}

New Interaction:
User: "{user_input}"
Assistant: "{final_msg}"

Task: Update the Memory Profile. 
1. If a previous interest (e.g. 'AI') is replaced by a new one (e.g. 'Quantum'), UPDATE the key.
2. If a fact has changed, UPDATE it.
3. If new important info is found, STORE it.
4. If a memory is now irrelevant/stale, DELETE it.

Format your response as one or more of:
STORE: key={{id}} content={{data}}
UPDATE: key={{id}} content={{new_data}}
DELETE: key={{id}}
If no changes, respond 'NONE'."""
                    
                    reflection = self.triage.generate(reflect_prompt, system_prompt="You are Lucenta's Memory Architect. Keep the user profile current and relevant.")
                    
                    # Process multi-line instructions from the reflection
                    for line in reflection.split('\n'):
                        if "STORE:" in line or "UPDATE:" in line:
                            match = re.search(r"(?:STORE|UPDATE): key=(.*) content=(.*)", line, re.IGNORECASE)
                            if match:
                                k, c = match.group(1).strip().lower(), match.group(2).strip()
                                self.memory.store_result(self.current_project, f"{k}.txt", c)
                                print(f"Lucenta > [Memory Updated: {k}]")
                        elif "DELETE:" in line:
                            match = re.search(r"DELETE: key=(.*)", line, re.IGNORECASE)
                            if match:
                                k = match.group(1).strip().lower()
                                file_path = os.path.join(self.memory.base_path, self.current_project, f"{k}.txt")
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                    print(f"Lucenta > [Memory Purged: {k}]")



                # Save the successful exchange to session history
                if final_msg:
                    self.history.append(f"User: {user_input}")
                    self.history.append(f"Assistant: {final_msg}")









            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Error in CLI Gateway: {e}")
                print(f"System Error: {e}")

        print("\nCLI Gateway stopped.")
