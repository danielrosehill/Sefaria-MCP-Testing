#!/bin/bash
#
# Sefaria Explorer - Chainlit Chatbot Runner
#
# This script activates the virtual environment and runs the Chainlit app.
# It automatically finds an available port if the default is in use.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default starting port
START_PORT=${1:-9101}
MAX_ATTEMPTS=10

# Function to check if a port is available
is_port_available() {
    local port=$1
    ! (echo >/dev/tcp/localhost/$port) 2>/dev/null
}

# Find an available port
find_available_port() {
    local port=$START_PORT
    local end_port=$((START_PORT + MAX_ATTEMPTS))

    while [ $port -lt $end_port ]; do
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo $port
            return 0
        fi
        port=$((port + 1))
    done

    echo "Error: Could not find an available port in range $START_PORT-$((end_port - 1))" >&2
    return 1
}

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating with UV..."
    uv venv .venv
    source .venv/bin/activate
    uv pip install chainlit openai httpx httpx-sse python-dotenv anthropic mcp
else
    source .venv/bin/activate
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Make sure to set OPEN_ROUTER_API."
    echo "Copy .env.example to .env and add your API key."
fi

# Find available port
PORT=$(find_available_port)
if [ $? -ne 0 ]; then
    echo "$PORT"
    exit 1
fi

# Run Chainlit
echo ""
echo "=========================================="
echo "  Sefaria Explorer - MCP Testing Environment"
echo "=========================================="
echo ""
echo "Starting on port $PORT..."
echo "Open http://localhost:$PORT in your browser"
echo ""
echo "DISCLAIMER: This is a prototype/testing environment."
echo "Do NOT rely on this for halachic or religious decisions."
echo ""

chainlit run app.py --host 0.0.0.0 --port "$PORT" "${@:2}"
