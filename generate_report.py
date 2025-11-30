#!/usr/bin/env python3
"""
Generate a comprehensive school analysis report
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "capsules" / "output"
HEATMAPS_DIR = BASE_DIR / "capsules" / "heatmaps"

def analyze_school(school_id="abbotsleigh", target_year=None, min_cohort=10):
    """Generate comprehensive analysis report"""

    db_file = OUTPUT_DIR / f"{school_id}.db"
    if not db_file.exists():
        return {"error": f"Database not found: {school_id}"}

    try:
        conn = sqlite3.connect(db_file)
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
                COUNT(DISTINCT course_id) as total_courses,
                SUM(units) as total_units
            FROM course_summary
            WHERE year = ?
        """, (analysis_year,))
        school_stats = dict(cursor.fetchone())

        # Get course data
        query = """
            SELECT
                c.course_id,
                COALESCE(c.code, c.name) as code,
                c.name,
                COALESCE(c.subject_area, 'Uncategorized') as subject_area,
                c.category,
                cs.year,
                cs.mean,
                cs.std_dev,
                cs.units,
                COUNT(DISTINCT cr.student_id) as cohort_size
            FROM course_summary cs
            JOIN course c ON cs.course_id = c.course_id
            LEFT JOIN course_result cr ON c.course_id = cr.course_id AND cr.year = cs.year
            WHERE cs.year IN (?, ?)
            GROUP BY c.course_id, cs.year
            ORDER BY c.subject_area, c.name, cs.year
        """

        params = [analysis_year, previous_year if previous_year else analysis_year]
        cursor.execute(query, params)
        courses_data = cursor.fetchall()

        # Process courses
        courses_by_code = {}
        for row in courses_data:
            row_dict = dict(row)
            code = row_dict['code']
            if code not in courses_by_code:
                courses_by_code[code] = {
                    'code': code,
                    'name': row_dict['name'],
                    'subject_area': row_dict['subject_area'],
                    'category': row_dict['category'],
                    'years': {}
                }

            year = row_dict['year']
            courses_by_code[code]['years'][year] = {
                'mean': row_dict['mean'],
                'std_dev': row_dict['std_dev'],
                'units': row_dict['units'],
                'cohort_size': row_dict['cohort_size']
            }

        # Analyze courses
        courses_for_attention = []
        subject_area_summary = {}
        all_courses = []

        for code, course_data in courses_by_code.items():
            current = course_data['years'].get(analysis_year)
            if not current:
                continue

            concerns = []
            insights = []

            # Calculate trend
            trend = None
            trend_value = None
            if previous_year and previous_year in course_data['years']:
                prev = course_data['years'][previous_year]
                if current['mean'] is not None and prev['mean'] is not None:
                    trend_value = current['mean'] - prev['mean']

                    if trend_value < -1.0:
                        trend = "declining"
                        concerns.append(f"Performance declined by {abs(trend_value):.2f} points")
                    elif trend_value > 1.0:
                        trend = "improving"
                        insights.append(f"Performance improved by {trend_value:.2f} points")
                    else:
                        trend = "stable"

            # Check performance relative to school average
            if school_stats['school_mean'] and current['mean'] is not None:
                deviation_from_mean = current['mean'] - school_stats['school_mean']
                if deviation_from_mean < -3.0:
                    concerns.append(f"Performing {abs(deviation_from_mean):.2f} points below school average")
                elif deviation_from_mean > 3.0:
                    insights.append(f"Performing {deviation_from_mean:.2f} points above school average")

            # Check variability
            if current['std_dev'] and current['std_dev'] > 1.0:
                concerns.append(f"High variability (std dev: {current['std_dev']:.2f})")

            # Check cohort size
            if current['cohort_size'] and current['cohort_size'] < min_cohort:
                concerns.append(f"Small cohort size ({current['cohort_size']} students)")

            # Subject area summary
            subject_area = course_data['subject_area'] or 'Uncategorized'
            if subject_area not in subject_area_summary:
                subject_area_summary[subject_area] = {
                    'courses': [],
                    'avg_mean': 0,
                    'total_students': 0,
                    'declining_count': 0,
                    'improving_count': 0,
                    'concern_count': 0
                }

            subject_area_summary[subject_area]['courses'].append(code)
            subject_area_summary[subject_area]['avg_mean'] += current['mean'] if current['mean'] else 0
            if current['cohort_size']:
                subject_area_summary[subject_area]['total_students'] += current['cohort_size']

            if trend == "declining":
                subject_area_summary[subject_area]['declining_count'] += 1
            elif trend == "improving":
                subject_area_summary[subject_area]['improving_count'] += 1

            if concerns:
                subject_area_summary[subject_area]['concern_count'] += 1

            # Store course info
            course_info = {
                'code': code,
                'name': course_data['name'],
                'subject_area': subject_area,
                'current_mean': round(current['mean'], 2) if current['mean'] else None,
                'current_std_dev': round(current['std_dev'], 2) if current['std_dev'] else None,
                'cohort_size': current['cohort_size'],
                'trend': trend,
                'trend_value': round(trend_value, 2) if trend_value is not None else None,
                'concerns': concerns,
                'insights': insights,
                'priority': len(concerns)
            }

            all_courses.append(course_info)

            if concerns:
                courses_for_attention.append(course_info)

        # Calculate subject area averages
        for area, data in subject_area_summary.items():
            course_count = len(data['courses'])
            if course_count > 0:
                data['avg_mean'] = round(data['avg_mean'] / course_count, 2)
                data['course_count'] = course_count

        # Sort courses
        courses_for_attention.sort(key=lambda x: (-x['priority'], x.get('trend_value') or 0))
        all_courses.sort(key=lambda x: x.get('current_mean') or 0)

        conn.close()

        return {
            'school_id': school_id,
            'analysis_year': analysis_year,
            'previous_year': previous_year,
            'school_statistics': school_stats,
            'subject_area_summary': subject_area_summary,
            'courses_requiring_attention': courses_for_attention,
            'all_courses': all_courses,
            'total_courses': len(all_courses),
            'total_courses_flagged': len(courses_for_attention)
        }

    except Exception as e:
        import traceback
        return {
            "error": f"Analysis failed: {str(e)}",
            "traceback": traceback.format_exc()
        }

