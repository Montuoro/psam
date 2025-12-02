"""
Accurate School Analysis V2
Fixes:
1. Moderated vs External (rank changes)
2. MXP averages not counts
3. Clear performance metrics (no confusing HSC marks)
4. Multi-year course analysis
"""
import sqlite3
import numpy as np
from pathlib import Path
from collections import defaultdict

def analyze_course(conn, course_name, year):
    """
    Analyze a single course with ACCURATE calculations
    """
    cursor = conn.cursor()

    # Get all student results for this course
    cursor.execute("""
        SELECT
            cr.student_id,
            cr.combined_mark as hsc_mark,
            cr.school_assessment,
            cr.moderated_assessment,
            cr.scaled_exam_mark,
            cr.scaled_score as actual_scaled,
            cr.map_score as expected_scaled,
            cr.band,
            cr.rank,
            sym.psam_score as atar
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        WHERE c.name = ? AND cr.year = ?
        ORDER BY cr.rank
    """, (course_name, year))

    students = []
    for row in cursor.fetchall():
        students.append({
            'student_id': row[0],
            'hsc_mark': row[1],
            'school_assessment': row[2],
            'moderated_assessment': row[3],
            'scaled_exam_mark': row[4],
            'actual_scaled': row[5],
            'expected_scaled': row[6],
            'band': row[7],
            'rank': row[8],
            'atar': row[9]
        })

    if not students:
        return None

    # === GENERALIZED INSIGHTS ===
    cohort_size = len(students)

    # Average ATAR of students in course
    atars = [s['atar'] for s in students if s['atar']]
    avg_atar = np.mean(atars) if atars else 0

    # CORRECT: Moderated vs External (not school assessment vs external)
    moderated_marks = [s['moderated_assessment'] for s in students if s['moderated_assessment']]
    exam_marks = [s['scaled_exam_mark'] for s in students if s['scaled_exam_mark']]
    avg_moderated = np.mean(moderated_marks) if moderated_marks else 0
    avg_exam = np.mean(exam_marks) if exam_marks else 0
    moderated_exam_gap = avg_moderated - avg_exam

    # Rank order changes between moderated and external
    rank_changes = []
    for student in students:
        if student['moderated_assessment'] and student['scaled_exam_mark']:
            rank_changes.append({
                'student_id': student['student_id'],
                'moderated': student['moderated_assessment'],
                'exam': student['scaled_exam_mark']
            })

    # Calculate rank positions for moderated and exam
    moderated_ranked = sorted(rank_changes, key=lambda x: x['moderated'], reverse=True)
    exam_ranked = sorted(rank_changes, key=lambda x: x['exam'], reverse=True)

    # Map student_id to rank positions
    moderated_ranks = {s['student_id']: i+1 for i, s in enumerate(moderated_ranked)}
    exam_ranks = {s['student_id']: i+1 for i, s in enumerate(exam_ranked)}

    # Calculate rank changes
    significant_rank_changes = []
    for student_id in moderated_ranks:
        mod_rank = moderated_ranks[student_id]
        exam_rank = exam_ranks[student_id]
        rank_change = mod_rank - exam_rank  # Positive = improved on exam

        if abs(rank_change) >= 3:  # Significant change
            significant_rank_changes.append({
                'student_id': student_id,
                'rank_change': rank_change,
                'mod_rank': mod_rank,
                'exam_rank': exam_rank
            })

    # Bands
    band_counts = {}
    for s in students:
        if s['band']:
            band_counts[s['band']] = band_counts.get(s['band'], 0) + 1

    # MXP - WITH AVERAGES not just counts
    mxp_gaps = []
    mxp_exceeded = 0
    mxp_below = 0
    mxp_on_target = 0

    for s in students:
        if s['actual_scaled'] is not None and s['expected_scaled'] is not None:
            gap = s['actual_scaled'] - s['expected_scaled']
            mxp_gaps.append(gap)

            # Match scatter plot visual: above/on/below the y=x line
            # No tolerance - exact comparison
            if gap > 0:
                mxp_exceeded += 1
            elif gap < 0:
                mxp_below += 1
            else:
                mxp_on_target += 1

    avg_mxp_gap = np.mean(mxp_gaps) if mxp_gaps else 0
    median_mxp_gap = np.median(mxp_gaps) if mxp_gaps else 0

    mxp_exceeded_pct = (mxp_exceeded / cohort_size * 100) if cohort_size > 0 else 0
    mxp_below_pct = (mxp_below / cohort_size * 100) if cohort_size > 0 else 0
    mxp_on_target_pct = (mxp_on_target / cohort_size * 100) if cohort_size > 0 else 0

    # === MULTI-YEAR ANALYSIS ===
    cursor.execute("""
        SELECT
            cr.year,
            AVG(cr.scaled_score) as avg_scaled,
            COUNT(*) as cohort_size
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ?
        AND cr.year >= ?
        GROUP BY cr.year
        ORDER BY cr.year ASC
    """, (course_name, year - 4))

    historical_scaled = []
    for row in cursor.fetchall():
        historical_scaled.append({
            'year': row[0],
            'avg_scaled': row[1],
            'cohort_size': row[2]
        })

    # Year-on-year change
    yoy_change = None
    if len(historical_scaled) >= 2:
        current = historical_scaled[-1]
        previous = historical_scaled[-2]
        yoy_change = {
            'from_year': previous['year'],
            'to_year': current['year'],
            'scaled_change': current['avg_scaled'] - previous['avg_scaled'],
            'cohort_change': current['cohort_size'] - previous['cohort_size']
        }

    # MXP trends over time
    cursor.execute("""
        SELECT
            cr.year,
            AVG(cr.scaled_score - cr.map_score) as avg_mxp_gap
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ?
        AND cr.year >= ?
        AND cr.map_score IS NOT NULL
        GROUP BY cr.year
        ORDER BY cr.year ASC
    """, (course_name, year - 4))

    historical_mxp = []
    for row in cursor.fetchall():
        historical_mxp.append({
            'year': row[0],
            'avg_mxp_gap': row[1]
        })

    # === DEEPER ANALYSIS ===

    # Top and bottom performers (NO confusing HSC marks)
    top_3 = students[:min(3, len(students))]
    bottom_3 = students[-min(3, len(students)):]

    # MXP underperformers (specific students needing intervention)
    # Use gap < -2 for "significantly below" requiring intervention
    mxp_underperformers = []
    for s in students:
        if s['actual_scaled'] is not None and s['expected_scaled'] is not None:
            gap = s['actual_scaled'] - s['expected_scaled']
            if gap < -2:
                mxp_underperformers.append({
                    'student_id': s['student_id'],
                    'gap': gap,
                    'actual': s['actual_scaled'],
                    'expected': s['expected_scaled']
                })

    return {
        'course_name': course_name,
        'generalized': {
            'cohort_size': cohort_size,
            'avg_atar': avg_atar,
            'avg_moderated': avg_moderated,
            'avg_exam': avg_exam,
            'moderated_exam_gap': moderated_exam_gap,
            'band_counts': band_counts,
            'mxp_avg_gap': avg_mxp_gap,
            'mxp_median_gap': median_mxp_gap,
            'mxp_exceeded_pct': mxp_exceeded_pct,
            'mxp_below_pct': mxp_below_pct,
            'mxp_on_target_pct': mxp_on_target_pct,
            'significant_rank_changes_count': len(significant_rank_changes)
        },
        'multiyear': {
            'historical_scaled': historical_scaled,
            'yoy_change': yoy_change,
            'historical_mxp': historical_mxp
        },
        'deeper': {
            'top_3': top_3,
            'bottom_3': bottom_3,
            'significant_rank_changes': sorted(significant_rank_changes, key=lambda x: abs(x['rank_change']), reverse=True),
            'mxp_underperformers': sorted(mxp_underperformers, key=lambda x: x['gap'])
        }
    }

