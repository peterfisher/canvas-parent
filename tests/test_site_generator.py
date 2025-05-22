import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.generate_site import SiteGenerator


class TestSiteGenerator(unittest.TestCase):
    """Test cases for the SiteGenerator class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for output
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock the file system paths
        self.templates_dir_patcher = patch('os.path.join')
        self.mock_path_join = self.templates_dir_patcher.start()
        
        # Return the temp directory for output dir
        def mock_join(dirname, *args):
            if args[0] == 'website':
                return self.temp_dir
            elif args[0] == 'templates':
                return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   'frontend', 'templates')
            elif args[0] == 'static':
                return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   'frontend', 'static')
            else:
                return os.path.join(dirname, *args)
        
        self.mock_path_join.side_effect = mock_join
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
        
        # Stop the patchers
        self.templates_dir_patcher.stop()
    
    @patch('frontend.generate_site.Environment')
    @patch('frontend.generate_site.FileSystemLoader')
    def test_init(self, mock_file_loader, mock_env):
        """Test initialization of SiteGenerator."""
        generator = SiteGenerator()
        
        # Check that the environment is set up correctly
        mock_file_loader.assert_called_once()
        mock_env.assert_called_once_with(loader=mock_file_loader.return_value)
        
        # Check that the output directory exists
        self.assertTrue(os.path.exists(self.temp_dir))
    
    @patch('frontend.generate_site.Environment')
    @patch('frontend.generate_site.FileSystemLoader')
    @patch('frontend.generate_site.get_db')
    def test_generate_index_page(self, mock_get_db, mock_file_loader, mock_env):
        """Test generation of index page."""
        # Mock the database session
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock the template
        mock_template = MagicMock()
        mock_env.return_value.get_template.return_value = mock_template
        
        # Mock the students
        student1 = MagicMock()
        student1.id = 1
        student1.name = "Test Student 1"
        
        student2 = MagicMock()
        student2.id = 2
        student2.name = "Test Student 2"
        
        students = [student1, student2]
        
        # Mock courses and assignments
        course = MagicMock()
        course.id = 1
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [course],  # Courses for student 1
            [],  # Assignments for course 1
            [],  # Courses for student 2
        ]
        
        # Create the generator and call generate_index_page
        generator = SiteGenerator()
        generator.generate_index_page(students, mock_db)
        
        # Check that the template was rendered
        mock_env.return_value.get_template.assert_called_with('index.html')
        mock_template.render.assert_called_once()
        
        # Check that the render call included student data
        render_kwargs = mock_template.render.call_args[1]
        self.assertIn('students', render_kwargs)
        self.assertEqual(len(render_kwargs['students']), 2)
        
        # Check that the output file was written
        mock_open_name = 'frontend.generate_site.open'
        with patch(mock_open_name, mock_open()) as mock_file:
            generator.generate_index_page(students, mock_db)
            mock_file.assert_called_once_with(os.path.join(self.temp_dir, 'index.html'), 'w')
            mock_file().write.assert_called_once_with(mock_template.render.return_value)
    
    @patch('frontend.generate_site.shutil.copytree')
    @patch('frontend.generate_site.shutil.rmtree')
    @patch('frontend.generate_site.os.path.exists')
    @patch('frontend.generate_site.Environment')
    @patch('frontend.generate_site.FileSystemLoader')
    def test_copy_static_files(self, mock_file_loader, mock_env, 
                               mock_exists, mock_rmtree, mock_copytree):
        """Test copying of static files."""
        # Mock os.path.exists to return True for static directory
        mock_exists.return_value = True
        
        # Create the generator and call copy_static_files
        generator = SiteGenerator()
        generator.copy_static_files()
        
        # Check that the static directory was copied
        mock_rmtree.assert_called_once()
        mock_copytree.assert_called_once()


if __name__ == '__main__':
    unittest.main() 