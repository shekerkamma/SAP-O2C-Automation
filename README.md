# SAP Order-to-Cash Automation

A multi-agent AI system that automates the SAP Order-to-Cash (O2C) business process. Built on Google ADK + Gemini + MCP. Runs entirely on the free tier.

**[Read the blog post: From 17 Power Automate Flows to 4 Python Classes](docs/blog/from-17-flows-to-4-classes.md)**

## Try it in 3 minutes

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/shekerkamma/SAP-O2C-Automation?quickstart=1)

1. Click the badge above (or: Code > Open with Codespaces)
2. Wait ~2 minutes for the container to build
3. Add your free [Gemini API key](https://aistudio.google.com/apikey) to `agent/.env`
4. Start the mock server: `cd mcp-server && node mock-server.js`
5. Start the agent: `cd agent && adk web`
6. Open port 8080 in your browser

No SAP system required. Mock mode gives you the full agent flow with synthetic data.

## Repository layout

| Folder | Purpose |
|---|---|
| [agent/](agent/) | Multi-agent system built on Google's Agent Development Kit (ADK). Coordinates sub-agents for product, inventory, sales order, outbound delivery, and cross-entity analytics. |
| [mcp-server/](mcp-server/) | TypeScript MCP server exposing SAP OData services (sales orders, deliveries, products, stock, billing, business partners, etc.) to the agents. Includes a mock server for local development. |
| [docs/](docs/) | Workshop guide, free-tier architecture notes, OpenAPI analysis, and copilot flow diagram. |
| [.devcontainer/](.devcontainer/) | GitHub Codespaces / VS Code Dev Container configuration for zero-install setup. |

## Quick start (manual)

If you prefer not to use Codespaces:

1. **Start the MCP server** -- see [mcp-server/README.md](mcp-server/README.md) for SAP connection setup (or use the mock server for local testing).
2. **Run the agent** -- see [agent/README.md](agent/README.md) for ADK prerequisites and the list of required SAP OData services.
3. **Full workshop** -- [docs/SAP_O2C_ADK_Workshop_Guide.md](docs/SAP_O2C_ADK_Workshop_Guide.md) walks through all 7 phases, from mock to real S/4HANA.

## Architecture

The agent uses a coordinator/dispatcher pattern: a root agent routes user requests to specialized sub-agents, which call SAP OData endpoints through MCP tools. BTP API Management handles all SAP authentication, so the agent layer never touches SAP credentials.

See [docs/SAP_O2C_Google_FreeTier_Architecture.md](docs/SAP_O2C_Google_FreeTier_Architecture.md) for the full deployment topology.

## Cost

$0. Every component runs on free tiers: Gemini API (AI Studio), Google ADK (open source), BTP Trial (90 days), GitHub Codespaces (60 hours/month free).
