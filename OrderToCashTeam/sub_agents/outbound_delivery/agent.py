"""
Outbound Delivery Agent - Order to Cash Sub-Agent

Handles all outbound delivery operations including delivery document management,
picking, goods issue, and delivery fulfillment within the O2C process.
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from OrderToCashTeam.sub_agents.outbound_delivery import prompt
from OrderToCashTeam.constants.constants import AGENT_MODEL, MCP_CONNECTION_PARAMS

# Delivery agent specialized for outbound delivery management
delivery_agent = Agent(
    model=AGENT_MODEL,
    name="delivery_specialist",
    description="Specialized agent for outbound delivery management and fulfillment operations. Handles delivery document creation, picking processes, goods issue posting, and delivery tracking within the Order to Cash process.",
    instruction=prompt.DELIVERY_AGENT_INSTR,
    tools=[
        MCPToolset(
            connection_params=MCP_CONNECTION_PARAMS,
        )
    ],
)