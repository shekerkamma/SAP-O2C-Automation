"""
Single-Entity Synthesis Agent — Order to Cash Sub-Agent

Architecture: User Query → Query Builder (QB) → OData Params → MCP Tool → Analyst Synthesis

The QB tools convert natural language to proper OData parameters BEFORE
calling the MCP/OData connector, ensuring accurate filtering and field selection.
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from OrderToCashTeam.constants.constants import AGENT_MODEL, MCP_CONNECTION_PARAMS
from OrderToCashTeam.sub_agents.single_entity_analyst import prompt
from OrderToCashTeam.tools.query_builder import (
    build_sales_order_query,
    build_sales_order_item_query,
    build_product_query,
    build_inventory_query,
    build_delivery_query,
    build_delivery_item_query,
)

single_entity_agent = Agent(
    model=AGENT_MODEL,
    name="single_entity_analyst",
    description=prompt.SINGLE_ENTITY_AGENT_DESCRIPTION,
    instruction=prompt.SINGLE_ENTITY_AGENT_INSTR,
    tools=[
        # Step 1: Query Builder tools (call FIRST to get OData params)
        build_sales_order_query,
        build_sales_order_item_query,
        build_product_query,
        build_inventory_query,
        build_delivery_query,
        build_delivery_item_query,
        # Step 2: MCP tools (call with params from QB)
        MCPToolset(
            connection_params=MCP_CONNECTION_PARAMS,
        ),
    ],
)
