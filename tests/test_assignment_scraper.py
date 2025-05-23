import pytest
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from scrappers.assignment_scraper import AssignmentScraper
from database.models import AssignmentType, AssignmentStatus
import os

def load_test_data(filename):
    """Load test data from the test_data directory."""
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    with open(os.path.join(test_data_dir, filename), 'r') as f:
        return f.read()

@pytest.fixture
def assignment_scraper():
    """Create an AssignmentScraper instance."""
    return AssignmentScraper()

@pytest.fixture
def real_grades_page():
    """Load the real grades page HTML."""
    return load_test_data('real_grades_page.html')

@pytest.fixture
def mock_html_row():
    """Create a mock HTML row for testing specific status scenarios."""
    return """
    <tr class="student_assignment {row_classes}">
        <th class="title">
            <a href="#">{title}</a>
            <div class="context">{context}</div>
        </th>
        <td class="due">{due_date}</td>
        <td class="submitted">{submitted_date}</td>
        <td class="status {status_cell_classes}">{status_html}</td>
        <td class="assignment_score">{score_html}</td>
    </tr>
    """

def test_parse_date_with_time(assignment_scraper):
    """Test parsing dates with time."""
    current_year = datetime.now().year
    
    # Test various date formats
    test_cases = [
        ("Mar 17 11:59PM", f"{current_year}-03-17 23:59:00"),
        ("Apr 16 8:00AM", f"{current_year}-04-16 08:00:00"),
        ("Dec 19 3:30PM", f"{current_year}-12-19 15:30:00"),
        ("Jan 15 8:00AM", f"{current_year}-01-15 08:00:00"),
        # Test with explicit year
        ("Mar 17 2025 11:59PM", "2025-03-17 23:59:00"),
        ("Dec 19 2024 3:30PM", "2024-12-19 15:30:00")
    ]
    
    for date_str, expected in test_cases:
        result = assignment_scraper._parse_date(date_str)
        assert result is not None
        assert result.strftime("%Y-%m-%d %H:%M:%S") == expected

def test_parse_date_invalid_formats(assignment_scraper):
    """Test parsing invalid date formats."""
    invalid_dates = [
        "",
        None,
        "Invalid Date",
        "2025",
        "Mar",
    ]
    
    for date_str in invalid_dates:
        result = assignment_scraper._parse_date(date_str)
        assert result is None

def test_determine_assignment_type(assignment_scraper):
    """Test determining assignment types from context strings."""
    test_cases = [
        ("Unit 1 Quiz", AssignmentType.QUIZ),
        ("Chapter 2 Test", AssignmentType.TEST),
        ("Lab Report 3", AssignmentType.LAB),
        ("Homework Assignment", AssignmentType.HOMEWORK),
        ("Group Project", AssignmentType.PROJECT),
        ("Writing Assignment", AssignmentType.PROJECT),
        ("Random Activity", AssignmentType.OTHER),
        ("", AssignmentType.OTHER),
        (None, AssignmentType.OTHER)
    ]
    
    for context, expected_type in test_cases:
        result = assignment_scraper._determine_assignment_type(context)
        assert result == expected_type

