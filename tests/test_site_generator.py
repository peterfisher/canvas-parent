import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.page_generator import PageGenerator


class TestSiteGenerator(unittest.TestCase):
    """Test cases for the PageGenerator class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for output
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a mock template directory
        self.template_dir = tempfile.mkdtemp()
        
        # Create a temporary database file
        self.db_path = os.path.join(self.temp_dir, 'test.db')
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directories
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.template_dir)
    
    @patch('jinja2.Environment')
    @patch('jinja2.FileSystemLoader')
    @patch('os.makedirs')
    def test_init(self, mock_makedirs, mock_file_loader, mock_env):
        """Test initialization of PageGenerator."""
        generator = PageGenerator(
            db_path=self.db_path,
            template_dir=self.template_dir,
            output_dir=self.temp_dir
        )
        
        # Check that the Jinja2 environment is set up correctly
        mock_file_loader.assert_called_once_with(self.template_dir)
        mock_env.assert_called_once()
        
        # Check that makedirs was called for output directory
        mock_makedirs.assert_called_once_with(self.temp_dir, exist_ok=True)
        
        # Check instance variables
        self.assertEqual(generator.db_path, self.db_path)
        self.assertEqual(generator.template_dir, self.template_dir)
        self.assertEqual(generator.output_dir, self.temp_dir)
    
    @patch('jinja2.Environment')
    @patch('jinja2.FileSystemLoader')
    @patch('os.makedirs')
    def test_generate_index_page(self, mock_makedirs, mock_file_loader, mock_env):
        """Test generation of index page."""
        # Mock the template
        mock_template = MagicMock()
        mock_env.return_value.get_template.return_value = mock_template
        mock_template.render.return_value = "<html>Test Index</html>"
        
        # Create the generator
        generator = PageGenerator(
            db_path=self.db_path,
            template_dir=self.template_dir,
            output_dir=self.temp_dir
        )
        
        # Mock the get_students method
        with patch.object(generator, 'get_students') as mock_get_students:
            mock_get_students.return_value = [
                {'id': 1, 'name': 'Test Student 1'},
                {'id': 2, 'name': 'Test Student 2'}
            ]
            
            # Mock the write_file method
            with patch.object(generator, 'write_file') as mock_write_file:
                generator.generate_index_page()
                
                # Check that get_students was called
                mock_get_students.assert_called_once()
                
                # Check that the template was rendered with correct context
                mock_env.return_value.get_template.assert_called_with('index.html')
                mock_template.render.assert_called_once()
                render_kwargs = mock_template.render.call_args[1]
                self.assertIn('students', render_kwargs)
                self.assertIn('title', render_kwargs)
                self.assertEqual(len(render_kwargs['students']), 2)
                
                # Check that the file was written
                expected_path = os.path.join(self.temp_dir, 'index.html')
                mock_write_file.assert_called_once_with(expected_path, "<html>Test Index</html>")
    
    @patch('jinja2.Environment')
    @patch('jinja2.FileSystemLoader')
    @patch('os.makedirs')
    @patch('shutil.copytree')
    @patch('shutil.rmtree')
    @patch('shutil.copy2')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_static_files(self, mock_isdir, mock_listdir, mock_exists, 
                               mock_copy2, mock_rmtree, mock_copytree, 
                               mock_makedirs, mock_file_loader, mock_env):
        """Test copying of static files."""
        # Mock os.path.exists to return True for static directory
        mock_exists.return_value = True
        mock_listdir.return_value = ['style.css', 'script.js']
        mock_isdir.return_value = False  # Treat all items as files
        
        # Create the generator
        generator = PageGenerator(
            db_path=self.db_path,
            template_dir=self.template_dir,
            output_dir=self.temp_dir
        )
        
        generator.copy_static_files()
        
        # Check that the static directory existence was checked
        expected_static_dir = os.path.join(self.template_dir, 'static')
        mock_exists.assert_called_with(expected_static_dir)
        
        # Check that files were copied
        self.assertEqual(mock_copy2.call_count, 2)


if __name__ == '__main__':
    unittest.main() 