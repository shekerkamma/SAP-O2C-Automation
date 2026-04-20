"""
Order to Cash Agent Team - Root Agent

This is the main coordinator agent for the Order to Cash (O2C) process.
It manages the entire customer order lifecycle from initial inquiry to cash collection.
"""

from google.adk.agents import Agent

from OrderToCashTeam import prompt
from OrderToCashTeam.constants.constants import AGENT_MODEL
from OrderToCashTeam.sub_agents.inventory.agent import inventory_agent
from OrderToCashTeam.sub_agents.sales_order.agent import sales_order_agent
from OrderToCashTeam.sub_agents.product.agent import product_agent
from OrderToCashTeam.sub_agents.outbound_delivery.agent import delivery_agent
from OrderToCashTeam.sub_agents.charts.agent import charts_agent
from OrderToCashTeam.sub_agents.cross_entity_analyst.agent import cross_entity_agent
from OrderToCashTeam.sub_agents.single_entity_analyst.agent import single_entity_agent

# Root agent for Order to Cash process coordination
root_agent = Agent(
    model=AGENT_MODEL,
    name="order_to_cash_coordinator",
    description="Main coordinator for Order to Cash (O2C) business process. Manages customer orders from inquiry to delivery and manages the coordination between specialized sub-agents for different aspects of the O2C process.",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[
        charts_agent,              # Visual analytics with branded charts
        cross_entity_agent,        # Cross-entity synthesis (orders+stock+deliveries)
        single_entity_agent,       # Single-entity data synthesis
        product_agent,             # Product catalog CRUD
        inventory_agent,           # Stock levels CRUD
        sales_order_agent,         # Sales order CRUD
        delivery_agent,            # Outbound delivery CRUD
    ],
)
