"""
MCP Server for PSAM School Data Library.

Exposes the PSAM School Data Library via Model Context Protocol,
providing AI-accessible tools for querying student performance,
school statistics, and course analysis.
"""

import asyncio
import sys
from typing import Optional
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

from data.nsw_schools_loader import NSWSchoolDataLoader
from data.nsw_schools_query import NSWSchoolQuery


# Initialize data loader and query API
loader = NSWSchoolDataLoader()
query_api: Optional[NSWSchoolQuery] = None

# MCP Server instance
server = Server("nsw-schools")


async def initialize_data():
    """Initialize data loader on startup."""
    global query_api
    
    # Path to data file
    data_path = Path(__file__).parent / "download" / "DemoNSWSchoolData.txt"
    
    print(f"Initializing PSAM School Data from {data_path}...", file=sys.stderr)
    
    try:
        load_time, stats = loader.load_from_file(data_path)
        query_api = NSWSchoolQuery(loader)
        
        print(f"✓ Data loaded successfully in {load_time:.2f}s", file=sys.stderr)
        print(f"  - Schools: {stats['schools']}", file=sys.stderr)
        print(f"  - Students: {stats['students']}", file=sys.stderr)
        print(f"  - Courses: {stats['courses']}", file=sys.stderr)
        print(f"  - Unique course types: {stats['unique_courses']}", file=sys.stderr)
        
    except Exception as e:
        print(f"✗ Failed to load data: {e}", file=sys.stderr)
        raise


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_student",
            description="Get detailed information about a student by their ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "integer",
                        "description": "The unique student ID"
                    }
                },
                "required": ["student_id"]
            }
        ),
        Tool(
            name="find_students",
            description="Find students matching specified filters (school, gender, PSAM score range, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "integer",
                        "description": "Filter by school ID"
                    },
                    "gender": {
                        "type": "string",
                        "description": "Filter by gender (M/F)"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Filter by calendar year"
                    },
                    "min_psam": {
                        "type": "number",
                        "description": "Minimum PSAM score"
                    },
                    "max_psam": {
                        "type": "number",
                        "description": "Maximum PSAM score"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Filter students taking this course"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 100
                    }
                }
            }
        ),
        Tool(
            name="get_school_stats",
            description="Get comprehensive statistics for a school (student count, PSAM averages, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "integer",
                        "description": "The school ID"
                    }
                },
                "required": ["school_id"]
            }
        ),
        Tool(
            name="get_school_rankings",
            description="Get student rankings within a school for a specific course",
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "integer",
                        "description": "The school ID"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "The course name (e.g., 'English Advanced', 'Mathematics Extension 1')"
                    }
                },
                "required": ["school_id", "course_name"]
            }
        ),
        Tool(
            name="get_course_distribution",
            description="Get statistical distribution for a course across all students (marks, bands, gender)",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "The course name"
                    }
                },
                "required": ["course_name"]
            }
        ),
        Tool(
            name="compare_courses",
            description="Compare statistics across multiple courses",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of course names to compare"
                    }
                },
                "required": ["course_names"]
            }
        ),
        Tool(
            name="get_all_courses",
            description="Get a list of all unique course names available in the dataset",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_top_performers",
            description="Get top N performing students by PSAM score or total unit scores",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of top performers to return",
                        "default": 10
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["psam_score", "total_unit_scores"],
                        "description": "Metric to rank by",
                        "default": "psam_score"
                    }
                }
            }
        ),
        Tool(
            name="get_course_popularity",
            description="Get most popular courses by enrollment count",
            inputSchema={
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Number of courses to return",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="calculate_school_averages",
            description="Calculate average PSAM scores for all schools, ranked by performance",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_dataset_stats",
            description="Get overall statistics about the loaded dataset",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from MCP clients."""
    
    if query_api is None:
        return [TextContent(
            type="text",
            text="Error: Data not loaded. Please restart the server."
        )]
    
    try:
        result = None
        
        if name == "get_student":
            result = query_api.get_student(arguments["student_id"])
            
        elif name == "find_students":
            result = query_api.find_students(
                school_id=arguments.get("school_id"),
                gender=arguments.get("gender"),
                year=arguments.get("year"),
                min_psam=arguments.get("min_psam"),
                max_psam=arguments.get("max_psam"),
                course_name=arguments.get("course_name"),
                limit=arguments.get("limit", 100)
            )
            
        elif name == "get_school_stats":
            result = query_api.get_school_stats(arguments["school_id"])
            
        elif name == "get_school_rankings":
            result = query_api.get_school_rankings(
                arguments["school_id"],
                arguments["course_name"]
            )
            
        elif name == "get_course_distribution":
            result = query_api.get_course_distribution(arguments["course_name"])
            
        elif name == "compare_courses":
            result = query_api.compare_courses(arguments["course_names"])
            
        elif name == "get_all_courses":
            result = query_api.get_all_courses()
            
        elif name == "get_top_performers":
            result = query_api.get_top_performers(
                n=arguments.get("n", 10),
                metric=arguments.get("metric", "psam_score")
            )
            
        elif name == "get_course_popularity":
            result = query_api.get_course_popularity(
                top_n=arguments.get("top_n", 20)
            )
            
        elif name == "calculate_school_averages":
            result = query_api.calculate_school_averages()
            
        elif name == "get_dataset_stats":
            result = query_api.get_query_stats()
            
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]
        
        # Format result
        if result is None:
            return [TextContent(
                type="text",
                text="No data found for the specified query."
            )]
        
        # Convert result to formatted string
        import json
        formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
        
        return [TextContent(
            type="text",
            text=formatted_result
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing query: {str(e)}"
        )]


async def main():
    """Main entry point for MCP server."""
    await initialize_data()
    
    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())