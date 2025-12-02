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

# Import student-level analysis
from analyze_students_v1 import get_student_multi_course_patterns, get_course_rank_analysis

# Import comprehensive school statistics
from analyze_school_stats_comprehensive import (
    get_multi_year_cohort_trends,
    analyze_atar_contribution_percentiles,
    analyze_mxp_performance,
    analyze_rank_changes_assessment_to_exam,
    analyze_rank_to_scaled_progression,
    analyze_relative_course_performance,
    analyze_course_synergies_expanded,
    analyze_nesa_bands,
    analyze_course_atar_correlation
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

    # V6: Student-level rank analysis
    rank_analysis = get_course_rank_analysis(conn, course_name, analysis_year)

    # V6: Comprehensive school statistics (all 10 points)
    comp_stats = {
        'cohort_trends': get_multi_year_cohort_trends(conn, course_name, analysis_year),
        'atar_contribution': analyze_atar_contribution_percentiles(conn, course_name, analysis_year),
        'mxp_performance': analyze_mxp_performance(conn, course_name, analysis_year),
        'rank_changes': analyze_rank_changes_assessment_to_exam(conn, course_name, analysis_year),
        'rank_progression': analyze_rank_to_scaled_progression(conn, course_name, analysis_year),
        'relative_performance': analyze_relative_course_performance(conn, course_name, analysis_year),
        'synergies': analyze_course_synergies_expanded(conn, course_name, analysis_year),
        'bands': analyze_nesa_bands(conn, course_name, analysis_year),
        'atar_correlation': analyze_course_atar_correlation(conn, course_name, analysis_year)
    }

    return {
        'metrics': metrics,
        'multiyear': multiyear,
        'scaling_impact': scaling_impact,
        'advanced_insights': advanced_insights,
        'deep_discoveries': deep_discoveries,
        'correlations': correlations,
        'rank_analysis': rank_analysis,
        'comp_stats': comp_stats
    }

def generate_v6_markdown(analysis, school_id, heatmaps_dir, atar_analysis, enriched_courses, conn, analysis_year):
    """
    Generate single unified V6 markdown report
    """
    md = []

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

    # STUDENT-LEVEL INTERVENTION TARGETS
    md.append(f"## Student Intervention Priorities")
    md.append(f"")

    student_patterns = get_student_multi_course_patterns(conn, analysis_year, school_atar_avg)

    if student_patterns['concerning_students']:
        high_priority = [s for s in student_patterns['concerning_students'] if s['priority'] == 'high']
        medium_priority = [s for s in student_patterns['concerning_students'] if s['priority'] == 'medium']

        md.append(f"**{len(student_patterns['concerning_students'])} Students Requiring Targeted Intervention:**")
        md.append(f"- {len(high_priority)} High Priority (struggling in 4+ courses)")
        md.append(f"- {len(medium_priority)} Medium Priority (specific weak areas or 3 courses)")
        md.append(f"")

        if high_priority:
            md.append(f"### High Priority Students")
            md.append(f"")
            for student in high_priority[:5]:  # Top 5
                courses_list = ', '.join([c['name'] for c in student['low_marks'][:5]])
                md.append(f"**Student ID {student['student_id']}** (ATAR: {student['atar']:.1f}, {student['atar_gap']:+.1f} vs school avg)")
                md.append(f"- Struggling in {len(student['low_marks'])} courses: {courses_list}")
                if student.get('large_gaps'):
                    gap_courses = ', '.join([c['name'] for c in student['large_gaps'][:3]])
                    md.append(f"- Large assessment-exam gaps in: {gap_courses} (possible exam anxiety)")
                md.append(f"- **Action**: Immediate multi-course intervention plan required")
                md.append(f"")

        if medium_priority:
            md.append(f"### Medium Priority Students")
            md.append(f"")
            for student in medium_priority[:5]:  # Top 5
                if student.get('note'):
                    courses_list = ', '.join([c['name'] for c in student.get('outliers', [])[:3]])
                    md.append(f"**Student ID {student['student_id']}** (ATAR: {student['atar']:.1f}) - {student['note']}")
                    md.append(f"- Weak areas: {courses_list}")
                else:
                    courses_list = ', '.join([c['name'] for c in student['low_marks'][:3]])
                    md.append(f"**Student ID {student['student_id']}** (ATAR: {student['atar']:.1f})")
                    md.append(f"- Needs support in: {courses_list}")
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
                md.append(f"")

                # School-specific scaling (FULL DETAIL)
                if enrichment.get('scaling_impact') and enrichment['scaling_impact']['sample_size'] >= 3:
                    si = enrichment['scaling_impact']
                    atar_gain = si['atar_per_hsc_point'] * 10
                    md.append(f"**School-Specific Scaling Impact (CALCULATED FROM {si['sample_size']} STUDENTS AT THIS SCHOOL):** For every 10-point HSC improvement in {course['name']}, students at THIS SCHOOL gain {atar_gain:.2f} ATAR points on average. HSC-to-Scaled conversion rate: {si['hsc_to_scaled_slope']:.2f}x (correlation: {si['hsc_to_scaled_corr']:.2f}). This is based on actual student outcomes, not state-wide averages.")
                    md.append(f"")

                # True ATAR contribution
                if enrichment.get('metrics'):
                    m = enrichment['metrics']
                    if m.get('avg_scaled') and m.get('avg_combined'):
                        contrib = m['avg_scaled'] * 2
                        md.append(f"**True ATAR Contribution:** Raw HSC mark {m['avg_combined']:.1f} scales to {contrib:.1f} unit contribution (penalty: {abs(contrib - m['avg_combined']):.1f} points).")
                        md.append(f"")

                # BASIC COURSE OVERVIEW
                md.append(f"**Course Overview:**")

                # Year-over-year comparison
                if enrichment.get('multiyear') and len(enrichment['multiyear']['historical_data']) >= 2:
                    hist = enrichment['multiyear']['historical_data']
                    # hist is ordered DESC (newest first), so [0] is current, [1] is prev
                    current_year = hist[0]
                    prev_year = hist[1]
                    yoy_change = current_year['mean'] - prev_year['mean']
                    direction = "↑" if yoy_change > 0.5 else "↓" if yoy_change < -0.5 else "→"
                    md.append(f"- Year-over-year: {prev_year['mean']:.1f} ({prev_year['year']}) {direction} {current_year['mean']:.1f} ({current_year['year']}) | Change: {yoy_change:+.1f} points")

                # Band distribution
                if enrichment.get('metrics') and enrichment['metrics'].get('band_distribution'):
                    bands = enrichment['metrics']['band_distribution']
                    total_students = sum(bands.values())
                    if 'Band 6' in bands or 'Band 5' in bands:
                        top_bands = bands.get('Band 6', 0) + bands.get('Band 5', 0)
                        top_pct = (top_bands / total_students * 100) if total_students > 0 else 0
                        md.append(f"- Bands: {top_pct:.0f}% in Band 5-6 ({', '.join([f'B{k[-1]}={v}' for k, v in sorted(bands.items(), reverse=True)])})")

                # Assessment vs Exam (basic)
                if enrichment.get('metrics'):
                    m = enrichment['metrics']
                    if m.get('avg_assessment') and m.get('avg_exam'):
                        gap = m['avg_assessment'] - m['avg_exam']
                        gap_type = "over-assess" if gap > 2 else "under-assess" if gap < -2 else "aligned"
                        md.append(f"- Assessment vs Exam: Internal {m['avg_assessment']:.1f} vs Exam {m['avg_exam']:.1f} (gap: {gap:+.1f}, {gap_type})")

                # Student ATAR cohort average
                if enrichment.get('metrics') and enrichment['metrics'].get('avg_atar_in_course'):
                    course_atar = enrichment['metrics']['avg_atar_in_course']
                    atar_diff = course_atar - school_atar_avg
                    cohort_type = "higher-achieving" if atar_diff > 5 else "lower-achieving" if atar_diff < -5 else "typical"
                    md.append(f"- Cohort ATAR: Students in this course average {course_atar:.1f} ATAR ({cohort_type}, {atar_diff:+.1f} vs school avg)")

                md.append(f"")

                # RANK-BASED ANALYSIS (Specific Students)
                if enrichment.get('rank_analysis'):
                    ra = enrichment['rank_analysis']
                    md.append(f"**Class Rankings & Gaps:**")

                    # Top performers
                    top_3 = ra['top_10'][:3]
                    md.append(f"- Top 3: Student {top_3[0]['student_id']} ({top_3[0]['mark']:.1f}, ATAR {top_3[0]['atar']:.1f}), Student {top_3[1]['student_id']} ({top_3[1]['mark']:.1f}), Student {top_3[2]['student_id']} ({top_3[2]['mark']:.1f})")

                    # Bottom performers (needs intervention)
                    bottom_3 = ra['bottom_10'][-3:]
                    md.append(f"- **Bottom 3 (INTERVENTION NEEDED):** Student {bottom_3[2]['student_id']} ({bottom_3[2]['mark']:.1f}, ATAR {bottom_3[2]['atar']:.1f}), Student {bottom_3[1]['student_id']} ({bottom_3[1]['mark']:.1f}), Student {bottom_3[0]['student_id']} ({bottom_3[0]['mark']:.1f})")

                    # Largest gap
                    if ra.get('largest_gap'):
                        gap = ra['largest_gap']
                        md.append(f"- Largest performance gap: {gap['gap_size']:.1f} points between ranks {gap['between_ranks']} and {gap['between_ranks']+1} ({gap['marks']})")

                    md.append(f"")

                # COMPREHENSIVE SCHOOL STATISTICS (All 10 Points)
                if enrichment.get('comp_stats'):
                    cs = enrichment['comp_stats']
                    md.append(f"**Comprehensive Analysis:**")

                    # Point 1: Cohort trends
                    if cs.get('cohort_trends') and cs['cohort_trends'].get('changes'):
                        notable_changes = [c for c in cs['cohort_trends']['changes'] if c['notable']]
                        if notable_changes:
                            md.append(f"- Cohort: {'; '.join([c['comment'] for c in notable_changes])}")

                    # Point 4: ATAR contribution
                    if cs.get('atar_contribution'):
                        ac = cs['atar_contribution']
                        if ac['zero_contributors'] > 0:
                            md.append(f"- ATAR Impact: {ac['zero_contributors']} students (IDs: {', '.join(map(str, ac['zero_contributor_ids']))}) got NO ATAR benefit")

                    # Point 5: Relative performance
                    if cs.get('relative_performance'):
                        rp = cs['relative_performance']
                        md.append(f"- Relative: {rp['interpretation']}")

                    # Point 6: Synergies
                    if cs.get('synergies'):
                        syn = cs['synergies']
                        if syn.get('positive_synergies'):
                            pos_courses = ', '.join([s['course'] for s in syn['positive_synergies'][:3]])
                            md.append(f"- Strong pairings: {pos_courses}")
                        if syn.get('negative_synergies'):
                            neg_courses = ', '.join([s['course'] for s in syn['negative_synergies'][:3]])
                            md.append(f"- Weak pairings: {neg_courses}")

                    # Point 7: MXP
                    if cs.get('mxp_performance'):
                        mxp = cs['mxp_performance']
                        if mxp['outperformers'] > 0 or mxp['underperformers'] > 0:
                            md.append(f"- MXP: {mxp['outperformers']} exceeded expectations, {mxp['underperformers']} fell short")
                            if mxp.get('outperformer_ids'):
                                md.append(f"  - Top performers: Students {', '.join(map(str, mxp['outperformer_ids'][:3]))}")

                    # Point 8: Rank changes
                    if cs.get('rank_changes') and cs['rank_changes']['significant_changes'] > 0:
                        rc = cs['rank_changes']
                        top_changes = rc['changes'][:3]
                        changes_str = ', '.join([f"Student {c['student_id']} ({c['direction']} {abs(c['rank_change'])} ranks)" for c in top_changes])
                        md.append(f"- Rank shifts (assessment→exam): {changes_str}")

                    # Point 9: Bands
                    if cs.get('bands'):
                        b = cs['bands']
                        md.append(f"- Bands: {b['band_5_6_pct']:.0f}% in Band 5-6 ({b['band_5_6_count']}/{b['total_students']})")

                    # Point 10: ATAR correlation
                    if cs.get('atar_correlation'):
                        atc = cs['atar_correlation']
                        md.append(f"- ATAR profile: {atc['correlation']}")

                    md.append(f"")

                # Advanced cross-course patterns (FULL DETAIL)
                if enrichment.get('advanced_insights') and enrichment['advanced_insights'].get('combinations'):
                    combos = enrichment['advanced_insights']['combinations']
                    if len(combos) >= 3:
                        import numpy as np
                        atar_by_combo = defaultdict(list)
                        for c in combos:
                            atar_by_combo[c['course2']].append(c['atar'])
                        best = sorted(atar_by_combo.items(), key=lambda x: np.mean(x[1]), reverse=True)[:3]
                        md.append(f"**ADVANCED Cross-Course Pattern #1 - Best Subject Combinations:** Students taking {course['name']} perform best when also taking: {', '.join([f'{b[0]} (avg ATAR {np.mean(b[1]):.1f})' for b in best])}. Consider these synergistic pairings when advising students.")
                        md.append(f"")
                        md.append(f"**ADVANCED Cross-Course Pattern #2 - Performance Consistency:** Analyzed {len(set([c['course2'] for c in combos]))} overlapping courses. Top insight: Look for courses where same students consistently underperform (indicates skill gap) vs courses where performance varies widely (indicates interest/engagement factor).")
                        md.append(f"")

                # Cross-course struggles (V4 correlations)
                if enrichment.get('correlations'):
                    struggling = [c['course'] for c in enrichment['correlations'][:3] if c['avg_mark'] < 85]
                    if struggling:
                        md.append(f"**Cross-Course Struggle Pattern:** Students taking {course['name']} also show below-average performance in {', '.join(struggling)}. Coordinate intervention across departments.")
                        md.append(f"")

                # Deep discoveries (FULL DETAIL)
                if enrichment.get('deep_discoveries'):
                    for i, disc in enumerate(enrichment['deep_discoveries'][:3], 1):
                        if disc['type'] == 'performance_clustering':
                            md.append(f"**DEEP DISCOVERY #{i} - Performance Clustering:** Bimodal distribution detected with {disc['gap_size']:.1f} point gap. Lower cluster: {disc['lower_cluster']['count']} students averaging {disc['lower_cluster']['avg']:.1f}. Upper cluster: {disc['upper_cluster']['count']} students averaging {disc['upper_cluster']['avg']:.1f}. This indicates TWO DISTINCT student populations in this course - consider splitting into differentiated groups.")
                            md.append(f"")
                        elif disc['type'] == 'assessment_exam_breakdown':
                            top_gaps = ', '.join([f"{g['gap']:.1f}pts" for g in disc['top_gaps'][:3]])
                            corr_strength = 'positive' if disc['gap_atar_correlation'] > 0.3 else 'negative' if disc['gap_atar_correlation'] < -0.3 else 'neutral'
                            explanation = 'Students with larger gaps achieve LOWER ATARs - exam anxiety is real issue' if disc['gap_atar_correlation'] < -0.3 else 'No systematic gap-ATAR relationship'
                            md.append(f"**DEEP DISCOVERY #{i} - Assessment-Exam Gap Analysis:** Top 3 individual gaps: {top_gaps}. Gap-to-ATAR correlation: {disc['gap_atar_correlation']:.2f} ({corr_strength}). {explanation}.")
                            md.append(f"")
                        elif disc['type'] == 'relative_performance_analysis':
                            interpretation = 'strength for strong students' if disc['overperformers'] > disc['underperformers'] else 'drag on otherwise capable students'
                            md.append(f"**DEEP DISCOVERY #{i} - Relative Performance Analysis:** {disc['overperformers']} students overperform in {course['name']} vs their other courses (avg +{disc['avg_overperformance']:.1f}pts). {disc['underperformers']} students underperform (avg {disc['avg_underperformance']:.1f}pts). This course is a {interpretation}.")
                            md.append(f"")

                # Deep heatmap (FULL 4-SECTION ANALYSIS)
                if heatmap_path.exists():
                    md.append(f"**DEEP Heatmap Analysis for {course['name']}:**")
                    md.append(f"Open: `{heatmap_path.name}` - Going beyond surface observations")
                    md.append(f"")
                    md.append(f"**Multi-Column Pattern Recognition:**")
                    md.append(f"  - If Columns 2 AND 3 both negative (dark): Recent decline on top of existing underperformance")
                    md.append(f"  - If Column 2 negative but Column 4 positive: School underperforms internally but beats state")
                    md.append(f"  - If Columns 8-9 (MXP Lower/Upper 50%) diverge: Top students thriving while bottom struggle")
                    md.append(f"  - If Column 6 low but Column 7 high: Course contributes little to ATAR despite high unit counts")
                    md.append(f"")
                    md.append(f"**Departmental Context Analysis:**")
                    md.append(f"  - Are ALL courses in this department showing similar patterns? (systemic dept issue)")
                    md.append(f"  - Is this course an outlier within its department? (course-specific issue)")
                    md.append(f"  - Check vertical patterns: Dark column across entire dept = dept-wide problem")
                    md.append(f"  - Look for department 'islands': Clusters of similar colors indicate shared characteristics")
                    md.append(f"")
                    md.append(f"**Z-Score Intensity Interpretation:**")
                    md.append(f"  - Dark Brown: z < -1.0 (bottom 15% of courses - crisis level)")
                    md.append(f"  - Light Brown: -1.0 < z < -0.5 (below average - concerning)")
                    md.append(f"  - Light Blue: 0.5 < z < 1.0 (above average - good)")
                    md.append(f"  - Dark Blue: z > 1.0 (top 15% of courses - excellence)")
                    md.append(f"  - ACTION: Count how many DARK cells vs light cells - more dark = more severe issues")
                    md.append(f"")
                    md.append(f"**2-Year Trajectory Deep-Dive:**")
                    md.append(f"  - Both columns 10 & 11 improving (both blue): Sustainable upward trajectory")
                    md.append(f"  - Both columns declining (both brown): Accelerating downward spiral")
                    md.append(f"  - Column 10 declining, 11 stable: Losing weaker students (attrition problem)")
                    md.append(f"  - Column 10 stable, 11 declining: Top students leaving/not being stretched")
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
        analysis, school_id, heatmaps_dir, atar_analysis, enriched_courses, conn, analysis_year
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
        **analysis,
        'markdown_report': str(md_path),  # Override v2's report path with v6
        'analysis_year': analysis_year,
        'version': 'v6'
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
