"""
Example usage of NSW School Data Library.

Demonstrates loading data and performing various queries.
"""

from data.nsw_schools_loader import NSWSchoolDataLoader
from data.nsw_schools_query import NSWSchoolQuery
import json


def main():
    # Load data
    print("=" * 60)
    print("NSW School Data Library - Example Usage")
    print("=" * 60)
    
    loader = NSWSchoolDataLoader()
    load_time, stats = loader.load_from_file('download/DemoNSWSchoolData.txt')
    
    print(f"\n✓ Data loaded in {load_time:.2f}s")
    print(f"  Schools: {stats['schools']}")
    print(f"  Students: {stats['students']}")
    print(f"  Courses: {stats['courses']}")
    print(f"  Unique course types: {stats['unique_courses']}")
    
    # Create query API
    query = NSWSchoolQuery(loader)
    
    # Example 1: Get dataset statistics
    print("\n" + "=" * 60)
    print("Example 1: Dataset Statistics")
    print("=" * 60)
    dataset_stats = query.get_query_stats()
    print(json.dumps(dataset_stats, indent=2))
    
    # Example 2: Get top performers
    print("\n" + "=" * 60)
    print("Example 2: Top 5 Performers by PSAM Score")
    print("=" * 60)
    top_students = query.get_top_performers(n=5, metric='psam_score')
    for i, student in enumerate(top_students, 1):
        print(f"{i}. {student['student_name']} - PSAM: {student['psam_score']}")
    
    # Example 3: Course popularity
    print("\n" + "=" * 60)
    print("Example 3: Top 10 Most Popular Courses")
    print("=" * 60)
    popular_courses = query.get_course_popularity(top_n=10)
    for i, course in enumerate(popular_courses, 1):
        print(f"{i}. {course['course_name']}: {course['enrollment_count']} students")
    
    # Example 4: School statistics
    print("\n" + "=" * 60)
    print("Example 4: School Statistics")
    print("=" * 60)
    school_id = list(loader.schools_by_id.keys())[0]
    school_stats = query.get_school_stats(school_id)
    print(json.dumps(school_stats, indent=2))
    
    # Example 5: Course distribution
    print("\n" + "=" * 60)
    print("Example 5: Course Distribution - English Advanced")
    print("=" * 60)
    course_dist = query.get_course_distribution('English Advanced')
    print(json.dumps(course_dist, indent=2))
    
    # Example 6: Find students with high PSAM scores
    print("\n" + "=" * 60)
    print("Example 6: Students with PSAM Score >= 95")
    print("=" * 60)
    high_achievers = query.find_students(min_psam=95.0, limit=10)
    for student in high_achievers:
        print(f"  {student['student_name']} - PSAM: {student['psam_score']} (School {student['school_id']})")
    
    # Example 7: Calculate school averages
    print("\n" + "=" * 60)
    print("Example 7: School Performance Rankings")
    print("=" * 60)
    school_averages = query.calculate_school_averages()
    for i, school in enumerate(school_averages, 1):
        print(f"{i}. School {school['school_id']}: Avg PSAM {school['average_psam']} ({school['student_count']} students)")
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()