def test_determine_status_specific_cases(assignment_scraper, mock_html_row):
    """Test specific status determination scenarios."""
    future_date = (datetime.now() + timedelta(days=7)).strftime("%b %d %I:%M%p")
    past_date = (datetime.now() - timedelta(days=7)).strftime("%b %d %I:%M%p")
    
    test_cases = [
        # Test EXCUSED status (highest priority)
        {
            "row_classes": "student_assignment excused",
            "title": "Excused Assignment",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">graded</span>',
            "score_html": '<span class="grade">EX</span>',
            "expected_status": AssignmentStatus.EXCUSED
        },
        # Test LATE status
        {
            "row_classes": "student_assignment",
            "title": "Late Assignment",
            "context": "",
            "due_date": past_date,
            "submitted_date": past_date,
            "status_cell_classes": "",
            "status_html": '<span class="submission-late-pill">LATE</span>',
            "score_html": "",
            "expected_status": AssignmentStatus.LATE
        },
        # Test GRADED status
        {
            "row_classes": "student_assignment assignment_graded",
            "title": "Graded Assignment",
            "context": "",
            "due_date": past_date,
            "submitted_date": past_date,
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">graded</span>',
            "score_html": '<span class="grade">95</span>',
            "expected_status": AssignmentStatus.GRADED
        },
        # Test SUBMITTED status
        {
            "row_classes": "student_assignment",
            "title": "Submitted Assignment",
            "context": "",
            "due_date": past_date,
            "submitted_date": past_date,
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">submitted</span>',
            "score_html": "",
            "expected_status": AssignmentStatus.SUBMITTED
        },
        # Test UPCOMING status
        {
            "row_classes": "student_assignment",
            "title": "Future Assignment",
            "context": "",
            "due_date": future_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": "",
            "score_html": "",
            "expected_status": AssignmentStatus.UPCOMING
        },
        # Test MISSING status - with visual indicator (submission-missing-pill)
        {
            "row_classes": "student_assignment",
            "title": "Missing Assignment with Pill",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">unsubmitted</span><span class="submission-missing-pill">MISSING</span>',
            "score_html": '<span class="grade">0</span><span> / 10</span>',
            "expected_status": AssignmentStatus.MISSING
        },
        # Test MISSING status - with missing_assignment class
        {
            "row_classes": "student_assignment missing_assignment",
            "title": "Missing Assignment with Class",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">unsubmitted</span>',
            "score_html": '<span class="grade">0</span><span> / 10</span>',
            "expected_status": AssignmentStatus.MISSING
        },
        # Test MISSING status - with missing class in status cell
        {
            "row_classes": "student_assignment",
            "title": "Missing Assignment with Status Class",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "missing",
            "status_html": '<span class="submission_status">unsubmitted</span>',
            "score_html": '<span class="grade">0</span><span> / 10</span>',
            "expected_status": AssignmentStatus.MISSING
        },
        # Test NOT MISSING - unsubmitted but pending grading with - score
        {
            "row_classes": "student_assignment",
            "title": "Pending Grading Assignment with Dash",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">unsubmitted</span>',
            "score_html": '<span class="grade">-</span><span> / 10</span>',
            "expected_status": AssignmentStatus.UNKNOWN
        },
        # Test NOT MISSING - unsubmitted but pending grading with en-dash score
        {
            "row_classes": "student_assignment",
            "title": "Pending Grading Assignment with En-dash",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">unsubmitted</span>',
            "score_html": '<span class="grade">–</span><span> / 10</span>',
            "expected_status": AssignmentStatus.UNKNOWN
        },
        # Test NOT MISSING - unsubmitted but pending grading with empty score
        {
            "row_classes": "student_assignment",
            "title": "Pending Grading Assignment with Empty Score",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">unsubmitted</span>',
            "score_html": '<span class="grade"></span><span> / 10</span>',
            "expected_status": AssignmentStatus.UNKNOWN
        },
        # Test MISSING status - unsubmitted with indicator and pending grading (still missing due to pill)
        {
            "row_classes": "student_assignment",
            "title": "Missing Despite Pending Grading",
            "context": "",
            "due_date": past_date,
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": '<span class="submission_status">unsubmitted</span><span class="submission-missing-pill">MISSING</span>',
            "score_html": '<span class="grade">-</span><span> / 10</span>',
            "expected_status": AssignmentStatus.MISSING
        },
        # Test UNKNOWN status (final grade row)
        {
            "row_classes": "student_assignment hard_coded final_grade",
            "title": "Final Grade",
            "context": "",
            "due_date": "",
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": "",
            "score_html": "",
            "expected_status": AssignmentStatus.UNKNOWN
        },
        # Test UNKNOWN status (ambiguous case)
        {
            "row_classes": "student_assignment",
            "title": "Ambiguous Assignment",
            "context": "",
            "due_date": "",
            "submitted_date": "",
            "status_cell_classes": "",
            "status_html": "",
            "score_html": "",
            "expected_status": AssignmentStatus.UNKNOWN
        }
    ]
    
    for case in test_cases:
        html = mock_html_row.format(**case)
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find("tr")
        status = assignment_scraper._determine_status(row)
        assert status == case["expected_status"], f"Failed for case: {case['title']}"

