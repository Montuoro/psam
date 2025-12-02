"""
Accurate School Analysis V3
New features:
1. Clearer courses of concern descriptions
2. YoY change and difference to school mean
3. ASCII scatter plot (scaled mark vs ATAR)
4. Class-level analysis
"""
import sqlite3
import numpy as np
from pathlib import Path
from collections import defaultdict

def create_ascii_scatter(students, width=60, height=15):
    """
    Create ASCII scatter plot of scaled marks vs ATAR
    X-axis: Scaled mark, Y-axis: ATAR
    """
    if not students:
        return "No data available"

    # Extract data points
    points = []
    for s in students:
        if s.get('actual_scaled') and s.get('atar'):
            points.append((s['actual_scaled'], s['atar']))

    if not points:
        return "No data available"

    # Determine ranges
    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]

    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = 0, 100  # ATAR range always 0-100

    # Add padding
    x_range = x_max - x_min
    if x_range == 0:
        x_range = 1  # Prevent division by zero
    x_min = max(0, x_min - x_range * 0.1)
    x_max = x_max + x_range * 0.1

    # Create grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Plot points
    for x, y in points:
        # Map to grid coordinates
        grid_x = int((x - x_min) / (x_max - x_min) * (width - 1))
        grid_y = int((y - y_min) / (y_max - y_min) * (height - 1))
        grid_y = height - 1 - grid_y  # Flip y-axis

        if 0 <= grid_x < width and 0 <= grid_y < height:
            grid[grid_y][grid_x] = '*'

    # Build output
    lines = []
    lines.append(f"  ATAR vs Scaled Mark (n={len(points)})")
    lines.append(f"  100 |" + "".join(grid[0]))

    for i in range(1, height - 1):
        atar_label = int(100 - (i / height) * 100)
        lines.append(f"  {atar_label:3d} |" + "".join(grid[i]))

    lines.append(f"    0 |" + "".join(grid[height - 1]))
    lines.append(f"      +" + "-" * width)
    lines.append(f"       {x_min:.0f}" + " " * (width - 10) + f"{x_max:.0f}")
    lines.append(f"       Scaled Mark -->")

    return "\n".join(lines)

def analyze_class_performance(conn, course_name, year):
    """
    Analyze performance by class/teacher within a course
    """
    cursor = conn.cursor()

    # Get class/teacher data for this course
    # CRITICAL FIX: Filter groups by name to match the course
    # E.g., for "Biology", only get groups where name starts with "Biology"
    cursor.execute("""
        SELECT
            g.group_id,
            g.name as class_name,
            g.teacher_id,
            t.name as teacher_name,
            COUNT(DISTINCT gm.student_id) as class_size,
            AVG(cr.scaled_score) as avg_scaled,
            AVG(cr.scaled_score - cr.map_score) as avg_mxp_gap
        FROM [group] g
        JOIN group_member gm ON g.group_id = gm.group_id
        JOIN course_result cr ON gm.student_id = cr.student_id AND cr.year = g.year
        JOIN course c ON cr.course_id = c.course_id
        LEFT JOIN teacher t ON g.teacher_id = t.teacher_id
        WHERE c.name = ?
        AND g.year = ?
        AND cr.year = ?
        AND (g.name LIKE ? OR g.name LIKE ?)
        GROUP BY g.group_id
        HAVING COUNT(DISTINCT gm.student_id) >= 3
        ORDER BY avg_scaled DESC
    """, (course_name, year, year, f"{course_name}%", f"{course_name.split()[0]}%"))

    classes = []
    for row in cursor.fetchall():
        classes.append({
            'group_id': row[0],
            'class_name': row[1],
            'teacher_id': row[2],
            'teacher_name': row[3] if row[3] else 'Unknown',
            'class_size': row[4],
            'avg_scaled': row[5],
            'avg_mxp_gap': row[6]
        })

    return classes if classes else None

