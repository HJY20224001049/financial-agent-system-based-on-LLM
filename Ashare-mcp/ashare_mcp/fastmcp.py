"""
Simple FastMCP implementation for Ashare-MCP compatibility.
This is a minimal implementation to support the Ashare stock data MCP server.
"""

import json
import sys
import asyncio
import inspect
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
import threading

@dataclass
class Tool:
    """Tool definition"""
    name: str
    description: str
    func: Callable
    input_schema: Dict[str, Any]

class FastMCP:
    """Minimal FastMCP implementation"""

    def __init__(self, name: str = "MCP Server", instructions: str = "", dependencies: List[str] = None):
        self.name = name
        self.instructions = instructions
        self.dependencies = dependencies or []
        self.tools: Dict[str, Tool] = {}

    def tool(self, name: str = None, description: str = ""):
        """Decorator to register a tool"""
        def decorator(func):
            tool_name = name or func.__name__

            # Generate input schema from function signature
            sig = inspect.signature(func)
            params = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                param_info = {
                    "type": "string"  # Default type
                }
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = str(param.default)
                if param.annotation != inspect.Parameter.empty:
                    ann = str(param.annotation)
                    if "Annotated" in ann:
                        # Extract field description
                        pass
                    elif "str" in ann.lower():
                        param_info["type"] = "string"
                    elif "int" in ann.lower():
                        param_info["type"] = "integer"
                    elif "float" in ann.lower() or "number" in ann.lower():
                        param_info["type"] = "number"
                    elif "bool" in ann.lower():
                        param_info["type"] = "boolean"
                    elif "list" in ann.lower() or "array" in ann.lower():
                        param_info["type"] = "array"
                    elif "dict" in ann.lower() or "object" in ann.lower():
                        param_info["type"] = "object"

                params[param_name] = param_info

            input_schema = {
                "type": "object",
                "properties": params,
                "required": [p for p, param in sig.parameters.items()
                            if param.default == inspect.Parameter.empty and p != 'self']
            }

            self.tools[tool_name] = Tool(
                name=tool_name,
                description=description or func.__doc__ or "",
                func=func,
                input_schema=input_schema
            )
            return func
        return decorator

    def run(self, stdio: bool = True):
        """Run the MCP server"""
        if stdio:
            self._run_stdio()
        else:
            # For HTTP mode, we'd need a different implementation
            print("HTTP mode not supported in this minimal implementation")
            print("Use stdio mode or install the full fastmcp package")
            sys.exit(1)

    def _run_stdio(self):
        """Run MCP server using stdio protocol"""
        import sys
        import json

        # Read from stdin, write to stdout
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Handle MCP protocol messages
                response = self._handle_message(message)
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

            except KeyboardInterrupt:
                break
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

    def _handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC message"""
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if method == "initialize":
            # Return server capabilities
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            # Return list of available tools
            tools_list = []
            for tool_name, tool in self.tools.items():
                tools_list.append({
                    "name": tool_name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema
                })

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": tools_list
                }
            }

        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }

            tool = self.tools[tool_name]
            try:
                # Call the tool function with the provided arguments
                result = tool.func(**arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False)
                            }
                        ]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution error: {str(e)}"
                    }
                }

        elif method == "notifications/initialized":
            # Notification, no response needed
            return None

        elif method == "shutdown":
            # Shutdown request
            sys.exit(0)

        else:
            # Method not found
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

# For backward compatibility
__all__ = ["FastMCP"]