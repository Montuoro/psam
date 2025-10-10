"""
Pydantic data models for NSW school assessment data.

This module defines type-safe models for schools, HSC students, HSC courses,
IB students, and IB subjects with component breakdowns.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class HSCCourse(BaseModel):
    """Individual HSC course with assessment details."""
    
    id: int
    school_id: int = Field(alias='schoolId')
    calendar_year: int = Field(alias='calendarYear')
    study_year: int = Field(alias='studyYear')
    student_id: int = Field(alias='studentId')
    course_id: int = Field(alias='courseId')
    course_name: str = Field(alias='courseName')
    cat: Optional[str] = None
    course_units: int = Field(alias='courseUnits')
    course_school_id: int = Field(alias='courseSchoolId')
    school_assessment: Optional[float] = Field(None, alias='schoolAssessment')
    moderated_assessment: Optional[float] = Field(None, alias='moderatedAssessment')
    scaled_exam_mark: Optional[float] = Field(None, alias='scaledExamMark')
    combined_mark: Optional[float] = Field(None, alias='combinedMark')
    band: Optional[str] = None
    convert_to_base: Optional[int] = Field(None, alias='convertToBase')
    unit_score: Optional[float] = Field(None, alias='unitScore')
    unit_count: Optional[int] = Field(None, alias='unitCount')
    map_score: Optional[float] = Field(None, alias='mapScore')
    is_ext: bool = Field(alias='isExt')
    student_name: str = Field(alias='studentName')
    gender: str
    award: Optional[str] = None
    psam_score: Optional[float] = Field(None, alias='psamScore')
    atar: Optional[float] = None
    scaled_score: Optional[float] = Field(None, alias='scaledScore')
    rank: Optional[int] = None
    status: Optional[int] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class HSCStudent(BaseModel):
    """HSC student with courses and results."""
    
    student_id: int = Field(alias='studentId')
    student_code: Optional[str] = Field(None, alias='studentCode')
    student_name: str = Field(alias='studentName')
    gender: str
    total_unit_scores: Optional[float] = Field(None, alias='totalUnitScores')
    psam_score: Optional[float] = Field(None, alias='psamScore')
    map_score: Optional[float] = Field(None, alias='mapScore')
    unit_count: Optional[int] = Field(None, alias='unitCount')
    ext_unit_count: Optional[int] = Field(None, alias='extUnitCount')
    result_type: Optional[int] = Field(None, alias='resultType')
    student_courses: List[HSCCourse] = Field(default_factory=list, alias='studentCourses')
    
    # These will be set from parent school record
    school_id: Optional[int] = None
    calendar_year: Optional[int] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class Component(BaseModel):
    """Individual IB assessment component (paper, internal assessment, etc.)."""
    
    component_name: str = Field(alias='componentName')
    component_mark: Optional[float] = Field(None, alias='componentMark')
    component_grade: Optional[str] = Field(None, alias='componentGrade')
    
    class Config:
        populate_by_name = True


class IBSubject(BaseModel):
    """IB diploma subject with component breakdown."""
    
    subject_id: int = Field(alias='subjectId')
    subject_name: str = Field(alias='subjectName')
    level: str  # HL or SL
    predicted_grade: Optional[int] = Field(None, alias='predictedGrade')
    final_grade: Optional[int] = Field(None, alias='finalGrade')
    components: List[Component] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class IBStudent(BaseModel):
    """IB diploma student with subjects and results."""
    
    student_id: int = Field(alias='studentId')
    student_code: Optional[str] = Field(None, alias='studentCode')
    student_name: str = Field(alias='studentName')
    gender: str
    total_points: Optional[int] = Field(None, alias='totalPoints')
    diploma_awarded: Optional[bool] = Field(None, alias='diplomaAwarded')
    subjects: List[IBSubject] = Field(default_factory=list)
    
    # These will be set from parent school record
    school_id: Optional[int] = None
    calendar_year: Optional[int] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class School(BaseModel):
    """Top-level school record with students and metadata."""
    
    school_id: int = Field(alias='schoolId')
    calendar_year: int = Field(alias='calendarYear')
    has_aas_results: bool = Field(alias='hasAasResults')
    student_details: List[HSCStudent] = Field(default_factory=list, alias='studentDetails')
    ib_student_details: List[IBStudent] = Field(default_factory=list, alias='ibStudentDetails')
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

