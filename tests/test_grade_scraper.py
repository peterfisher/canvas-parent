import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from datetime import datetime
import os
from grade_scraper import GradeScraper, create_grade_scraper, ScrapingResult
from database.models import Student
from scrappers import AssignmentScraper

def load_test_data(filename):
    """Load test data from the test_data directory."""
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    with open(os.path.join(test_data_dir, filename), 'r') as f:
        return f.read()

@pytest.fixture
def mock_session():
    """Create a mock requests session with required cookies."""
    session = Mock(spec=requests.Session)
    cookie = Mock()
    cookie.name = '_csrf_token'
    cookie.domain = 'test.instructure.com'
    session.cookies = [cookie]
    return session

@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    manager = Mock()
    # Setup basic student return
    student = Mock()
    student.name = "Test Student"
    manager.get_student.return_value = student
    return manager

@pytest.fixture
def grade_scraper(mock_session, mock_db_manager, monkeypatch):
    """Create a GradeScraper instance with mocked dependencies."""
    # Mock the database session creation
    mock_db = Mock()
    monkeypatch.setattr("grade_scraper.get_db", lambda: iter([mock_db]))
    
    # Create scraper instance
    scraper = GradeScraper(mock_session, student_id=1)
    scraper.db_manager = mock_db_manager
    return scraper

def test_grade_scraper_initialization(mock_session):
    """Test GradeScraper initialization with valid session."""
    scraper = GradeScraper(mock_session, student_id=1)
    assert scraper.base_url == "https://test.instructure.com"
    assert scraper.student_id == 1

def test_grade_scraper_initialization_invalid_session():
    """Test GradeScraper initialization with invalid session."""
    invalid_session = Mock(spec=requests.Session)
    invalid_session.cookies = []
    
    with pytest.raises(ValueError, match="Could not determine base URL from session cookies"):
        GradeScraper(invalid_session, student_id=1)

def test_grade_scraper_invalid_student(mock_session, mock_db_manager):
    """Test GradeScraper initialization with invalid student ID."""
    mock_db_manager.get_student.return_value = None
    
    with patch("grade_scraper.DatabaseManager", return_value=mock_db_manager):
        with pytest.raises(ValueError, match="Student with ID 999 not found in database"):
            GradeScraper(mock_session, student_id=999)

def test_register_scraper(grade_scraper):
    """Test registering a scraper."""
    class TestScraper:
        pass
    
    grade_scraper.register_scraper(TestScraper)
    assert len(grade_scraper.scrapers) == 1
    assert isinstance(grade_scraper.scrapers[0], TestScraper)

def test_get_course_ids_and_names(grade_scraper):
    """Test retrieving course IDs and names using real test data."""
    # Load real test data
    test_html = load_test_data('real_grades_page.html')
    
    # Extract course info from the test data
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "id": "102017",
            "name": "8th Grade History-Wooten"
        },
        {
            "id": "101745",
            "name": "English 8 Chapa"
        }
    ]
    grade_scraper.session.get.return_value = mock_response
    
    courses = grade_scraper.get_course_ids_and_names()
    
    assert len(courses) == 2
    assert courses[0] == {"id": "102017", "name": "8th Grade History-Wooten"}
    assert courses[1] == {"id": "101745", "name": "English 8 Chapa"}
    grade_scraper.session.get.assert_called_once_with(
        'https://test.instructure.com/api/v1/courses',
        params={'enrollment_state': 'active'}
    )

def test_get_grades_page(grade_scraper):
    """Test retrieving grades page for a course."""
    mock_response = Mock()
    mock_response.text = "<html>Test content</html>"
    grade_scraper.session.get.return_value = mock_response
    
    content = grade_scraper.get_grades_page("123")
    
    assert content == "<html>Test content</html>"
    grade_scraper.session.get.assert_called_once_with(
        'https://test.instructure.com/courses/123/grades'
    )

def test_scrape_course_success(grade_scraper):
    """Test successful course scraping with real test data."""
    # Load real test data
    test_html = load_test_data('real_grades_page.html')
    
    # Mock the grades page response
    mock_response = Mock()
    mock_response.text = test_html
    grade_scraper.session.get.return_value = mock_response
    
    # Register a mock scraper
    mock_scraper = Mock(spec=AssignmentScraper)
    mock_scraper.scrape.return_value = {
        "assignments": [
            {
                "name": "8th Grade History-Wooten",
                "score": 80.0,
                "points_possible": 100.0,
                "due_at": "2025-04-16T08:00:00-07:00",
                "status": "graded"
            }
        ]
    }
    grade_scraper.scrapers = [mock_scraper]
    
    result = grade_scraper.scrape_course("102017", "8th Grade History-Wooten")
    
    assert result is True
    mock_scraper.set_page_content.assert_called_once_with(test_html, "102017")
    grade_scraper.db_manager.save_assignments.assert_called_once_with(
        [
            {
                "name": "8th Grade History-Wooten",
                "score": 80.0,
                "points_possible": 100.0,
                "due_at": "2025-04-16T08:00:00-07:00",
                "status": "graded"
            }
        ],
        "102017",
        grade_scraper.student_id,
        "8th Grade History-Wooten"
    )

