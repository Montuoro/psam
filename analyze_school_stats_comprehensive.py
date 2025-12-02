"""
Comprehensive School-Level Statistics
Addresses 10 key analytical dimensions for PSAM review
"""
import sqlite3
import numpy as np
from collections import defaultdict
from pathlib import Path

def get_multi_year_cohort_trends(conn, course_name, analysis_year, years_back=2):
    """
    Point 1: Course cohort size and scaled mark trends over previous 2 years
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cr.year,
            COUNT(DISTINCT cr.student_id) as cohort_size,
            AVG(cr.scaled_score) as avg_scaled,
            AVG(cr.combined_mark) as avg_hsc,
            cs.mean as course_mean
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        LEFT JOIN course_summary cs ON cs.course_id = c.course_id AND cs.year = cr.year
        WHERE c.name = ?
        AND cr.year <= ?
        AND cr.year >= ?
        GROUP BY cr.year
        ORDER BY cr.year DESC
    """, (course_name, analysis_year, analysis_year - years_back))

    years_data = [dict(zip(['year', 'cohort_size', 'avg_scaled', 'avg_hsc', 'course_mean'], row))
                  for row in cursor.fetchall()]

    if len(years_data) < 2:
        return None

    # Calculate year-over-year changes
    changes = []
    for i in range(len(years_data) - 1):
        current = years_data[i]
        prev = years_data[i + 1]

        cohort_change = current['cohort_size'] - prev['cohort_size']
        cohort_pct = (cohort_change / prev['cohort_size'] * 100) if prev['cohort_size'] > 0 else 0

        scaled_change = current['avg_scaled'] - prev['avg_scaled']

        notable = False
        comment = []

        if abs(cohort_pct) > 30:
            notable = True
            direction = "surge" if cohort_change > 0 else "drop"
            comment.append(f"{abs(cohort_pct):.0f}% cohort {direction}")

        if abs(scaled_change) > 3:
            notable = True
            direction = "improvement" if scaled_change > 0 else "decline"
            comment.append(f"{abs(scaled_change):.1f}pt scaled mark {direction}")

        changes.append({
            'from_year': prev['year'],
            'to_year': current['year'],
            'cohort_change': cohort_change,
            'cohort_pct': cohort_pct,
            'scaled_change': scaled_change,
            'notable': notable,
            'comment': '; '.join(comment) if comment else 'stable'
        })

    return {
        'years_data': years_data,
        'changes': changes
    }

def analyze_atar_contribution_percentiles(conn, course_name, analysis_year):
    """
    Point 4: Percentile contribution to ATAR
    Identify 0% contributors, low contributors, trends
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cr.student_id,
            cr.scaled_score * 2 as scaled_contribution,
            cr.unit_count,
            sym.psam_score as atar,
            sym.total_unit_scores
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        WHERE c.name = ?
        AND cr.year = ?
    """, (course_name, analysis_year))

    students = []
    zero_contributors = []
    low_contributors = []

    for row in cursor.fetchall():
        student_id, scaled, units, atar, total_units = row

        contribution_pct = (scaled / total_units * 100) if total_units > 0 else 0

        students.append({
            'student_id': student_id,
            'scaled': scaled,
            'atar': atar,
            'contribution_pct': contribution_pct
        })

        if contribution_pct < 0.1:
            zero_contributors.append(student_id)
        elif contribution_pct < 15:
            low_contributors.append(student_id)

    if not students:
        return None

    contrib_values = [s['contribution_pct'] for s in students]

    return {
        'total_students': len(students),
        'zero_contributors': len(zero_contributors),
        'low_contributors': len(low_contributors),
        'avg_contribution': np.mean(contrib_values),
        'median_contribution': np.median(contrib_values),
        'zero_contributor_ids': zero_contributors[:5],
        'interpretation': f"{len(zero_contributors)} students got no ATAR benefit from this course" if zero_contributors else "All students gained ATAR benefit"
    }

