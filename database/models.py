from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .config import Base
import enum
from datetime import datetime

class AssignmentType(enum.Enum):
    HOMEWORK = "homework"
    PROJECT = "project"
    QUIZ = "quiz"
    WRITING = "writing"
    LAB = "lab"
    TEST = "test"
    OTHER = "other"

class AssignmentStatus(enum.Enum):
    SUBMITTED = "submitted"
    LATE = "late"
    MISSING = "missing"
    UPCOMING = "upcoming"
    GRADED = "graded"
    EXCUSED = "excused"
    UNKNOWN = "unknown"  # For assignments whose status cannot be determined

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    # Relationships
    courses = relationship("Course", back_populates="student")
    service_metadata = relationship("ServiceMetadata", back_populates="student")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    canvas_course_id = Column(String, nullable=False)  # Store the original Canvas course ID
    course_name = Column(String, nullable=False)
    
    # Overall Assignment/Homework metrics
    homework_percentage = Column(Float)
    homework_submitted = Column(Integer)
    homework_total = Column(Integer)
    
    # Overall Projects/Writing metrics
    projects_percentage = Column(Float)
    projects_submitted = Column(Integer)
    projects_total = Column(Integer)
    
    # Overall Quiz metrics
    quiz_percentage = Column(Float)
    quiz_submitted = Column(Integer)
    quiz_total = Column(Integer)
    
    # Relationships
    student = relationship("Student", back_populates="courses")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    course_grade = relationship("CourseGrade", back_populates="course", uselist=False, cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    
    assignment_type = Column(Enum(AssignmentType), nullable=False)
    name = Column(String, nullable=False)
    due_date = Column(DateTime)
    submitted_date = Column(DateTime)
    status = Column(Enum(AssignmentStatus), nullable=False)
    score = Column(Float)
    max_score = Column(Float)
    is_missing = Column(Boolean, default=False)
    
    # Relationships
    course = relationship("Course", back_populates="assignments")

class CourseGrade(Base):
    __tablename__ = "course_grades"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    
    percentage = Column(Float)
    letter_grade = Column(String)
    has_grade = Column(Boolean, default=False)
    raw_grade_text = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="course_grade")

class ServiceMetadata(Base):
    __tablename__ = "service_metadata"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    last_scraping_date = Column(DateTime, default=datetime.utcnow)
    last_scraping_status = Column(String)
    
    # Relationships
    student = relationship("Student", back_populates="service_metadata") 