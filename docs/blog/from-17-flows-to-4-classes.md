# From 17 Power Automate Flows to 4 Python Classes: Rebuilding Enterprise SAP AI on the Free Tier

I built a multi-agent AI system that automates SAP Order-to-Cash processes at a large enterprise. Microsoft stack. Copilot Studio, Power Automate, Azure OpenAI, Adaptive Cards. It worked. It shipped. Real users, real SAP data, real business impact.

Then I rebuilt the whole thing on Google's open-source stack. For free.

The result: **17 Power Automate flows collapsed into 4 Python classes.** The complexity wasn't in the problem. It was in the tooling.

## What the system does

Order-to-Cash is the core revenue process in SAP: a customer asks about a product, you check inventory, create a sales order, ship it, and collect payment. In most organizations, this involves humans navigating 6-10 SAP transactions, copying data between screens, and making judgment calls that an LLM can handle.

The AI agent team handles it conversationally. You say "check if we have 500 units of material X in plant 1000" and the system routes your request to the right specialist agent, which calls the right SAP OData API through a secure gateway, and returns a natural language answer. No SAP GUI. No transaction codes.

## The enterprise stack (what I built first)

- **MS Teams** as the user interface
- **Copilot Studio** for conversation management
- **Power Automate** for orchestration (17 flows!)
- **Azure OpenAI** for the LLM
- **SAP OData APIs** for business data
- **Adaptive Cards** for rich responses

It works. Users love it. But the 17 Power Automate flows are the tell. Each flow handles one SAP operation: get a sales order, create a delivery, check stock levels. Each has its own error handling, its own auth, its own retry logic. Most of the "development" was clicking through the Power Automate designer, not writing code.

## The Google stack (what I rebuilt)

- **Google ADK** (Agent Development Kit), open source, `pip install google-adk`
- **Gemini 2.5 Flash** via AI Studio free tier (10 RPM, 250 requests/day)
- **SAP OData MCP Server**, a Node.js process with 11 generic tools
- **BTP API Management** as the security gateway

Four Python classes:
1. `product_agent` ... looks up the product catalog
2. `inventory_agent` ... checks stock levels
3. `sales_order_agent` ... manages sales orders
4. `delivery_agent` ... handles outbound deliveries

Each class is about 40 lines. The root coordinator agent that routes between them is 35 lines. The entire agent layer is under 200 lines of Python.

## Where the complexity went

The 17-to-4 compression happened because of two things:

**MCP replaced the glue code.** In the Microsoft stack, each Power Automate flow manually constructed HTTP requests, parsed OData responses, handled pagination, managed auth tokens. The MCP server does all of that once. Each agent just declares which MCP tools it can use. No HTTP, no auth, no parsing.

**ADK's coordinator pattern replaced the orchestration.** Power Automate flows had to explicitly route between each other with conditional logic. ADK's root agent reads the user's intent and delegates to the right specialist automatically. The LLM *is* the router.

## The SAP security model

This is the part most people skip and shouldn't.

BTP API Management sits between the AI agents and SAP. It holds all SAP credentials in encrypted Named Values. The MCP server only has a low-privilege consumer API key. The agents have nothing, just a Gemini API key.

Three backend modes with zero code changes:
- **Mock**: APIM's built-in mock service. No SAP access needed.
- **POC**: api.sap.com sandbox. Real demo data, read-only.
- **Real**: Your S/4HANA system. Full read/write.

You switch between them by changing one URL in APIM. The agents and MCP server don't know or care which backend they're hitting.

## The free tier is real

Everything in this stack is genuinely free:

| Component | Service | Cost |
|-----------|---------|------|
| LLM | Gemini 2.5 Flash (AI Studio) | $0 |
| Agent framework | Google ADK | $0, open source |
| Dev environment | Google Cloud Shell or GitHub Codespaces | $0 |
| SAP gateway | BTP Trial (90 days) | $0 |
| MCP server | Node.js subprocess | $0 |

The Gemini free tier has limits (10 requests per minute, 250 per day), but that's more than enough for development, demos, and workshops. You're not going to hit 250 agent turns in a day of building.

## Try it yourself

The full repo, working code, and a step-by-step workshop guide:

**[github.com/shekerkamma/SAP-O2C-Automation](https://github.com/shekerkamma/SAP-O2C-Automation)**

Fastest path: click **Code > Open with Codespaces**. Everything installs automatically. Add your Gemini API key, start the mock server, run `adk web`. You'll have a working SAP AI agent in under 10 minutes.

The workshop guide covers all 7 phases, from mock mode to real S/4HANA connection. No prior AI experience required. SAP basics (what a sales order is, what OData does) are assumed.

## What this means for SAP developers

SAP is one of the last enterprise categories where "real data integration" is still a moat. Every SAP system is different. Every OData service has quirks. The business logic is in customizing tables and pricing procedures that no generic AI tool understands.

If you know SAP, you can build AI agents that actually work for your organization. The tooling is no longer the bottleneck. A single developer, on the free tier, in an afternoon, can build what took a team and an enterprise license stack to build a year ago.

The 17 flows weren't the product. They were the tax. Now the tax is gone.

---

*Built with Google ADK, Gemini, and the Model Context Protocol. The [workshop repo](https://github.com/shekerkamma/SAP-O2C-Automation) is open source under Apache 2.0.*
