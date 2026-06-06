import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.models import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import (
    StdioConnectionParams,
    StdioServerParameters,
)

load_dotenv()

import litellm
litellm.num_retries = 5
litellm.request_timeout = 120

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
    timeout=30.0,
)

# Maintain backward compatibility
connection_params = MCP_CONNECTION_PARAMS

# Model is configurable via AGENT_MODEL in .env (see .env for provider examples)
AGENT_MODEL = LiteLlm(model=os.getenv("AGENT_MODEL", "gemini/gemini-2.5-flash"))