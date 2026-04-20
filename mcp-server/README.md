# SAP OData MCP Server

A Model Context Protocol (MCP) server for integrating SAP systems with AI assistants like Claude using OData REST APIs. This server provides tools for connecting to SAP OData services, querying entity sets, executing CRUD operations, and calling OData functions.

## Features

- **SAP OData Connectivity**: Connect to SAP systems via OData REST APIs
- **Smart Connection Handling**: Properly handles SAP OData URL structures and 404 responses
- **Service Discovery**: Automatically discover available OData services via catalog or common service testing
- **Entity Set Queries**: Query any OData entity set with filtering, sorting, and pagination
- **CRUD Operations**: Create, Read, Update, and Delete operations on OData entities
- **Function Imports**: Execute OData function imports and custom functions
- **CSRF Token Handling**: Automatic CSRF token management for secure operations
- **Modular Architecture**: Clean, maintainable TypeScript codebase with separation of concerns

## Prerequisites

- **Node.js 18+**
- **SAP system with OData services enabled**
- **Network access to SAP OData endpoints**
- **SAP user credentials with appropriate authorizations**

⚠️ **Advantage**: No SAP RFC SDK installation required! Uses standard HTTP/REST APIs.

## Installation

### Quick Setup

1. **Create the project:**
```bash
mkdir sap-odata-mcp-server
cd sap-odata-mcp-server
mkdir src
```

2. **Copy the source files** from the artifacts to your `src/` directory:
   - `src/index.ts` - Entry point
   - `src/server.ts` - MCP server setup
   - `src/handlers.ts` - Request handlers
   - `src/odata-client.ts` - SAP OData client
   - `src/tool-definitions.ts` - Tool definitions
   - `src/types.ts` - TypeScript types

3. **Copy configuration files:**
   - `package.json` - Dependencies and scripts
   - `tsconfig.json` - TypeScript configuration
   - `.env.example` - Environment variables template

4. **Install dependencies:**
```bash
npm install
```

5. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your SAP details
```

6. **Build the project:**
```bash
npm run build
```

## Configuration

### Environment Variables

Create a `.env` file with your SAP system details:

```bash
# Required SAP OData Configuration
SAP_ODATA_BASE_URL=https://your-sap-host:8000/sap/opu/odata/sap/
SAP_USERNAME=your-sap-username
SAP_PASSWORD=your-sap-password

# Optional Configuration
SAP_CLIENT=100
SAP_TIMEOUT=30000
SAP_VALIDATE_SSL=false  # for development with self-signed certificates
SAP_ENABLE_CSRF=true
```

### Claude Desktop Integration

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sap-odata": {
      "command": "node",
      "args": ["/full/path/to/your/sap-odata-mcp-server/dist/index.js"],
      "env": {
        "SAP_ODATA_BASE_URL": "https://your-sap-host:8000/sap/opu/odata/sap/",
        "SAP_USERNAME": "your-username",
        "SAP_PASSWORD": "your-password",
        "SAP_CLIENT": "100",
        "SAP_VALIDATE_SSL": "false"
      }
    }
  }
}
```

## Available Tools

### 1. sap_connect
Connect to SAP OData service.

**Parameters:**
- `baseUrl` (required): SAP OData service base URL
- `username` (required): SAP username
- `password` (required): SAP password
- `client` (optional): SAP client number
- `timeout` (optional): Request timeout in milliseconds (default: 30000)
- `validateSSL` (optional): Validate SSL certificates (default: true)
- `enableCSRF` (optional): Enable CSRF token handling (default: true)

### 2. sap_get_services
Get list of available OData services with intelligent discovery.

### 3. sap_get_service_metadata
Get metadata for a specific OData service.

**Parameters:**
- `serviceName` (required): Name of the OData service

### 4. sap_query_entity_set
Query an OData entity set with filtering, sorting, and pagination.

**Parameters:**
- `serviceName` (required): Name of the OData service
- `entitySet` (required): Name of the entity set
- `select` (optional): Array of fields to select
- `filter` (optional): OData filter expression
- `orderby` (optional): OData orderby expression
- `top` (optional): Number of records to return
- `skip` (optional): Number of records to skip
- `expand` (optional): Navigation properties to expand

### 5. sap_get_entity
Get a specific entity by its key values.

**Parameters:**
- `serviceName` (required): Name of the OData service
- `entitySet` (required): Name of the entity set
- `keyValues` (required): Object with key-value pairs for entity keys

### 6. sap_create_entity
Create a new entity in an entity set.

### 7. sap_update_entity
Update an existing entity.

### 8. sap_delete_entity
Delete an entity.

### 9. sap_call_function
Call an OData function import.

### 10. sap_connection_status
Check current SAP OData connection status.

### 11. sap_disconnect
Disconnect from SAP OData service.

## Usage Examples

### Getting Started with Claude

Once configured, you can interact with SAP using natural language in Claude:

#### **Connect to SAP:**
```
Connect to SAP OData service at https://sap-host:8000/sap/opu/odata/sap/ using username DEVELOPER and password mypassword
```

#### **Discover Available Services:**
```
Get list of available OData services
```

#### **Get Service Information:**
```
Get metadata for service GWSAMPLE_BASIC
```

#### **Query Data:**
```
Query BusinessPartnerSet from GWSAMPLE_BASIC, select BusinessPartnerID and CompanyName, top 10
```

#### **Advanced Filtering:**
```
Query SalesOrderSet from ZSD_SALES_SRV, filter by CreationDate ge datetime'2024-01-01T00:00:00', order by CreationDate desc, top 20
```

