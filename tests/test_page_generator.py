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


if __name__ == '__main__':
    unittest.main() 