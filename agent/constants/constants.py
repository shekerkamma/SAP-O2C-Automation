import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.models import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import (
    StdioConnectionParams,
    StdioServerParameters,
)

load_dotenv()

_project_root = Path(__file__).resolve().parent.parent
_default_mcp_path = str(_project_root.parent / "sap-odata-mcp-server" / "dist" / "index.js")
_mcp_path = os.getenv("MCP_SERVER_PATH", _default_mcp_path)

# Connection parameters for SAP OData MCP server
MCP_CONNECTION_PARAMS = StdioConnectionParams(
    server_params=StdioServerParameters(
        command="node",
        args=[_mcp_path],
        env={
            "SAP_ODATA_BASE_URL": os.getenv("SAP_ODATA_BASE_URL", ""),
            "APIM_API_KEY": os.getenv("APIM_API_KEY", ""),
            "SAP_USERNAME": os.getenv("SAP_USERNAME", ""),
            "SAP_PASSWORD": os.getenv("SAP_PASSWORD", ""),
            "SAP_VALIDATE_SSL": os.getenv("SAP_VALIDATE_SSL", "true"),
            "PATH": os.environ.get("PATH", ""),
            "NODE_ENV": "production",
        },
    ),
    timeout=10.0,
)

# Maintain backward compatibility
connection_params = MCP_CONNECTION_PARAMS

# LLM model for all agents — change this one line to switch providers
# Options:
#   "gemini-2.0-flash"                          — 1,500 req/day free, native ADK
#   "gemini-2.5-flash"                          — 20 req/day free (too low), best quality
#   LiteLlm(model="groq/llama-3.3-70b-versatile") — 14,400 req/day free, weak tool calling
#   LiteLlm(model="anthropic/claude-sonnet-4-20250514") — paid, excellent quality
AGENT_MODEL = LiteLlm(model="anthropic/claude-haiku-4-5-20251001")