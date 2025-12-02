"""
Exploratory Insights - Deep Cohort Analysis
NEW ADDITION to V3 - does not modify existing analysis

Focus: Cohort-level patterns, course selection optimization, multi-year trends
"""
import sqlite3
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

def analyze_course_selection_optimization(conn, year):
    """
    Did students select the right courses given their ATAR outcomes?
    Identify students whose course choices may have limited their ATAR
    """
    cursor = conn.cursor()

    # Get each student's courses and ATAR
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name || ':' || cr.scaled_score || ':' || cr.combined_mark) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        GROUP BY sym.student_id
    """, (year,))

    students = []
    for row in cursor.fetchall():
        student_id, atar, courses_str = row
        courses = []
        for course_info in courses_str.split(','):
            parts = course_info.split(':')
            if len(parts) == 3:
                courses.append({
                    'name': parts[0],
                    'scaled': float(parts[1]) if parts[1] else 0,
                    'hsc': float(parts[2]) if parts[2] else 0
                })

        students.append({
            'student_id': student_id,
            'atar': atar,
            'courses': courses
        })

    # Analyze patterns
    mismatches = []
    for student in students:
        # High ATAR but took mostly low-performing courses
        if student['atar'] > 90:
            low_scaled_courses = [c for c in student['courses'] if c['scaled'] < 35]
            if len(low_scaled_courses) >= 3:
                mismatches.append({
                    'student_id': student['student_id'],
                    'atar': student['atar'],
                    'issue': 'High ATAR student with many low-scaled courses',
                    'low_courses': [c['name'] for c in low_scaled_courses]
                })

        # Low ATAR with high-performing courses (unexpected)
        if student['atar'] < 70:
            high_scaled_courses = [c for c in student['courses'] if c['scaled'] > 40]
            if len(high_scaled_courses) >= 2:
                mismatches.append({
                    'student_id': student['student_id'],
                    'atar': student['atar'],
                    'issue': 'Low ATAR despite high-scaled courses',
                    'high_courses': [c['name'] for c in high_scaled_courses]
                })

    return {
        'total_students': len(students),
        'mismatches': mismatches[:10]  # Top 10
    }

def analyze_extension_decisions(conn, year):
    """
    Did students make good decisions about taking extension courses?
    """
    cursor = conn.cursor()

    # Find students who took extensions
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            c.name as course_name,
            cr.scaled_score,
            cr.combined_mark
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        AND (c.name LIKE '%Extension%' OR c.name LIKE '%Ext %')
    """, (year,))

    extension_students = defaultdict(list)
    for row in cursor.fetchall():
        student_id, atar, course_name, scaled, hsc = row
        extension_students[student_id].append({
            'atar': atar,
            'course': course_name,
            'scaled': scaled,
            'hsc': hsc
        })

    # Analyze extension performance
    successful_extensions = []
    struggling_extensions = []

    for student_id, extensions in extension_students.items():
        atar = extensions[0]['atar']

        # Check if extensions helped (high scaled scores)
        high_scaled = [e for e in extensions if e['scaled'] > 40]
        low_scaled = [e for e in extensions if e['scaled'] < 30]

        if len(high_scaled) >= 2:
            successful_extensions.append({
                'student_id': student_id,
                'atar': atar,
                'extensions': [e['course'] for e in high_scaled]
            })

        if len(low_scaled) >= 1 and atar < 90:
            struggling_extensions.append({
                'student_id': student_id,
                'atar': atar,
                'struggling_in': [e['course'] for e in low_scaled]
            })

    return {
        'total_extension_students': len(extension_students),
        'successful_extensions': successful_extensions[:5],
        'struggling_extensions': struggling_extensions[:5]
    }

def analyze_unit_selection_strategy(conn, year):
    """
    Did students benefit from taking >10 units?
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            sym.total_unit_scores,
            COUNT(DISTINCT cr.course_id) as num_courses,
            SUM(c2.units) as total_units
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        LEFT JOIN (
            SELECT course_id, 2 as units FROM course
        ) c2 ON cr.course_id = c2.course_id
        WHERE sym.year = ?
        GROUP BY sym.student_id
    """, (year,))

    students_by_units = defaultdict(list)
    for row in cursor.fetchall():
        student_id, atar, total_unit_scores, num_courses, total_units = row
        unit_count = total_units if total_units else num_courses * 2

        students_by_units[unit_count].append({
            'student_id': student_id,
            'atar': atar,
            'num_courses': num_courses
        })

    # Compare ATARs by unit count
    unit_performance = {}
    for units, students in students_by_units.items():
        if len(students) >= 3:
            atars = [s['atar'] for s in students]
            unit_performance[units] = {
                'count': len(students),
                'avg_atar': np.mean(atars),
                'median_atar': np.median(atars)
            }

    return {
        'unit_performance': dict(sorted(unit_performance.items())),
        'students_over_10': sum(1 for u in students_by_units.keys() if u > 10)
    }

