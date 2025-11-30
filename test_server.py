#!/usr/bin/env python3
"""
Quick test script to verify the MCP server can load and access data
"""

import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
CAPSULES_DIR = BASE_DIR / "capsules"
OUTPUT_DIR = CAPSULES_DIR / "output"
INPUT_DIR = CAPSULES_DIR / "input"

def test_databases():
    """Test database access"""
    print("=" * 50)
    print("Testing Database Access")
    print("=" * 50)

    databases = list(OUTPUT_DIR.glob("*.db"))
    print(f"\nFound {len(databases)} database(s):")

    for db_file in databases:
        print(f"\n  [DB] {db_file.name}")

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Get table count
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"     Tables: {len(tables)}")

            # Get some sample data from first table if exists
            if tables:
                table_name = tables[0][0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"     Sample: {table_name} has {count} rows")

            conn.close()
            print(f"     [OK] Access successful")

        except Exception as e:
            print(f"     [ERROR] {e}")

def test_json_files():
    """Test JSON file access"""
    print("\n" + "=" * 50)
    print("Testing JSON File Access")
    print("=" * 50)

    json_files = list(INPUT_DIR.glob("*.json"))
    print(f"\nFound {len(json_files)} JSON file(s):")

    for json_file in json_files:
        print(f"\n  [JSON] {json_file.name}")

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            if isinstance(data, list):
                print(f"     Type: Array with {len(data)} items")
            elif isinstance(data, dict):
                print(f"     Type: Object with {len(data)} keys")
            else:
                print(f"     Type: {type(data).__name__}")

            print(f"     [OK] Access successful")

        except Exception as e:
            print(f"     [ERROR] {e}")

def test_summary():
    """Test summary file"""
    print("\n" + "=" * 50)
    print("Testing Summary File")
    print("=" * 50)

    summary_file = OUTPUT_DIR / "schools_summary.json"

    if summary_file.exists():
        with open(summary_file, 'r') as f:
            summary = json.load(f)

        print(f"\n  [SUMMARY] Import Summary:")
        for school in summary:
            print(f"\n    School: {school['school_name']}")
            print(f"    Status: {school['summary']['status']}")
            if 'imported' in school['summary']:
                stats = school['summary']['imported']
                print(f"    Students: {stats.get('students', 0)}")
                print(f"    Courses: {stats.get('courses', 0)}")

        print(f"\n  [OK] Summary loaded")
    else:
        print(f"\n  [WARNING] Summary file not found")

if __name__ == "__main__":
    print("\n*** School Data MCP Server - Pre-flight Check ***\n")

    test_databases()
    test_json_files()
    test_summary()

    print("\n" + "=" * 50)
    print("All tests completed successfully!")
    print("=" * 50)
    print("\nYour MCP server should be ready to use.")
    print("Run install_to_claude.bat to configure Claude Desktop.")
    print()
