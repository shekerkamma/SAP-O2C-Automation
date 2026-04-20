import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { SAPODataHandlers } from "./handlers";

export class SAPODataMCPServer {
  private server: McpServer;
  private handlers: SAPODataHandlers;

  constructor() {
    this.server = new McpServer({
      name: "sap-odata-mcp-server",
      version: "0.1.0",
    });

    this.handlers = new SAPODataHandlers();
    this.registerTools();
    this.setupErrorHandling();
  }

  private setupErrorHandling(): void {
    process.on("SIGINT", async () => {
      await this.handlers.handleDisconnect();
      await this.server.close();
      process.exit(0);
    });
  }

  private registerTools(): void {
    this.server.tool(
      "sap_connect",
      "Connect to SAP OData service",
      {
        baseUrl: z.string().describe("SAP OData service base URL (e.g., https://sap-host:8000/sap/opu/odata/sap/)"),
        username: z.string().optional().describe("SAP username"),
        password: z.string().optional().describe("SAP password"),
        client: z.string().optional().describe("SAP client number (optional)"),
        timeout: z.number().optional().describe("Request timeout in milliseconds"),
        validateSSL: z.boolean().optional().describe("Validate SSL certificates"),
        enableCSRF: z.boolean().optional().describe("Enable CSRF token handling"),
      },
      async (args) => this.handlers.handleConnect(args),
    );

    this.server.tool(
      "sap_get_services",
      "Get list of available OData services",
      {},
      async () => this.handlers.handleGetServices(),
    );

    this.server.tool(
      "sap_get_service_metadata",
      "Get metadata for a specific OData service",
      {
        serviceName: z.string().describe("Name of the OData service"),
      },
      async (args) => this.handlers.handleGetServiceMetadata(args),
    );

    this.server.tool(
      "sap_query_entity_set",
      "Query an OData entity set with filtering, sorting, and pagination",
      {
        serviceName: z.string().describe("Name of the OData service"),
        entitySet: z.string().describe("Name of the entity set"),
        select: z.array(z.string()).optional().describe("Fields to select"),
        filter: z.string().optional().describe("OData filter expression"),
        orderby: z.string().optional().describe("OData orderby expression"),
        top: z.number().optional().describe("Number of records to return"),
        skip: z.number().optional().describe("Number of records to skip"),
        expand: z.array(z.string()).optional().describe("Navigation properties to expand"),
      },
      async (args) => this.handlers.handleQueryEntitySet(args),
    );

    this.server.tool(
      "sap_get_entity",
      "Get a specific entity by its key values",
      {
        serviceName: z.string().describe("Name of the OData service"),
        entitySet: z.string().describe("Name of the entity set"),
        keyValues: z.record(z.string()).describe("Key-value pairs for entity keys"),
      },
      async (args) => this.handlers.handleGetEntity(args),
    );

    this.server.tool(
      "sap_create_entity",
      "Create a new entity in an entity set",
      {
        serviceName: z.string().describe("Name of the OData service"),
        entitySet: z.string().describe("Name of the entity set"),
        data: z.record(z.unknown()).describe("Entity data to create"),
      },
      async (args) => this.handlers.handleCreateEntity(args),
    );

    this.server.tool(
      "sap_update_entity",
      "Update an existing entity",
      {
        serviceName: z.string().describe("Name of the OData service"),
        entitySet: z.string().describe("Name of the entity set"),
        keyValues: z.record(z.string()).describe("Key-value pairs for entity keys"),
        data: z.record(z.unknown()).describe("Entity data to update"),
      },
      async (args) => this.handlers.handleUpdateEntity(args),
    );

    this.server.tool(
      "sap_delete_entity",
      "Delete an entity",
      {
        serviceName: z.string().describe("Name of the OData service"),
        entitySet: z.string().describe("Name of the entity set"),
        keyValues: z.record(z.string()).describe("Key-value pairs for entity keys"),
      },
      async (args) => this.handlers.handleDeleteEntity(args),
    );

    this.server.tool(
      "sap_call_function",
      "Call an OData function import",
      {
        serviceName: z.string().describe("Name of the OData service"),
        functionName: z.string().describe("Name of the function to call"),
        parameters: z.record(z.unknown()).optional().describe("Function parameters"),
      },
      async (args) => this.handlers.handleCallFunction(args),
    );

    this.server.tool(
      "sap_connection_status",
      "Check SAP OData connection status and get connection info",
      {},
      async () => this.handlers.handleConnectionStatus(),
    );

    this.server.tool(
      "sap_disconnect",
      "Disconnect from SAP OData service",
      {},
      async () => this.handlers.handleDisconnect(),
    );
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("SAP OData MCP server running on stdio");

    // Auto-connect using environment variables if SAP_ODATA_BASE_URL is set
    const baseUrl = process.env.SAP_ODATA_BASE_URL;
    if (baseUrl) {
      try {
        await this.handlers.handleConnect({
          baseUrl,
          username: process.env.SAP_USERNAME || "",
          password: process.env.SAP_PASSWORD || "",
          validateSSL: process.env.SAP_VALIDATE_SSL !== "false",
          enableCSRF: false,
        });
        console.error(`SAP OData auto-connected to ${baseUrl}`);
      } catch (err) {
        console.error("SAP OData auto-connect skipped:", (err as Error).message);
      }
    }
  }
}
