import os
import sqlite3
import jinja2
import shutil
import datetime
from typing import Dict, Any, List, Optional

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
        self.env.filters['format_score'] = self._format_score
        
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
        
    def _format_score(self, score, max_score):
        """
        Format assignment score with American letter grade and percentage or fraction
        
        Args:
            score: Numeric score received (can be None)
            max_score: Maximum possible points (can be None)
            
        Returns:
            Formatted score string with letter grade and percentage/fraction
        """
        # If no score, return dash aligned with center dot position
        if score is None or max_score is None:
            return f'''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
        
        try:
            score = float(score)
            max_score = float(max_score)
            
            # Calculate percentage
            if max_score == 0:
                percentage = 0
            else:
                percentage = (score / max_score) * 100
            
            # Determine letter grade based on percentage
            if percentage >= 90:
                letter_grade = 'A'
                grade_class = 'grade-a'
            elif percentage >= 80:
                letter_grade = 'B'
                grade_class = 'grade-b'
            elif percentage >= 70:
                letter_grade = 'C'
                grade_class = 'grade-c'
            elif percentage >= 60:
                letter_grade = 'D'
                grade_class = 'grade-d'
            else:
                letter_grade = 'F'
                grade_class = 'grade-f'
            
            # For percentage-based grades (max_score = 100), display as "F • 50%"
            # For traditional scores, display as fraction "A • 18/20"
            if max_score == 100.0:
                # This is a percentage-based grade, display as percentage
                percentage_str = f"{score:g}%"  # :g removes trailing zeros
                score_display = percentage_str
            else:
                # Traditional fraction-based score
                score_str = f"{score:g}"  # :g removes trailing zeros
                max_score_str = f"{max_score:g}"
                score_display = f"{score_str}/{max_score_str}"
            
            return f'''<div class="score-container">
                <span class="letter-grade {grade_class} grade-letter">{letter_grade}</span>
                <span class="grade-separator">•</span>
                <span class="score-fraction grade-fraction">{score_display}</span>
            </div>'''
            
        except (ValueError, TypeError):
            return f'''<div class="score-container">
                <span class="grade-letter"></span>
                <span class="grade-separator">-</span>
                <span class="grade-fraction"></span>
            </div>'''
    
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
    

    
    def generate_assignments_page(self, student_id: int = None) -> None:
        """
        Generate a page showing all assignments across all courses
        
        Args:
            student_id: Optional student ID to filter assignments by
        """
        assignments = self.get_all_assignments(student_id)
        sync_info = self.get_last_sync_info()
        
        # Group assignments into sections
        assignment_sections = self._group_assignments_into_sections(assignments)
        
        # Format the sync timestamp if available
        last_sync = None
        if sync_info.get('timestamp'):
            try:
                timestamp = datetime.datetime.fromisoformat(sync_info['timestamp'])
                last_sync = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                last_sync = sync_info['timestamp']
        
        html_content = self.render_template('assignments.html', {
            'assignment_sections': assignment_sections,
            'last_sync': last_sync,
            'sync_status': sync_info.get('status')
        })
        
        # Determine output filename based on student filtering
        if student_id:
            output_path = os.path.join(self.output_dir, f'assignments_{student_id}.html')
        else:
            output_path = os.path.join(self.output_dir, 'assignments.html')
        
        self.write_file(output_path, html_content)
    
    def generate_grades_page(self, student_id: Optional[int] = None) -> None:
        """Generate the grades page for a specific student or all students.
        
        Args:
            student_id: Optional student ID to filter by. If None, shows all students.
        """
        # Get course grades from database
        course_grades = self.get_course_grades(student_id)
        
        # Get sync information
        sync_info = self.get_last_sync_info()
        
        # Calculate statistics
        total_courses = len(course_grades)
        courses_with_grades = len([c for c in course_grades if c.get('has_grade')])
        courses_without_grades = total_courses - courses_with_grades
        
        # Calculate average percentage
        grades_with_percentages = [c for c in course_grades if c.get('has_grade') and c.get('percentage') is not None]
        average_percentage = None
        if grades_with_percentages:
            total_percentage = sum(c['percentage'] for c in grades_with_percentages)
            average_percentage = total_percentage / len(grades_with_percentages)
        
        # Format the sync timestamp if available
        last_sync = None
        if sync_info.get('timestamp'):
            try:
                timestamp = datetime.datetime.fromisoformat(sync_info['timestamp'])
                last_sync = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                last_sync = sync_info['timestamp']
        
        html_content = self.render_template('grades.html', {
            'course_grades': course_grades,
            'total_courses': total_courses,
            'courses_with_grades': courses_with_grades,
            'courses_without_grades': courses_without_grades,
            'average_percentage': average_percentage,
            'last_sync': last_sync,
            'sync_status': sync_info.get('status')
        })
        
        # Determine output filename based on student filtering
        if student_id:
            output_path = os.path.join(self.output_dir, f'grades_{student_id}.html')
        else:
            output_path = os.path.join(self.output_dir, 'grades.html')
        
        self.write_file(output_path, html_content)
    
    def get_course_grades(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get course grades from the database.
        
        Args:
            student_id: Optional student ID to filter by. If None, gets all students.
            
        Returns:
            List of course grade dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            if student_id:
                # Get grades for specific student
                cursor = conn.execute("""
                    SELECT cg.percentage, cg.letter_grade, cg.has_grade, cg.raw_grade_text, 
                           cg.last_updated, c.course_name, c.canvas_course_id
                    FROM course_grades cg
                    JOIN courses c ON cg.course_id = c.id
                    WHERE c.student_id = ?
                    ORDER BY c.course_name
                """, (student_id,))
            else:
                # Get grades for all students
                cursor = conn.execute("""
                    SELECT cg.percentage, cg.letter_grade, cg.has_grade, cg.raw_grade_text, 
                           cg.last_updated, c.course_name, c.canvas_course_id
                    FROM course_grades cg
                    JOIN courses c ON cg.course_id = c.id
                    ORDER BY c.course_name
                """)
            
            grades = []
            for row in cursor.fetchall():
                grades.append({
                    'percentage': row['percentage'],
                    'letter_grade': row['letter_grade'],
                    'has_grade': bool(row['has_grade']),
                    'raw_grade_text': row['raw_grade_text'],
                    'last_updated': row['last_updated'],
                    'course_name': row['course_name'],
                    'canvas_course_id': row['canvas_course_id']
                })
            
            return grades
            
        finally:
            conn.close()
    
    def _group_assignments_into_sections(self, assignments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group assignments into sections based on their status and sort by due date
        
        Args:
            assignments: List of assignment dictionaries
            
        Returns:
            Dictionary with sections as keys and sorted assignment lists as values
        """
        upcoming = []
        graded = []
        missing = []
        unknown = []
        
        for assignment in assignments:
            status = assignment.get('status', 'UNKNOWN')
            
            # Categorize based on status
            if status in ['UPCOMING']:
                upcoming.append(assignment)
            elif status in ['GRADED', 'SUBMITTED', 'EXCUSED', 'LATE']:
                graded.append(assignment)
            elif status in ['MISSING']:
                missing.append(assignment)
            else:  # UNKNOWN and any other status
                unknown.append(assignment)
        
        # Sort each section by due date (with None dates last)
        def sort_key(assignment):
            due_date = assignment.get('due_date')
            if due_date is None:
                return (1, datetime.datetime.max)  # None dates go to the end
            try:
                parsed_date = datetime.datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                return (0, parsed_date)
            except (ValueError, TypeError, AttributeError):
                return (1, datetime.datetime.max)
        
        # Sort upcoming assignments by earliest due date first (soonest at top)
        upcoming.sort(key=sort_key, reverse=False)
        # Sort other sections by newest first
        graded.sort(key=sort_key, reverse=True)
        missing.sort(key=sort_key, reverse=True)
        unknown.sort(key=sort_key, reverse=True)
        
        return {
            'upcoming': {
                'title': 'Upcoming Assignments',
                'assignments': upcoming,
                'count': len(upcoming)
            },
            'graded': {
                'title': 'Graded Assignments',
                'assignments': graded,
                'count': len(graded)
            },
            'missing': {
                'title': 'Missing Assignments',
                'assignments': missing,
                'count': len(missing)
            },
            'unknown': {
                'title': 'Unknown Assignments',
                'assignments': unknown,
                'count': len(unknown)
            }
        }
    
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
        
        # Generate grades page (all students)
        self.generate_grades_page()
        
        # Generate individual assignment pages for each student
        students = self.get_students()
        for student in students:
            self.generate_assignments_page(student['id'])
            self.generate_grades_page(student['id'])
        
 