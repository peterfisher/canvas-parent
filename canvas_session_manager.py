#!/usr/bin/env python3

import requests
from typing import List, Type, Dict, Optional
from database import get_db
from scrappers import BaseScraper, AssignmentScraper
from database.manager import DatabaseManager
from datetime import datetime
import logging
from urllib.parse import urljoin
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Container for scraping results and metadata."""
    total_courses: int
    successful_courses: int
    failed_courses: int
    duration_seconds: float
    status: str
    student_name: str
    course_assignments: Dict[str, int]  # Dictionary of course_name: assignment_count

class GradeScraper:
    """Main scraper class that coordinates the scraping process for Canvas grades."""
    
    def __init__(self, session: requests.Session, student_id: int):
        """Initialize the grade scraper.
        
        Args:
            session: Authenticated requests session for Canvas
            student_id: Database ID of the student being scraped
        """
        self.session = session
        self.student_id = student_id
        self.scrapers: List[BaseScraper] = []
        self.db_manager = DatabaseManager(next(get_db()))
        
        # Verify student exists
        if not self.db_manager.get_student(student_id):
            raise ValueError(f"Student with ID {student_id} not found in database")
        
        # Extract base URL from the session's cookies
        cookie_domain = next((c.domain for c in session.cookies if c.name == '_csrf_token'), None)
        if cookie_domain:
            self.base_url = f"https://{cookie_domain}"
        else:
            raise ValueError("Could not determine base URL from session cookies")
    
    def register_scraper(self, scraper_class: Type[BaseScraper]) -> None:
        """Register a scraper to be used during the scraping process.
        
        Args:
            scraper_class: Class of the scraper to register
        """
        scraper = scraper_class()
        self.scrapers.append(scraper)
    
    def get_course_ids_and_names(self) -> List[Dict[str, str]]:
        """Retrieve all active course IDs and names from Canvas.
        
        Returns:
            List of dictionaries containing course IDs and names
        
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        courses_url = urljoin(self.base_url, '/api/v1/courses')
        response = self.session.get(
            courses_url,
            params={'enrollment_state': 'active'}
        )
        response.raise_for_status()
        
        courses: List[Dict] = response.json()
        course_info = [
            {"id": str(course['id']), "name": course['name']}
            for course in courses
            if 'id' in course and 'name' in course
        ]
        
        logger.info(f"Retrieved {len(course_info)} active courses from Canvas")
        return course_info
    
    def get_grades_page(self, course_id: str) -> str:
        """Download the grades page for a course.
        
        Args:
            course_id: Canvas course ID
        
        Returns:
            HTML content of the grades page
        """
        url = f"{self.base_url}/courses/{course_id}/grades"
        response = self.session.get(url)
        response.raise_for_status()
        return response.text
    
    def get_dashboard_page(self) -> str:
        """Download the Canvas dashboard page.
        
        Returns:
            HTML content of the dashboard page
        """
        url = f"{self.base_url}/dashboard"
        response = self.session.get(url)
        response.raise_for_status()
        return response.text
    
    def scrape_course(self, course_id: str, course_name: str) -> bool:
        """Scrape data for a single course.
        
        Args:
            course_id: Canvas course ID
            course_name: Name of the course
            
        Returns:
            bool: True if scraping was successful, False otherwise
        """
        try:
            # Get the grades page content
            html_content = self.get_grades_page(course_id)
            
            # Run each registered scraper on the page content
            for scraper in self.scrapers:
                scraper.set_page_content(html_content, course_id)
                data = scraper.scrape()
                
                # Save the scraped data using the database manager
                if isinstance(scraper, AssignmentScraper):
                    self.db_manager.save_assignments(
                        data["assignments"],
                        course_id,
                        self.student_id,
                        course_name
                    )
            
            # Also run the grade scraper to extract course grades
            from scrappers import GradeScraper
            grade_scraper = GradeScraper()
            grade_scraper.set_page_content(html_content, course_id)
            grade_data = grade_scraper.scrape()
            
            # Save course grade if available
            if grade_data.get("has_course_grade") and grade_data.get("course_grade") is not None:
                course_grade_data = {
                    "course_id": course_id,
                    "course_name": course_name,
                    "percentage": grade_data.get("course_grade"),
                    "letter_grade": grade_data.get("course_letter_grade"),
                    "has_grade": grade_data.get("has_course_grade", False),
                    "raw_grade_text": f"Total: {grade_data.get('course_grade', 'N/A')}% ({grade_data.get('course_letter_grade', 'N/A')})"
                }
                self.db_manager.save_course_grades([course_grade_data], self.student_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error scraping course {course_id}: {str(e)}")
            return False
    

    
    def scrape_all_courses(self) -> ScrapingResult:
        """Main method to scrape all courses.
        
        Returns:
            ScrapingResult containing execution statistics
        """
        start_time = datetime.utcnow()
        total_courses = 0
        failed_courses = 0
        course_assignments = {}
        
        try:
            # Get student name
            student = self.db_manager.get_student(self.student_id)
            student_name = student.name if student else "Unknown"
            

            
            courses = self.get_course_ids_and_names()
            total_courses = len(courses)
            
            if not courses:
                result = ScrapingResult(
                    total_courses=0,
                    successful_courses=0,
                    failed_courses=0,
                    duration_seconds=0,
                    status="No courses found to scrape",
                    student_name=student_name,
                    course_assignments={}
                )
                self.db_manager.save_scraping_metadata(result.__dict__, self.student_id)
                return result
            
            for course in courses:
                if not self.scrape_course(course["id"], course["name"]):
                    failed_courses += 1
                else:
                    # Count assignments for this course
                    db_course = self.db_manager.get_or_create_course(course["id"], self.student_id, course["name"])
                    assignment_count = self.db_manager.count_course_assignments(db_course.id)
                    course_assignments[course["name"]] = assignment_count
            
            # Calculate statistics
            successful_courses = total_courses - failed_courses
            duration = (datetime.utcnow() - start_time).total_seconds()
            success_rate = (successful_courses / total_courses) * 100 if total_courses > 0 else 0
            
            status = (
                f"Scraping completed. "
                f"Processed {total_courses} courses in {duration:.1f} seconds. "
                f"Success rate: {success_rate:.1f}% "
                f"({successful_courses}/{total_courses} courses successful)"
            )
            
            result = ScrapingResult(
                total_courses=total_courses,
                successful_courses=successful_courses,
                failed_courses=failed_courses,
                duration_seconds=duration,
                status=status,
                student_name=student_name,
                course_assignments=course_assignments
            )
            
            self.db_manager.save_scraping_metadata(result.__dict__, self.student_id)
            return result
            
        except Exception as e:
            error_msg = f"Critical error during scraping: {str(e)}"
            logger.error(error_msg)
            
            result = ScrapingResult(
                total_courses=total_courses,
                successful_courses=0,
                failed_courses=total_courses,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                status=error_msg,
                student_name=student_name,
                course_assignments={}
            )
            
            self.db_manager.save_scraping_metadata(result.__dict__, self.student_id)
            raise

def create_grade_scraper(session: requests.Session, student_id: int) -> GradeScraper:
    """Create and configure a GradeScraper instance.
    
    Args:
        session: Authenticated requests session for Canvas
        student_id: Database ID of the student being scraped
    
    Returns:
        Configured GradeScraper instance
    """
    scraper = GradeScraper(session, student_id)
    
    # Register scrapers
    scraper.register_scraper(AssignmentScraper)
    
    return scraper 