def analyze_school(conn, year):
    """
    Overall school analysis: generalized → deep
    """
    cursor = conn.cursor()

    # Get all courses
    cursor.execute("""
        SELECT DISTINCT c.name
        FROM course c
        JOIN course_result cr ON c.course_id = cr.course_id
        WHERE cr.year = ?
        ORDER BY c.name
    """, (year,))

    courses = [row[0] for row in cursor.fetchall()]

    # Analyze each course
    course_analyses = []
    for course_name in courses:
        analysis = analyze_course(conn, course_name, year)
        if analysis:
            course_analyses.append(analysis)

    # Get school-wide ATAR stats
    cursor.execute("""
        SELECT
            AVG(psam_score) as avg_atar,
            MIN(psam_score) as min_atar,
            MAX(psam_score) as max_atar,
            COUNT(*) as total_students
        FROM student_year_metric
        WHERE year = ?
    """, (year,))

    school_stats = cursor.fetchone()

    # Identify courses of concern
    courses_of_concern = []
    for analysis in course_analyses:
        gen = analysis['generalized']
        concerns = []

        # MXP issues (using percentage now)
        if gen['mxp_below_pct'] > 50:
            concerns.append(f"{gen['mxp_below_pct']:.0f}% below expectations (avg gap: {gen['mxp_avg_gap']:.1f})")

        # Moderated-exam misalignment
        if abs(gen['moderated_exam_gap']) > 8:
            direction = "over-moderated" if gen['moderated_exam_gap'] > 0 else "under-moderated"
            concerns.append(f"Large moderated-exam gap ({gen['moderated_exam_gap']:.1f}pts, {direction})")

        # Significant rank changes
        if gen['significant_rank_changes_count'] > gen['cohort_size'] * 0.3:
            concerns.append(f"{gen['significant_rank_changes_count']} students had major rank changes")

        if concerns:
            courses_of_concern.append({
                'course': analysis['course_name'],
                'concerns': concerns,
                'cohort_size': gen['cohort_size']
            })

    return {
        'year': year,
        'school_generalized': {
            'avg_atar': school_stats[0],
            'min_atar': school_stats[1],
            'max_atar': school_stats[2],
            'total_students': school_stats[3],
            'total_courses': len(course_analyses),
            'courses_of_concern_count': len(courses_of_concern)
        },
        'school_deeper': {
            'courses_of_concern': sorted(courses_of_concern, key=lambda x: len(x['concerns']), reverse=True)
        },
        'course_analyses': course_analyses
    }

if __name__ == "__main__":
    print("Testing accurate analysis V2...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")

    # Test single course
    analysis = analyze_course(conn, "Software Design & Develop", 2024)
    if analysis:
        print(f"\n{analysis['course_name']}:")
        print(f"  Cohort: {analysis['generalized']['cohort_size']} students")
        print(f"  Moderated-Exam gap: {analysis['generalized']['moderated_exam_gap']:+.1f}")
        print(f"  MXP avg gap: {analysis['generalized']['mxp_avg_gap']:+.1f} (median: {analysis['generalized']['mxp_median_gap']:+.1f})")
        print(f"  MXP: {analysis['generalized']['mxp_exceeded_pct']:.0f}% exceeded, {analysis['generalized']['mxp_below_pct']:.0f}% below")
        print(f"  Rank changes: {analysis['generalized']['significant_rank_changes_count']} students")
        if analysis['multiyear']['yoy_change']:
            yoy = analysis['multiyear']['yoy_change']
            print(f"  YoY: {yoy['scaled_change']:+.2f} scaled mark change")

    conn.close()
    print("\nV2 analysis test complete!")
