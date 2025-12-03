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

    # Get each student's courses and ATAR (exclude NG ATAR students)
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name || ':' || cr.scaled_score || ':' || cr.combined_mark) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        AND sym.psam_score > 0
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
        'mismatches': mismatches  # ALL mismatches (no limit)
    }

def analyze_extension_decisions(conn, year):
    """
    Did students make good decisions about taking extension courses?
    """
    cursor = conn.cursor()

    # Find students who took extensions (exclude NG ATAR students)
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
        AND sym.psam_score > 0
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
        'successful_extensions': successful_extensions,  # ALL successful students
        'struggling_extensions': struggling_extensions  # ALL struggling students
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
        AND sym.psam_score > 0
        GROUP BY sym.student_id
    """, (year,))

    students_by_units = defaultdict(list)
    for row in cursor.fetchall():
        student_id, atar, total_unit_scores, num_courses, total_units = row
        unit_count = total_units if total_units else num_courses * 2

        # ONLY include students with >= 10 units
        if unit_count >= 10:
            students_by_units[unit_count].append({
                'student_id': student_id,
                'atar': atar,
                'num_courses': num_courses
            })

    # Compare ATARs by unit count (only for >= 10 units)
    unit_performance = {}
    for units, students in students_by_units.items():
        if len(students) >= 3:
            atars = [s['atar'] for s in students]
            unit_performance[units] = {
                'count': len(students),
                'avg_atar': np.mean(atars),
                'median_atar': np.median(atars)
            }

    # Count STUDENTS taking 10 or more units
    students_over_10 = sum(len(students) for units, students in students_by_units.items())

    return {
        'unit_performance': dict(sorted(unit_performance.items())),
        'students_over_10': students_over_10
    }

def analyze_cohort_trends_multiyear(conn, years=[2022, 2023, 2024]):
    """
    Multi-year cohort trends with HSC and scaled marks
    """
    cursor = conn.cursor()

    cohort_stats = []
    for year in years:
        # Cohort ATAR stats (exclude NG students, cap max at 99.95)
        cursor.execute("""
            SELECT
                AVG(psam_score) as avg_atar,
                MIN(psam_score) as min_atar,
                MAX(psam_score) as max_atar,
                COUNT(*) as cohort_size
            FROM student_year_metric
            WHERE year = ?
            AND psam_score > 0
        """, (year,))

        atar_stats = cursor.fetchone()
        # Cap max ATAR at 99.95
        atar_stats = (atar_stats[0], atar_stats[1], min(atar_stats[2], 99.95), atar_stats[3])

        # Mean HSC mark and scaled mark across all courses
        cursor.execute("""
            SELECT
                AVG(cr.combined_mark) as avg_hsc,
                AVG(cr.scaled_score * 2) as avg_scaled
            FROM course_result cr
            WHERE cr.year = ?
            AND cr.combined_mark IS NOT NULL
            AND cr.scaled_score IS NOT NULL
        """, (year,))

        marks_stats = cursor.fetchone()

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
            'avg_hsc': marks_stats[0] if marks_stats[0] else 0,
            'avg_scaled': marks_stats[1] if marks_stats[1] else 0,
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

    # Get course combinations and ATARs (exclude NG students)
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        AND sym.psam_score > 0
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
        'high_performing_pairs': sorted(high_performing_pairs, key=lambda x: x['num_students'], reverse=True)[:10]  # Top 10 by enrollment
    }

def analyze_extension_trends_multiyear(conn, years=[2022, 2023, 2024]):
    """
    Track extension course uptake trends over multiple years
    """
    cursor = conn.cursor()

    extension_trends = []
    for year in years:
        # Count students by number of extensions taken
        cursor.execute("""
            SELECT
                sym.student_id,
                COUNT(DISTINCT cr.course_id) as num_extensions
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            JOIN course c ON cr.course_id = c.course_id
            WHERE sym.year = ?
            AND (c.name LIKE '%Extension%' OR c.name LIKE '%Ext %')
            GROUP BY sym.student_id
        """, (year,))

        extension_counts = Counter()
        for row in cursor.fetchall():
            student_id, num_extensions = row
            extension_counts[num_extensions] += 1

        # Get total cohort size
        cursor.execute("""
            SELECT COUNT(*) FROM student_year_metric WHERE year = ?
        """, (year,))
        cohort_size = cursor.fetchone()[0]

        total_with_extensions = sum(extension_counts.values())

        extension_trends.append({
            'year': year,
            'cohort_size': cohort_size,
            'total_with_extensions': total_with_extensions,
            'pct_with_extensions': (total_with_extensions / cohort_size * 100) if cohort_size > 0 else 0,
            'by_count': dict(extension_counts)
        })

    return extension_trends

def analyze_unit_strategy_multiyear(conn, years=[2022, 2023, 2024]):
    """
    Multi-year unit selection strategy with ASCII visualization
    """
    cursor = conn.cursor()

    unit_data = []
    for year in years:
        cursor.execute("""
            SELECT
                sym.student_id,
                sym.psam_score as atar,
                COUNT(DISTINCT cr.course_id) as num_courses,
                SUM(c2.units) as total_units
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            LEFT JOIN (
                SELECT course_id, 2 as units FROM course
            ) c2 ON cr.course_id = c2.course_id
            WHERE sym.year = ?
            AND sym.psam_score > 0
            GROUP BY sym.student_id
        """, (year,))

        students_by_units = defaultdict(list)
        for row in cursor.fetchall():
            student_id, atar, num_courses, total_units = row
            unit_count = total_units if total_units else num_courses * 2

            # ONLY include students with >= 10 units
            if unit_count >= 10:
                students_by_units[unit_count].append(atar)

        # Calculate averages (only for >= 10 units)
        unit_performance = {}
        for units, atars in students_by_units.items():
            if len(atars) >= 3:
                unit_performance[units] = {
                    'count': len(atars),
                    'avg_atar': np.mean(atars),
                    'median_atar': np.median(atars)
                }

        unit_data.append({
            'year': year,
            'unit_performance': unit_performance
        })

    # Create ASCII graph
    ascii_graph = create_unit_atar_ascii_graph(unit_data)

    return {
        'unit_data': unit_data,
        'ascii_graph': ascii_graph
    }

def create_unit_atar_ascii_graph(unit_data, width=60, height=15):
    """
    Create ASCII graph of unit count vs ATAR over multiple years
    """
    if not unit_data:
        return "No data available"

    # Collect all data points
    all_points = []
    for year_data in unit_data:
        year = year_data['year']
        for units, perf in year_data['unit_performance'].items():
            all_points.append({
                'year': year,
                'units': units,
                'avg_atar': perf['avg_atar']
            })

    if not all_points:
        return "No data available"

    # Get ranges
    min_units = min(p['units'] for p in all_points)
    max_units = max(p['units'] for p in all_points)
    min_atar = 0
    max_atar = 100

    units_range = max_units - min_units
    if units_range == 0:
        units_range = 1

    atar_range = max_atar - min_atar

    # Create grid (store lists to handle multiple points at same position)
    grid = [[[] for _ in range(width)] for _ in range(height)]

    # Create year symbol mapping dynamically
    year_symbols = {}
    for i, year_data in enumerate(unit_data):
        year_symbols[year_data['year']] = str(i + 1)

    # Plot points
    for point in all_points:
        x = int((point['units'] - min_units) / units_range * (width - 1))
        y = height - 1 - int((point['avg_atar'] - min_atar) / atar_range * (height - 1))

        if 0 <= x < width and 0 <= y < height:
            symbol = year_symbols.get(point['year'], '*')
            if symbol not in grid[y][x]:
                grid[y][x].append(symbol)

    # Convert grid lists to strings (combine symbols if multiple at same position)
    display_grid = []
    for row in grid:
        display_row = []
        for cell in row:
            if cell:
                # Sort to always show in order: 1, 2, 3
                display_row.append(''.join(sorted(cell)))
            else:
                display_row.append(' ')
        display_grid.append(display_row)

    # Build output
    lines = []
    lines.append(f"  Unit Count vs ATAR (1={unit_data[0]['year']}, 2={unit_data[1]['year']}, 3={unit_data[2]['year']})")

    for i, row in enumerate(display_grid):
        atar_val = max_atar - (i * atar_range / (height - 1))
        # Pad each cell to ensure consistent spacing
        display_row = ''.join(cell if cell != ' ' else ' ' for cell in row)
        lines.append(f" {atar_val:3.0f} | {display_row}")

    lines.append("      +" + "-" * width)
    lines.append(f"       {min_units:<{width//2}}{max_units:>{width//2}}")
    lines.append("       Units -->")

    return '\n'.join(lines)

def analyze_triple_course_combinations(conn, year):
    """
    Find 3-course combinations that produce high ATARs
    """
    cursor = conn.cursor()

    # Get course combinations and ATARs (exclude NG students)
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        AND sym.psam_score > 0
        GROUP BY sym.student_id
        HAVING COUNT(DISTINCT c.course_id) >= 5
    """, (year,))

    # Find common course triples and their average ATAR
    course_triple_atars = defaultdict(list)
    for row in cursor.fetchall():
        student_id, atar, courses_str = row
        courses = sorted(courses_str.split(','))

        # Look at triples of courses
        for i in range(len(courses)):
            for j in range(i+1, len(courses)):
                for k in range(j+1, len(courses)):
                    triple = f"{courses[i]} + {courses[j]} + {courses[k]}"
                    course_triple_atars[triple].append(atar)

    # Find high-performing triples
    high_performing_triples = []
    for triple, atars in course_triple_atars.items():
        if len(atars) >= 3:  # At least 3 students
            avg_atar = np.mean(atars)
            if avg_atar > 90:
                high_performing_triples.append({
                    'courses': triple,
                    'avg_atar': avg_atar,
                    'num_students': len(atars)
                })

    return sorted(high_performing_triples, key=lambda x: x['num_students'], reverse=True)[:10]  # Top 10 by enrollment