def analyze_mxp_performance(conn, course_name, analysis_year):
    """
    Point 7: MXP (map_score) analysis - Performance relative to expectations
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cr.student_id,
            cr.combined_mark as hsc_mark,
            cr.scaled_score * 2 as scaled_contribution,
            cr.map_score as expected_score,
            sym.psam_score as actual_atar,
            cr.rank
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        WHERE c.name = ?
        AND cr.year = ?
        AND cr.map_score IS NOT NULL
    """, (course_name, analysis_year))

    students = []
    for row in cursor.fetchall():
        student_id, hsc, scaled, expected, actual_atar, rank = row

        relative_performance = hsc - expected if expected else 0

        students.append({
            'student_id': student_id,
            'hsc': hsc,
            'expected': expected,
            'actual_atar': actual_atar,
            'relative': relative_performance,
            'rank': rank
        })

    if not students:
        return None

    high_exp = [s for s in students if s['expected'] > 85]
    mid_exp = [s for s in students if 70 <= s['expected'] <= 85]
    low_exp = [s for s in students if s['expected'] < 70]

    outperformers = [s for s in students if s['relative'] > 5]
    underperformers = [s for s in students if s['relative'] < -5]

    return {
        'total_students': len(students),
        'high_expectation': {
            'count': len(high_exp),
            'avg_relative': np.mean([s['relative'] for s in high_exp]) if high_exp else 0
        },
        'mid_expectation': {
            'count': len(mid_exp),
            'avg_relative': np.mean([s['relative'] for s in mid_exp]) if mid_exp else 0
        },
        'low_expectation': {
            'count': len(low_exp),
            'avg_relative': np.mean([s['relative'] for s in low_exp]) if low_exp else 0
        },
        'outperformers': len(outperformers),
        'underperformers': len(underperformers),
        'outperformer_ids': [s['student_id'] for s in outperformers[:5]],
        'underperformer_ids': [s['student_id'] for s in underperformers[:5]],
        'expectation_gap': "Low expectation students performed worse" if low_exp and np.mean([s['relative'] for s in low_exp]) < -3 else "Performance consistent across expectations"
    }

def analyze_rank_changes_assessment_to_exam(conn, course_name, analysis_year):
    """
    Point 8: Students who changed rank between assessment and exam
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cr.student_id,
            cr.school_assessment,
            cr.moderated_assessment,
            cr.scaled_exam_mark,
            cr.combined_mark,
            cr.rank as final_rank
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ?
        AND cr.year = ?
        AND cr.school_assessment IS NOT NULL
        ORDER BY cr.school_assessment DESC
    """, (course_name, analysis_year))

    students = list(cursor.fetchall())

    if len(students) < 2:
        return None

    for i, student in enumerate(students):
        students[i] = {
            'student_id': student[0],
            'assessment': student[1],
            'moderated': student[2],
            'exam': student[3],
            'final': student[4],
            'final_rank': student[5],
            'assessment_rank': i + 1
        }

    rank_changes = []
    for s in students:
        rank_change = s['assessment_rank'] - s['final_rank'] if s['final_rank'] else 0

        if abs(rank_change) >= 3:
            direction = "improved" if rank_change > 0 else "dropped"
            rank_changes.append({
                'student_id': s['student_id'],
                'assessment_rank': s['assessment_rank'],
                'final_rank': s['final_rank'],
                'rank_change': rank_change,
                'direction': direction,
                'assessment_mark': s['assessment'],
                'exam_mark': s['exam']
            })

    return {
        'total_students': len(students),
        'significant_changes': len(rank_changes),
        'changes': sorted(rank_changes, key=lambda x: abs(x['rank_change']), reverse=True)[:10]
    }

