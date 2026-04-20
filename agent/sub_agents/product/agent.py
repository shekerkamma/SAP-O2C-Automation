"""
Product Agent - Order to Cash Sub-Agent

Handles all product-related operations including product catalog management,
product information retrieval, and product data management within the O2C process.
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from OrderToCashTeam.sub_agents.product import prompt
from OrderToCashTeam.constants.constants import AGENT_MODEL, MCP_CONNECTION_PARAMS

# Product agent specialized for product catalog management
product_agent = Agent(
    model=AGENT_MODEL,
    name="product_specialist",
    description="Specialized agent for product catalog management and product information queries. Handles product master data, descriptions, plant-specific data, and product inquiries within the Order to Cash process.",
    instruction=prompt.PRODUCT_AGENT_INSTR,
    tools=[
        MCPToolset(
            connection_params=MCP_CONNECTION_PARAMS,
        )
    ],
)