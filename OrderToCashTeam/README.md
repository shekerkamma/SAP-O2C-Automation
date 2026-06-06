# Order to Cash (O2C) Agent Team

A multi-agent system built with Google ADK that manages the complete Order to Cash business process in SAP environments using SAP OData APIs through Model Context Protocol (MCP).

## Overview

The Order to Cash Agent Team is a sophisticated multi-agent system that automates and assists with the complete customer order lifecycle, from initial product inquiry through delivery fulfillment and preparation for cash collection. It demonstrates advanced agent composition patterns using Google's Agent Development Kit (ADK).

## Prerequisites

###  Dependencies

- **Google Agent Development Kit (ADK)**: Latest version
- **SAP OData MCP Server**: Custom MCP server for SAP connectivity
- **SAP S/4HANA 2023 FPS03, Fully-Activated Appliance**: Valid SAP credentials and network connectivity
- **OData services**

- API_OUTBOUND_DELIVERY_SRV
- API_MATERIAL_DOCUMENT_SRV
- API_SUPPLIERINVOICE_PROCESS_SRV
- API_PRODUCT_SRV
- API_BILLING_DOCUMENT_SRV
- API_BUSINESS_PARTNER
- API_MATERIAL_STOCK_SRV
- API_INSPECTIONLOT_SRV
- API_SALES_ORDER_SRV
- API_INSPECTIONMETHOD_SRV
- API_INSPECTIONPLAN_SRV
- API_QUALITYINFORECORD_SRV
- API_MASTERINSPCHARACTERISTIC_SRV

 

## Architecture

### Multi-Agent System Design

The system follows a **Coordinator/Dispatcher Pattern** with a hierarchical structure:

```
Order to Cash Coordinator (Root Agent)
├── Product Specialist Agent
├── Inventory Manager Agent  
├── Sales Order Manager Agent
└── Delivery Specialist Agent
```

### Agent Hierarchy & Delegation

- **Root Agent**: `order_to_cash_coordinator` - Orchestrates the entire O2C process
- **Sub-Agents**: Four specialized agents handling specific business domains
- **Communication**: LLM-driven delegation with session state sharing
- **Integration**: SAP OData APIs through MCP tools for real-time business data

## Agent Responsibilities

### 🎯 Order to Cash Coordinator (Root Agent)
**Role**: Main orchestrator and customer interface
- Manages overall customer journey and experience
- Routes requests to appropriate specialist agents
- Synthesizes responses from multiple agents
- Maintains session continuity across the O2C process
- Provides business process guidance and escalation handling

### 🛍️ Product Specialist Agent
**Role**: Product catalog and master data management
- **SAP Tools**: 8 product-related operations
- Product catalog searches and inquiries
- Product descriptions and specifications retrieval
- Plant-specific product configurations
- Product master data creation and updates

**Available Tools**:
- Product Management: `getAllProducts`, `getProductByKey`, `createProduct`, `updateProduct`
- Descriptions: `getAllProductDescriptions`, `getProductDescriptionsByProduct`
- Plant Data: `getAllProductPlants`, `getProductPlantsByProduct`

### 📦 Inventory Manager Agent
**Role**: Stock management and material movements
- **SAP Tools**: 14 inventory and material document operations
- Real-time stock level checks and availability
- Material document creation and management
- Stock movements and inventory transactions
- Serial number tracking

**Available Tools**:
- Stock Management: `getAllMaterialStocks`, `getMaterialStockByKey`, `getAllStockDetails`
- Material Documents: `getAllMaterialDocumentHeaders`, `createMaterialDocumentHeader`, etc.
- Operations: `cancelMaterialDocument`, `cancelMaterialDocumentItem`

### 📋 Sales Order Manager Agent
**Role**: Order processing and lifecycle management
- **SAP Tools**: 18 sales order operations
- Sales order creation, modification, and tracking
- Order item management and scheduling
- Partner and text management
- Order status monitoring and updates

