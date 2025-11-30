#!/usr/bin/env python3
"""
Test script for the analyze_school_results tool
"""

import json
import sqlite3
import sys
from pathlib import Path

# Simulate the tool's logic
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "capsules" / "output"
HEATMAPS_DIR = BASE_DIR / "capsules" / "heatmaps"

def test_analyze_school_results(school_id="abbotsleigh", target_year=None, min_cohort=10):
    """Test the analyze_school_results functionality"""

    db_file = OUTPUT_DIR / f"{school_id}.db"

    if not db_file.exists():
        return {"error": f"Database not found: {school_id}"}

    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get available years
        cursor.execute("""
            SELECT DISTINCT year
            FROM course_summary
            ORDER BY year DESC
        """)
        available_years = [row[0] for row in cursor.fetchall()]
        print(f"Available years: {available_years}")

        if not available_years:
            conn.close()
            return {"error": "No course summary data found"}

        # Use target year or most recent
        analysis_year = target_year if target_year and target_year in available_years else available_years[0]
        previous_year = analysis_year - 1 if (analysis_year - 1) in available_years else None
        print(f"Analysis year: {analysis_year}, Previous year: {previous_year}")

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
        print(f"\nSchool statistics: {school_stats}")

        # Get course-level performance
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
        print(f"\nFound {len(courses_data)} course records")

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

        print(f"Unique courses: {len(courses_by_code)}")

        # Analyze courses
        courses_for_attention = []
        subject_area_summary = {}

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

            # Check variability
            if current['std_dev'] and current['std_dev'] > 1.0:
                concerns.append(f"High variability (std dev: {current['std_dev']:.2f})")

            # Check cohort size
            if current['cohort_size'] and current['cohort_size'] < min_cohort:
                concerns.append(f"Small cohort size ({current['cohort_size']} students)")

            # Add to subject area summary
            subject_area = course_data['subject_area'] or 'Uncategorized'
            if subject_area not in subject_area_summary:
                subject_area_summary[subject_area] = {
                    'courses': [],
                    'avg_mean': 0,
                    'total_students': 0,
                    'declining_count': 0,
                    'improving_count': 0
                }

            subject_area_summary[subject_area]['courses'].append(code)
            subject_area_summary[subject_area]['avg_mean'] += current['mean']
            if current['cohort_size']:
                subject_area_summary[subject_area]['total_students'] += current['cohort_size']

            if trend == "declining":
                subject_area_summary[subject_area]['declining_count'] += 1
            elif trend == "improving":
                subject_area_summary[subject_area]['improving_count'] += 1

            # Add to attention list
            if concerns:
                courses_for_attention.append({
                    'code': code,
                    'name': course_data['name'],
                    'subject_area': subject_area,
                    'current_mean': round(current['mean'], 2),
                    'cohort_size': current['cohort_size'],
                    'trend': trend,
                    'trend_value': round(trend_value, 2) if trend_value is not None else None,
                    'concerns': concerns,
                    'priority': len(concerns)
                })

        # Calculate averages
        for area, data in subject_area_summary.items():
            course_count = len(data['courses'])
            if course_count > 0:
                data['avg_mean'] = round(data['avg_mean'] / course_count, 2)
                data['course_count'] = course_count

        # Sort by priority
        courses_for_attention.sort(key=lambda x: (-x['priority'], x.get('trend_value') or 0))

        conn.close()

        # Build result
        result = {
            'school_id': school_id,
            'analysis_year': analysis_year,
            'previous_year': previous_year,
            'school_statistics': {
                'overall_mean': round(school_stats['school_mean'], 2),
                'total_courses': school_stats['total_courses']
            },
            'subject_area_summary': subject_area_summary,
            'courses_requiring_attention': courses_for_attention[:10],
            'total_courses_flagged': len(courses_for_attention)
        }

        return result

    except Exception as e:
        import traceback
        return {
            "error": f"Analysis failed: {str(e)}",
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    result = test_analyze_school_results()
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)
    print(json.dumps(result, indent=2))

    print("\n" + "="*80)
    print("TOP COURSES FOR ATTENTION")
    print("="*80)
    for i, course in enumerate(result.get('courses_requiring_attention', [])[:5], 1):
        print(f"\n{i}. {course['code']} - {course['name']}")
        print(f"   Subject Area: {course['subject_area']}")
        print(f"   Mean: {course['current_mean']} | Cohort: {course['cohort_size']} | Trend: {course['trend']}")
        print(f"   Concerns:")
        for concern in course['concerns']:
            print(f"     - {concern}")