def test_determine_status_from_real_data(assignment_scraper, real_grades_page):
    """Test determining assignment status from real HTML data."""
    soup = BeautifulSoup(real_grades_page, 'html.parser')
    assignment_rows = soup.find_all("tr", class_="student_assignment")
    
    # Test various status scenarios from real data
    status_counts = {status: 0 for status in AssignmentStatus}
    
    for row in assignment_rows:
        status = assignment_scraper._determine_status(row)
        assert status in AssignmentStatus
        status_counts[status] += 1
    
    # Verify we found the expected statuses in real data
    assert status_counts[AssignmentStatus.GRADED] > 0, "No graded assignments found"
    assert status_counts[AssignmentStatus.EXCUSED] > 0, "No excused assignments found"
    assert status_counts[AssignmentStatus.UNKNOWN] > 0, "No unknown status assignments found"
    
    # Print status distribution for debugging
    print("\nStatus distribution in real data:")
    for status, count in status_counts.items():
        print(f"{status.name}: {count}")

def test_determine_status_error_handling(assignment_scraper):
    """Test error handling in status determination."""
    # Test with invalid HTML
    invalid_html = "<tr><td>Invalid HTML</td></tr>"
    soup = BeautifulSoup(invalid_html, 'html.parser')
    row = soup.find("tr")
    status = assignment_scraper._determine_status(row)
    assert status == AssignmentStatus.UNKNOWN, "Invalid HTML should result in UNKNOWN status"
    
    # Test with None input
    status = assignment_scraper._determine_status(None)
    assert status == AssignmentStatus.UNKNOWN, "None input should result in UNKNOWN status"

def test_parse_score(assignment_scraper, real_grades_page):
    """Test parsing scores from grade cells."""
    soup = BeautifulSoup(real_grades_page, 'html.parser')
    score_cells = soup.find_all("td", class_="assignment_score")
    
    scores_found = False
    for cell in score_cells:
        score, max_score = assignment_scraper._parse_score(cell)
        
        if score is not None:
            scores_found = True
            assert isinstance(score, float)
            assert isinstance(max_score, float)
            assert score <= max_score
            
        # Test excused assignments
        if cell.find("span", class_="grade") and cell.find("span", class_="grade").text.strip() == "EX":
            assert score is None
            assert max_score is None
    
    assert scores_found, "No scores were found in the test data"

def test_extract_data_with_real_data(assignment_scraper, real_grades_page):
    """Test extracting all data from real HTML."""
    assignment_scraper.set_page_content(real_grades_page, "test_course_123")
    data = assignment_scraper.extract_data()
    
    # Verify we got data
    assert "assignments" in data
    assert len(data["assignments"]) > 0
    
    # Verify the structure of the first assignment
    first_assignment = data["assignments"][0]
    assert "name" in first_assignment
    assert "assignment_type" in first_assignment
    assert "due_date" in first_assignment
    assert "submitted_date" in first_assignment
    assert "status" in first_assignment
    assert "score" in first_assignment
    assert "max_score" in first_assignment
    assert "is_missing" in first_assignment
    
    # Verify data types
    assert isinstance(first_assignment["name"], str)
    assert isinstance(first_assignment["assignment_type"], AssignmentType)
    assert first_assignment["due_date"] is None or isinstance(first_assignment["due_date"], datetime)
    assert first_assignment["submitted_date"] is None or isinstance(first_assignment["submitted_date"], datetime)
    assert isinstance(first_assignment["status"], AssignmentStatus)
    assert first_assignment["score"] is None or isinstance(first_assignment["score"], float)
    assert first_assignment["max_score"] is None or isinstance(first_assignment["max_score"], float)
    assert isinstance(first_assignment["is_missing"], bool)
    
    # Verify is_missing flag is set correctly
    for assignment in data["assignments"]:
        assert assignment["is_missing"] == (assignment["status"] == AssignmentStatus.MISSING)

def test_extract_data_no_content(assignment_scraper):
    """Test extracting data without setting content."""
    with pytest.raises(ValueError):
        assignment_scraper.extract_data()

def test_extract_data_invalid_html(assignment_scraper):
    """Test extracting data from invalid HTML."""
    assignment_scraper.set_page_content("<html><body>No assignments here</body></html>", "test_course_123")
    data = assignment_scraper.extract_data()
    assert "assignments" in data
    assert len(data["assignments"]) == 0 