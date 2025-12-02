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

def create_rank_order_histogram(internal_ranks, exam_ranks, width=60, height=15):
    """
    Create ASCII histogram of rank order changes
    X-axis: Rank change (-x to +x), Y-axis: Frequency
    Shows distribution of how many students had each rank change
    """
    if not internal_ranks or not exam_ranks:
        return "No data available"

    # Calculate rank changes for all students
    rank_changes = []
    for student_id in internal_ranks:
        if student_id in exam_ranks:
            int_rank = internal_ranks[student_id]
            ext_rank = exam_ranks[student_id]
            change = int_rank - ext_rank  # Positive = improved on external
            rank_changes.append(change)

    if not rank_changes:
        return "No data available"

    # Get range
    min_change = int(min(rank_changes))
    max_change = int(max(rank_changes))

    # Ensure we include 0
    min_change = min(min_change, 0)
    max_change = max(max_change, 0)

    # Create bins for histogram
    from collections import Counter
    change_counts = Counter(rank_changes)

    # Get max frequency for scaling
    max_freq = max(change_counts.values()) if change_counts else 1

    # Create grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Calculate bin width
    total_range = max_change - min_change
    if total_range == 0:
        total_range = 1
    bin_width = total_range / width

    # Plot histogram bars
    for change, count in change_counts.items():
        # Calculate x position
        x = int((change - min_change) / total_range * (width - 1))

        # Calculate bar height
        bar_height = int((count / max_freq) * (height - 1))

        # Draw bar from bottom up
        for y in range(bar_height + 1):
            grid_y = height - 1 - y
            if 0 <= x < width and 0 <= grid_y < height:
                grid[grid_y][x] = '*'

    # Draw zero line
    zero_x = int((0 - min_change) / total_range * (width - 1))
    if 0 <= zero_x < width:
        for y in range(height):
            if grid[y][zero_x] == ' ':
                grid[y][zero_x] = '|'

    # Build output
    lines = []
    lines.append(f"  Rank Order Changes Distribution (n={len(rank_changes)})")
    lines.append(f"  (Improved on external ← | → Dropped on external)")

    for i, row in enumerate(grid):
        freq_val = int(max_freq * (height - 1 - i) / (height - 1))
        if i == 0:
            lines.append(f" {max_freq:3d} | {''.join(row)}")
        elif i == height - 1:
            lines.append(f"   0 | {''.join(row)}")
        else:
            lines.append(f"     | {''.join(row)}")

    lines.append("      +" + "-" * width)

    # X-axis labels
    label_line = "       "
    label_line += f"{min_change:<{width//3}}"
    label_line += f"0".center(width//3)
    label_line += f"{max_change:>{width//3}}"
    lines.append(label_line)
    lines.append("       Rank Change (Internal - External) -->")

    return '\n'.join(lines)

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
    # Exclude NG ATAR students (atar = 0) from average ATAR calculation
    atars = [s['atar'] for s in students if s['atar'] and s['atar'] > 0]
    avg_atar = np.mean(atars) if atars else 0

    # Internal vs External (school assessment vs external exam)
    internal_marks = [s['school_assessment'] for s in students if s['school_assessment']]
    exam_marks = [s['scaled_exam_mark'] for s in students if s['scaled_exam_mark']]
    avg_internal = np.mean(internal_marks) if internal_marks else 0
    avg_exam = np.mean(exam_marks) if exam_marks else 0
    internal_exam_gap = avg_internal - avg_exam

    # Rank order changes (Internal vs External)
    rank_changes = []
    for student in students:
        if student['school_assessment'] and student['scaled_exam_mark']:
            rank_changes.append({
                'student_id': student['student_id'],
                'internal': student['school_assessment'],
                'exam': student['scaled_exam_mark']
            })

    internal_ranked = sorted(rank_changes, key=lambda x: x['internal'], reverse=True)
    exam_ranked = sorted(rank_changes, key=lambda x: x['exam'], reverse=True)

    internal_ranks = {s['student_id']: i+1 for i, s in enumerate(internal_ranked)}
    exam_ranks = {s['student_id']: i+1 for i, s in enumerate(exam_ranked)}

    significant_rank_changes = []
    rank_change_values = []
    for student_id in internal_ranks:
        int_rank = internal_ranks[student_id]
        ext_rank = exam_ranks[student_id]
        rank_change = int_rank - ext_rank

        if abs(rank_change) >= 3:
            significant_rank_changes.append({
                'student_id': student_id,
                'rank_change': rank_change,
                'internal_rank': int_rank,
                'exam_rank': ext_rank
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

    # Identity line breakdown (above/below expected performance)
    above_identity = 0
    below_identity = 0
    on_identity = 0

    for s in students:
        if s['actual_scaled'] is not None and s['expected_scaled'] is not None:
            gap = s['actual_scaled'] - s['expected_scaled']
            mxp_gaps.append(gap)

            if gap > 0:
                mxp_exceeded += 1
                above_identity += 1
            elif gap < 0:
                mxp_below += 1
                below_identity += 1
            else:
                mxp_on_target += 1
                on_identity += 1

    avg_mxp_gap = np.mean(mxp_gaps) if mxp_gaps else 0
    median_mxp_gap = np.median(mxp_gaps) if mxp_gaps else 0

    mxp_exceeded_pct = (mxp_exceeded / cohort_size * 100) if cohort_size > 0 else 0
    mxp_below_pct = (mxp_below / cohort_size * 100) if cohort_size > 0 else 0
    mxp_on_target_pct = (mxp_on_target / cohort_size * 100) if cohort_size > 0 else 0

    # Calculate proportions for identity line breakdown
    total_with_mxp = len(mxp_gaps)
    above_identity_pct = (above_identity / total_with_mxp * 100) if total_with_mxp > 0 else 0
    below_identity_pct = (below_identity / total_with_mxp * 100) if total_with_mxp > 0 else 0
    on_identity_pct = (on_identity / total_with_mxp * 100) if total_with_mxp > 0 else 0

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

    # Calculate z-scores for 5-year trend
    # Z-score shows how this course performs relative to school average each year
    z_scores = []
    for hist in historical_scaled:
        # Get school-wide course averages for this year
        cursor.execute("""
            SELECT AVG(cr.scaled_score) as course_avg
            FROM course_result cr
            JOIN course c ON cr.course_id = c.course_id
            WHERE cr.year = ?
            GROUP BY c.course_id
        """, (hist['year'],))

        course_avgs = [row[0] for row in cursor.fetchall() if row[0] is not None]
        if len(course_avgs) > 1:
            school_mean = np.mean(course_avgs)
            school_std = np.std(course_avgs, ddof=1)  # Sample standard deviation
            if school_std > 0:
                z_score = (hist['avg_scaled'] - school_mean) / school_std
                z_scores.append({
                    'year': hist['year'],
                    'z_score': z_score,
                    'avg_scaled': hist['avg_scaled']
                })

    # Statistical testing: Rank to AAS scaled mark correlation across years
    # Test if the relationship between internal rank and final scaled mark
    # is statistically different between the most recent year and previous years
    from scipy import stats as scipy_stats
    rank_scaled_correlations = []

    for hist_year in range(year - 2, year + 1):  # Last 3 years
        cursor.execute("""
            SELECT
                cr.rank,
                cr.scaled_score
            FROM course_result cr
            JOIN course c ON cr.course_id = c.course_id
            WHERE c.name = ?
            AND cr.year = ?
            AND cr.rank IS NOT NULL
            AND cr.scaled_score IS NOT NULL
            ORDER BY cr.rank
        """, (course_name, hist_year))

        year_data = cursor.fetchall()
        if len(year_data) >= 5:  # Need at least 5 data points
            ranks = [row[0] for row in year_data]
            scaled = [row[1] for row in year_data]

            # Calculate Spearman correlation (rank correlation)
            corr, p_value = scipy_stats.spearmanr(ranks, scaled)

            rank_scaled_correlations.append({
                'year': hist_year,
                'correlation': corr,
                'p_value': p_value,
                'n': len(year_data)
            })

    # Compare most recent year with 2nd and 3rd most recent
    rank_correlation_comparison = None
    if len(rank_scaled_correlations) == 3:
        recent = rank_scaled_correlations[2]  # Most recent
        second = rank_scaled_correlations[1]  # 2nd most recent
        third = rank_scaled_correlations[0]   # 3rd most recent

        # Fisher's Z transformation for comparing correlations
        def fisher_z(r):
            return 0.5 * np.log((1 + r) / (1 - r))

        z_recent = fisher_z(recent['correlation'])
        z_second = fisher_z(second['correlation'])
        z_third = fisher_z(third['correlation'])

        # Test statistic for difference
        se_diff_2nd = np.sqrt(1/(recent['n']-3) + 1/(second['n']-3))
        z_stat_2nd = (z_recent - z_second) / se_diff_2nd
        p_value_2nd = 2 * (1 - scipy_stats.norm.cdf(abs(z_stat_2nd)))

        se_diff_3rd = np.sqrt(1/(recent['n']-3) + 1/(third['n']-3))
        z_stat_3rd = (z_recent - z_third) / se_diff_3rd
        p_value_3rd = 2 * (1 - scipy_stats.norm.cdf(abs(z_stat_3rd)))

        rank_correlation_comparison = {
            'recent_year': recent['year'],
            'recent_corr': recent['correlation'],
            'second_year': second['year'],
            'second_corr': second['correlation'],
            'third_year': third['year'],
            'third_corr': third['correlation'],
            'vs_2nd_p_value': p_value_2nd,
            'vs_2nd_significant': p_value_2nd < 0.05,
            'vs_3rd_p_value': p_value_3rd,
            'vs_3rd_significant': p_value_3rd < 0.05
        }

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

    # Rank order histogram
    rank_order_plot = create_rank_order_histogram(internal_ranks, exam_ranks)

    # Class analysis
    class_analysis = analyze_class_performance(conn, course_name, year)

    # Deeper analysis - COMPREHENSIVE with definitive cut-offs
    # High performers: Band 6 (45+) OR top 10% of cohort
    high_performers = []
    scaled_threshold_high = np.percentile([s['actual_scaled'] for s in students if s['actual_scaled']], 90) if len(students) >= 10 else 45
    for s in students:
        if s['actual_scaled'] is not None:
            if s['actual_scaled'] >= 45 or s['actual_scaled'] >= scaled_threshold_high:
                high_performers.append(s)

    # Low performers: Band 1-2 (< 30) OR bottom 10% of cohort
    low_performers = []
    scaled_threshold_low = np.percentile([s['actual_scaled'] for s in students if s['actual_scaled']], 10) if len(students) >= 10 else 30
    for s in students:
        if s['actual_scaled'] is not None:
            if s['actual_scaled'] < 30 or s['actual_scaled'] <= scaled_threshold_low:
                low_performers.append(s)

    # MXP underperformers: ALL students with gap < -2
    mxp_underperformers = []
    for s in students:
        if s['actual_scaled'] is not None and s['expected_scaled'] is not None:
            gap = s['actual_scaled'] - s['expected_scaled']
            if gap < -2:
                mxp_underperformers.append({
                    'student_id': s['student_id'],
                    'gap': gap,
                    'actual': s['actual_scaled'],
                    'expected': s['expected_scaled'],
                    'rank': s.get('rank'),
                    'hsc_mark': s.get('hsc_mark')
                })

    return {
        'course_name': course_name,
        'generalized': {
            'cohort_size': cohort_size,
            'avg_atar': avg_atar,
            'avg_internal': avg_internal,
            'avg_exam': avg_exam,
            'internal_exam_gap': internal_exam_gap,
            'band_counts': band_counts,
            'mxp_avg_gap': avg_mxp_gap,
            'mxp_median_gap': median_mxp_gap,
            'mxp_exceeded_pct': mxp_exceeded_pct,
            'mxp_below_pct': mxp_below_pct,
            'mxp_on_target_pct': mxp_on_target_pct,
            'above_identity': above_identity,
            'below_identity': below_identity,
            'on_identity': on_identity,
            'above_identity_pct': above_identity_pct,
            'below_identity_pct': below_identity_pct,
            'on_identity_pct': on_identity_pct,
            'significant_rank_changes_count': len(significant_rank_changes),
            'mean_rank_change': mean_rank_change,
            'current_avg_scaled': current_avg_scaled,
            'diff_to_school_mean': diff_to_school_mean
        },
        'multiyear': {
            'historical_scaled': historical_scaled,
            'yoy_change': yoy_change,
            'historical_mxp': historical_mxp,
            'z_scores': z_scores,
            'rank_correlation_test': rank_correlation_comparison
        },
        'visualization': {
            'ascii_scatter': ascii_plot,
            'rank_order_scatter': rank_order_plot
        },
        'class_analysis': class_analysis,
        'deeper': {
            'high_performers': sorted(high_performers, key=lambda x: x['actual_scaled'], reverse=True),
            'low_performers': sorted(low_performers, key=lambda x: x['actual_scaled']),
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

    # School-wide stats (excluding NG/0.0 ATAR students)
    cursor.execute("""
        SELECT
            AVG(psam_score) as avg_atar,
            MIN(psam_score) as min_atar,
            MAX(psam_score) as max_atar,
            COUNT(*) as total_students
        FROM student_year_metric
        WHERE year = ?
        AND psam_score > 0
    """, (year,))

    school_stats = cursor.fetchone()
    # Cap max ATAR at 99.95
    school_stats = (school_stats[0], school_stats[1], min(school_stats[2], 99.95), school_stats[3])

    # Count total students including NG
    cursor.execute("""
        SELECT COUNT(*) FROM student_year_metric WHERE year = ?
    """, (year,))
    total_students_including_ng = cursor.fetchone()[0]

    # Find courses with non-ATAR students
    cursor.execute("""
        SELECT
            c.name as course_name,
            COUNT(DISTINCT CASE WHEN sym.psam_score = 0 THEN sym.student_id END) as ng_count,
            COUNT(DISTINCT sym.student_id) as total_count
        FROM course c
        JOIN course_result cr ON c.course_id = cr.course_id
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        WHERE cr.year = ?
        GROUP BY c.name
        HAVING ng_count > 0
        ORDER BY ng_count DESC, c.name
    """, (year,))

    non_atar_courses = []
    for row in cursor.fetchall():
        non_atar_courses.append({
            'course': row[0],
            'ng_count': row[1],
            'total_count': row[2],
            'ng_pct': (row[1] / row[2] * 100) if row[2] > 0 else 0
        })

    # Identify courses of concern with CLEAR descriptions
    # NOTE: Internal-exam gaps are NOT included here as they reflect assessment quality, not student performance
    courses_of_concern = []
    for analysis in course_analyses:
        gen = analysis['generalized']
        concerns = []

        # MXP issues with CLEAR wording
        if gen['mxp_below_pct'] > 50:
            concerns.append(f"{gen['mxp_below_pct']:.0f}% below expected MXP (avg gap: {gen['mxp_avg_gap']:.1f})")

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
            'total_students_including_ng': total_students_including_ng,
            'ng_students_count': total_students_including_ng - school_stats[3],
            'total_courses': len(course_analyses),
            'courses_of_concern_count': len(courses_of_concern),
            'non_atar_courses': non_atar_courses
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
