# School Data MCP Server - Setup Instructions

This MCP server provides your other Claude Desktop instance with access to school databases and JSON data files.

## What's Included

- **school_data_server.py**: The MCP server that exposes tools to query school databases
- **Requirements**: Python 3.13+ and MCP SDK (already installed)
- **Data Access**:
  - SQLite databases for Abbotsleigh and Northern Beaches schools
  - JSON input files with school data
  - Summary statistics

## Setup Steps

### 1. Test the Server (Optional)
Run this command to verify the server works:
```bash
cd "C:\data projects\mcp"
python school_data_server.py
```
Press `Ctrl+C` to stop it.

### 2. Configure Claude Desktop

You need to add this server to your **other** Claude Desktop instance's configuration file.

**Location of config file:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Full path usually: `C:\Users\[YourUsername]\AppData\Roaming\Claude\claude_desktop_config.json`

**What to do:**

1. Open your Claude Desktop config file (create it if it doesn't exist)
2. Add the server configuration from `claude_desktop_config.json` file in this directory
3. Your config should look like this:

```json
{
  "mcpServers": {
    "school-data": {
      "command": "python",
      "args": [
        "C:\\data projects\\mcp\\school_data_server.py"
      ],
      "description": "School data MCP server - provides access to school databases and JSON files"
    }
  }
}
```

If you already have other MCP servers configured, just add the "school-data" entry to your existing "mcpServers" object.

### 3. Restart Claude Desktop

After saving the config file, restart your Claude Desktop application completely.

### 4. Verify Connection

In your other Claude Desktop instance, you should see:
- A "🔌" icon or MCP indicator showing the server is connected
- The server name "school-data" in your MCP servers list

## Available Tools

Once connected, your other Claude instance can use these tools:

### Database Tools
1. **list_schools** - List all available schools and their configurations
2. **query_database** - Execute SQL queries on school databases
3. **list_tables** - List all tables in a school database
4. **get_table_schema** - Get schema information for a specific table
5. **get_summary** - Get import summary for all schools

### Heatmap Tools (NEW!)
6. **list_heatmaps** - List all available performance heatmaps
7. **analyze_heatmap** - View and analyze a specific heatmap image
8. **get_school_overview** - Get comprehensive school overview (database + heatmaps)

## Example Usage

In your other Claude instance, you can ask things like:

**Database queries:**
- "List all available schools in the MCP server"
- "Show me the tables in the Abbotsleigh database"
- "Query the students table from northern-beaches database"
- "Get the schema for the courses table"
- "Show me the import summary"

**Heatmap analysis (NEW!):**
- "Show me the Abbotsleigh performance heatmap"
- "Analyze the heatmap for Abbotsleigh"
- "Give me a complete overview of Abbotsleigh (database + heatmaps)"
- "What heatmaps are available?"
- "Which courses are performing best according to the heatmap?"

## Available Databases

- **abbotsleigh.db** - Abbotsleigh school data (965 students, 208 courses)
- **abbotsleigh-encrypted.db** - Encrypted version (key: 1234567890)
- **northern-beaches.db** - Northern Beaches school data (629 students, 198 courses)

## Troubleshooting

**Server not showing up in Claude Desktop:**
1. Check that the path in config file is correct (use double backslashes `\\`)
2. Verify Python is in your PATH: `python --version`
3. Check Claude Desktop logs for errors
4. Restart Claude Desktop completely

**Permission errors:**
- Make sure Python has access to the directory
- Check that all database files are readable

**Query errors:**
- Only SELECT queries are allowed for safety
- Make sure the school_id matches a database file name

## Security Notes

- Only SELECT queries are permitted (no modifications to databases)
- Encrypted databases require the encryption key from schools.json
- The server only allows access to files in the capsules directory

## File Structure

```
C:\data projects\mcp\
├── school_data_server.py       # MCP server script
├── requirements.txt             # Python dependencies
├── claude_desktop_config.json   # Config to add to Claude Desktop
├── SETUP_INSTRUCTIONS.md        # This file
└── capsules/
    ├── input/                   # JSON data files
    │   ├── schools.json         # School configurations
    │   ├── abbotsleigh.json
    │   ├── northern-beaches.json
    │   └── teachers.json
    └── output/                  # Database files
        ├── abbotsleigh.db
        ├── abbotsleigh-encrypted.db
        ├── northern-beaches.db
        └── schools_summary.json
```
