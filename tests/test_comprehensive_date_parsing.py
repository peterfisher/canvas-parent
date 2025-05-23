import unittest
import sys
sys.path.append('..')
from scrappers.assignment_scraper import AssignmentScraper
from datetime import datetime


class TestComprehensiveDateParsing(unittest.TestCase):
    """Comprehensive test suite for Canvas date parsing to prevent regressions"""
    
    def setUp(self):
        """Set up test scraper"""
        self.scraper = AssignmentScraper()
        self.current_year = datetime.now().year
    
    def test_comma_separated_dates_with_year(self):
        """Test comma-separated dates with explicit year (date-only, time components ignored)"""
        test_cases = [
            # Standard comma format - time components are stripped
            ("May 23, 2025 11:59pm", datetime(2025, 5, 23, 0, 0)),
            ("Dec 25, 2024 11:59pm", datetime(2024, 12, 25, 0, 0)),
            ("Jan 1, 2025 11:59pm", datetime(2025, 1, 1, 0, 0)),
            
            # With space in time - time components are stripped
            ("May 23, 2025 11:59 pm", datetime(2025, 5, 23, 0, 0)),
            ("Dec 25, 2024 11:59 pm", datetime(2024, 12, 25, 0, 0)),
            
            # With "at" prefix - time components are stripped
            ("May 23, 2025 at 11:59pm", datetime(2025, 5, 23, 0, 0)),
            ("Dec 25, 2024 at 11:59 pm", datetime(2024, 12, 25, 0, 0)),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNotNone(result, f"Failed to parse: '{date_str}'")
                self.assertEqual(result, expected, f"'{date_str}' parsed to {result}, expected {expected}")
    
    def test_original_formats_still_work(self):
        """Test that original working formats still work (backward compatibility, date-only)"""
        test_cases = [
            ("May 23 11:59pm", datetime(self.current_year, 5, 23, 0, 0)),
            ("May 23 11:59 pm", datetime(self.current_year, 5, 23, 0, 0)),
            ("Dec 25 2024 11:59pm", datetime(2024, 12, 25, 0, 0)),
            ("May 23 at 11:59pm", datetime(self.current_year, 5, 23, 0, 0)),
            ("May 23 at 11:59 pm", datetime(self.current_year, 5, 23, 0, 0)),
            ("May 23 by 11:59pm", datetime(self.current_year, 5, 23, 0, 0)),
            ("May 23 by 11:59 pm", datetime(self.current_year, 5, 23, 0, 0)),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNotNone(result, f"Failed to parse: '{date_str}'")
                self.assertEqual(result, expected, f"'{date_str}' parsed to {result}, expected {expected}")
    
    def test_prefix_handling(self):
        """Test handling of Canvas due date prefixes (date-only)"""
        test_cases = [
            # "Due:" prefix - time components are stripped
            ("Due: May 23, 2025 at 11:59pm", datetime(2025, 5, 23, 0, 0)),
            ("Due: May 23 at 11:59pm", datetime(self.current_year, 5, 23, 0, 0)),
            
            # "Due" without colon - time components are stripped
            ("Due May 23, 2025 at 11:59pm", datetime(2025, 5, 23, 0, 0)),
            ("Due May 23 at 11:59pm", datetime(self.current_year, 5, 23, 0, 0)),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNotNone(result, f"Failed to parse: '{date_str}'")
                self.assertEqual(result, expected, f"'{date_str}' parsed to {result}, expected {expected}")
    
    def test_no_due_date_indicators(self):
        """Test various 'no due date' indicators return None"""
        no_date_cases = [
            "No Due Date",
            "no due date", 
            "No due date",
            "TBD",
            "tbd",
            "N/A",
            "n/a",
            "-",
            "None",
            "none",
            "",           # Empty string
            "   ",        # Whitespace only
        ]
        
        for date_str in no_date_cases:
            with self.subTest(date_str=repr(date_str)):
                result = self.scraper._parse_date(date_str)
                self.assertIsNone(result, f"Expected None for '{date_str}', got {result}")
    
    def test_invalid_dates_return_none(self):
        """Test that invalid dates gracefully return None"""
        invalid_cases = [
            "13th month 11:59pm",       # Invalid month name
            "23-May-2025",              # Different format (not yet supported)
            "Some random text",         # Random text
            "13/45/2024",              # Invalid format
        ]
        
        for date_str in invalid_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNone(result, f"Expected None for invalid date '{date_str}', got {result}")
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions (date-only)"""
        test_cases = [
            # Different months - all times are stripped to midnight
            ("Jan 1, 2025 12:00am", datetime(2025, 1, 1, 0, 0)),
            ("Feb 14, 2025 12:00pm", datetime(2025, 2, 14, 0, 0)),
            ("Mar 31, 2025 11:59pm", datetime(2025, 3, 31, 0, 0)),
            ("Apr 30, 2025 1:00am", datetime(2025, 4, 30, 0, 0)),
            ("Dec 31, 2024 11:59pm", datetime(2024, 12, 31, 0, 0)),
            
            # Different times - all stripped to midnight
            ("May 23, 2025 12:00am", datetime(2025, 5, 23, 0, 0)),    # Midnight
            ("May 23, 2025 12:00pm", datetime(2025, 5, 23, 0, 0)),   # Noon
            ("May 23, 2025 1:00am", datetime(2025, 5, 23, 0, 0)),     # 1 AM
            ("May 23, 2025 1:00pm", datetime(2025, 5, 23, 0, 0)),    # 1 PM
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNotNone(result, f"Failed to parse: '{date_str}'")
                self.assertEqual(result, expected, f"'{date_str}' parsed to {result}, expected {expected}")
    
    def test_year_assumption_for_no_year_formats(self):
        """Test that dates without years assume current year"""
        test_cases = [
            "May 23 11:59pm",
            "Dec 25 11:59pm", 
            "Jan 1 at 11:59pm",
        ]
        
        for date_str in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNotNone(result, f"Failed to parse: '{date_str}'")
                self.assertEqual(result.year, self.current_year, 
                               f"Expected current year {self.current_year}, got {result.year}")
    
    def test_case_sensitivity(self):
        """Test case sensitivity handling (date-only)"""
        # Python's datetime parsing is more flexible than expected
        # This test documents the actual behavior
        test_cases = [
            ("may 23, 2025 11:59pm", True),      # lowercase month actually works
            ("MAY 23, 2025 11:59pm", True),      # uppercase month actually works  
            ("May 23, 2025 11:59PM", True),      # uppercase PM actually works
            ("May 23, 2025 11:59pm", True),      # proper case should work
        ]
        
        for date_str, should_work in test_cases:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                if should_work:
                    self.assertIsNotNone(result, f"Expected '{date_str}' to parse")
                    # Verify the parsed result is correct (date-only)
                    self.assertEqual(result.year, 2025)
                    self.assertEqual(result.month, 5)
                    self.assertEqual(result.day, 23)
                    self.assertEqual(result.hour, 0)  # Should be midnight
                    self.assertEqual(result.minute, 0)  # Should be midnight
                else:
                    self.assertIsNone(result, f"Expected '{date_str}' to fail parsing")
    
    def test_regression_prevention(self):
        """Test specific cases that caused the original bug (date-only)"""
        # These are the exact formats that were causing NULL due dates
        problematic_formats = [
            ("May 23, 2025 at 11:59pm", datetime(2025, 5, 23, 0, 0)),
            ("Dec 25, 2024 at 11:59pm", datetime(2024, 12, 25, 0, 0)),
            ("Jan 1, 2025 at 11:59pm", datetime(2025, 1, 1, 0, 0)),
        ]
        
        for date_str, expected in problematic_formats:
            with self.subTest(date_str=date_str):
                result = self.scraper._parse_date(date_str)
                self.assertIsNotNone(result, 
                                   f"REGRESSION: '{date_str}' failed to parse - this was the main bug!")
                self.assertEqual(result, expected, 
                               f"REGRESSION: '{date_str}' parsed incorrectly")


if __name__ == '__main__':
    unittest.main() 