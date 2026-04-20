#!/bin/bash
set -e

echo "=== Setting up SAP O2C Workshop ==="

# Install Python dependencies
echo "[1/4] Installing ADK agent dependencies..."
cd /workspace/agent
pip install -e ".[dev]" --quiet

# Install MCP server dependencies
echo "[2/4] Installing MCP server dependencies..."
cd /workspace/mcp-server
npm ci --silent

# Build MCP server
echo "[3/4] Building MCP server..."
npm run build

# Create .env template if it doesn't exist
echo "[4/4] Checking environment config..."
if [ ! -f /workspace/agent/.env ]; then
  cat > /workspace/agent/.env << 'EOF'
# === REQUIRED: Get your free key at https://aistudio.google.com/apikey ===
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-gemini-api-key-here

# === MCP Server Config ===
# For Mock Mode (default): use any URL, the mock server handles everything
SAP_ODATA_BASE_URL=http://localhost:3000/odata/sap
SAP_ODATA_USERNAME=mock
SAP_ODATA_PASSWORD=mock

# === For Real APIM Mode: uncomment and fill these ===
# SAP_ODATA_BASE_URL=https://your-apim-tenant.prod.apimanagement.region.hana.ondemand.com/odata/sap
# APIM_API_KEY=your-consumer-key-from-developer-portal
EOF
  echo "  Created agent/.env template - add your Gemini API key!"
else
  echo "  agent/.env already exists - skipping"
fi

echo ""
echo "=== Workshop ready! ==="
echo ""
echo "Next steps:"
echo "  1. Add your Gemini API key to agent/.env"
echo "  2. Start the mock server:  cd mcp-server && node mock-server.js"
echo "  3. Start the agent UI:     cd agent && adk web"
echo "  4. Open port 8080 in your browser"
echo ""