def analyze_quad_course_combinations(conn, year):
    """
    Find 4-course combinations that produce high ATARs
    """
    cursor = conn.cursor()

    # Get course combinations and ATARs (exclude NG students)
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        AND sym.psam_score > 0
        GROUP BY sym.student_id
        HAVING COUNT(DISTINCT c.course_id) >= 5
    """, (year,))

    # Find common course quads and their average ATAR
    course_quad_atars = defaultdict(list)
    for row in cursor.fetchall():
        student_id, atar, courses_str = row
        courses = sorted(courses_str.split(','))

        # Look at quads of courses (4-course combinations)
        for i in range(len(courses)):
            for j in range(i+1, len(courses)):
                for k in range(j+1, len(courses)):
                    for l in range(k+1, len(courses)):
                        quad = f"{courses[i]} + {courses[j]} + {courses[k]} + {courses[l]}"
                        course_quad_atars[quad].append(atar)

    # Find high-performing quads
    high_performing_quads = []
    for quad, atars in course_quad_atars.items():
        if len(atars) >= 3:  # At least 3 students
            avg_atar = np.mean(atars)
            if avg_atar > 90:
                high_performing_quads.append({
                    'courses': quad,
                    'avg_atar': avg_atar,
                    'num_students': len(atars)
                })

    return sorted(high_performing_quads, key=lambda x: x['num_students'], reverse=True)[:10]  # Top 10 by enrollment

def analyze_poor_course_combinations(conn, year):
    """
    Find course combinations that produce lower ATARs
    """
    cursor = conn.cursor()

    # Get course combinations and ATARs (exclude NG students)
    cursor.execute("""
        SELECT
            sym.student_id,
            sym.psam_score as atar,
            GROUP_CONCAT(c.name) as courses
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        AND sym.psam_score > 0
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

    # Find low-performing pairs
    low_performing_pairs = []
    for pair, atars in course_pair_atars.items():
        if len(atars) >= 3:  # At least 3 students
            avg_atar = np.mean(atars)
            if avg_atar < 75:
                low_performing_pairs.append({
                    'courses': pair,
                    'avg_atar': avg_atar,
                    'num_students': len(atars)
                })

    return sorted(low_performing_pairs, key=lambda x: x['avg_atar'])  # ALL low-performing pairs