#### **Get Specific Records:**
```
Get entity from MaterialSet in ZMM_MATERIAL_SRV with key Material = '000000000000000001'
```

#### **Create New Records:**
```
Create entity in CustomerSet with data: {"CustomerNumber": "1000", "CustomerName": "Test Customer", "Country": "US"}
```

### OData Query Examples

#### **Filtering:**
```
$filter=MaterialType eq 'FERT' and CreationDate ge datetime'2024-01-01T00:00:00'
```

#### **Selecting Fields:**
```
$select=Material,MaterialDescription,MaterialType,BaseUnit
```

#### **Sorting:**
```
$orderby=CreationDate desc,Material asc
```

#### **Pagination:**
```
$top=50&$skip=100
```

#### **Expanding Navigation Properties:**
```
$expand=MaterialPlantData,MaterialSalesData
```

## SAP System Requirements

### Required SAP Components
- **SAP NetWeaver 7.0 or higher**
- **SAP Gateway component activated**
- **OData services enabled and configured**

### Required SAP Authorizations

The SAP user needs these authorization objects:
- **S_SERVICE**: Service authorization for OData endpoints
- **S_ICF**: Internet Communication Framework authorization
- **S_TCODE**: Transaction authorization for BAPIs (if using function imports)

### Activating OData Services

1. **Transaction SICF**: Activate ICF services at `/sap/opu/odata`
2. **Transaction /IWFND/MAINT_SERVICE**: Manage and activate OData services
3. **Transaction /IWFND/GW_CLIENT**: Test OData service calls

## Architecture

### Modular Design

```
src/
├── index.ts              # Entry point - starts the server
├── server.ts             # MCP server setup and request routing
├── handlers.ts           # Business logic for each tool
├── odata-client.ts       # SAP OData HTTP client
├── tool-definitions.ts   # MCP tool schemas
└── types.ts              # TypeScript type definitions
```

### Key Features

- **Smart Connection Testing**: Handles SAP's URL structure where base URLs return 404
- **Service Discovery**: Multiple methods to find available OData services
- **Error Handling**: Comprehensive error handling with helpful messages
- **Type Safety**: Full TypeScript support with proper interfaces
- **CSRF Protection**: Automatic CSRF token management for write operations

## Troubleshooting

### Common Issues

#### **Connection Refused (Network Error)**
- Verify SAP system is running and accessible
- Check hostname/port in SAP_ODATA_BASE_URL
- Verify firewall settings allow HTTP/HTTPS traffic

#### **401 Unauthorized**
- Check SAP_USERNAME and SAP_PASSWORD
- Verify user account is not locked
- Ensure user has S_SERVICE authorization

#### **403 Forbidden**
- Check user has required SAP authorizations
- Verify S_ICF authorization for OData paths
- Contact SAP administrator for permission review

#### **404 Not Found**
- This is normal for SAP OData base URLs without service names
- Verify OData services are activated (SICF transaction)
- Use service discovery to find available services

#### **SSL Certificate Errors**
- Set `SAP_VALIDATE_SSL=false` for development
- Install proper certificates for production
- Check certificate chain and expiration

### Debug Mode

Enable detailed logging:
```bash
DEBUG=axios npm start
```

### SAP System Verification

1. **Test OData URL in browser**: Navigate to your SAP OData URL
2. **Check service activation**: Transaction SICF → `/sap/opu/odata`
3. **Verify gateway services**: Transaction /IWFND/MAINT_SERVICE
4. **Test with gateway client**: Transaction /IWFND/GW_CLIENT

## Security Best Practices

### Production Deployment

- **Use HTTPS** for all SAP OData connections
- **Store credentials securely** - never hardcode passwords
- **Create dedicated service users** with minimal required permissions
- **Enable CSRF protection** for write operations
- **Implement proper authorization** in SAP for OData services
- **Monitor access logs** and set up alerting
- **Regular security audits** of user permissions

### Network Security

- **Use VPN or private networks** for SAP access
- **Implement IP restrictions** where possible
- **Enable SAP Gateway security** features
- **Use proper certificate management**

## Common SAP OData Services

### Standard SAP Services
- **GWSAMPLE_BASIC** - Basic sample service for testing
- **GWDEMO** - Comprehensive demo service
- **RMTSAMPLEFLIGHT** - Flight booking demo

### Business Services
- **API_MATERIAL_SRV** - Material Management
- **API_BUSINESS_PARTNER** - Business Partner Management
- **API_SALES_ORDER_SRV** - Sales Order Management
- **API_PURCHASEORDER_PROCESS_SRV** - Purchase Order Processing

### Entity Sets by Module
- **MM (Materials Management)**: MaterialSet, MaterialPlantDataSet
- **SD (Sales & Distribution)**: SalesOrderSet, CustomerSet, PricingConditionSet
- **FI (Financial Accounting)**: GeneralLedgerEntrySet, AccountingDocumentSet
- **HR (Human Resources)**: EmployeeSet, OrganizationalUnitSet

## Development

### Available Scripts

```bash
# Build TypeScript
npm run build

# Start production server
npm start

# Development mode with auto-reload
npm run dev

# Code quality
npm run lint
npm run format
```

### Adding New Features

1. **Add tool definition** in `tool-definitions.ts`
2. **Implement handler** in `handlers.ts`
3. **Add route** in `server.ts` switch statement
4. **Update types** in `types.ts` if needed
5. **Build and test**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with proper TypeScript types
4. Test with a real SAP system
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

