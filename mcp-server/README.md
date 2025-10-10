# PSAM School Data Library

A high-performance Python library for querying NSW Higher School Certificate (HSC) and International Baccalaureate (IB) assessment data. Optimized for read-only access with fast in-memory indices and comprehensive query capabilities.

## Features

- **Fast Data Loading**: Loads 473k+ lines of JSON data in under 5 seconds
- **Optimized Indices**: O(1) lookups for students, schools, and courses
- **Rich Query API**: Student searches, school statistics, course analysis, and aggregations
- **MCP Integration**: Exposes data via Model Context Protocol for AI/LLM consumption
- **Type Safety**: Full Pydantic models with validation
- **Comprehensive Tests**: 40+ test cases covering functionality and performance

## Architecture

### Data Models (`data/nsw_schools.py`)

Pydantic models for type-safe data structures:
- `School`: Top-level school record
- `HSCStudent`: HSC student with courses
- `HSCCourse`: Individual course with assessment details
- `IBStudent`: IB student with subjects
- `IBSubject`: IB subject with component breakdown

### Data Loader (`data/nsw_schools_loader.py`)

Builds optimized in-memory indices:
- `students_by_id`: O(1) student lookup
- `schools_by_id`: O(1) school lookup
- `courses_by_name`: Find courses by name
- `students_by_school`: Find students in a school
- `courses_by_student`: Find courses for a student
- Additional indices for gender, year filtering

### Query API (`data/nsw_schools_query.py`)

High-level query methods:
- **Student queries**: `get_student()`, `find_students()`, `get_student_summary()`
- **School queries**: `get_school_stats()`, `get_school_rankings()`
- **Course queries**: `get_course_distribution()`, `compare_courses()`, `get_all_courses()`
- **Aggregations**: `calculate_school_averages()`, `get_top_performers()`, `get_course_popularity()`

### MCP Server (`mcp_nsw_schools.py`)

Exposes query API via Model Context Protocol with tools:
- `get_student`: Get detailed student information
- `find_students`: Search with filters (school, gender, PSAM range, course)
- `get_school_stats`: Comprehensive school statistics
- `get_school_rankings`: Student rankings by course
- `get_course_distribution`: Course statistics and distributions
- `compare_courses`: Multi-course comparison
- `get_top_performers`: Top students by metric
- `calculate_school_averages`: School performance rankings
- And more...

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Python API

```python
from data.nsw_schools_loader import NSWSchoolDataLoader
from data.nsw_schools_query import NSWSchoolQuery

# Load data
loader = NSWSchoolDataLoader()
loader.load_from_file('download/DemoNSWSchoolData.txt')

# Create query API
query = NSWSchoolQuery(loader)

# Get a student
student = query.get_student(10000450)
print(student['student_name'], student['psam_score'])

# Find high-performing students
top_students = query.find_students(min_psam=95.0, limit=10)

# Get school statistics
school_stats = query.get_school_stats(99999)
print(f"Average PSAM: {school_stats['psam_stats']['mean']}")

# Analyze course performance
course_dist = query.get_course_distribution('English Advanced')
print(f"Students: {course_dist['count']}")
print(f"Average mark: {course_dist['mark_stats']['mean']}")

# Top performers
top_10 = query.get_top_performers(n=10, metric='psam_score')

# Course popularity
popular = query.get_course_popularity(top_n=20)
```

### MCP Server

Run as MCP server for AI/LLM integration:

```bash
python mcp_nsw_schools.py
```

The server exposes 11 tools accessible via MCP protocol.

## Running Tests

```bash
python -m pytest tests/test_nsw_schools.py -v
```

Or run directly:

```bash
python tests/test_nsw_schools.py
```

Tests cover:
- Data loading and indexing
- All query methods
- Performance benchmarks
- Edge cases and error handling

## Performance

Meets all performance targets:
- ✅ Load 473k lines in < 5 seconds
- ✅ O(1) indexed lookups
- ✅ Simple queries < 10ms
- ✅ Complex aggregations < 100ms (95th percentile)
- ✅ Memory usage < 500MB

## Data Format

Expected JSON structure:
```json
[
  {
    "schoolId": 99999,
    "calendarYear": 2023,
    "hasAasResults": false,
    "studentDetails": [
      {
        "studentId": 10000450,
        "studentName": "STUDENT Name",
        "gender": "F",
        "psamScore": 95.00,
        "totalUnitScores": 403.39,
        "studentCourses": [...]
      }
    ],
    "ibStudentDetails": [...]
  }
]
```

## Project Structure

```
jai-psam/
├── data/
│   ├── __init__.py
│   ├── nsw_schools.py          # Pydantic data models
│   ├── nsw_schools_loader.py   # Data loading and indexing
│   └── nsw_schools_query.py    # Query API
├── tests/
│   ├── __init__.py
│   └── test_nsw_schools.py     # Comprehensive test suite
├── download/
│   └── DemoNSWSchoolData.txt   # Data file
├── mcp_nsw_schools.py          # MCP server
├── requirements.txt
└── README.md
```

## Future Enhancements

See `MCP_ENHANCEMENT_PLAN.md` for a comprehensive roadmap of planned enhancements to match and exceed the PSAM Angular UI functionality. Key additions include:

- **21 new MCP tools** for advanced analytics
- Achievement recognition (honor rolls, distinguished achievers)
- Enhanced course analytics (band distributions, rankings, trends)
- Student progression tracking and comparisons
- Statistical distributions and percentiles
- Gender and cohort analysis
- Time series and trend analysis
- Value-added analysis
- IB component-level analysis

Quick overview available in `MCP_ENHANCEMENT_SUMMARY.md`.

## License

See project license.

