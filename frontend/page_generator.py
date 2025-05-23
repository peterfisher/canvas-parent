import os
import sqlite3
import jinja2
import shutil
import datetime
from typing import Dict, Any, List

class PageGenerator:
    """
    Generates static HTML/JS pages from templates and database data
    """
    
    def __init__(self, db_path: str, template_dir: str, output_dir: str):
        """
        Initialize the page generator
        
        Args:
            db_path: Path to the SQLite database
            template_dir: Directory containing templates
            output_dir: Directory where output files will be written
        """
        self.db_path = db_path
        self.template_dir = template_dir
        self.output_dir = output_dir
        
        # Set up the template environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['default'] = self._default_filter
        self.env.filters['format_due_date'] = self._format_due_date
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def _default_filter(self, value, default_value='', boolean=False):
        """Custom default filter for Jinja2 templates"""
        return default_value if not value else value
    
    def _format_due_date(self, due_date_str, status):
        """
        Format due date with specific formatting and days remaining for upcoming assignments
        
        Args:
            due_date_str: ISO format date string from database
            status: Assignment status (UPCOMING, etc.)
            
        Returns:
            Formatted date string
        """
        if not due_date_str:
            return 'N/A'
        
        try:
            # Parse the date string from the database
            due_date = datetime.datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            now = datetime.datetime.now()
            
            # Format base date as "Month Day, Year"
            formatted_date = due_date.strftime("%B %d, %Y")
            
            # For upcoming assignments, add days remaining
            if status == 'UPCOMING' and due_date > now:
                days_remaining = (due_date.date() - now.date()).days
                if days_remaining == 0:
                    days_text = "due today"
                elif days_remaining == 1:
                    days_text = "1 day left"
                else:
                    days_text = f"{days_remaining} days left"
                
                return f"{formatted_date} ({days_text})"
            else:
                return formatted_date
                
        except (ValueError, TypeError, AttributeError):
            return due_date_str or 'N/A'
        
    def get_db_connection(self) -> sqlite3.Connection:
        """Get a connection to the database"""
        return sqlite3.connect(self.db_path)
    
    def get_students(self) -> List[Dict[str, Any]]:
        """Get list of all students from database"""
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM students")
        students = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return students
    
    def get_courses_for_student(self, student_id: int) -> List[Dict[str, Any]]:
        """Get all courses for a student"""
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM courses WHERE student_id = ?",
            (student_id,)
        )
        courses = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return courses
    
    def get_assignments_for_course(self, course_id: int) -> List[Dict[str, Any]]:
        """Get all assignments for a course"""
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM assignments WHERE course_id = ?",
            (course_id,)
        )
        assignments = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return assignments
    
    def get_all_assignments(self, student_id: int = None) -> List[Dict[str, Any]]:
        """
        Get all assignments across all courses, optionally filtered by student_id
        
        Returns enriched assignment data with course_name included
        """
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if course_name column exists in courses table
        cursor.execute("PRAGMA table_info(courses)")
        columns = [info[1] for info in cursor.fetchall()]
        course_name_col = "course_name" if "course_name" in columns else "name"
        
        if student_id:
            cursor.execute(f"""
                SELECT a.*, c.{course_name_col} as course_name 
                FROM assignments a
                JOIN courses c ON a.course_id = c.id
                JOIN students s ON c.student_id = s.id
                WHERE s.id = ?
                ORDER BY a.due_date DESC
            """, (student_id,))
        else:
            cursor.execute(f"""
                SELECT a.*, c.{course_name_col} as course_name 
                FROM assignments a
                JOIN courses c ON a.course_id = c.id
                ORDER BY a.due_date DESC
            """)
            
        assignments = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return assignments
    
    def get_last_sync_info(self) -> Dict[str, Any]:
        """Get information about the last sync from the database"""
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if service_metadata table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_metadata'")
        if cursor.fetchone():
            cursor.execute("SELECT last_scraping_date as timestamp, last_scraping_status as status FROM service_metadata ORDER BY last_scraping_date DESC LIMIT 1")
        else:
            cursor.execute("SELECT timestamp, status FROM sync_info ORDER BY id DESC LIMIT 1")
            
        sync_info = cursor.fetchone()
        
        conn.close()
        
        if sync_info:
            return dict(sync_info)
        else:
            # Return default values if no sync info is found
            return {
                'timestamp': None,
                'status': 'Unknown'
            }
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context
        
        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to the template
            
        Returns:
            Rendered HTML content
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def write_file(self, path: str, content: str) -> None:
        """Write content to a file"""
        with open(path, 'w') as f:
            f.write(content)
    
    def copy_static_files(self) -> None:
        """Copy static files (CSS, JS, images) to output directory"""
        static_dir = os.path.join(self.template_dir, 'static')
        output_static_dir = os.path.join(self.output_dir, 'static')
        
        if os.path.exists(static_dir):
            # Create output static directory if it doesn't exist
            os.makedirs(output_static_dir, exist_ok=True)
            
            # Copy all files from static directory
            for item in os.listdir(static_dir):
                src = os.path.join(static_dir, item)
                dst = os.path.join(output_static_dir, item)
                
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
    
    def generate_index_page(self) -> None:
        """Generate the main index page with links to student pages"""
        students = self.get_students()
        
        html_content = self.render_template('index.html', {
            'students': students,
            'title': 'Student Scorecards'
        })
        
        self.write_file(os.path.join(self.output_dir, 'index.html'), html_content)
    
    def generate_student_page(self, student_id: int, student_name: str) -> None:
        """Generate a page for a specific student"""
        courses = self.get_courses_for_student(student_id)
        
        # Get assignments for each course
        for course in courses:
            course['assignments'] = self.get_assignments_for_course(course['id'])
        
        html_content = self.render_template('student.html', {
            'student_id': student_id,
            'student_name': student_name,
            'courses': courses,
            'title': f'Scorecard for {student_name}'
        })
        
        # Create student directory
        student_dir = os.path.join(self.output_dir, f'student_{student_id}')
        os.makedirs(student_dir, exist_ok=True)
        
        self.write_file(os.path.join(student_dir, 'index.html'), html_content)
    
    def generate_assignments_page(self, student_id: int = None) -> None:
        """
        Generate a page showing all assignments across all courses
        
        Args:
            student_id: Optional student ID to filter assignments by
        """
        assignments = self.get_all_assignments(student_id)
        sync_info = self.get_last_sync_info()
        
        # Format the sync timestamp if available
        last_sync = None
        if sync_info.get('timestamp'):
            try:
                timestamp = datetime.datetime.fromisoformat(sync_info['timestamp'])
                last_sync = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                last_sync = sync_info['timestamp']
        
        html_content = self.render_template('assignments.html', {
            'assignments': assignments,
            'last_sync': last_sync,
            'sync_status': sync_info.get('status')
        })
        
        # Determine output path based on whether we're filtering by student
        if student_id:
            # Create student directory
            student_dir = os.path.join(self.output_dir, f'student_{student_id}')
            os.makedirs(student_dir, exist_ok=True)
            output_path = os.path.join(student_dir, 'assignments.html')
        else:
            output_path = os.path.join(self.output_dir, 'assignments.html')
        
        self.write_file(output_path, html_content)
    
    def generate_all_pages(self) -> None:
        """Generate all pages for the website"""
        # Clean up existing website directory
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)
        
        # Copy static files first
        self.copy_static_files()
        
        # Generate main index page
        self.generate_index_page()
        
        # Generate assignments page (all students)
        self.generate_assignments_page()
        
        # Generate student pages
        students = self.get_students()
        for student in students:
            self.generate_student_page(student['id'], student['name'])
            
            # Generate assignments page for this student
            self.generate_assignments_page(student['id']) 