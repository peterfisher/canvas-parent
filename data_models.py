#!/usr/bin/env python3

from datetime import datetime

class Assignment:
    def __init__(self, name, due_date, points_possible, score, submitted, missing):
        self.name = name
        self.due_date = due_date
        self.points_possible = points_possible
        self.score = score
        self.submitted = submitted
        self.missing = missing

class Course:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.assignments = []
        self.total_score = 0
        self.total_possible = 0
        
    def calculate_grade(self):
        if self.total_possible > 0:
            return (self.total_score / self.total_possible) * 100
        return 0

def parse_grades(raw_grades):
    """
    Parse raw grade data into a structured format.
    Returns a list of Course objects with their assignments.
    """
    courses = []
    
    for course_data in raw_grades:
        course = Course(course_data['course_id'], course_data['course_name'])
        
        # Create a lookup for submissions by assignment ID
        submissions_lookup = {
            sub['assignment_id']: sub 
            for sub in course_data['submissions']
        }
        
        for assignment_data in course_data['assignments']:
            assignment_id = assignment_data['id']
            submission = submissions_lookup.get(assignment_id, {})
            
            # Parse due date
            due_date = None
            if assignment_data.get('due_at'):
                due_date = datetime.fromisoformat(assignment_data['due_at'].replace('Z', '+00:00'))
            
            # Create assignment object
            assignment = Assignment(
                name=assignment_data['name'],
                due_date=due_date,
                points_possible=assignment_data['points_possible'],
                score=submission.get('score'),
                submitted=submission.get('submitted_at') is not None,
                missing=submission.get('missing', False)
            )
            
            course.assignments.append(assignment)
            
            # Update course totals
            if assignment.score is not None and assignment.points_possible:
                course.total_score += assignment.score
                course.total_possible += assignment.points_possible
        
        courses.append(course)
    
    return courses 