#!/usr/bin/env python3
"""
MCP Server for School Data Access
Provides access to school databases and JSON data files
"""

import json
import sqlite3
import os
import base64
from pathlib import Path
from typing import Any
import asyncio

# Import MCP SDK
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Import analysis functions
from analyze_school_results_v3 import analyze_school_results_v3

# Base directory
BASE_DIR = Path(__file__).parent
CAPSULES_DIR = BASE_DIR / "capsules"
INPUT_DIR = CAPSULES_DIR / "input"
OUTPUT_DIR = CAPSULES_DIR / "output"
HEATMAPS_DIR = CAPSULES_DIR / "heatmaps"

# Create server instance
server = Server("school-data-server")

# Store for encryption keys (loaded from schools.json)
SCHOOL_CONFIG = {}

def load_school_config():
    """Load school configuration including encryption keys"""
    global SCHOOL_CONFIG
    schools_file = INPUT_DIR / "schools.json"
    if schools_file.exists():
        with open(schools_file, 'r') as f:
            schools = json.load(f)
            for school in schools:
                SCHOOL_CONFIG[school['file_id']] = school

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List all available school databases and data files"""
    resources = []

    # List databases
    if OUTPUT_DIR.exists():
        for db_file in OUTPUT_DIR.glob("*.db"):
            resources.append(types.Resource(
                uri=f"school-db://{db_file.stem}",
                name=f"Database: {db_file.stem}",
                description=f"SQLite database for {db_file.stem}",
                mimeType="application/x-sqlite3"
            ))

    # List JSON input files
    if INPUT_DIR.exists():
        for json_file in INPUT_DIR.glob("*.json"):
            resources.append(types.Resource(
                uri=f"school-json://{json_file.stem}",
                name=f"Data: {json_file.stem}",
                description=f"JSON data file for {json_file.stem}",
                mimeType="application/json"
            ))

    # List heatmap images
    if HEATMAPS_DIR.exists():
        for school_dir in HEATMAPS_DIR.iterdir():
            if school_dir.is_dir():
                for heatmap_file in school_dir.glob("*.png"):
                    resources.append(types.Resource(
                        uri=f"school-heatmap://{school_dir.name}/{heatmap_file.stem}",
                        name=f"Heatmap: {school_dir.name} - {heatmap_file.stem}",
                        description=f"Performance heatmap for {school_dir.name}",
                        mimeType="image/png"
                    ))

    return resources

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a specific resource"""
    if uri.startswith("school-json://"):
        file_id = uri.replace("school-json://", "")
        json_file = INPUT_DIR / f"{file_id}.json"

        if json_file.exists():
            with open(json_file, 'r') as f:
                return f.read()
        else:
            raise ValueError(f"JSON file not found: {file_id}")

    elif uri.startswith("school-db://"):
        db_id = uri.replace("school-db://", "")
        db_file = OUTPUT_DIR / f"{db_id}.db"

        if db_file.exists():
            return f"Database path: {db_file}\nUse query_database tool to query this database."
        else:
            raise ValueError(f"Database not found: {db_id}")

    elif uri.startswith("school-heatmap://"):
        # Format: school-heatmap://school_id/filename
        path_parts = uri.replace("school-heatmap://", "").split("/")
        if len(path_parts) != 2:
            raise ValueError(f"Invalid heatmap URI format: {uri}")

        school_id, filename = path_parts
        heatmap_file = HEATMAPS_DIR / school_id / f"{filename}.png"

        if heatmap_file.exists():
            return f"Heatmap image: {heatmap_file}\nUse analyze_heatmap tool to analyze this heatmap."
        else:
            raise ValueError(f"Heatmap not found: {uri}")

    else:
        raise ValueError(f"Unknown resource URI: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="list_schools",
            description="List all available schools and their configurations",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="query_database",
            description="Execute a SQL query on a school database",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "The school file ID (e.g., 'abbotsleigh', 'northern-beaches')",
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (SELECT statements only for safety)",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of rows to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["school_id", "query"],
            },
        ),
        types.Tool(
            name="list_tables",
            description="List all tables in a school database",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "The school file ID (e.g., 'abbotsleigh', 'northern-beaches')",
                    },
                },
                "required": ["school_id"],
            },
        ),
        types.Tool(
            name="get_table_schema",
            description="Get the schema (columns and types) for a specific table",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "The school file ID",
                    },
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table",
                    },
                },
                "required": ["school_id", "table_name"],
            },
        ),
        types.Tool(
            name="get_summary",
            description="Get the import summary for all schools",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="list_heatmaps",
            description="List all available heatmap images for schools. Heatmaps are the fundamental PSAM summary view - a 10,000-foot establishing shot of school performance across all courses and metrics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "Optional: filter to specific school (e.g., 'abbotsleigh', 'northern-beaches')",
                    },
                },
            },
        ),
        types.Tool(
            name="analyze_heatmap",
            description="Analyze a school's performance heatmap image. Returns the image for visual analysis. The heatmap shows z-scores across courses (rows) and performance metrics (columns), with color coding indicating performance levels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "The school ID (e.g., 'abbotsleigh', 'northern-beaches')",
                    },
                    "heatmap_name": {
                        "type": "string",
                        "description": "The heatmap filename without extension (e.g., 'abbotsleigh_heat_1', 'abbotsleigh_heat_2')",
                    },
                },
                "required": ["school_id", "heatmap_name"],
            },
        ),
        types.Tool(
            name="get_school_overview",
            description="Get a comprehensive overview of a school combining database statistics and available heatmaps. This provides the essential context for school analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "The school ID (e.g., 'abbotsleigh', 'northern-beaches')",
                    },
                },
                "required": ["school_id"],
            },
        ),
        types.Tool(
            name="analyze_school_results",
            description="Comprehensive school performance analysis with ATAR insights. Generates a detailed markdown report identifying courses requiring intervention, high performers, and actionable recommendations. Includes: 1) ATAR performance overview, 2) Departmental analysis with three-tier categorization (Courses of Concern / Middling / High Performers), 3) Deep insights with assessment-exam correlations, band distributions, scaling impacts, 4) Specific heatmap directions with z-score interpretations, 5) Database deep-dive suggestions. The report automatically saves as a .md file and provides evidence-based recommendations explaining WHY interventions are needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "string",
                        "description": "The school ID (e.g., 'abbotsleigh', 'northern-beaches')",
                    },
                    "year": {
                        "type": "number",
                        "description": "Optional: specific year to analyze (defaults to most recent year)",
                    },
                },
                "required": ["school_id"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""

    if name == "list_schools":
        if not SCHOOL_CONFIG:
            load_school_config()

        result = {
            "schools": list(SCHOOL_CONFIG.values()),
            "total": len(SCHOOL_CONFIG)
        }
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "get_summary":
        summary_file = OUTPUT_DIR / "schools_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = f.read()
            return [types.TextContent(type="text", text=summary)]
        else:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "Summary file not found"}, indent=2)
            )]

    elif name == "list_tables":
        school_id = arguments["school_id"]
        db_file = OUTPUT_DIR / f"{school_id}.db"

        if not db_file.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Database not found: {school_id}"}, indent=2)
            )]

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        return [types.TextContent(
            type="text",
            text=json.dumps({"tables": tables, "count": len(tables)}, indent=2)
        )]

    elif name == "get_table_schema":
        school_id = arguments["school_id"]
        table_name = arguments["table_name"]
        db_file = OUTPUT_DIR / f"{school_id}.db"

        if not db_file.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Database not found: {school_id}"}, indent=2)
            )]

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        conn.close()

        schema = []
        for col in columns:
            schema.append({
                "name": col[1],
                "type": col[2],
                "not_null": bool(col[3]),
                "default": col[4],
                "primary_key": bool(col[5])
            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "table": table_name,
                "columns": schema,
                "column_count": len(schema)
            }, indent=2)
        )]

    elif name == "query_database":
        school_id = arguments["school_id"]
        query = arguments["query"]
        limit = arguments.get("limit", 100)

        # Safety check: only allow SELECT queries
        if not query.strip().upper().startswith("SELECT"):
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Only SELECT queries are allowed for safety"
                }, indent=2)
            )]

        db_file = OUTPUT_DIR / f"{school_id}.db"

        if not db_file.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Database not found: {school_id}"}, indent=2)
            )]

        try:
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Add LIMIT to query if not present
            if "LIMIT" not in query.upper():
                query += f" LIMIT {limit}"

            cursor.execute(query)
            rows = cursor.fetchall()

            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(row))

            conn.close()

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "school_id": school_id,
                    "query": query,
                    "row_count": len(results),
                    "results": results
                }, indent=2, default=str)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Query execution failed: {str(e)}"
                }, indent=2)
            )]

    elif name == "list_heatmaps":
        school_id = arguments.get("school_id")
        heatmaps = []

        if HEATMAPS_DIR.exists():
            if school_id:
                # List heatmaps for specific school
                school_heatmap_dir = HEATMAPS_DIR / school_id
                if school_heatmap_dir.exists():
                    for heatmap_file in school_heatmap_dir.glob("*.png"):
                        heatmaps.append({
                            "school_id": school_id,
                            "filename": heatmap_file.stem,
                            "full_filename": heatmap_file.name,
                            "path": str(heatmap_file)
                        })
            else:
                # List all heatmaps for all schools
                for school_dir in HEATMAPS_DIR.iterdir():
                    if school_dir.is_dir():
                        for heatmap_file in school_dir.glob("*.png"):
                            heatmaps.append({
                                "school_id": school_dir.name,
                                "filename": heatmap_file.stem,
                                "full_filename": heatmap_file.name,
                                "path": str(heatmap_file)
                            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "heatmaps": heatmaps,
                "count": len(heatmaps)
            }, indent=2)
        )]

    elif name == "analyze_heatmap":
        school_id = arguments["school_id"]
        heatmap_name = arguments["heatmap_name"]

        heatmap_file = HEATMAPS_DIR / school_id / f"{heatmap_name}.png"

        if not heatmap_file.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Heatmap not found: {school_id}/{heatmap_name}"
                }, indent=2)
            )]

        # Read and encode the image
        with open(heatmap_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Return both the image and metadata
        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "school_id": school_id,
                    "heatmap_name": heatmap_name,
                    "description": "Performance heatmap showing z-scores across courses (rows) and metrics (columns). The Total column shows mean z-score (excluding cohort size). Color coding: dark blue = high positive, gray/tan = negative, light blue = moderate positive.",
                    "path": str(heatmap_file)
                }, indent=2)
            ),
            types.ImageContent(
                type="image",
                data=image_data,
                mimeType="image/png"
            )
        ]

    elif name == "get_school_overview":
        school_id = arguments["school_id"]
        overview = {
            "school_id": school_id,
            "database_stats": {},
            "heatmaps": [],
            "summary": {}
        }

        # Get database info
        db_file = OUTPUT_DIR / f"{school_id}.db"
        if db_file.exists():
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                # Get table count
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                overview["database_stats"]["tables"] = tables
                overview["database_stats"]["table_count"] = len(tables)

                # Get record counts for key tables
                record_counts = {}
                for table in ["students", "courses", "course_results", "groups"]:
                    if table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        record_counts[table] = cursor.fetchone()[0]

                overview["database_stats"]["record_counts"] = record_counts
                conn.close()
            except Exception as e:
                overview["database_stats"]["error"] = str(e)

        # Get heatmaps for this school
        school_heatmap_dir = HEATMAPS_DIR / school_id
        if school_heatmap_dir.exists():
            for heatmap_file in sorted(school_heatmap_dir.glob("*.png")):
                overview["heatmaps"].append({
                    "filename": heatmap_file.stem,
                    "full_filename": heatmap_file.name,
                    "path": str(heatmap_file)
                })

        # Get summary from schools_summary.json
        summary_file = OUTPUT_DIR / "schools_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                all_summaries = json.load(f)
                for school_summary in all_summaries:
                    if school_summary.get("file_id") == school_id:
                        overview["summary"] = school_summary.get("summary", {})
                        break

        return [types.TextContent(
            type="text",
            text=json.dumps(overview, indent=2)
        )]

    elif name == "analyze_school_results":
        school_id = arguments["school_id"]
        target_year = arguments.get("year")

        db_file = OUTPUT_DIR / f"{school_id}.db"

        if not db_file.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Database not found: {school_id}"}, indent=2)
            )]

        try:
            # Call the enhanced v3 analysis function
            analysis_result = analyze_school_results_v3(
                school_id=school_id,
                db_path=str(db_file),
                heatmaps_dir=str(HEATMAPS_DIR),
                output_dir=str(BASE_DIR),
                target_year=target_year
            )

            # Extract the markdown report path from the result
            report_path = analysis_result.get('markdown_report')

            # Read the generated markdown report
            if report_path and Path(report_path).exists():
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()

                return [types.TextContent(
                    type="text",
                    text=f"Analysis complete! Report generated: {report_path}\n\n{report_content}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="Analysis completed but no report file was generated."
                )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Analysis failed: {str(e)}"
                }, indent=2)
            )]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main entry point"""
    # Load school configuration on startup
    load_school_config()

    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="school-data-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
