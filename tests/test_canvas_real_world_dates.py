"""
Test real-world Canvas date parsing scenarios to demonstrate improved flexibility.
"""
import pytest
from datetime import datetime
from scrappers.assignment_scraper import AssignmentScraper


def test_canvas_real_world_date_scenarios():
    """Test parsing of actual Canvas date formats seen in production (date-only, no time accuracy)."""
    scraper = AssignmentScraper()
    current_year = datetime.now().year
    
    # These are actual date formats we've encountered from different teachers/schools
    # Note: Time components are now stripped, all dates return at midnight (00:00)
    real_canvas_dates = [
        # Format from test data: "Mar 17 by 11:59pm" - time will be ignored
        ("Mar 17 by 11:59pm", 3, 17),
        ("Mar 19 by 11:59pm", 3, 19),
        ("Apr 4 by 3:00pm", 4, 4),
        ("Apr 16 by 8:00am", 4, 16),
        ("May 22 by 9:00am", 5, 22),
        
        # Variations teachers might use - time components ignored
        ("Dec 15 at 11:59 PM", 12, 15),
        ("Jan 30, 2025 11:59pm", 1, 30, 2025),  # explicit year
        ("February 14 5pm", 2, 14),
        ("Sept 1st 8:30am", 9, 1),
        ("Nov 25th at 2:15pm", 11, 25),
        
        # Different separator styles - time components ignored
        ("10/31/2024 11:59pm", 10, 31, 2024),  # explicit year
        ("3-15-2025 5:00PM", 3, 15, 2025),  # explicit year
        ("12.25.2024 midnight", 12, 25, 2024),  # explicit year
        
        # Edge cases - time components ignored
        ("March 1 11:59 p.m.", 3, 1),
        ("Aug 15th by 11:59 PM", 8, 15),
        ("June 30th, 2025 at 11:59pm", 6, 30, 2025),  # explicit year
    ]
    
    for test_case in real_canvas_dates:
        if len(test_case) == 4:  # includes explicit year
            date_str, expected_month, expected_day, expected_year = test_case
        else:
            date_str, expected_month, expected_day = test_case
            expected_year = current_year
            
        result = scraper._parse_date(date_str)
        assert result is not None, f"Failed to parse real Canvas date: {date_str}"
        
        assert result.year == expected_year, f"Wrong year for {date_str}: got {result.year}, expected {expected_year}"
        assert result.month == expected_month, f"Wrong month for {date_str}: got {result.month}, expected {expected_month}"
        assert result.day == expected_day, f"Wrong day for {date_str}: got {result.day}, expected {expected_day}"
        # All parsed dates should be at midnight since we removed time parsing
        assert result.hour == 0, f"Expected midnight hour for {date_str}: got {result.hour}, expected 0"
        assert result.minute == 0, f"Expected midnight minute for {date_str}: got {result.minute}, expected 0"


def test_teacher_creative_date_formats():
    """Test that our flexible parser handles creative variations teachers might use."""
    scraper = AssignmentScraper()
    current_year = datetime.now().year
    
    # Formats that our simplified parser can handle
    creative_formats = [
        # Standard formats with time (which gets stripped)
        "Mar 17 at 11:59pm",  
        "April 15, 2025 @ 5:00 PM",  # @ symbol is stripped
        "May 1st 11:59pm",
        "Jun 30 by 8am",
        
        # Full month names
        "September 15 11:59pm",
        "November 15th at 2pm",
        
        # Basic date formats
        "Dec 25, 2024",
        "Jan 1 2025",
    ]
    
    for date_str in creative_formats:
        result = scraper._parse_date(date_str)
        # We should get a valid date for all these formats
        assert result is not None, f"Failed to parse creative format: {date_str}"
        # Year should be reasonable (within a few years of current year, or explicit year from string)
        assert 2020 <= result.year <= 2030, f"Year out of reasonable range for {date_str}: {result.year}"
        assert 1 <= result.month <= 12, f"Invalid month for {date_str}: {result.month}"
        assert 1 <= result.day <= 31, f"Invalid day for {date_str}: {result.day}"
        # All dates should be at midnight since we stripped time parsing
        assert result.hour == 0, f"Expected midnight for {date_str}: got {result.hour}"
        assert result.minute == 0, f"Expected midnight for {date_str}: got {result.minute}"


