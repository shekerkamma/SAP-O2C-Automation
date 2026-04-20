"""
Order to Cash Agent Team — Charts & Visual Analysis Agent

This agent specializes in generating branded executive-quality charts
and providing data-driven visual interpretation of O2C analytics.
"""

from google.adk.agents import Agent

from OrderToCashTeam.constants.constants import AGENT_MODEL
from OrderToCashTeam.sub_agents.charts import prompt
from OrderToCashTeam.tools.cross_entity import (
    assess_stock_risk_for_open_orders,
    get_revenue_by_customer,
    get_order_pipeline_summary,
    get_product_demand_analysis,
    get_inventory_turnover_analysis,
    get_order_value_analysis,
    get_process_bottleneck_summary,
)

# Charts & Visual Analysis agent
charts_agent = Agent(
    model=AGENT_MODEL,
    name="visual_analyst",
    description=prompt.CHARTS_AGENT_DESCRIPTION,
    instruction=prompt.CHARTS_AGENT_INSTR,
    tools=[
        assess_stock_risk_for_open_orders,
        get_revenue_by_customer,
        get_order_pipeline_summary,
        get_product_demand_analysis,
        get_inventory_turnover_analysis,
        get_order_value_analysis,
        get_process_bottleneck_summary,
    ],
)