def analyze_rank_to_scaled_progression(conn, course_name, analysis_year, years_back=2):
    """
    Point 3: Rank-to-scaled progression across 3 years
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cr.year,
            cr.rank,
            cr.scaled_score * 2 as scaled_contribution,
            cr.combined_mark as hsc_mark
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ?
        AND cr.year <= ?
        AND cr.year >= ?
        AND cr.rank IS NOT NULL
        ORDER BY cr.year DESC, cr.rank ASC
    """, (course_name, analysis_year, analysis_year - years_back))

    by_year = defaultdict(list)
    for row in cursor.fetchall():
        year, rank, scaled, hsc = row
        by_year[year].append({'rank': rank, 'scaled': scaled, 'hsc': hsc})

    if not by_year:
        return None

    year_analysis = {}
    for year, data in by_year.items():
        if len(data) < 3:
            continue

        ranks = [d['rank'] for d in data]
        scaled = [d['scaled'] for d in data]

        if len(set(ranks)) > 1:
            slope = np.polyfit(ranks, scaled, 1)[0]

            year_analysis[year] = {
                'total_students': len(data),
                'rank_1_scaled': data[0]['scaled'],
                'last_rank_scaled': data[-1]['scaled'],
                'total_spread': data[0]['scaled'] - data[-1]['scaled'],
                'slope': slope,
                'compressed': abs(slope) < 1.0
            }

    trends = []
    if len(year_analysis) > 1:
        years = sorted(year_analysis.keys(), reverse=True)
        current = year_analysis[years[0]]
        prev = year_analysis[years[1]] if len(years) > 1 else None

        if prev:
            if current['compressed'] and not prev['compressed']:
                trends.append("Rank compression - top students not pulling away as much")
            elif not current['compressed'] and prev['compressed']:
                trends.append("Rank spread increasing - larger performance gaps")

    return {
        'by_year': year_analysis,
        'trends': trends
    }

def analyze_relative_course_performance(conn, course_name, analysis_year):
    """
    Point 5: How students in this course performed relative to their other courses
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT student_id
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ? AND cr.year = ?
    """, (course_name, analysis_year))

    student_ids = [row[0] for row in cursor.fetchall()]

    if not student_ids:
        return None

    placeholders = ','.join('?' * len(student_ids))
    cursor.execute(f"""
        SELECT
            cr.student_id,
            c.name as course,
            cr.combined_mark
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE cr.student_id IN ({placeholders})
        AND cr.year = ?
    """, (*student_ids, analysis_year))

    student_courses = defaultdict(list)
    for row in cursor.fetchall():
        student_id, course, mark = row
        student_courses[student_id].append({'course': course, 'mark': mark})

    relative_performance = []
    for student_id, courses in student_courses.items():
        target_mark = next((c['mark'] for c in courses if c['course'] == course_name), None)
        other_marks = [c['mark'] for c in courses if c['course'] != course_name and c['mark']]

        if target_mark and other_marks:
            other_avg = np.mean(other_marks)
            relative = target_mark - other_avg
            relative_performance.append(relative)

    if not relative_performance:
        return None

    avg_relative = np.mean(relative_performance)
    outperform_count = sum(1 for r in relative_performance if r > 5)
    underperform_count = sum(1 for r in relative_performance if r < -5)

    return {
        'avg_relative_performance': avg_relative,
        'outperformers': outperform_count,
        'underperformers': underperform_count,
        'interpretation': "Students perform better in this course than their other courses" if avg_relative > 3 else "Students perform worse in this course than their other courses" if avg_relative < -3 else "Performance consistent with other courses"
    }

def analyze_course_synergies_expanded(conn, course_name, analysis_year):
    """
    Point 6: Expanded synergy analysis - which courses work well/poorly together
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT student_id
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ? AND cr.year = ?
    """, (course_name, analysis_year))

    student_ids = [row[0] for row in cursor.fetchall()]

    if not student_ids:
        return None

    placeholders = ','.join('?' * len(student_ids))
    cursor.execute(f"""
        SELECT
            c.name as other_course,
            AVG(cr.combined_mark) as avg_mark,
            COUNT(DISTINCT cr.student_id) as student_count
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE cr.student_id IN ({placeholders})
        AND cr.year = ?
        AND c.name != ?
        GROUP BY c.name
        HAVING COUNT(DISTINCT cr.student_id) >= 3
    """, (*student_ids, analysis_year, course_name))

    course_pairs = []
    for row in cursor.fetchall():
        other_course, avg_mark, count = row
        course_pairs.append({
            'course': other_course,
            'avg_mark': avg_mark,
            'students': count
        })

    positive = sorted([c for c in course_pairs if c['avg_mark'] > 85], key=lambda x: x['avg_mark'], reverse=True)[:5]
    negative = sorted([c for c in course_pairs if c['avg_mark'] < 75], key=lambda x: x['avg_mark'])[:5]

    return {
        'positive_synergies': positive,
        'negative_synergies': negative
    }

