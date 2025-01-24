import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class MultiServerMCPClient:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def connect_to_servers(self, server_configs: dict[str, str]):
        """
        Connect to multiple MCP servers
        
        Args:
            server_configs: Dictionary of server names to their script paths
        """
        for server_name, server_script_path in server_configs.items():
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                raise ValueError(f"Server script for {server_name} must be a .py or .js file")
            
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command,
                args=[server_script_path],
                env=None
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            
            await session.initialize()
            
            # List available tools for each server
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [tool.name for tool in tools])
            
            # Store the session
            self.sessions[server_name] = session

    async def process_query(self, query: str) -> str:
        """Process a query across all connected servers"""
        # Collect tools from all servers
        all_tools = []
        for server_name, session in self.sessions.items():
            response = await session.list_tools()
            server_tools = [{ 
                "name": f"{server_name}_{tool.name}",  # Prefix tool names with server name
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in response.tools]
            all_tools.extend(server_tools)

        messages = [{"role": "user", "content": query}]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=all_tools
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
            elif content.type == 'tool_use':
                # Parse server name from tool name
                full_tool_name = content.name
                server_name, tool_name = full_tool_name.split('_', 1)
                tool_args = content.input
                
                # Execute tool call on the correct server
                result = await self.sessions[server_name].call_tool(tool_name, tool_args)
                tool_results.append({"call": full_tool_name, "result": result})
                final_text.append(f"[Calling tool {full_tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                messages.append({
                    "role": "user", 
                    "content": result.content
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMulti-Server MCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    # Dictionary of server names to their script paths
    server_configs = {
        "weather": "weather.py",  # Path to weather server script
        "github": "github.py"     # Path to GitHub server script
    }

    client = MultiServerMCPClient()
    try:
        await client.connect_to_servers(server_configs)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())