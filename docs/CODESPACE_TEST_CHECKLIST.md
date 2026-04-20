# Codespace Test Checklist

Run through this after opening the repo in GitHub Codespaces.
Every step should pass without manual fixes. If something breaks, note it.

## Build phase (automatic, ~2 min)

- [ ] Container builds without errors in the Codespaces log
- [ ] `python3 --version` shows 3.12.x
- [ ] `node --version` shows v20.x
- [ ] `npm --version` returns a version (not "command not found")
- [ ] `post-create.sh` output shows all 4 steps completed
- [ ] `agent/.env` file was created with the template

## Dependencies installed

- [ ] `cd /workspace/agent && python3 -c "import google.adk; print('ADK OK')"` prints "ADK OK"
- [ ] `cd /workspace/agent && python3 -c "import google.genai; print('GenAI OK')"` prints "GenAI OK"
- [ ] `cd /workspace/mcp-server && node -e "require('./dist/index.js')" 2>&1 | head -1` does not say "Cannot find module"
- [ ] `ls /workspace/mcp-server/node_modules/@modelcontextprotocol` shows the `sdk` folder

## Mock server

- [ ] `cd /workspace/mcp-server && node mock-server.js &` starts without errors
- [ ] `curl -s http://localhost:3000/odata/sap/ | head -5` returns JSON or XML (not connection refused)
- [ ] Kill the mock server: `kill %1`

## ADK web UI

- [ ] Add a real Gemini API key to `agent/.env` (replace `your-gemini-api-key-here`)
- [ ] `cd /workspace/mcp-server && node mock-server.js &` (restart mock server)
- [ ] `cd /workspace/agent && adk web &` starts and says "listening on port 8080"
- [ ] Port 8080 notification appears in Codespaces (or check Ports tab)
- [ ] Opening the forwarded URL shows the ADK web UI in the browser
- [ ] Agent dropdown shows "order_to_cash_coordinator"

## End-to-end agent test

Type these in the ADK web UI chat:

- [ ] "List all products" — returns product data from mock server
- [ ] "Check inventory for material 100" — routes to inventory agent, returns stock data
- [ ] "Show open sales orders" — routes to sales order agent, returns order list
- [ ] "What deliveries are pending?" — routes to delivery agent, returns delivery data

## Ports

- [ ] Ports tab shows 8080 (ADK Web UI) forwarded
- [ ] Ports tab shows 3000 (Mock SAP Backend) forwarded (may be silent/not auto-opened)

## Cleanup

- [ ] `gh codespace delete` (or delete from github.com/codespaces) to free hours
