from .config import Base, engine, get_db
from .models import Student, Course, Assignment, ServiceMetadata, AssignmentType, AssignmentStatus

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Export all models and database utilities
__all__ = [
    'init_db',
    'get_db',
    'Student',
    'Course',
    'Assignment',
    'ServiceMetadata',
    'AssignmentType',
    'AssignmentStatus'
] 