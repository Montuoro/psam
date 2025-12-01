#!/usr/bin/env python3
"""
Revised analyze_school_results implementation
Focus on departmental breakdown with three-tier categorization
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Subject area mappings (can be customized per school)
SUBJECT_MAPPINGS = {
    'Mathematics': ['Mathematics', 'Maths'],
    'English': ['English'],
    'Sciences': ['Biology', 'Chemistry', 'Physics', 'Science', 'Earth'],
    'Languages': ['Chinese', 'French', 'German', 'Japanese', 'Latin'],
    'HSIE': ['History', 'Geography', 'Economics', 'Business', 'Religion', 'Studies'],
    'Creative Arts': ['Visual Arts', 'Music', 'Drama', 'Design', 'Technology'],
    'PDHPE': ['PDHPE', 'Personal Development']
}

def categorize_course(course_name):
    """Intelligently categorize course into department"""
    for department, keywords in SUBJECT_MAPPINGS.items():
        for keyword in keywords:
            if keyword.lower() in course_name.lower():
                return department
    return 'Other'

def analyze_school_results_v2(school_id, db_path, heatmaps_dir, output_dir, target_year=None):
    """
    Comprehensive school results analysis with departmental focus

    Returns:
        - JSON analysis data
        - Markdown report path
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get available years
    cursor.execute("SELECT DISTINCT year FROM course_summary ORDER BY year DESC")
    available_years = [row[0] for row in cursor.fetchall()]

    if not available_years:
        return {"error": "No course summary data found"}

    analysis_year = target_year if target_year and target_year in available_years else available_years[0]
    previous_year = analysis_year - 1 if (analysis_year - 1) in available_years else None

    # Get school-wide statistics
    cursor.execute("""
        SELECT
            AVG(mean) as school_mean,
            AVG(std_dev) as school_std_dev,
            COUNT(DISTINCT course_id) as total_courses
        FROM course_summary
        WHERE year = ?
    """, (analysis_year,))
    school_stats = dict(cursor.fetchone())

    # Get course data for current and previous year
    query = """
        SELECT
            c.course_id,
            COALESCE(c.code, c.name) as code,
            c.name,
            cs.year,
            cs.mean,
            cs.std_dev,
            COUNT(DISTINCT cr.student_id) as cohort_size
        FROM course_summary cs
        JOIN course c ON cs.course_id = c.course_id
        LEFT JOIN course_result cr ON c.course_id = cr.course_id AND cr.year = cs.year
        WHERE cs.year IN (?, ?)
        GROUP BY c.course_id, cs.year
        ORDER BY c.name, cs.year
    """

    params = [analysis_year, previous_year if previous_year else analysis_year]
    cursor.execute(query, params)
    courses_data = cursor.fetchall()

    # Organize data by course
    courses_by_name = {}
    for row in courses_data:
        row_dict = dict(row)
        name = row_dict['name']
        if name not in courses_by_name:
            courses_by_name[name] = {
                'name': name,
                'department': categorize_course(name),
                'years': {}
            }

        year = row_dict['year']
        courses_by_name[name]['years'][year] = {
            'mean': row_dict['mean'],
            'std_dev': row_dict['std_dev'],
            'cohort_size': row_dict['cohort_size']
        }

    # Categorize courses into three tiers
    courses_of_concern = []
    middling_courses = []
    high_performers = []

    for name, course_data in courses_by_name.items():
        current = course_data['years'].get(analysis_year)
        if not current or current['mean'] is None:
            continue

        # Calculate trend
        trend_value = None
        trend_label = "stable"
        if previous_year and previous_year in course_data['years']:
            prev = course_data['years'][previous_year]
            if prev['mean'] is not None:
                trend_value = current['mean'] - prev['mean']
                if trend_value < -1.0:
                    trend_label = "declining"
                elif trend_value > 1.0:
                    trend_label = "improving"

        # Calculate deviation from school mean
        deviation = current['mean'] - school_stats['school_mean']

        # Build course info
        course_info = {
            'name': name,
            'department': course_data['department'],
            'mean': round(current['mean'], 2),
            'cohort_size': current['cohort_size'],
            'trend': trend_label,
            'trend_value': round(trend_value, 2) if trend_value is not None else None,
            'deviation': round(deviation, 2),
            'previous_mean': round(course_data['years'][previous_year]['mean'], 2) if previous_year in course_data['years'] and course_data['years'][previous_year]['mean'] is not None else None
        }

        # Categorize into three tiers
        # CONCERN: Declining OR significantly below average
        if trend_label == "declining" or deviation < -3.0:
            courses_of_concern.append(course_info)
        # HIGH PERFORMER: Improving OR significantly above average
        elif trend_label == "improving" or deviation > 3.0:
            high_performers.append(course_info)
        # MIDDLING: Everything else
        else:
            middling_courses.append(course_info)

    conn.close()

    # Sort each tier
    courses_of_concern.sort(key=lambda x: (x['trend'] == 'declining', -x['deviation']))
    high_performers.sort(key=lambda x: (-x['deviation'], x['trend'] == 'improving'))
    middling_courses.sort(key=lambda x: x['deviation'])

    # Group by department
    departments = defaultdict(lambda: {
        'courses_of_concern': [],
        'middling_courses': [],
        'high_performers': [],
        'avg_deviation': 0,
        'total_students': 0,
        'declining_count': 0,
        'improving_count': 0
    })

    for course in courses_of_concern:
        dept = course['department']
        departments[dept]['courses_of_concern'].append(course)
        departments[dept]['avg_deviation'] += course['deviation']
        departments[dept]['total_students'] += course['cohort_size'] or 0
        if course['trend'] == 'declining':
            departments[dept]['declining_count'] += 1

    for course in middling_courses:
        dept = course['department']
        departments[dept]['middling_courses'].append(course)
        departments[dept]['avg_deviation'] += course['deviation']
        departments[dept]['total_students'] += course['cohort_size'] or 0

    for course in high_performers:
        dept = course['department']
        departments[dept]['high_performers'].append(course)
        departments[dept]['avg_deviation'] += course['deviation']
        departments[dept]['total_students'] += course['cohort_size'] or 0
        if course['trend'] == 'improving':
            departments[dept]['improving_count'] += 1

    # Calculate department averages
    for dept, data in departments.items():
        total_courses = len(data['courses_of_concern']) + len(data['middling_courses']) + len(data['high_performers'])
        if total_courses > 0:
            data['avg_deviation'] = round(data['avg_deviation'] / total_courses, 2)
            data['total_courses'] = total_courses

    # Build analysis result
    analysis = {
        'school_id': school_id,
        'analysis_year': analysis_year,
        'previous_year': previous_year,
        'generated': datetime.now().isoformat(),
        'school_statistics': {
            'overall_mean': round(school_stats['school_mean'], 2),
            'total_courses': school_stats['total_courses']
        },
        'summary': {
            'courses_of_concern': len(courses_of_concern),
            'middling_courses': len(middling_courses),
            'high_performers': len(high_performers)
        },
        'departments': dict(departments),
        'courses_of_concern': courses_of_concern,
        'middling_courses': middling_courses,
        'high_performers': high_performers
    }

    # Generate Markdown report
    md_content = generate_markdown_report(analysis, school_id, heatmaps_dir)

    # Save Markdown file
    md_filename = f"{school_id}_{analysis_year}_analysis.md"
    output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
    md_path = output_path / md_filename
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    analysis['markdown_report'] = str(md_path)

    return analysis

