"""
Cross-Entity Synthesis Agent — Order to Cash Sub-Agent

Handles queries that span multiple SAP domains by calling cross-entity
analytical tools and synthesizing the results into executive narratives.
"""

from google.adk.agents import Agent

from OrderToCashTeam.constants.constants import AGENT_MODEL
from OrderToCashTeam.sub_agents.cross_entity_analyst import prompt
from OrderToCashTeam.tools.cross_entity import (
    get_order_fulfillment_status,
    get_delivery_delays,
    get_customer_order_history,
    get_end_to_end_order_tracking,
    get_unfulfilled_orders_report,
    get_customer_delivery_performance,
    get_material_availability_matrix,
    get_open_order_aging,
)

cross_entity_agent = Agent(
    model=AGENT_MODEL,
    name="cross_entity_analyst",
    description=prompt.CROSS_ENTITY_AGENT_DESCRIPTION,
    instruction=prompt.CROSS_ENTITY_AGENT_INSTR,
    tools=[
        get_order_fulfillment_status,
        get_delivery_delays,
        get_customer_order_history,
        get_end_to_end_order_tracking,
        get_unfulfilled_orders_report,
        get_customer_delivery_performance,
        get_material_availability_matrix,
        get_open_order_aging,
    ],
)
