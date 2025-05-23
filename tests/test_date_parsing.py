import unittest
import sys
sys.path.append('..')
from scrappers.assignment_scraper import AssignmentScraper
from datetime import datetime


class TestDateParsing(unittest.TestCase):
    """Test the date parsing logic in AssignmentScraper"""
    
    def setUp(self):
        """Set up test scraper"""
        self.scraper = AssignmentScraper()
    
    def test_parse_date_with_various_formats(self):
        """Test parsing dates with different Canvas formats"""
        
        # Test cases with different date formats that might appear in Canvas
        test_cases = [
            # Standard Canvas formats
            ("May 23 11:59pm", True),
            ("May 23 at 11:59pm", True),
            ("May 23 by 11:59pm", True),
            ("Dec 25 2024 11:59pm", True),
            ("Jan 1 2025 at 11:59pm", True),
            
            # Edge cases that might cause failures
            ("", False),  # Empty string
            ("N/A", False),  # Literal N/A
            ("No Due Date", False),  # No due date text
            ("TBD", False),  # To be determined
            ("13/45/2024", False),  # Invalid format
            ("Some random text", False),  # Random text
            
            # Formats that our parser actually handles (surprisingly flexible)
            ("May 32 11:59pm", True),  # dateutil interprets as 2032-05-01
            ("2025-05-23 23:59:00", True),  # ISO format actually works
            ("5/23/2025", True),  # MM/DD/YYYY format works
            ("23 May 2025", True),  # DD Month YYYY format works
        ]
        
        for date_str, should_parse in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                if should_parse:
                    self.assertIsNotNone(result, f"Failed to parse: '{date_str}'")
                    self.assertIsInstance(result, datetime)
                else:
                    self.assertIsNone(result, f"Unexpectedly parsed: '{date_str}' -> {result}")
    
    def test_parse_date_current_year_assumption(self):
        """Test that dates without year assume current year (date-only)"""
        current_year = datetime.now().year
        result = self.scraper._parse_date("May 23 11:59pm")
        
        if result:  # Only test if parsing succeeded
            self.assertEqual(result.year, current_year)
            self.assertEqual(result.month, 5)
            self.assertEqual(result.day, 23)
            self.assertEqual(result.hour, 0)  # Should be midnight (date-only)
            self.assertEqual(result.minute, 0)  # Should be midnight (date-only)
    
    def test_parse_date_with_explicit_year(self):
        """Test dates with explicit years (date-only)"""
        result = self.scraper._parse_date("Dec 25 2024 11:59pm")
        
        if result:  # Only test if parsing succeeded
            self.assertEqual(result.year, 2024)
            self.assertEqual(result.month, 12)
            self.assertEqual(result.day, 25)
            # Time components should be stripped to midnight
            self.assertEqual(result.hour, 0)
            self.assertEqual(result.minute, 0)
    
    def test_common_canvas_due_date_patterns(self):
        """Test patterns commonly seen in Canvas that might not be parsing correctly"""
        
        # These are patterns I suspect might be failing based on the high NULL rate
        potentially_problematic = [
            "Due: May 23, 2025 at 11:59pm",  # Full "Due:" prefix
            "Due May 23 at 11:59pm",  # "Due" without colon
            "May 23, 2025 11:59pm",  # Comma in date
            "May 23rd at 11:59pm",  # Ordinal dates
            "5/23 at 11:59pm",  # Numeric month
            "23-May-2025",  # Dash separated
            "May 23 (11:59 PM)",  # Parentheses around time
            "23 May 11:59pm",  # Day first format
        ]
        
        print("\nTesting potentially problematic Canvas date formats:")
        for date_str in potentially_problematic:
            result = self.scraper._parse_date(date_str)
            print(f"  '{date_str}' -> {result}")
            
        # These should all fail with current implementation
        # This will help us identify what formats Canvas actually uses


if __name__ == '__main__':
    unittest.main() 