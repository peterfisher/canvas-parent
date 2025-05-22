import unittest
import os
import tempfile
from load_config import load_config

class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        # Clean up temporary files
        for file in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, file))
        os.rmdir(self.test_dir)
        
    def create_config_file(self, content):
        config_path = os.path.join(self.test_dir, 'test_config.ini')
        with open(config_path, 'w') as f:
            f.write(content)
        return config_path
        
    def test_successful_load(self):
        """Test loading a valid configuration file"""
        config_content = """
            USERNAME = testuser@example.com
            PASSWORD = testpass123
            LOGIN_URL = https://canvas.example.com/login
            STUDENT = Test Student
            OPTIONAL_FIELD = some_value
        """
        config_path = self.create_config_file(config_content)
        config = load_config(config_path)
        
        self.assertEqual(config['USERNAME'], 'testuser@example.com')
        self.assertEqual(config['PASSWORD'], 'testpass123')
        self.assertEqual(config['LOGIN_URL'], 'https://canvas.example.com/login')
        self.assertEqual(config['STUDENT'], 'Test Student')
        self.assertEqual(config['OPTIONAL_FIELD'], 'some_value')
        
    def test_missing_config_file(self):
        """Test behavior when config file doesn't exist"""
        with self.assertRaises(FileNotFoundError):
            load_config('nonexistent_config.ini')
            
    def test_missing_required_fields(self):
        """Test behavior when required fields are missing"""
        config_content = """
            USERNAME = testuser@example.com
            PASSWORD = testpass123
        """
        config_path = self.create_config_file(config_content)
        
        with self.assertRaises(Exception) as context:
            load_config(config_path)
        
        self.assertIn('Missing required configuration fields', str(context.exception))
        self.assertIn('LOGIN_URL', str(context.exception))
        self.assertIn('STUDENT', str(context.exception))
            
    def test_invalid_format(self):
        """Test behavior with invalid file format"""
        config_content = """
            USERNAME testuser@example.com
            PASSWORD = testpass123
            LOGIN_URL = https://canvas.example.com/login
            STUDENT = Test Student
        """
        config_path = self.create_config_file(config_content)
        
        with self.assertRaises(Exception) as context:
            load_config(config_path)
            
        self.assertIn('Error loading configuration', str(context.exception))
        
    def test_comments_handling(self):
        """Test that comments are properly ignored"""
        config_content = """
            # This is a comment
            USERNAME = testuser@example.com
            # Another comment
            PASSWORD = testpass123
            LOGIN_URL = https://canvas.example.com/login
            STUDENT = Test Student
        """
        config_path = self.create_config_file(config_content)
        config = load_config(config_path)
        
        self.assertEqual(config['USERNAME'], 'testuser@example.com')
        self.assertEqual(config['PASSWORD'], 'testpass123')
        self.assertEqual(len(config), 4)  # Only the required fields, no comments
        
if __name__ == '__main__':
    unittest.main() 