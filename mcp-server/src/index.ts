
/**
 * SAP OData MCP Server Entry Point
 * 
 * This is the main entry point for the SAP OData Model Context Protocol server.
 * It creates and starts the server instance.
 */

import { SAPODataMCPServer } from "./server";

// Create and start the server
const server = new SAPODataMCPServer();

// Handle startup
server.run().catch((error) => {
  console.error("Failed to start SAP OData MCP server:", error);
  process.exit(1);
});