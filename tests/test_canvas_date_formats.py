import unittest
import sys
sys.path.append('..')
from scrappers.assignment_scraper import AssignmentScraper
from datetime import datetime


class TestCanvasDateFormats(unittest.TestCase):
    """Comprehensive test for Canvas date formats that are failing"""
    
    def setUp(self):
        """Set up test scraper"""
        self.scraper = AssignmentScraper()
    
    def test_known_problematic_formats(self):
        """Test formats identified as problematic from our analysis"""
        
        # Formats that Canvas likely uses - now testing which ones work after the fix
        test_formats = [
            # Comma-separated dates (FIXED - these now work!)
            ("May 23, 2025 at 11:59pm", True),   # FIXED!
            ("Dec 25, 2024 at 11:59pm", True),   # FIXED!
            ("Jan 1, 2025 at 11:59pm", True),    # FIXED!
            
            # Text indicators for no due date (should return None)
            ("No Due Date", False),
            ("TBD", False),
            ("-", False),
            ("N/A", False),
            ("", False),
            ("   ", False),  # Whitespace only
            
            # Potential other Canvas formats
            ("Due: May 23 at 11:59pm", True),    # FIXED!
            ("May 23rd at 11:59pm", False),      # Ordinal (not yet supported)
            ("5/23 at 11:59pm", False),          # Numeric month (not yet supported)
            ("May 23 (11:59 PM)", False),        # Parentheses (not yet supported)
            ("2025-05-23T23:59:00Z", False),     # ISO format (not yet supported)
        ]
        
        print("\nTesting Canvas date formats after the fix:")
        successful_parses = 0
        expected_successes = sum(1 for _, should_work in test_formats if should_work)
        
        for date_str, should_work in test_formats:
            result = self.scraper._parse_date(date_str)
            success = result is not None
            if success == should_work:
                successful_parses += 1
            status = "✓" if success == should_work else "✗"
            expected = "should work" if should_work else "should fail"
            print(f"  '{date_str}' -> {result} ({expected}) {status}")
        
        print(f"\nTest accuracy: {successful_parses}/{len(test_formats)} ({successful_parses/len(test_formats)*100:.1f}%)")
        
        # The main fix: comma-separated dates should now parse successfully
        self.assertIsNotNone(self.scraper._parse_date("May 23, 2025 at 11:59pm"))
        self.assertIsNotNone(self.scraper._parse_date("Dec 25, 2024 at 11:59pm"))
    
    def test_current_working_formats(self):
        """Test formats that currently work"""
        
        working_formats = [
            "May 23 at 11:59pm",
            "May 23 11:59pm", 
            "Dec 25 2024 11:59pm",
            "May 23 by 11:59pm",
        ]
        
        print("\nTesting currently working formats:")
        for date_str in working_formats:
            result = self.scraper._parse_date(date_str)
            success = result is not None
            print(f"  '{date_str}' -> {result} {'✓' if success else '✗'}")
            
            # These should all work
            self.assertIsNotNone(result, f"Expected '{date_str}' to parse successfully")
    
    def test_improved_date_parser(self):
        """Test an improved date parser that handles commas"""
        
        def improved_parse_date(date_str: str):
            """Improved date parser that handles comma-separated dates"""
            if not date_str:
                return None
            
            # Remove common prefixes and indicators
            date_str = date_str.replace("Due: ", "").replace("Due ", "")
            date_str = date_str.replace(" at ", " ").replace(" by ", " ").strip()
            
            # Handle "No Due Date" cases
            no_date_indicators = ["No Due Date", "TBD", "N/A", "-", ""]
            if date_str.strip() in no_date_indicators:
                return None
            
            try:
                current_year = datetime.now().year
                
                # Try different formats including comma-separated dates
                formats = [
                    "%b %d, %Y %I:%M%p",    # May 23, 2025 11:59pm
                    "%b %d, %Y %I:%M %p",   # May 23, 2025 11:59 pm  
                    "%b %d %Y %I:%M%p",     # May 23 2025 11:59pm
                    "%b %d %I:%M%p",        # May 23 11:59pm
                    "%b %d %I:%M %p",       # May 23 11:59 pm
                ]
                
                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        # Set current year if year wasn't in the format
                        if "%Y" not in fmt:
                            return parsed_date.replace(year=current_year)
                        return parsed_date
                    except ValueError:
                        continue
                        
                return None
            except Exception:
                return None
        
        # Test the improved parser
        test_cases = [
            ("May 23, 2025 at 11:59pm", True),
            ("Dec 25, 2024 at 11:59pm", True), 
            ("May 23 at 11:59pm", True),
            ("No Due Date", False),
            ("TBD", False),
            ("", False),
        ]
        
        print("\nTesting improved date parser:")
        for date_str, should_work in test_cases:
            result = improved_parse_date(date_str)
            success = result is not None
            expected = "✓" if should_work else "✗"
            actual = "✓" if success else "✗"
            status = "PASS" if (success == should_work) else "FAIL"
            
            print(f"  '{date_str}' -> {result} [{expected}→{actual}] {status}")


if __name__ == '__main__':
    unittest.main() 