**Available Tools**:
- Order Management: `getAllSalesOrders`, `getSalesOrderByKey`, `createSalesOrder`
- Item Management: `getAllSalesOrderItems`, `createSalesOrderItem`, etc.
- Supporting Data: Partners, schedule lines, texts

### 🚚 Delivery Specialist Agent  
**Role**: Fulfillment and delivery operations
- **SAP Tools**: 17 outbound delivery operations
- Delivery document creation and management
- Picking and warehouse operations
- Goods issue processing
- Delivery tracking and exception handling

**Available Tools**:
- Delivery Management: `getAllOutboundDeliveryHeadersV1`, `createOutboundDeliveryHeaderV1`
- Operations: `pickAllItemsV1`, `postGoodsIssueV1`, `confirmPickingAllItemsV1`
- Diagnostics: `diagnoseDeliveryDocumentV1`

## Business Process Flow

### Typical O2C Sequence

1. **🔍 Inquiry Phase**
   - Customer product research → **Product Agent**
   - Catalog browsing and product specifications

2. **✅ Availability Check**
   - Stock verification → **Inventory Agent**  
   - Multi-plant availability and allocation

3. **📝 Order Creation**
   - Order processing → **Sales Order Agent**
   - Pricing, scheduling, and order confirmation

4. **📦 Fulfillment**
   - Delivery execution → **Delivery Agent**
   - Picking, packing, shipping, and tracking
### Cross-Agent Coordination

- **Session State**: Shared data across agents (order details, customer info)
- **Agent Transfer**: LLM-driven routing based on request context
- **Business Logic**: End-to-end process orchestration
- **Error Handling**: Graceful escalation and alternative solutions

## Technical Implementation

### Technology Stack

- **Framework**: Google Agent Development Kit (ADK)
- **LLM**: Gemini 2.5 Flash for all agents
- **Integration**: Model Context Protocol (MCP) for SAP connectivity
- **Backend**: SAP OData APIs (via custom MCP server)
- **Language**: Python 3.9+

### Key Features

- **MCP Integration**: Real-time SAP data access through standardized protocol
- **Tool Filtering**: Each agent has access only to relevant SAP operations
- **Session Management**: Persistent state across agent interactions
- **Error Handling**: Comprehensive exception management and user guidance
- **Scalability**: Modular design supporting additional agents and capabilities

### Connection Configuration

The system connects to SAP through a custom MCP server:

```python
# Located in constants/constants.py
MCP_CONNECTION_PARAMS = StdioServerParameters(
    command='node',
    args=["/path/to/sap-odata-mcp/build/index.js"]
)
```

## Usage Examples

### Customer Interactions

```
Customer: "I need to order 100 units of product ABC123"

O2C Coordinator:
1. Routes to Product Agent → Validates product exists
2. Routes to Inventory Agent → Checks stock availability  
3. Routes to Sales Order Agent → Creates sales order
4. Routes to Delivery Agent → Schedules delivery
5. Provides integrated response with order confirmation
```

### Business Process Support

```
Sales Rep: "What's the delivery status for order SO12345?"

O2C Coordinator:
→ Routes to Delivery Agent
→ Retrieves delivery document status
→ Provides tracking information and next steps
```

## Testing & Development

### Running the Agent Team

```bash
# Navigate to the parent directory
cd /path/to/sap-odata-mcp/multi_tool_agent

# Launch ADK development UI
adk web

# Select "OrderToCashTeam" from the agent dropdown
```

### Test Scenarios

1. **Product Inquiry**: "What products do you have in category X?"
2. **Stock Check**: "Is product Y available in plant 1000?"
3. **Order Creation**: "I want to order 50 units of product Z"
4. **Delivery Status**: "What's the status of delivery 123456?"
5. **Complete O2C Flow**: End-to-end order processing

### Conversation Testing

The system supports natural conversation flows:
- Multi-turn interactions with context preservation
- Business process guidance and education
- Error recovery and alternative solutions
- Integration with existing SAP business data

## Agent Prompt Engineering

Each agent has carefully crafted prompts that include:

