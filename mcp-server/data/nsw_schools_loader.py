"""
Data loader for NSW school assessment data.

This module parses large JSON files and builds optimized in-memory indices
for O(1) lookups and efficient filtering operations.
"""

import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path

from .nsw_schools import School, HSCStudent, HSCCourse, IBStudent


class NSWSchoolDataLoader:
    """
    Loads and indexes NSW school assessment data for fast queries.

    Builds multiple index structures:
    - students_by_id: O(1) student lookup
    - schools_by_id: O(1) school lookup
    - courses_by_name: Find all courses by name
    - students_by_school: Find all students in a school
    - courses_by_student: Find all courses for a student
    """

    def __init__(self):
        self.schools: List[School] = []
        self.students_by_id: Dict[int, HSCStudent | IBStudent] = {}
        self.schools_by_id: Dict[int, School] = {}
        self.courses_by_name: Dict[str, List[HSCCourse]] = defaultdict(list)
        self.students_by_school: Dict[int, List[HSCStudent | IBStudent]] = defaultdict(list)
        self.courses_by_student: Dict[int, List[HSCCourse]] = {}

        # Additional indices for efficient filtering
        self.students_by_gender: Dict[str, List[HSCStudent | IBStudent]] = defaultdict(list)
        self.students_by_year: Dict[int, List[HSCStudent | IBStudent]] = defaultdict(list)

        # Metadata
        self.load_time: Optional[float] = None
        self.total_students: int = 0
        self.total_courses: int = 0
        self.total_schools: int = 0

    def load_from_file(self, file_path: str | Path) -> Tuple[float, Dict[str, int]]:
        """
        Load and index data from JSON file.

        Args:
            file_path: Path to JSON file containing school data

        Returns:
            Tuple of (load_time_seconds, statistics_dict)
        """
        start_time = time.time()
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        print(f"Loading data from {file_path}...", file=sys.stderr)

        # Load JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        print(f"Parsed JSON in {time.time() - start_time:.2f}s", file=sys.stderr)

        # Parse and index schools
        parse_start = time.time()
        for school_data in raw_data:
            school = School(**school_data)
            self.schools.append(school)
            self.schools_by_id[school.school_id] = school
            self.total_schools += 1

            # Index HSC students
            for student in school.student_details:
                # Set school context
                student.school_id = school.school_id
                student.calendar_year = school.calendar_year

                # Add to indices
                self.students_by_id[student.student_id] = student
                self.students_by_school[school.school_id].append(student)
                self.students_by_gender[student.gender].append(student)
                self.students_by_year[school.calendar_year].append(student)
                self.total_students += 1

                # Index courses
                student_courses = []
                for course in student.student_courses:
                    self.courses_by_name[course.course_name].append(course)
                    student_courses.append(course)
                    self.total_courses += 1

                self.courses_by_student[student.student_id] = student_courses

            # Index IB students
            for student in school.ib_student_details:
                # Set school context
                student.school_id = school.school_id
                student.calendar_year = school.calendar_year

                # Add to indices
                self.students_by_id[student.student_id] = student
                self.students_by_school[school.school_id].append(student)
                self.students_by_gender[student.gender].append(student)
                self.students_by_year[school.calendar_year].append(student)
                self.total_students += 1

        self.load_time = time.time() - start_time

        print(f"Indexed {self.total_schools} schools, {self.total_students} students, "
              f"{self.total_courses} courses in {self.load_time:.2f}s", file=sys.stderr)

        stats = {
            'schools': self.total_schools,
            'students': self.total_students,
            'courses': self.total_courses,
            'unique_courses': len(self.courses_by_name),
            'load_time': self.load_time
        }

        return self.load_time, stats

    def get_student(self, student_id: int) -> Optional[HSCStudent | IBStudent]:
        """Get a student by ID. O(1) lookup."""
        return self.students_by_id.get(student_id)

    def get_school(self, school_id: int) -> Optional[School]:
        """Get a school by ID. O(1) lookup."""
        return self.schools_by_id.get(school_id)

    def get_courses_by_name(self, course_name: str) -> List[HSCCourse]:
        """Get all courses with a specific name. O(1) lookup."""
        return self.courses_by_name.get(course_name, [])

    def get_students_by_school(self, school_id: int) -> List[HSCStudent | IBStudent]:
        """Get all students in a school. O(1) lookup."""
        return self.students_by_school.get(school_id, [])

    def get_courses_by_student(self, student_id: int) -> List[HSCCourse]:
        """Get all courses for a student. O(1) lookup."""
        return self.courses_by_student.get(student_id, [])

    def get_all_course_names(self) -> List[str]:
        """Get list of all unique course names."""
        return sorted(self.courses_by_name.keys())

    def get_students_by_gender(self, gender: str) -> List[HSCStudent | IBStudent]:
        """Get all students of a specific gender. O(1) lookup."""
        return self.students_by_gender.get(gender, [])

    def get_students_by_year(self, year: int) -> List[HSCStudent | IBStudent]:
        """Get all students from a specific calendar year. O(1) lookup."""
        return self.students_by_year.get(year, [])

    def get_statistics(self) -> Dict[str, any]:
        """Get summary statistics about loaded data."""
        return {
            'total_schools': self.total_schools,
            'total_students': self.total_students,
            'total_courses': self.total_courses,
            'unique_course_names': len(self.courses_by_name),
            'calendar_years': sorted(self.students_by_year.keys()),
            'genders': sorted(self.students_by_gender.keys()),
            'load_time_seconds': self.load_time,
        }