def analyze_cohort_trends_multiyear(conn, years=[2022, 2023, 2024]):
    """
    Multi-year cohort trends
    """
    cursor = conn.cursor()

    cohort_stats = []
    for year in years:
        # Cohort ATAR stats
        cursor.execute("""
            SELECT
                AVG(psam_score) as avg_atar,
                MIN(psam_score) as min_atar,
                MAX(psam_score) as max_atar,
                COUNT(*) as cohort_size
            FROM student_year_metric
            WHERE year = ?
        """, (year,))

        atar_stats = cursor.fetchone()

        # Extension course uptake
        cursor.execute("""
            SELECT COUNT(DISTINCT sym.student_id) as extension_students
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            JOIN course c ON cr.course_id = c.course_id
            WHERE sym.year = ?
            AND (c.name LIKE '%Extension%' OR c.name LIKE '%Ext %')
        """, (year,))

        extension_count = cursor.fetchone()[0]

        cohort_stats.append({
            'year': year,
            'avg_atar': atar_stats[0],
            'min_atar': atar_stats[1],
            'max_atar': atar_stats[2],
            'cohort_size': atar_stats[3],
            'extension_students': extension_count,
            'extension_pct': (extension_count / atar_stats[3] * 100) if atar_stats[3] > 0 else 0
        })

    # Calculate trends
    trends = []
    if len(cohort_stats) >= 2:
        for i in range(1, len(cohort_stats)):
            prev = cohort_stats[i-1]
            curr = cohort_stats[i]

            atar_change = curr['avg_atar'] - prev['avg_atar']
            extension_change = curr['extension_pct'] - prev['extension_pct']

            trends.append({
                'from_year': prev['year'],
                'to_year': curr['year'],
                'atar_change': atar_change,
                'extension_pct_change': extension_change
            })

    return {
        'cohort_stats': cohort_stats,
        'trends': trends
    }

def analyze_optimal_course_combinations(conn, year):
    """
    Which course combinations produce the best ATARs?
    """
    cursor = conn.cursor()

    # Get course combinations and ATARs
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        GROUP BY sym.student_id
        HAVING COUNT(DISTINCT c.course_id) >= 5
    """, (year,))

    # Find common course pairs and their average ATAR
    course_pair_atars = defaultdict(list)
    for row in cursor.fetchall():
        student_id, atar, courses_str = row
        courses = sorted(courses_str.split(','))

        # Look at pairs of courses
        for i in range(len(courses)):
            for j in range(i+1, len(courses)):
                pair = f"{courses[i]} + {courses[j]}"
                course_pair_atars[pair].append(atar)

    # Find high-performing pairs
    high_performing_pairs = []
    for pair, atars in course_pair_atars.items():
        if len(atars) >= 3:  # At least 3 students
            avg_atar = np.mean(atars)
            if avg_atar > 85:
                high_performing_pairs.append({
                    'courses': pair,
                    'avg_atar': avg_atar,
                    'num_students': len(atars)
                })

    return {
        'high_performing_pairs': sorted(high_performing_pairs, key=lambda x: x['avg_atar'], reverse=True)[:10]
    }

def generate_exploratory_insights(conn, year):
    """
    Main function to generate all exploratory insights
    """
    print(f"Generating exploratory insights for {year}...")

    insights = {
        'year': year,
        'course_selection': analyze_course_selection_optimization(conn, year),
        'extensions': analyze_extension_decisions(conn, year),
        'unit_strategy': analyze_unit_selection_strategy(conn, year),
        'cohort_trends': analyze_cohort_trends_multiyear(conn),
        'optimal_combinations': analyze_optimal_course_combinations(conn, year)
    }

    return insights

if __name__ == "__main__":
    print("Testing exploratory insights...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")

    insights = generate_exploratory_insights(conn, 2024)

    print(f"\nCourse Selection Mismatches: {len(insights['course_selection']['mismatches'])}")
    print(f"Extension Students: {insights['extensions']['total_extension_students']}")
    print(f"Students >10 units: {insights['unit_strategy']['students_over_10']}")
    print(f"Cohort trends: {len(insights['cohort_trends']['trends'])} year-to-year changes")
    print(f"High-performing course pairs: {len(insights['optimal_combinations']['high_performing_pairs'])}")

    conn.close()
    print("\nExploratory insights test complete!")
