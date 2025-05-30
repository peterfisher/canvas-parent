#!/usr/bin/env python3

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from frontend.page_generator import PageGenerator


class TestPageGenerator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.template_dir = os.path.join(self.temp_dir, 'templates')
        self.output_dir = os.path.join(self.temp_dir, 'output')
        
        # Create template directory
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Initialize PageGenerator
        self.page_generator = PageGenerator(
            db_path=self.db_path,
            template_dir=self.template_dir,
            output_dir=self.output_dir
        )

    def test_format_due_date_upcoming_assignment(self):
        """Test formatting of upcoming assignment due dates with days remaining"""
        # Test assignment due tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow.isoformat()
        
        result = self.page_generator._format_due_date(tomorrow_str, 'UPCOMING')
        expected_date = tomorrow.strftime("%B %d, %Y")
        self.assertEqual(result, f"{expected_date} (1 day left)")
        
        # Test assignment due in 5 days
        future_date = datetime.now() + timedelta(days=5)
        future_str = future_date.isoformat()
        
        result = self.page_generator._format_due_date(future_str, 'UPCOMING')
        expected_date = future_date.strftime("%B %d, %Y")
        self.assertEqual(result, f"{expected_date} (5 days left)")
        
        # Test assignment due today
        today = datetime.now().replace(hour=23, minute=59)
        today_str = today.isoformat()
        
        result = self.page_generator._format_due_date(today_str, 'UPCOMING')
        expected_date = today.strftime("%B %d, %Y")
        self.assertEqual(result, f"{expected_date} (due today)")

    def test_format_due_date_past_assignment(self):
        """Test formatting of past assignment due dates without days remaining"""
        # Test past assignment
        past_date = datetime.now() - timedelta(days=3)
        past_str = past_date.isoformat()
        
        result = self.page_generator._format_due_date(past_str, 'GRADED')
        expected = past_date.strftime("%B %d, %Y")
        self.assertEqual(result, expected)
        
        # Test submitted assignment
        result = self.page_generator._format_due_date(past_str, 'SUBMITTED')
        self.assertEqual(result, expected)

    def test_format_due_date_no_date(self):
        """Test formatting when no due date is provided"""
        result = self.page_generator._format_due_date(None, 'UPCOMING')
        self.assertEqual(result, 'N/A')
        
        result = self.page_generator._format_due_date('', 'GRADED')
        self.assertEqual(result, 'N/A')

    def test_format_due_date_invalid_date(self):
        """Test formatting with invalid date strings"""
        result = self.page_generator._format_due_date('invalid-date', 'UPCOMING')
        self.assertEqual(result, 'invalid-date')
        
        result = self.page_generator._format_due_date('2025-13-45', 'UPCOMING')
        self.assertEqual(result, '2025-13-45')

    def test_format_score_letter_grades(self):
        """Test formatting of scores with correct letter grades"""
        # Test A grade (90-100%)
        result = self.page_generator._format_score(95, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-a grade-letter">A</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">95/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test B grade (80-89%)
        result = self.page_generator._format_score(85, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-b grade-letter">B</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">85/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test C grade (70-79%)
        result = self.page_generator._format_score(75, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-c grade-letter">C</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">75/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test D grade (60-69%)
        result = self.page_generator._format_score(65, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-d grade-letter">D</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">65/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test F grade (0-59%)
        result = self.page_generator._format_score(45, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-f grade-letter">F</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">45/100</span>
            </div>'''
        self.assertEqual(result, expected)

    def test_format_score_edge_cases(self):
        """Test score formatting with edge cases and boundary values"""
        # Test exact boundary values
        result = self.page_generator._format_score(90, 100)  # Exactly 90%
        self.assertIn('grade-a', result)
        
        result = self.page_generator._format_score(89.9, 100)  # Just below 90%
        self.assertIn('grade-b', result)
        
        # Test perfect score
        result = self.page_generator._format_score(100, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-a grade-letter">A</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">100/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test zero score
        result = self.page_generator._format_score(0, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-f grade-letter">F</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">0/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test fractional scores (should format cleanly)
        result = self.page_generator._format_score(87.5, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-b grade-letter">B</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">87.5/100</span>
            </div>'''
        self.assertEqual(result, expected)

    def test_format_score_different_point_values(self):
        """Test score formatting with different point scales"""
        # Test small assignment
        result = self.page_generator._format_score(9, 10)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-a grade-letter">A</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">9/10</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test large assignment
        result = self.page_generator._format_score(450, 500)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-a grade-letter">A</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">450/500</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test odd point values
        result = self.page_generator._format_score(23, 30)  # 76.67% = C
        self.assertIn('grade-c', result)
        self.assertIn('23/30', result)

    def test_format_score_none_values(self):
        """Test score formatting when score or max_score is None"""
        # Test None score
        result = self.page_generator._format_score(None, 100)
        expected = '''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test None max_score
        result = self.page_generator._format_score(85, None)
        expected = '''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test both None
        result = self.page_generator._format_score(None, None)
        expected = '''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
        self.assertEqual(result, expected)

    def test_format_score_invalid_values(self):
        """Test score formatting with invalid input values"""
        # Test string values
        result = self.page_generator._format_score('invalid', 100)
        expected = '''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
        self.assertEqual(result, expected)
        
        result = self.page_generator._format_score(85, 'invalid')
        expected = '''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
        self.assertEqual(result, expected)

    def test_format_score_floating_point_precision(self):
        """Test that floating point scores are formatted cleanly"""
        # Test that .0 is removed from whole numbers
        result = self.page_generator._format_score(85.0, 100.0)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-b grade-letter">B</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">85/100</span>
            </div>'''
        self.assertEqual(result, expected)
        
        # Test that meaningful decimals are preserved
        result = self.page_generator._format_score(85.75, 100)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-b grade-letter">B</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">85.75/100</span>
            </div>'''
        self.assertEqual(result, expected)

    def test_format_score_zero_max_score(self):
        """Test score formatting with zero max_score"""
        # Test zero max_score (edge case)
        result = self.page_generator._format_score(0, 0)
        expected = '''<div class="score-container">
                <span class="letter-grade grade-f grade-letter">F</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">0/0</span>
            </div>'''
        self.assertEqual(result, expected)

    def test_group_assignments_into_sections(self):
        """Test assignment grouping and sorting within sections"""
        # Create test assignments with different statuses and due dates
        test_assignments = [
            {
                'name': 'Future Assignment 1',
                'status': 'UPCOMING',
                'due_date': (datetime.now() + timedelta(days=2)).isoformat(),
                'course_name': 'Math'
            },
            {
                'name': 'Future Assignment 2',
                'status': 'UPCOMING',
                'due_date': (datetime.now() + timedelta(days=1)).isoformat(),
                'course_name': 'Science'
            },
            {
                'name': 'Graded Assignment 1',
                'status': 'GRADED',
                'due_date': (datetime.now() - timedelta(days=3)).isoformat(),
                'course_name': 'English'
            },
            {
                'name': 'Submitted Assignment',
                'status': 'SUBMITTED',
                'due_date': (datetime.now() - timedelta(days=1)).isoformat(),
                'course_name': 'History'
            },
            {
                'name': 'Late Assignment',
                'status': 'LATE',
                'due_date': (datetime.now() - timedelta(days=5)).isoformat(),
                'course_name': 'Art'
            },
            {
                'name': 'Missing Assignment',
                'status': 'MISSING',
                'due_date': (datetime.now() - timedelta(days=7)).isoformat(),
                'course_name': 'PE'
            },
            {
                'name': 'Unknown Assignment',
                'status': 'UNKNOWN',
                'due_date': None,
                'course_name': 'Music'
            },
            {
                'name': 'Excused Assignment',
                'status': 'EXCUSED',
                'due_date': (datetime.now() - timedelta(days=2)).isoformat(),
                'course_name': 'Biology'
            }
        ]
        
        # Test the grouping function
        sections = self.page_generator._group_assignments_into_sections(test_assignments)
        
        # Verify section structure
        self.assertIn('upcoming', sections)
        self.assertIn('graded', sections)
        self.assertIn('missing', sections)
        self.assertIn('unknown', sections)
        
        # Verify upcoming section
        upcoming_section = sections['upcoming']
        self.assertEqual(upcoming_section['title'], 'Upcoming Assignments')
        self.assertEqual(upcoming_section['count'], 2)
        self.assertEqual(len(upcoming_section['assignments']), 2)
        
        # Verify upcoming assignments are sorted by due date (soonest first)
        upcoming_assignments = upcoming_section['assignments']
        self.assertEqual(upcoming_assignments[0]['name'], 'Future Assignment 2')  # 1 day away (soonest)
        self.assertEqual(upcoming_assignments[1]['name'], 'Future Assignment 1')  # 2 days away
        
        # Verify graded section includes GRADED, SUBMITTED, EXCUSED, LATE
        graded_section = sections['graded']
        self.assertEqual(graded_section['title'], 'Graded Assignments')
        self.assertEqual(graded_section['count'], 4)
        graded_assignment_names = [a['name'] for a in graded_section['assignments']]
        self.assertIn('Graded Assignment 1', graded_assignment_names)
        self.assertIn('Submitted Assignment', graded_assignment_names)
        self.assertIn('Late Assignment', graded_assignment_names)
        self.assertIn('Excused Assignment', graded_assignment_names)
        
        # Verify graded assignments are sorted by due date (newest first)
        graded_assignments = graded_section['assignments']
        expected_order = ['Submitted Assignment', 'Excused Assignment', 'Graded Assignment 1', 'Late Assignment']
        actual_order = [a['name'] for a in graded_assignments]
        self.assertEqual(actual_order, expected_order)
        
        # Verify missing section includes only MISSING
        missing_section = sections['missing']
        self.assertEqual(missing_section['title'], 'Missing Assignments')
        self.assertEqual(missing_section['count'], 1)
        missing_assignment_names = [a['name'] for a in missing_section['assignments']]
        self.assertIn('Missing Assignment', missing_assignment_names)
        
        # Verify unknown section includes only UNKNOWN
        unknown_section = sections['unknown']
        self.assertEqual(unknown_section['title'], 'Unknown Assignments')
        self.assertEqual(unknown_section['count'], 1)
        unknown_assignment_names = [a['name'] for a in unknown_section['assignments']]
        self.assertIn('Unknown Assignment', unknown_assignment_names)
        
        # Verify assignments with None due_date come last in sorting
        unknown_assignments = unknown_section['assignments']
        self.assertEqual(unknown_assignments[0]['name'], 'Unknown Assignment')  # None due date
        
    def test_group_assignments_empty_list(self):
        """Test assignment grouping with empty list"""
        sections = self.page_generator._group_assignments_into_sections([])
        
        # Verify all sections exist but are empty
        self.assertEqual(sections['upcoming']['count'], 0)
        self.assertEqual(sections['graded']['count'], 0)
        self.assertEqual(sections['missing']['count'], 0)
        self.assertEqual(sections['unknown']['count'], 0)
        self.assertEqual(len(sections['upcoming']['assignments']), 0)
        self.assertEqual(len(sections['graded']['assignments']), 0)
        self.assertEqual(len(sections['missing']['assignments']), 0)
        self.assertEqual(len(sections['unknown']['assignments']), 0)


if __name__ == '__main__':
    unittest.main() 