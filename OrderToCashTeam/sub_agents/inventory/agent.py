"""
Order to Cash Agent Team - Inventory Management Agent

This agent specializes in material stock management, inventory levels,
and stock availability checks across SAP plants and storage locations.
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from OrderToCashTeam.sub_agents.inventory import prompt
from OrderToCashTeam.constants.constants import AGENT_MODEL, connection_params

# Inventory management agent for stock levels and material availability
inventory_agent = Agent(
    model=AGENT_MODEL,
    name="inventory_manager",
    description=prompt.INVENTORY_AGENT_DESCRIPTION,   
    instruction=prompt.INVENTORY_AGENT_INSTR,
    tools=[
        MCPToolset(
            connection_params=connection_params,
        ),
    ]
)

