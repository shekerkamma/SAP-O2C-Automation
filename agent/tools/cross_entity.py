"""
Cross-entity business rule tools for Order-to-Cash.

These are deterministic Python functions that call the SAP OData API
directly and perform cross-entity joins in code — not via LLM reasoning.
The root coordinator agent uses these for reliable multi-entity queries.
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse

from OrderToCashTeam.constants.branding import (
    BLUE, BLUE_T, CORAL, CORAL_T, AMBER, TEAL, PURPLE_T,
    PIE_PALETTE, BAR_PRIMARY, BAR_SECONDARY, BAR_REVENUE,
    RAG, ABOVE_THRESHOLD, BELOW_THRESHOLD,
    STOCK_COLOR, DEMAND_COLOR,
    CHART_WIDTH, CHART_HEIGHT, CHART_BG,
    FONT_FAMILY, LABEL_FONT_SIZE, TITLE_FONT_SIZE,
    DATALABEL_FONT_SIZE, LEGEND_FONT_SIZE,
)

BASE_URL = os.getenv("SAP_ODATA_BASE_URL", "http://127.0.0.1:3001/odata/sap/")
APIM_API_KEY = os.getenv("APIM_API_KEY", "")
SAP_USERNAME = os.getenv("SAP_USERNAME", "")
SAP_PASSWORD = os.getenv("SAP_PASSWORD", "")
QUICKCHART_URL = os.getenv("QUICKCHART_BASE_URL", "https://quickchart.io")


def _get(service: str, entity_set: str,
         filter_: str = "", top: int = 0, select: str = "",
         orderby: str = "") -> list[dict]:
    """Fetch entities from a SAP OData entity set with optional query parameters.

    Args:
        service:    OData service name (e.g. "API_SALES_ORDER_SRV")
        entity_set: Entity set name (e.g. "A_SalesOrder")
        filter_:    OData $filter string (e.g. "SalesOrder eq '10'")
        top:        Max records to return (0 = server default)
        select:     Comma-separated field list for $select
        orderby:    OData $orderby string
    """
    params = {}
    if filter_:
        params["$filter"] = filter_
    if top:
        params["$top"] = str(top)
    if select:
        params["$select"] = select
    if orderby:
        params["$orderby"] = orderby

    query_string = urllib.parse.urlencode(params) if params else ""
    url = f"{BASE_URL}{service}/{entity_set}"
    if query_string:
        url = f"{url}?{query_string}"

    headers = {"Accept": "application/json"}
    if APIM_API_KEY:
        headers["APIKey"] = APIM_API_KEY
    elif SAP_USERNAME and SAP_PASSWORD:
        import base64
        creds = base64.b64encode(f"{SAP_USERNAME}:{SAP_PASSWORD}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("d", {}).get("results", [])
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        return [{"error": str(e)}]


_JS_PLACEHOLDER_PREFIX = '"__JS__'
_JS_PLACEHOLDER_SUFFIX = '__JS__"'


def _js(func_str: str) -> str:
    """Wrap a raw JavaScript expression so _chart_url can unquote it after json.dumps."""
    return f"__JS__{func_str}__JS__"


def _chart_url(chart_config: dict, width: int = CHART_WIDTH, height: int = CHART_HEIGHT) -> str:
    """Build a QuickChart.io image URL from a Chart.js config dict."""
    cfg = json.dumps(chart_config, separators=(",", ":"))
    # Restore raw JS functions that were wrapped with _js()
    cfg = cfg.replace(_JS_PLACEHOLDER_PREFIX, "").replace(_JS_PLACEHOLDER_SUFFIX, "")
    return f"{QUICKCHART_URL}/chart?c={urllib.parse.quote(cfg, safe='')}&w={width}&h={height}&bkg={CHART_BG}"


def _global_options() -> dict:
    """Shared Chart.js options for consistent font sizing and clean rendering."""
    return {
        "defaultFontFamily": FONT_FAMILY,
        "defaultFontSize": LABEL_FONT_SIZE,
    }


def _bar_chart(labels: list[str], data: list[float], label: str = "Value",
               color: str = BAR_PRIMARY, width: int = CHART_WIDTH, height: int = CHART_HEIGHT,
               caption: str | None = None) -> dict:
    """Return a dict with Markdown image tag and optional caption for a horizontal bar chart."""
    cfg = {
        "type": "horizontalBar",
        "data": {"labels": labels, "datasets": [{"label": label, "data": data, "backgroundColor": color}]},
        "options": {
            **_global_options(),
            "plugins": {
                "datalabels": {
                    "anchor": "end", "align": "right",
                    "font": {"size": DATALABEL_FONT_SIZE},
                    "formatter": _js("(v)=>v>=1000?'$'+Math.round(v/1000)+'K':v"),
                },
            },
            "legend": {"display": False},
            "scales": {
                "xAxes": [{"ticks": {"fontSize": LABEL_FONT_SIZE, "beginAtZero": True}}],
                "yAxes": [{"ticks": {"fontSize": LABEL_FONT_SIZE}}],
            },
        },
    }
    return {"img": f"![{label}]({_chart_url(cfg, width, height)})", "caption": caption or label}


def _pie_chart(labels: list[str], data: list[float], label: str = "Share",
               width: int = CHART_WIDTH, height: int = CHART_HEIGHT,
               caption: str | None = None) -> dict:
    """Return a dict with Markdown image tag and optional caption for a doughnut chart."""
    colors = PIE_PALETTE
    cfg = {
        "type": "doughnut",
        "data": {"labels": labels, "datasets": [{"data": data, "backgroundColor": colors[:len(labels)]}]},
        "options": {
            **_global_options(),
            "plugins": {
                "datalabels": {
                    "display": True,
                    "font": {"size": DATALABEL_FONT_SIZE},
                    "formatter": _js("(val,ctx)=>{var pct=(val/ctx.dataset.data.reduce((a,b)=>a+b,0)*100).toFixed(1);return pct>2?pct+'%':''}"),
                },
            },
            "legend": {
                "position": "right",
                "labels": {"fontSize": LEGEND_FONT_SIZE, "boxWidth": 12, "padding": 8},
            },
        },
    }
    return {"img": f"![{label}]({_chart_url(cfg, width, height)})", "caption": caption or label}


def _stacked_bar(labels: list[str], datasets: list[dict],
                 width: int = CHART_WIDTH, height: int = CHART_HEIGHT,
                 caption: str | None = None) -> dict:
    """Return a dict with Markdown image tag and optional caption for a stacked bar chart."""
    cfg = {
        "type": "bar",
        "data": {"labels": labels, "datasets": datasets},
        "options": {
            **_global_options(),
            "scales": {
                "xAxes": [{"stacked": True, "ticks": {"fontSize": LABEL_FONT_SIZE}}],
                "yAxes": [{"stacked": True, "ticks": {"fontSize": LABEL_FONT_SIZE}}],
            },
            "plugins": {"datalabels": {"display": False}},
            "legend": {"labels": {"fontSize": LEGEND_FONT_SIZE, "boxWidth": 12}},
        },
    }
    return {"img": f"![Stacked Bar]({_chart_url(cfg, width, height)})", "caption": caption or "Stacked Bar"}


def _format_executive_output(
    title: str,
    kpis: list[tuple[str, str]],
    summary: str | None = None,
    table_headers: list[str] | None = None,
    table_rows: list[list[str]] | None = None,
    insights: list[str] | None = None,
    recommendations: list[str] | None = None,
    status: str | None = None,
    charts: list[dict] | None = None,  # Now expects list of dicts with 'img' and 'caption'
) -> str:
    """Build a Sophia-style executive dashboard with storytelling narrative and compact chart panel."""
    lines: list[str] = []

    # ── Title + Status ────────────────────────────────────────────────
    if status:
        indicator = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(status, "⚪")
        lines.append(f"## {indicator} {title}")
    else:
        lines.append(f"## {title}")
    lines.append("")

    # ── Narrative Story (blockquote — the Sophia "messaging front") ──
    if summary:
        lines.append(f"> {summary}")
        lines.append("")

    # ── KPI Metrics Strip (compact dashboard cards in rows of 4) ─────
    if kpis:
        chunk = 4
        for i in range(0, len(kpis), chunk):
            batch = kpis[i : i + chunk]
            lines.append("| " + " | ".join(f"**{lbl}**" for lbl, _ in batch) + " |")
            lines.append("| " + " | ".join(":---:" for _ in batch) + " |")
            lines.append("| " + " | ".join(val for _, val in batch) + " |")
            lines.append("")

    # ── Visual Dashboard (chart panel as table) ──────────────────────
    if charts:
        lines.append("### 📈 Visual Dashboard")
        lines.append("")
        # Render charts in a single row as a Markdown table
        lines.append("| " + " | ".join(chart["img"] for chart in charts) + " |")
        lines.append("| " + " | ".join(":---:" for _ in charts) + " |")
        lines.append("| " + " | ".join(chart["caption"] for chart in charts) + " |")
        lines.append("")

    # ── Detail Breakdown ──────────────────────────────────────────────
    if table_headers and table_rows:
        lines.append("### 📋 Detail Breakdown")
        lines.append("")
        lines.append("| " + " | ".join(table_headers) + " |")
        lines.append("| " + " | ".join("---" for _ in table_headers) + " |")
        for row in table_rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
        lines.append("")

    # ── Key Insights ──────────────────────────────────────────────────
    if insights:
        lines.append("### 🔍 Key Insights")
        lines.append("")
        for i, insight in enumerate(insights, 1):
            lines.append(f"{i}. {insight}")
        lines.append("")

    # ── Recommended Actions ───────────────────────────────────────────
    if recommendations:
        lines.append("### ⚡ Recommended Actions")
        lines.append("")
        for rec in recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    lines.append("---")
    return "\n".join(lines)


def assess_stock_risk_for_open_orders() -> dict:
    """Check which open sales orders are at risk due to insufficient stock.

    This tool fetches all sales orders, their line items, and current stock
    levels, then compares required quantities against available inventory.
    Returns a structured risk assessment showing which orders/materials
    have shortfalls.
    """
    # 1. Fetch all sales orders
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    # 2. Fetch all order line items
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")
    if items and "error" in items[0]:
        return {"error": f"Failed to fetch order items: {items[0]['error']}"}

    # 3. Fetch current stock levels
    stock = _get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    if stock and "error" in stock[0]:
        return {"error": f"Failed to fetch stock levels: {stock[0]['error']}"}

    # 4. Build stock lookup: material → available qty
    stock_by_material = {}
    for s in stock:
        mat = s.get("Material", "")
        qty = float(s.get("MatlWrhsStkQtyInMatlBaseUnit", "0"))
        stock_by_material[mat] = stock_by_material.get(mat, 0) + qty

    # 5. Filter to open orders (status A = open/in process)
    open_order_ids = set()
    order_info = {}
    for o in orders:
        status = o.get("OverallSDProcessStatus", "")
        if status == "A":
            so_id = o.get("SalesOrder", "")
            open_order_ids.add(so_id)
            order_info[so_id] = {
                "SoldToParty": o.get("SoldToParty", ""),
                "TotalNetAmount": o.get("TotalNetAmount", ""),
                "Currency": o.get("TransactionCurrency", ""),
            }

    # 6. Aggregate demand per material from open orders
    demand_by_material = {}
    order_items_detail = []
    for item in items:
        so_id = item.get("SalesOrder", "")
        if so_id not in open_order_ids:
            continue
        material = item.get("Material", "")
        qty = float(item.get("OrderQuantity", "0"))
        demand_by_material[material] = demand_by_material.get(material, 0) + qty
        order_items_detail.append({
            "SalesOrder": so_id,
            "SalesOrderItem": item.get("SalesOrderItem", ""),
            "Material": material,
            "OrderQuantity": qty,
        })

    # 7. Compare demand vs stock
    risk_assessment = []
    for material, total_demand in sorted(demand_by_material.items()):
        available = stock_by_material.get(material, 0)
        shortfall = total_demand - available
        risk_assessment.append({
            "Material": material,
            "TotalDemand": total_demand,
            "AvailableStock": available,
            "Shortfall": max(0, shortfall),
            "AtRisk": shortfall > 0,
        })

    # 8. Build per-order risk detail
    at_risk_orders = []
    for item in order_items_detail:
        material = item["Material"]
        available = stock_by_material.get(material, 0)
        demand_total = demand_by_material.get(material, 0)
        if demand_total > available:
            at_risk_orders.append({
                "SalesOrder": item["SalesOrder"],
                "Customer": order_info.get(item["SalesOrder"], {}).get("SoldToParty", ""),
                "Material": material,
                "OrderedQty": item["OrderQuantity"],
                "TotalDemandForMaterial": demand_total,
                "AvailableStock": available,
                "Shortfall": demand_total - available,
            })

    at_risk = [r for r in risk_assessment if r["AtRisk"]]
    total_shortfall = sum(r["Shortfall"] for r in risk_assessment)
    insights = []
    if at_risk:
        insights.append(f"{len(at_risk)} of {len(risk_assessment)} materials cannot meet current demand")
        for r in at_risk:
            insights.append(f"{r['Material']}: need {r['TotalDemand']:,.0f} units, only {r['AvailableStock']:,.0f} in stock \u2192 shortfall of {r['Shortfall']:,.0f}")
        affected = sorted(set(o["SalesOrder"] for o in at_risk_orders))
        insights.append(f"Affected sales orders: {', '.join(affected)}")
    else:
        insights.append("All materials have sufficient stock to fulfill open orders")
    recs = []
    if at_risk:
        recs.append(f"Urgently procure: {', '.join(r['Material'] for r in at_risk)}")
        customers = sorted(set(o["Customer"] for o in at_risk_orders))
        recs.append(f"Proactively notify affected customers: {', '.join(customers)}")
        recs.append("Consider partial fulfillment for orders with mixed availability")
    # Charts: demand vs stock per material
    chart_labels = [r["Material"] for r in risk_assessment]
    chart_demand = [r["TotalDemand"] for r in risk_assessment]
    chart_stock = [r["AvailableStock"] for r in risk_assessment]
    risk_charts = []
    if chart_labels:
        risk_charts = [
            _stacked_bar(
                chart_labels,
                [
                    {"label": "Available Stock", "data": chart_stock, "backgroundColor": STOCK_COLOR},
                    {"label": "Shortfall", "data": [max(0, d - s) for d, s in zip(chart_demand, chart_stock)], "backgroundColor": DEMAND_COLOR},
                ],
                caption="Supply vs Demand Gap — available stock vs shortfall for each material. Red highlights risk areas."
            ),
            _pie_chart(
                ["At Risk", "Adequate"],
                [len(at_risk), max(0, len(risk_assessment) - len(at_risk))],
                "Material Risk Profile",
                caption=f"Pie: {len(at_risk)} at risk, {max(0, len(risk_assessment) - len(at_risk))} adequate. Visualizes overall risk exposure."
            ) if len(risk_assessment) else None,
        ]
        risk_charts = [c for c in risk_charts if c is not None]

    risk_summary = (
        f"{len(at_risk)} of {len(risk_assessment)} materials cannot meet current open-order demand, "
        f"creating a total shortfall of {total_shortfall:,.0f} units across {len(set(o['SalesOrder'] for o in at_risk_orders))} order(s). "
        "Procurement action is needed immediately to avoid delivery delays."
    ) if at_risk else "All materials have sufficient stock to fulfill every open order — supply chain is healthy."

    narrative = _format_executive_output(
        title="Stock Risk Assessment — Open Orders",
        status="RED" if at_risk else "GREEN",
        summary=risk_summary,
        kpis=[
            ("Open Orders", str(len(open_order_ids))),
            ("Materials Assessed", str(len(risk_assessment))),
            ("Materials at Risk", str(len(at_risk))),
            ("Total Shortfall", f"{total_shortfall:,.0f} units"),
        ],
        table_headers=["Material", "Total Demand", "Available Stock", "Shortfall", "At Risk"],
        table_rows=[
            [r["Material"], f"{r['TotalDemand']:,.0f}", f"{r['AvailableStock']:,.0f}",
             f"{r['Shortfall']:,.0f}", "\u274c Yes" if r["AtRisk"] else "\u2705 No"]
            for r in risk_assessment
        ],
        charts=risk_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


def get_order_fulfillment_status(sales_order: str) -> dict:
    """Get complete fulfillment status for a specific sales order.

    Fetches the order header, its line items, stock availability for each
    material, and any related deliveries. Returns a single consolidated view.

    Args:
        sales_order: The sales order number (e.g. "10", "11", "12").
    """
    # 1. Fetch order header (filtered by order ID)
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder",
                   filter_=f"SalesOrder eq '{sales_order}'")
    order = next((o for o in orders if o.get("SalesOrder") == sales_order), None)
    if not order:
        return {"error": f"Sales order {sales_order} not found"}

    # 2. Fetch line items (filtered by order ID)
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem",
                  filter_=f"SalesOrder eq '{sales_order}'")
    items = [i for i in items if i.get("SalesOrder") == sales_order]

    # 3. Fetch stock (for materials in this order)
    materials = {i.get("Material", "") for i in items if i.get("Material")}
    stock = _get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    stock_by_material = {}
    for s in stock:
        mat = s.get("Material", "")
        if mat in materials:
            qty = float(s.get("MatlWrhsStkQtyInMatlBaseUnit", "0"))
            stock_by_material[mat] = stock_by_material.get(mat, 0) + qty

    # 4. Fetch deliveries (filtered by customer)
    customer = order.get("SoldToParty", "")
    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader",
                       filter_=f"SoldToParty eq '{customer}'" if customer else "")
    related_deliveries = [d for d in deliveries if d.get("SoldToParty") == customer]

    # 5. Build line item detail with stock check
    line_details = []
    for item in items:
        material = item.get("Material", "")
        ordered = float(item.get("OrderQuantity", "0"))
        available = stock_by_material.get(material, 0)
        line_details.append({
            "Item": item.get("SalesOrderItem", ""),
            "Material": material,
            "OrderedQty": ordered,
            "AvailableStock": available,
            "CanFulfill": available >= ordered,
            "Shortfall": max(0, ordered - available),
        })

    STATUS_MAP = {"A": "Open / In Process", "B": "Partially Delivered", "C": "Completed"}
    can_fulfill_all = all(ld["CanFulfill"] for ld in line_details)
    total_shortfall = sum(ld["Shortfall"] for ld in line_details)
    unfulfillable_count = sum(1 for ld in line_details if not ld["CanFulfill"])
    has_deliveries = len(related_deliveries) > 0
    insights = [
        f"Order status: {STATUS_MAP.get(order.get('OverallSDProcessStatus', ''), 'Unknown')}",
        f"All items can be fulfilled from current stock" if can_fulfill_all else f"{unfulfillable_count} item(s) have stock shortfall totaling {total_shortfall:,.0f} units",
        f"Delivery in progress ({len(related_deliveries)} document(s))" if has_deliveries else "No delivery document created yet \u2014 needs warehouse action",
    ]
    recs = []
    if not can_fulfill_all:
        recs.append("Expedite procurement for short materials before confirming delivery date")
    if not has_deliveries:
        recs.append("Create outbound delivery document to initiate shipping process")
    ful_summary = (
        f"Sales order {sales_order} for customer {customer} is fully fulfillable from current stock "
        + ("and has delivery documents in progress." if has_deliveries else "but no delivery document has been created yet — warehouse action needed.")
    ) if can_fulfill_all else (
        f"Sales order {sales_order} cannot be fully fulfilled — {unfulfillable_count} of {len(line_details)} item(s) "
        f"have a combined stock shortfall of {total_shortfall:,.0f} units. Procurement is required before delivery can proceed."
    )
    narrative = _format_executive_output(
        title=f"Order Fulfillment Status \u2014 SO {sales_order}",
        status="GREEN" if can_fulfill_all and has_deliveries else ("AMBER" if can_fulfill_all else "RED"),
        summary=ful_summary,
        kpis=[
            ("Sales Order", sales_order),
            ("Customer", customer),
            ("Order Value", f"${float(order.get('TotalNetAmount', '0')):,.2f} {order.get('TransactionCurrency', 'USD')}"),
            ("Line Items", str(len(line_details))),
            ("Fulfillable Items", f"{sum(1 for ld in line_details if ld['CanFulfill'])} of {len(line_details)}"),
            ("Deliveries", str(len(related_deliveries))),
        ],
        table_headers=["Item", "Material", "Ordered", "Available", "Fulfillable", "Shortfall"],
        table_rows=[
            [ld["Item"], ld["Material"], f"{ld['OrderedQty']:,.0f}", f"{ld['AvailableStock']:,.0f}",
             "\u2705 Yes" if ld["CanFulfill"] else "\u274c No", f"{ld['Shortfall']:,.0f}"]
            for ld in line_details
        ],
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


def get_revenue_by_customer() -> dict:
    """Get total revenue breakdown per customer across all sales orders.

    Aggregates order values by customer (SoldToParty), showing the number
    of orders, total revenue, and order details for each customer.
    Useful for identifying top customers and revenue concentration.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    customer_data: dict[str, dict] = {}
    for o in orders:
        cust = o.get("SoldToParty", "UNKNOWN")
        amount = float(o.get("TotalNetAmount", "0"))
        currency = o.get("TransactionCurrency", "USD")
        if cust not in customer_data:
            customer_data[cust] = {
                "customer": cust,
                "order_count": 0,
                "total_revenue": 0.0,
                "currency": currency,
                "orders": [],
            }
        customer_data[cust]["order_count"] += 1
        customer_data[cust]["total_revenue"] += amount
        customer_data[cust]["orders"].append({
            "SalesOrder": o.get("SalesOrder", ""),
            "Amount": amount,
            "Status": o.get("OverallSDProcessStatus", ""),
        })

    # Sort by revenue descending
    ranked = sorted(customer_data.values(), key=lambda c: c["total_revenue"], reverse=True)
    grand_total = sum(c["total_revenue"] for c in ranked)

    insights = []
    if ranked and grand_total:
        insights.append(f"Top customer: {ranked[0]['customer']} — ${ranked[0]['total_revenue']:,.2f} ({ranked[0]['total_revenue']/grand_total*100:.1f}% of total)")
        insights.append(f"Average revenue per customer: ${grand_total/len(ranked):,.2f}")
        if len(ranked) > 1:
            insights.append(f"Revenue spread: ${ranked[0]['total_revenue']:,.2f} (highest) vs ${ranked[-1]['total_revenue']:,.2f} (lowest) — {ranked[0]['total_revenue']/ranked[-1]['total_revenue']:.1f}x gap")
            top_share = ranked[0]['total_revenue']/grand_total*100 if grand_total else 0
            insights.append(f"Concentration risk: top customer drives {top_share:.1f}% of revenue — {'high dependency' if top_share > 50 else 'healthy diversification'}")
    else:
        insights.append("No customer data")

    # Charts: revenue by customer
    rev_labels = [c["customer"] for c in ranked]
    rev_data = [c["total_revenue"] for c in ranked]
    rev_pct = [c["total_revenue"] / grand_total * 100 for c in ranked] if grand_total else []
    revenue_charts = []
    if rev_labels:
        revenue_charts = [
            _bar_chart(
                rev_labels, rev_data, "Revenue ($)",
                caption="Revenue Concentration — top contributors and revenue distribution across customer base."
            ),
            _pie_chart(
                rev_labels, rev_pct, "Revenue Share",
                caption="Customer Portfolio Balance — share of total revenue by customer, reveals dependency risk."
            ),
        ]

    table_rows = [
        [str(i+1), c["customer"], str(c["order_count"]), f"${c['total_revenue']:,.2f}",
         f"{c['total_revenue']/grand_total*100:.1f}%" if grand_total else "0%"]
        for i, c in enumerate(ranked)
    ]

    top = ranked[0] if ranked else None
    rev_summary = (
        f"Total revenue of ${grand_total:,.2f} across {len(ranked)} customers. "
        f"{top['customer']} leads with ${top['total_revenue']:,.2f} ({top['total_revenue']/grand_total*100:.1f}% of total). "
        f"Average revenue per customer: ${grand_total/len(ranked):,.2f}."
    ) if top and grand_total else "No revenue data available."

    recs = []
    if ranked and grand_total:
        top_share = ranked[0]['total_revenue'] / grand_total * 100
        if top_share > 50:
            recs.append(f"Diversify — {ranked[0]['customer']} drives {top_share:.0f}% of revenue")
        if len(ranked) > 1:
            recs.append(f"Grow bottom customers: {', '.join(c['customer'] for c in ranked[-2:])}")

    narrative = _format_executive_output(
        title="Revenue by Customer",
        status="AMBER" if (ranked and ranked[0]['total_revenue'] / grand_total > 0.5) else "GREEN" if ranked else None,
        summary=rev_summary,
        kpis=[
            ("Total Revenue", f"${grand_total:,.2f}"),
            ("Customers", str(len(ranked))),
            ("Top Customer", top["customer"] if top else "N/A"),
            ("Avg / Customer", f"${grand_total/len(ranked):,.2f}" if ranked else "$0"),
        ],
        table_headers=["Rank", "Customer", "Orders", "Revenue", "Share"],
        table_rows=table_rows,
        charts=revenue_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


def get_delivery_delays() -> dict:
    """Identify potential delivery delays by comparing delivery dates against
    the requested delivery dates on sales orders.

    Matches deliveries to orders via SoldToParty (customer) and checks
    whether the actual delivery date is on time, early, or late compared
    to the order's requested delivery date.
    Also flags open orders that have no delivery created yet.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader")
    if deliveries and "error" in deliveries[0]:
        return {"error": f"Failed to fetch deliveries: {deliveries[0]['error']}"}

    # Build delivery lookup by customer
    delivery_by_customer: dict[str, list[dict]] = {}
    for d in deliveries:
        cust = d.get("SoldToParty", "")
        if cust not in delivery_by_customer:
            delivery_by_customer[cust] = []
        delivery_by_customer[cust].append(d)

    def parse_odata_date(date_str: str) -> int | None:
        if not date_str:
            return None
        import re
        m = re.search(r"/Date\((\d+)\)/", date_str)
        return int(m.group(1)) if m else None

    results = []
    orders_without_delivery = []

    for o in orders:
        so_id = o.get("SalesOrder", "")
        cust = o.get("SoldToParty", "")
        requested_ms = parse_odata_date(o.get("RequestedDeliveryDate", ""))
        status = o.get("OverallSDProcessStatus", "")

        cust_deliveries = delivery_by_customer.get(cust, [])

        if not cust_deliveries:
            orders_without_delivery.append({
                "SalesOrder": so_id,
                "Customer": cust,
                "OrderStatus": status,
                "RequestedDeliveryDate": o.get("RequestedDeliveryDate", ""),
                "Issue": "No delivery document created",
            })
            continue

        for d in cust_deliveries:
            delivery_ms = parse_odata_date(d.get("DeliveryDate", ""))
            delay_days = None
            delay_status = "unknown"

            if requested_ms and delivery_ms:
                diff_ms = delivery_ms - requested_ms
                delay_days = round(diff_ms / (1000 * 60 * 60 * 24), 1)
                if delay_days <= 0:
                    delay_status = "on_time_or_early"
                elif delay_days <= 3:
                    delay_status = "slightly_late"
                else:
                    delay_status = "delayed"

            results.append({
                "SalesOrder": so_id,
                "Customer": cust,
                "DeliveryDocument": d.get("DeliveryDocument", ""),
                "DeliveryStatus": d.get("OverallGoodsMovementStatus", ""),
                "RequestedDeliveryDate": o.get("RequestedDeliveryDate", ""),
                "ActualDeliveryDate": d.get("DeliveryDate", ""),
                "DelayDays": delay_days,
                "DelayStatus": delay_status,
            })

    delayed_count = sum(1 for r in results if r["DelayStatus"] == "delayed")
    on_time = [r for r in results if r["DelayStatus"] == "on_time_or_early"]
    slightly_late = [r for r in results if r["DelayStatus"] == "slightly_late"]
    delayed = [r for r in results if r["DelayStatus"] == "delayed"]
    on_time_pct = len(on_time) / len(results) * 100 if results else 100

    table_rows = [
        [r["SalesOrder"], r["Customer"], r["DeliveryDocument"],
         {"on_time_or_early": "\U0001f7e2 On Time", "slightly_late": "\U0001f7e1 Slight", "delayed": "\U0001f534 Late"}.get(r["DelayStatus"], "?"),
         f"{r['DelayDays']:.1f}" if r["DelayDays"] is not None else "N/A"]
        for r in results
    ]

    insights = [
        f"On-time delivery rate: {on_time_pct:.0f}% ({len(on_time)} of {len(results)} deliveries on time or early)",
        f"Delayed shipments: {len(delayed)}" + (f" — avg delay: {sum(r['DelayDays'] for r in delayed if r['DelayDays'])/len(delayed):.1f} days" if delayed else ""),
        f"{len(orders_without_delivery)} order(s) have no delivery document created yet" if orders_without_delivery else "All orders have delivery documents",
    ]
    recs = []
    if delayed:
        recs.append(f"Expedite delayed deliveries: {', '.join(r['DeliveryDocument'] for r in delayed)}")
    if orders_without_delivery:
        recs.append(f"Create deliveries for orders: {', '.join(o['SalesOrder'] for o in orders_without_delivery)}")
    if on_time_pct < 80:
        recs.append("Review shipping processes — on-time rate below 80% target")

    delivery_charts = []
    if results:
        status_labels = ["On Time / Early", "Slightly Late", "Delayed"]
        status_counts = [len(on_time), len(slightly_late), len(delayed)]
        delivery_charts = [
            _pie_chart(status_labels, status_counts, "Delivery Status Split", caption="Delivery Performance Spread — status distribution across delivery portfolio."),
        ]

    delay_summary = (
        f"On-time delivery rate is {on_time_pct:.0f}% across {len(results)} tracked deliveries. "
        + (f"{len(delayed)} shipment(s) are significantly delayed. " if delayed else "No major delays detected. ")
        + (f"{len(orders_without_delivery)} order(s) still have no delivery document created." if orders_without_delivery else "")
    )

    narrative = _format_executive_output(
        title="Delivery Delay Analysis",
        status="RED" if delayed else ("AMBER" if orders_without_delivery else "GREEN"),
        summary=delay_summary,
        kpis=[
            ("Deliveries Tracked", str(len(results))),
            ("On-Time Rate", f"{on_time_pct:.0f}%"),
            ("Delayed", str(len(delayed))),
            ("No Delivery Doc", str(len(orders_without_delivery))),
        ],
        table_headers=["Order", "Customer", "Delivery", "Status", "Delay (days)"],
        table_rows=table_rows,
        charts=delivery_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


def get_order_pipeline_summary() -> dict:
    """Get a summary of the sales order pipeline grouped by order status.

    Shows how many orders are in each status (A=Open/In Process, B=Partially Delivered, C=Completed, etc.),
    with total values per status. Useful for understanding the current order backlog,
    throughput, and financial pipeline.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    STATUS_LABELS = {
        "A": "Open / In Process",
        "B": "Partially Delivered",
        "C": "Completed",
        "": "Unknown",
    }

    pipeline: dict[str, dict] = {}
    for o in orders:
        status = o.get("OverallSDProcessStatus", "UNKNOWN")
        amount = float(o.get("TotalNetAmount", "0"))
        currency = o.get("TransactionCurrency", "USD")

        if status not in pipeline:
            pipeline[status] = {
                "status_code": status,
                "status_label": STATUS_LABELS.get(status, f"Unknown ({status})"),
                "order_count": 0,
                "total_value": 0.0,
                "currency": currency,
                "orders": [],
            }
        pipeline[status]["order_count"] += 1
        pipeline[status]["total_value"] += amount
        pipeline[status]["orders"].append({
            "SalesOrder": o.get("SalesOrder", ""),
            "Customer": o.get("SoldToParty", ""),
            "Amount": amount,
        })

    stages = sorted(pipeline.values(), key=lambda s: s["status_code"])
    grand_total = sum(s["total_value"] for s in stages)
    total_orders = sum(s["order_count"] for s in stages)

    open_stages = [s for s in stages if s["status_code"] == "A"]
    completed_stages = [s for s in stages if s["status_code"] == "B"]
    open_count = sum(s["order_count"] for s in open_stages)
    open_value = sum(s["total_value"] for s in open_stages)
    completed_count = sum(s["order_count"] for s in completed_stages)
    completed_value = sum(s["total_value"] for s in completed_stages)
    completion_rate = (completed_count / total_orders * 100) if total_orders else 0
    avg_open = open_value / open_count if open_count else 0
    avg_completed = completed_value / completed_count if completed_count else 0

    table_rows = [
        [s["status_label"], str(s["order_count"]),
         f"${s['total_value']:,.2f}",
         f"{(s['total_value']/grand_total*100):.1f}%" if grand_total else "0%",
         f"${s['total_value']/s['order_count']:,.2f}" if s["order_count"] else "$0"]
        for s in stages
    ]

    insights = []
    if total_orders:
        insights.append(f"Completion rate: {completion_rate:.1f}% — {'healthy throughput' if completion_rate > 50 else 'backlog building, needs attention'}")
        if open_value and completed_value:
            insights.append(f"Open pipeline (${open_value:,.2f}) is {open_value/completed_value:.1f}x the completed value — {'significant backlog' if open_value/completed_value > 3 else 'manageable ratio'}")
        elif open_count and not completed_count:
            insights.append("No orders completed yet — entire pipeline is open")
        if avg_open and avg_completed:
            insights.append(f"Average open order: ${avg_open:,.2f} vs completed: ${avg_completed:,.2f}")
        for s in open_stages:
            if s["orders"]:
                top = max(s["orders"], key=lambda x: x["Amount"])
                insights.append(f"Highest-value open order: SO {top['SalesOrder']} ({top['Customer']}) at ${top['Amount']:,.2f} — {top['Amount']/open_value*100:.0f}% of open pipeline")
    else:
        insights.append("No orders in the pipeline.")

    recs = []
    if completion_rate < 50:
        recs.append(f"Improve completion rate from {completion_rate:.1f}% toward 50%+ target")
    if open_count:
        for s in open_stages:
            if s["orders"]:
                top = max(s["orders"], key=lambda x: x["Amount"])
                recs.append(f"Prioritize SO {top['SalesOrder']} — represents ${top['Amount']:,.2f} in pipeline")
                break
        recs.append(f"Monitor {open_count} open orders worth ${open_value:,.2f} for fulfillment progress")

    pipe_labels = [s["status_label"] for s in stages]
    pipe_values = [s["total_value"] for s in stages]
    pipe_counts = [s["order_count"] for s in stages]
    pipeline_charts = []
    if pipe_labels:
        pipeline_charts = [
            _pie_chart(
                pipe_labels,
                [v / grand_total * 100 for v in pipe_values] if grand_total else pipe_counts,
                "Pipeline Value Split",
                caption=f"Pie: {open_value/grand_total*100:.1f}% of pipeline value is open/in-process — backlog risk." if grand_total else "Pipeline value split."
            ),
            _bar_chart(
                pipe_labels,
                pipe_counts,
                "Orders by Status",
                BLUE,
                caption=f"Bar: {open_count} open vs {completed_count} completed. Focus on clearing open orders."
            ),
        ]

    pipe_summary = (
        f"{total_orders} orders totaling ${grand_total:,.2f} in the pipeline. "
        f"{open_count} open (${open_value:,.2f}), {completed_count} completed (${completed_value:,.2f}). "
        f"Completion rate: {completion_rate:.1f}%."
    ) if total_orders else "No orders in the pipeline."

    narrative = _format_executive_output(
        title="Order Pipeline Summary",
        status="GREEN" if completion_rate >= 50 else "AMBER" if total_orders else None,
        summary=pipe_summary,
        kpis=[
            ("Total Orders", str(total_orders)),
            ("Pipeline Value", f"${grand_total:,.2f}"),
            ("Open Orders", f"{open_count} (${open_value:,.2f})"),
            ("Completion Rate", f"{completion_rate:.1f}%"),
        ],
        table_headers=["Status", "Orders", "Value", "Share", "Avg Value"],
        table_rows=table_rows,
        charts=pipeline_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 6: Customer 360° ────────────────────────────────────────────────────

def get_customer_order_history(customer: str) -> dict:
    """Get complete 360-degree view of a customer's activity across the O2C process.

    Shows all orders, line items, deliveries, and financial summary for a
    specific customer (SoldToParty). Useful for customer relationship
    management, account reviews, and understanding buying patterns.

    Args:
        customer: The customer ID (e.g. "CUST-001", "CUST-002").
    """
    # Filtered fetch: orders, items, deliveries for this customer
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder",
                   filter_=f"SoldToParty eq '{customer}'")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    cust_orders = [o for o in orders if o.get("SoldToParty") == customer]
    if not cust_orders:
        return {"error": f"No orders found for customer {customer}"}

    cust_order_ids = {o.get("SalesOrder") for o in cust_orders}
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")
    cust_items = [i for i in items if i.get("SalesOrder") in cust_order_ids]
    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader",
                       filter_=f"SoldToParty eq '{customer}'")
    cust_deliveries = [d for d in deliveries if d.get("SoldToParty") == customer]

    total_revenue = sum(float(o.get("TotalNetAmount", "0")) for o in cust_orders)
    open_orders = [o for o in cust_orders if o.get("OverallSDProcessStatus") == "A"]
    completed_orders = [o for o in cust_orders if o.get("OverallSDProcessStatus") == "B"]

    # Products purchased
    materials = {}
    for i in cust_items:
        mat = i.get("Material", "")
        qty = float(i.get("OrderQuantity", "0"))
        amt = float(i.get("NetAmount", "0"))
        if mat not in materials:
            materials[mat] = {"material": mat, "total_qty": 0, "total_value": 0.0}
        materials[mat]["total_qty"] += qty
        materials[mat]["total_value"] += amt

    ranked_products = sorted(materials.values(), key=lambda m: m["total_value"], reverse=True)
    STATUS_MAP = {"A": "Open / In Process", "B": "Partially Delivered", "C": "Completed"}
    avg_order = total_revenue / len(cust_orders) if cust_orders else 0
    insights = [
        f"Customer has {len(cust_orders)} total orders — {len(open_orders)} open, {len(completed_orders)} completed",
        f"Average order value: ${avg_order:,.2f}",
    ]
    if ranked_products:
        top = ranked_products[0]
        insights.append(f"Most purchased product: {top['material']} — {top['total_qty']:,.0f} units, ${top['total_value']:,.2f} revenue")
        if len(ranked_products) > 1:
            insights.append(f"Product breadth: {len(ranked_products)} distinct materials ordered")
    if not cust_deliveries:
        insights.append("No delivery documents found — fulfillment not yet initiated")
    elif len(cust_deliveries) < len(cust_orders):
        insights.append(f"Delivery coverage gap: {len(cust_deliveries)} deliveries for {len(cust_orders)} orders")
    recs = []
    if open_orders:
        recs.append(f"Follow up on {len(open_orders)} open order(s) worth ${sum(float(o.get('TotalNetAmount', '0')) for o in open_orders):,.2f}")
    if not cust_deliveries and open_orders:
        recs.append("Create outbound delivery documents to begin fulfillment")
    cust_summary = (
        f"Customer {customer} has placed {len(cust_orders)} order(s) with lifetime revenue of ${total_revenue:,.2f} "
        f"(average ${avg_order:,.2f} per order). "
        + (f"{len(open_orders)} order(s) are currently open. " if open_orders else "All orders are completed. ")
        + (f"{len(cust_deliveries)} delivery document(s) are active." if cust_deliveries else "No delivery documents have been created yet.")
    )
    narrative = _format_executive_output(
        title=f"Customer 360\u00b0 Profile \u2014 {customer}",
        summary=cust_summary,
        kpis=[
            ("Customer ID", customer),
            ("Total Orders", str(len(cust_orders))),
            ("Open Orders", str(len(open_orders))),
            ("Completed Orders", str(len(completed_orders))),
            ("Lifetime Revenue", f"${total_revenue:,.2f}"),
            ("Avg Order Value", f"${avg_order:,.2f}"),
            ("Active Deliveries", str(len(cust_deliveries))),
        ],
        table_headers=["Material", "Qty Ordered", "Revenue", "% of Total"],
        table_rows=[
            [p["material"], f"{p['total_qty']:,.0f}", f"${p['total_value']:,.2f}",
             f"{p['total_value']/total_revenue*100:.1f}%" if total_revenue else "0%"]
            for p in ranked_products
        ],
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 7: Product Demand Analysis ──────────────────────────────────────────

def get_product_demand_analysis() -> dict:
    """Analyze product demand across all orders to identify best sellers,
    revenue drivers, and demand patterns by product group.

    Joins sales order items with product master data to show each product's
    total order quantity, revenue contribution, and which customers order it.
    """
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")
    if items and "error" in items[0]:
        return {"error": f"Failed to fetch order items: {items[0]['error']}"}

    products = _get("API_PRODUCT_SRV", "A_Product")
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")

    # Product master lookup
    product_info = {p.get("Product"): p for p in products}
    # Order → customer mapping
    order_customer = {o.get("SalesOrder"): o.get("SoldToParty") for o in orders}

    demand: dict[str, dict] = {}
    for i in items:
        mat = i.get("Material", "")
        qty = float(i.get("OrderQuantity", "0"))
        amt = float(i.get("NetAmount", "0"))
        so = i.get("SalesOrder", "")
        cust = order_customer.get(so, "UNKNOWN")

        if mat not in demand:
            pinfo = product_info.get(mat, {})
            demand[mat] = {
                "material": mat,
                "product_group": pinfo.get("ProductGroup", "N/A"),
                "gross_weight_kg": float(pinfo.get("GrossWeight", "0")),
                "total_quantity_ordered": 0,
                "total_revenue": 0.0,
                "order_count": 0,
                "customers": set(),
            }
        demand[mat]["total_quantity_ordered"] += qty
        demand[mat]["total_revenue"] += amt
        demand[mat]["order_count"] += 1
        demand[mat]["customers"].add(cust)

    # Convert sets to lists for JSON
    ranked = sorted(demand.values(), key=lambda d: d["total_revenue"], reverse=True)
    for d in ranked:
        d["customers"] = sorted(d["customers"])
        d["customer_count"] = len(d["customers"])

    # Group by product group
    by_group: dict[str, float] = {}
    for d in ranked:
        grp = d["product_group"]
        by_group[grp] = by_group.get(grp, 0) + d["total_revenue"]

    grand_revenue = sum(d["total_revenue"] for d in ranked)

    table_rows = [
        [str(i+1), d["material"], d["product_group"], f"{d['total_quantity_ordered']:,.0f}",
         f"${d['total_revenue']:,.2f}",
         f"{d['total_revenue']/grand_revenue*100:.1f}%" if grand_revenue else "0%",
         str(d.get("customer_count", 0))]
        for i, d in enumerate(ranked)
    ]

    insights = []
    if ranked and grand_revenue:
        insights.append(f"Best seller: {ranked[0]['material']} — ${ranked[0]['total_revenue']:,.2f} ({ranked[0]['total_revenue']/grand_revenue*100:.1f}% of total)")
        if len(ranked) > 1:
            top_share = ranked[0]["total_revenue"] / grand_revenue * 100 if grand_revenue else 0
            insights.append(f"Product concentration: top product drives {top_share:.1f}% of revenue — {'high dependency' if top_share > 50 else 'healthy spread'}")
            insights.append(f"Revenue spread: ${ranked[0]['total_revenue']:,.2f} (top) vs ${ranked[-1]['total_revenue']:,.2f} (bottom)")
        if by_group:
            top_grp = max(by_group, key=by_group.get)
            insights.append(f"Top product group: {top_grp} — ${by_group[top_grp]:,.2f} ({by_group[top_grp]/grand_revenue*100:.1f}% of revenue)")
        multi_cust = [d for d in ranked if d.get("customer_count", 0) > 1]
        if multi_cust:
            insights.append(f"{len(multi_cust)} product(s) ordered by multiple customers — broad market appeal")
    else:
        insights.append("No demand data")

    prod_labels = [d["material"] for d in ranked[:8]]
    prod_rev = [d["total_revenue"] for d in ranked[:8]]
    prod_qty = [d["total_quantity_ordered"] for d in ranked[:8]]
    demand_charts = []
    if prod_labels:
        demand_charts = [
            _bar_chart(
                prod_labels, prod_rev, "Revenue ($)", BAR_REVENUE,
                caption="Demand Leadership — revenue ranking identifies best sellers and revenue drivers."
            ),
            _bar_chart(
                prod_labels, prod_qty, "Qty Ordered", BAR_SECONDARY,
                caption="Product-Revenue Alignment — demand volume and breadth across product portfolio."
            ),
        ]

    best = ranked[0] if ranked else None
    demand_summary = (
        f"{len(ranked)} products generating ${grand_revenue:,.2f} in total revenue across {len(by_group)} product group(s). "
        f"Best seller: {best['material']} at ${best['total_revenue']:,.2f} ({best['total_revenue']/grand_revenue*100:.1f}% of total)."
    ) if best and grand_revenue else "No product demand data available."

    recs = []
    if ranked and grand_revenue:
        top_share = ranked[0]["total_revenue"] / grand_revenue * 100
        if top_share > 50:
            recs.append(f"Reduce product dependency — {ranked[0]['material']} drives {top_share:.0f}% of revenue")
        recs.append("Ensure adequate stock for top-demand products to avoid lost sales")

    narrative = _format_executive_output(
        title="Product Demand Analysis",
        summary=demand_summary,
        kpis=[
            ("Products", str(len(ranked))),
            ("Total Revenue", f"${grand_revenue:,.2f}"),
            ("Best Seller", best["material"] if best else "N/A"),
            ("Product Groups", str(len(by_group))),
        ],
        table_headers=["Rank", "Material", "Group", "Qty Ordered", "Revenue", "Share", "Customers"],
        table_rows=table_rows,
        charts=demand_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 8: End-to-End Order Tracking ────────────────────────────────────────

def get_end_to_end_order_tracking(sales_order: str) -> dict:
    """Track a single order through every stage of the O2C lifecycle.

    Traces the order from creation → line items → product details →
    stock availability → delivery status. Returns a timeline-style view
    showing the current state at each stage and any blockers.

    Args:
        sales_order: The sales order number (e.g. "10").
    """
    import re

    # Filtered fetch: order header by ID
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder",
                   filter_=f"SalesOrder eq '{sales_order}'")
    order = next((o for o in orders if o.get("SalesOrder") == sales_order), None)
    if not order:
        return {"error": f"Sales order {sales_order} not found"}

    # Filtered fetch: line items for this order
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem",
                  filter_=f"SalesOrder eq '{sales_order}'")
    order_items = [i for i in items if i.get("SalesOrder") == sales_order]

    # Fetch products and stock for materials in this order
    materials = {i.get("Material", "") for i in order_items if i.get("Material")}
    products = _get("API_PRODUCT_SRV", "A_Product")
    product_info = {p.get("Product"): p for p in products if p.get("Product") in materials}

    stock = _get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    stock_by_mat = {}
    for s in stock:
        mat = s.get("Material", "")
        if mat in materials:
            stock_by_mat[mat] = stock_by_mat.get(mat, 0) + float(s.get("MatlWrhsStkQtyInMatlBaseUnit", "0"))

    # Filtered fetch: deliveries for this customer
    customer = order.get("SoldToParty", "")
    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader",
                       filter_=f"SoldToParty eq '{customer}'" if customer else "")
    order_deliveries = [d for d in deliveries if d.get("SoldToParty") == customer]

    def parse_date(ds):
        m = re.search(r"/Date\((\d+)\)/", ds or "")
        if m:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        return None

    STATUS_MAP = {"A": "Open / In Process", "B": "Partially Delivered", "C": "Completed"}
    DELIVERY_STATUS_MAP = {"A": "Not Yet Processed", "B": "Partially Processed", "C": "Completely Processed"}

    # Build lifecycle stages
    stages = []

    # Stage 1: Order Created
    stages.append({
        "stage": "1_ORDER_CREATED",
        "status": "complete",
        "details": {
            "SalesOrder": sales_order,
            "Customer": customer,
            "CreationDate": parse_date(order.get("CreationDate", "")),
            "OrderStatus": STATUS_MAP.get(order.get("OverallSDProcessStatus", ""), "Unknown"),
            "TotalNetAmount": order.get("TotalNetAmount"),
        },
    })

    # Stage 2: Items Confirmed
    line_details = []
    for i in order_items:
        mat = i.get("Material", "")
        pinfo = product_info.get(mat, {})
        line_details.append({
            "Item": i.get("SalesOrderItem"),
            "Material": mat,
            "ProductGroup": pinfo.get("ProductGroup", "N/A"),
            "Quantity": float(i.get("OrderQuantity", "0")),
            "NetAmount": float(i.get("NetAmount", "0")),
        })
    stages.append({
        "stage": "2_ITEMS_CONFIRMED",
        "status": "complete" if order_items else "blocked",
        "item_count": len(order_items),
        "details": line_details,
    })

    # Stage 3: Stock Availability
    all_available = True
    stock_details = []
    for i in order_items:
        mat = i.get("Material", "")
        ordered = float(i.get("OrderQuantity", "0"))
        available = stock_by_mat.get(mat, 0)
        can_fulfill = available >= ordered
        if not can_fulfill:
            all_available = False
        stock_details.append({
            "Material": mat,
            "Ordered": ordered,
            "Available": available,
            "CanFulfill": can_fulfill,
            "Shortfall": max(0, ordered - available),
        })
    stages.append({
        "stage": "3_STOCK_AVAILABILITY",
        "status": "complete" if all_available else "at_risk",
        "details": stock_details,
    })

    # Stage 4: Delivery
    if order_deliveries:
        del_details = []
        for d in order_deliveries:
            del_details.append({
                "DeliveryDocument": d.get("DeliveryDocument"),
                "DeliveryDate": parse_date(d.get("DeliveryDate", "")),
                "GoodsMovementStatus": DELIVERY_STATUS_MAP.get(d.get("OverallGoodsMovementStatus", ""), "Unknown"),
            })
        all_shipped = all(d.get("OverallGoodsMovementStatus") == "C" for d in order_deliveries)
        stages.append({
            "stage": "4_DELIVERY",
            "status": "complete" if all_shipped else "in_progress",
            "details": del_details,
        })
    else:
        stages.append({
            "stage": "4_DELIVERY",
            "status": "not_started",
            "details": "No delivery document created yet",
        })

    # Overall status
    blockers = [s for s in stages if s["status"] in ("blocked", "at_risk", "not_started")]

    stage_emoji = {"complete": "✅", "in_progress": "🟡", "at_risk": "🟠", "blocked": "❌", "not_started": "⚪"}
    stage_labels = {"1_ORDER_CREATED": "Order Created", "2_ITEMS_CONFIRMED": "Items Confirmed",
                    "3_STOCK_AVAILABILITY": "Stock Availability", "4_DELIVERY": "Delivery / Shipping"}
    insights = []
    for s in stages:
        label = stage_labels.get(s["stage"], s["stage"])
        emoji = stage_emoji.get(s["status"], "?")
        insights.append(f"{emoji} {label}: {s['status'].replace('_', ' ').title()}")
    if blockers:
        insights.append(f"\u26a0\ufe0f {len(blockers)} stage(s) need attention: {', '.join(stage_labels.get(b, b) for b in [s['stage'] for s in blockers])}")
    else:
        insights.append("All lifecycle stages completed \u2014 order is on track")
    recs = []
    for s in stages:
        if s["status"] == "at_risk":
            if s["stage"] == "3_STOCK_AVAILABILITY":
                shorts = [d for d in s.get("details", []) if isinstance(d, dict) and not d.get("CanFulfill")]
                if shorts:
                    recs.append(f"Procure materials: {', '.join(d['Material'] for d in shorts)}")
        if s["status"] == "not_started":
            if s["stage"] == "4_DELIVERY":
                recs.append("Create outbound delivery document to initiate shipping")
    req_date = parse_date(order.get("RequestedDeliveryDate", ""))
    e2e_summary = (
        f"Order {sales_order} for {customer} is valued at ${float(order.get('TotalNetAmount', '0')):,.2f}. "
        f"{len(stages) - len(blockers)} of {len(stages)} lifecycle stages are complete"
        + (f" — {len(blockers)} stage(s) have issues requiring attention." if blockers else " — order is progressing smoothly through the O2C cycle.")
    )
    narrative = _format_executive_output(
        title=f"End-to-End Order Tracking \u2014 SO {sales_order}",
        status="RED" if blockers else "GREEN",
        summary=e2e_summary,
        kpis=[
            ("Sales Order", sales_order),
            ("Customer", customer),
            ("Order Value", f"${float(order.get('TotalNetAmount', '0')):,.2f}"),
            ("Requested Delivery", req_date or "N/A"),
            ("Lifecycle Stages", f"{len(stages) - len(blockers)}/{len(stages)} complete"),
        ],
        table_headers=["Stage", "Status", "Indicator"],
        table_rows=[
            [stage_labels.get(s["stage"], s["stage"]), s["status"].replace("_", " ").title(), stage_emoji.get(s["status"], "?")]
            for s in stages
        ],
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 9: Unfulfilled Orders Report ────────────────────────────────────────

def get_unfulfilled_orders_report() -> dict:
    """Identify open orders that have no delivery document created yet.

    These represent fulfillment gaps — orders the customer is waiting for
    that haven't entered the shipping pipeline. Useful for operations teams
    to prioritize warehouse picking and for customer-facing teams to manage
    expectations.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader")
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")

    # Customers with deliveries
    customers_with_delivery = {d.get("SoldToParty") for d in deliveries}

    unfulfilled = []
    for o in orders:
        status = o.get("OverallSDProcessStatus", "")
        customer = o.get("SoldToParty", "")
        # Open order with no delivery for this customer
        if status == "A" and customer not in customers_with_delivery:
            so_id = o.get("SalesOrder", "")
            order_items = [i for i in items if i.get("SalesOrder") == so_id]
            unfulfilled.append({
                "SalesOrder": so_id,
                "Customer": customer,
                "TotalNetAmount": float(o.get("TotalNetAmount", "0")),
                "RequestedDeliveryDate": o.get("RequestedDeliveryDate", ""),
                "ItemCount": len(order_items),
                "Materials": [i.get("Material") for i in order_items],
            })

    total_value = sum(u["TotalNetAmount"] for u in unfulfilled)

    insights = []
    if unfulfilled:
        insights.append(f"{len(unfulfilled)} open order(s) worth ${total_value:,.2f} have no delivery document")
        for u in unfulfilled:
            insights.append(f"SO {u['SalesOrder']} ({u['Customer']}): ${u['TotalNetAmount']:,.2f} \u2014 {u['ItemCount']} items, materials: {', '.join(u['Materials'])}")
        insights.append("These orders are stalled in the pipeline \u2014 customers waiting with no shipping in progress")
    else:
        insights.append("All open orders have corresponding delivery documents \u2014 fulfillment pipeline is active")
    recs = []
    if unfulfilled:
        recs.append(f"Create delivery documents immediately for: {', '.join(u['SalesOrder'] for u in unfulfilled)}")
        recs.append(f"Total value at risk: ${total_value:,.2f} \u2014 prioritize by order value")
        recs.append("Notify affected customers with updated delivery timelines")
    unf_summary = (
        f"{len(unfulfilled)} open order(s) worth ${total_value:,.2f} have no delivery document created — "
        f"these are stalled in the pipeline with customers waiting. Immediate warehouse action is required."
    ) if unfulfilled else (
        "All open orders have corresponding delivery documents. The fulfillment pipeline is active with no gaps."
    )
    narrative = _format_executive_output(
        title="Unfulfilled Orders Report",
        status="RED" if unfulfilled else "GREEN",
        summary=unf_summary,
        kpis=[
            ("Unfulfilled Orders", str(len(unfulfilled))),
            ("Value at Risk", f"${total_value:,.2f}"),
            ("Affected Customers", str(len(set(u['Customer'] for u in unfulfilled))) if unfulfilled else "0"),
        ],
        table_headers=["Order", "Customer", "Value", "Items", "Materials"],
        table_rows=[
            [u["SalesOrder"], u["Customer"], f"${u['TotalNetAmount']:,.2f}",
             str(u["ItemCount"]), ", ".join(u["Materials"])]
            for u in unfulfilled
        ] if unfulfilled else None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 10: Inventory Turnover / Fast-Slow Mover Analysis ───────────────────

def get_inventory_turnover_analysis() -> dict:
    """Analyze inventory efficiency by comparing stock levels against demand.

    Classifies each material as a fast mover, slow mover, or overstocked
    based on the ratio of total demand to available stock. Helps warehouse
    managers optimize stock levels and procurement teams adjust purchasing.
    """
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")
    if items and "error" in items[0]:
        return {"error": f"Failed to fetch order items: {items[0]['error']}"}

    stock = _get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    products = _get("API_PRODUCT_SRV", "A_Product")

    product_info = {p.get("Product"): p for p in products}

    # Aggregate demand per material
    demand: dict[str, float] = {}
    for i in items:
        mat = i.get("Material", "")
        demand[mat] = demand.get(mat, 0) + float(i.get("OrderQuantity", "0"))

    # Stock lookup
    stock_levels: dict[str, float] = {}
    for s in stock:
        mat = s.get("Material", "")
        stock_levels[mat] = stock_levels.get(mat, 0) + float(s.get("MatlWrhsStkQtyInMatlBaseUnit", "0"))

    all_materials = set(demand.keys()) | set(stock_levels.keys())
    analysis = []
    for mat in sorted(all_materials):
        d = demand.get(mat, 0)
        s = stock_levels.get(mat, 0)
        ratio = d / s if s > 0 else float("inf") if d > 0 else 0

        if ratio > 1:
            classification = "FAST_MOVER_UNDERSTOCKED"
        elif ratio > 0.5:
            classification = "FAST_MOVER"
        elif ratio > 0.1:
            classification = "MODERATE"
        elif d == 0:
            classification = "DEAD_STOCK"
        else:
            classification = "SLOW_MOVER_OVERSTOCKED"

        pinfo = product_info.get(mat, {})
        analysis.append({
            "material": mat,
            "product_group": pinfo.get("ProductGroup", "N/A"),
            "total_demand": d,
            "current_stock": s,
            "demand_to_stock_ratio": round(ratio, 2) if ratio != float("inf") else "infinite",
            "classification": classification,
        })

    fast = [a for a in analysis if "FAST" in a["classification"]]
    slow = [a for a in analysis if "SLOW" in a["classification"] or "DEAD" in a["classification"]]
    understocked = [a for a in analysis if a["classification"] == "FAST_MOVER_UNDERSTOCKED"]
    moderate = [a for a in analysis if a["classification"] == "MODERATE"]

    class_emoji = {"FAST_MOVER_UNDERSTOCKED": "🔴", "FAST_MOVER": "🟢", "MODERATE": "🟡", "SLOW_MOVER_OVERSTOCKED": "🟠", "DEAD_STOCK": "⚫"}

    table_rows = [
        [a["material"], a["product_group"], f"{a['total_demand']:,.0f}", f"{a['current_stock']:,.0f}",
         str(a["demand_to_stock_ratio"]),
         f"{class_emoji.get(a['classification'], '?')} {a['classification'].replace('_', ' ').title()}"]
        for a in analysis
    ]

    insights = []
    if analysis:
        insights.append(f"{len(fast)} fast-moving material(s), {len(moderate)} moderate, {len(slow)} slow/dead stock")
        if understocked:
            insights.append(f"\u26a0\ufe0f {len(understocked)} material(s) critically understocked: {', '.join(a['material'] for a in understocked)}")
            for a in understocked:
                insights.append(f"  {a['material']}: demand {a['total_demand']:,.0f} vs stock {a['current_stock']:,.0f} (ratio: {a['demand_to_stock_ratio']})")
        dead = [a for a in analysis if a["classification"] == "DEAD_STOCK"]
        if dead:
            insights.append(f"{len(dead)} dead-stock material(s) with zero demand — consider liquidation: {', '.join(a['material'] for a in dead)}")
    else:
        insights.append("No inventory data available.")

    recs = []
    if understocked:
        recs.append(f"Urgently restock: {', '.join(a['material'] for a in understocked)}")
    dead = [a for a in analysis if a["classification"] == "DEAD_STOCK"]
    if dead:
        recs.append(f"Review dead stock for write-off or liquidation: {', '.join(a['material'] for a in dead)}")
    if slow:
        recs.append("Reduce procurement for slow movers to free working capital")

    inv_labels = [a["material"] for a in analysis]
    inv_demand = [a["total_demand"] for a in analysis]
    inv_stock = [a["current_stock"] for a in analysis]
    cat_labels = ["Fast Movers", "Moderate", "Slow / Dead"]
    cat_counts = [len(fast), len(moderate), len(slow)]
    inv_charts = []
    if inv_labels:
        inv_charts = [
            _stacked_bar(
                inv_labels,
                [
                    {"label": "Current Stock", "data": inv_stock, "backgroundColor": STOCK_COLOR},
                    {"label": "Demand", "data": inv_demand, "backgroundColor": DEMAND_COLOR},
                ],
                caption="Stock Efficiency Spectrum — stock vs demand for each material, highlights overstock and understock."
            ),
            _pie_chart(
                cat_labels,
                [c / len(analysis) * 100 for c in cat_counts] if analysis else cat_counts,
                "Turnover Classification",
                caption="Working Capital Exposure — proportion of fast, moderate, and slow/dead stock reveals inventory health."
            ),
        ]

    inv_summary = (
        f"{len(analysis)} materials analyzed: {len(fast)} fast movers, {len(moderate)} moderate, {len(slow)} slow/dead stock. "
        + (f"{len(understocked)} material(s) critically understocked — demand exceeds supply." if understocked else "No critical understocking detected.")
    ) if analysis else "No inventory data available."

    narrative = _format_executive_output(
        title="Inventory Turnover Analysis",
        status="RED" if understocked else ("AMBER" if slow else "GREEN"),
        summary=inv_summary,
        kpis=[
            ("Materials", str(len(analysis))),
            ("Fast Movers", str(len(fast))),
            ("Slow / Dead", str(len(slow))),
            ("Critically Short", str(len(understocked))),
        ],
        table_headers=["Material", "Group", "Demand", "Stock", "D/S Ratio", "Classification"],
        table_rows=table_rows,
        charts=inv_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 11: Customer Delivery Performance KPIs ──────────────────────────────

def get_customer_delivery_performance() -> dict:
    """Measure delivery performance per customer — on-time rate, completion
    status, and orders still awaiting delivery.

    Cross-references sales orders, delivery documents, and their statuses
    to produce customer-level logistics KPIs.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader")

    import re
    def parse_epoch(ds):
        m = re.search(r"/Date\((\d+)\)/", ds or "")
        return int(m.group(1)) if m else None

    # Build delivery lookup by customer
    del_by_cust: dict[str, list[dict]] = {}
    for d in deliveries:
        cust = d.get("SoldToParty", "")
        del_by_cust.setdefault(cust, []).append(d)

    DELIVERY_STATUS = {"A": "Not Processed", "B": "Partial", "C": "Complete"}
    customers: dict[str, dict] = {}

    for o in orders:
        cust = o.get("SoldToParty", "")
        if cust not in customers:
            customers[cust] = {
                "customer": cust,
                "total_orders": 0,
                "orders_with_delivery": 0,
                "orders_without_delivery": 0,
                "deliveries_complete": 0,
                "deliveries_pending": 0,
                "on_time_count": 0,
                "late_count": 0,
            }
        customers[cust]["total_orders"] += 1

        cust_dels = del_by_cust.get(cust, [])
        if cust_dels:
            customers[cust]["orders_with_delivery"] += 1
            for d in cust_dels:
                gs = d.get("OverallGoodsMovementStatus", "")
                if gs == "C":
                    customers[cust]["deliveries_complete"] += 1
                else:
                    customers[cust]["deliveries_pending"] += 1

                # On-time check
                req_ms = parse_epoch(o.get("RequestedDeliveryDate", ""))
                del_ms = parse_epoch(d.get("DeliveryDate", ""))
                if req_ms and del_ms:
                    if del_ms <= req_ms:
                        customers[cust]["on_time_count"] += 1
                    else:
                        customers[cust]["late_count"] += 1
        else:
            customers[cust]["orders_without_delivery"] += 1

    # Compute rates
    for c in customers.values():
        total_evaluated = c["on_time_count"] + c["late_count"]
        c["on_time_rate"] = f"{(c['on_time_count'] / total_evaluated * 100):.0f}%" if total_evaluated else "N/A"
        c["fulfillment_rate"] = f"{(c['orders_with_delivery'] / c['total_orders'] * 100):.0f}%" if c["total_orders"] else "N/A"

    result = sorted(customers.values(), key=lambda c: c["total_orders"], reverse=True)

    total_orders_all = sum(c["total_orders"] for c in result)
    total_on_time = sum(c["on_time_count"] for c in result)
    total_late = sum(c["late_count"] for c in result)
    overall_rate = (total_on_time / (total_on_time + total_late) * 100) if (total_on_time + total_late) else 0
    insights = [
        f"Overall on-time delivery rate: {overall_rate:.0f}% across {len(result)} customers",
        f"Total deliveries evaluated: {total_on_time + total_late} ({total_on_time} on-time, {total_late} late)",
    ]
    no_delivery = [c for c in result if c["orders_without_delivery"] > 0]
    if no_delivery:
        insights.append(f"{len(no_delivery)} customer(s) have orders without delivery documents")
    perfect = [c for c in result if c["on_time_rate"] == "100%" and c["on_time_count"] > 0]
    if perfect:
        insights.append(f"{len(perfect)} customer(s) at 100% on-time rate")
    recs = []
    if overall_rate < 80:
        recs.append(f"On-time rate {overall_rate:.0f}% is below 80% target \u2014 review logistics processes")
    if no_delivery:
        recs.append(f"Create deliveries for: {', '.join(c['customer'] for c in no_delivery)}")
    cdp_summary = (
        f"Delivery performance across {len(result)} customer(s) stands at {overall_rate:.0f}% on-time rate "
        f"({total_on_time} on-time, {total_late} late). "
        + (f"{len(no_delivery)} customer(s) have orders without any delivery document — fulfillment gaps exist." if no_delivery else "All customers have active delivery documents.")
    )
    narrative = _format_executive_output(
        title="Customer Delivery Performance KPIs",
        status="GREEN" if overall_rate >= 80 else ("AMBER" if overall_rate >= 60 else "RED"),
        summary=cdp_summary,
        kpis=[
            ("Total Customers", str(len(result))),
            ("Overall On-Time Rate", f"{overall_rate:.0f}%"),
            ("On-Time Deliveries", str(total_on_time)),
            ("Late Deliveries", str(total_late)),
            ("Customers Missing Deliveries", str(len(no_delivery))),
        ],
        table_headers=["Customer", "Orders", "With Delivery", "Without", "On-Time", "Late", "OT Rate", "Fulfillment"],
        table_rows=[
            [c["customer"], str(c["total_orders"]), str(c["orders_with_delivery"]),
             str(c["orders_without_delivery"]), str(c["on_time_count"]), str(c["late_count"]),
             c["on_time_rate"], c["fulfillment_rate"]]
            for c in result
        ],
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 12: Order Value Analysis ────────────────────────────────────────────

def get_order_value_analysis() -> dict:
    """Financial analysis of sales order values across the portfolio.

    Computes average order value, identifies highest and lowest value orders,
    shows value distribution, and breaks down revenue by order status.
    Useful for finance teams and sales managers.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    STATUS_LABELS = {"A": "Open / In Process", "B": "Partially Delivered", "C": "Completed", "": "Unknown ()"}
    values = []
    by_status: dict[str, dict] = {}

    for o in orders:
        amt = float(o.get("TotalNetAmount", "0"))
        status = o.get("OverallSDProcessStatus", "")
        values.append(amt)

        if status not in by_status:
            by_status[status] = {"status": STATUS_LABELS.get(status, status or "Unknown"), "count": 0, "total": 0.0}
        by_status[status]["count"] += 1
        by_status[status]["total"] += amt

    values.sort()
    total = sum(values)
    avg = total / len(values) if values else 0

    order_list = sorted(
        [{"SalesOrder": o.get("SalesOrder"), "Customer": o.get("SoldToParty"),
          "Amount": float(o.get("TotalNetAmount", "0")), "Status": o.get("OverallSDProcessStatus")}
         for o in orders],
        key=lambda x: x["Amount"], reverse=True,
    )

    STATUS_LABELS_DISP = {"A": "Open / In Process", "B": "Partially Delivered", "C": "Completed"}
    median_val = values[len(values) // 2] if values else 0

    table_rows = [
        [str(i+1), o["SalesOrder"], o["Customer"], f"${o['Amount']:,.2f}",
         f"{'+' if o['Amount'] >= avg else ''}{((o['Amount']-avg)/avg*100):.0f}%" if avg else "N/A",
         STATUS_LABELS_DISP.get(o["Status"], o["Status"])]
        for i, o in enumerate(order_list)
    ]

    insights = []
    if order_list:
        highest = order_list[0]
        lowest = order_list[-1]
        insights.append(f"Highest: SO {highest['SalesOrder']} ({highest['Customer']}) at ${highest['Amount']:,.2f} — {highest['Amount']/total*100:.1f}% of total")
        insights.append(f"Lowest: SO {lowest['SalesOrder']} ({lowest['Customer']}) at ${lowest['Amount']:,.2f}")
        if len(order_list) > 1:
            spread_ratio = highest["Amount"] / lowest["Amount"] if lowest["Amount"] else float("inf")
            insights.append(f"Value spread: {spread_ratio:.1f}x between highest and lowest orders")
    if values:
        insights.append(f"Total portfolio: {len(values)} orders worth ${total:,.2f}")
        insights.append(f"Average order value: ${avg:,.2f} | Median: ${median_val:,.2f}")
    for s_data in by_status.values():
        insights.append(f"{s_data['status']}: {s_data['count']} orders, ${s_data['total']:,.2f} ({s_data['total']/total*100:.1f}% of revenue)" if total else f"{s_data['status']}: {s_data['count']} orders")

    recs = []
    above_avg = [o for o in order_list if o["Amount"] > avg]
    if above_avg:
        recs.append(f"{len(above_avg)} orders above average value — prioritize these for fulfillment")
    open_by_status = by_status.get("A")
    if open_by_status:
        recs.append(f"${open_by_status['total']:,.2f} in open pipeline — expedite to convert to revenue")

    ov_labels = [f"SO {o['SalesOrder']}" for o in order_list[:10]]
    ov_data = [o['Amount'] for o in order_list[:10]]
    ov_status_labels = list(by_status.keys())
    ov_status_totals = [by_status[k]["total"] for k in ov_status_labels]
    ov_status_names = [by_status[k]["status"] for k in ov_status_labels]
    ov_charts = []
    if ov_labels:
        ov_charts = [
            _bar_chart(
                ov_labels, ov_data, "Order Value ($)",
                caption="Value Distribution — order value ranking spotlights high-value concentration and outliers."
            ),
            _pie_chart(
                ov_status_names,
                [v / total * 100 for v in ov_status_totals] if total else ov_status_totals,
                "Value by Status",
                caption="Pipeline Conversion Health — share of value by order status reveals pipeline maturity."
            ) if ov_status_labels else None,
        ]
        ov_charts = [c for c in ov_charts if c is not None]

    val_summary = (
        f"{len(values)} orders totaling ${total:,.2f}. "
        f"Average order value: ${avg:,.2f}, median: ${median_val:,.2f}. "
        + (f"Highest order (SO {order_list[0]['SalesOrder']}) at ${order_list[0]['Amount']:,.2f} represents {order_list[0]['Amount']/total*100:.1f}% of portfolio." if order_list and total else "")
    ) if values else "No order data available."

    narrative = _format_executive_output(
        title="Order Value Analysis",
        summary=val_summary,
        kpis=[
            ("Total Orders", str(len(values))),
            ("Total Value", f"${total:,.2f}"),
            ("Avg Order", f"${avg:,.2f}"),
            ("Median Order", f"${median_val:,.2f}"),
        ],
        table_headers=["Rank", "Order", "Customer", "Value", "vs Avg", "Status"],
        table_rows=table_rows,
        charts=ov_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 13: Material Availability Matrix ────────────────────────────────────

def get_material_availability_matrix() -> dict:
    """Comprehensive material availability view across the entire supply chain.

    For each material: shows product master info, current stock, total demand
    from all orders, which orders use it, and net availability. This is the
    single source of truth for material planning.
    """
    products = _get("API_PRODUCT_SRV", "A_Product")
    stock = _get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")

    order_status = {o.get("SalesOrder"): o.get("OverallSDProcessStatus") for o in orders}
    product_info = {p.get("Product"): p for p in products}

    # Stock by material
    stock_map: dict[str, dict] = {}
    for s in stock:
        mat = s.get("Material", "")
        stock_map[mat] = {
            "stock_qty": float(s.get("MatlWrhsStkQtyInMatlBaseUnit", "0")),
            "plant": s.get("Plant"),
            "storage_location": s.get("StorageLocation"),
        }

    # Demand by material — split by open vs all
    demand_all: dict[str, float] = {}
    demand_open: dict[str, float] = {}
    mat_orders: dict[str, list] = {}
    for i in items:
        mat = i.get("Material", "")
        qty = float(i.get("OrderQuantity", "0"))
        so = i.get("SalesOrder", "")
        demand_all[mat] = demand_all.get(mat, 0) + qty
        mat_orders.setdefault(mat, []).append(so)
        if order_status.get(so) == "A":
            demand_open[mat] = demand_open.get(mat, 0) + qty

    all_mats = set(product_info.keys()) | set(stock_map.keys()) | set(demand_all.keys())
    matrix = []
    for mat in sorted(all_mats):
        pinfo = product_info.get(mat, {})
        sinfo = stock_map.get(mat, {})
        stk = sinfo.get("stock_qty", 0)
        open_dem = demand_open.get(mat, 0)
        total_dem = demand_all.get(mat, 0)
        matrix.append({
            "material": mat,
            "product_group": pinfo.get("ProductGroup", "N/A"),
            "weight_kg": float(pinfo.get("GrossWeight", "0")),
            "plant": sinfo.get("plant", "N/A"),
            "current_stock": stk,
            "open_order_demand": open_dem,
            "total_demand_all_orders": total_dem,
            "net_available_for_open": stk - open_dem,
            "status": "SUFFICIENT" if stk >= open_dem else "SHORTFALL",
            "used_in_orders": sorted(set(mat_orders.get(mat, []))),
        })

    shortfalls = [m for m in matrix if m["status"] == "SHORTFALL"]
    sufficient = [m for m in matrix if m["status"] == "SUFFICIENT"]

    insights = [
        f"{len(sufficient)} material(s) have sufficient stock, {len(shortfalls)} have shortfalls",
    ]
    if shortfalls:
        total_gap = sum(abs(m["net_available_for_open"]) for m in shortfalls)
        insights.append(f"Total shortage: {total_gap:,.0f} units across {len(shortfalls)} materials")
        for m in shortfalls:
            insights.append(f"\u26a0\ufe0f {m['material']}: need {m['open_order_demand']:,.0f}, have {m['current_stock']:,.0f} \u2014 gap of {abs(m['net_available_for_open']):,.0f} units")
    else:
        insights.append("Supply chain is healthy \u2014 all open order demand covered by current inventory")
    no_demand = [m for m in matrix if m["total_demand_all_orders"] == 0 and m["current_stock"] > 0]
    if no_demand:
        insights.append(f"{len(no_demand)} material(s) in stock with zero demand \u2014 potential dead stock")
    recs = []
    if shortfalls:
        recs.append(f"Procure immediately: {', '.join(m['material'] for m in shortfalls)}")
        recs.append(f"Affected orders: {', '.join(sorted(set(o for m in shortfalls for o in m['used_in_orders'])))}")
    if no_demand:
        recs.append(f"Review for liquidation: {', '.join(m['material'] for m in no_demand)}")
    mat_summary = (
        f"{len(matrix)} material(s) in the supply chain: {len(sufficient)} have sufficient stock, "
        f"{len(shortfalls)} have shortfalls against open order demand"
        + (f", and {len(no_demand)} have zero demand (potential dead stock)." if no_demand else ".")
        + (f" Procurement action required for {', '.join(m['material'] for m in shortfalls)}." if shortfalls else " Supply chain is healthy.")
    )
    narrative = _format_executive_output(
        title="Material Availability Matrix",
        status="RED" if shortfalls else "GREEN",
        summary=mat_summary,
        kpis=[
            ("Total Materials", str(len(matrix))),
            ("Sufficient Stock", str(len(sufficient))),
            ("Shortfall", str(len(shortfalls))),
            ("Zero Demand (Dead Stock)", str(len(no_demand))),
        ],
        table_headers=["Material", "Group", "Stock", "Open Demand", "Net Avail", "Status"],
        table_rows=[
            [m["material"], m["product_group"], f"{m['current_stock']:,.0f}",
             f"{m['open_order_demand']:,.0f}", f"{m['net_available_for_open']:,.0f}",
             "🔴 SHORTFALL" if m["status"] == "SHORTFALL" else "🟢 OK"]
            for m in matrix
        ],
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 14: Open Order Aging ────────────────────────────────────────────────

def get_open_order_aging() -> dict:
    """Analyze how long open orders have been sitting without completion.

    Computes aging in days from creation date to today for all open orders.
    Classifies orders as new (<7 days), normal (7-30 days), aging (30-60),
    or critical (>60 days). Helps management identify stuck orders.
    """
    import re
    from datetime import datetime, timezone

    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    if orders and "error" in orders[0]:
        return {"error": f"Failed to fetch sales orders: {orders[0]['error']}"}

    now = datetime.now(tz=timezone.utc)
    aging_results = []

    for o in orders:
        if o.get("OverallSDProcessStatus") != "A":
            continue

        so_id = o.get("SalesOrder", "")
        creation_str = o.get("CreationDate", "")
        m = re.search(r"/Date\((\d+)\)/", creation_str)
        if not m:
            continue

        created = datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc)
        age_days = (now - created).days

        if age_days < 7:
            bucket = "NEW"
        elif age_days < 30:
            bucket = "NORMAL"
        elif age_days < 60:
            bucket = "AGING"
        else:
            bucket = "CRITICAL"

        aging_results.append({
            "SalesOrder": so_id,
            "Customer": o.get("SoldToParty", ""),
            "TotalNetAmount": float(o.get("TotalNetAmount", "0")),
            "CreationDate": created.strftime("%Y-%m-%d"),
            "AgeDays": age_days,
            "Bucket": bucket,
        })

    aging_results.sort(key=lambda x: x["AgeDays"], reverse=True)

    buckets = {}
    for a in aging_results:
        b = a["Bucket"]
        if b not in buckets:
            buckets[b] = {"count": 0, "total_value": 0.0}
        buckets[b]["count"] += 1
        buckets[b]["total_value"] += a["TotalNetAmount"]

    bucket_order = ["NEW", "NORMAL", "AGING", "CRITICAL"]
    bucket_emoji = {"NEW": "🟢", "NORMAL": "🟡", "AGING": "🟠", "CRITICAL": "🔴"}
    total_value = sum(a["TotalNetAmount"] for a in aging_results)
    critical = [a for a in aging_results if a["Bucket"] == "CRITICAL"]
    aging_orders = [a for a in aging_results if a["Bucket"] == "AGING"]

    table_rows = [
        [a["SalesOrder"], a["Customer"], f"${a['TotalNetAmount']:,.2f}",
         a["CreationDate"], str(a["AgeDays"]),
         f"{bucket_emoji.get(a['Bucket'], '?')} {a['Bucket']}"]
        for a in aging_results
    ]

    insights = []
    if aging_results:
        avg_age = sum(a["AgeDays"] for a in aging_results) / len(aging_results)
        insights.append(f"{len(aging_results)} open orders worth ${total_value:,.2f} total")
        oldest = aging_results[0]
        insights.append(f"Oldest order: SO {oldest['SalesOrder']} ({oldest['Customer']}) — {oldest['AgeDays']} days old, ${oldest['TotalNetAmount']:,.2f}")
        if critical:
            insights.append(f"\u26a0\ufe0f {len(critical)} CRITICAL order(s) over 60 days — immediate escalation needed")
        if aging_orders:
            insights.append(f"{len(aging_orders)} order(s) in AGING bracket (30-60 days) — at risk of becoming critical")
        insights.append(f"Average order age: {avg_age:.1f} days")
    else:
        avg_age = 0
        insights.append("No open orders in the system — pipeline is clear")

    recs = []
    if critical:
        recs.append("Escalate immediately: " + ", ".join(f"SO {a['SalesOrder']}" for a in critical))
    if aging_orders:
        recs.append("Review aging orders before they go critical: " + ", ".join(f"SO {a['SalesOrder']}" for a in aging_orders))
    if aging_results:
        recs.append("Set up automated alerts for orders approaching 30-day and 60-day thresholds")

    bucket_counts = [buckets.get(b, {"count": 0})["count"] for b in bucket_order]
    aging_charts = []
    if any(bucket_counts):
        aging_charts = [
            _pie_chart(bucket_order, bucket_counts, "Order Aging Buckets", caption="Aging Risk Distribution — open orders by aging bucket reveals stuck pipeline value."),
        ]

    aging_summary = (
        f"{len(aging_results)} open orders worth ${total_value:,.2f} with average age of {avg_age:.1f} days. "
        + (f"{len(critical)} order(s) are critical (>60 days) requiring immediate escalation." if critical else "No critical aging detected.")
    ) if aging_results else "No open orders — pipeline is clear."

    narrative = _format_executive_output(
        title="Open Order Aging Analysis",
        status="RED" if critical else ("AMBER" if aging_orders else "GREEN"),
        summary=aging_summary,
        kpis=[
            ("Open Orders", str(len(aging_results))),
            ("Total Value", f"${total_value:,.2f}"),
            ("Critical (>60d)", str(len(critical))),
            ("Avg Age", f"{avg_age:.1f} days"),
        ],
        table_headers=["Order", "Customer", "Value", "Created", "Age (days)", "Bucket"],
        table_rows=table_rows,
        charts=aging_charts or None,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


# ── Tool 15: O2C Process Health Dashboard ────────────────────────────────────

def get_process_bottleneck_summary() -> dict:
    """Executive-level O2C process health dashboard.

    Scans every stage of the Order-to-Cash process and identifies bottlenecks:
    - Orders without items
    - Materials with stock shortfalls
    - Orders without deliveries
    - Deliveries not yet shipped
    Returns a RAG (Red/Amber/Green) status for each stage.
    """
    orders = _get("API_SALES_ORDER_SRV", "A_SalesOrder")
    items = _get("API_SALES_ORDER_SRV", "A_SalesOrderItem")
    stock = _get("API_MATERIAL_STOCK_SRV", "A_MatlStkInAcctMod")
    deliveries = _get("API_OUTBOUND_DELIVERY_SRV", "A_OutbDeliveryHeader")

    open_orders = [o for o in orders if o.get("OverallSDProcessStatus") == "A"]
    open_ids = {o.get("SalesOrder") for o in open_orders}
    open_customers = {o.get("SoldToParty") for o in open_orders}
    total_open_value = sum(float(o.get("TotalNetAmount", "0")) for o in open_orders)

    # Stage 1: Order Pipeline
    order_stage = {
        "stage": "ORDER_PIPELINE",
        "total_orders": len(orders),
        "open_orders": len(open_orders),
        "open_value": total_open_value,
    }
    # Stage 2: Stock Availability
    open_items = [i for i in items if i.get("SalesOrder") in open_ids]
    demand: dict[str, float] = {}
    for i in open_items:
        mat = i.get("Material", "")
        demand[mat] = demand.get(mat, 0) + float(i.get("OrderQuantity", "0"))

    stock_map: dict[str, float] = {}
    for s in stock:
        mat = s.get("Material", "")
        stock_map[mat] = stock_map.get(mat, 0) + float(s.get("MatlWrhsStkQtyInMatlBaseUnit", "0"))

    shortfalls = []
    for mat, dem in demand.items():
        avail = stock_map.get(mat, 0)
        if dem > avail:
            shortfalls.append({"material": mat, "demand": dem, "stock": avail, "gap": dem - avail})

    stock_stage = {
        "stage": "STOCK_AVAILABILITY",
        "materials_needed": len(demand),
        "materials_short": len(shortfalls),
        "shortfall_details": shortfalls,
    }
    # Stage 3: Delivery Creation
    customers_with_delivery = {d.get("SoldToParty") for d in deliveries}
    customers_missing_delivery = open_customers - customers_with_delivery

    delivery_stage = {
        "stage": "DELIVERY_CREATION",
        "open_customers": len(open_customers),
        "with_delivery": len(open_customers & customers_with_delivery),
        "without_delivery": len(customers_missing_delivery),
        "missing_for_customers": sorted(customers_missing_delivery),
    }
    # Stage 4: Shipping / Goods Movement
    pending_deliveries = [d for d in deliveries if d.get("OverallGoodsMovementStatus") != "C"]
    complete_deliveries = [d for d in deliveries if d.get("OverallGoodsMovementStatus") == "C"]

    shipping_stage = {
        "stage": "SHIPPING",
        "total_deliveries": len(deliveries),
        "shipped": len(complete_deliveries),
        "pending": len(pending_deliveries),
    }

    stages = [order_stage, stock_stage, delivery_stage, shipping_stage]
    rag_counts = {"RED": 0, "AMBER": 0, "GREEN": 0}
    rag_emoji = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}
    stage_labels = {"ORDER_PIPELINE": "Order Pipeline", "STOCK_AVAILABILITY": "Stock Availability",
                    "DELIVERY_CREATION": "Delivery Creation", "SHIPPING": "Shipping / Goods Movement"}

    # RAG status for each stage
    for s in stages:
        if s["stage"] == "ORDER_PIPELINE":
            s["rag"] = "GREEN" if s["open_orders"] == 0 else "AMBER"
            s["note"] = "No open orders — pipeline clear" if s["open_orders"] == 0 else f"{s['open_orders']} open order(s) worth ${s['open_value']:,.2f}"
        elif s["stage"] == "STOCK_AVAILABILITY":
            if s["materials_short"] == 0:
                s["rag"] = "GREEN"
                s["note"] = "All materials in stock for open orders"
            elif s["materials_short"] <= 1:
                s["rag"] = "AMBER"
                s["note"] = f"{s['materials_short']} material(s) with shortfall"
            else:
                s["rag"] = "RED"
                s["note"] = f"{s['materials_short']} material(s) critically short"
        elif s["stage"] == "DELIVERY_CREATION":
            if s["without_delivery"] == 0:
                s["rag"] = "GREEN"
                s["note"] = "All open-order customers have deliveries"
            else:
                s["rag"] = "RED"
                s["note"] = f"{s['without_delivery']} customer(s) awaiting delivery creation"
        elif s["stage"] == "SHIPPING":
            if s["pending"] == 0:
                s["rag"] = "GREEN"
                s["note"] = "All deliveries shipped"
            else:
                s["rag"] = "AMBER"
                s["note"] = f"{s['pending']} delivery(ies) pending shipment"
        rag_counts[s["rag"]] = rag_counts.get(s["rag"], 0) + 1

    if rag_counts["RED"] > 0:
        overall = "RED"
    elif rag_counts["AMBER"] > 0:
        overall = "AMBER"
    else:
        overall = "GREEN"

    insights = [
        f"Overall O2C health: {rag_emoji.get(overall, '?')} {overall} — {rag_counts['RED']} red, {rag_counts['AMBER']} amber, {rag_counts['GREEN']} green",
    ]
    for s in stages:
        insights.append(f"{rag_emoji.get(s['rag'], '?')} {stage_labels.get(s['stage'], s['stage'])}: {s['note']}")
    red_stages = [s for s in stages if s["rag"] == "RED"]
    if red_stages:
        insights.append(f"\u26a0\ufe0f Critical bottlenecks in: {', '.join(stage_labels.get(s['stage'], s['stage']) for s in red_stages)}")

    recs = []
    for s in stages:
        if s["rag"] == "RED":
            if s["stage"] == "STOCK_AVAILABILITY" and s.get("shortfall_details"):
                recs.append(f"Procure materials: {', '.join(sf['material'] for sf in s['shortfall_details'])}")
            elif s["stage"] == "DELIVERY_CREATION" and s.get("missing_for_customers"):
                recs.append(f"Create deliveries for: {', '.join(s['missing_for_customers'])}")
        elif s["rag"] == "AMBER":
            if s["stage"] == "SHIPPING":
                recs.append(f"Expedite {s.get('pending', 0)} pending shipment(s)")
            elif s["stage"] == "ORDER_PIPELINE":
                recs.append(f"Review {s.get('open_orders', 0)} open orders for completion readiness")

    rag_labels = [stage_labels.get(s["stage"], s["stage"]) for s in stages]
    rag_colors = [RAG.get(s["rag"], "#ccc") for s in stages]
    rag_values = [1 for _ in stages]
    rag_chart_cfg = {
        "type": "bar",
        "data": {"labels": rag_labels, "datasets": [{"data": rag_values, "backgroundColor": rag_colors}]},
        "options": {"legend": {"display": False}, "scales": {"yAxes": [{"display": False}]},
                    "plugins": {"datalabels": {"display": False}}},
    }
    rag_pie_labels = [k for k, v in rag_counts.items() if v > 0]
    rag_pie_data = [rag_counts[k] / 4 * 100 for k in rag_pie_labels]
    health_charts = [
        {"img": f"![O2C Health]({_chart_url(rag_chart_cfg, 260, 180)})", "caption": "Bar: RAG status by stage. Red = critical, amber = warning, green = healthy."},
        _pie_chart(
            rag_pie_labels,
            rag_pie_data,
            "Health Distribution",
            caption="O2C Stage Health — distribution of health status across order-to-cash process stages."
        ),
    ]

    table_rows = [
        [stage_labels.get(s["stage"], s["stage"]),
         f"{rag_emoji.get(s['rag'], '?')} {s['rag']}",
         s.get("note", "")]
        for s in stages
    ]

    health_summary = (
        f"O2C process health is {overall}: {rag_counts['RED']} critical, {rag_counts['AMBER']} warning, {rag_counts['GREEN']} healthy stages. "
        + (f"Bottlenecks in {', '.join(stage_labels.get(s['stage'], s['stage']) for s in red_stages)}. " if red_stages else "")
        + f"Open pipeline value: ${order_stage.get('open_value', 0):,.2f}."
    )

    narrative = _format_executive_output(
        title="O2C Process Health Dashboard",
        status=overall,
        summary=health_summary,
        kpis=[
            ("Overall Health", f"{rag_emoji.get(overall, '?')} {overall}"),
            ("Red Stages", str(rag_counts["RED"])),
            ("Amber Stages", str(rag_counts["AMBER"])),
            ("Open Pipeline", f"${order_stage.get('open_value', 0):,.2f}"),
        ],
        table_headers=["Stage", "Status", "Details"],
        table_rows=table_rows,
        charts=health_charts,
        insights=insights,
        recommendations=recs or None,
    )

    return {"executive_narrative": narrative}


def _build_conclusion(risk_assessment: list[dict], at_risk_orders: list[dict]) -> str:
    at_risk_materials = [r for r in risk_assessment if r["AtRisk"]]
    if not at_risk_materials:
        return "All open orders can be fulfilled with current stock levels."

    lines = ["The following materials have insufficient stock:"]
    for r in at_risk_materials:
        lines.append(
            f"- {r['Material']}: need {r['TotalDemand']:.0f}, "
            f"have {r['AvailableStock']:.0f}, "
            f"shortfall of {r['Shortfall']:.0f} units"
        )
    affected = set(o["SalesOrder"] for o in at_risk_orders)
    lines.append(f"Affected orders: {', '.join(sorted(affected))}")
    return "\n".join(lines)