def print_report(analysis):
    """Print a formatted report"""

    print("=" * 100)
    print(f"SCHOOL PERFORMANCE ANALYSIS REPORT - {analysis['school_id'].upper()}")
    print(f"Analysis Year: {analysis['analysis_year']}")
    if analysis['previous_year']:
        print(f"Comparison Year: {analysis['previous_year']}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    # Executive Summary
    print("\n" + "=" * 100)
    print("EXECUTIVE SUMMARY")
    print("=" * 100)

    stats = analysis['school_statistics']
    print(f"\nSchool-Wide Statistics:")
    print(f"  Overall Mean:        {stats['school_mean']:.2f}")
    print(f"  Overall Std Dev:     {stats['school_std_dev']:.2f}")
    print(f"  Total Courses:       {stats['total_courses']}")
    print(f"  Total Units:         {stats['total_units']}")

    print(f"\nCourse Analysis:")
    print(f"  Total Courses Analyzed:     {analysis['total_courses']}")
    print(f"  Courses Requiring Attention: {analysis['total_courses_flagged']}")
    print(f"  Percentage Flagged:          {(analysis['total_courses_flagged']/analysis['total_courses']*100):.1f}%")

    # Subject Area Summary
    print("\n" + "=" * 100)
    print("SUBJECT AREA OVERVIEW")
    print("=" * 100)

    for area, data in sorted(analysis['subject_area_summary'].items(),
                            key=lambda x: x[1]['concern_count'], reverse=True):
        print(f"\n{area}:")
        print(f"  Courses:           {data['course_count']}")
        print(f"  Average Mean:      {data['avg_mean']:.2f}")
        print(f"  Total Students:    {data['total_students']}")
        print(f"  Improving:         {data['improving_count']}")
        print(f"  Declining:         {data['declining_count']}")
        print(f"  With Concerns:     {data['concern_count']}")

        if data['declining_count'] > data['improving_count']:
            print(f"  [!] WARNING: More declining than improving courses")

    # High Priority Courses
    print("\n" + "=" * 100)
    print("HIGH PRIORITY COURSES (3+ CONCERNS)")
    print("=" * 100)

    high_priority = [c for c in analysis['courses_requiring_attention'] if c['priority'] >= 3]

    if high_priority:
        for i, course in enumerate(high_priority, 1):
            print(f"\n{i}. {course['name']}")
            print(f"   Code: {course['code']}")
            std_dev_str = f"{course['current_std_dev']:.2f}" if course['current_std_dev'] else 'N/A'
            print(f"   Mean: {course['current_mean']:.2f} | Std Dev: {std_dev_str}")
            print(f"   Cohort: {course['cohort_size']} students | Trend: {course['trend'] or 'N/A'}")
            if course['trend_value'] is not None:
                arrow = "DOWN" if course['trend_value'] < 0 else "UP"
                print(f"   Change: {arrow} {abs(course['trend_value']):.2f} points")
            print(f"   Concerns ({course['priority']}):")
            for concern in course['concerns']:
                print(f"     - {concern}")
            if course['insights']:
                print(f"   Insights:")
                for insight in course['insights']:
                    print(f"     + {insight}")
    else:
        print("\nNo high-priority courses identified.")

    # Medium Priority Courses
    print("\n" + "=" * 100)
    print("MEDIUM PRIORITY COURSES (2 CONCERNS)")
    print("=" * 100)

    medium_priority = [c for c in analysis['courses_requiring_attention'] if c['priority'] == 2]

    if medium_priority:
        for i, course in enumerate(medium_priority[:10], 1):  # Top 10
            print(f"\n{i}. {course['name']} - Mean: {course['current_mean']:.2f} | Cohort: {course['cohort_size']}")
            for concern in course['concerns']:
                print(f"     - {concern}")
    else:
        print("\nNo medium-priority courses identified.")

    # Top Performing Courses
    print("\n" + "=" * 100)
    print("TOP PERFORMING COURSES")
    print("=" * 100)

    top_performers = sorted([c for c in analysis['all_courses'] if c['current_mean'] and c['cohort_size'] and c['cohort_size'] >= 10],
                          key=lambda x: x['current_mean'], reverse=True)[:10]

    for i, course in enumerate(top_performers, 1):
        status = ""
        if course['trend'] == 'improving':
            status = "[UP] IMPROVING"
        elif course['trend'] == 'declining':
            status = "[DOWN] DECLINING"

        print(f"{i:2}. {course['name']:50} Mean: {course['current_mean']:5.2f} | Cohort: {course['cohort_size']:3} {status}")

    # Recommendations
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)

    print("\n1. IMMEDIATE ATTENTION REQUIRED:")
    for course in high_priority[:5]:
        print(f"   - {course['name']}: Review curriculum delivery and student support")

    print("\n2. MONITOR CLOSELY:")
    for course in medium_priority[:5]:
        print(f"   - {course['name']}: Track performance trends")

    print("\n3. SUBJECT AREA FOCUS:")
    concerning_areas = [area for area, data in analysis['subject_area_summary'].items()
                       if data['declining_count'] > data['improving_count']]
    if concerning_areas:
        for area in concerning_areas:
            data = analysis['subject_area_summary'][area]
            print(f"   - {area}: {data['declining_count']} declining vs {data['improving_count']} improving courses")
    else:
        print("   - No subject areas showing concerning patterns")

    print("\n" + "=" * 100)

if __name__ == "__main__":
    print("Generating analysis report for Abbotsleigh...")
    analysis = analyze_school("abbotsleigh")

    if "error" in analysis:
        print(f"ERROR: {analysis['error']}")
        if "traceback" in analysis:
            print(analysis['traceback'])
    else:
        print_report(analysis)

        # Save JSON report
        report_file = Path("abbotsleigh_analysis_report.json")
        with open(report_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"\nDetailed JSON report saved to: {report_file}")
