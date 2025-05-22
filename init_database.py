from database import init_db, get_db, Student
import logging

logger = logging.getLogger(__name__)

def init_student(config):
    """Initialize or get the student from the database based on config."""
    student_name = config.get('STUDENT')
    if not student_name:
        raise ValueError("STUDENT not found in config.ini")
        
    # Get database session
    db = next(get_db())
    
    # Check if student exists, create if not
    student = db.query(Student).filter(Student.name == student_name).first()
    if not student:
        student = Student(name=student_name)
        db.add(student)
        db.commit()
        logger.info(f"Created new student: {student_name}")
    else:
        logger.info(f"Found existing student: {student_name}")
        
    # Refresh the student object to ensure it's bound to the session
    db.refresh(student)
    return student

if __name__ == "__main__":
    print("Initializing the database...")
    init_db()
    print("Database initialized successfully!") 