"""
Generate accurate school analysis report V3
New features:
1. Clearer courses of concern descriptions
2. YoY change and difference to school mean
3. ASCII scatter plot (scaled mark vs ATAR)
4. Class-level analysis
5. Exploratory insights (cohort-level deep analysis)
6. Custom course ordering (most to least concerning)
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from analyze_accurate_v3 import analyze_school
from analyze_exploratory import generate_exploratory_insights, create_combination_trend_ascii

def load_course_order(school_name, year):
    """
    Load custom course order from JSON file if it exists
    """
    BASE_DIR = Path(__file__).parent
    order_file = BASE_DIR / f"course_order_{school_name.lower()}_{year}.json"

    if order_file.exists():
        try:
            with open(order_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('course_order', [])
        except Exception as e:
            print(f"Warning: Could not load course order file: {e}")
            return []
    return []

def generate_markdown_report(school_analysis, school_name, output_path, conn=None, year=None):
    """
    Generate markdown report with all V3 features including exploratory insights
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
    if gen.get('ng_students_count', 0) > 0:
        md.append(f"  - *Note: {gen['ng_students_count']} students with NG (Not Given) ATAR excluded from ATAR statistics*")
    md.append(f"**Average ATAR:** {gen['avg_atar']:.2f}")
    md.append(f"**ATAR Range:** {gen['min_atar']:.1f} - {gen['max_atar']:.1f}")
    md.append(f"**Total Courses:** {gen['total_courses']}")
    md.append("")

    # Non-ATAR courses
    if gen.get('non_atar_courses'):
        md.append(f"**Courses with Non-ATAR Students:** {len(gen['non_atar_courses'])} courses")
        md.append("")
        for course_info in gen['non_atar_courses']:
            pct = course_info['ng_pct']
            md.append(f"- **{course_info['course']}**: {course_info['ng_count']}/{course_info['total_count']} students ({pct:.1f}%)")
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

            # Generate plain language explanation
            explanations = []
            for concern in course_concern['concerns']:
                if "below expected MXP" in concern:
                    explanations.append("Students are performing below their expected scaled marks (MXP), suggesting the course may not be maximizing their potential or assessment practices may need review.")
                elif "major rank changes" in concern:
                    explanations.append("A large proportion of students experienced significant rank position changes between internal and external assessments, indicating inconsistency in assessment or student preparation.")
                elif "YoY decline" in concern:
                    explanations.append("The course has shown a year-over-year decline in scaled marks, indicating a concerning downward trend that warrants investigation.")

                md.append(f"- {concern}")

            # Add comprehensive explanation
            if explanations:
                md.append("")
                md.append(f"  *Why this course is included:* {' '.join(explanations)}")
                md.append("")

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

    # === ORDER COURSES (CUSTOM ORDER OR DEFAULT) ===
    # Load custom course order if available
    custom_order = load_course_order(school_name, school_analysis['year'])

    if custom_order:
        # Order courses according to custom order
        course_order_map = {name: idx for idx, name in enumerate(custom_order)}
        ordered_courses = sorted(
            school_analysis['course_analyses'],
            key=lambda x: course_order_map.get(x['course_name'], 999)
        )
    else:
        # Default: order by concern level (most concerning first)
        def concern_score(course_analysis):
            gen = course_analysis['generalized']
            score = 0
            if gen['mxp_below_pct'] > 50:
                score += gen['mxp_below_pct']
            if abs(gen['moderated_exam_gap']) > 8:
                score += abs(gen['moderated_exam_gap']) * 5
            if gen['significant_rank_changes_count'] > gen['cohort_size'] * 0.3:
                score += 20
            return -score  # Negative for descending order

        ordered_courses = sorted(school_analysis['course_analyses'], key=concern_score)

    # === ALL COURSES (ORDERED FROM MOST TO LEAST CONCERNING) ===
    md.append("## Course Analysis (Ordered by Priority)")
    md.append("")
    if custom_order:
        md.append("*Courses ordered from most to least concerning based on provided priority list.*")
    else:
        md.append("*Courses automatically ordered from most to least concerning.*")
    md.append("")
    md.append("---")
    md.append("")

    for course_analysis in ordered_courses:
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

        # Internal vs External - ASSESSMENT QUALITY METRIC (not student performance)
        gap_direction = "higher" if gen['internal_exam_gap'] > 0 else "lower"
        gap_severity = "significantly" if abs(gen['internal_exam_gap']) > 8 else "moderately" if abs(gen['internal_exam_gap']) > 4 else "slightly"
        md.append(f"- **Internal vs External Assessment (Assessment Quality):** School internal assessment (avg {gen['avg_internal']:.1f}) vs external exam (avg {gen['avg_exam']:.1f}) - internal marks were {gap_severity} {gap_direction} by {abs(gen['internal_exam_gap']):.1f} points")
        md.append(f"  - *Note: This reflects marking calibration, not student performance*")
        md.append("")

        # Rank changes
        if gen['significant_rank_changes_count'] > 0:
            md.append(f"- **Rank Order Changes:** {gen['significant_rank_changes_count']} students had significant rank changes (3+ positions) between internal and external assessments (mean change: {gen['mean_rank_change']:.1f} positions)")
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

        # Identity Line Breakdown
        if gen.get('above_identity') is not None:
            md.append(f"- **Identity Line Breakdown (Actual vs Expected):**")
            md.append(f"  - Above identity line: {gen['above_identity']} students ({gen['above_identity_pct']:.1f}%)")
            md.append(f"  - On identity line: {gen['on_identity']} students ({gen['on_identity_pct']:.1f}%)")
            md.append(f"  - Below identity line: {gen['below_identity']} students ({gen['below_identity_pct']:.1f}%)")
            md.append("")

        # MULTI-YEAR TRENDS
        if multi['yoy_change']:
            yoy = multi['yoy_change']
            direction = "improved" if yoy['scaled_change'] > 0 else "declined"
            md.append(f"- **Year-over-Year:** Scaled mark {direction} by {abs(yoy['scaled_change']):.2f} points ({yoy['from_year']} → {yoy['to_year']})")
            md.append("")

        # 5-YEAR Z-SCORE TREND
        if multi.get('z_scores') and len(multi['z_scores']) > 0:
            z_trend_str = []
            for z_data in multi['z_scores']:
                sign = "+" if z_data['z_score'] > 0 else ""
                z_trend_str.append(f"{z_data['year']}:{sign}{z_data['z_score']:.2f}")
            md.append(f"- **5-Year Z-Score Trend:** {' | '.join(z_trend_str)}")
            md.append("")
            # Add interpretation
            if len(multi['z_scores']) >= 2:
                recent_z = multi['z_scores'][-1]['z_score']
                if recent_z > 0.5:
                    md.append(f"  *The course is performing above the school average (z={recent_z:.2f}).*")
                elif recent_z < -0.5:
                    md.append(f"  *The course is performing below the school average (z={recent_z:.2f}).*")
                else:
                    md.append(f"  *The course is performing near the school average (z={recent_z:.2f}).*")
            md.append("")

        # RANK TO SCALED MARK CORRELATION TEST
        if multi.get('rank_correlation_test'):
            rct = multi['rank_correlation_test']
            md.append(f"- **Rank to AAS Scaled Mark - Statistical Testing:**")
            md.append(f"  - {rct['recent_year']}: r={rct['recent_corr']:.3f}")
            md.append(f"  - {rct['second_year']}: r={rct['second_corr']:.3f}")
            md.append(f"  - {rct['third_year']}: r={rct['third_corr']:.3f}")
            md.append("")

            # Report significance
            if rct['vs_2nd_significant'] or rct['vs_3rd_significant']:
                md.append(f"  *Statistically significant difference detected:*")
                if rct['vs_2nd_significant']:
                    diff = rct['recent_corr'] - rct['second_corr']
                    direction = "stronger" if diff > 0 else "weaker"
                    md.append(f"  - {rct['recent_year']} vs {rct['second_year']}: {direction} correlation (p={rct['vs_2nd_p_value']:.4f})")
                if rct['vs_3rd_significant']:
                    diff = rct['recent_corr'] - rct['third_corr']
                    direction = "stronger" if diff > 0 else "weaker"
                    md.append(f"  - {rct['recent_year']} vs {rct['third_year']}: {direction} correlation (p={rct['vs_3rd_p_value']:.4f})")
            else:
                md.append(f"  *No statistically significant difference in rank-to-scaled-mark correlation across years (null hypothesis retained).*")
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

        # RANK ORDER HISTOGRAM
        if course_analysis.get('visualization') and course_analysis['visualization'].get('rank_order_scatter'):
            md.append("**Rank Order Changes Distribution:**")
            md.append("")
            md.append("```")
            md.append(course_analysis['visualization']['rank_order_scatter'])
            md.append("```")
            md.append("")

        # CLASS-LEVEL ANALYSIS
        if course_analysis.get('class_analysis') and len(course_analysis['class_analysis']) > 0:
            classes = course_analysis['class_analysis']
            md.append("**Class Performance:**")
            md.append("")
            md.append(f"- **{len(classes)} classes** in this course")

            # Categorize by MXP gap
            high_performing = [cls for cls in classes if cls['avg_mxp_gap'] > 0]
            low_performing = [cls for cls in classes if cls['avg_mxp_gap'] < 0]
            on_target = [cls for cls in classes if cls['avg_mxp_gap'] == 0]

            # High-performing classes (above expected mean)
            if high_performing:
                md.append(f"- *High-performing classes (above expected mean):*")
                # Sort by gap descending, show top 5
                for cls in sorted(high_performing, key=lambda x: x['avg_mxp_gap'], reverse=True)[:5]:
                    teacher = cls['teacher_name'] if cls['teacher_name'] != 'Unknown' else 'Teacher unknown'
                    md.append(f"  - {cls['class_name']} ({teacher}): Avg scaled {cls['avg_scaled']:.1f}, MXP gap {cls['avg_mxp_gap']:+.1f}")

            # Low-performing classes (below expected mean)
            if low_performing:
                md.append(f"- *Low-performing classes (below expected mean):*")
                # Sort by gap ascending (most negative first), show worst 5
                for cls in sorted(low_performing, key=lambda x: x['avg_mxp_gap'])[:5]:
                    teacher = cls['teacher_name'] if cls['teacher_name'] != 'Unknown' else 'Teacher unknown'
                    md.append(f"  - {cls['class_name']} ({teacher}): Avg scaled {cls['avg_scaled']:.1f}, MXP gap {cls['avg_mxp_gap']:+.1f}")

            md.append("")

        # DEEPER ANALYSIS
        md.append("**Deeper Analysis:**")
        md.append("")

        # High performers (Band 6 or top 10%)
        if deep.get('high_performers'):
            md.append(f"*High Performers ({len(deep['high_performers'])} students - Band 6 or top 10%):*")
            for student in deep['high_performers']:
                scaled = student['actual_scaled'] if student['actual_scaled'] else 0
                atar = student['atar'] if student['atar'] else 0
                md.append(f"- Student {student['student_id']}: ATAR {atar:.1f}, Scaled {scaled:.1f}, Rank {student['rank']}")
            md.append("")

        # Low performers (Band 1-2 or bottom 10%)
        if deep.get('low_performers'):
            md.append(f"*Students Requiring Support ({len(deep['low_performers'])} students - Band 1-2 or bottom 10%):*")
            for student in deep['low_performers']:
                scaled = student['actual_scaled'] if student['actual_scaled'] else 0
                atar = student['atar'] if student['atar'] else 0
                md.append(f"- Student {student['student_id']}: ATAR {atar:.1f}, Scaled {scaled:.1f}, Rank {student['rank']}")
            md.append("")

        # Significant rank changes (internal → exam) - ALL students with >=3 position changes
        if deep['significant_rank_changes']:
            md.append(f"*Significant Rank Changes ({len(deep['significant_rank_changes'])} students with ≥3 position changes):*")
            for change in deep['significant_rank_changes']:
                direction = "improved" if change['rank_change'] > 0 else "dropped"
                md.append(f"- Student {change['student_id']}: {direction} {abs(change['rank_change'])} positions (internal rank {change['internal_rank']} → external rank {change['exam_rank']})")
            md.append("")

        # MXP underperformers - ALL students with gap < -2
        if deep['mxp_underperformers']:
            md.append(f"*Significantly Below Expectations ({len(deep['mxp_underperformers'])} students with MXP gap < -2):*")
            for underperf in deep['mxp_underperformers']:
                md.append(f"- Student {underperf['student_id']}: Scored {underperf['actual']:.1f} vs expected {underperf['expected']:.1f} (gap: {underperf['gap']:.1f})")
            md.append("")

        md.append("---")
        md.append("")

    # === EXPLORATORY INSIGHTS ===
    # NEW ADDITION: Deep cohort-level analysis across multiple years
    if conn and year:
        md.append("## Exploratory Insights")
        md.append("")
        md.append("*This section provides deep cohort-level analysis to identify patterns, trends, and optimization opportunities that may not be immediately visible in course-level data.*")
        md.append("")
        md.append("---")
        md.append("")

        try:
            insights = generate_exploratory_insights(conn, year)

            # 1. Course Selection Optimization
            md.append("### Course Selection Optimization")
            md.append("")
            cs = insights['course_selection']
            md.append(f"**Analysis of {cs['total_students']} students** to identify potential course selection mismatches:")
            md.append("")

            if cs['mismatches']:
                md.append(f"**Found {len(cs['mismatches'])} students** with interesting patterns:")
                md.append("")
                for mismatch in cs['mismatches']:
                    md.append(f"- **Student {mismatch['student_id']}** (ATAR {mismatch['atar']:.1f}): {mismatch['issue']}")
                    if 'low_courses' in mismatch:
                        md.append(f"  - Low-scaled courses: {', '.join(mismatch['low_courses'])}")
                    if 'high_courses' in mismatch:
                        md.append(f"  - High-scaled courses: {', '.join(mismatch['high_courses'])}")
                md.append("")
            else:
                md.append("No significant course selection mismatches detected.")
                md.append("")

            md.append("---")
            md.append("")

            # 2. Extension Course Decisions
            md.append("### Extension Course Performance")
            md.append("")
            ext = insights['extensions']
            md.append(f"**{ext['total_extension_students']} students** took extension courses:")
            md.append("")

            if ext['successful_extensions']:
                md.append(f"**High-performing extension students ({len(ext['successful_extensions'])} students):**")
                md.append("")
                for student in ext['successful_extensions']:
                    md.append(f"- Student {student['student_id']} (ATAR {student['atar']:.1f}): {', '.join(student['extensions'])}")
                md.append("")

            if ext['struggling_extensions']:
                md.append(f"**Students struggling in extensions ({len(ext['struggling_extensions'])} students):**")
                md.append("")
                for student in ext['struggling_extensions']:
                    md.append(f"- Student {student['student_id']} (ATAR {student['atar']:.1f}): {', '.join(student['struggling_in'])}")
                md.append("")

            # Extension trends over 3 years
            if 'extension_trends' in insights:
                md.append("**Extension Uptake Trends (3-Year):**")
                md.append("")
                for trend in insights['extension_trends']:
                    md.append(f"**{trend['year']}:** {trend['total_with_extensions']} students ({trend['pct_with_extensions']:.1f}% of cohort)")
                    if trend['by_count']:
                        count_str = ", ".join([f"{count} ext: {num} students" for count, num in sorted(trend['by_count'].items())])
                        md.append(f"- Breakdown: {count_str}")
                md.append("")

            md.append("---")
            md.append("")

            # 3. Unit Selection Strategy
            md.append("### Unit Selection Strategy")
            md.append("")
            us = insights['unit_strategy']
            md.append(f"**{us['students_over_10']} students** took more than 10 units.")
            md.append("")

            if us['unit_performance']:
                md.append("**Average ATAR by unit count (current year):**")
                md.append("")
                for units, perf in sorted(us['unit_performance'].items()):
                    md.append(f"- **{units} units** ({perf['count']} students): Avg ATAR {perf['avg_atar']:.1f}, Median {perf['median_atar']:.1f}")
                md.append("")

            # Multi-year unit strategy with ASCII graph
            if 'unit_strategy_multiyear' in insights:
                usm = insights['unit_strategy_multiyear']
                md.append("**3-Year Unit Selection Trend:**")
                md.append("")
                md.append("```")
                md.append(usm['ascii_graph'])
                md.append("```")
                md.append("")

            md.append("---")
            md.append("")

            # 4. Multi-Year Cohort Trends
            md.append("### Multi-Year Cohort Trends")
            md.append("")
            ct = insights['cohort_trends']

            if ct['cohort_stats']:
                md.append("**Cohort statistics over time:**")
                md.append("")
                for stat in ct['cohort_stats']:
                    md.append(f"**{stat['year']}:**")
                    md.append(f"- Cohort size: {stat['cohort_size']} students")
                    md.append(f"- Average ATAR: {stat['avg_atar']:.2f}")
                    md.append(f"- ATAR range: {stat['min_atar']:.1f} - {stat['max_atar']:.1f}")
                    md.append(f"- Mean HSC mark: {stat['avg_hsc']:.1f}")
                    md.append(f"- Mean scaled mark: {stat['avg_scaled']:.1f}")
                    md.append(f"- Extension students: {stat['extension_students']} ({stat['extension_pct']:.1f}%)")
                    md.append("")

            if ct['trends']:
                md.append("**Year-over-year changes:**")
                md.append("")
                for trend in ct['trends']:
                    atar_dir = "↑" if trend['atar_change'] > 0 else "↓"
                    ext_dir = "↑" if trend['extension_pct_change'] > 0 else "↓"
                    md.append(f"**{trend['from_year']} → {trend['to_year']}:**")
                    md.append(f"- ATAR change: {atar_dir} {abs(trend['atar_change']):.2f} points")
                    md.append(f"- Extension uptake: {ext_dir} {abs(trend['extension_pct_change']):.1f}%")
                    md.append("")

            md.append("---")
            md.append("")

            # 5. Optimal Course Combinations (Pairs)
            md.append("### High-Performing Course Combinations (2-Course Pairs)")
            md.append("")
            oc = insights['optimal_combinations']

            if oc['high_performing_pairs']:
                md.append(f"**Top {len(oc['high_performing_pairs'])} course pairs** ordered by enrollment (most popular first):")
                md.append("")
                for idx, pair in enumerate(oc['high_performing_pairs'], 1):
                    md.append(f"{idx}. **{pair['courses']}**: {pair['num_students']} students (Avg ATAR {pair['avg_atar']:.1f})")
                md.append("")

                # Add 3-year ATAR trend visualization
                md.append("**3-Year ATAR Trend:**")
                md.append("")
                md.append("```")
                md.append(create_combination_trend_ascii(oc['high_performing_pairs']))
                md.append("```")
                md.append("")
            else:
                md.append("Insufficient data to identify course combination patterns.")
                md.append("")

            md.append("---")
            md.append("")

            # 6. Triple Course Combinations
            if 'triple_combinations' in insights and insights['triple_combinations']:
                md.append("### High-Performing Course Combinations (3-Course Triples)")
                md.append("")
                tc = insights['triple_combinations']
                md.append(f"**Top {len(tc)} 3-course combinations** ordered by enrollment (most popular first):")
                md.append("")
                for idx, triple in enumerate(tc, 1):
                    md.append(f"{idx}. **{triple['courses']}**: {triple['num_students']} students (Avg ATAR {triple['avg_atar']:.1f})")
                md.append("")

                # Add 3-year ATAR trend visualization
                md.append("**3-Year ATAR Trend:**")
                md.append("")
                md.append("```")
                md.append(create_combination_trend_ascii(tc))
                md.append("```")
                md.append("")

                md.append("---")
                md.append("")

            # 7. Quad Course Combinations
            if 'quad_combinations' in insights and insights['quad_combinations']:
                md.append("### High-Performing Course Combinations (4-Course Quads)")
                md.append("")
                qc = insights['quad_combinations']
                md.append(f"**Top {len(qc)} 4-course combinations** ordered by enrollment (most popular first):")
                md.append("")
                for idx, quad in enumerate(qc, 1):
                    md.append(f"{idx}. **{quad['courses']}**: {quad['num_students']} students (Avg ATAR {quad['avg_atar']:.1f})")
                md.append("")

                # Add 3-year ATAR trend visualization
                md.append("**3-Year ATAR Trend:**")
                md.append("")
                md.append("```")
                md.append(create_combination_trend_ascii(qc))
                md.append("```")
                md.append("")

                md.append("---")
                md.append("")

            # 7. Low-Performing Course Combinations (2-Course Pairs)
            if 'poor_combinations' in insights and insights['poor_combinations']:
                md.append("### Low-Performing Course Combinations (2-Course Pairs)")
                md.append("")
                pc = insights['poor_combinations']
                md.append(f"**Bottom {len(pc)} course pairs** ordered by enrollment (most common first):")
                md.append("")
                md.append("*Note: These combinations may indicate students facing challenges or require additional support.*")
                md.append("")
                for idx, pair in enumerate(pc, 1):
                    md.append(f"{idx}. **{pair['courses']}**: {pair['num_students']} students (Avg ATAR {pair['avg_atar']:.1f})")
                md.append("")

                # Add 3-year ATAR trend visualization
                md.append("**3-Year ATAR Trend:**")
                md.append("")
                md.append("```")
                md.append(create_combination_trend_ascii(pc))
                md.append("```")
                md.append("")

                md.append("---")
                md.append("")

            # 8. Low-Performing Course Combinations (3-Course Triples)
            if 'poor_triple_combinations' in insights and insights['poor_triple_combinations']:
                md.append("### Low-Performing Course Combinations (3-Course Triples)")
                md.append("")
                ptc = insights['poor_triple_combinations']
                md.append(f"**Bottom {len(ptc)} 3-course combinations** ordered by enrollment (most common first):")
                md.append("")
                md.append("*Note: These combinations may indicate students facing challenges or require additional support.*")
                md.append("")
                for idx, triple in enumerate(ptc, 1):
                    md.append(f"{idx}. **{triple['courses']}**: {triple['num_students']} students (Avg ATAR {triple['avg_atar']:.1f})")
                md.append("")

                # Add 3-year ATAR trend visualization
                md.append("**3-Year ATAR Trend:**")
                md.append("")
                md.append("```")
                md.append(create_combination_trend_ascii(ptc))
                md.append("```")
                md.append("")

                md.append("---")
                md.append("")

            # 9. Low-Performing Course Combinations (4-Course Quads)
            if 'poor_quad_combinations' in insights and insights['poor_quad_combinations']:
                md.append("### Low-Performing Course Combinations (4-Course Quads)")
                md.append("")
                pqc = insights['poor_quad_combinations']
                md.append(f"**Bottom {len(pqc)} 4-course combinations** ordered by enrollment (most common first):")
                md.append("")
                md.append("*Note: These combinations may indicate students facing challenges or require additional support.*")
                md.append("")
                for idx, quad in enumerate(pqc, 1):
                    md.append(f"{idx}. **{quad['courses']}**: {quad['num_students']} students (Avg ATAR {quad['avg_atar']:.1f})")
                md.append("")

                # Add 3-year ATAR trend visualization
                md.append("**3-Year ATAR Trend:**")
                md.append("")
                md.append("```")
                md.append(create_combination_trend_ascii(pqc))
                md.append("```")
                md.append("")

                md.append("---")
                md.append("")

            # 10. Hidden Cohorts (Multiple Types)
            if 'hidden_cohorts' in insights:
                md.append("### Hidden Cohorts - Students Who May Benefit from Different Strategies")
                md.append("")
                md.append("*Analysis of students who might achieve higher ATARs with different course selections:*")
                md.append("")

                hc = insights['hidden_cohorts']

                # Cohort 1: 80-90 ATAR with Advanced but no Extension
                if 'cohort_1' in hc:
                    md.append("#### Cohort 1: Extension Course Candidates")
                    md.append("*Students in ATAR range 80-90 taking Advanced courses but NO extensions:*")
                    md.append("")
                    for year_data in hc['cohort_1']:
                        md.append(f"**{year_data['year']}:** {year_data['count']} students identified")
                        if year_data['examples']:
                            for student in year_data['examples'][:3]:
                                md.append(f"- Student {student['student_id']} (ATAR {student['atar']:.1f}): Taking {', '.join(student['courses'])}")
                        md.append("")

                # Cohort 2: 70-80 ATAR not taking Advanced
                if 'cohort_2' in hc:
                    md.append("#### Cohort 2: Advanced Course Candidates")
                    md.append("*Students in ATAR range 70-80 NOT taking any Advanced courses:*")
                    md.append("")
                    for year_data in hc['cohort_2']:
                        md.append(f"**{year_data['year']}:** {year_data['count']} students identified")
                        if year_data['examples']:
                            for student in year_data['examples'][:3]:
                                courses_str = ', '.join(student['courses']) if student['courses'] else 'Standard courses'
                                md.append(f"- Student {student['student_id']} (ATAR {student['atar']:.1f}): Taking {courses_str}")
                        md.append("")

                # Cohort 3: 90-95 ATAR taking only 1 extension
                if 'cohort_3' in hc:
                    md.append("#### Cohort 3: Additional Extension Candidates")
                    md.append("*High-performing students (90-95 ATAR) taking only 1 extension course:*")
                    md.append("")
                    for year_data in hc['cohort_3']:
                        md.append(f"**{year_data['year']}:** {year_data['count']} students identified")
                        if year_data['examples']:
                            for student in year_data['examples'][:3]:
                                md.append(f"- Student {student['student_id']} (ATAR {student['atar']:.1f}): Taking {student['courses'][0]}")
                        md.append("")

                # Cohort 4: High ATAR (>95) taking <12 units
                if 'cohort_4' in hc:
                    md.append("#### Cohort 4: Additional Units Candidates")
                    md.append("*Top students (>95 ATAR) taking fewer than 12 units:*")
                    md.append("")
                    for year_data in hc['cohort_4']:
                        md.append(f"**{year_data['year']}:** {year_data['count']} students identified")
                        if year_data['examples']:
                            for student in year_data['examples'][:3]:
                                md.append(f"- Student {student['student_id']} (ATAR {student['atar']:.1f}): Taking only {student['units']} units")
                        md.append("")

                md.append("---")
                md.append("")

        except Exception as e:
            md.append(f"*Error generating exploratory insights: {str(e)}*")
            md.append("")

    # Write to file
    output_path.write_text('\n'.join(md), encoding='utf-8')
    return str(output_path)

if __name__ == "__main__":
    print("Generating accurate report V3 with exploratory insights...")
    BASE_DIR = Path(__file__).parent
    conn = sqlite3.connect(BASE_DIR / "capsules/output/abbotsleigh.db")

    year = 2024

    # Analyze school
    school_analysis = analyze_school(conn, year)

    # Generate report (now with exploratory insights)
    output_path = BASE_DIR / "abbotsleigh_2024_accurate_v3.md"
    report_path = generate_markdown_report(school_analysis, "Abbotsleigh", output_path, conn=conn, year=year)

    print(f"Report generated: {report_path}")
    print(f"\nQuick stats:")
    print(f"  Total courses: {school_analysis['school_generalized']['total_courses']}")
    print(f"  Courses of concern: {school_analysis['school_generalized']['courses_of_concern_count']}")

    conn.close()
