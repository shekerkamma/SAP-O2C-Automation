FROM mcr.microsoft.com/devcontainers/python:3.12

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (ADK agents)
COPY agent/pyproject.toml /tmp/pyproject.toml
RUN pip install --no-cache-dir google-adk google-genai python-dotenv litellm

# Install MCP server dependencies
COPY mcp-server/package.json mcp-server/package-lock.json /tmp/mcp-server/
RUN cd /tmp/mcp-server && npm ci --ignore-scripts

WORKDIR /workspace
