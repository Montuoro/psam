#!/bin/bash

# Script to install MCP server configuration to Claude Desktop

CLAUDE_CONFIG_DIR="/c/Users/PMontuoro/AppData/Roaming/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
MCP_CONFIG="/c/data projects/mcp/claude_desktop_config.json"

echo "========================================"
echo "School Data MCP Server Installer"
echo "========================================"
echo ""

# Check if Claude config directory exists
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo "Creating Claude Desktop config directory..."
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

# Check if config file already exists
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "WARNING: Claude Desktop config file already exists!"
    echo "Location: $CLAUDE_CONFIG_FILE"
    echo ""
    echo "You need to manually merge the configuration."
    echo ""
    echo "Existing config:"
    cat "$CLAUDE_CONFIG_FILE"
    echo ""
    echo "============================================"
    echo "Config to add (from claude_desktop_config.json):"
    cat "$MCP_CONFIG"
    echo ""
    echo "Please add the 'school-data' entry to your existing mcpServers section."
else
    echo "No existing config found. Creating new config file..."
    cp "$MCP_CONFIG" "$CLAUDE_CONFIG_FILE"
    echo "Config file created successfully!"
    echo "Location: $CLAUDE_CONFIG_FILE"
fi

echo ""
echo "========================================"
echo "IMPORTANT: Restart Claude Desktop"
echo "========================================"
echo ""
echo "After configuring, you MUST restart Claude Desktop completely."
echo ""
