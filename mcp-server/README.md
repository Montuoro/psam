# PSAM MCP Server

This directory contains the MCP (Model Context Protocol) server for Jai AI integration with PSAM data.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Claude to use this MCP server:
```json
{
  "mcpServers": {
    "psam": {
      "command": "C:\\Users\\paulm\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["-u", "C:\\Users\\paulm\\psam\\mcp-server\\mcp_psam.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

## Migration Steps

1. Copy your current `mcp_psam.py` from `C:\Users\paulm\AppData\Roaming\Claude\Jai-PSAM\` to this directory
2. Update your Claude config to point to the new location
3. Test the MCP server connection

## Usage

Once configured, Jai can use this MCP server to:
- Query student data
- Analyze PSAM scores  
- Generate statistical reports
- Search and filter student records
