#!/usr/bin/env python3

from datetime import datetime

def display_grades(courses):
    """
    Display formatted grades for courses.
    
    Args:
        courses: List of Course objects with grade information
    """
    if not courses:
        print("No course data available.")
        return
    
    print("\n===== GRADE SUMMARY =====")
    
    for course in courses:
        print(f"\nCOURSE: {course.name}")
        print(f"Overall Grade: {course.calculate_grade():.1f}%")
        print("-" * 60)
        print(f"{'ASSIGNMENT':<30} {'SCORE':<10} {'POSSIBLE':<10} {'STATUS':<10}")
        print("-" * 60)
        
        # Sort assignments by due date, with None dates last
        sorted_assignments = sorted(
            course.assignments,
            key=lambda a: (a.due_date is None, a.due_date)
        )
        
        for assignment in sorted_assignments:
            score_display = f"{assignment.score}" if assignment.score is not None else "N/A"
            
            # Determine status
            status = ""
            if assignment.missing:
                status = "MISSING"
            elif not assignment.submitted and assignment.due_date and assignment.due_date < datetime.now():
                status = "LATE"
            elif assignment.submitted:
                status = "SUBMITTED"
            
            print(f"{assignment.name[:30]:<30} {score_display:<10} {assignment.points_possible:<10} {status:<10}")
        
        print("-" * 60)
        print(f"TOTAL: {course.total_score:.1f}/{course.total_possible:.1f}")
    
    print("\n=========================") 