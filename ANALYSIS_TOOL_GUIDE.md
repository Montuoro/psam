# School Results Analysis Tool

## Overview

The `analyze_school_results` tool provides comprehensive analysis of school performance data, mimicking the workflow you demonstrated in your videos:

1. **Overview**: Get high-level statistics across all courses
2. **Subject Area Summary**: Aggregate performance by subject area
3. **Trend Analysis**: Year-over-year performance comparison
4. **Course Identification**: Flag courses requiring attention
5. **Heatmap Integration**: Visual analysis of z-scores (optional)

## Based on Your Analysis Workflow

The tool replicates your video analysis approach:
- ✅ Start with overview (like the sunburst chart view)
- ✅ Identify declining trends (down arrows)
- ✅ Compare performance across subject areas
- ✅ Drill down into specific courses
- ✅ Integrate heatmap visual analysis

## How It Works

### Analysis Criteria

The tool flags courses with:

1. **Declining Performance** (trend_value < -1.0 points)
   - Compares current year vs. previous year

2. **Below School Average** (deviation > 3.0 points)
   - Flags courses significantly underperforming

3. **High Variability** (std_dev > 1.0)
   - Indicates inconsistent student performance

4. **Small Cohort Size** (default: < 10 students)
   - May indicate enrollment issues or concerns

### Priority Scoring

Courses are prioritized by number of concerns:
- **Priority 3+**: Multiple concerns requiring immediate attention
- **Priority 2**: Two concerns
- **Priority 1**: One concern

## Usage

### Via MCP (Claude Desktop or API)

```json
{
  "name": "analyze_school_results",
  "arguments": {
    "school_id": "abbotsleigh",
    "year": 2024,
    "include_heatmap_analysis": true,
    "min_cohort_size": 10
  }
}
```

### Parameters

- **school_id** (required): School identifier (e.g., "abbotsleigh", "northern-beaches")
- **year** (optional): Specific year to analyze (defaults to most recent)
- **include_heatmap_analysis** (optional): Include heatmap visual (default: true)
- **min_cohort_size** (optional): Threshold for small cohort flag (default: 10)

### Test Script

```bash
python test_analysis_tool.py
```

## Output Structure

```json
{
  "school_id": "abbotsleigh",
  "analysis_year": 2024,
  "previous_year": 2023,
  "school_statistics": {
    "overall_mean": 29.98,
    "overall_std_dev": 9.07,
    "total_courses": 42,
    "total_units": 74
  },
  "subject_area_summary": {
    "Mathematics": {
      "courses": ["Mathematics Advanced", "Mathematics Ext 1", ...],
      "avg_mean": 32.5,
      "avg_std_dev": 8.2,
      "total_students": 150,
      "declining_count": 1,
      "improving_count": 2,
      "course_count": 4
    }
  },
  "courses_requiring_attention": [
    {
      "code": "Aboriginal Studies",
      "name": "Aboriginal Studies",
      "subject_area": "Humanities",
      "current_mean": 15.1,
      "current_std_dev": 12.1,
      "cohort_size": 1,
      "trend": "declining",
      "trend_value": -2.5,
      "concerns": [
        "Performance declined by 2.50 points from 2023 to 2024",
        "Performing 14.88 points below school average",
        "High variability (std dev: 12.10) suggests inconsistent performance",
        "Small cohort size (1 students) may indicate enrollment issues"
      ],
      "insights": [],
      "priority": 4
    }
  ],
  "total_courses_flagged": 42,
  "summary_insights": {
    "high_priority_courses": ["Aboriginal Studies", "Ancient History", ...],
    "most_declining": ["Course A", "Course B", ...],
    "subject_areas_of_concern": ["Humanities", "Arts"]
  }
}
```

## Example Analysis

From Abbotsleigh 2024 analysis:

### Top Priority Courses

1. **Aboriginal Studies** (Priority 3)
   - Mean: 15.1 (14.88 points below average)
   - Cohort: 1 student
   - High variability: 12.10 std dev
   - **Recommendation**: Review curriculum delivery and student support

2. **Ancient History** (Priority 3)
   - Mean: 22.7 (7.28 points below average)
   - Cohort: 8 students
   - High variability: 11.30 std dev
   - **Recommendation**: Examine teaching methods and assessment strategies

3. **Music 1** (Priority 3)
   - Mean: 21.1 (8.88 points below average)
   - Cohort: 3 students
   - **Recommendation**: Consider program viability or targeted interventions

## Integration with Heatmaps

When `include_heatmap_analysis: true`, the tool includes:
- Visual heatmap showing z-scores across all courses
- Color-coded performance indicators
- Complements numerical analysis with visual patterns

## Interpreting Results

### Quick Start Questions

1. **What are my highest priority courses?**
   - Check `summary_insights.high_priority_courses`

2. **Which subject areas need attention?**
   - Review `summary_insights.subject_areas_of_concern`

3. **What courses are declining?**
   - Look for courses with `trend: "declining"`
   - Check `summary_insights.most_declining`

4. **Are there enrollment concerns?**
   - Filter courses with small `cohort_size`

### Drill-Down Workflow

1. **Start with subject_area_summary** for the big picture
2. **Identify subject areas** with more declining than improving courses
3. **Review courses_requiring_attention** for specific issues
4. **Use heatmap** to visualize patterns across all metrics
5. **Query database** for detailed student-level data (using `query_database` tool)

## Next Steps

After running the analysis:

1. **Investigate Root Causes**
   - Use `query_database` to examine student-level data
   - Review historical trends with different `year` parameters
   - Analyze heatmaps for visual patterns

2. **Compare with Heatmaps**
   - Use `analyze_heatmap` to see z-score distributions
   - Identify courses performing poorly across multiple metrics

3. **Deep Dive**
   - Query specific course results
   - Examine teacher assignments
   - Review assessment patterns

## Technical Notes

- Uses `course_summary` table for aggregate metrics
- Joins with `course_result` for cohort sizes
- Handles null values in course codes and subject areas
- Sorts by priority (most concerns first), then by trend value (most declining first)

## Limitations

- Requires at least 2 years of data for trend analysis
- Small cohort sizes may show high variability naturally
- Subject area grouping depends on database categorization
- Does not account for external factors (e.g., teacher changes, curriculum updates)

## Questions?

The tool mirrors your video analysis workflow and should help you quickly:
- **Understand** school performance at a high level
- **Identify** courses requiring attention
- **Drill down** into specific areas for improvement insights
