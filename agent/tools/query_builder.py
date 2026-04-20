"""
Query Builder (QB) Tools for SAP OData — Order to Cash

These tools convert natural language SAP queries into proper OData v2 parameters
BEFORE calling the MCP/OData connector. This is the critical QB step that ensures
accurate filtering, sorting, and field selection.

Architecture: User Query → QB Tool → OData Params → MCP Tool → Analyst Synthesis

Each entity type has its own QB function with knowledge of:
- Filterable fields and their data types
- OData v2 syntax rules (string quoting, decimal handling, date format)
- ID handling patterns (eq for exact, substringof for partial)
- Default $select fields for optimal payload
- Default $orderby for meaningful sort
"""

import re


def _extract_patterns(question: str) -> dict:
    """Extract common patterns from natural language questions."""
    q = question.strip()
    q_lower = q.lower()

    patterns = {
        "order_ids": [],
        "customer_ids": [],
        "material_ids": [],
        "delivery_ids": [],
        "plant_ids": [],
        "statuses": [],
        "is_open": False,
        "is_closed": False,
        "is_partial": False,
        "amount_gt": None,
        "amount_lt": None,
        "top": 50,
    }

    # Order IDs: "order 10", "order 14", "SO 10", "sales order 10"
    for m in re.finditer(r'(?:order|SO)[- ]?(\d+)', q, re.IGNORECASE):
        patterns["order_ids"].append(m.group(1))

    # Customer IDs: "customer CUST-001", "CUST-001", "customer 17100001"
    # Pattern 1: "customer <ID>" or "customer <ID>" with space separator
    for m in re.finditer(r'customer\s+([\w-]+)', q, re.IGNORECASE):
        cid = m.group(1)
        if cid.lower() not in ('id', 'ids', 'name', 'names', 'data', 'the',
                                'for', 'in', 'with', 'and', 'or', 'is', 'are'):
            if cid not in patterns["customer_ids"]:
                patterns["customer_ids"].append(cid)
    # Pattern 2: standalone CUST-XXX (but NOT the word "customer" itself)
    for m in re.finditer(r'\bCUST[-_]\w+', q):
        cid = m.group(0)
        if cid not in patterns["customer_ids"]:
            patterns["customer_ids"].append(cid)

    # Material IDs: "material LAPTOP-01", "LAPTOP-01", "product MONITOR-24"
    # Require a space/hyphen separator to avoid matching "items" → "s"
    for m in re.finditer(r'(?:material|product)\s+([\w-]+)', q, re.IGNORECASE):
        mid = m.group(1)
        # Skip generic words
        if mid.lower() not in ('for', 'in', 'of', 'the', 'all', 'a', 'an',
                                'catalog', 'list', 'type', 'types', 'details',
                                'status', 'data', 'info', 'information',
                                'id', 'ids', 'name', 'names', 'number'):
            patterns["material_ids"].append(mid)
    # Also catch standalone product-like patterns (UPPERCASE-XX)
    for m in re.finditer(r'\b([A-Z][A-Z0-9]+-[A-Z0-9]+)\b', q):
        mid = m.group(1)
        if mid not in patterns["material_ids"] and mid not in patterns["customer_ids"]:
            patterns["material_ids"].append(mid)

    # Delivery IDs: "delivery 80000010", "delivery document 80000010"
    for m in re.finditer(r'(?:delivery|shipment)[- ]?(?:document[- ]?)?(\d{6,})', q, re.IGNORECASE):
        patterns["delivery_ids"].append(m.group(1))

    # Plant IDs: "plant 1000", "plant 1710"
    for m in re.finditer(r'plant[- ]?(\d{4})', q, re.IGNORECASE):
        patterns["plant_ids"].append(m.group(1))

    # Status detection
    if any(w in q_lower for w in ['open', 'active', 'pending', 'in process', 'in-process']):
        patterns["is_open"] = True
        patterns["statuses"].append("A")
    if any(w in q_lower for w in ['closed', 'completed', 'done', 'finished']):
        patterns["is_closed"] = True
        patterns["statuses"].append("C")
    if any(w in q_lower for w in ['partial', 'partially']):
        patterns["is_partial"] = True
        patterns["statuses"].append("B")

    # Amount thresholds: "over $10000", "greater than 5000", "above 10000"
    m = re.search(r'(?:over|above|greater than|more than|gt|>)\s*\$?([\d,]+)', q, re.IGNORECASE)
    if m:
        patterns["amount_gt"] = m.group(1).replace(',', '')
    m = re.search(r'(?:under|below|less than|lt|<)\s*\$?([\d,]+)', q, re.IGNORECASE)
    if m:
        patterns["amount_lt"] = m.group(1).replace(',', '')

    # Top/limit: "top 10", "first 5", "limit 20"
    m = re.search(r'(?:top|first|limit|show)\s+(\d+)', q, re.IGNORECASE)
    if m:
        patterns["top"] = min(int(m.group(1)), 100)

    return patterns


