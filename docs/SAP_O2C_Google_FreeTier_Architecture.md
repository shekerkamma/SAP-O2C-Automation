# SAP O2C Multi-Agent on Google Free Tier — Architecture & Setup Guide

## The Architecture (As-Is from the Repos)

The two GitHub repos define a complete architecture:

- **gutjahrai/sap-odata-mcp-server** — Node.js MCP server that converts SAP OData services into MCP tools (11 generic tools: connect, discover, query, CRUD, function calls)
- **FelipeLujan/SAP-O2C-Automation** — Google ADK multi-agent (Python) with 5 agents (1 coordinator + 4 specialists) that consume MCP tools via stdio transport

The agents use Gemini as the LLM, the MCP server talks OData to SAP, and `adk web` provides the dev UI on port 8080. That's the whole stack.

```
                         ┌──────────────────────────────────┐
                         │        adk web (port 8080)       │
                         │     Google ADK Dev UI (Python)    │
                         ├──────────────────────────────────┤
                         │     O2C Coordinator (root)       │
                         │  ┌────────┬─────────┬─────────┐ │
                         │  │Product │Inventory│Sales Ord│ │──→ Gemini API
                         │  │Speclist│Manager  │Manager  │ │    (Google AI Studio)
                         │  ├────────┴─────────┴─────────┤ │    gemini-2.5-flash
                         │  │  Delivery Specialist        │ │
                         │  └─────────────────────────────┘ │
                         │              │ stdio (MCP)       │
                         │  ┌───────────▼─────────────────┐ │
                         │  │ SAP OData MCP Server        │ │
                         │  │ (Node.js subprocess)        │ │
                         │  │ 11 generic OData tools      │ │
                         │  └───────────┬─────────────────┘ │
                         └──────────────┼──────────────────┘
                                        │ HTTPS / Basic Auth
                         ┌──────────────▼──────────────────┐
                         │    SAP BTP Trial (ABAP Cloud)    │
                         │    OData V2/V4 endpoints         │
                         │    P-user + password auth        │
                         └─────────────────────────────────┘
```

---

## Google Free-Tier Service Mapping

Every layer of this architecture runs on $0 Google services:

| Layer | Google Free Service | What It Replaces (from SOFIE) | Limits | Notes |
|-------|-------------------|-------------------------------|--------|-------|
| **LLM** | Gemini API via AI Studio | Claude via Azure AI Foundry | Flash: 10 RPM, 250 req/day | No credit card needed. Get key at aistudio.google.com/apikey |
| **Agent Framework** | Google ADK (open source) | Copilot Studio + Power Automate | Unlimited (runs locally) | pip install google-adk. Multi-agent, MCP-native |
| **Dev Environment** | Google Cloud Shell | Local dev machine | 5GB persistent storage | Free browser terminal with Node.js + Python pre-installed |
| **Dev UI** | `adk web` (built into ADK) | Teams channel | Port 8080 via Cloud Shell Web Preview | Agent selection dropdown, chat interface |
| **MCP Server Runtime** | Node.js subprocess (stdio) | Azure APIM + Custom Connectors | No limits (local process) | MCP server runs as child process of ADK agent |
| **SAP Backend** | SAP BTP Trial | TMNA S/4HANA | 90-day trial, nightly hibernation | ABAP Cloud — no pre-loaded data, must build RAP services or use Hub Sandbox |
| **Alternative: Hosted** | Cloud Run (always-free tier) | Azure App Service | 2M req/month, 360K GB-sec | For when you want to host the agent remotely |
| **Alternative: Web UI** | Firebase Hosting (Spark) | Teams bot framework | 10GB bandwidth/month | If you want a custom web chat frontend |
| **Alternative: Storage** | Firestore (Spark) | Dataverse | 1GB, 50K reads/day | For conversation history / session state |

### Gemini Free Tier Details (April 2026)

As of April 1, 2026, free tier is **Flash models only** (Pro requires billing):

| Model | RPM | Requests/Day | Tokens/Min | Context Window |
|-------|-----|-------------|------------|----------------|
| gemini-2.5-flash | 10 | 250 | 250,000 | 1M tokens |
| gemini-2.5-flash-lite | 15 | 1,000 | 250,000 | 1M tokens |

For a dev/POC SAP agent, 250 requests/day on Flash is plenty. Each O2C interaction is roughly 3-5 agent turns.

---

## How the OData-to-MCP Conversion Works

This is the core pattern from the YouTube video and the repos. The gutjahrai MCP server:

1. **Connects** to any SAP system via Basic Auth (or API Key for Hub Sandbox)
2. **Discovers** available OData services via the Gateway catalog (`/IWFND/CATALOGSERVICE`)
3. **Reads metadata** ($metadata) to learn entity sets, properties, keys, and navigation properties
4. **Exposes 11 generic MCP tools** that Gemini can call with any service/entity combination:

| MCP Tool | OData Operation | Example |
|----------|----------------|---------|
| `sap_connect` | Establish connection | Connect with base URL + credentials |
| `sap_get_services` | Catalog discovery | List all available OData services |
| `sap_get_service_metadata` | $metadata | Get entity types, properties for API_SALES_ORDER_SRV |
| `sap_query_entity_set` | GET with $filter/$select/$top | Query A_SalesOrder where SalesOrderType eq 'OR' |
| `sap_get_entity` | GET by key | Get SalesOrder('12345') |
| `sap_create_entity` | POST | Create new SalesOrder |
| `sap_update_entity` | PATCH/PUT | Update SalesOrder fields |
| `sap_delete_entity` | DELETE | Delete SalesOrder |
| `sap_call_function` | Function Import | PostGoodsIssue, ConfirmPicking |
| `sap_connection_status` | Health check | Verify connection is alive |
| `sap_disconnect` | Cleanup | Close connection |

The ADK agents don't need to know OData syntax. Gemini reads the tool schemas, understands the prompt context (e.g., "I'm the Sales Order specialist, use API_SALES_ORDER_SRV"), and constructs the right tool calls.

---

## What Needs Fixing in the Repos

### Fix 1: pyproject.toml — Remove GCP Billing Dependencies

The original requires `google-cloud-aiplatform[agent-engines]` which needs a GCP paid account.

**Remove:**
```toml
google-cloud-aiplatform = { extras = ["adk", "agent-engines"], version = "^1.93.0" }
```

**Replace with:**
```toml
[project.dependencies]
google-adk = ">=1.0.0"
google-genai = ">=1.16.1"
python-dotenv = ">=1.0.1"
```

Also change `[build-system]` from poetry to setuptools (simpler, no poetry needed).

### Fix 2: constants.py — Replace Hardcoded Path

Original has Felipe's Mac path:
```python
args=["/Users/felipe/Documents/coding/sap-odata-mcp/build/index.js"]
```

Replace with dynamic path resolution + env var passthrough:
```python
import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters

load_dotenv()

_project_root = Path(__file__).resolve().parent.parent
_mcp_path = os.getenv(
    "MCP_SERVER_PATH",
    str(_project_root.parent / "sap-odata-mcp-server" / "dist" / "index.js")
)

MCP_CONNECTION_PARAMS = StdioServerParameters(
    command="node",
    args=[_mcp_path],
    env={
        "SAP_ODATA_BASE_URL": os.getenv("SAP_ODATA_BASE_URL", ""),
        "SAP_USERNAME": os.getenv("SAP_USERNAME", ""),
        "SAP_PASSWORD": os.getenv("SAP_PASSWORD", ""),
        "SAP_VALIDATE_SSL": os.getenv("SAP_VALIDATE_SSL", "false"),
        "PATH": os.environ.get("PATH", ""),
    },
)
connection_params = MCP_CONNECTION_PARAMS
```

### Fix 3: Package Naming

The cloned folder `SAP-O2C-Automation` must be renamed to `OrderToCashTeam` because all Python imports reference `from OrderToCashTeam.xxx import yyy`.

```bash
mv SAP-O2C-Automation OrderToCashTeam
```

### Fix 4: Tool Filter Mismatch (CRITICAL)

The O2C agents filter for entity-specific tools like `getAllProducts`, `createSalesOrder`, `getAllMaterialStocks` — **64 tool names that don't exist in the MCP server**. The MCP server only exposes 11 generic tools.

**Two approaches:**

**Option A (Quick — remove filters):** Delete `tool_filter` from all 4 sub-agent definitions. Each agent gets all 11 generic tools. The agent prompts already describe which SAP services each specialist should use, so Gemini naturally calls the right service/entity.

**Option B (Better — extend MCP server):** Modify the MCP server to dynamically generate per-entity tools after connecting. After reading `$metadata`, register tools like `getAllProducts` → wraps `sap_query_entity_set(serviceName="API_PRODUCT_SRV", entitySet="A_Product")`. This is what the odata-mcp-proxy project (lemaiwo) does with its `MCP_TOOL_REGISTRY_TYPE=flat` mode. The O2C tool_filter names would then match.

For getting running fast, go with Option A.

### Fix 5: SAP Backend — BTP Trial Has No Pre-loaded Data

BTP Trial ABAP Cloud is a blank slate. It does NOT include:
- API_SALES_ORDER_SRV
- API_PRODUCT_SRV
- API_BUSINESS_PARTNER
- API_MATERIAL_STOCK_SRV
- Any other standard S/4HANA OData services

**Options to get data:**
1. **SAP Accelerator Hub Sandbox** (sandbox.api.sap.com) — Has pre-loaded data for all standard APIs. Uses API Key auth instead of Basic Auth. Needs a small patch to the MCP server's OData client to send `APIKey` header instead of Basic Auth credentials.
2. **Build RAP services in BTP Trial** — Create custom CDS views, expose as OData V4 via service binding. Full write-path support, but significant development effort.
3. **Hybrid** — Use Hub Sandbox for reads (demo/POC), BTP Trial for write-path testing once you build RAP services.