def analyze_nesa_bands(conn, course_name, analysis_year):
    """
    Point 9: NESA bands analysis
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            band,
            COUNT(*) as count,
            AVG(combined_mark) as avg_mark,
            AVG(scaled_score * 2) as avg_scaled
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        WHERE c.name = ?
        AND cr.year = ?
        AND band IS NOT NULL
        GROUP BY band
        ORDER BY band DESC
    """, (course_name, analysis_year))

    bands = []
    total_students = 0
    for row in cursor.fetchall():
        band, count, avg_mark, avg_scaled = row
        bands.append({
            'band': band,
            'count': count,
            'avg_mark': avg_mark,
            'avg_scaled': avg_scaled
        })
        total_students += count

    if not bands:
        return None

    band_6_count = sum(b['count'] for b in bands if b['band'] == 'Band 6' or b['band'] == '6')
    band_5_6_count = sum(b['count'] for b in bands if b['band'] in ['Band 6', '6', 'Band 5', '5'])

    return {
        'bands': bands,
        'total_students': total_students,
        'band_6_count': band_6_count,
        'band_5_6_count': band_5_6_count,
        'band_6_pct': (band_6_count / total_students * 100) if total_students > 0 else 0,
        'band_5_6_pct': (band_5_6_count / total_students * 100) if total_students > 0 else 0
    }

def analyze_course_atar_correlation(conn, course_name, analysis_year):
    """
    Point 10: Course correlation with ATAR levels
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sym.psam_score as atar,
            cr.combined_mark as hsc_mark,
            cr.scaled_score * 2 as scaled_contribution
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        WHERE c.name = ?
        AND cr.year = ?
    """, (course_name, analysis_year))

    data = [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    if not data:
        return None

    high_atar = [(d[1], d[2]) for d in data if d[0] >= 90]
    mid_atar = [(d[1], d[2]) for d in data if 70 <= d[0] < 90]
    low_atar = [(d[1], d[2]) for d in data if d[0] < 70]

    return {
        'high_atar_students': {
            'count': len(high_atar),
            'avg_course_mark': np.mean([d[0] for d in high_atar]) if high_atar else 0,
            'avg_contribution': np.mean([d[1] for d in high_atar]) if high_atar else 0
        },
        'mid_atar_students': {
            'count': len(mid_atar),
            'avg_course_mark': np.mean([d[0] for d in mid_atar]) if mid_atar else 0,
            'avg_contribution': np.mean([d[1] for d in mid_atar]) if mid_atar else 0
        },
        'low_atar_students': {
            'count': len(low_atar),
            'avg_course_mark': np.mean([d[0] for d in low_atar]) if low_atar else 0,
            'avg_contribution': np.mean([d[1] for d in low_atar]) if low_atar else 0
        },
        'correlation': "Predominantly high-ATAR course" if len(high_atar) > len(mid_atar) + len(low_atar) else "Mixed ATAR levels" if len(mid_atar) > len(high_atar) else "Lower-ATAR course"
    }

if __name__ == "__main__":
    print("Testing comprehensive school statistics...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")
    conn.row_factory = sqlite3.Row

    course = "Biology"
    year = 2024

    print(f"\n1. Multi-year cohort trends:")
    trends = get_multi_year_cohort_trends(conn, course, year)
    if trends:
        for change in trends['changes']:
            print(f"   {change['from_year']}->{change['to_year']}: {change['comment']}")

    print(f"\n4. ATAR contribution percentiles:")
    contrib = analyze_atar_contribution_percentiles(conn, course, year)
    if contrib:
        print(f"   {contrib['interpretation']}")
        print(f"   Low contributors: {contrib['low_contributors']}")

    print(f"\n7. MXP performance:")
    mxp = analyze_mxp_performance(conn, course, year)
    if mxp:
        print(f"   {mxp['expectation_gap']}")
        print(f"   Outperformers: {mxp['outperformers']}, Underperformers: {mxp['underperformers']}")

    print(f"\n8. Rank changes (assessment -> exam):")
    rank_changes = analyze_rank_changes_assessment_to_exam(conn, course, year)
    if rank_changes:
        print(f"   {rank_changes['significant_changes']} students changed rank significantly")

    conn.close()
    print("\nComprehensive stats test complete!")