def build_sales_order_query(user_question: str) -> dict:
    """Convert natural language to OData v2 parameters for A_SalesOrder.

    Call this BEFORE calling sap_query_entity_set for sales orders.
    Returns a dict with keys: serviceName, entitySet, filter, top, orderby, select.
    Pass these values directly to sap_query_entity_set.

    Args:
        user_question: The user's natural language question about sales orders.

    Returns:
        Dict with OData parameters ready for sap_query_entity_set.
    """
    p = _extract_patterns(user_question)
    filters = []

    # Order ID filter (exact match)
    if p["order_ids"]:
        if len(p["order_ids"]) == 1:
            filters.append(f"SalesOrder eq '{p['order_ids'][0]}'")
        else:
            # Multiple orders: OR them
            or_parts = [f"SalesOrder eq '{oid}'" for oid in p["order_ids"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Customer filter
    if p["customer_ids"]:
        for cid in p["customer_ids"]:
            if len(cid) >= 8 and cid.isdigit():
                # Full SAP customer ID — exact match
                filters.append(f"SoldToParty eq '{cid}'")
            else:
                # Partial/short ID — use substringof
                filters.append(f"substringof('{cid}', SoldToParty) eq true")

    # Status filter
    if p["statuses"]:
        if len(p["statuses"]) == 1:
            filters.append(f"OverallSDProcessStatus eq '{p['statuses'][0]}'")
        else:
            or_parts = [f"OverallSDProcessStatus eq '{s}'" for s in p["statuses"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Amount filters (TotalNetAmount is Edm.Decimal — no quotes)
    if p["amount_gt"]:
        filters.append(f"TotalNetAmount gt {p['amount_gt']}")
    if p["amount_lt"]:
        filters.append(f"TotalNetAmount lt {p['amount_lt']}")

    result = {
        "serviceName": "API_SALES_ORDER_SRV",
        "entitySet": "A_SalesOrder",
        "filter": " and ".join(filters) if filters else "",
        "top": p["top"],
        "orderby": "SalesOrder desc",
        "select": ["SalesOrder", "SalesOrderType", "SoldToParty", "TotalNetAmount",
                   "TransactionCurrency", "OverallSDProcessStatus",
                   "OverallDeliveryStatus", "CreationDate", "RequestedDeliveryDate"],
        "query_explanation": _explain_query(filters, p),
    }
    return result


def build_sales_order_item_query(user_question: str) -> dict:
    """Convert natural language to OData v2 parameters for A_SalesOrderItem.

    Call this BEFORE calling sap_query_entity_set for order line items.
    Returns a dict with OData parameters ready for sap_query_entity_set.

    Args:
        user_question: The user's natural language question about order items.

    Returns:
        Dict with OData parameters ready for sap_query_entity_set.
    """
    p = _extract_patterns(user_question)
    filters = []

    # Order ID filter
    if p["order_ids"]:
        if len(p["order_ids"]) == 1:
            filters.append(f"SalesOrder eq '{p['order_ids'][0]}'")
        else:
            or_parts = [f"SalesOrder eq '{oid}'" for oid in p["order_ids"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Material filter
    if p["material_ids"]:
        for mid in p["material_ids"]:
            filters.append(f"Material eq '{mid}'")

    result = {
        "serviceName": "API_SALES_ORDER_SRV",
        "entitySet": "A_SalesOrderItem",
        "filter": " and ".join(filters) if filters else "",
        "top": p["top"],
        "orderby": "SalesOrder desc",
        "select": ["SalesOrder", "SalesOrderItem", "Material", "SalesOrderItemText",
                   "RequestedQuantity", "RequestedQuantityUnit", "OrderQuantityUnit",
                   "NetAmount", "TransactionCurrency"],
        "query_explanation": _explain_query(filters, p),
    }
    return result


def build_product_query(user_question: str) -> dict:
    """Convert natural language to OData v2 parameters for A_Product.

    Call this BEFORE calling sap_query_entity_set for products.
    Returns a dict with OData parameters ready for sap_query_entity_set.

    Args:
        user_question: The user's natural language question about products.

    Returns:
        Dict with OData parameters ready for sap_query_entity_set.
    """
    p = _extract_patterns(user_question)
    q_lower = user_question.lower()
    filters = []

    # Specific product ID
    if p["material_ids"]:
        if len(p["material_ids"]) == 1:
            filters.append(f"Product eq '{p['material_ids'][0]}'")
        else:
            or_parts = [f"Product eq '{mid}'" for mid in p["material_ids"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Product type filter
    if any(w in q_lower for w in ['finished good', 'finished goods', 'fert']):
        filters.append("ProductType eq 'FERT'")
    elif any(w in q_lower for w in ['raw material', 'raw materials', 'roh']):
        filters.append("ProductType eq 'ROH'")
    elif any(w in q_lower for w in ['semi-finished', 'semifinished', 'halb']):
        filters.append("ProductType eq 'HALB'")

    result = {
        "serviceName": "API_PRODUCT_SRV",
        "entitySet": "A_Product",
        "filter": " and ".join(filters) if filters else "",
        "top": p["top"],
        "orderby": "Product asc",
        "select": ["Product", "ProductType", "ProductGroup", "GrossWeight",
                   "NetWeight", "WeightUnit", "BaseUnit", "Division", "IndustrySector"],
        "query_explanation": _explain_query(filters, p),
    }
    return result


def build_inventory_query(user_question: str) -> dict:
    """Convert natural language to OData v2 parameters for A_MatlStkInAcctMod.

    Call this BEFORE calling sap_query_entity_set for inventory/stock.
    Returns a dict with OData parameters ready for sap_query_entity_set.

    Args:
        user_question: The user's natural language question about inventory.

    Returns:
        Dict with OData parameters ready for sap_query_entity_set.
    """
    p = _extract_patterns(user_question)
    filters = []

    # Material filter
    if p["material_ids"]:
        if len(p["material_ids"]) == 1:
            filters.append(f"Material eq '{p['material_ids'][0]}'")
        else:
            or_parts = [f"Material eq '{mid}'" for mid in p["material_ids"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Plant filter
    if p["plant_ids"]:
        for pid in p["plant_ids"]:
            filters.append(f"Plant eq '{pid}'")

    result = {
        "serviceName": "API_MATERIAL_STOCK_SRV",
        "entitySet": "A_MatlStkInAcctMod",
        "filter": " and ".join(filters) if filters else "",
        "top": p["top"],
        "orderby": "Material asc",
        "select": ["Material", "Plant", "StorageLocation",
                   "MatlWrhsStkQtyInMatlBaseUnit", "MaterialBaseUnit"],
        "query_explanation": _explain_query(filters, p),
    }
    return result


def build_delivery_query(user_question: str) -> dict:
    """Convert natural language to OData v2 parameters for A_OutbDeliveryHeader.

    Call this BEFORE calling sap_query_entity_set for deliveries.
    Returns a dict with OData parameters ready for sap_query_entity_set.

    Args:
        user_question: The user's natural language question about deliveries.

    Returns:
        Dict with OData parameters ready for sap_query_entity_set.
    """
    p = _extract_patterns(user_question)
    q_lower = user_question.lower()
    filters = []

    # Delivery document ID
    if p["delivery_ids"]:
        if len(p["delivery_ids"]) == 1:
            filters.append(f"DeliveryDocument eq '{p['delivery_ids'][0]}'")
        else:
            or_parts = [f"DeliveryDocument eq '{did}'" for did in p["delivery_ids"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Customer filter (SoldToParty on delivery)
    if p["customer_ids"]:
        for cid in p["customer_ids"]:
            if len(cid) >= 8 and cid.isdigit():
                filters.append(f"SoldToParty eq '{cid}'")
            else:
                filters.append(f"substringof('{cid}', SoldToParty) eq true")

    # Goods movement status
    if any(w in q_lower for w in ['not started', 'pending', 'not shipped']):
        filters.append("OverallGoodsMovementStatus eq 'A'")
    elif any(w in q_lower for w in ['partial', 'partially']):
        filters.append("OverallGoodsMovementStatus eq 'B'")
    elif any(w in q_lower for w in ['complete', 'completed', 'shipped', 'done']):
        filters.append("OverallGoodsMovementStatus eq 'C'")

    result = {
        "serviceName": "API_OUTBOUND_DELIVERY_SRV",
        "entitySet": "A_OutbDeliveryHeader",
        "filter": " and ".join(filters) if filters else "",
        "top": p["top"],
        "orderby": "DeliveryDocument desc",
        "select": ["DeliveryDocument", "DeliveryDocumentType", "SoldToParty",
                   "ShippingPoint", "DeliveryDate", "OverallGoodsMovementStatus",
                   "OverallSDProcessStatus", "SalesOrganization"],
        "query_explanation": _explain_query(filters, p),
    }
    return result


def build_delivery_item_query(user_question: str) -> dict:
    """Convert natural language to OData v2 parameters for A_OutbDeliveryItem.

    Call this BEFORE calling sap_query_entity_set for delivery line items.
    Returns a dict with OData parameters ready for sap_query_entity_set.

    Args:
        user_question: The user's natural language question about delivery items.

    Returns:
        Dict with OData parameters ready for sap_query_entity_set.
    """
    p = _extract_patterns(user_question)
    filters = []

    # Delivery document ID
    if p["delivery_ids"]:
        if len(p["delivery_ids"]) == 1:
            filters.append(f"DeliveryDocument eq '{p['delivery_ids'][0]}'")
        else:
            or_parts = [f"DeliveryDocument eq '{did}'" for did in p["delivery_ids"]]
            filters.append(f"({' or '.join(or_parts)})")

    # Material filter
    if p["material_ids"]:
        for mid in p["material_ids"]:
            filters.append(f"Material eq '{mid}'")

    result = {
        "serviceName": "API_OUTBOUND_DELIVERY_SRV",
        "entitySet": "A_OutbDeliveryItem",
        "filter": " and ".join(filters) if filters else "",
        "top": p["top"],
        "orderby": "DeliveryDocument desc",
        "select": ["DeliveryDocument", "DeliveryDocumentItem", "Material",
                   "ActualDeliveryQuantity", "DeliveryQuantityUnit"],
        "query_explanation": _explain_query(filters, p),
    }
    return result


def _explain_query(filters: list, patterns: dict) -> str:
    """Generate a human-readable explanation of what the query will fetch."""
    if not filters:
        return "No filters applied — fetching all records."
    parts = []
    if patterns["order_ids"]:
        parts.append(f"Order ID(s): {', '.join(patterns['order_ids'])}")
    if patterns["customer_ids"]:
        parts.append(f"Customer(s): {', '.join(patterns['customer_ids'])}")
    if patterns["material_ids"]:
        parts.append(f"Material(s): {', '.join(patterns['material_ids'])}")
    if patterns["delivery_ids"]:
        parts.append(f"Delivery doc(s): {', '.join(patterns['delivery_ids'])}")
    if patterns["statuses"]:
        status_map = {"A": "Open", "B": "Partial", "C": "Completed"}
        parts.append(f"Status: {', '.join(status_map.get(s, s) for s in patterns['statuses'])}")
    if patterns["amount_gt"]:
        parts.append(f"Amount > ${patterns['amount_gt']}")
    if patterns["amount_lt"]:
        parts.append(f"Amount < ${patterns['amount_lt']}")
    return f"Filtering by: {'; '.join(parts)}. OData $filter: {' and '.join(filters)}"
