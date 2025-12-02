"""
Generate accurate school analysis report V3
New features:
1. Clearer courses of concern descriptions
2. YoY change and difference to school mean
3. ASCII scatter plot (scaled mark vs ATAR)
4. Class-level analysis
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from analyze_accurate_v3 import analyze_school

def generate_markdown_report(school_analysis, school_name, output_path):
    """
    Generate markdown report with all V2 corrections
    """
    md = []

    # Header
    md.append(f"# {school_name} - School Analysis {school_analysis['year']}")
    md.append(f"")
    md.append(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y')}")
    md.append(f"**Analysis Year:** {school_analysis['year']}")
    md.append(f"")
    md.append("---")
    md.append("")

    # === SCHOOL-LEVEL: GENERALIZED INSIGHTS ===
    gen = school_analysis['school_generalized']
    md.append("## School Overview - Generalized Insights")
    md.append("")
    md.append(f"**Student Population:** {gen['total_students']} students")
    md.append(f"**Average ATAR:** {gen['avg_atar']:.2f}")
    md.append(f"**ATAR Range:** {gen['min_atar']:.1f} - {gen['max_atar']:.1f}")
    md.append(f"**Total Courses:** {gen['total_courses']}")
    md.append("")
    md.append(f"**Courses Requiring Attention:** {gen['courses_of_concern_count']} out of {gen['total_courses']} courses show concerning patterns")
    md.append("")
    md.append("---")
    md.append("")

    # === SCHOOL-LEVEL: DEEPER ANALYSIS ===
    deep = school_analysis['school_deeper']
    if deep['courses_of_concern']:
        md.append("## School Overview - Deeper Analysis")
        md.append("")
        md.append("### Courses of Concern")
        md.append("")
        for course_concern in deep['courses_of_concern'][:10]:
            md.append(f"**{course_concern['course']}** ({course_concern['cohort_size']} students)")
            for concern in course_concern['concerns']:
                md.append(f"- {concern}")
            # Add YoY change and diff to school mean
            if course_concern.get('yoy_change'):
                yoy = course_concern['yoy_change']
                direction = "↑" if yoy['scaled_change'] > 0 else "↓"
                md.append(f"- YoY change: {direction} {abs(yoy['scaled_change']):.2f} scaled marks")
            if course_concern.get('diff_to_school_mean') is not None:
                diff = course_concern['diff_to_school_mean']
                comparison = "above" if diff > 0 else "below"
                md.append(f"- School comparison: {abs(diff):.1f} marks {comparison} school mean")
            md.append("")
        md.append("---")
        md.append("")

    # === SEPARATE COURSES INTO CONCERNS AND SUCCESSES ===
    courses_of_concern = []
    successful_courses = []

    for course_analysis in school_analysis['course_analyses']:
        gen = course_analysis['generalized']
        is_concern = False

        if gen['mxp_below_pct'] > 50:
            is_concern = True
        if abs(gen['moderated_exam_gap']) > 8:
            is_concern = True
        if gen['significant_rank_changes_count'] > gen['cohort_size'] * 0.3:
            is_concern = True

        if is_concern:
            courses_of_concern.append(course_analysis)
        else:
            successful_courses.append(course_analysis)

    # === PART 1: COURSES OF CONCERN ===
    md.append("## Courses Requiring Attention")
    md.append("")
    md.append(f"**{len(courses_of_concern)} courses** show concerning patterns and require intervention.")
    md.append("")
    md.append("---")
    md.append("")

    for course_analysis in courses_of_concern:
        course_name = course_analysis['course_name']
        gen = course_analysis['generalized']
        deep = course_analysis['deeper']
        multi = course_analysis['multiyear']

        md.append(f"### {course_name}")
        md.append("")

        # GENERALIZED INSIGHTS
        md.append("**Generalized Insights:**")
        md.append("")
        md.append(f"- **Cohort Size:** {gen['cohort_size']} students")
        md.append(f"- **Average Student ATAR:** {gen['avg_atar']:.1f}")
        md.append("")

        # Moderated vs External (CORRECTED)
        gap_direction = "over-moderated" if gen['moderated_exam_gap'] > 0 else "under-moderated"
        gap_severity = "significantly" if abs(gen['moderated_exam_gap']) > 8 else "moderately" if abs(gen['moderated_exam_gap']) > 4 else "slightly"
        md.append(f"- **Moderated vs External Exam:** State-moderated internal (avg {gen['avg_moderated']:.1f}) vs external exam (avg {gen['avg_exam']:.1f}) - students were {gap_severity} {gap_direction} by {abs(gen['moderated_exam_gap']):.1f} points")
        md.append("")

        # Rank changes
        if gen['significant_rank_changes_count'] > 0:
            md.append(f"- **Rank Order Changes:** {gen['significant_rank_changes_count']} students had significant rank changes (3+ positions) between moderated and external assessments")
            md.append("")

        # Bands
        if gen['band_counts']:
            band_str = ", ".join([f"{band}: {count}" for band, count in sorted(gen['band_counts'].items())])
            md.append(f"- **Band Distribution:** {band_str}")
            md.append("")

        # MXP Performance (WITH AVERAGES)
        md.append(f"- **Performance vs Expectations (MXP):**")
        md.append(f"  - Average gap: {gen['mxp_avg_gap']:+.2f} (median: {gen['mxp_median_gap']:+.2f})")
        md.append(f"  - Exceeded expectations: {gen['mxp_exceeded_pct']:.0f}%")
        md.append(f"  - Met expectations: {gen['mxp_on_target_pct']:.0f}%")
        md.append(f"  - Below expectations: {gen['mxp_below_pct']:.0f}%")
        md.append("")

        # MULTI-YEAR TRENDS
        if multi['yoy_change']:
            yoy = multi['yoy_change']
            direction = "improved" if yoy['scaled_change'] > 0 else "declined"
            md.append(f"- **Year-over-Year:** Scaled mark {direction} by {abs(yoy['scaled_change']):.2f} points ({yoy['from_year']} → {yoy['to_year']})")
            md.append("")

        if len(multi['historical_scaled']) > 1:
            trend_str = " → ".join([f"{h['year']}:{h['avg_scaled']:.1f}" for h in multi['historical_scaled']])
            md.append(f"- **5-Year Scaled Mark Trend:** {trend_str}")
            md.append("")

        if len(multi['historical_mxp']) > 1:
            mxp_trend_str = " → ".join([f"{h['year']}:{h['avg_mxp_gap']:+.1f}" for h in multi['historical_mxp']])
            md.append(f"- **5-Year MXP Trend:** {mxp_trend_str}")
            md.append("")

        # ASCII SCATTER PLOT
        if course_analysis.get('visualization') and course_analysis['visualization'].get('ascii_scatter'):
            md.append("**Visual Analysis:**")
            md.append("")
            md.append("```")
            md.append(course_analysis['visualization']['ascii_scatter'])
            md.append("```")
            md.append("")

        # CLASS-LEVEL ANALYSIS
        if course_analysis.get('class_analysis') and len(course_analysis['class_analysis']) > 0:
            classes = course_analysis['class_analysis']
            md.append("**Class Performance:**")
            md.append("")
            md.append(f"- **{len(classes)} classes** in this course")

            # Top 3 performing classes
            top_classes = classes[:min(3, len(classes))]
            if top_classes:
                md.append(f"- *Top performing classes:*")
                for cls in top_classes:
                    teacher = cls['teacher_name'] if cls['teacher_name'] != 'Unknown' else 'Teacher unknown'
                    md.append(f"  - {cls['class_name']} ({teacher}): Avg scaled {cls['avg_scaled']:.1f}, MXP gap {cls['avg_mxp_gap']:+.1f}")

            # Bottom 3 classes if there are concerns
            if len(classes) >= 3:
                bottom_classes = classes[-min(3, len(classes)):]
                if bottom_classes and any(cls['avg_mxp_gap'] < -2 for cls in bottom_classes):
                    md.append(f"- *Classes needing support:*")
                    for cls in reversed(bottom_classes):
                        if cls['avg_mxp_gap'] < -2:
                            teacher = cls['teacher_name'] if cls['teacher_name'] != 'Unknown' else 'Teacher unknown'
                            md.append(f"  - {cls['class_name']} ({teacher}): Avg scaled {cls['avg_scaled']:.1f}, MXP gap {cls['avg_mxp_gap']:+.1f}")
            md.append("")

        # DEEPER ANALYSIS
        md.append("**Deeper Analysis:**")
        md.append("")

        # Top performers (ATAR + Scaled + Rank, NO HSC)
        if deep['top_3']:
            md.append("*Top Performers:*")
            for i, student in enumerate(deep['top_3'], 1):
                scaled = student['actual_scaled'] if student['actual_scaled'] else 0
                md.append(f"{i}. Student {student['student_id']}: ATAR {student['atar']:.1f}, Scaled {scaled:.1f}, Rank {student['rank']}")
            md.append("")

        # Bottom performers
        if deep['bottom_3']:
            md.append("*Students Requiring Support:*")
            for student in reversed(deep['bottom_3']):
                scaled = student['actual_scaled'] if student['actual_scaled'] else 0
                md.append(f"- Student {student['student_id']}: ATAR {student['atar']:.1f}, Scaled {scaled:.1f}, Rank {student['rank']}")
            md.append("")

        # Significant rank changes (moderated → exam)
        if deep['significant_rank_changes']:
            md.append("*Significant Rank Changes (Moderated → External):*")
            for change in deep['significant_rank_changes'][:5]:
                direction = "improved" if change['rank_change'] > 0 else "dropped"
                md.append(f"- Student {change['student_id']}: {direction} {abs(change['rank_change'])} positions (rank {change['mod_rank']} → {change['exam_rank']})")
            md.append("")

        # MXP underperformers
        if deep['mxp_underperformers']:
            md.append("*Significantly Below Expectations (MXP):*")
            for underperf in deep['mxp_underperformers'][:5]:
                md.append(f"- Student {underperf['student_id']}: Scored {underperf['actual']:.1f} vs expected {underperf['expected']:.1f} (gap: {underperf['gap']:.1f})")
            md.append("")

        md.append("---")
        md.append("")

    # === PART 2: SUCCESSFUL COURSES ===
    md.append("## Successful Courses")
    md.append("")
    md.append(f"**{len(successful_courses)} courses** are performing well with positive results.")
    md.append("")
    md.append("---")
    md.append("")

    for course_analysis in successful_courses:
        course_name = course_analysis['course_name']
        gen = course_analysis['generalized']
        deep = course_analysis['deeper']
        multi = course_analysis['multiyear']

        md.append(f"### {course_name}")
        md.append("")

        # GENERALIZED INSIGHTS
        md.append("**Generalized Insights:**")
        md.append("")
        md.append(f"- **Cohort Size:** {gen['cohort_size']} students")
        md.append(f"- **Average Student ATAR:** {gen['avg_atar']:.1f}")
        md.append("")

        # Moderated vs External
        gap_direction = "over-moderated" if gen['moderated_exam_gap'] > 0 else "under-moderated"
        gap_severity = "significantly" if abs(gen['moderated_exam_gap']) > 8 else "moderately" if abs(gen['moderated_exam_gap']) > 4 else "slightly"
        md.append(f"- **Moderated vs External Exam:** State-moderated internal (avg {gen['avg_moderated']:.1f}) vs external exam (avg {gen['avg_exam']:.1f}) - students were {gap_severity} {gap_direction} by {abs(gen['moderated_exam_gap']):.1f} points")
        md.append("")

        # Bands
        if gen['band_counts']:
            band_str = ", ".join([f"{band}: {count}" for band, count in sorted(gen['band_counts'].items())])
            md.append(f"- **Band Distribution:** {band_str}")
            md.append("")

        # MXP Performance
        md.append(f"- **Performance vs Expectations (MXP):**")
        md.append(f"  - Average gap: {gen['mxp_avg_gap']:+.2f} (median: {gen['mxp_median_gap']:+.2f})")
        md.append(f"  - Exceeded: {gen['mxp_exceeded_pct']:.0f}%, Met: {gen['mxp_on_target_pct']:.0f}%, Below: {gen['mxp_below_pct']:.0f}%")
        md.append("")

        # MULTI-YEAR TRENDS
        if multi['yoy_change']:
            yoy = multi['yoy_change']
            direction = "improved" if yoy['scaled_change'] > 0 else "declined"
            md.append(f"- **Year-over-Year:** Scaled mark {direction} by {abs(yoy['scaled_change']):.2f} points ({yoy['from_year']} → {yoy['to_year']})")
            md.append("")

        if len(multi['historical_scaled']) > 1:
            trend_str = " → ".join([f"{h['year']}:{h['avg_scaled']:.1f}" for h in multi['historical_scaled']])
            md.append(f"- **5-Year Trend:** {trend_str}")
            md.append("")

        # ASCII SCATTER PLOT
        if course_analysis.get('visualization') and course_analysis['visualization'].get('ascii_scatter'):
            md.append("**Visual Analysis:**")
            md.append("")
            md.append("```")
            md.append(course_analysis['visualization']['ascii_scatter'])
            md.append("```")
            md.append("")

        # CLASS-LEVEL ANALYSIS (positive tone for successful courses)
        if course_analysis.get('class_analysis') and len(course_analysis['class_analysis']) > 0:
            classes = course_analysis['class_analysis']
            md.append("**Class Performance:**")
            md.append("")
            md.append(f"- **{len(classes)} classes** in this course")

            # Top 3 performing classes
            top_classes = classes[:min(3, len(classes))]
            if top_classes:
                md.append(f"- *Excellent class performance:*")
                for cls in top_classes:
                    teacher = cls['teacher_name'] if cls['teacher_name'] != 'Unknown' else 'Teacher unknown'
                    md.append(f"  - {cls['class_name']} ({teacher}): Avg scaled {cls['avg_scaled']:.1f}, MXP gap {cls['avg_mxp_gap']:+.1f}")
            md.append("")

        # HIGHLIGHTS
        md.append("**Highlights:**")
        md.append("")

        # Top performers
        if deep['top_3']:
            md.append("*Top Performers:*")
            for i, student in enumerate(deep['top_3'], 1):
                scaled = student['actual_scaled'] if student['actual_scaled'] else 0
                md.append(f"{i}. Student {student['student_id']}: ATAR {student['atar']:.1f}, Scaled {scaled:.1f}, Rank {student['rank']}")
            md.append("")

        md.append("---")
        md.append("")

    # Write to file
    output_path.write_text('\n'.join(md), encoding='utf-8')
    return str(output_path)

if __name__ == "__main__":
    print("Generating accurate report V3...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")

    # Analyze school
    school_analysis = analyze_school(conn, 2024)

    # Generate report
    output_path = BASE_DIR / "abbotsleigh_2024_accurate_v3.md"
    report_path = generate_markdown_report(school_analysis, "Abbotsleigh", output_path)

    print(f"Report generated: {report_path}")
    print(f"\nQuick stats:")
    print(f"  Total courses: {school_analysis['school_generalized']['total_courses']}")
    print(f"  Courses of concern: {school_analysis['school_generalized']['courses_of_concern_count']}")

    conn.close()
