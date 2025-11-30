#!/usr/bin/env python3
"""
Test script to verify heatmap functionality
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
HEATMAPS_DIR = BASE_DIR / "capsules" / "heatmaps"

def test_heatmap_structure():
    """Test that heatmap directory structure is correct"""
    print("=" * 50)
    print("Testing Heatmap Directory Structure")
    print("=" * 50)

    if not HEATMAPS_DIR.exists():
        print("[ERROR] Heatmaps directory does not exist!")
        return False

    print(f"[OK] Heatmaps directory exists: {HEATMAPS_DIR}")

    # Check for school directories
    school_dirs = [d for d in HEATMAPS_DIR.iterdir() if d.is_dir()]
    print(f"\n[INFO] Found {len(school_dirs)} school directories:")

    for school_dir in school_dirs:
        print(f"\n  School: {school_dir.name}")

        # Count PNG files
        png_files = list(school_dir.glob("*.png"))
        print(f"    Heatmaps: {len(png_files)}")

        for png_file in png_files:
            size_kb = png_file.stat().st_size / 1024
            print(f"      - {png_file.name} ({size_kb:.1f} KB)")

    return True

def test_heatmap_listing():
    """Test listing heatmaps programmatically (simulating MCP tool)"""
    print("\n" + "=" * 50)
    print("Testing Heatmap Listing Logic")
    print("=" * 50)

    heatmaps = []

    if HEATMAPS_DIR.exists():
        for school_dir in HEATMAPS_DIR.iterdir():
            if school_dir.is_dir():
                for heatmap_file in school_dir.glob("*.png"):
                    heatmaps.append({
                        "school_id": school_dir.name,
                        "filename": heatmap_file.stem,
                        "full_filename": heatmap_file.name,
                        "path": str(heatmap_file)
                    })

    print(f"\n[INFO] Found {len(heatmaps)} total heatmaps")
    print(json.dumps({"heatmaps": heatmaps, "count": len(heatmaps)}, indent=2))

    return len(heatmaps) > 0

def test_heatmap_access():
    """Test that heatmap files can be read"""
    print("\n" + "=" * 50)
    print("Testing Heatmap File Access")
    print("=" * 50)

    test_cases = [
        ("abbotsleigh", "abbotsleigh_heat_1"),
        ("abbotsleigh", "abbotsleigh_heat_2"),
    ]

    for school_id, heatmap_name in test_cases:
        heatmap_file = HEATMAPS_DIR / school_id / f"{heatmap_name}.png"

        print(f"\n[TEST] {school_id}/{heatmap_name}")

        if heatmap_file.exists():
            # Try to read the file
            try:
                with open(heatmap_file, 'rb') as f:
                    data = f.read()
                    size_kb = len(data) / 1024
                    print(f"  [OK] Successfully read {size_kb:.1f} KB")

                    # Verify it's a PNG
                    if data[:8] == b'\x89PNG\r\n\x1a\n':
                        print(f"  [OK] Valid PNG header detected")
                    else:
                        print(f"  [WARNING] File may not be a valid PNG")

            except Exception as e:
                print(f"  [ERROR] Failed to read file: {e}")
                return False
        else:
            print(f"  [ERROR] File not found: {heatmap_file}")
            return False

    return True

def test_school_overview_data():
    """Test gathering school overview data"""
    print("\n" + "=" * 50)
    print("Testing School Overview Data")
    print("=" * 50)

    school_id = "abbotsleigh"
    print(f"\n[TEST] Getting overview for {school_id}")

    # Simulate the overview logic
    school_heatmap_dir = HEATMAPS_DIR / school_id
    heatmaps = []

    if school_heatmap_dir.exists():
        for heatmap_file in sorted(school_heatmap_dir.glob("*.png")):
            heatmaps.append({
                "filename": heatmap_file.stem,
                "full_filename": heatmap_file.name,
                "path": str(heatmap_file)
            })

    overview = {
        "school_id": school_id,
        "heatmaps": heatmaps,
        "heatmap_count": len(heatmaps)
    }

    print(json.dumps(overview, indent=2))

    return len(heatmaps) > 0

if __name__ == "__main__":
    print("\n*** Heatmap Integration Test Suite ***\n")

    tests = [
        ("Directory Structure", test_heatmap_structure),
        ("Heatmap Listing", test_heatmap_listing),
        ("File Access", test_heatmap_access),
        ("School Overview", test_school_overview_data),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed! Heatmap integration is ready.")
        print("\nNext step: Restart Claude Desktop to activate the changes.")
    else:
        print("\n[WARNING] Some tests failed. Please review the errors above.")
