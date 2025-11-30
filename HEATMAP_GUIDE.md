# Heatmap Integration Guide

## Overview

Heatmaps are **the fundamental PSAM summary view** - they provide a 10,000-foot establishing shot of school performance across all courses and metrics. Each heatmap shows z-scores that summarize student results, with the Total column representing the mean z-score (excluding cohort size).

## Directory Structure

```
capsules/
└── heatmaps/
    ├── abbotsleigh/
    │   ├── abbotsleigh_heat_1.png
    │   └── abbotsleigh_heat_2.png
    └── northern-beaches/
        └── (your heatmaps here)
```

## Adding Heatmaps for New Schools

When analyzing a new school, simply:

1. Create a directory under `capsules/heatmaps/` with the school's file_id:
   ```bash
   mkdir "capsules/heatmaps/your-school-name"
   ```

2. Copy your heatmap PNG files into that directory:
   ```bash
   cp your_heatmap_*.png "capsules/heatmaps/your-school-name/"
   ```

3. The MCP server will automatically detect and serve them - no configuration needed!

## Naming Convention

- Use the school's `file_id` for the directory name (e.g., "abbotsleigh", "northern-beaches")
- Name heatmaps descriptively (e.g., "abbotsleigh_heat_1.png", "abbotsleigh_heat_2.png")
- Multi-part heatmaps: use `_1`, `_2` suffixes for continuation sheets

## Available MCP Tools

### 1. list_heatmaps
Lists all available heatmap images.

**Usage:**
```python
# List all heatmaps
{"school_id": null}

# List heatmaps for specific school
{"school_id": "abbotsleigh"}
```

**Returns:**
```json
{
  "heatmaps": [
    {
      "school_id": "abbotsleigh",
      "filename": "abbotsleigh_heat_1",
      "full_filename": "abbotsleigh_heat_1.png",
      "path": "C:\\data projects\\mcp\\capsules\\heatmaps\\abbotsleigh\\abbotsleigh_heat_1.png"
    }
  ],
  "count": 2
}
```

### 2. analyze_heatmap
Retrieves and analyzes a specific heatmap image.

**Usage:**
```python
{
  "school_id": "abbotsleigh",
  "heatmap_name": "abbotsleigh_heat_1"
}
```

**Returns:**
- JSON metadata with description
- Base64-encoded PNG image for visual analysis

### 3. get_school_overview
Provides comprehensive school overview combining database stats and heatmap availability.

**Usage:**
```python
{"school_id": "abbotsleigh"}
```

**Returns:**
```json
{
  "school_id": "abbotsleigh",
  "database_stats": {
    "tables": ["students", "courses", "course_results", ...],
    "table_count": 15,
    "record_counts": {
      "students": 965,
      "courses": 208,
      "course_results": 5217
    }
  },
  "heatmaps": [
    {
      "filename": "abbotsleigh_heat_1",
      "full_filename": "abbotsleigh_heat_1.png",
      "path": "..."
    }
  ],
  "summary": {
    "status": "success",
    "imported": {...}
  }
}
```

## Understanding Heatmap Data

### Heatmap Structure
- **Rows**: Courses (e.g., English Advanced, Mathematics, etc.)
- **Columns**: Performance metrics (z-scores)
  1. Cohort Size
  2. Scaled Score to Mean
  3. Scaled Mark Mean to Previous Year
  4. State Z-Score
  5. Course Rank
  6. Course Contribution to Aggregate
  7. Percentage of Units Counting
  8. MXP Score Lower/Upper 50%
  9. 2-Year Scaled Mark Comparisons
  10. **Total** (mean z-score, excluding cohort size)

### Color Coding
- **Dark Blue**: High positive z-scores (strong performance)
- **Light Blue**: Moderate positive z-scores
- **Gray/Tan**: Negative z-scores (below average)
- **Darker Gray**: More negative z-scores

### Total Column
The rightmost "Total" column is the **key metric** - it represents the mean z-score across all metrics (excluding cohort size), providing a single summary score for each course's overall performance.

## Integration with Database Analysis

The heatmap provides the essential context for deeper database queries:

1. **Start with heatmap** - Get the 10,000-foot view using `analyze_heatmap` or `get_school_overview`
2. **Identify areas of interest** - Note courses with strong or weak Total scores
3. **Drill down with queries** - Use `query_database` to investigate specific courses, students, or patterns

Example workflow:
```
1. analyze_heatmap("abbotsleigh", "abbotsleigh_heat_1")
   → Notice Mathematics Advanced has Total = +0.18 (positive)

2. query_database("abbotsleigh", "SELECT * FROM courses WHERE course_name LIKE '%Mathematics Advanced%'")
   → Get course details

3. query_database("abbotsleigh", "SELECT * FROM course_results WHERE course_id = [id] ORDER BY scaled_mark DESC")
   → Examine individual student results
```

## Best Practices

1. **Always start with the overview**: Use `get_school_overview` first to understand available data
2. **View heatmaps holistically**: Don't focus on single metrics - the Total column provides the summary
3. **Context matters**: Heatmaps show **relative** performance (z-scores), not absolute scores
4. **Multi-part heatmaps**: View all parts (_1, _2, etc.) to see the complete course list
5. **Combine with database**: Use heatmap insights to guide specific database queries

## Example Analysis Session

```python
# 1. Start with overview
get_school_overview("abbotsleigh")

# 2. View heatmaps to identify patterns
analyze_heatmap("abbotsleigh", "abbotsleigh_heat_1")
analyze_heatmap("abbotsleigh", "abbotsleigh_heat_2")

# 3. Investigate specific courses from heatmap
query_database("abbotsleigh", "SELECT * FROM courses WHERE course_name = 'Japanese in Context'")
# (Japanese in Context showed Total = +3.19 in heatmap)

# 4. Deep dive into results
query_database("abbotsleigh", "SELECT * FROM course_results WHERE course_id = [...] LIMIT 50")
```

## Troubleshooting

**Heatmap not showing up:**
- Check the directory name matches the school's `file_id` exactly
- Verify PNG files are in the correct location
- Restart the MCP server (Claude Desktop restart)

**Image analysis not working:**
- Ensure PNG files are valid and not corrupted
- Check file permissions are readable

**School overview missing heatmaps:**
- Verify heatmaps directory exists: `capsules/heatmaps/[school_id]/`
- Check PNG files have `.png` extension (case-sensitive on some systems)