def test_scrape_course_failure(grade_scraper):
    """Test course scraping with failure."""
    grade_scraper.session.get.side_effect = requests.RequestException("Network error")
    
    result = grade_scraper.scrape_course("123", "Test Course")
    
    assert result is False

def test_scrape_all_courses_success(grade_scraper):
    """Test successful scraping of all courses using real test data."""
    # Load real test data
    test_html = load_test_data('real_grades_page.html')
    
    # Mock course retrieval
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "id": "102017",
            "name": "8th Grade History-Wooten"
        },
        {
            "id": "101745",
            "name": "English 8 Chapa"
        }
    ]
    mock_response.text = test_html
    grade_scraper.session.get.return_value = mock_response
    
    # Mock successful course scraping
    with patch.object(grade_scraper, 'scrape_course', return_value=True):
        # Mock course assignment counting
        grade_scraper.db_manager.get_or_create_course.return_value = Mock(id=1)
        grade_scraper.db_manager.count_course_assignments.return_value = 12  # Real number from test data
        
        result = grade_scraper.scrape_all_courses()
        
        assert isinstance(result, ScrapingResult)
        assert result.total_courses == 2
        assert result.successful_courses == 2
        assert result.failed_courses == 0
        assert result.student_name == "Test Student"
        assert result.course_assignments == {
            "8th Grade History-Wooten": 12,
            "English 8 Chapa": 12
        }
        assert "Success rate: 100.0%" in result.status

def test_scrape_all_courses_no_courses(grade_scraper):
    """Test scraping when no courses are found."""
    # Mock empty course list
    mock_response = Mock()
    mock_response.json.return_value = []
    grade_scraper.session.get.return_value = mock_response
    
    result = grade_scraper.scrape_all_courses()
    
    assert isinstance(result, ScrapingResult)
    assert result.total_courses == 0
    assert result.status == "No courses found to scrape"

def test_scrape_all_courses_partial_failure(grade_scraper):
    """Test scraping with some course failures."""
    # Mock course retrieval
    mock_response = Mock()
    mock_response.json.return_value = [
        {"id": 1, "name": "Course 1"},
        {"id": 2, "name": "Course 2"}
    ]
    grade_scraper.session.get.return_value = mock_response
    
    # Create a new mock for scrape_course method
    with patch.object(grade_scraper, 'scrape_course', side_effect=[True, False]) as mock_scrape:
        # Mock course assignment counting
        grade_scraper.db_manager.get_or_create_course.return_value = Mock(id=1)
        grade_scraper.db_manager.count_course_assignments.return_value = 5
        
        result = grade_scraper.scrape_all_courses()
        
        assert isinstance(result, ScrapingResult)
        assert result.total_courses == 2
        assert result.successful_courses == 1
        assert result.failed_courses == 1
        assert "Success rate: 50.0%" in result.status

def test_scrape_all_courses_critical_error(grade_scraper):
    """Test handling of critical errors during scraping."""
    # Mock course retrieval to raise an exception
    mock_response = Mock()
    mock_response.json.side_effect = Exception("Critical error")
    grade_scraper.session.get.return_value = mock_response
    
    with pytest.raises(Exception, match="Critical error"):
        result = grade_scraper.scrape_all_courses()
        
        # Even though we're raising, we should still save metadata
        grade_scraper.db_manager.save_scraping_metadata.assert_called_once()
        metadata = grade_scraper.db_manager.save_scraping_metadata.call_args[0][0]
        assert metadata["total_courses"] == 0
        assert metadata["successful_courses"] == 0
        assert metadata["failed_courses"] == 0
        assert "Critical error during scraping: Critical error" in metadata["status"]

def test_create_grade_scraper_factory():
    """Test the create_grade_scraper factory function."""
    mock_session = Mock(spec=requests.Session)
    cookie = Mock()
    cookie.name = '_csrf_token'
    cookie.domain = 'test.instructure.com'
    mock_session.cookies = [cookie]
    
    scraper = create_grade_scraper(mock_session, student_id=1)
    
    assert isinstance(scraper, GradeScraper)
    assert len(scraper.scrapers) == 1
    assert isinstance(scraper.scrapers[0], AssignmentScraper) 