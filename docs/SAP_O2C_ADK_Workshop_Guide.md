# SAP Order-to-Cash Automation with Google ADK
## Workshop Guide — Full Stack: Gemini + ADK + BTP API Management + OData MCP Server

**Based on:**
- Video: *Automation Order to Cash in SAP with Google Gemini and Agent Development Kit ADK* — Felipe Lujan
- Repo 1: `github.com/gutjahrai/sap-odata-mcp-server` — OData → MCP bridge (Node.js)
- Repo 2: `github.com/FelipeLujan/SAP-O2C-Automation` — O2C multi-agent (Google ADK / Python)

**Cost to run this workshop: $0**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Free-Tier Service Map](#2-free-tier-service-map)
3. [How the Stack Works End-to-End](#3-how-the-stack-works-end-to-end)
4. [Prerequisites](#4-prerequisites)
5. [Phase 1 — BTP API Management Setup](#5-phase-1--btp-api-management-setup)
6. [Phase 2 — Google Cloud Shell Setup](#6-phase-2--google-cloud-shell-setup)
7. [Phase 3 — Clone and Fix the Repos](#7-phase-3--clone-and-fix-the-repos)
8. [Phase 4 — Configure the MCP Server for APIM](#8-phase-4--configure-the-mcp-server-for-apim)
9. [Phase 5 — Launch and Test (Mock Mode)](#9-phase-5--launch-and-test-mock-mode)
10. [Phase 6 — Switch to Real SAP Data (api.sap.com via APIM)](#10-phase-6--switch-to-real-sap-data-apisapcom-via-apim)
11. [Phase 7 — Real S/4HANA Connection](#11-phase-7--real-s4hana-connection)
12. [Security Controls Reference](#12-security-controls-reference)
13. [Repo Fixes Reference](#13-repo-fixes-reference)
14. [SOFIE vs Google Stack Comparison](#14-sofie-vs-google-stack-comparison)
15. [Gemini Rate Limits and Model Selection](#15-gemini-rate-limits-and-model-selection)
16. [Next Steps Beyond This Workshop](#16-next-steps-beyond-this-workshop)

---

## 1. Architecture Overview

### The Core Design Principle

**BTP API Management is the only component that ever touches SAP credentials or SAP endpoints.** The MCP server holds only a low-privilege APIM consumer key. ADK agents hold only a Gemini API key. Backend can be swapped (mock → api.sap.com → real S/4HANA) by changing one URL in APIM — zero code changes anywhere.

### Full Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                  Google Cloud Shell (Free)                      │
│                  shell.cloud.google.com                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              adk web  (port 8080)                        │  │
│  │          Google ADK Dev UI — browser chat                │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                O2C Coordinator Agent                     │  │──→ Gemini API
│  │  ┌─────────────┬──────────────┬──────────────────────┐  │  │    AI Studio
│  │  │  Product    │  Inventory   │  Sales Order         │  │  │    gemini-2.5-flash
│  │  │  Specialist │  Manager     │  Manager             │  │  │    (free, no billing)
│  │  ├─────────────┴──────────────┴──────────────────────┤  │  │
│  │  │            Delivery Specialist                     │  │  │
│  │  └───────────────────────┬────────────────────────────┘  │  │
│  │                          │ stdio transport (MCP)          │  │
│  │  ┌───────────────────────▼────────────────────────────┐  │  │
│  │  │         SAP OData MCP Server  (Node.js)            │  │  │
│  │  │         11 generic OData tools                     │  │  │
│  │  │         Auth: APIM_API_KEY only                    │  │  │
│  │  │         SAP_VALIDATE_SSL=true                      │  │  │
│  │  └───────────────────────┬────────────────────────────┘  │  │
│  └──────────────────────────┼───────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────┘
                              │ HTTPS + Consumer API Key
                              ▼
┌────────────────────────────────────────────────────────────────┐
│              SAP BTP Trial — Integration Suite                  │
│              API Management (free with BTP Trial)               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Proxy  /odata/sap/*                                 │  │
│  │                                                          │  │
│  │  Policies (order of execution):                         │  │
│  │   1. Verify-API-Key (consumer key from Developer Portal) │  │
│  │   2. Spike-Arrest  (10 calls/min — protects SAP + quota) │  │
│  │   3. Assign-Message: inject APIKey header from           │  │
│  │      Named Value [encrypted, never leaves APIM]          │  │
│  │   4. SSL-Enforcement (reject non-HTTPS)                  │  │
│  │   5. Analytics / Logging                                 │  │
│  └────────────────────────────┬─────────────────────────────┘  │
│                               │                                 │
│  ┌────────────────────────────▼─────────────────────────────┐  │
│  │  Target Endpoint  (one config change = full backend swap) │  │
│  │                                                          │  │
│  │  [MODE 1 — MOCK]   APIM Mock Service (built-in)          │  │
│  │  [MODE 2 — POC]    https://sandbox.api.sap.com/...       │  │
│  │  [MODE 3 — REAL]   https://your-s4.company.com/...       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
       APIM Mock         api.sap.com      Customer
       Service           Hub Sandbox      S/4HANA
       (no account)      (API Key in      (OAuth2 /
                         Named Value)     Basic Auth)
```

### Three Operational Modes

| Mode | Backend | What You Need | What Works |
|------|---------|---------------|------------|
| **Mock** | APIM built-in Mock | BTP Trial account only | Full agent logic, tool calls, end-to-end flow. No real SAP data. |
| **POC** | api.sap.com Hub Sandbox | + api.sap.com account + API key | Real S/4HANA demo data. Read-only (writes do not persist). |
| **Real** | Customer S/4HANA | + network access + SAP credentials | Live business data. Full read/write. |

**The MCP server and all ADK agent code are identical across all three modes.** Only the APIM target endpoint and Named Value change.

---

## 2. Free-Tier Service Map

Every component in this workshop costs $0.

| Layer | Google/SAP Free Service | Limits | Notes |
|-------|------------------------|--------|-------|
| **LLM** | Gemini API via AI Studio | 10 RPM, 250 req/day (Flash) | No credit card. Key at aistudio.google.com/apikey |
| **Agent Framework** | Google ADK (open source) | Unlimited (runs locally) | `pip install google-adk`. MCP-native, multi-agent built in. |
| **Dev Environment** | Google Cloud Shell | 5GB persistent, 50hr/week | Free browser VM. Node.js 18+ and Python 3.11+ pre-installed. |
| **Dev UI** | `adk web` (built into ADK) | Port 8080, Cloud Shell preview | Agent dropdown, chat interface, tool call traces. |
| **MCP Transport** | stdio (local subprocess) | No limits | MCP server is a child process — no open port, no network exposure. |
| **SAP Gateway** | BTP Trial — API Management | Included in BTP Trial (90 days) | Policies, mock service, developer portal, analytics — all included. |
| **SAP Mock Data** | APIM Mock Service | Unlimited | Mock responses defined inline — no SAP system needed at all. |
| **SAP Real Demo Data** | api.sap.com Hub Sandbox | Rate-limited, read-only | Pre-loaded S/4HANA data. Requires free api.sap.com account. |
| **Future: Hosting** | Cloud Run (always-free) | 2M req/month, 360K GB-sec | If you want to host the agent stack remotely. |
| **Future: Web UI** | Firebase Hosting (Spark) | 10GB bandwidth/month | Custom chat frontend beyond `adk web`. |
| **Future: Session State** | Firestore (Spark) | 1GB, 50K reads/day | Conversation history persistence. |

---

## 3. How the Stack Works End-to-End

### Component Roles

**Google ADK** is the agent framework. It manages the multi-agent team: one root coordinator and four specialist sub-agents. ADK handles agent routing, tool call dispatch, and conversation state. `adk web` is its built-in development UI — a browser-based chat that shows the full agent turn sequence and tool calls.

**Gemini API** is the LLM. Each agent turn sends the conversation context + available MCP tool schemas to Gemini. Gemini decides which tool to call with which parameters. The result comes back as JSON and is fed into the next turn.

**SAP OData MCP Server** is a Node.js process that runs as a subprocess of the ADK agent framework (stdio transport). It exposes 11 generic tools that map to OData operations. It does not know about SAP business concepts — it is purely an HTTP client that speaks OData. It connects to BTP APIM, not directly to SAP.

**BTP API Management** is the secure gateway. It owns all SAP credentials (stored as encrypted Named Values). It enforces auth, rate limits, and SSL. It routes requests to whichever backend is currently configured (mock, api.sap.com, or real SAP). This is the component that makes backend-switching a config operation rather than a code operation.

### A Single Agent Turn (e.g., "Show me open sales orders")

```
1. User types in adk web chat
2. ADK routes message to O2C Coordinator
3. Coordinator sends message + tool schemas to Gemini
4. Gemini returns: call sap_query_entity_set with
      serviceName="API_SALES_ORDER_SRV"
      entitySet="A_SalesOrder"
      filter="OverallSDProcessStatus eq 'A'"
5. ADK calls MCP server tool via stdio
6. MCP server sends:
      GET https://<apim-host>/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder
          ?$filter=OverallSDProcessStatus eq 'A'
          Header: x-apim-key: <consumer_key>
7. APIM verifies consumer key
8. APIM injects APIKey header from Named Value
9. APIM forwards to backend (mock / api.sap.com / real SAP)
10. OData JSON response returns through APIM → MCP server → ADK → Gemini
11. Gemini formats a natural language response
12. User sees result in adk web chat
```

### The 11 MCP Tools (OData Operations)

| Tool | OData | Typical Agent Use |
|------|-------|-------------------|
| `sap_connect` | Establish session | Called once on startup |
| `sap_get_services` | GET catalog | Discover available OData services |
| `sap_get_service_metadata` | GET $metadata | Learn entity types and properties |
| `sap_query_entity_set` | GET with $filter/$select/$top | "List all open sales orders" |
| `sap_get_entity` | GET by key | "Get sales order 12345" |
| `sap_create_entity` | POST | "Create a new sales order" |
| `sap_update_entity` | PATCH/PUT | "Update delivery status to shipped" |
| `sap_delete_entity` | DELETE | "Delete draft sales order" |
| `sap_call_function` | Function Import | PostGoodsIssue, ConfirmPicking |
| `sap_connection_status` | Health check | Verify connection is alive |
| `sap_disconnect` | Cleanup | Close session |

### The 5 ADK Agents

| Agent | Role | SAP Services It Uses |
|-------|------|----------------------|
| O2C Coordinator | Root agent. Routes user requests to the right specialist. Aggregates responses. | None directly |
| Product Specialist | Looks up product catalogue, prices, descriptions | API_PRODUCT_SRV |
| Inventory Manager | Checks stock levels, availability, warehouse locations | API_MATERIAL_STOCK_SRV |
| Sales Order Manager | Creates, reads, updates sales orders | API_SALES_ORDER_SRV |
| Delivery Specialist | Tracks delivery status, confirms picking, posts goods issue | API_OUTBOUND_DELIVERY_SRV |

---

## 4. Prerequisites

Complete all of these before starting Phase 1.

### 4.1 Accounts Required

| Account | URL | Cost | Purpose |
|---------|-----|------|---------|
| Google Account | accounts.google.com | Free | Cloud Shell + AI Studio |
| SAP Universal ID | account.sap.com | Free | BTP Trial access |
| api.sap.com account | api.sap.com | Free | Hub Sandbox (Phase 6 only) |

### 4.2 Keys to Collect Before Starting

**Gemini API Key** (needed for Phase 2)
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Copy and save securely — you will need it in Phase 2 Step 2 (`.env` file)

**api.sap.com Application Key** (needed for Phase 6 only — skip for now)
1. Go to [api.sap.com](https://api.sap.com) and sign in with SAP Universal ID
2. Go to **Settings → Application Keys**
3. Click **Add Application Key**
4. Copy the key — you will add it to APIM Named Values in Phase 6

### 4.3 Software Verified Present in Cloud Shell

You do not need to install anything locally. Google Cloud Shell provides:
- Node.js 18+ (`node --version`)
- Python 3.11+ (`python3 --version`)
- npm (`npm --version`)
- git (`git --version`)

---

## 5. Phase 1 — BTP API Management Setup

**Goal:** Create a BTP APIM proxy with Mock Service as the backend, and generate a consumer API key for the MCP server.

### 5.1 Provision BTP Trial with Integration Suite

1. Go to [account.hanatrial.ondemand.com](https://account.hanatrial.ondemand.com)
2. Sign in with your SAP Universal ID
3. In the **Trial Global Account**, open your **Subaccount** (usually named `trial`)
4. Go to **Service Marketplace** → search for **Integration Suite**
5. Click **Integration Suite** → **Create** → select plan **trial**
6. Wait for provisioning (~5 minutes)
7. Go to **Instances and Subscriptions** → click the Integration Suite URL to open it
8. Click **Add Capabilities** and enable **API Management**
9. Click **Configure API Management** — accept defaults for the virtual host

> Note: Integration Suite trial is included in the BTP trial entitlement. No credit card required.

### 5.2 Open API Management

From Integration Suite home page, click **API Management** → **Design, Develop, and Manage APIs**.

You will land on the APIM portal. The URL will look like:
```
https://<tenant>.prod.apimanagement.<region>.hana.ondemand.com/apiportal
```
Save this tenant hostname — you will use it as `SAP_ODATA_BASE_URL` in the MCP server `.env`.

### 5.3 Create the API Proxy

1. In APIM Portal → **Develop** → **APIs** → **Create**
2. Select **Create from Scratch**
3. Fill in:
   - **Name:** `SAP-O2C-Proxy`
   - **Title:** `SAP O2C OData Gateway`
   - **Base Path:** `/odata/sap`
   - **Backend URL:** Leave empty for now — we will set the mock target in Step 5.4
4. Click **Create**

### 5.4 Configure Mock Service as Target (Mode 1)

1. In the proxy → **Target Endpoint** tab
2. Click **Edit**
3. Under **Target**, select **Mock Target**
4. Click **Add Mock Response**:

Add these responses (minimum set to make agents work):

| HTTP Method | URL Pattern | Status | Response Body |
|-------------|-------------|--------|---------------|
| GET | `/API_SALES_ORDER_SRV/A_SalesOrder` | 200 | See JSON below |
| GET | `/API_SALES_ORDER_SRV/A_SalesOrder('10')` | 200 | Single order JSON |
| GET | `/API_PRODUCT_SRV/A_Product` | 200 | Products list JSON |
| GET | `/API_MATERIAL_STOCK_SRV/A_MatlStkInAcctMod` | 200 | Stock levels JSON |
| GET | `/API_OUTBOUND_DELIVERY_SRV/A_OutbDeliveryHeader` | 200 | Deliveries JSON |
| POST | `/API_SALES_ORDER_SRV/A_SalesOrder` | 201 | Created order JSON |

**Mock response for GET /API_SALES_ORDER_SRV/A_SalesOrder:**
```json
{
  "d": {
    "results": [
      {
        "SalesOrder": "10",
        "SalesOrderType": "OR",
        "SoldToParty": "CUST-001",
        "TotalNetAmount": "5000.00",
        "TransactionCurrency": "USD",
        "OverallSDProcessStatus": "A",
        "RequestedDeliveryDate": "/Date(1775000000000)/",
        "CreationDate": "/Date(1774000000000)/"
      },
      {
        "SalesOrder": "11",
        "SalesOrderType": "OR",
        "SoldToParty": "CUST-002",
        "TotalNetAmount": "12500.00",
        "TransactionCurrency": "USD",
        "OverallSDProcessStatus": "A",
        "RequestedDeliveryDate": "/Date(1776000000000)/",
        "CreationDate": "/Date(1774100000000)/"
      },
      {
        "SalesOrder": "12",
        "SalesOrderType": "OR",
        "SoldToParty": "CUST-003",
        "TotalNetAmount": "3200.00",
        "TransactionCurrency": "USD",
        "OverallSDProcessStatus": "B",
        "RequestedDeliveryDate": "/Date(1774500000000)/",
        "CreationDate": "/Date(1773900000000)/"
      }
    ]
  }
}
```

**Mock response for GET /API_PRODUCT_SRV/A_Product:**
```json
{
  "d": {
    "results": [
      {
        "Product": "LAPTOP-01",
        "ProductType": "FERT",
        "BaseUnit": "EA",
        "GrossWeight": "2.500",
        "WeightUnit": "KG",
        "ProductGroup": "ELECTRONICS"
      },
      {
        "Product": "MONITOR-24",
        "ProductType": "FERT",
        "BaseUnit": "EA",
        "GrossWeight": "4.200",
        "WeightUnit": "KG",
        "ProductGroup": "ELECTRONICS"
      },
      {
        "Product": "KEYBOARD-US",
        "ProductType": "FERT",
        "BaseUnit": "EA",
        "GrossWeight": "0.800",
        "WeightUnit": "KG",
        "ProductGroup": "ACCESSORIES"
      }
    ]
  }
}
```

**Mock response for GET /API_MATERIAL_STOCK_SRV/A_MatlStkInAcctMod:**
```json
{
  "d": {
    "results": [
      {
        "Material": "LAPTOP-01",
        "Plant": "1000",
        "StorageLocation": "0001",
        "MatlWrhsStkQtyInMatlBaseUnit": "45.000",
        "MaterialBaseUnit": "EA"
      },
      {
        "Material": "MONITOR-24",
        "Plant": "1000",
        "StorageLocation": "0001",
        "MatlWrhsStkQtyInMatlBaseUnit": "22.000",
        "MaterialBaseUnit": "EA"
      },
      {
        "Material": "KEYBOARD-US",
        "Plant": "1000",
        "StorageLocation": "0001",
        "MatlWrhsStkQtyInMatlBaseUnit": "150.000",
        "MaterialBaseUnit": "EA"
      }
    ]
  }
}
```

**Mock response for GET /API_OUTBOUND_DELIVERY_SRV/A_OutbDeliveryHeader:**
```json
{
  "d": {
    "results": [
      {
        "DeliveryDocument": "80000010",
        "DeliveryDocumentType": "LF",
        "ShippingPoint": "SP01",
        "DeliveryDate": "/Date(1775100000000)/",
        "OverallGoodsMovementStatus": "A",
        "SoldToParty": "CUST-001"
      },
      {
        "DeliveryDocument": "80000011",
        "DeliveryDocumentType": "LF",
        "ShippingPoint": "SP01",
        "DeliveryDate": "/Date(1775200000000)/",
        "OverallGoodsMovementStatus": "C",
        "SoldToParty": "CUST-002"
      }
    ]
  }
}
```

5. Click **Save**

### 5.5 Add Policies to the Proxy

In the proxy → **Policies** tab → click **Edit** → switch to **Code** view.

Replace the policy XML with:

```xml
<Policies>
  <PreFlow>
    <!-- 1. Verify the consumer API key from the MCP server -->
    <Step>
      <Name>verify-api-key</Name>
    </Step>
    <!-- 2. Rate limit: protect SAP and stay within free quotas -->
    <Step>
      <Name>spike-arrest</Name>
    </Step>
    <!-- 3. Enforce HTTPS -->
    <Step>
      <Name>ssl-enforcement</Name>
    </Step>
    <!-- 4. Inject SAP backend credentials (from encrypted Named Value) -->
    <Step>
      <Name>set-sap-credentials</Name>
    </Step>
  </PreFlow>
</Policies>
```

Create each referenced policy:

**verify-api-key** (Verify API Key policy):
```xml
<VerifyAPIKey name="verify-api-key">
  <APIKey ref="request.header.x-apim-key"/>
</VerifyAPIKey>
```

**spike-arrest** (Spike Arrest policy):
```xml
<SpikeArrest name="spike-arrest">
  <Rate>10pm</Rate>
  <UseEffectiveCount>true</UseEffectiveCount>
</SpikeArrest>
```

**ssl-enforcement** (assign condition that rejects HTTP):
```xml
<RaiseFault name="ssl-enforcement">
  <Condition>request.verb != "HTTPS"</Condition>
  <FaultResponse>
    <Set>
      <StatusCode>403</StatusCode>
      <ReasonPhrase>HTTPS Required</ReasonPhrase>
    </Set>
  </FaultResponse>
</RaiseFault>
```

**set-sap-credentials** (Assign Message — injects API key for backend):
```xml
<!-- For Mode 1 (Mock): this policy does nothing visible but stays in place -->
<!-- For Mode 2 (api.sap.com): injects the APIKey header from Named Value -->
<!-- For Mode 3 (Real SAP): change to inject Authorization: Basic or Bearer token -->
<AssignMessage name="set-sap-credentials">
  <AssignTo createNew="false" type="request"/>
  <Set>
    <Headers>
      <Header name="APIKey">{named.value.sap_backend_key}</Header>
    </Headers>
  </Set>
  <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</AssignMessage>
```

> `IgnoreUnresolvedVariables=true` means Mode 1 (Mock) will not fail even though `sap_backend_key` is not yet set. Set it to `false` when you configure Mode 2.

Click **Save** → **Deploy**.

### 5.6 Create Named Value for SAP Backend Key (Encrypted)

In APIM Portal → **Configure** → **Named Values** → **Create**:

| Field | Value |
|-------|-------|
| Name | `sap_backend_key` |
| Value | (leave empty for Mode 1; add api.sap.com key in Phase 6) |
| Is Encrypted | YES |

Click **Save**. This is where the api.sap.com API key (and later, any SAP credential) will live. It is stored encrypted and never returned in API responses or logs.

### 5.7 Generate Consumer API Key for the MCP Server

1. APIM Portal → **Developer Portal** (link at top right)
2. Go to **My Apps** → **Create Application**
3. Fill in:
   - **Name:** `o2c-mcp-server`
   - **Description:** SAP O2C MCP server consumer
4. Click **Add API** → select `SAP-O2C-Proxy`
5. Click **Save**
6. Your application now shows a **Consumer Key** (sometimes called API Key)
7. Copy this key — this goes in the MCP server `.env` as `APIM_API_KEY`

> This consumer key is the **only credential that ever leaves BTP**. It grants access only to this APIM proxy. If compromised, rotate it in the Developer Portal without touching any SAP credential.

### 5.8 Note Your APIM Proxy URL

Your proxy virtual host URL will be in the format:
```
https://<tenant>.prod.apimanagement.<region>.hana.ondemand.com
```

The full OData base URL for the MCP server is:
```
https://<tenant>.prod.apimanagement.<region>.hana.ondemand.com/odata/sap/
```

Save this — it becomes `SAP_ODATA_BASE_URL` in the `.env`.

---

## 6. Phase 2 — Google Cloud Shell Setup

### 6.1 Open Cloud Shell

Go to [shell.cloud.google.com](https://shell.cloud.google.com). Sign in with your Google account.

You get a free persistent Linux VM with:
- 5GB home directory (persists between sessions)
- Node.js 18+ and Python 3.11+ pre-installed
- Browser terminal + code editor

> Cloud Shell idles after 20 minutes of inactivity. Use `tmux` to keep processes running. We will set this up in Phase 5.

### 6.2 Verify Environment

```bash
node --version    # should be v18 or higher
python3 --version # should be 3.11 or higher
npm --version
git --version
```

### 6.3 Create a Python Virtual Environment

Do not use `--break-system-packages`. A virtualenv keeps your Cloud Shell Python clean.

```bash
python3 -m venv ~/.venv/o2c
source ~/.venv/o2c/bin/activate

# Make it activate automatically on reconnect
echo 'source ~/.venv/o2c/bin/activate' >> ~/.bashrc
```

### 6.4 Install Python Dependencies

```bash
pip install google-adk google-genai python-dotenv
```

Verify:
```bash
adk --version
python -c "from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters; print('ADK MCP import OK')"
```

---

## 7. Phase 3 — Clone and Fix the Repos

### 7.1 Clone Both Repos

```bash
cd ~
git clone https://github.com/FelipeLujan/SAP-O2C-Automation OrderToCashTeam
git clone https://github.com/gutjahrai/sap-odata-mcp-server
```

> The O2C repo is cloned directly as `OrderToCashTeam` because all Python imports in the code reference `from OrderToCashTeam.xxx import yyy`. The folder name must match.

### 7.2 Build the MCP Server

```bash
cd ~/sap-odata-mcp-server
npm install
npm run build
```

Verify the build output exists:
```bash
ls dist/index.js   # must exist
```

Smoke-test the MCP server starts correctly (Ctrl+C to stop):
```bash
node dist/index.js
# Should print startup message on stderr — no errors
```

```bash
cd ~
```

### 7.3 Fix 1 — Replace pyproject.toml (Remove GCP Billing Dependency)

The original repo requires `google-cloud-aiplatform[agent-engines]` which requires a paid GCP account and Vertex AI billing enabled. Replace the entire file:

```bash
cd ~/OrderToCashTeam

cat > pyproject.toml << 'EOF'
[project]
name = "OrderToCashTeam"
version = "0.1.0"
description = "SAP O2C Multi-Agent on Google ADK — Free Tier"
requires-python = ">=3.11"
dependencies = [
    "google-adk>=1.0.0",
    "google-genai>=1.16.1",
    "python-dotenv>=1.0.1",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
EOF
```

### 7.4 Fix 2 — Replace constants.py (Remove Hardcoded Mac Path)

The original file has Felipe's Mac filesystem path hardcoded:
```python
args=["/Users/felipe/Documents/coding/sap-odata-mcp/build/index.js"]
```

Replace the entire `constants.py` (find it in the package root or `OrderToCashTeam/` subdirectory):

```bash
# Find constants.py
find ~/OrderToCashTeam -name "constants.py"
```

Replace its contents:

```bash
cat > $(find ~/OrderToCashTeam -name "constants.py") << 'EOF'
import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

load_dotenv()

# Resolve MCP server path: env var takes priority, then default relative to project
_project_root = Path(__file__).resolve().parent.parent
_default_mcp_path = str(_project_root.parent / "sap-odata-mcp-server" / "dist" / "index.js")
_mcp_path = os.getenv("MCP_SERVER_PATH", _default_mcp_path)

MCP_CONNECTION_PARAMS = StdioServerParameters(
    command="node",
    args=[_mcp_path],
    env={
        "SAP_ODATA_BASE_URL": os.getenv("SAP_ODATA_BASE_URL", ""),
        "APIM_API_KEY": os.getenv("APIM_API_KEY", ""),
        # SAP_USERNAME and SAP_PASSWORD are empty in APIM mode
        # The MCP server will include APIM_API_KEY as x-apim-key header
        "SAP_USERNAME": os.getenv("SAP_USERNAME", ""),
        "SAP_PASSWORD": os.getenv("SAP_PASSWORD", ""),
        "SAP_VALIDATE_SSL": os.getenv("SAP_VALIDATE_SSL", "true"),
        "PATH": os.environ.get("PATH", ""),
        "NODE_ENV": "production",
    },
)

# Alias used by some agent files
connection_params = MCP_CONNECTION_PARAMS
EOF
```

### 7.5 Fix 3 — Verify Model Names

The agents must use `gemini-2.5-flash` (the free tier model). Check all agent files:

```bash
grep -r "model" ~/OrderToCashTeam --include="*.py" | grep -v ".pyc"
```

Any agent using `gemini-pro`, `gemini-1.5-pro`, or `claude` will fail hit billing. fix occurrences:

```bash
# Replace any non-free model references
find ~/OrderToCashTeam -name "agent.py" -exec \
  sed -i 's/model="gemini-pro"/model="gemini-2.5-flash"/g' {} \;
find ~/OrderToCashTeam -name "agent.py" -exec \
  sed -i 's/model="gemini-1.5-pro"/model="gemini-2.5-flash"/g' {} \;
find ~/OrderToCashTeam -name "agent.py" -exec \
  sed -i 's/model="gemini-1.5-flash"/model="gemini-2.5-flash"/g' {} \;
```

### 7.6 Fix 4 — Remove tool_filter from Sub-Agents (Critical)

The sub-agents filter for 64 entity-specific tool names (`getAllProducts`, `createSalesOrder`, etc.) that **do not exist** in the MCP server. The MCP server has 11 generic tools. The filter causes every tool lookup to return empty — agents will have no tools and fail silently.

Remove `tool_filter=` from all four sub-agent definitions:

```bash
# View sub-agent files
find ~/OrderToCashTeam -name "agent.py" | head -20

# Remove tool_filter parameter from all sub-agent definitions
find ~/OrderToCashTeam -name "agent.py" -exec \
  sed -i '/tool_filter=/d' {} \;

# Verify removal
grep -r "tool_filter" ~/OrderToCashTeam --include="*.py"
# Should return no output
```

> **Why this works:** The agent system prompts already describe which SAP service each specialist uses (e.g., "You are the Sales Order specialist. Use API_SALES_ORDER_SRV and entity set A_SalesOrder."). Gemini reads those instructions and constructs correct `sap_query_entity_set` calls naturally — no entity-specific tool names are needed.

---

## 8. Phase 4 — Configure the MCP Server for APIM

### 8.1 Patch the MCP Server to Send APIM Consumer Key

The MCP server uses Basic Auth by default. We need it to send the APIM consumer key as an `x-apim-key` header instead. This is a small patch to the MCP server's HTTP client.

Find the HTTP client file:

```bash
find ~/sap-odata-mcp-server/src -name "*.ts" | xargs grep -l "axios\|fetch\|https\|Authorization" 2>/dev/null
```

Open the OData client file (typically `src/odata-client.ts` or `src/client.ts`) and apply this patch:

```bash
# View the current HTTP client setup
cat ~/sap-odata-mcp-server/src/odata-client.ts   # adjust filename if different
```

Locate the section where request headers are built (look for `Authorization` or `headers`) and replace:

```typescript
// BEFORE (Basic Auth only):
const headers = {
  'Authorization': 'Basic ' + Buffer.from(`${username}:${password}`).toString('base64'),
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};

// AFTER (APIM consumer key mode — falls back to Basic Auth if no APIM key):
const apimKey = process.env.APIM_API_KEY;
const username = process.env.SAP_USERNAME;
const password = process.env.SAP_PASSWORD;

const headers: Record<string, string> = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};

if (apimKey) {
  // APIM gateway mode: send consumer key, APIM handles backend auth
  headers['x-apim-key'] = apimKey;
} else if (username && password) {
  // Direct SAP mode: Basic Auth (only for non-APIM setups)
  headers['Authorization'] = 'Basic ' +
    Buffer.from(`${username}:${password}`).toString('base64');
}
```

Rebuild after the patch:

```bash
cd ~/sap-odata-mcp-server
npm run build
cd ~
```

### 8.2 Create the .env File

```bash
cd ~/OrderToCashTeam

cat > .env << 'EOF'
# Gemini (Google AI Studio — no billing required)
GOOGLE_GENAI_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE

# BTP API Management — the ONLY SAP-facing credential stored here
# This is the consumer key from the APIM Developer Portal (Step 5.7)
APIM_API_KEY=PASTE_YOUR_APIM_CONSUMER_KEY_HERE

# APIM proxy base URL (from Step 5.8)
SAP_ODATA_BASE_URL=https://PASTE_YOUR_TENANT.prod.apimanagement.REGION.hana.ondemand.com/odata/sap/

# SAP credentials are empty in APIM mode — APIM owns these
SAP_USERNAME=
SAP_PASSWORD=

# Always true — APIM has a valid TLS certificate
SAP_VALIDATE_SSL=true

# MCP server path (auto-resolved if blank; set explicitly if needed)
MCP_SERVER_PATH=/home/YOUR_CLOUD_SHELL_USERNAME/sap-odata-mcp-server/dist/index.js
EOF
```

Replace the placeholder values:
- `PASTE_YOUR_GEMINI_API_KEY_HERE` — from aistudio.google.com/apikey
- `PASTE_YOUR_APIM_CONSUMER_KEY_HERE` — from APIM Developer Portal Step 5.7
- `PASTE_YOUR_TENANT.prod.apimanagement.REGION` — from Step 5.8
- `YOUR_CLOUD_SHELL_USERNAME` — run `echo $USER` to find yours

Secure the file immediately:

```bash
chmod 600 .env
echo ".env" >> ~/.gitignore
echo ".env.*" >> ~/.gitignore
```

### 8.3 Verify the .env Values Are Correct

```bash
# Quick sanity check — should show your values (not blanks for the key ones)
grep -E "GOOGLE_GENAI_API_KEY|APIM_API_KEY|SAP_ODATA_BASE_URL" .env
```

---

## 9. Phase 5 — Launch and Test (Mock Mode)

### 9.1 Set Up tmux (Keeps adk web Running Through Cloud Shell Reconnects)

```bash
sudo apt-get install -y tmux 2>/dev/null || true  # already installed on most Cloud Shell instances

# Create a named session
tmux new-session -s o2c
```

Inside the tmux session, run all workshop commands. To detach: `Ctrl+B then D`. To reattach after a Cloud Shell reconnect: `tmux attach -t o2c`.

### 9.2 Launch adk web

```bash
# Must be run from the PARENT directory of OrderToCashTeam
# ADK discovers agents by finding Python packages in subdirectories
cd ~
source ~/.venv/o2c/bin/activate
adk web
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 9.3 Open the Browser UI

In Cloud Shell, click the **Web Preview** button (top right) → **Preview on port 8080**.

Your browser opens the ADK web UI. In the **Agent** dropdown, select **OrderToCashTeam**.

### 9.4 Test Queries for Mock Mode

Try these in order. Each tests a different specialist agent:

**Test 1 — Coordinator routing:**
```
What can you help me with in Order to Cash?
```
Expected: Coordinator lists capabilities and sub-agents.

**Test 2 — Sales Order Manager:**
```
Show me all open sales orders
```
Expected: Agent calls `sap_query_entity_set` → APIM Mock returns 3 orders → Gemini formats them in a table.

**Test 3 — Product Specialist:**
```
List all products in the catalogue
```
Expected: 3 products returned from mock (LAPTOP-01, MONITOR-24, KEYBOARD-US).

**Test 4 — Inventory Manager:**
```
What is the current stock level for LAPTOP-01?
```
Expected: 45 units in plant 1000, storage location 0001.

**Test 5 — Delivery Specialist:**
```
Show me all pending deliveries
```
Expected: 2 deliveries — one open (status A), one completed (status C).

**Test 6 — Cross-agent O2C flow:**
```
I need to process order 10 for customer CUST-001. 
Check if we have stock for the products on the order, 
then confirm the delivery status.
```
Expected: Coordinator routes to Sales Order Manager → Inventory Manager → Delivery Specialist in sequence. Multiple tool calls visible in the ADK trace panel.

### 9.5 Reading the ADK Trace Panel

In the adk web UI, each agent turn shows:
- Which agent handled the request
- Which MCP tools were called
- The exact OData URL that was sent to APIM
- The raw JSON response from APIM
- Gemini's reasoning and formatted output

This is your debugging surface. If a tool call fails, the error is visible here.

---

## 10. Phase 6 — Switch to Real SAP Data (api.sap.com via APIM)

**Goal:** One change in APIM — route to api.sap.com instead of the mock. Zero code changes.

### 10.1 Get Your api.sap.com API Key

If you haven't already:
1. Go to [api.sap.com](https://api.sap.com) and sign in
2. Go to **Settings → Application Keys**
3. Click **Add Application Key** → name it `o2c-workshop`
4. Copy the key

### 10.2 Store the Key in APIM Named Value

In BTP APIM Portal → **Configure** → **Named Values** → Find `sap_backend_key` → **Edit**:
- Set **Value** to your api.sap.com application key
- Ensure **Is Encrypted** is checked
- Click **Save**

> This key never leaves BTP. The MCP server, Cloud Shell, and your laptop never see it.

Update the `set-sap-credentials` policy to stop ignoring unresolved variables:
```xml
<AssignMessage name="set-sap-credentials">
  <IgnoreUnresolvedVariables>false</IgnoreUnresolvedVariables>
  ...
</AssignMessage>
```

### 10.3 Change APIM Target to api.sap.com

In the `SAP-O2C-Proxy` → **Target Endpoint** → **Edit**:
- Change **Target** from Mock Service to **HTTP Target**
- Set **Target URL:** `https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap`
- Click **Save** → **Deploy**

That is the only change. No restarts, no code edits.

### 10.4 Verify the Switch

In the APIM portal → **Analyze** → **API Analytics** — you should see incoming requests from the MCP server, then outgoing requests to api.sap.com after the mode switch.

Run the same test queries from Phase 5. You will now get real S/4HANA demo data. Note:
- api.sap.com Hub Sandbox is **read-only** — POST requests return 200/201 but data is not persisted
- Rate limits apply — the Spike Arrest policy (10 calls/min) protects you from exhausting them

### 10.5 api.sap.com Key APIs Available

| SAP OData Service | api.sap.com Path | Agent |
|-------------------|-----------------|-------|
| API_SALES_ORDER_SRV | `/API_SALES_ORDER_SRV` | Sales Order Manager |
| API_PRODUCT_SRV | `/API_PRODUCT_SRV` | Product Specialist |
| API_MATERIAL_STOCK_SRV | `/API_MATERIAL_STOCK_SRV` | Inventory Manager |
| API_OUTBOUND_DELIVERY_SRV | `/API_OUTBOUND_DELIVERY_SRV` | Delivery Specialist |
| API_BUSINESS_PARTNER | `/API_BUSINESS_PARTNER` | (future: Customer agent) |

---

## 11. Phase 7 — Real S/4HANA Connection

**Zero agent code changes required.** Change only APIM target endpoint and Named Value.

### 11.1 Determine Your SAP Connectivity Pattern

| SAP System Type | Network Path | Auth Method |
|-----------------|-------------|-------------|
| S/4HANA On-Premise | BTP Cloud Connector (agent installed in corporate network) | Basic Auth or OAuth2 SAML Bearer |
| S/4HANA Private Cloud | BTP Cloud Connector or Private Link | Basic Auth or OAuth2 |
| S/4HANA Public Cloud | Direct HTTPS from APIM | OAuth2 (Communication Arrangement) |
| S/4HANA via Integration Suite | Direct HTTPS to IS endpoint | OAuth2 client credentials |

### 11.2 For On-Premise: Configure Cloud Connector

Cloud Connector is a Java agent installed inside the corporate network. It creates an outbound-only TLS tunnel to BTP — no inbound firewall changes needed.

1. Download Cloud Connector from [tools.hana.ondemand.com](https://tools.hana.ondemand.com)
2. Install on a server that can reach your S/4HANA system
3. Configure: BTP subaccount → Add your on-prem S/4HANA as an accessible system
4. In APIM, set the target to the Cloud Connector virtual host

### 11.3 Update APIM for the Real System

In `SAP-O2C-Proxy` → **Target Endpoint** → **Edit**:
- **For on-premise via Cloud Connector:** `https://virtualhost.cc/sap/opu/odata/sap`
- **For S/4HANA Cloud Public:** `https://<tenant>.s4hana.ondemand.com/sap/opu/odata/sap`

Update `sap_backend_key` Named Value with the real system credentials (Basic Auth base64 string or OAuth2 token, depending on system type).

Update the `set-sap-credentials` policy:

**For Basic Auth on real system:**
```xml
<AssignMessage name="set-sap-credentials">
  <AssignTo createNew="false" type="request"/>
  <Set>
    <Headers>
      <Header name="Authorization">Basic {named.value.sap_backend_key}</Header>
    </Headers>
  </Set>
</AssignMessage>
```

**For OAuth2 on S/4HANA Cloud:**
Use APIM's built-in OAuth2 policy to exchange credentials for a token — the Named Value stores the client secret, not the token itself.

### 11.4 Verify OData Services Are Activated on Real System

In S/4HANA (transaction `/IWFND/MAINT_SERVICE`), confirm these services are active:
- `API_SALES_ORDER_SRV`
- `API_PRODUCT_SRV`
- `API_MATERIAL_STOCK_SRV`
- `API_OUTBOUND_DELIVERY_SRV`

If not active, activate them or work with your Basis team to do so.

---

## 12. Security Controls Reference

### Summary of Controls Applied in This Architecture

| Threat | Control | Where Implemented |
|--------|---------|-------------------|
| SAP credentials exposed on client | All SAP auth stored as encrypted Named Values | BTP APIM |
| API key in transit | HTTPS enforced end-to-end | APIM SSL-Enforcement policy |
| Runaway agent loops exhausting SAP quota | 10 calls/min spike arrest | APIM Spike-Arrest policy |
| Unauthorized MCP server access | Consumer API key required on every request | APIM Verify-API-Key policy |
| Credentials committed to git | `.env` in `.gitignore`, `chmod 600` | Local + Cloud Shell |
| MCP server network exposure | stdio transport (no open port) | ADK subprocess architecture |
| `SAP_VALIDATE_SSL=false` | Removed — always `true` in APIM mode | `.env` |
| Destructive agent tool calls (DELETE) | Read-only by design in Modes 1 + 2 (Mock + Hub Sandbox) | api.sap.com sandbox is stateless |
| Prompt injection from SAP data | Out of scope for POC; add output sanitization for production | Application layer |

### The Consumer Key is Low-Privilege

The `APIM_API_KEY` stored in `.env` on Cloud Shell:
- Grants access only to the `/odata/sap/*` proxy
- Is not a SAP credential — cannot be used to log into any SAP system
- Can be rotated in the APIM Developer Portal in seconds without changing any SAP credential
- Shows in APIM analytics as a named application (`o2c-mcp-server`)

If this key is ever compromised: revoke it in the APIM Developer Portal, generate a new one, update `.env`. That is the entire incident response.

### Named Value Security

`sap_backend_key` stored in APIM:
- Stored encrypted at rest in BTP
- Never returned in responses or logs (masked in analytics)
- Accessible only to APIM policy execution — no API to retrieve the value
- Changing backends means updating this value — the MCP server is never informed

---

## 13. Repo Fixes Reference

Quick summary of all changes made to the original repos:

| Fix | File | Problem | Solution |
|-----|------|---------|----------|
| 1 | `pyproject.toml` | Requires `google-cloud-aiplatform[agent-engines]` (paid GCP) | Replace with `google-adk`, `google-genai`, `python-dotenv` only |
| 2 | `constants.py` | Hardcoded Mac filesystem path for MCP server | Dynamic path resolution with env var override; add `APIM_API_KEY` passthrough |
| 3 | All `agent.py` files | Wrong model name (non-free tier) | Replace with `gemini-2.5-flash` |
| 4 | All sub-agent `agent.py` files | `tool_filter` lists 64 entity-specific tool names that don't exist in MCP server | Remove all `tool_filter=` parameters |
| 5 | `sap-odata-mcp-server/src/odata-client.ts` | Only supports Basic Auth | Add `APIM_API_KEY` → `x-apim-key` header mode; fall back to Basic Auth if no APIM key |

---

## 14. SOFIE vs Google Stack Comparison

| SOFIE Component | Microsoft Service | Google Free Equivalent |
|----------------|-------------------|----------------------|
| LLM | Claude Opus/Sonnet (Azure AI Foundry) | Gemini 2.5 Flash (AI Studio, free) |
| Orchestration | Copilot Studio GenOrch | Google ADK `root_agent` |
| Specialist Agents | Power Automate flows (17 flows) | ADK `sub_agents` (4 Python classes) |
| SAP Auth Gateway | Azure APIM + Entra ID | BTP API Management (included in BTP Trial) |
| SAP Connector | Custom Connector | SAP OData MCP Server (Node.js, open source) |
| SAP Data | TMNA S/4HANA | api.sap.com Hub Sandbox / BTP Trial |
| UI | Microsoft Teams + Adaptive Cards | `adk web` chat (built-in dev UI) |
| QueryBuilder Logic | Power Automate expressions | Gemini native tool-calling |
| Math Aggregation | PA JavaScript Code action | Gemini native computation |
| Auth (end-user) | Entra ID SSO | Google account (Cloud Shell) |
| Deployment | Azure App Service | Cloud Run always-free (future) |

---

## 15. Gemini Rate Limits and Model Selection

As of April 2026, free tier requires no credit card and supports Flash models only:

| Model | RPM | Requests/Day | Best For |
|-------|-----|-------------|----------|
| `gemini-2.5-flash` | 10 | 250 | Coordinator agent — best reasoning |
| `gemini-2.5-flash-lite` | 15 | 1,000 | Sub-agents — faster, higher throughput |

**For this workshop:** Use `gemini-2.5-flash` for all agents. 250 requests/day is sufficient — each full O2C flow (query → format → respond) is 3-5 Gemini calls. That is ~50-80 complete interactions per day.

**To maximize throughput:** Configure the 4 sub-agents to use `gemini-2.5-flash-lite` (1,000 req/day) and keep the coordinator on `gemini-2.5-flash`. ADK calls sub-agents sequentially (not in parallel), so the 10/15 RPM limit is not a bottleneck for interactive demos.

**ADK calls sub-agents sequentially** — the coordinator does not fan out to all 4 specialists simultaneously. A multi-agent O2C query touching all 4 specialists uses ~5-8 Gemini calls total, well within both RPM and daily limits.

---

## 16. Next Steps Beyond This Workshop

Once the full O2C flow runs end-to-end in `adk web` against api.sap.com via APIM:

### Immediate Extensions
- **Add Business Partner agent** — add a 5th specialist that queries `API_BUSINESS_PARTNER` for customer details, credit limit, and contact information
- **Add O2C write flows** — create a real sales order, update delivery confirmation, post goods issue using the existing `sap_create_entity` and `sap_call_function` tools
- **Connect to a real SAP DEV client** — follow Phase 7 to point APIM at a real S/4HANA system

### Architecture Extensions
- **Deploy to Cloud Run** (free always-on tier) — containerize ADK agent + MCP server so it runs without Cloud Shell being open
- **Firebase web UI** — replace `adk web` with a production chat frontend on Firebase Hosting (free Spark plan)
- **Firestore session state** — persist conversation history across sessions using Firestore (free: 1GB, 50K reads/day)
- **odata-mcp-proxy** (lemaiwo) — generates named per-entity tools (`getAllProducts`, `createSalesOrder`) from a JSON config file, making tool names match the original `tool_filter` values in the repos — restores Option B from Fix 4 without modifying the MCP server

### SAP Domain Extensions
- **Record-to-Report (R2R) agents** — add sub-agents for GL Account inquiry, Trial Balance, Journal Entry posting using the same MCP server pattern
- **Procure-to-Pay (P2P) agents** — Purchase Orders, Goods Receipts, Invoice Verification
- **Multi-tenant APIM** — create separate API proxies per SAP client/landscape, each with its own Named Values — one ADK agent team can serve multiple SAP environments

### Production Readiness
- **OAuth2 for S/4HANA Cloud** — replace Basic Auth in APIM policy with OAuth2 client credentials flow
- **Tool allowlists per agent** — reinstate `tool_filter` using the actual 11 MCP tool names, scoped per specialist (e.g., Delivery Specialist can call `sap_call_function` for PostGoodsIssue but not `sap_delete_entity`)
- **Google Cloud Secret Manager** — move `APIM_API_KEY` and `GOOGLE_GENAI_API_KEY` from `.env` file to Secret Manager (free tier: 6 secrets, 10K access operations/month)
- **APIM metering** — move from BTP Trial to a permanent BTP subscription for production SLA guarantees