def analyze_hidden_cohorts(conn, years=[2022, 2023, 2024]):
    """
    Find multiple 'hidden cohorts' - students who might benefit from different course strategies
    """
    cursor = conn.cursor()

    all_cohorts = {
        'cohort_1': [],  # 80-90 ATAR with Advanced but no Extension
        'cohort_2': [],  # 70-80 ATAR not taking Advanced courses
        'cohort_3': [],  # 90-95 ATAR taking only 1 extension
        'cohort_4': []   # High ATAR (>95) taking <12 units
    }

    for year in years:
        # COHORT 1: 80-90 ATAR with Advanced but no Extension
        cursor.execute("""
            SELECT DISTINCT
                sym.student_id,
                sym.psam_score as atar,
                GROUP_CONCAT(c.name) as courses
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            JOIN course c ON cr.course_id = c.course_id
            WHERE sym.year = ?
            AND sym.psam_score BETWEEN 80 AND 90
            AND sym.student_id NOT IN (
                SELECT DISTINCT sym2.student_id
                FROM student_year_metric sym2
                JOIN course_result cr2 ON sym2.student_id = cr2.student_id AND sym2.year = cr2.year
                JOIN course c2 ON cr2.course_id = c2.course_id
                WHERE sym2.year = ?
                AND (c2.name LIKE '%Extension%' OR c2.name LIKE '%Ext %')
            )
            GROUP BY sym.student_id
        """, (year, year))

        cohort_1_students = []
        for row in cursor.fetchall():
            student_id, atar, courses_str = row
            courses = courses_str.split(',')
            advanced_courses = [c for c in courses if 'Advanced' in c]
            if advanced_courses:
                cohort_1_students.append({
                    'student_id': student_id,
                    'atar': atar,
                    'courses': advanced_courses
                })

        all_cohorts['cohort_1'].append({
            'year': year,
            'description': '80-90 ATAR with Advanced but no Extension',
            'count': len(cohort_1_students),
            'examples': cohort_1_students  # ALL students in this cohort
        })

        # COHORT 2: 70-80 ATAR not taking Advanced courses
        cursor.execute("""
            SELECT DISTINCT
                sym.student_id,
                sym.psam_score as atar,
                GROUP_CONCAT(c.name) as courses
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            JOIN course c ON cr.course_id = c.course_id
            WHERE sym.year = ?
            AND sym.psam_score BETWEEN 70 AND 80
            GROUP BY sym.student_id
        """, (year,))

        cohort_2_students = []
        for row in cursor.fetchall():
            student_id, atar, courses_str = row
            courses = courses_str.split(',')
            has_advanced = any('Advanced' in c for c in courses)
            if not has_advanced:
                cohort_2_students.append({
                    'student_id': student_id,
                    'atar': atar,
                    'courses': [c for c in courses if 'Standard' in c or 'Mathematics' in c]  # ALL relevant courses
                })

        all_cohorts['cohort_2'].append({
            'year': year,
            'description': '70-80 ATAR not taking any Advanced courses',
            'count': len(cohort_2_students),
            'examples': cohort_2_students  # ALL students in this cohort
        })

        # COHORT 3: 90-95 ATAR taking only 1 extension
        cursor.execute("""
            SELECT
                sym.student_id,
                sym.psam_score as atar,
                COUNT(DISTINCT cr.course_id) as num_extensions,
                GROUP_CONCAT(c.name) as extension_courses
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            JOIN course c ON cr.course_id = c.course_id
            WHERE sym.year = ?
            AND sym.psam_score BETWEEN 90 AND 95
            AND (c.name LIKE '%Extension%' OR c.name LIKE '%Ext %')
            GROUP BY sym.student_id
            HAVING num_extensions = 1
        """, (year,))

        cohort_3_students = []
        for row in cursor.fetchall():
            student_id, atar, num_ext, ext_courses = row
            cohort_3_students.append({
                'student_id': student_id,
                'atar': atar,
                'courses': [ext_courses]
            })

        all_cohorts['cohort_3'].append({
            'year': year,
            'description': '90-95 ATAR taking only 1 extension',
            'count': len(cohort_3_students),
            'examples': cohort_3_students  # ALL students in this cohort
        })

        # COHORT 4: High ATAR (>95) taking <12 units
        cursor.execute("""
            SELECT
                sym.student_id,
                sym.psam_score as atar,
                COUNT(DISTINCT cr.course_id) as num_courses
            FROM student_year_metric sym
            JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
            WHERE sym.year = ?
            AND sym.psam_score > 95
            GROUP BY sym.student_id
        """, (year,))

        cohort_4_students = []
        for row in cursor.fetchall():
            student_id, atar, num_courses = row
            total_units = num_courses * 2
            if total_units < 12:
                cohort_4_students.append({
                    'student_id': student_id,
                    'atar': atar,
                    'units': total_units
                })

        all_cohorts['cohort_4'].append({
            'year': year,
            'description': 'High ATAR (>95) taking <12 units',
            'count': len(cohort_4_students),
            'examples': cohort_4_students  # ALL students in this cohort
        })

    return all_cohorts

def generate_exploratory_insights(conn, year):
    """
    Main function to generate all exploratory insights
    """
    print(f"Generating exploratory insights for {year}...")

    insights = {
        'year': year,
        'course_selection': analyze_course_selection_optimization(conn, year),
        'extensions': analyze_extension_decisions(conn, year),
        'extension_trends': analyze_extension_trends_multiyear(conn),
        'unit_strategy': analyze_unit_selection_strategy(conn, year),
        'unit_strategy_multiyear': analyze_unit_strategy_multiyear(conn),
        'cohort_trends': analyze_cohort_trends_multiyear(conn),
        'optimal_combinations': analyze_optimal_course_combinations(conn, year),
        'triple_combinations': analyze_triple_course_combinations(conn, year),
        'quad_combinations': analyze_quad_course_combinations(conn, year),
        'poor_combinations': analyze_poor_course_combinations(conn, year),
        'hidden_cohorts': analyze_hidden_cohorts(conn)
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
