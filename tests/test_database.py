import pytest
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session, sessionmaker
from database import init_db, get_db, Base, engine
from database.models import Student, Course, Assignment, ServiceMetadata, AssignmentType, AssignmentStatus
from database.config import SQLITE_DATABASE_URL

@pytest.fixture(scope="function")
def test_db():
    """
    Create a test database and tables.
    This fixture uses a temporary test database for each test function.
    """
    # Use an in-memory SQLite database for testing
    test_db_url = "sqlite:///:memory:"
    
    # Create a new engine for testing
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create and yield a test session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

def test_database_initialization():
    """Test that database initialization creates all necessary tables"""
    # Use in-memory database for testing
    test_db_url = "sqlite:///:memory:"
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables in the test engine
    Base.metadata.create_all(bind=test_engine)
    
    # Get all table names in the database
    inspector = inspect(test_engine)
    actual_tables = set(inspector.get_table_names())
    
    # Expected tables based on our models
    expected_tables = {
        'students',
        'courses',
        'assignments',
        'service_metadata'
    }
    
    assert actual_tables == expected_tables, f"Missing tables. Expected: {expected_tables}, Got: {actual_tables}"
    
    # Clean up
    Base.metadata.drop_all(bind=test_engine)

def test_database_session():
    """Test that we can create and use a database session"""
    # Get a database session
    db = next(get_db())
    
    try:
        # Verify we can perform a simple query
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1, "Database session is not working properly"
    finally:
        db.close()

def test_student_creation(test_db):
    """Test creating a student record"""
    # Create a test student
    test_student = Student(name="Test Student")
    test_db.add(test_student)
    test_db.commit()
    
    # Query the student back
    queried_student = test_db.query(Student).filter_by(name="Test Student").first()
    
    assert queried_student is not None, "Student was not created"
    assert queried_student.name == "Test Student"
    assert queried_student.id is not None, "Student ID was not generated"

def test_course_creation_with_student(test_db):
    """Test creating a course with an associated student"""
    # Create a test student
    student = Student(name="Test Student")
    test_db.add(student)
    test_db.commit()
    
    # Create a test course associated with the student
    course = Course(
        student_id=student.id,
        canvas_course_id="TEST101",
        course_name="Test Course",
        homework_percentage=85.5,
        homework_submitted=9,
        homework_total=10,
        projects_percentage=90.0,
        projects_submitted=2,
        projects_total=2,
        quiz_percentage=88.5,
        quiz_submitted=5,
        quiz_total=6
    )
    test_db.add(course)
    test_db.commit()
    
    # Query the course back
    queried_course = test_db.query(Course).filter_by(canvas_course_id="TEST101").first()
    
    assert queried_course is not None, "Course was not created"
    assert queried_course.student_id == student.id
    assert queried_course.course_name == "Test Course"
    assert queried_course.homework_percentage == 85.5
    assert queried_course.projects_percentage == 90.0
    assert queried_course.quiz_percentage == 88.5
    
    # Verify the relationship works
    assert queried_course.student.name == "Test Student"

def test_assignment_creation(test_db):
    """Test creating an assignment with all its fields"""
    # Create a test student and course first
    student = Student(name="Test Student")
    test_db.add(student)
    test_db.commit()
    
    course = Course(
        student_id=student.id,
        canvas_course_id="TEST101",
        course_name="Test Course"
    )
    test_db.add(course)
    test_db.commit()
    
    # Create a test assignment
    assignment = Assignment(
        course_id=course.id,
        assignment_type=AssignmentType.HOMEWORK,
        name="Test Assignment",
        status=AssignmentStatus.SUBMITTED,
        score=95.0,
        max_score=100.0,
        is_missing=False
    )
    test_db.add(assignment)
    test_db.commit()
    
    # Query the assignment back
    queried_assignment = test_db.query(Assignment).filter_by(name="Test Assignment").first()
    
    assert queried_assignment is not None, "Assignment was not created"
    assert queried_assignment.assignment_type == AssignmentType.HOMEWORK
    assert queried_assignment.status == AssignmentStatus.SUBMITTED
    assert queried_assignment.score == 95.0
    assert queried_assignment.max_score == 100.0
    assert not queried_assignment.is_missing
    
    # Verify relationships
    assert queried_assignment.course.course_name == "Test Course"
    assert queried_assignment.course.student.name == "Test Student"

def test_service_metadata_creation(test_db):
    """Test creating service metadata for a student"""
    # Create a test student
    student = Student(name="Test Student")
    test_db.add(student)
    test_db.commit()
    
    # Create service metadata
    metadata = ServiceMetadata(
        student_id=student.id,
        last_scraping_status="SUCCESS"
    )
    test_db.add(metadata)
    test_db.commit()
    
    # Query the metadata back
    queried_metadata = test_db.query(ServiceMetadata).filter_by(student_id=student.id).first()
    
    assert queried_metadata is not None, "Service metadata was not created"
    assert queried_metadata.last_scraping_status == "SUCCESS"
    assert queried_metadata.last_scraping_date is not None
    assert queried_metadata.student.name == "Test Student"

def test_database_url():
    """Test that the database URL is properly configured"""
    assert SQLITE_DATABASE_URL == "sqlite:///./canvas.db", "Database URL is not correctly configured"

def test_engine_configuration():
    """Test that the SQLAlchemy engine is properly configured"""
    assert engine.url.drivername == "sqlite", "Database engine should be SQLite"
    assert "check_same_thread" in engine.dialect.create_connect_args(engine.url)[1], "SQLite engine should have check_same_thread configuration" 