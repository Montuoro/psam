#!/usr/bin/env python3
"""
Test the v3 integration in the MCP server
"""

from analyze_school_results_v3 import analyze_school_results_v3
from pathlib import Path

# Test with Abbotsleigh
BASE_DIR = Path(__file__).parent
CAPSULES_DIR = BASE_DIR / "capsules"
OUTPUT_DIR = CAPSULES_DIR / "output"
HEATMAPS_DIR = CAPSULES_DIR / "heatmaps"

school_id = "abbotsleigh"
db_file = OUTPUT_DIR / f"{school_id}.db"

print(f"Testing v3 analysis for {school_id}...")
print(f"Database: {db_file}")
print(f"Database exists: {db_file.exists()}")

if db_file.exists():
    try:
        result = analyze_school_results_v3(
            school_id=school_id,
            db_path=str(db_file),
            heatmaps_dir=str(HEATMAPS_DIR),
            output_dir=str(BASE_DIR),
            target_year=None
        )

        report_path = result.get('markdown_report')

        print(f"\n[SUCCESS] Analysis successful!")
        print(f"Report generated: {report_path}")

        if report_path and Path(report_path).exists():
            # Check report size
            report_size = Path(report_path).stat().st_size
            print(f"Report size: {report_size:,} bytes")

            # Read first 500 chars
            with open(report_path, 'r', encoding='utf-8') as f:
                preview = f.read(500)
            print(f"\nReport preview:\n{preview}...")
        else:
            print("[ERROR] Report file not found")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("[ERROR] Database not found")
