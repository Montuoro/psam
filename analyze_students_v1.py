"""
Student-Level Analysis for PSAM School Results
Focus: Individual students, rankings, specific intervention targets
"""
import sqlite3
from collections import defaultdict
import numpy as np
from pathlib import Path

def get_student_multi_course_patterns(conn, analysis_year, school_atar_avg):
    """
    Identify specific students with concerning patterns across multiple courses
    """
    cursor = conn.cursor()
    
    # Get all students with their ATAR and course results
    cursor.execute("""
        SELECT 
            sym.student_id,
            sym.psam_score as atar,
            c.name as course_name,
            cr.combined_mark as hsc_mark,
            cr.school_assessment,
            cr.scaled_exam_mark,
            cr.rank,
            cr.band
        FROM student_year_metric sym
        JOIN course_result cr ON sym.student_id = cr.student_id AND sym.year = cr.year
        JOIN course c ON cr.course_id = c.course_id
        WHERE sym.year = ?
        ORDER BY sym.student_id, c.name
    """, (analysis_year,))
    
    # Group by student
    students = defaultdict(lambda: {'atar': 0, 'courses': []})
    for row in cursor.fetchall():
        student_id = row[0]
        students[student_id]['atar'] = row[1]
        students[student_id]['courses'].append({
            'name': row[2],
            'hsc_mark': row[3],
            'assessment': row[4],
            'exam': row[5],
            'rank': row[6],
            'band': row[7]
        })
    
    # Analyze patterns
    concerning_students = []
    high_performers = []
    
    for student_id, data in students.items():
        courses = data['courses']
        atar = data['atar']
        
        # Pattern 1: Low ranks across multiple courses (bottom 25%)
        poor_ranks = [c for c in courses if c['rank'] and c['rank'] > 15]
        
        # Pattern 2: Large assessment-exam gaps (exam anxiety)
        large_gaps = [c for c in courses if c['assessment'] and c['exam'] and (c['assessment'] - c['exam']) > 10]
        
        # Pattern 3: Low HSC marks in multiple courses
        low_marks = [c for c in courses if c['hsc_mark'] and c['hsc_mark'] < 75]
        
        # Pattern 4: High achiever underperforming in specific area
        avg_mark = np.mean([c['hsc_mark'] for c in courses if c['hsc_mark']])
        outliers = [c for c in courses if c['hsc_mark'] and c['hsc_mark'] < avg_mark - 15]
        
        if len(poor_ranks) >= 3 or len(low_marks) >= 3:
            concerning_students.append({
                'student_id': student_id,
                'atar': atar,
                'atar_gap': atar - school_atar_avg,
                'num_courses': len(courses),
                'poor_ranks': poor_ranks,
                'low_marks': low_marks,
                'large_gaps': large_gaps,
                'priority': 'high' if len(low_marks) >= 4 else 'medium'
            })
        
        elif atar > 90 and len(outliers) >= 2:
            concerning_students.append({
                'student_id': student_id,
                'atar': atar,
                'atar_gap': atar - school_atar_avg,
                'num_courses': len(courses),
                'poor_ranks': [],
                'low_marks': [],
                'large_gaps': large_gaps,
                'outliers': outliers,
                'priority': 'medium',
                'note': 'High achiever with specific weak areas'
            })
        
        elif atar > school_atar_avg + 10:
            high_performers.append({
                'student_id': student_id,
                'atar': atar,
                'top_courses': sorted([c for c in courses], key=lambda x: x['hsc_mark'] or 0, reverse=True)[:3]
            })
    
    return {
        'concerning_students': sorted(concerning_students, key=lambda x: x['atar']),
        'high_performers': sorted(high_performers, key=lambda x: x['atar'], reverse=True)[:10]
    }

def get_course_rank_analysis(conn, course_name, analysis_year):
    """
    Get top 10, bottom 10, and gap analysis for a course
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cr.student_id,
            cr.combined_mark,
            cr.rank,
            cr.band,
            sym.psam_score as atar
        FROM course_result cr
        JOIN course c ON cr.course_id = c.course_id
        JOIN student_year_metric sym ON cr.student_id = sym.student_id AND cr.year = sym.year
        WHERE c.name = ? AND cr.year = ?
        ORDER BY cr.rank ASC
    """, (course_name, analysis_year))
    
    all_students = cursor.fetchall()
    
    if len(all_students) < 3:
        return None
    
    top_10 = all_students[:min(10, len(all_students))]
    bottom_10 = all_students[-min(10, len(all_students)):]
    
    # Calculate gaps
    marks = [s[1] for s in all_students if s[1]]
    if len(marks) >= 3:
        gaps = [marks[i+1] - marks[i] for i in range(len(marks)-1)]
        max_gap_idx = gaps.index(max(gaps)) if gaps else 0
        
        return {
            'top_10': [{'student_id': s[0], 'mark': s[1], 'rank': s[2], 'band': s[3], 'atar': s[4]} for s in top_10],
            'bottom_10': [{'student_id': s[0], 'mark': s[1], 'rank': s[2], 'band': s[3], 'atar': s[4]} for s in bottom_10],
            'largest_gap': {
                'gap_size': max(gaps),
                'between_ranks': max_gap_idx + 1,
                'marks': f"{marks[max_gap_idx]:.1f} → {marks[max_gap_idx+1]:.1f}"
            },
            'total_students': len(all_students)
        }
    
    return None

if __name__ == "__main__":
    print("Testing student-level analysis...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")
    conn.row_factory = sqlite3.Row
    
    # Test student patterns
    patterns = get_student_multi_course_patterns(conn, 2024, 77.67)
    print(f"\nConcerning students: {len(patterns['concerning_students'])}")
    if patterns['concerning_students']:
        student = patterns['concerning_students'][0]
        print(f"  Example: Student {student['student_id']} - ATAR {student['atar']:.1f}")
        print(f"    Low marks in {len(student['low_marks'])} courses")
    
    # Test rank analysis
    rank_analysis = get_course_rank_analysis(conn, "Biology", 2024)
    if rank_analysis:
        print(f"\nBiology rank analysis:")
        print(f"  Top student: Rank {rank_analysis['top_10'][0]['rank']}, {rank_analysis['top_10'][0]['mark']:.1f}")
        print(f"  Largest gap: {rank_analysis['largest_gap']['gap_size']:.1f} points between ranks {rank_analysis['largest_gap']['between_ranks']}")
    
    conn.close()
    print("\nStudent analysis tests complete!")
