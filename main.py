#!/usr/bin/env python3

import logging
from load_config import load_config
from login import login_to_canvas
from canvas_session_manager import create_grade_scraper

from datetime import datetime
from init_database import init_student
from database import get_db, init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = None
    try:
        # Initialize database tables if they don't exist
        init_db()
        logger.info("Database tables initialized")
        
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Get database session
        db = next(get_db())
        
        # Initialize student
        student = init_student(config)
        logger.info(f"Using student ID: {student.id}")
        
        # Login to Canvas and get session
        canvas_session = login_to_canvas(config)
        logger.info("Successfully logged into Canvas")
        
        # Create and configure grade scraper
        scraper = create_grade_scraper(canvas_session.session, student.id)
        logger.info("Grade scraper initialized")
        
        # Start scraping process
        start_time = datetime.utcnow()
        result = scraper.scrape_all_courses()
        
        # Calculate and log duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Scraping completed in {duration:.1f} seconds")
        logger.info(f"Scraping result: {result.status}")
        
        # Print course statistics
        logger.info(f"\n=== Course Statistics ===")
        logger.info(f"Student: {result.student_name}")
        logger.info(f"Total courses: {result.total_courses}")
        for course_name, assignment_count in result.course_assignments.items():
            logger.info(f"Course '{course_name}': {assignment_count} assignments")
        logger.info("=====================\n")
        

        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return 1
    finally:
        if db:
            db.close()
    
    return 0

if __name__ == "__main__":
    exit(main()) 