---

## Step-by-Step Setup (Google Cloud Shell)

### Prerequisites

- Google account (for Cloud Shell + AI Studio)
- SAP Universal ID (for BTP Trial — you already have P2011946209)
- Gemini API key from aistudio.google.com/apikey

### Step 1: Open Google Cloud Shell

Go to shell.cloud.google.com. This gives you a free VM with:
- 5GB persistent home directory
- Node.js 18+ pre-installed
- Python 3.11+ pre-installed
- Browser-based terminal

### Step 2: Clone Both Repos

```bash
# Clone the O2C agent
git clone https://github.com/FelipeLujan/SAP-O2C-Automation OrderToCashTeam
# Clone the MCP server
git clone https://github.com/gutjahrai/sap-odata-mcp-server
```

### Step 3: Build the MCP Server

```bash
cd ~/sap-odata-mcp-server
npm install
npm run build
cd ~
```

This creates `dist/index.js` — the compiled MCP server.

### Step 4: Fix the O2C Agent

```bash
cd ~/OrderToCashTeam

# Fix pyproject.toml (replace entire file)
cat > pyproject.toml << 'EOF'
[project]
name = "OrderToCashTeam"
version = "0.1.0"
description = "SAP O2C Multi-Agent on Google ADK"
requires-python = ">=3.11"
[project.dependencies]
google-adk = ">=1.0.0"
google-genai = ">=1.16.1"
python-dotenv = ">=1.0.1"
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
EOF

# Fix constants.py (dynamic path + env passthrough)
# [Apply the constants.py patch from Fix 2 above]

# Remove tool_filter from all 4 sub-agents
# [Edit each sub_agents/*/agent.py — remove tool_filter parameter]
```

### Step 5: Create .env

```bash
cat > .env << 'EOF'
GOOGLE_GENAI_API_KEY=your_gemini_key_here
SAP_ODATA_BASE_URL=https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/
SAP_USERNAME=
SAP_PASSWORD=
SAP_VALIDATE_SSL=false
MCP_SERVER_PATH=/home/your_user/sap-odata-mcp-server/dist/index.js
EOF
```

### Step 6: Install Python Deps

```bash
pip install google-adk google-genai python-dotenv --break-system-packages
```

### Step 7: Launch

```bash
cd ~  # Parent of OrderToCashTeam
adk web
```

Click "Web Preview" on port 8080 in Cloud Shell. Select "OrderToCashTeam" from the agent dropdown.

---

## SOFIE → Google Architecture Comparison

| SOFIE Component | Microsoft Service | Google Free Equivalent | Status |
|----------------|-------------------|----------------------|--------|
| LLM (Claude Opus/Sonnet) | Azure AI Foundry | Gemini 2.5 Flash (AI Studio) | FREE — 250 req/day |
| Orchestrator | Copilot Studio GenOrch | Google ADK root_agent | FREE — open source |
| Agent Flows (17 flows) | Power Automate | ADK sub_agents (4 specialists) | FREE — Python code |
| SAP Connector | Custom Connector + APIM | SAP OData MCP Server | FREE — Node.js |
| QueryBuilder Prompts | Power Automate expressions | Gemini tool-calling | FREE — prompt-driven |
| Adaptive Cards | Teams Adaptive Cards | adk web chat UI | FREE — built-in dev UI |
| Auth (JWT/SAML/Bearer) | Azure APIM + Entra ID | Basic Auth (BTP Trial) | Simplified for POC |
| Dynamic Math Aggregator | PA JavaScript Code action | Gemini native (or Python tool) | FREE |
| Knowledge Source | Azure AI Search + SharePoint | Not needed for O2C demo | — |
| Delivery Channel | Microsoft Teams | Cloud Shell Web Preview | FREE |

---

## Next Steps After POC

Once the basic O2C flow works on Cloud Shell with `adk web`:

1. **Add SAP Accelerator Hub API Key auth** — Patch the MCP server's OData client to support `APIKey` header for Hub Sandbox data
2. **Build RAP services on BTP Trial** — Create CDS views for SalesOrder, Product, etc. with demo data
3. **Deploy to Cloud Run** — Containerize the ADK agent + MCP server for a hosted endpoint (still free tier)
4. **Add Firebase web UI** — Build a custom chat frontend on Firebase Hosting (free Spark plan)
5. **Add R2R domain** — Create additional sub-agents for Record-to-Report (GL Accounts, Trial Balance, Ledgers) mirroring SOFIE's R2R connected agent
6. **Explore odata-mcp-proxy** — lemaiwo's config-driven approach to generate per-entity MCP tools from JSON config, eliminating the tool_filter mismatch entirely
