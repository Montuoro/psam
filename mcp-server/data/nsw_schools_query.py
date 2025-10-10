"""
Query API for NSW school assessment data.

Provides high-level query methods for students, schools, courses, and aggregations.
Supports complex filtering and statistical analysis.
"""

import time
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
from statistics import mean, median, stdev

from .nsw_schools import HSCStudent, HSCCourse, School, IBStudent
from .nsw_schools_loader import NSWSchoolDataLoader


class NSWSchoolQuery:
    """
    High-level query API for NSW school data.
    
    Provides methods for:
    - Student queries and filtering
    - School statistics and rankings
    - Course analysis and comparisons
    - Aggregations and top performers
    """
    
    def __init__(self, loader: NSWSchoolDataLoader):
        self.loader = loader
        self._cache: Dict[str, Any] = {}
    
    # ==================== Student Queries ====================
    
    def get_student(self, student_id: int) -> Optional[Dict]:
        """Get detailed student information by ID."""
        student = self.loader.get_student(student_id)
        if not student:
            return None
        
        return self._student_to_dict(student)
    
    def get_student_summary(self, student_id: int) -> Optional[Dict]:
        """Get summarized student information (less detail)."""
        student = self.loader.get_student(student_id)
        if not student:
            return None
        
        if isinstance(student, HSCStudent):
            return {
                'student_id': student.student_id,
                'student_name': student.student_name,
                'gender': student.gender,
                'school_id': student.school_id,
                'calendar_year': student.calendar_year,
                'psam_score': student.psam_score,
                'total_unit_scores': student.total_unit_scores,
                'unit_count': student.unit_count,
                'course_count': len(student.student_courses)
            }
        else:  # IB Student
            return {
                'student_id': student.student_id,
                'student_name': student.student_name,
                'gender': student.gender,
                'school_id': student.school_id,
                'calendar_year': student.calendar_year,
                'total_points': student.total_points,
                'diploma_awarded': student.diploma_awarded,
                'subject_count': len(student.subjects)
            }
    
    def find_students(self,
                     school_id: Optional[int] = None,
                     gender: Optional[str] = None,
                     year: Optional[int] = None,
                     min_psam: Optional[float] = None,
                     max_psam: Optional[float] = None,
                     min_units: Optional[int] = None,
                     course_name: Optional[str] = None,
                     limit: Optional[int] = None) -> List[Dict]:
        """
        Find students matching specified filters.
        
        Args:
            school_id: Filter by school
            gender: Filter by gender
            year: Filter by calendar year
            min_psam: Minimum PSAM score
            max_psam: Maximum PSAM score
            min_units: Minimum unit count
            course_name: Filter students taking this course
            limit: Maximum results to return
            
        Returns:
            List of student summaries
        """
        # Start with most specific filter to minimize iterations
        if school_id:
            students = self.loader.get_students_by_school(school_id)
        elif gender:
            students = self.loader.get_students_by_gender(gender)
        elif year:
            students = self.loader.get_students_by_year(year)
        else:
            students = list(self.loader.students_by_id.values())
        
        # Apply filters
        results = []
        for student in students:
            if not isinstance(student, HSCStudent):
                continue  # Skip IB students for now
            
            # Filter by criteria
            if gender and student.gender != gender:
                continue
            if year and student.calendar_year != year:
                continue
            if min_psam and (student.psam_score is None or student.psam_score < min_psam):
                continue
            if max_psam and (student.psam_score is None or student.psam_score > max_psam):
                continue
            if min_units and (student.unit_count is None or student.unit_count < min_units):
                continue
            if course_name:
                has_course = any(c.course_name == course_name for c in student.student_courses)
                if not has_course:
                    continue
            
            results.append(self.get_student_summary(student.student_id))
            
            if limit and len(results) >= limit:
                break
        
        return results
    
    # ==================== School Queries ====================
    
    def get_school_stats(self, school_id: int) -> Optional[Dict]:
        """Get comprehensive statistics for a school."""
        school = self.loader.get_school(school_id)
        if not school:
            return None
        
        students = self.loader.get_students_by_school(school_id)
        hsc_students = [s for s in students if isinstance(s, HSCStudent)]
        
        if not hsc_students:
            return {
                'school_id': school_id,
                'calendar_year': school.calendar_year,
                'student_count': 0
            }
        
        psam_scores = [s.psam_score for s in hsc_students if s.psam_score is not None]
        unit_scores = [s.total_unit_scores for s in hsc_students if s.total_unit_scores is not None]
        
        stats = {
            'school_id': school_id,
            'calendar_year': school.calendar_year,
            'student_count': len(hsc_students),
            'gender_distribution': self._count_by_attr(hsc_students, 'gender'),
        }
        
        if psam_scores:
            stats['psam_stats'] = {
                'mean': round(mean(psam_scores), 2),
                'median': round(median(psam_scores), 2),
                'min': round(min(psam_scores), 2),
                'max': round(max(psam_scores), 2),
                'stdev': round(stdev(psam_scores), 2) if len(psam_scores) > 1 else 0
            }
        
        if unit_scores:
            stats['unit_score_stats'] = {
                'mean': round(mean(unit_scores), 2),
                'median': round(median(unit_scores), 2),
                'min': round(min(unit_scores), 2),
                'max': round(max(unit_scores), 2)
            }
        
        return stats
    
    def get_school_rankings(self, school_id: int, course_name: str) -> Optional[Dict]:
        """Get student rankings within a school for a specific course."""
        students = self.loader.get_students_by_school(school_id)
        hsc_students = [s for s in students if isinstance(s, HSCStudent)]
        
        # Collect course results for this school
        course_results = []
        for student in hsc_students:
            for course in student.student_courses:
                if course.course_name == course_name:
                    course_results.append({
                        'student_id': student.student_id,
                        'student_name': student.student_name,
                        'combined_mark': course.combined_mark,
                        'band': course.band,
                        'rank': course.rank
                    })
        
        if not course_results:
            return None
        
        # Sort by combined mark descending
        course_results.sort(key=lambda x: x['combined_mark'] or 0, reverse=True)
        
        return {
            'school_id': school_id,
            'course_name': course_name,
            'student_count': len(course_results),
            'rankings': course_results
        }
    
    # ==================== Course Queries ====================
    
    def get_course_distribution(self, course_name: str) -> Dict:
        """Get statistical distribution for a course across all students."""
        courses = self.loader.get_courses_by_name(course_name)
        
        if not courses:
            return {'course_name': course_name, 'count': 0}
        
        combined_marks = [c.combined_mark for c in courses if c.combined_mark is not None]
        bands = [c.band for c in courses if c.band]
        
        result = {
            'course_name': course_name,
            'count': len(courses),
            'band_distribution': self._count_items(bands),
            'gender_distribution': self._count_items([c.gender for c in courses])
        }
        
        if combined_marks:
            result['mark_stats'] = {
                'mean': round(mean(combined_marks), 2),
                'median': round(median(combined_marks), 2),
                'min': round(min(combined_marks), 2),
                'max': round(max(combined_marks), 2),
                'stdev': round(stdev(combined_marks), 2) if len(combined_marks) > 1 else 0
            }
        
        return result
    
    def compare_courses(self, course_names: List[str]) -> Dict:
        """Compare statistics across multiple courses."""
        comparisons = {}
        
        for course_name in course_names:
            comparisons[course_name] = self.get_course_distribution(course_name)
        
        return {
            'courses': comparisons,
            'comparison_count': len(course_names)
        }
    
    def get_all_courses(self) -> List[str]:
        """Get list of all unique course names."""
        return self.loader.get_all_course_names()
    
    # ==================== Aggregations ====================
    
    def calculate_school_averages(self) -> List[Dict]:
        """Calculate average PSAM scores for all schools."""
        school_averages = []
        
        for school_id, school in self.loader.schools_by_id.items():
            students = self.loader.get_students_by_school(school_id)
            hsc_students = [s for s in students if isinstance(s, HSCStudent)]
            
            psam_scores = [s.psam_score for s in hsc_students if s.psam_score is not None]
            
            if psam_scores:
                school_averages.append({
                    'school_id': school_id,
                    'calendar_year': school.calendar_year,
                    'student_count': len(hsc_students),
                    'average_psam': round(mean(psam_scores), 2),
                    'median_psam': round(median(psam_scores), 2),
                    'max_psam': round(max(psam_scores), 2)
                })
        
        # Sort by average PSAM descending
        school_averages.sort(key=lambda x: x['average_psam'], reverse=True)
        
        return school_averages
    
    def get_top_performers(self, n: int = 10, metric: str = 'psam_score') -> List[Dict]:
        """
        Get top N performing students by specified metric.
        
        Args:
            n: Number of top performers to return
            metric: Metric to sort by ('psam_score', 'total_unit_scores')
            
        Returns:
            List of top student summaries
        """
        all_students = [s for s in self.loader.students_by_id.values() 
                       if isinstance(s, HSCStudent)]
        
        # Filter out None values and sort
        if metric == 'psam_score':
            students_with_metric = [(s, s.psam_score) for s in all_students 
                                   if s.psam_score is not None]
        elif metric == 'total_unit_scores':
            students_with_metric = [(s, s.total_unit_scores) for s in all_students 
                                   if s.total_unit_scores is not None]
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        students_with_metric.sort(key=lambda x: x[1], reverse=True)
        top_students = students_with_metric[:n]
        
        return [
            {
                **self.get_student_summary(student.student_id),
                metric: value
            }
            for student, value in top_students
        ]
    
    def get_course_popularity(self, top_n: int = 20) -> List[Dict]:
        """Get most popular courses by enrollment count."""
        popularity = []
        
        for course_name, courses in self.loader.courses_by_name.items():
            popularity.append({
                'course_name': course_name,
                'enrollment_count': len(courses),
                'unique_students': len(set(c.student_id for c in courses))
            })
        
        popularity.sort(key=lambda x: x['enrollment_count'], reverse=True)
        return popularity[:top_n]
    
    # ==================== Helper Methods ====================
    
    def _student_to_dict(self, student: HSCStudent | IBStudent) -> Dict:
        """Convert student model to dictionary with all details."""
        if isinstance(student, HSCStudent):
            return {
                'student_id': student.student_id,
                'student_code': student.student_code,
                'student_name': student.student_name,
                'gender': student.gender,
                'school_id': student.school_id,
                'calendar_year': student.calendar_year,
                'psam_score': student.psam_score,
                'map_score': student.map_score,
                'total_unit_scores': student.total_unit_scores,
                'unit_count': student.unit_count,
                'ext_unit_count': student.ext_unit_count,
                'result_type': student.result_type,
                'courses': [self._course_to_dict(c) for c in student.student_courses]
            }
        else:  # IB Student
            return {
                'student_id': student.student_id,
                'student_code': student.student_code,
                'student_name': student.student_name,
                'gender': student.gender,
                'school_id': student.school_id,
                'calendar_year': student.calendar_year,
                'total_points': student.total_points,
                'diploma_awarded': student.diploma_awarded,
                'subjects': [self._subject_to_dict(s) for s in student.subjects]
            }
    
    def _course_to_dict(self, course: HSCCourse) -> Dict:
        """Convert HSC course to dictionary."""
        return {
            'course_id': course.course_id,
            'course_name': course.course_name,
            'course_units': course.course_units,
            'combined_mark': course.combined_mark,
            'band': course.band,
            'rank': course.rank,
            'school_assessment': course.school_assessment,
            'moderated_assessment': course.moderated_assessment,
            'scaled_exam_mark': course.scaled_exam_mark,
            'unit_score': course.unit_score,
            'is_ext': course.is_ext,
            'award': course.award
        }
    
    def _subject_to_dict(self, subject) -> Dict:
        """Convert IB subject to dictionary."""
        return {
            'subject_id': subject.subject_id,
            'subject_name': subject.subject_name,
            'level': subject.level,
            'predicted_grade': subject.predicted_grade,
            'final_grade': subject.final_grade,
            'components': [
                {
                    'component_name': c.component_name,
                    'component_mark': c.component_mark,
                    'component_grade': c.component_grade
                }
                for c in subject.components
            ]
        }
    
    def _count_by_attr(self, items: List, attr: str) -> Dict[str, int]:
        """Count items by attribute value."""
        counts = defaultdict(int)
        for item in items:
            value = getattr(item, attr, None)
            if value is not None:
                counts[str(value)] += 1
        return dict(counts)
    
    def _count_items(self, items: List) -> Dict[str, int]:
        """Count occurrences of items in list."""
        counts = defaultdict(int)
        for item in items:
            if item is not None:
                counts[str(item)] += 1
        return dict(counts)
    
    def get_query_stats(self) -> Dict:
        """Get statistics about the loaded dataset."""
        return self.loader.get_statistics()

