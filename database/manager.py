from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .models import Assignment, ServiceMetadata, Student, Course
from datetime import datetime

class DatabaseManager:
    """Manages database operations for the Canvas scraper."""
    
    def __init__(self, db_session: Session):
        """Initialize the database manager.
        
        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db_session = db_session
    
    def get_or_create_course(self, canvas_course_id: str, student_id: int, course_name: str) -> Course:
        """Get an existing course or create a new one.
        
        Args:
            canvas_course_id: Canvas course ID
            student_id: Database student ID
            course_name: Name of the course
            
        Returns:
            Course object from database
        """
        course = self.db_session.query(Course).filter(
            Course.student_id == student_id,
            Course.canvas_course_id == canvas_course_id
        ).first()
        
        if not course:
            course = Course(
                student_id=student_id,
                canvas_course_id=canvas_course_id,
                course_name=course_name
            )
            self.db_session.add(course)
            self.db_session.commit()
        
        return course
    
    def get_student(self, student_id: int) -> Optional[Student]:
        """Get a student by ID.
        
        Args:
            student_id: Database student ID
            
        Returns:
            Student object if found, None otherwise
        """
        return self.db_session.query(Student).filter(Student.id == student_id).first()
    
    def count_course_assignments(self, course_id: int) -> int:
        """Count the number of assignments for a course.
        
        Args:
            course_id: Database course ID
            
        Returns:
            Number of assignments in the course
        """
        return self.db_session.query(Assignment).filter(Assignment.course_id == course_id).count()
    
    def save_assignments(self, assignments_data: List[Dict[str, Any]], canvas_course_id: str, student_id: int, course_name: str) -> None:
        """Save assignment data to the database.
        
        Args:
            assignments_data: List of dictionaries containing assignment data
            canvas_course_id: Canvas course ID
            student_id: Database student ID
            course_name: Name of the course
        """
        # Get or create the course
        course = self.get_or_create_course(canvas_course_id, student_id, course_name)
        
        # Delete existing assignments for this course to avoid duplicates
        self.db_session.query(Assignment).filter(Assignment.course_id == course.id).delete()
        
        # Add new assignments
        for assignment_data in assignments_data:
            assignment = Assignment(
                course_id=course.id,  # Use our database course ID
                **assignment_data
            )
            self.db_session.add(assignment)
        
        self.db_session.commit()
    
    def save_scraping_metadata(self, result: Dict[str, Any], student_id: int) -> None:
        """Save metadata about the scraping execution.
        
        Args:
            result: Dictionary containing execution statistics and status
            student_id: Database student ID
        """
        metadata = ServiceMetadata(
            student_id=student_id,
            last_scraping_date=datetime.utcnow(),
            last_scraping_status=result["status"]
        )
        self.db_session.add(metadata)
        self.db_session.commit()
    
    def get_latest_scraping_metadata(self, student_id: int) -> Optional[ServiceMetadata]:
        """Get the most recent scraping metadata for a student.
        
        Args:
            student_id: Database student ID
            
        Returns:
            Most recent ServiceMetadata entry for the student
        """
        return self.db_session.query(ServiceMetadata).filter(
            ServiceMetadata.student_id == student_id
        ).order_by(
            ServiceMetadata.last_scraping_date.desc()
        ).first() 