def generate_markdown_report(analysis, school_id, heatmaps_dir):
    """Generate comprehensive Markdown report"""

    school_name = school_id.replace('-', ' ').title()
    year = analysis['analysis_year']
    prev_year = analysis['previous_year']
    stats = analysis['school_statistics']

    # Check for heatmaps
    heatmap_path = Path(heatmaps_dir) / school_id
    heatmaps_available = []
    if heatmap_path.exists():
        heatmaps_available = list(heatmap_path.glob("*.png"))

    md = []
    md.append(f"# {school_name} - Performance Analysis Report {year}")
    md.append(f"")
    md.append(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y')}")
    md.append(f"**Analysis Year:** {year}")
    if prev_year:
        md.append(f"**Comparison Year:** {prev_year}")
    md.append(f"**School Average:** {stats['overall_mean']}")
    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # Executive Summary
    md.append(f"## Executive Summary")
    md.append(f"")
    summary = analysis['summary']
    total = summary['courses_of_concern'] + summary['middling_courses'] + summary['high_performers']
    md.append(f"This report analyzes **{total} courses** at {school_name}, categorizing them into three performance tiers:")
    md.append(f"")
    md.append(f"- **{summary['courses_of_concern']} Courses of Concern** - Declining performance or significantly below average")
    md.append(f"- **{summary['middling_courses']} Middling Courses** - Stable performance around school average")
    md.append(f"- **{summary['high_performers']} High Performers** - Improving performance or significantly above average")
    md.append(f"")

    # Key findings
    concern_count = summary['courses_of_concern']
    high_count = summary['high_performers']

    md.append(f"### Key Findings")
    md.append(f"")
    if concern_count > high_count:
        md.append(f"- **CONCERN:** More courses declining ({concern_count}) than improving ({high_count})")
    elif high_count > concern_count:
        md.append(f"- **POSITIVE:** More courses improving ({high_count}) than declining ({concern_count})")
    else:
        md.append(f"- **BALANCED:** Equal numbers of declining and improving courses")

    # Department overview
    dept_concerns = [(d, data['courses_of_concern']) for d, data in analysis['departments'].items() if data['courses_of_concern']]
    dept_concerns.sort(key=lambda x: (len(x[1]), x[1][0]['deviation'] if x[1] else 0))

    if dept_concerns:
        worst_dept = dept_concerns[0][0]
        worst_count = len(dept_concerns[0][1])
        md.append(f"- **{worst_dept}** is the department of greatest concern with **{worst_count} courses** requiring attention")

    md.append(f"")
    md.append(f"---")
    md.append(f"")

    # Departmental Breakdown with integrated recommendations
    md.append(f"## Departmental Analysis & Recommendations")
    md.append(f"")

    for dept in sorted(analysis['departments'].keys()):
        data = analysis['departments'][dept]
        total_courses = data['total_courses']

        md.append(f"### {dept}")
        md.append(f"")
        md.append(f"**Total Courses:** {total_courses} | **Total Students:** {data['total_students']} | **Avg Deviation:** {data['avg_deviation']:+.2f}")
        md.append(f"")

        # Courses of Concern with detailed recommendations
        if data['courses_of_concern']:
            md.append(f"#### Courses of Concern ({len(data['courses_of_concern'])})")
            md.append(f"")

            for course in data['courses_of_concern']:
                trend_icon = "📉" if course['trend'] == 'declining' else "➡️"
                prev_str = f"{course['previous_mean']}" if course['previous_mean'] else "N/A"

                # Course header with stats
                md.append(f"##### {course['name']}")
                md.append(f"")
                md.append(f"**Current Performance:**")
                md.append(f"- Mean: **{course['mean']}** ({course['deviation']:+.2f} from school average)")
                md.append(f"- Cohort: {course['cohort_size']} students")
                md.append(f"- Trend: {trend_icon} {course['trend']}")
                if course['previous_mean']:
                    change = course['mean'] - course['previous_mean']
                    md.append(f"- Previous Year: {course['previous_mean']} (change: {change:+.2f})")
                md.append(f"")

                # Specific recommendations for this course
                md.append(f"**Recommendations:**")

                if course['trend'] == 'declining' and course['deviation'] < -3:
                    md.append(f"- 🚨 **CRITICAL:** Both declining trend AND performing {abs(course['deviation']):.1f} points below average")
                    md.append(f"- Immediate action required: Schedule department head meeting within 1 week")
                    md.append(f"- Review teaching methods and curriculum delivery")
                    md.append(f"- Analyze student feedback and assessment results")
                    md.append(f"- Consider peer observation from high-performing {dept} courses")
                elif course['trend'] == 'declining':
                    md.append(f"- 📉 **Declining trend:** Performance dropped {abs(course['trend_value']):.1f} points from {prev_year}")
                    md.append(f"- Investigate changes in: cohort composition, teaching staff, or curriculum")
                    md.append(f"- Implement targeted interventions for current cohort")
                    md.append(f"- Schedule review meeting with course coordinator")
                elif course['deviation'] < -7:
                    md.append(f"- ⚠️ **Significantly below average:** Performing {abs(course['deviation']):.1f} points below school mean")
                    md.append(f"- Conduct comprehensive program review")
                    md.append(f"- Compare with similar courses at other schools using NESA data")
                    md.append(f"- Review curriculum alignment and assessment practices")
                elif course['deviation'] < -3:
                    md.append(f"- ⚠️ **Below average:** Performing {abs(course['deviation']):.1f} points below school mean")
                    md.append(f"- Monitor closely for continued decline")
                    md.append(f"- Implement early intervention strategies")
                    md.append(f"- Review teaching resources and support materials")

                # Data analysis recommendations
                md.append(f"")
                md.append(f"**Data Analysis:**")
                if heatmaps_available:
                    md.append(f"- **Heatmap:** Review z-scores for {course['name']} across all metrics")
                    md.append(f"  - Check Assessment Mark vs. Exam Mark correlation")
                    md.append(f"  - Identify specific assessment components needing attention")
                else:
                    md.append(f"- **Heatmap:** Generate heatmap to visualize z-score patterns")

                md.append(f"- **PSAM System:**")
                md.append(f"  - Navigate: Overall Performance → Course Reports → {course['name']}")
                md.append(f"  - Review: Student-level performance data and trends")
                md.append(f"  - Check: Forecast Reports for Year 11 projections")
                md.append(f"  - Analyze: Sunburst Chart for visual department comparison")
                md.append(f"")

        # High Performers
        if data['high_performers']:
            md.append(f"#### High Performers ({len(data['high_performers'])})")
            md.append(f"")

            for i, course in enumerate(data['high_performers'][:5], 1):  # Top 5
                trend_icon = "📈" if course['trend'] == 'improving' else "➡️"
                prev_str = f"{course['previous_mean']}" if course['previous_mean'] else "N/A"

                md.append(f"**{i}. {course['name']}** - Mean: {course['mean']} ({course['deviation']:+.2f}) | Cohort: {course['cohort_size']} | {trend_icon} {course['trend']}")

                if course['trend'] == 'improving':
                    md.append(f"   - ✅ **Improving:** {course['trend_value']:+.1f} points from previous year")
                    md.append(f"   - **Action:** Document successful teaching strategies for department sharing")
                elif course['deviation'] > 7:
                    md.append(f"   - ⭐ **Excellent:** {abs(course['deviation']):.1f} points above school average")
                    md.append(f"   - **Action:** Use as model for other {dept} courses")
                else:
                    md.append(f"   - **Action:** Maintain current practices and share strategies")

                md.append(f"")

            if len(data['high_performers']) > 5:
                md.append(f"*Plus {len(data['high_performers']) - 5} additional high-performing courses*")
                md.append(f"")

        # Middling (summary only)
        if data['middling_courses']:
            md.append(f"#### Middling Courses ({len(data['middling_courses'])})")
            md.append(f"")
            md.append(f"Stable courses performing around school average. Continue quarterly monitoring.")
            md.append(f"")

        md.append(f"---")
        md.append(f"")

    md.append(f"")

    # Strategic Summary
    md.append(f"## Strategic Action Summary")
    md.append(f"")

    md.append(f"### Priority Overview")
    md.append(f"")

    if analysis['courses_of_concern']:
        # Count by severity
        critical = [c for c in analysis['courses_of_concern'] if c['trend'] == 'declining' and c['deviation'] < -3]
        declining = [c for c in analysis['courses_of_concern'] if c['trend'] == 'declining']
        below_avg = [c for c in analysis['courses_of_concern'] if c['deviation'] < -5]

        if critical:
            md.append(f"🚨 **{len(critical)} CRITICAL courses** - Declining AND significantly below average")
        if declining:
            md.append(f"📉 **{len(declining)} Declining courses** - Immediate intervention required")
        if below_avg:
            md.append(f"⚠️ **{len(below_avg)} Significantly underperforming** - Comprehensive review needed")

        md.append(f"")

    md.append(f"### Cross-Departmental Actions")
    md.append(f"")
    md.append(f"**Best Practice Sharing:**")
    if analysis['high_performers']:
        md.append(f"- Organize school-wide forum showcasing strategies from {len(analysis['high_performers'])} high-performing courses")
        md.append(f"- Create peer observation program pairing high and low performers")
        md.append(f"- Document and distribute assessment strategies from top courses")
    md.append(f"")

    md.append(f"**Data-Driven Monitoring:**")
    md.append(f"- **Heatmap Analysis:** Use `analyze_heatmap` tool to identify patterns")
    if heatmaps_available:
        md.append(f"  - Available heatmaps: {', '.join([h.name for h in heatmaps_available])}")
    md.append(f"- **Database Queries:** Pull student-level data using `query_database` tool")
    md.append(f"- **PSAM Navigation:** Sunburst Chart → Course Reports → Forecast Reports")
    md.append(f"")

    md.append(f"### Monitoring Schedule")
    md.append(f"")
    md.append(f"| Timeframe | Action |")
    md.append(f"|-----------|--------|")
    md.append(f"| **This week** | Share report with department heads |")
    md.append(f"| **Within 2 weeks** | Develop action plans for all concern courses |")
    md.append(f"| **Within 1 month** | Implement first interventions |")
    md.append(f"| **Quarterly** | Re-run analysis to track progress |")
    md.append(f"")

    md.append(f"---")
    md.append(f"")

    # Conclusions
    md.append(f"## Conclusions & Strategic Priorities")
    md.append(f"")

    # Calculate some metrics for conclusion
    concern_pct = (len(analysis['courses_of_concern']) / total) * 100
    high_pct = (len(analysis['high_performers']) / total) * 100

    md.append(f"### Overall Assessment")
    md.append(f"")

    if concern_pct > 30:
        md.append(f"**SIGNIFICANT CONCERN:** {concern_pct:.0f}% of courses require immediate attention. This suggests systemic issues that need addressing at the school level.")
        md.append(f"")
        md.append(f"**Priority Actions:**")
        md.append(f"1. Convene emergency department head meetings for affected areas")
        md.append(f"2. Conduct comprehensive curriculum review")
        md.append(f"3. Assess teaching staff allocation and professional development needs")
        md.append(f"4. Review school-wide assessment and teaching policies")
    elif concern_pct > 20:
        md.append(f"**MODERATE CONCERN:** {concern_pct:.0f}% of courses need attention. Focus on targeted departmental interventions.")
    else:
        md.append(f"**HEALTHY PROFILE:** Only {concern_pct:.0f}% of courses flagged as concerns. Most courses performing satisfactorily.")

    md.append(f"")

    # Department-specific conclusions
    md.append(f"### Departmental Priorities")
    md.append(f"")

    # Find departments with most concerns
    dept_priority = [(d, len(data['courses_of_concern'])) for d, data in analysis['departments'].items()]
    dept_priority.sort(key=lambda x: x[1], reverse=True)

    for dept, concern_count in dept_priority[:3]:
        if concern_count > 0:
            dept_data = analysis['departments'][dept]
            md.append(f"**{dept}:** {concern_count} courses of concern")
            md.append(f"- Average deviation: {dept_data['avg_deviation']:+.2f} points from school mean")
            md.append(f"- Requires comprehensive department review and intervention strategy")
            md.append(f"")

    md.append(f"### Next Steps")
    md.append(f"")
    md.append(f"1. **Within 1 week:** Share this report with relevant department heads")
    md.append(f"2. **Within 2 weeks:** Develop action plans for all courses of concern")
    md.append(f"3. **Within 1 month:** Implement first-round interventions")
    md.append(f"4. **Quarterly:** Re-run this analysis to track progress")
    md.append(f"")
    md.append(f"### Long-Term Strategy")
    md.append(f"")
    md.append(f"Based on this analysis, {school_name} should focus on:")
    md.append(f"")

    if analysis['departments']['Languages']['courses_of_concern']:
        md.append(f"- **Languages program sustainability** - Multiple small cohorts indicate low uptake")
    if len([c for c in analysis['courses_of_concern'] if c['cohort_size'] and c['cohort_size'] < 10]) > 5:
        md.append(f"- **Small cohort management** - Review viability of courses with consistently low enrollment")
    if concern_pct > 25:
        md.append(f"- **Teaching quality assurance** - High proportion of declining courses suggests need for professional development")

    md.append(f"- **Data-driven decision making** - Continue quarterly analysis using this tool")
    md.append(f"- **Best practice sharing** - Create formal mechanisms to share strategies from high performers")
    md.append(f"- **Early intervention systems** - Develop triggers for when courses move into 'concern' category")
    md.append(f"")

    md.append(f"---")
    md.append(f"")
    md.append(f"*Report generated by analyze_school_results MCP tool*")
    md.append(f"*For detailed methodology, see ANALYSIS_TOOL_GUIDE.md*")

    return "\n".join(md)

if __name__ == "__main__":
    # Test with Abbotsleigh
    BASE_DIR = Path(__file__).parent
    db_path = BASE_DIR / "capsules" / "output" / "abbotsleigh.db"
    heatmaps_dir = BASE_DIR / "capsules" / "heatmaps"
    output_dir = BASE_DIR

    result = analyze_school_results_v2(
        school_id="abbotsleigh",
        db_path=db_path,
        heatmaps_dir=heatmaps_dir,
        output_dir=output_dir
    )

    print(f"Analysis complete!")
    print(f"Markdown report: {result['markdown_report']}")
    print(f"\nSummary:")
    print(f"  Courses of concern: {result['summary']['courses_of_concern']}")
    print(f"  Middling courses: {result['summary']['middling_courses']}")
    print(f"  High performers: {result['summary']['high_performers']}")
