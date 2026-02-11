import asyncio
import logging
from typing import List
from lucenta.core.orchestrator import Orchestrator

class CLIGateway:
    """
    A lightweight terminal gateway for Lucenta.
    Delegates all logic to the central Orchestrator.
    """
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.running = True
        self.history: List[str] = []

    async def start(self):
        print("\n" + "="*50)
        print("   Lucenta CLI Gateway - Interactive Mode")
        print("   Type 'exit' or 'quit' to stop.")
        print("   Type 'tools' to see available MCP tools.")
        print("   Type 'clear' to reset conversation memory.")
        print("="*50 + "\n")

        while self.running:
            try:
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

                if user_input.lower() == 'tools':
                    if self.orchestrator.mcp_manager:
                        tools_info = self.orchestrator.mcp_manager.get_server_info()
                        print("\n--- Available MCP Tools ---")
                        for info in tools_info:
                            print(f"[{info['name']}] {', '.join(info['tools'][:10])}{'...' if len(info['tools']) > 10 else ''}")
                        print("---------------------------\n")
                    else:
                        print("MCP Manager not initialized.")
                    continue

                if not user_input:
                    continue

                # Callback to print status updates from the core
                def sink(msg: str):
                    print(f"Lucenta > {msg}")

                # Delegate to Orchestrator
                response = await self.orchestrator.process_message(
                    user_input, 
                    self.history, 
                    sink
                )

                print(f"Lucenta > {response}\n")

                # Track history
                self.history.append(f"User: {user_input}")
                self.history.append(f"Assistant: {response}")

            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Error in CLI Gateway: {e}")
                print(f"System Error: {e}")

        print("\nCLI Gateway stopped.")
