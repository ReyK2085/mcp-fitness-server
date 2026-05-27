# Unit Converter API + MCP (tools, resources, prompts)
# Uses FastAPI for HTTP routes and FastMCP to expose tools/resources/prompts over HTTP/SSE transports.
from fastapi import FastAPI, APIRouter
from fastmcp import FastMCP

from mcp_tools.converter_tools import router as converter_router
from mcp_resources.converter_resources import unit_reference, troubleshooting_guide
from mcp_prompts.converter_prompts import explain_conversion_prompt, api_usage_prompt

from utils.logging_utils import build_log_config
import platform
import datetime
import os
import time
from pathlib import Path
import uvicorn

PORT = 8003  # adjust as needed

# Set up your logging preferences 
# LOG_FILE = Path(r".\logs\mcp_log_streamable_http.log")(use forward slashes on mac/Linux too)
LOG_FILE = Path("logs/mcp_log_streamable_http.log")

LOG_CONFIG = build_log_config(
    LOG_FILE,
    logger_handlers={
        "uvicorn": ["rotating_file", "console"],
        "uvicorn.error": ["rotating_file", "console"],
        "uvicorn.access": ["rotating_file"],
    },
    root_level="INFO",
    logger_level="DEBUG",
)


# FastAPI app for plain HTTP
app = FastAPI(
    title="Unit Converter MCP Server",
    description="FastAPI endpoints auto-exposed as MCP tools via FastMCP, with resources and prompts.",
    version="1.2.1",
)
app.include_router(converter_router)

# System health router
system_router = APIRouter(prefix="", tags=["system"])
_started_at = time.time()


# @system_router.get("/health")
# def health():
#     return {
#         "status": "ok",
#         "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
#         "python": platform.python_version(),
#         "platform": platform.platform(),
#         "pid": os.getpid(),
#         "cwd": os.getcwd(),
#         "uptime_seconds": round(time.time() - _started_at, 2),
#     }


app.include_router(system_router)

# FastMCP server generated from FastAPI OpenAPI (tools) plus manual resources/prompts
mcp = FastMCP.from_fastapi(
    app,
    name="Unit Converter MCP Server",
    instructions="Unit conversion tools with supporting resources and prompts.",
)

# Resources
@mcp.resource("resource://unit_reference", name="Unit Converter Cheatsheet", mime_type="application/json")
def _resource_unit_reference():
    return unit_reference()


@mcp.resource("resource://troubleshooting_guide", name="Troubleshooting Guide", mime_type="text/plain")
def _resource_troubleshooting():
    return troubleshooting_guide()


# Prompts
@mcp.prompt(name="explain_conversion", description="Guide a learner through the math for a conversion.")
def _prompt_explain_conversion():
    return explain_conversion_prompt()


@mcp.prompt(name="api_usage", description="Produce a curl example for a conversion endpoint.")
def _prompt_api_usage():
    return api_usage_prompt()


# Build MCP sub-apps (need lifespan) and mount onto FastAPI
mcp_http_app = mcp.http_app(path="/", transport="streamable-http")
mcp_sse_app = mcp.http_app(path="/", transport="sse")
# Ensure FastAPI runs the MCP lifespan so streamable-http initializes properly
app.router.lifespan_context = mcp_http_app.lifespan

app.mount("/mcp", mcp_http_app)
app.mount("/sse", mcp_sse_app)


if __name__ == "__main__":
    import uvicorn

    PORT = 8003 # avoid conflicts/permissions on lower ports
    print("Starting the Unit Converter API server (HTTP + MCP tools/resources/prompts)...")
    print(f"HTTP docs:      http://localhost:{PORT}/docs")
    print(f"HTTP redoc:     http://localhost:{PORT}/redoc")
    print(f"MCP endpoint:   http://localhost:{PORT}/mcp (HTTP)")
    print(f"MCP endpoint:   http://localhost:{PORT}/sse (SSE)")

    uvicorn.run(
        app,
        host="localhost",
        port=PORT,
        log_level="trace",   # Uvicorn internal level
        log_config=LOG_CONFIG,
    )
