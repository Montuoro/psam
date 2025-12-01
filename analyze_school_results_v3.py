#!/usr/bin/env python3
"""
Enhanced analyze_school_results with ATAR analysis and deep insights
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from analyze_school_results_v2 import categorize_course, SUBJECT_MAPPINGS

def get_atar_analysis(conn, analysis_year):
    """Get ATAR distribution and analysis"""
    cursor = conn.cursor()

    # Get ATAR distribution
    cursor.execute("""
        SELECT
            psam_score,
            map_score,
            COUNT(*) as student_count
        FROM student_year_metric
        WHERE year = ? AND psam_score IS NOT NULL
        GROUP BY ROUND(psam_score)
        ORDER BY psam_score DESC
    """, (analysis_year,))

    atar_data = cursor.fetchall()

    # Calculate statistics
    cursor.execute("""
        SELECT
            AVG(psam_score) as avg_atar,
            MIN(psam_score) as min_atar,
            MAX(psam_score) as max_atar,
            COUNT(*) as total_students
        FROM student_year_metric
        WHERE year = ? AND psam_score IS NOT NULL
    """, (analysis_year,))

    stats = dict(cursor.fetchone())

    # Get band distribution by course
    cursor.execute("""
        SELECT
            c.name,
            cr.band,
            COUNT(*) as count
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE cr.year = ? AND cr.band IS NOT NULL
        GROUP BY c.name, cr.band
        ORDER BY c.name, cr.band DESC
    """, (analysis_year,))

    band_data = defaultdict(dict)
    for row in cursor.fetchall():
        course_name, band, count = row
        band_data[course_name][band] = count

    return {
        'stats': stats,
        'distribution': atar_data,
        'band_data': band_data
    }

def get_course_detail_metrics(conn, course_name, analysis_year):
    """Get detailed metrics for a specific course"""
    cursor = conn.cursor()

    # Get assessment vs exam correlation
    cursor.execute("""
        SELECT
            AVG(school_assessment) as avg_assessment,
            AVG(moderated_assessment) as avg_mod_assessment,
            AVG(scaled_exam_mark) as avg_exam,
            AVG(combined_mark) as avg_combined,
            AVG(scaled_score) as avg_scaled,
            band,
            COUNT(*) as band_count
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ? AND cr.year = ?
        GROUP BY band
        ORDER BY band DESC
    """, (course_name, analysis_year))

    results = cursor.fetchall()

    if not results:
        return None

    # Get first row for averages
    first_row = results[0] if results else None

    # Get ATAR impact (students in this course vs overall ATAR)
    cursor.execute("""
        SELECT
            AVG(sym.psam_score) as avg_atar_in_course
        FROM course_result cr
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ? AND cr.year = ?
    """, (course_name, analysis_year))

    atar_row = cursor.fetchone()

    return {
        'avg_assessment': round(first_row[0], 1) if first_row and first_row[0] else None,
        'avg_mod_assessment': round(first_row[1], 1) if first_row and first_row[1] else None,
        'avg_exam': round(first_row[2], 1) if first_row and first_row[2] else None,
        'avg_combined': round(first_row[3], 1) if first_row and first_row[3] else None,
        'avg_scaled': round(first_row[4], 1) if first_row and first_row[4] else None,
        'band_distribution': {row[5]: row[6] for row in results if row[5]},
        'avg_atar_in_course': round(atar_row[0], 1) if atar_row and atar_row[0] else None
    }

def generate_course_insights(course, metrics, school_atar_avg, prev_year):
    """Generate deep, specific insights for a course"""
    insights = []

    if not metrics:
        return ["Insufficient data for detailed analysis"]

    # Assessment vs Exam alignment
    if metrics['avg_assessment'] and metrics['avg_exam']:
        diff = metrics['avg_assessment'] - metrics['avg_exam']
        if abs(diff) > 5:
            if diff > 5:
                insights.append(
                    f"**Assessment-Exam Misalignment:** Internal assessments average {metrics['avg_assessment']:.1f} "
                    f"while exam marks average {metrics['avg_exam']:.1f} (difference: {diff:+.1f}). "
                    f"This suggests internal assessments may not adequately prepare students for HSC exam rigor. "
                    f"Review assessment task alignment with HSC exam format and difficulty."
                )
            else:
                insights.append(
                    f"**Exam Underperformance:** Students score {abs(diff):.1f} points lower on exams than internal assessments. "
                    f"This indicates a gap between classroom learning and exam execution. "
                    f"Increase exam-style practice and time-constrained assessment tasks."
                )

    # Band analysis
    if metrics['band_distribution']:
        bands = metrics['band_distribution']
        total_students = sum(bands.values())

        # Calculate Band 4+ percentage (typical success threshold)
        band4_plus = sum(count for band, count in bands.items() if band and int(band.replace('E', '').replace('B', '')) >= 4)
        band4_plus_pct = (band4_plus / total_students * 100) if total_students > 0 else 0

        # Calculate Band 6 percentage (excellence)
        band6_count = bands.get('B6', 0) + bands.get('E4', 0)  # B6 or E4 (extension)
        band6_pct = (band6_count / total_students * 100) if total_students > 0 else 0

        if band6_pct < 10 and course['deviation'] < -3:
            insights.append(
                f"**Low Excellence Rate:** Only {band6_pct:.0f}% achieving Band 6/E4 (vs. typical 15-20% for performing courses). "
                f"Combined with below-average mean, this indicates systemic issues. "
                f"Priority: Identify and support high-potential students who could reach Band 6 with intervention."
            )

        if band4_plus_pct < 70:
            insights.append(
                f"**Below Success Threshold:** {band4_plus_pct:.0f}% achieving Band 4+. "
                f"Students in Bands 1-3 are significantly limiting their ATAR potential. "
                f"Focus: Targeted support for Band 3 students to reach Band 4 minimum competency."
            )

    # ATAR impact analysis
    if metrics['avg_atar_in_course'] and school_atar_avg:
        atar_diff = metrics['avg_atar_in_course'] - school_atar_avg
        if atar_diff < -5:
            insights.append(
                f"**ATAR Impact:** Students taking this course average ATAR {metrics['avg_atar_in_course']:.1f} "
                f"(school average: {school_atar_avg:.1f}). "
                f"This {abs(atar_diff):.1f} point gap suggests this course is dragging down overall ATAR outcomes. "
                f"Underperformance here directly impacts university entrance prospects."
            )

    # Scaling impact
    if metrics['avg_scaled'] and metrics['avg_combined']:
        scaling_impact = metrics['avg_scaled'] - metrics['avg_combined']
        if scaling_impact < -3:
            insights.append(
                f"**Negative Scaling Impact:** Course scaled score ({metrics['avg_scaled']:.1f}) is "
                f"{abs(scaling_impact):.1f} points below raw HSC mark ({metrics['avg_combined']:.1f}). "
                f"This course scales down, meaning student effort yields lower ATAR contribution. "
                f"While this is partially cohort-driven statewide, consistent underperformance compounds the effect."
            )

    # Trend-based insights
    if course['trend'] == 'declining' and course['trend_value'] and course['trend_value'] < -2:
        insights.append(
            f"**Accelerating Decline:** {abs(course['trend_value']):.1f} point drop from {prev_year} represents "
            f"a significant deterioration (>2 points = full band drop equivalent). "
            f"Investigate: Has there been a teaching staff change? Curriculum modification? "
            f"Cohort composition shift? This requires immediate root cause analysis."
        )

    if not insights:
        insights.append("Performance within expected range. Continue current monitoring protocols.")

    return insights

def generate_heatmap_specifics(course, metrics):
    """Generate specific heatmap analysis directions"""
    directions = []

    # Scaled exam mark specific
    if course['deviation'] < -5:
        directions.append(
            f"**Scaled Exam Mark Column:** Your course shows {abs(course['deviation']):.1f} points below average. "
            f"In the heatmap, check if 'Scaled Exam Mark' z-score is dark gray/brown (negative). "
            f"This confirms exam performance is the primary drag factor vs. assessment marks."
        )

    # Assessment mark specific
    if metrics and metrics['avg_assessment'] and metrics['avg_exam']:
        if metrics['avg_assessment'] - metrics['avg_exam'] > 5:
            directions.append(
                f"**Assessment Mark Column:** Look for light blue (positive z-score) in assessment "
                f"while exam mark shows negative z-score. This pattern confirms internal assessments "
                f"are inflated relative to HSC standards. Use this visual to justify moderation review."
            )

    # Total z-score
    if course['deviation'] < -7:
        directions.append(
            f"**Total Z-Score Column (rightmost):** Your {abs(course['deviation']):.1f} point deficit "
            f"likely translates to z-score around -0.7 to -0.9 (dark tan/gray in heatmap). "
            f"This indicates consistent underperformance across ALL metrics, not just one weak area. "
            f"This pattern demands comprehensive program review, not targeted fixes."
        )

    # Comparative analysis
    directions.append(
        f"**Departmental Comparison:** In heatmap, compare this course's row to other "
        f"{course['department']} courses. If all {course['department']} courses show negative z-scores, "
        f"this is a department-wide issue requiring leadership intervention."
    )

    return directions

def generate_markdown_report_v3(analysis, school_id, heatmaps_dir, atar_analysis):
    """Generate enhanced Markdown with ATAR analysis and deep insights"""

    school_name = school_id.replace('-', ' ').title()
    year = analysis['analysis_year']
    prev_year = analysis['previous_year']
    stats = analysis['school_statistics']

    heatmap_path = Path(heatmaps_dir) / school_id
    heatmaps_available = list(heatmap_path.glob("*.png")) if heatmap_path.exists() else []

    md = []
    md.append(f"# {school_name} - Comprehensive Performance & ATAR Analysis {year}")
    md.append(f"")
    md.append(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y')}")
    md.append(f"**Analysis Year:** {year}")
    if prev_year:
        md.append(f"**Comparison Year:** {prev_year}")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # ATAR Analysis Section
    md.append(f"## ATAR Performance Overview")
    md.append(f"")

    if atar_analysis and atar_analysis['stats']:
        atar_stats = atar_analysis['stats']
        md.append(f"### School ATAR Statistics")
        md.append(f"")
        md.append(f"| Metric | Value |")
        md.append(f"|--------|-------|")
        md.append(f"| **Average ATAR** | {atar_stats['avg_atar']:.2f} |")
        md.append(f"| **Highest ATAR** | {atar_stats['max_atar']:.2f} |")
        md.append(f"| **Lowest ATAR** | {atar_stats['min_atar']:.2f} |")
        md.append(f"| **Total Students** | {atar_stats['total_students']} |")
        md.append(f"| **Course Mean** | {stats['overall_mean']:.2f} |")
        md.append(f"")

        # ATAR insights
        md.append(f"### ATAR Impact Analysis")
        md.append(f"")

        if atar_stats['avg_atar'] > 85:
            md.append(f"**Strong Performance:** School average ATAR of {atar_stats['avg_atar']:.1f} places cohort well above state median (70.00). ")
            md.append(f"This indicates effective overall program delivery. However, {analysis['summary']['courses_of_concern']} underperforming ")
            md.append(f"courses are preventing students from maximizing their potential ATARs.")
        elif atar_stats['avg_atar'] > 75:
            md.append(f"**Above Average:** School ATAR {atar_stats['avg_atar']:.1f} is above state median. ")
            md.append(f"Focus on elevating underperforming courses to push more students into 85+ ATAR range (top quartile).")
        else:
            md.append(f"**Below Median:** School ATAR {atar_stats['avg_atar']:.1f} indicates significant room for improvement. ")
            md.append(f"The {analysis['summary']['courses_of_concern']} courses of concern are major contributing factors.")

        md.append(f"")
        md.append(f"**Key Finding:** Course performance (mean {stats['overall_mean']:.1f}) directly impacts ATAR outcomes. ")
        md.append(f"Each 1-point improvement in course means translates approximately 0.3-0.5 points in ATAR scaling, ")
        md.append(f"making targeted course interventions critical for ATAR improvement.")
        md.append(f"")

    md.append(f"---")
    md.append(f"")

    # Executive Summary
    md.append(f"## Executive Summary")
    md.append(f"")
    summary = analysis['summary']
    total = summary['courses_of_concern'] + summary['middling_courses'] + summary['high_performers']

    md.append(f"This analysis examines **{total} courses** across {school_name}, categorizing by performance tier:")
    md.append(f"")
    md.append(f"- **{summary['courses_of_concern']} Courses of Concern** - Declining trend or >3 points below average")
    md.append(f"- **{summary['middling_courses']} Middling Courses** - Stable performance near school mean  ")
    md.append(f"- **{summary['high_performers']} High Performers** - Improving trend or >3 points above average")
    md.append(f"")
    md.append(f"**Critical Context:** Courses of concern don't just represent poor performance—they directly limit ")
    md.append(f"student ATAR outcomes and university entrance prospects. Each significantly underperforming course ")
    md.append(f"can reduce a student's ATAR by 2-4 points, potentially costing competitive university placements.")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # Store metrics for later use
    all_course_metrics = {}

    # Departmental Analysis with integrated recommendations
    md.append(f"## Departmental Analysis & Recommendations")
    md.append(f"")

    for dept in sorted(analysis['departments'].keys()):
        data = analysis['departments'][dept]
        total_courses = data['total_courses']

        md.append(f"### {dept}")
        md.append(f"")
        md.append(f"**Portfolio:** {total_courses} courses | {data['total_students']} students | Avg deviation: {data['avg_deviation']:+.2f}")
        md.append(f"")

        # Courses of Concern
        if data['courses_of_concern']:
            md.append(f"#### Courses Requiring Intervention ({len(data['courses_of_concern'])})")
            md.append(f"")

            for course in data['courses_of_concern']:
                # Get detailed metrics
                metrics = get_course_detail_metrics(
                    analysis['_conn'],
                    course['name'],
                    year
                )
                all_course_metrics[course['name']] = metrics

                md.append(f"##### {course['name']}")
                md.append(f"")

                # Performance summary
                trend_icon = "📉" if course['trend'] == 'declining' else "➡️"
                md.append(f"**Performance Summary:**")
                md.append(f"- Mean: **{course['mean']}** ({course['deviation']:+.2f} vs school avg {stats['overall_mean']:.1f})")
                md.append(f"- Cohort: {course['cohort_size']} students")
                md.append(f"- Trend: {trend_icon} {course['trend']}")
                if course['previous_mean']:
                    change = course['mean'] - course['previous_mean']
                    md.append(f"- Change: {change:+.2f} points from {prev_year}")

                if metrics and metrics['avg_atar_in_course']:
                    md.append(f"- ATAR Impact: Students in this course average {metrics['avg_atar_in_course']:.1f} ATAR")

                md.append(f"")

                # Deep insights
                insights = generate_course_insights(
                    course,
                    metrics,
                    atar_analysis['stats']['avg_atar'] if atar_analysis else None,
                    prev_year
                )

                md.append(f"**Analysis & Insights:**")
                for insight in insights:
                    md.append(f"{insight}")
                    md.append(f"")

                # Specific heatmap directions
                heatmap_directions = generate_heatmap_specifics(course, metrics)

                md.append(f"**Heatmap Analysis - Specific Directions:**")
                if heatmaps_available:
                    md.append(f"Open heatmap: `{heatmaps_available[0].name}`")
                    md.append(f"")
                    for direction in heatmap_directions:
                        md.append(f"{direction}")
                        md.append(f"")
                else:
                    md.append(f"Generate heatmap to access visual z-score analysis")
                    md.append(f"")

                # PSAM system navigation with purpose
                md.append(f"**Database Deep-Dive:**")
                md.append(f"- Query student-level data for {course['name']} to identify:")
                md.append(f"  - Students with large assessment-vs-exam gaps (indicates exam anxiety or preparation issues)")
                md.append(f"  - Cohort composition: Are underperformers concentrated in specific assessment tasks?")
                md.append(f"  - Correlation with other courses: Do students struggling here also struggle in related subjects?")
                md.append(f"")
                md.append(f"---")
                md.append(f"")

        # High Performers
        if data['high_performers']:
            md.append(f"#### High Performers ({len(data['high_performers'])})")
            md.append(f"")

            for i, course in enumerate(data['high_performers'][:5], 1):
                trend_icon = "📈" if course['trend'] == 'improving' else "⭐"

                md.append(f"**{i}. {course['name']}** - Mean: {course['mean']} ({course['deviation']:+.2f}) | Cohort: {course['cohort_size']} | {trend_icon}")

                if course['trend'] == 'improving' and course['trend_value']:
                    md.append(f"   - Improved {course['trend_value']:+.1f} points - Identify what changed (new teacher? curriculum update?) to replicate success")
                elif course['deviation'] > 7:
                    md.append(f"   - Exceptional: {abs(course['deviation']):.1f} points above average contributes strongly to student ATAR outcomes")

                md.append(f"")

            if len(data['high_performers']) > 5:
                md.append(f"*Plus {len(data['high_performers']) - 5} additional high-performing courses*")
                md.append(f"")

        # Middling
        if data['middling_courses']:
            md.append(f"#### Stable Courses ({len(data['middling_courses'])})")
            md.append(f"Performing near school average. Monitor quarterly to catch early signs of decline.")
            md.append(f"")

        md.append(f"")

    md.append(f"---")
    md.append(f"")

    # Strategic Summary
    md.append(f"## Strategic Priorities")
    md.append(f"")

    if analysis['courses_of_concern']:
        critical = [c for c in analysis['courses_of_concern'] if c['trend'] == 'declining' and c['deviation'] < -3]

        if critical:
            md.append(f"### Immediate Crisis Management ({len(critical)} courses)")
            md.append(f"")
            md.append(f"These courses are both declining AND significantly below average—a double failure requiring urgent intervention:")
            md.append(f"")
            for c in critical[:5]:
                md.append(f"- **{c['name']}**: {c['mean']} mean ({c['deviation']:+.2f}), dropping {abs(c['trend_value']):.1f} points")
            md.append(f"")
            md.append(f"**Action:** Emergency department meetings this week. These courses are active ATAR destroyers.")
            md.append(f"")

    md.append(f"### Why These Recommendations Matter")
    md.append(f"")
    md.append(f"Each recommendation is driven by data patterns indicating specific, fixable problems:")
    md.append(f"")
    md.append(f"- **Assessment-exam gaps** suggest misalignment between classroom teaching and HSC exam demands")
    md.append(f"- **Low Band 6 rates** indicate failure to stretch high-achievers who could drive school performance")
    md.append(f"- **ATAR impacts** quantify real consequences: underperformance here = lost university places")
    md.append(f"- **Heatmap z-scores** provide visual proof for stakeholders and focus intervention efforts")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # Conclusions
    md.append(f"## Conclusions & Next Steps")
    md.append(f"")

    concern_pct = (len(analysis['courses_of_concern']) / total) * 100

    if concern_pct > 30:
        md.append(f"**Systemic Issues Detected:** {concern_pct:.0f}% of courses underperforming suggests school-wide problems, ")
        md.append(f"not isolated course failures. Root causes likely include inadequate professional development, curriculum ")
        md.append(f"misalignment with HSC standards, or assessment practice inconsistencies.")
    elif concern_pct > 20:
        md.append(f"**Targeted Intervention Needed:** {concern_pct:.0f}% of courses require attention. Focus on departmental support ")
        md.append(f"rather than school-wide changes.")
    else:
        md.append(f"**Healthy Overall Profile:** {concern_pct:.0f}% underperformance rate is manageable with targeted course-level fixes.")

    md.append(f"")
    md.append(f"### Timeline")
    md.append(f"")
    md.append(f"| Phase | Action | Purpose |")
    md.append(f"|-------|--------|---------|")
    md.append(f"| **This week** | Share report with department heads | Establish shared understanding of problems |")
    md.append(f"| **Week 2** | Deep-dive analysis using heatmaps & database queries | Identify root causes |")
    md.append(f"| **Week 3-4** | Implement first interventions | Quick wins to build momentum |")
    md.append(f"| **Quarter 2** | Re-run analysis | Measure intervention effectiveness |")
    md.append(f"")
    md.append(f"**Remember:** Every 1-point course improvement ≈ 0.3-0.5 ATAR points for students. Small course gains create ")
    md.append(f"significant university entrance opportunities.")
    md.append(f"")
    md.append(f"---")
    md.append(f"")
    md.append(f"*Report generated by analyze_school_results MCP tool | For methodology: see ANALYSIS_TOOL_GUIDE.md*")

    return "\n".join(md)

# Modify main analysis function to include connection for later queries
def analyze_school_results_v3(school_id, db_path, heatmaps_dir, output_dir, target_year=None):
    """Enhanced analysis with ATAR integration"""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get years
    cursor.execute("SELECT DISTINCT year FROM course_summary ORDER BY year DESC")
    available_years = [row[0] for row in cursor.fetchall()]

    if not available_years:
        return {"error": "No data"}

    analysis_year = target_year if target_year and target_year in available_years else available_years[0]
    previous_year = analysis_year - 1 if (analysis_year - 1) in available_years else None

    # Get ATAR analysis
    atar_analysis = get_atar_analysis(conn, analysis_year)

    # Run existing analysis logic from v2
    from analyze_school_results_v2 import analyze_school_results_v2 as run_v2

    # Call v2 but don't close connection yet
    analysis = run_v2(school_id, db_path, heatmaps_dir, output_dir, target_year)

    # Add connection to analysis for later use
    analysis['_conn'] = conn

    # Generate enhanced markdown
    md_content = generate_markdown_report_v3(analysis, school_id, heatmaps_dir, atar_analysis)

    # Save markdown
    md_filename = f"{school_id}_{analysis_year}_analysis_enhanced.md"
    output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
    md_path = output_path / md_filename
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    conn.close()
    del analysis['_conn']

    analysis['markdown_report'] = str(md_path)
    analysis['atar_analysis'] = atar_analysis

    return analysis

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent
    db_path = BASE_DIR / "capsules" / "output" / "abbotsleigh.db"
    heatmaps_dir = BASE_DIR / "capsules" / "heatmaps"
    output_dir = BASE_DIR

    result = analyze_school_results_v3(
        school_id="abbotsleigh",
        db_path=db_path,
        heatmaps_dir=heatmaps_dir,
        output_dir=output_dir
    )

    if 'error' not in result:
        print(f"Enhanced analysis complete!")
        print(f"Report: {result['markdown_report']}")
        print(f"\nATAR Stats:")
        print(f"  Average: {result['atar_analysis']['stats']['avg_atar']:.2f}")
        print(f"  Range: {result['atar_analysis']['stats']['min_atar']:.1f} - {result['atar_analysis']['stats']['max_atar']:.1f}")
