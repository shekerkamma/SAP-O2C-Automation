# SAP Order-to-Cash Automation

A proof-of-concept that automates the SAP Order-to-Cash (O2C) business process using a multi-agent system. Agents query live SAP S/4HANA data through an OData-based Model Context Protocol (MCP) server.

## Repository layout

| Folder | Purpose |
|---|---|
| [agent/](agent/) | Multi-agent system built on Google's Agent Development Kit (ADK). Coordinates sub-agents for product, inventory, sales order, outbound delivery, and cross-entity analytics. |
| [mcp-server/](mcp-server/) | TypeScript MCP server exposing SAP OData services (sales orders, deliveries, products, stock, billing, business partners, etc.) to the agents. Includes a mock server for local development. |
| [docs/](docs/) | Workshop guide, free-tier architecture notes, OpenAPI analysis, and copilot flow diagram. |

## Quick start

1. **Start the MCP server** — see [mcp-server/README.md](mcp-server/README.md) for SAP connection setup (or use the mock server for local testing).
2. **Run the agent** — see [agent/README.md](agent/README.md) for ADK prerequisites and the list of required SAP OData services.
3. **Reference material** — [docs/SAP_O2C_ADK_Workshop_Guide.md](docs/SAP_O2C_ADK_Workshop_Guide.md) walks through the end-to-end workshop.

## Architecture

The agent uses a coordinator/dispatcher pattern: a root agent routes user requests to specialized sub-agents, which call SAP OData endpoints through MCP tools. See [docs/SAP_O2C_Google_FreeTier_Architecture.md](docs/SAP_O2C_Google_FreeTier_Architecture.md) for the deployment topology.