def analyze_course(conn, course_name, year, school_avg_scaled=None):
    """
    Analyze a single course with all V3 features
    """
    cursor = conn.cursor()

    # Get all student results
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

    cohort_size = len(students)
    atars = [s['atar'] for s in students if s['atar']]
    avg_atar = np.mean(atars) if atars else 0

    # Moderated vs External
    moderated_marks = [s['moderated_assessment'] for s in students if s['moderated_assessment']]
    exam_marks = [s['scaled_exam_mark'] for s in students if s['scaled_exam_mark']]
    avg_moderated = np.mean(moderated_marks) if moderated_marks else 0
    avg_exam = np.mean(exam_marks) if exam_marks else 0
    moderated_exam_gap = avg_moderated - avg_exam

    # Rank order changes
    rank_changes = []
    for student in students:
        if student['moderated_assessment'] and student['scaled_exam_mark']:
            rank_changes.append({
                'student_id': student['student_id'],
                'moderated': student['moderated_assessment'],
                'exam': student['scaled_exam_mark']
            })

    moderated_ranked = sorted(rank_changes, key=lambda x: x['moderated'], reverse=True)
    exam_ranked = sorted(rank_changes, key=lambda x: x['exam'], reverse=True)

    moderated_ranks = {s['student_id']: i+1 for i, s in enumerate(moderated_ranked)}
    exam_ranks = {s['student_id']: i+1 for i, s in enumerate(exam_ranked)}

    significant_rank_changes = []
    rank_change_values = []
    for student_id in moderated_ranks:
        mod_rank = moderated_ranks[student_id]
        exam_rank = exam_ranks[student_id]
        rank_change = mod_rank - exam_rank

        if abs(rank_change) >= 3:
            significant_rank_changes.append({
                'student_id': student_id,
                'rank_change': rank_change,
                'mod_rank': mod_rank,
                'exam_rank': exam_rank
            })
            rank_change_values.append(abs(rank_change))

    mean_rank_change = np.mean(rank_change_values) if rank_change_values else 0

    # Bands
    band_counts = {}
    for s in students:
        if s['band']:
            band_counts[s['band']] = band_counts.get(s['band'], 0) + 1

    # MXP
    mxp_gaps = []
    mxp_exceeded = 0
    mxp_below = 0
    mxp_on_target = 0

    for s in students:
        if s['actual_scaled'] is not None and s['expected_scaled'] is not None:
            gap = s['actual_scaled'] - s['expected_scaled']
            mxp_gaps.append(gap)

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

    # Multi-year analysis
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

    # Current year avg scaled
    current_avg_scaled = historical_scaled[-1]['avg_scaled'] if historical_scaled else 0

    # Difference to school mean
    diff_to_school_mean = None
    if school_avg_scaled:
        diff_to_school_mean = current_avg_scaled - school_avg_scaled

    # MXP trends
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

    # ASCII scatter plot
    ascii_plot = create_ascii_scatter(students)

    # Class analysis
    class_analysis = analyze_class_performance(conn, course_name, year)

    # Deeper analysis
    top_3 = students[:min(3, len(students))]
    bottom_3 = students[-min(3, len(students)):]

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
            'significant_rank_changes_count': len(significant_rank_changes),
            'mean_rank_change': mean_rank_change,
            'current_avg_scaled': current_avg_scaled,
            'diff_to_school_mean': diff_to_school_mean
        },
        'multiyear': {
            'historical_scaled': historical_scaled,
            'yoy_change': yoy_change,
            'historical_mxp': historical_mxp
        },
        'visualization': {
            'ascii_scatter': ascii_plot
        },
        'class_analysis': class_analysis,
        'deeper': {
            'top_3': top_3,
            'bottom_3': bottom_3,
            'significant_rank_changes': sorted(significant_rank_changes, key=lambda x: abs(x['rank_change']), reverse=True),
            'mxp_underperformers': sorted(mxp_underperformers, key=lambda x: x['gap'])
        }
    }

def analyze_school(conn, year):
    """
    Overall school analysis
    """
    cursor = conn.cursor()

    # Calculate school-wide average scaled mark
    cursor.execute("""
        SELECT AVG(scaled_score)
        FROM course_result
        WHERE year = ?
        AND scaled_score IS NOT NULL
    """, (year,))
    school_avg_scaled = cursor.fetchone()[0]

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
        analysis = analyze_course(conn, course_name, year, school_avg_scaled)
        if analysis:
            course_analyses.append(analysis)

    # School-wide stats
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

    # Identify courses of concern with CLEAR descriptions
    courses_of_concern = []
    for analysis in course_analyses:
        gen = analysis['generalized']
        concerns = []

        # MXP issues with CLEAR wording
        if gen['mxp_below_pct'] > 50:
            concerns.append(f"{gen['mxp_below_pct']:.0f}% below expected MXP (avg gap: {gen['mxp_avg_gap']:.1f})")

        # Moderated-exam misalignment
        if abs(gen['moderated_exam_gap']) > 8:
            direction = "over-moderated" if gen['moderated_exam_gap'] > 0 else "under-moderated"
            concerns.append(f"Large moderated-exam gap ({gen['moderated_exam_gap']:.1f}pts, {direction})")

        # Significant rank changes with MEAN
        if gen['significant_rank_changes_count'] > gen['cohort_size'] * 0.3:
            concerns.append(f"{gen['significant_rank_changes_count']} students had major rank changes (mean change: {gen['mean_rank_change']:.1f} positions)")

        # YoY decline
        if analysis['multiyear']['yoy_change']:
            yoy = analysis['multiyear']['yoy_change']
            if yoy['scaled_change'] < -2:
                concerns.append(f"YoY decline of {abs(yoy['scaled_change']):.1f} scaled marks")

        if concerns:
            courses_of_concern.append({
                'course': analysis['course_name'],
                'concerns': concerns,
                'cohort_size': gen['cohort_size'],
                'yoy_change': analysis['multiyear']['yoy_change'],
                'diff_to_school_mean': gen['diff_to_school_mean']
            })

    return {
        'year': year,
        'school_avg_scaled': school_avg_scaled,
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
    print("Testing V3 analysis...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")

    analysis = analyze_course(conn, "Biology", 2024, 35.0)
    if analysis:
        print(f"\n{analysis['course_name']}:")
        print(f"  MXP: {analysis['generalized']['mxp_below_pct']:.0f}% below expected")
        print(f"  Rank changes: {analysis['generalized']['significant_rank_changes_count']} students (mean: {analysis['generalized']['mean_rank_change']:.1f})")
        print(f"  Diff to school mean: {analysis['generalized']['diff_to_school_mean']:+.1f}")
        print(f"  Classes: {len(analysis['class_analysis']) if analysis['class_analysis'] else 0}")
        print(f"\n{analysis['visualization']['ascii_scatter']}")

    conn.close()
    print("\nV3 analysis test complete!")
