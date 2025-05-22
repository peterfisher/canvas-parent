#!/usr/bin/env python3

import unittest
from unittest.mock import patch
from io import StringIO
from datetime import datetime, timedelta
from grades import Course, Assignment
from display import display_grades

class TestDisplay(unittest.TestCase):
    def setUp(self):
        # Create test course with assignments
        self.course = Course(1, "Test Course")
        
        # Create a few assignments with different statuses
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        # Submitted assignment
        assignment1 = Assignment(
            name="Submitted Assignment",
            due_date=yesterday,
            points_possible=100,
            score=85,
            submitted=True,
            missing=False
        )
        
        # Missing assignment
        assignment2 = Assignment(
            name="Missing Assignment",
            due_date=yesterday,
            points_possible=50,
            score=None,
            submitted=False,
            missing=True
        )
        
        # Late assignment
        assignment3 = Assignment(
            name="Late Assignment",
            due_date=yesterday,
            points_possible=75,
            score=None,
            submitted=False,
            missing=False
        )
        
        # Future assignment
        assignment4 = Assignment(
            name="Future Assignment",
            due_date=tomorrow,
            points_possible=60,
            score=None,
            submitted=False,
            missing=False
        )
        
        self.course.assignments = [assignment1, assignment2, assignment3, assignment4]
        self.course.total_score = 85
        self.course.total_possible = 100
        
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_grades(self, mock_stdout):
        # Call the function with our test data
        display_grades([self.course])
        
        # Get the printed output
        output = mock_stdout.getvalue()
        
        # Verify expected content is in the output
        self.assertIn("GRADE SUMMARY", output)
        self.assertIn("Test Course", output)
        self.assertIn("Overall Grade: 85.0%", output)
        self.assertIn("Submitted Assignment", output)
        self.assertIn("Missing Assignment", output)
        self.assertIn("MISSING", output)
        self.assertIn("SUBMITTED", output)
        self.assertIn("TOTAL: 85.0/100.0", output)
        
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_empty_courses(self, mock_stdout):
        # Test with empty list
        display_grades([])
        
        # Check output
        output = mock_stdout.getvalue()
        self.assertIn("No course data available", output)
        
if __name__ == "__main__":
    unittest.main() 