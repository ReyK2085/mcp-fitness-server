import json
from pathlib import Path

from fastmcp import FastMCP

from mcp_tools.converter_tools import TOOL_DEFINITIONS
from mcp_resources.converter_resources import RESOURCE_DEFINITIONS
from mcp_prompts.converter_prompts import PROMPT_DEFINITIONS

from utils.logging_utils import build_log_config, configure_logging

# Set up your logging preferences
LOG_FILE = Path("./logs/mcp_log_stdio.log")
configure_logging(
    build_log_config(
        LOG_FILE,
        console=True,
        logger_handlers={
            "fastmcp": ["rotating_file", "console"],
        },
        root_level="INFO",
        logger_level="DEBUG",
    )
)

mcp = FastMCP("Unit Converter (STDIO)")

# TODO To run the stdio server only using npx @modelcontextprotocol/inspector python converter_stdio_server.py

# --- Register tools ---
for tool in TOOL_DEFINITIONS:
    mcp.tool(
        name=tool["name"],
        description=tool.get("description", tool["name"])
    )(tool["func"])

# --- Register resources ---
for resource in RESOURCE_DEFINITIONS:
    uri = f"resource://{resource['name']}"
    display_name = resource.get("description", resource["name"])
    mime = resource.get("mime_type", "text/plain")
    resource_function = resource["func"]

    def register_static_resource(uri: str, name: str, mime: str, resource_function):
        @mcp.resource(uri, name=name, mime_type=mime)
        def _resource():
            # Resource functions must return: str | bytes | list[ResourceContent]
            resource_value = resource_function()
            if isinstance(resource_value, (str, bytes)):
                return resource_value
            
            # For dicts/other serializable objects, return JSON string
            return json.dumps(resource_value)

    register_static_resource(uri, display_name, mime, resource_function)

# --- Register prompt templates ---
for prompt in PROMPT_DEFINITIONS:
    print(prompt)
    name = prompt["name"]
    desc= prompt.get("description", name)
    prompt_function = prompt["func"]

    # Register the prompt function as-is (it returns a list[dict])
    mcp.prompt(name=name, description=desc)(prompt_function)

if __name__ == "__main__":
    mcp.run()
