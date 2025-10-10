"""
Hidden Cohort Effect Analyzer
Identifies students in the crucial 85-95 PSAM range who could reach 95+ with strategic intervention
"""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class HiddenCohortStudent:
    """Represents a student in the hidden cohort with improvement potential"""
    student_id: int
    student_name: str
    gender: str
    school_id: int
    calendar_year: int
    psam_score: float
    total_unit_scores: float
    unit_count: int
    course_count: int
    courses: List[str]
    improvement_potential: float
    recommended_changes: List[str]
    target_psam: float

class HiddenCohortAnalyzer:
    """Analyzes students who could reach 95+ PSAM with strategic changes"""
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        
    def analyze_hidden_cohort(self, 
                            school_id: Optional[int] = None,
                            min_psam: float = 85.0,
                            max_psam: float = 94.9,
                            target_psam: float = 95.0,
                            year: Optional[int] = None) -> Dict:
        """
        Perform comprehensive hidden cohort analysis
        
        Args:
            school_id: Filter by specific school
            min_psam: Minimum PSAM score for cohort
            max_psam: Maximum PSAM score for cohort  
            target_psam: Target PSAM score to reach
            year: Filter by specific year
            
        Returns:
            Comprehensive analysis results
        """
        
        # Get students in the hidden cohort range
        cohort_students = self._get_cohort_students(school_id, min_psam, max_psam, year)
        
        # Analyze each student for improvement potential
        analyzed_students = []
        for student in cohort_students:
            analysis = self._analyze_student_potential(student, target_psam)
            if analysis:
                analyzed_students.append(analysis)
        
        # Generate strategic insights
        insights = self._generate_strategic_insights(analyzed_students)
        
        # Calculate aggregate impact
        aggregate_impact = self._calculate_aggregate_impact(analyzed_students)
        
        return {
            "cohort_summary": {
                "total_students": len(cohort_students),
                "students_with_potential": len(analyzed_students),
                "psam_range": f"{min_psam}-{max_psam}",
                "target_psam": target_psam,
                "school_id": school_id,
                "year": year
            },
            "students": analyzed_students,
            "strategic_insights": insights,
            "aggregate_impact": aggregate_impact
        }
    
    def _get_cohort_students(self, school_id, min_psam, max_psam, year):
        """Get students in the specified PSAM range"""
        filters = {
            "min_psam": min_psam,
            "max_psam": max_psam,
            "limit": 100  # Reasonable limit
        }
        
        if school_id:
            filters["school_id"] = school_id
        if year:
            filters["year"] = year
            
        return self.data_loader.find_students(**filters)
    
    def _analyze_student_potential(self, student, target_psam) -> Optional[HiddenCohortStudent]:
        """Analyze individual student's improvement potential"""
        
        # Get student's current courses
        courses = self._get_student_courses(student["student_id"])
        
        # Calculate improvement potential based on common scenarios
        improvement_scenarios = self._calculate_improvement_scenarios(student, courses)
        
        if not improvement_scenarios:
            return None
            
        best_scenario = max(improvement_scenarios, key=lambda x: x["potential_gain"])
        
        if student["psam_score"] + best_scenario["potential_gain"] >= target_psam:
            return HiddenCohortStudent(
                student_id=student["student_id"],
                student_name=student["student_name"],
                gender=student["gender"],
                school_id=student["school_id"],
                calendar_year=student["calendar_year"],
                psam_score=student["psam_score"],
                total_unit_scores=student["total_unit_scores"],
                unit_count=student["unit_count"],
                course_count=student["course_count"],
                courses=courses,
                improvement_potential=best_scenario["potential_gain"],
                recommended_changes=best_scenario["recommendations"],
                target_psam=student["psam_score"] + best_scenario["potential_gain"]
            )
        
        return None
    
    def _get_student_courses(self, student_id):
        """Get list of courses for a specific student"""
        try:
            student_details = self.data_loader.get_student(student_id)
            # Extract course names from student data
            # This would need to be implemented based on your data structure
            return student_details.get("courses", [])
        except:
            return []
    
    def _calculate_improvement_scenarios(self, student, courses):
        """Calculate potential improvement scenarios"""
        scenarios = []
        
        # Scenario 1: Mathematics pathway upgrade
        math_scenario = self._analyze_mathematics_pathway(courses)
        if math_scenario:
            scenarios.append(math_scenario)
        
        # Scenario 2: STEM subject optimization
        stem_scenario = self._analyze_stem_optimization(courses)
        if stem_scenario:
            scenarios.append(stem_scenario)
        
        # Scenario 3: Extension subject addition
        extension_scenario = self._analyze_extension_potential(courses)
        if extension_scenario:
            scenarios.append(extension_scenario)
        
        # Scenario 4: Subject combination optimization
        combination_scenario = self._analyze_subject_combinations(courses)
        if combination_scenario:
            scenarios.append(combination_scenario)
            
        return scenarios
    
    def _analyze_mathematics_pathway(self, courses):
        """Analyze mathematics pathway improvement potential"""
        current_math = self._get_highest_math_level(courses)
        
        improvements = {
            "Mathematics Standard 2": {
                "upgrade_to": "Mathematics Advanced",
                "potential_gain": 4.5,
                "description": "Upgrade from Standard to Advanced Mathematics"
            },
            "Mathematics Advanced": {
                "upgrade_to": "Mathematics Extension 1",
                "potential_gain": 6.2,
                "description": "Add Mathematics Extension 1"
            },
            "Mathematics Extension 1": {
                "upgrade_to": "Mathematics Extension 2", 
                "potential_gain": 8.1,
                "description": "Add Mathematics Extension 2"
            }
        }
        
        if current_math in improvements:
            scenario = improvements[current_math]
            return {
                "type": "mathematics_pathway",
                "potential_gain": scenario["potential_gain"],
                "recommendations": [scenario["description"]],
                "current": current_math,
                "proposed": scenario["upgrade_to"]
            }
        
        return None
    
    def _analyze_stem_optimization(self, courses):
        """Analyze STEM subject optimization potential"""
        current_stem = [c for c in courses if c in ["Physics", "Chemistry", "Biology"]]
        
        # High-scaling STEM combinations
        optimal_combinations = [
            (["Physics", "Chemistry"], 5.2, "Add Physics+Chemistry combination"),
            (["Physics", "Mathematics Extension 1"], 7.1, "Add Physics with Maths Extension"),
            (["Chemistry", "Biology"], 3.8, "Optimize Chemistry+Biology combination")
        ]
        
        for combination, gain, description in optimal_combinations:
            if not all(subject in current_stem for subject in combination):
                missing = [s for s in combination if s not in current_stem]
                if len(missing) <= 1:  # Only suggest if missing 1 or fewer subjects
                    return {
                        "type": "stem_optimization",
                        "potential_gain": gain,
                        "recommendations": [description],
                        "missing_subjects": missing
                    }
        
        return None
    
    def _analyze_extension_potential(self, courses):
        """Analyze potential for extension subjects"""
        extensions = ["English Extension 1", "English Extension 2", "History Extension"]
        current_extensions = [c for c in courses if "Extension" in c]
        
        if len(current_extensions) < 2:  # Room for more extensions
            return {
                "type": "extension_subjects",
                "potential_gain": 4.8,
                "recommendations": ["Consider adding English Extension or other extension subjects"],
                "current_extensions": len(current_extensions)
            }
        
        return None
    
    def _analyze_subject_combinations(self, courses):
        """Analyze overall subject combination optimization"""
        # This is a simplified version - could be much more sophisticated
        high_scaling_subjects = [
            "Mathematics Extension 2", "Mathematics Extension 1", "Physics", 
            "Chemistry", "English Extension 1", "English Extension 2"
        ]
        
        current_high_scaling = len([c for c in courses if c in high_scaling_subjects])
        
        if current_high_scaling < 4:  # Could add more high-scaling subjects
            return {
                "type": "subject_combination",
                "potential_gain": 3.2,
                "recommendations": ["Optimize subject combination with more high-scaling subjects"],
                "current_high_scaling": current_high_scaling
            }
        
        return None
    
    def _get_highest_math_level(self, courses):
        """Determine the highest mathematics level a student is taking"""
        math_hierarchy = [
            "Mathematics Extension 2",
            "Mathematics Extension 1", 
            "Mathematics Advanced",
            "Mathematics Standard 2",
            "Mathematics Standard 1"
        ]
        
        for math_level in math_hierarchy:
            if math_level in courses:
                return math_level
        
        return "No Mathematics"
    
    def _generate_strategic_insights(self, analyzed_students):
        """Generate strategic insights from the analyzed cohort"""
        if not analyzed_students:
            return {}
        
        # Common improvement patterns
        improvement_types = {}
        for student in analyzed_students:
            for rec in student.recommended_changes:
                improvement_types[rec] = improvement_types.get(rec, 0) + 1
        
        # Gender patterns
        gender_analysis = {"M": 0, "F": 0}
        for student in analyzed_students:
            gender_analysis[student.gender] += 1
        
        # Average improvement potential
        avg_improvement = sum(s.improvement_potential for s in analyzed_students) / len(analyzed_students)
        
        return {
            "most_common_improvements": sorted(improvement_types.items(), key=lambda x: x[1], reverse=True)[:5],
            "gender_distribution": gender_analysis,
            "average_improvement_potential": round(avg_improvement, 2),
            "total_potential_psam_gain": round(sum(s.improvement_potential for s in analyzed_students), 1)
        }
    
    def _calculate_aggregate_impact(self, analyzed_students):
        """Calculate the aggregate impact of implementing recommendations"""
        total_students = len(analyzed_students)
        total_psam_gain = sum(s.improvement_potential for s in analyzed_students)
        
        # Estimate students who would reach 95+
        students_reaching_95 = len([s for s in analyzed_students if s.target_psam >= 95.0])
        
        # Estimate school rank improvement (simplified)
        estimated_rank_improvement = total_psam_gain * 0.1  # Rough estimate
        
        return {
            "total_students_with_potential": total_students,
            "total_psam_points_possible": round(total_psam_gain, 1),
            "students_could_reach_95_plus": students_reaching_95,
            "percentage_of_cohort": round((students_reaching_95 / total_students * 100) if total_students > 0 else 0, 1),
            "estimated_school_rank_improvement": round(estimated_rank_improvement, 1)
        }

# Usage example:
def analyze_school_hidden_cohort(data_loader, school_id=99999, year=2023):
    """Convenience function to analyze hidden cohort for a specific school"""
    analyzer = HiddenCohortAnalyzer(data_loader)
    return analyzer.analyze_hidden_cohort(
        school_id=school_id,
        min_psam=85.0,
        max_psam=94.9,
        target_psam=95.0,
        year=year
    )
