#!/usr/bin/env python3
"""
V6 FULL: Complete unified report combining V4 structure with V5 deep analysis

Single comprehensive report with:
- V4: Multi-year trends, fixed scaling, departmental analysis
- V5: School-specific calculations, advanced cross-course, deep discoveries, enhanced heatmap
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent))

# Import V4 base functions
from analyze_school_results_v4 import get_multiyear_trends, get_atar_analysis
from analyze_school_results_v3 import get_course_detail_metrics, categorize_course, SUBJECT_MAPPINGS
from analyze_school_results_v2 import analyze_school_results_v2

# Import V5 deep analysis functions
from analyze_school_results_v5 import (
    calculate_school_specific_scaling_impact,
    get_advanced_cross_course_insights,
    get_deep_database_discoveries,
    analyze_heatmap_deeply
)

def generate_v6_course_analysis(course, conn, analysis_year, school_atar_avg, heatmap_path):
    """
    Generate complete V6 analysis for a single course
    Combines V4 breadth with V5 depth
    """
    course_name = course['name']

    # Get all data
    metrics = get_course_detail_metrics(conn, course_name, analysis_year)
    multiyear = get_multiyear_trends(conn, course_name, analysis_year, years_back=4)

    # V5 enhancements
    scaling_impact = calculate_school_specific_scaling_impact(conn, course_name, analysis_year)
    advanced_insights = get_advanced_cross_course_insights(conn, course_name, analysis_year)
    deep_discoveries = get_deep_database_discoveries(conn, course_name, analysis_year)

    # V4 basic correlations
    from analyze_school_results_v4 import get_cross_course_correlations
    correlations = get_cross_course_correlations(conn, course_name, analysis_year)

    return {
        'metrics': metrics,
        'multiyear': multiyear,
        'scaling_impact': scaling_impact,
        'advanced_insights': advanced_insights,
        'deep_discoveries': deep_discoveries,
        'correlations': correlations
    }

def generate_v6_markdown(analysis, school_id, heatmaps_dir, atar_analysis, enriched_courses):
    """
    Generate single unified V6 markdown report
    """
    md = []

    analysis_year = analysis['analysis_year']
    previous_year = analysis['previous_year']
    stats = analysis['school_statistics']
    school_atar_avg = atar_analysis['stats']['avg_atar']

    # Header
    md.append(f"# {school_id.title()} - Complete Performance Analysis {analysis_year} (V6)")
    md.append(f"")
    md.append(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y')}")
    md.append(f"**Analysis Year:** {analysis_year}")
    md.append(f"**Multi-Year Depth:** 2020-{analysis_year} (5 years)")
    md.append(f"**Enhancements:** School-specific scaling, advanced cross-course patterns, deep discoveries")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # ATAR Overview
    md.append(f"## ATAR Performance Overview")
    md.append(f"")
    md.append(f"| Metric | Value |")
    md.append(f"|--------|-------|")
    md.append(f"| **Average ATAR** | {atar_analysis['stats']['avg_atar']:.2f} |")
    md.append(f"| **Range** | {atar_analysis['stats']['min_atar']:.1f} - {atar_analysis['stats']['max_atar']:.1f} |")
    md.append(f"| **Total Students** | {atar_analysis['stats']['total_students']} |")
    md.append(f"| **Course Mean** | {stats['overall_mean']:.2f} |")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # Executive Summary
    md.append(f"## Executive Summary")
    md.append(f"")
    md.append(f"**{stats['total_courses']} Courses Analyzed:**")
    md.append(f"- **{len(analysis['courses_of_concern'])} Courses of Concern**")
    md.append(f"- **{len(analysis['middling_courses'])} Middling Courses**")
    md.append(f"- **{len(analysis['high_performers'])} High Performers**")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # Departmental Analysis
    md.append(f"## Departmental Analysis")
    md.append(f"")

    heatmap_path = Path(heatmaps_dir) / school_id / "abbotsleigh_heat_1.png"

    for dept, dept_data in analysis['departments'].items():
        md.append(f"### {dept}")
        md.append(f"")
        md.append(f"**Portfolio:** {dept_data['total_courses']} courses | {dept_data['total_students']} students")
        md.append(f"")

        # Courses of Concern with FULL V6 analysis
        if dept_data['courses_of_concern']:
            md.append(f"#### Courses Requiring Intervention ({len(dept_data['courses_of_concern'])})")
            md.append(f"")

            for course in dept_data['courses_of_concern']:
                enrichment = enriched_courses.get(course['name'], {})

                md.append(f"##### {course['name']}")
                md.append(f"")

                # Performance Summary with multi-year
                md.append(f"**Performance:**")
                md.append(f"- Mean: **{course['mean']:.1f}** ({course['deviation']:+.2f} vs avg)")
                md.append(f"- Cohort: {course['cohort_size']} students")

                if enrichment.get('multiyear'):
                    my_data = enrichment['multiyear']['historical_data']
                    years_str = ', '.join([f"{d['year']}={d['mean']:.1f}" for d in reversed(my_data)])
                    md.append(f"- **5-Year Trend:** {years_str}")

                md.append(f"")

                # V5 DEEP ANALYSIS
                md.append(f"**Deep Analysis:**")

                # School-specific scaling
                if enrichment.get('scaling_impact') and enrichment['scaling_impact']['sample_size'] >= 3:
                    si = enrichment['scaling_impact']
                    atar_gain = si['atar_per_hsc_point'] * 10
                    md.append(f"")
                    md.append(f"**School-Specific Impact ({si['sample_size']} students):** +10 HSC points = +{atar_gain:.1f} ATAR points at THIS school")

                # True ATAR contribution
                if enrichment.get('metrics'):
                    m = enrichment['metrics']
                    if m.get('avg_scaled') and m.get('avg_combined'):
                        contrib = m['avg_scaled'] * 2
                        md.append(f"**ATAR Contribution:** {m['avg_combined']:.1f} HSC → {contrib:.1f} units (penalty: {abs(contrib - m['avg_combined']):.1f}pts)")

                # Advanced cross-course patterns
                if enrichment.get('advanced_insights') and enrichment['advanced_insights'].get('combinations'):
                    combos = enrichment['advanced_insights']['combinations']
                    if len(combos) >= 3:
                        import numpy as np
                        atar_by_combo = defaultdict(list)
                        for c in combos:
                            atar_by_combo[c['course2']].append(c['atar'])
                        best = sorted(atar_by_combo.items(), key=lambda x: np.mean(x[1]), reverse=True)[:2]
                        md.append(f"**Best Combinations:** {', '.join([f'{b[0]} ({np.mean(b[1]):.1f})' for b in best])}")

                # Cross-course struggles
                if enrichment.get('correlations'):
                    struggling = [c['course'] for c in enrichment['correlations'][:3] if c['avg_mark'] < 85]
                    if struggling:
                        md.append(f"**Struggles alongside:** {', '.join(struggling)}")

                md.append(f"")

                # Deep discoveries
                if enrichment.get('deep_discoveries'):
                    md.append(f"**Deep Discoveries:**")
                    for disc in enrichment['deep_discoveries'][:3]:
                        if disc['type'] == 'performance_clustering':
                            md.append(f"- Bimodal: {disc['lower_cluster']['count']}@{disc['lower_cluster']['avg']:.0f} vs {disc['upper_cluster']['count']}@{disc['upper_cluster']['avg']:.0f}")
                        elif disc['type'] == 'relative_performance_analysis':
                            md.append(f"- Relative: {disc['overperformers']} overperform (+{disc['avg_overperformance']:.1f}), {disc['underperformers']} underperform ({disc['avg_underperformance']:.1f})")
                    md.append(f"")

                # Deep heatmap
                if heatmap_path.exists():
                    md.append(f"**Heatmap Deep-Dive (`{heatmap_path.name}`):**")
                    md.append(f"- Multi-column: Check if cols 2 & 3 both negative (compounding decline)")
                    md.append(f"- Department context: Compare to other {dept} courses for patterns")
                    md.append(f"- Trajectory: Cols 10-11 show if decline affects top/bottom students")
                    md.append(f"")

                md.append(f"---")
                md.append(f"")

        # High Performers (abbreviated)
        if dept_data['high_performers']:
            md.append(f"#### High Performers ({len(dept_data['high_performers'])})")
            md.append(f"")
            for course in dept_data['high_performers']:
                enrichment = enriched_courses.get(course['name'], {})
                md.append(f"**{course['name']}:** {course['mean']:.1f} ({course['cohort_size']} students)")
                if enrichment.get('multiyear'):
                    my_data = enrichment['multiyear']['historical_data']
                    years_str = ', '.join([f"{d['year']}={d['mean']:.1f}" for d in reversed(my_data)])
                    md.append(f"  - 5-Year: {years_str}")
            md.append(f"")

        md.append(f"")

    # Conclusion
    md.append(f"## Strategic Priorities")
    md.append(f"")
    md.append(f"Focus on {len(analysis['courses_of_concern'])} courses of concern with targeted, evidence-based interventions.")
    md.append(f"")
    md.append(f"*V6 Complete: Multi-year trends + school-specific scaling + advanced patterns + deep discoveries + enhanced heatmap analysis*")
    md.append(f"")

    return "\n".join(md)

def analyze_school_results_v6(school_id, db_path, heatmaps_dir, output_dir, target_year=None):
    """
    V6 FULL: Single comprehensive report with all enhancements
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get years
    cursor.execute("SELECT DISTINCT year FROM course_summary ORDER BY year DESC")
    available_years = [row[0] for row in cursor.fetchall()]

    if not available_years:
        conn.close()
        return {"error": "No data"}

    analysis_year = target_year if target_year and target_year in available_years else available_years[0]
    previous_year = analysis_year - 1 if (analysis_year - 1) in available_years else None

    # Get ATAR analysis
    atar_analysis = get_atar_analysis(conn, analysis_year)
    school_atar_avg = atar_analysis['stats']['avg_atar']

    # Run v2 for structure
    analysis = analyze_school_results_v2(school_id, db_path, heatmaps_dir, output_dir, target_year)

    # Enrich ALL courses with V6 data
    heatmap_path = Path(heatmaps_dir) / school_id / "abbotsleigh_heat_1.png" if Path(heatmaps_dir).exists() else None

    enriched_courses = {}

    print(f"Enriching {len(analysis['courses_of_concern'])} courses of concern...")
    for course in analysis['courses_of_concern']:
        enriched_courses[course['name']] = generate_v6_course_analysis(
            course, conn, analysis_year, school_atar_avg, heatmap_path
        )

    print(f"Enriching {len(analysis['high_performers'])} high performers...")
    for course in analysis['high_performers']:
        enriched_courses[course['name']] = generate_v6_course_analysis(
            course, conn, analysis_year, school_atar_avg, heatmap_path
        )

    # Generate V6 markdown
    print("Generating V6 unified report...")
    md_content = generate_v6_markdown(
        analysis, school_id, heatmaps_dir, atar_analysis, enriched_courses
    )

    # Save
    md_filename = f"{school_id}_{analysis_year}_analysis_v6_full.md"
    output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
    md_path = output_path / md_filename
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    conn.close()

    print(f"V6 Complete: {md_path}")

    return {
        'markdown_report': str(md_path),
        'analysis_year': analysis_year,
        'version': 'v6',
        **analysis
    }

if __name__ == "__main__":
    print("Testing V6 Full...")
    BASE_DIR = Path(__file__).parent
    result = analyze_school_results_v6(
        "abbotsleigh",
        str(BASE_DIR / "capsules/output/abbotsleigh.db"),
        str(BASE_DIR / "capsules/heatmaps"),
        str(BASE_DIR)
    )
    print(f"\nV6 Report: {result['markdown_report']}")
