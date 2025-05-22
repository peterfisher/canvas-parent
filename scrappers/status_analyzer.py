from bs4 import BeautifulSoup
from typing import Set, Dict
from collections import defaultdict
from pathlib import Path
import sys
from os.path import dirname, abspath

# Add the parent directory to sys.path
parent_dir = dirname(dirname(abspath(__file__)))
sys.path.append(parent_dir)

from scrappers.assignment_scraper import AssignmentScraper

def analyze_assignment_statuses(html_file: str) -> Dict[str, Set[str]]:
    """
    Analyze an HTML file to find all possible assignment statuses and their context.
    Returns a dictionary of status information and raw HTML context.
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    scraper = AssignmentScraper()
    # Using a test course ID since we're just analyzing statuses
    scraper.set_page_content(html_content, course_id="test_course_123")
    
    status_info = defaultdict(set)
    assignment_rows = soup.find_all("tr", class_="student_assignment")

    for row in assignment_rows:
        try:
            # Get the assignment name for context
            title_cell = row.find("th", class_="title")
            name = title_cell.find("a").text.strip() if title_cell and title_cell.find("a") else "Unknown"
            
            # Get the raw status elements
            status_cell = row.find("td", class_="status")
            submission_status = row.find("span", class_="submission_status")
            status_text = submission_status.text.strip() if submission_status else "None"
            
            # Get the determined status using our scraper
            determined_status = scraper._determine_status(row)
            
            # Collect relevant HTML classes
            row_classes = " ".join(row.get("class", []))
            status_classes = " ".join(status_cell.get("class", [])) if status_cell else "None"
            
            # Get additional status indicators
            late_pill = row.find("span", class_="submission-late-pill")
            is_late = "Yes" if late_pill else "No"
            
            excused = "excused" in row.get("class", [])
            is_excused = "Yes" if excused else "No"
            
            # Get submission date info
            submitted_date = row.find("td", class_="submitted")
            submitted_text = submitted_date.text.strip() if submitted_date else "None"
            
            # Store the context with more detailed information
            context = (
                f"Assignment: {name} | "
                f"Raw Status: {status_text} | "
                f"Row Classes: {row_classes} | "
                f"Status Cell Classes: {status_classes} | "
                f"Is Late: {is_late} | "
                f"Is Excused: {is_excused} | "
                f"Submission Date: {submitted_text}"
            )
            status_info[str(determined_status)].add(context)
        except Exception as e:
            print(f"Error processing row for assignment '{name}': {str(e)}")
            continue
    
    return status_info

def main():
    # Get the path to the test data
    current_dir = Path(__file__).parent
    test_data_path = current_dir.parent / "tests" / "test_data" / "real_grades_page.html"
    
    if not test_data_path.exists():
        print(f"Test data file not found at: {test_data_path}")
        return
    
    print("Analyzing assignment statuses...\n")
    status_info = analyze_assignment_statuses(str(test_data_path))
    
    print("Found the following assignment statuses:")
    print("=" * 80)
    for status, contexts in sorted(status_info.items()):
        print(f"\n{status}:")
        print("-" * 40)
        for context in sorted(contexts):
            print(f"  • {context}")
        print()
    
    print("\nTotal unique statuses found:", len(status_info))

if __name__ == "__main__":
    main() 