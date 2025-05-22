import os
import unittest
import sqlite3
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import sys
sys.path.append('frontend')
from page_generator import PageGenerator

class TestPageGenerator(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for output
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, 'output')
        self.template_dir = os.path.join(self.temp_dir, 'templates')
        
        # Create a temporary database
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Create test tables
        self.cursor.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                student_id INTEGER,
                name TEXT NOT NULL,
                grade TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY,
                course_id INTEGER,
                name TEXT NOT NULL,
                score TEXT,
                status TEXT,
                due_date TEXT,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE sync_info (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                status TEXT
            )
        ''')
        
        # Insert test data
        self.cursor.execute("INSERT INTO students (id, name) VALUES (1, 'Test Student')")
        self.cursor.execute("INSERT INTO courses (id, student_id, name, grade) VALUES (1, 1, 'Math', 'A')")
        self.cursor.execute("INSERT INTO courses (id, student_id, name, grade) VALUES (2, 1, 'Science', 'B')")
        self.cursor.execute("INSERT INTO assignments (id, course_id, name, score, status, due_date) VALUES (1, 1, 'Homework 1', '90', 'Submitted', '2023-05-15')")
        self.cursor.execute("INSERT INTO assignments (id, course_id, name, score, status, due_date) VALUES (2, 1, 'Homework 2', '85', 'Submitted', '2023-05-20')")
        self.cursor.execute("INSERT INTO assignments (id, course_id, name, score, status, due_date) VALUES (3, 2, 'Lab 1', NULL, 'missing', '2023-05-10')")
        self.cursor.execute("INSERT INTO sync_info (id, timestamp, status) VALUES (1, '2023-05-25T10:30:00', 'Success')")
        
        self.conn.commit()
        
        # Create test template directories
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(os.path.join(self.template_dir, 'static', 'css'), exist_ok=True)
        
        # Create test templates
        with open(os.path.join(self.template_dir, 'test.html'), 'w') as f:
            f.write('Test: {{ test_var }}')
            
        with open(os.path.join(self.template_dir, 'index.html'), 'w') as f:
            f.write('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ title }}</title>
            </head>
            <body>
                <h1>Student List</h1>
                <ul>
                {% for student in students %}
                    <li>{{ student.name }}</li>
                {% endfor %}
                </ul>
            </body>
            </html>
            ''')
            
        with open(os.path.join(self.template_dir, 'student.html'), 'w') as f:
            f.write('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ title }}</title>
            </head>
            <body>
                <h1>{{ student_name }}</h1>
                <ul>
                {% for course in courses %}
                    <li>{{ course.name }} - {{ course.grade }}</li>
                {% endfor %}
                </ul>
            </body>
            </html>
            ''')
            
        with open(os.path.join(self.template_dir, 'assignments.html'), 'w') as f:
            f.write('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Assignments</title>
            </head>
            <body>
                <div class="sync-info">
                    <p>Last Sync: {{ last_sync }}</p>
                </div>
                <h1>Assignments</h1>
                <ul>
                {% for assignment in assignments %}
                    <li>{{ assignment.name }} - {{ assignment.course_name }} - {{ assignment.status }}</li>
                {% endfor %}
                </ul>
            </body>
            </html>
            ''')
        
        # Create a simple CSS file
        with open(os.path.join(self.template_dir, 'static', 'css', 'test.css'), 'w') as f:
            f.write('body { color: black; }')
        
        # Create PageGenerator instance
        self.generator = PageGenerator(
            db_path=self.db_path,
            template_dir=self.template_dir,
            output_dir=self.output_dir
        )
    
    def tearDown(self):
        # Close database connection
        self.conn.close()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_get_students(self):
        students = self.generator.get_students()
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]['name'], 'Test Student')
    
    def test_get_courses_for_student(self):
        courses = self.generator.get_courses_for_student(1)
        self.assertEqual(len(courses), 2)
        self.assertEqual(courses[0]['name'], 'Math')
        self.assertEqual(courses[1]['name'], 'Science')
    
    def test_get_assignments_for_course(self):
        assignments = self.generator.get_assignments_for_course(1)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0]['name'], 'Homework 1')
        self.assertEqual(assignments[1]['name'], 'Homework 2')
    
    def test_get_all_assignments(self):
        # Test getting all assignments
        all_assignments = self.generator.get_all_assignments()
        self.assertEqual(len(all_assignments), 3)
        
        # Verify course names are included
        self.assertEqual(all_assignments[0]['course_name'], 'Math')
        self.assertEqual(all_assignments[2]['course_name'], 'Science')
        
        # Test filtering by student ID
        student_assignments = self.generator.get_all_assignments(1)
        self.assertEqual(len(student_assignments), 3)
    
    def test_get_last_sync_info(self):
        sync_info = self.generator.get_last_sync_info()
        self.assertEqual(sync_info['timestamp'], '2023-05-25T10:30:00')
        self.assertEqual(sync_info['status'], 'Success')
    
    def test_render_template(self):
        html = self.generator.render_template('test.html', {'test_var': 'Hello'})
        self.assertEqual(html, 'Test: Hello')
    
    def test_write_file(self):
        test_file = os.path.join(self.output_dir, 'test.txt')
        self.generator.write_file(test_file, 'Test content')
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        self.assertEqual(content, 'Test content')
    
    def test_copy_static_files(self):
        self.generator.copy_static_files()
        
        # Check if static files were copied
        css_path = os.path.join(self.output_dir, 'static', 'css', 'test.css')
        self.assertTrue(os.path.exists(css_path))
        
        with open(css_path, 'r') as f:
            content = f.read()
        
        self.assertEqual(content, 'body { color: black; }')
    
    def test_generate_index_page(self):
        # No mocking, test the actual method
        self.generator.generate_index_page()
        
        # Check if index.html was created
        index_path = os.path.join(self.output_dir, 'index.html')
        self.assertTrue(os.path.exists(index_path))
        
        # Check if the file contains expected content
        with open(index_path, 'r') as f:
            content = f.read()
        
        self.assertIn('Student List', content)
        self.assertIn('Test Student', content)
    
    def test_generate_student_page(self):
        # No mocking, test the actual method
        self.generator.generate_student_page(1, 'Test Student')
        
        # Check if student page was created
        student_path = os.path.join(self.output_dir, 'student_1', 'index.html')
        self.assertTrue(os.path.exists(student_path))
        
        # Check if the file contains expected content
        with open(student_path, 'r') as f:
            content = f.read()
        
        self.assertIn('Test Student', content)
        self.assertIn('Math - A', content)
    
    def test_generate_assignments_page(self):
        # Test generating assignments page for all students
        self.generator.generate_assignments_page()
        
        # Check if assignments.html was created
        assignments_path = os.path.join(self.output_dir, 'assignments.html')
        self.assertTrue(os.path.exists(assignments_path))
        
        # Check if the file contains expected content
        with open(assignments_path, 'r') as f:
            content = f.read()
        
        self.assertIn('Assignments', content)
        self.assertIn('Last Sync: 2023-05-25 10:30:00', content)
        self.assertNotIn('Sync Status:', content)  # Verify sync status is removed
        self.assertIn('Homework 1 - Math - Submitted', content)
        self.assertIn('Lab 1 - Science - missing', content)
        
        # Test generating assignments page for a specific student
        self.generator.generate_assignments_page(1)
        
        # Check if student-specific assignments.html was created
        student_assignments_path = os.path.join(self.output_dir, 'student_1', 'assignments.html')
        self.assertTrue(os.path.exists(student_assignments_path))
        
        # Check if the file contains expected content
        with open(student_assignments_path, 'r') as f:
            content = f.read()
        
        self.assertIn('Homework 1 - Math - Submitted', content)
        self.assertIn('Lab 1 - Science - missing', content)
    
    def test_generate_all_pages(self):
        # Create a stale file that should be removed
        stale_dir = os.path.join(self.output_dir, 'stale_directory')
        os.makedirs(stale_dir)
        stale_file = os.path.join(self.output_dir, 'stale.html')
        with open(stale_file, 'w') as f:
            f.write('Stale content')
            
        # No mocking, test the actual method
        self.generator.generate_all_pages()
        
        # Verify stale content was removed
        self.assertFalse(os.path.exists(stale_dir))
        self.assertFalse(os.path.exists(stale_file))
        
        # Check if index.html was created
        index_path = os.path.join(self.output_dir, 'index.html')
        self.assertTrue(os.path.exists(index_path))
        
        # Check if assignments.html was created
        assignments_path = os.path.join(self.output_dir, 'assignments.html')
        self.assertTrue(os.path.exists(assignments_path))
        
        # Check if student page was created
        student_path = os.path.join(self.output_dir, 'student_1', 'index.html')
        self.assertTrue(os.path.exists(student_path))
        
        # Check if student-specific assignments page was created
        student_assignments_path = os.path.join(self.output_dir, 'student_1', 'assignments.html')
        self.assertTrue(os.path.exists(student_assignments_path))
        
        # Check if static files were copied
        css_path = os.path.join(self.output_dir, 'static', 'css', 'test.css')
        self.assertTrue(os.path.exists(css_path))

if __name__ == '__main__':
    unittest.main() 