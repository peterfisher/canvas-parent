import unittest
import sqlite3
import os
import sys
sys.path.append('..')
from frontend.page_generator import PageGenerator


class TestDueDateFormatting(unittest.TestCase):
    """Test the due date formatting logic in PageGenerator"""
    
    def setUp(self):
        """Set up test database and PageGenerator"""
        self.test_db_path = 'test_canvas.db'
        self.generator = PageGenerator(
            db_path=self.test_db_path,
            template_dir='frontend/templates',
            output_dir='test_output'
        )
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_format_due_date_with_null_value(self):
        """Test that _format_due_date handles None values correctly"""
        result = self.generator._format_due_date(None, 'UNKNOWN')
        self.assertEqual(result, 'N/A')
        
    def test_format_due_date_with_empty_string(self):
        """Test that _format_due_date handles empty strings correctly"""
        result = self.generator._format_due_date('', 'UNKNOWN')
        self.assertEqual(result, 'N/A')
        
    def test_format_due_date_with_valid_date(self):
        """Test that _format_due_date handles valid dates correctly"""
        result = self.generator._format_due_date('2025-05-23 23:59:00.000000', 'GRADED')
        self.assertEqual(result, 'May 23, 2025')
        
    def test_format_due_date_with_upcoming_status(self):
        """Test that _format_due_date handles upcoming assignments correctly"""
        result = self.generator._format_due_date('2025-12-25 23:59:00.000000', 'UPCOMING')
        self.assertIn('December 25, 2025', result)
        self.assertIn('days left', result)
        
    def test_sql_order_by_with_null_dates(self):
        """Test how SQLite orders NULL due_date values with ORDER BY due_date DESC"""
        # Create a temporary test database
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute('''
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                course_name TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY,
                course_id INTEGER,
                name TEXT,
                due_date DATETIME,
                status TEXT,
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        ''')
        
        # Insert test data
        cursor.execute("INSERT INTO courses (id, course_name) VALUES (1, 'Test Course')")
        
        # Insert assignments with and without due dates
        cursor.execute("INSERT INTO assignments (course_id, name, due_date, status) VALUES (1, 'Assignment 1', '2025-05-23 23:59:00', 'GRADED')")
        cursor.execute("INSERT INTO assignments (course_id, name, due_date, status) VALUES (1, 'Assignment 2', '2025-05-24 23:59:00', 'UPCOMING')")
        cursor.execute("INSERT INTO assignments (course_id, name, due_date, status) VALUES (1, 'Assignment 3', NULL, 'UNKNOWN')")
        cursor.execute("INSERT INTO assignments (course_id, name, due_date, status) VALUES (1, 'Assignment 4', NULL, 'UNKNOWN')")
        cursor.execute("INSERT INTO assignments (course_id, name, due_date, status) VALUES (1, 'Assignment 5', '2025-05-22 23:59:00', 'GRADED')")
        
        conn.commit()
        
        # Test the ORDER BY due_date DESC query
        cursor.execute('''
            SELECT a.*, c.course_name 
            FROM assignments a
            JOIN courses c ON a.course_id = c.id
            ORDER BY a.due_date DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        # Print results to understand the actual ordering
        print("SQLite ORDER BY due_date DESC results:")
        for i, row in enumerate(results):
            print(f"  {i}: {row[2]} - due_date: {row[3]} - status: {row[4]}")
        
        # Check the order: Let's see what SQLite actually does
        self.assertEqual(len(results), 5)
        
        # SQLite orders NULL values LAST in DESC order, not first
        # So the order should be: non-NULL dates in DESC order, then NULL dates
        self.assertEqual(results[0][2], 'Assignment 2')  # 2025-05-24 (highest date)
        self.assertEqual(results[1][2], 'Assignment 1')  # 2025-05-23
        self.assertEqual(results[2][2], 'Assignment 5')  # 2025-05-22 (lowest date)
        self.assertIsNone(results[3][3])  # NULL due_date
        self.assertIsNone(results[4][3])  # NULL due_date


if __name__ == '__main__':
    unittest.main() 