- **Role Definition**: Clear business responsibilities
- **Tool Documentation**: Detailed SAP operation descriptions  
- **Business Context**: O2C process integration
- **Communication Guidelines**: Professional customer service
- **Error Handling**: Graceful failure management

## Best Practices

### Multi-Agent Design
- **Clear Separation of Concerns**: Each agent has distinct business domain
- **Hierarchical Structure**: Root coordinator with specialized sub-agents
- **Session State Management**: Shared context across agent interactions
- **LLM-Driven Delegation**: Natural language routing decisions

### SAP Integration
- **Tool Filtering**: Agents access only relevant SAP operations
- **Business Logic**: SAP-aware prompts and error handling
- **Data Consistency**: Real-time integration with SAP business data
- **Process Compliance**: Adherence to SAP business process standards

### Customer Experience
- **Natural Language**: Business-friendly communication
- **Process Guidance**: Step-by-step O2C assistance
- **Error Recovery**: Alternative solutions and escalation paths
- **Context Preservation**: Continuous conversation across domains

## Future Enhancements

### Planned Features
- **Advanced Planning**: Multi-step order optimization
- **Integration Extensions**: Additional SAP modules (MM, FI, etc.)
- **Analytics Agent**: Business intelligence and reporting
- **Workflow Automation**: Automated exception handling

### Architectural Evolution
- **Custom Agents**: Advanced orchestration logic
- **Event-Driven Architecture**: Real-time SAP event processing
- **Multi-Company Support**: Cross-organizational order processing
- **Advanced State Management**: Persistent conversation history

## Contributing

### Adding New Agents
1. Create new agent directory under `sub_agents/`
2. Implement `agent.py` with MCP tool filtering
3. Create comprehensive `prompt.py` with business context
4. Add agent to root coordinator's sub_agents list
5. Update this README with new capabilities

### Extending Functionality
- Add new SAP tools to relevant agents
- Enhance prompts with business logic
- Implement custom error handling
- Add new business process flows

---

**Total SAP Tools Available**: 64 operations across 5 business domains
**Agent Count**: 5 (1 coordinator + 4 specialists)
**Business Process Coverage**: Complete Order to Cash lifecycle

This agent team demonstrates the power of multi-agent systems for complex business process automation while maintaining the flexibility and intelligence of LLM-driven decision making.
**System**: Routes to Inventory Manager → Uses `getStockByMaterial`

### Order Creation
**User**: "Create a sales order for customer 12345 with material ABC123 quantity 10"
**System**: Routes to Sales Order Manager → Uses `createSalesOrder` and `createSalesOrderItem`

### Delivery Processing
**User**: "Create delivery for sales order 9876543210"
**System**: Routes to Delivery Specialist → Uses `createOutboundDeliveryHeaderV1`

## Business Value

### Process Automation
- Streamlines the complete order-to-cash process
- Reduces manual intervention and errors
- Ensures consistent process execution

### Customer Service
- Provides instant access to product and stock information
- Enables real-time order status tracking
- Improves response times for customer inquiries

### Operational Efficiency
- Automates routine SAP transactions
- Provides intelligent process routing
- Enables proactive issue identification and resolution

### Data Integration
- Centralizes access to SAP master and transactional data
- Ensures data consistency across business functions
- Provides real-time visibility into business operations

## Future Enhancements

### Planned Features
- Billing and invoicing agent integration
- Advanced analytics and reporting capabilities
- Customer portal integration
- Mobile accessibility

### Technical Improvements
- Performance optimization for high-volume operations
- Enhanced error handling and recovery
- Advanced workflow automation
- Integration with additional SAP modules

## Support and Maintenance

### Monitoring
- Agent performance metrics
- SAP system connectivity monitoring
- Business process completion rates

### Updates
- Regular prompt optimization
- SAP API version compatibility
- New business capability additions

This O2C Agent Team represents a sophisticated approach to business process automation, combining the power of Google ADK's multi-agent capabilities with comprehensive SAP system integration.
