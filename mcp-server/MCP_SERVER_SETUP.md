# Configuring PSAM School Data Library as an MCP Server for Claude

This guide explains how to configure the `mcp_psam.py` file as a Model Context Protocol (MCP) server for Claude Desktop or other MCP-compatible clients.

## Prerequisites

- Python 3.10 or higher
- Claude Desktop application installed
- PSAM School Data Library dependencies installed

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify data file exists:**
   Ensure the data file is present at:
   ```
   download/DemoNSWSchoolData.txt
   ```

## Configuration for Claude Desktop

### macOS/Linux

1. **Open Claude Desktop configuration file:**
   ```bash
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Add the MCP server configuration:**
   ```json
   {
     "mcpServers": {
       "psam": {
         "command": "python3",
         "args": [
           "/Users/waynehoulden/GitHub/jai-psam/mcp_psam.py"
         ],
         "env": {}
       }
     }
   }
   ```

   **Important:** Replace `/Users/waynehoulden/GitHub/jai-psam/mcp_psam.py` with the actual absolute path to your `mcp_psam.py` file.

### Windows

1. **Open Claude Desktop configuration file:**
   ```powershell
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Add the MCP server configuration:**
   ```json
   {
     "mcpServers": {
       "psam": {
         "command": "python",
         "args": [
           "C:\\Users\\YourUsername\\GitHub\\jai-psam\\mcp_psam.py"
         ],
         "env": {}
       }
     }
   }
   ```

   **Important:** Replace the path with the actual absolute path to your `mcp_psam.py` file.

## Restart Claude Desktop

After configuring the MCP server, restart Claude Desktop for the changes to take effect.

## Verify Connection

Once Claude Desktop restarts, you should see the PSAM School Data Library available in the MCP servers list. You can verify by asking Claude:

```
What MCP servers are available?
```

Claude should list "psam" as one of the available servers.

## Available Tools

The MCP server exposes the following tools:

- **get_student** - Get detailed information about a student by ID
- **find_students** - Find students with various filters
- **get_school_stats** - Get comprehensive statistics for a school
- **get_school_rankings** - Get student rankings within a school for a course
- **get_course_distribution** - Get statistical distribution for a course
- **compare_courses** - Compare statistics across multiple courses
- **get_all_courses** - List all available courses
- **get_top_performers** - Get top N performing students
- **get_course_popularity** - Get most popular courses by enrollment
- **calculate_school_averages** - Calculate average PSAM scores for all schools
- **get_dataset_stats** - Get overall dataset statistics

## Example Usage

Once configured, you can ask Claude questions like:

- "Show me the top 10 students by PSAM score"
- "What are the statistics for school ID 101?"
- "Compare the performance in English Advanced vs Mathematics Extension 1"
- "Find all female students with PSAM scores above 90"

## Troubleshooting

### Server Not Appearing

1. Check that the path to `mcp_psam.py` is absolute and correct
2. Verify Python is in your PATH
3. Check Claude Desktop logs for errors

### Data Loading Errors

1. Verify the data file exists at `download/DemoNSWSchoolData.txt`
2. Check file permissions
3. Review server logs for specific error messages

### Python Environment Issues

If using a virtual environment, specify the full path to the Python interpreter:

```json
{
  "mcpServers": {
    "psam": {
      "command": "/Users/waynehoulden/GitHub/jai-psam/.venv/bin/python3",
      "args": [
        "/Users/waynehoulden/GitHub/jai-psam/mcp_psam.py"
      ]
    }
  }
}
```

## Advanced Configuration

### Custom Data File Path

To use a different data file, modify the `mcp_psam.py` file at line 34:

```python
data_path = Path(__file__).parent / "path" / "to" / "your" / "datafile.txt"
```

### Environment Variables

You can pass environment variables through the configuration:

```json
{
  "mcpServers": {
    "psam": {
      "command": "python3",
      "args": ["/path/to/mcp_psam.py"],
      "env": {
        "DATA_PATH": "/custom/path/to/data.txt"
      }
    }
  }
}
```

## Security Considerations

- The MCP server runs locally on your machine
- Data is not transmitted over the network
- Claude Desktop communicates with the server via stdio (standard input/output)
- Ensure the data file contains no sensitive information if sharing configurations