def test_structured_data_priority_with_real_canvas_json():
    """Test that structured JSON data takes priority over text when available (date-only)."""
    scraper = AssignmentScraper()
    
    # Real Canvas JSON structure (simplified from actual test data)
    real_canvas_html = '''
    <html>
    <head>
        <script>
            ENV = {
                "assignment_groups": [
                    {
                        "id": "343605",
                        "assignments": [
                            {
                                "id": "7167381",
                                "due_at": "2025-03-17T23:59:59-07:00",
                                "points_possible": 30.0
                            },
                            {
                                "id": "7167619", 
                                "due_at": "2025-04-16T08:00:00-07:00",
                                "points_possible": 100.0
                            }
                        ]
                    }
                ],
                "effective_due_dates": {
                    "7167381": {
                        "149157": {
                            "due_at": "2025-03-17T23:59:59-07:00"
                        }
                    }
                }
            };
        </script>
    </head>
    <body>
        <table>
            <tr class="student_assignment" id="submission_7167381">
                <th class="title">
                    <a href="/courses/102017/assignments/7167381/submissions/149157">Manifest Destiny Analysis</a>
                </th>
                <td class="due">Mar 17 by 11:59pm</td>
            </tr>
        </table>
    </body>
    </html>
    '''
    
    scraper.set_page_content(real_canvas_html, "102017")
    
    # Should extract from structured data, not text
    result = scraper._extract_structured_date("7167381")
    assert result is not None
    assert result.year == 2025
    assert result.month == 3
    assert result.day == 17
    # Time components are now stripped - should be at midnight
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0
    
    # When using the main parse_date method with assignment ID, should prefer structured data
    main_result = scraper._parse_date("Mar 17 by 11:59pm", "7167381")
    assert main_result is not None
    assert main_result.year == 2025
    assert main_result.month == 3
    assert main_result.day == 17
    # Should also be at midnight when using structured data
    assert main_result.hour == 0
    assert main_result.minute == 0


def test_fallback_gracefully_handles_malformed_json():
    """Test that malformed JSON doesn't break the date parsing, falls back gracefully."""
    scraper = AssignmentScraper()
    
    # HTML with malformed JSON
    malformed_html = '''
    <script>
        ENV = {
            "assignment_groups": [
                {
                    "assignments": [
                        {
                            "id": "123456",
                            "due_at": "2025-03-17T23:59:59-07:00"  // Missing comma
                            "points_possible": 30.0
                        }
                    ]
                }
            // Missing closing brace
        };
    </script>
    '''
    
    scraper.set_page_content(malformed_html, "102017")
    
    # Should fall back to text parsing when JSON is malformed
    result = scraper._parse_date("Mar 17 by 11:59pm", "123456")
    assert result is not None
    assert result.month == 3
    assert result.day == 17
    # Should get current year since the structured data extraction failed
    assert result.year == datetime.now().year


def test_performance_with_multiple_strategies():
    """Test that the multi-strategy approach doesn't significantly impact performance."""
    import time
    scraper = AssignmentScraper()
    
    # Test dates that will go through different strategies
    test_dates = [
        "Mar 17 by 11:59pm",  # dateutil parsing
        "Apr 15, 2025 5pm",   # dateutil parsing
        "Strange format XYZ", # Should fail quickly
        "May 1st 8:30am",     # dateutil parsing
        "Invalid",            # Should fail quickly
    ] * 10  # Repeat to get meaningful timing
    
    start_time = time.time()
    
    for date_str in test_dates:
        scraper._parse_date(date_str)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Should process 50 dates in well under a second
    assert total_time < 1.0, f"Date parsing too slow: {total_time:.3f} seconds for {len(test_dates)} dates"
    
    # Average should be under 20ms per date
    avg_time_per_date = total_time / len(test_dates)
    assert avg_time_per_date < 0.02, f"Average time per date too slow: {avg_time_per_date:.3f} seconds" 