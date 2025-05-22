#!/usr/bin/env python3

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

class CanvasLoginError(Exception):
    """Custom exception for Canvas login errors"""
    pass

class CanvasSession:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url
        
    def get_session_token(self):
        """Get the session token from cookies"""
        session_cookies = [cookie for cookie in self.session.cookies if '_session' in cookie.name.lower()]
        return session_cookies[0].value if session_cookies else None

def extract_csrf_token(html_content):
    """Extract CSRF token from the login page HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for meta tag with csrf token
    csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
    if csrf_meta:
        return csrf_meta.get('content')
    
    # Look for input field with csrf token
    csrf_input = soup.find('input', attrs={'name': 'authenticity_token'})
    if csrf_input:
        return csrf_input.get('value')
    
    return None

def login_to_canvas(config):
    """
    Login to Canvas using provided credentials.
    Returns a session object with valid authentication.
    
    Required config fields:
    - USERNAME: Canvas username/email
    - PASSWORD: Canvas password
    - LOGIN_URL: Full URL to the Canvas login endpoint
    
    Raises:
    - CanvasLoginError: If login fails due to invalid credentials or other issues
    - ValueError: If configuration is invalid
    """
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Get configuration
    login_url = config.get('LOGIN_URL', '').strip()
    if not login_url:
        raise ValueError("LOGIN_URL must be provided in configuration")
    
    # Extract base URL from login URL
    parsed_url = urlparse(login_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    try:
        # Get the login page first to obtain CSRF token
        response = session.get(login_url)
        response.raise_for_status()
        
        # Extract CSRF token
        csrf_token = extract_csrf_token(response.text)
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        if csrf_token:
            headers['X-CSRF-Token'] = csrf_token
        
        # Prepare login data
        login_data = {
            'pseudonym_session[unique_id]': config['USERNAME'],
            'pseudonym_session[password]': config['PASSWORD'],
        }
        
        if csrf_token:
            login_data['authenticity_token'] = csrf_token
        
        # Attempt login
        response = session.post(
            login_url,
            data=login_data,
            headers=headers,
            allow_redirects=True
        )
        
        # Check for specific error responses
        if response.status_code == 400:
            raise CanvasLoginError("Login failed: Invalid credentials")
        elif response.status_code == 401:
            raise CanvasLoginError("Login failed: Unauthorized")
        elif response.status_code != 200:
            raise CanvasLoginError(f"Login failed with status code: {response.status_code}")
        
        response.raise_for_status()
        
        # Check if login was successful by verifying we're no longer on the login page
        if login_url in response.url:
            raise CanvasLoginError("Login failed: Invalid credentials")
        
        # Create session object
        canvas_session = CanvasSession(session, base_url)
        
        # Verify we have a session token
        if not canvas_session.get_session_token():
            raise CanvasLoginError("Login failed: No session token obtained")
        
        return canvas_session
        
    except requests.RequestException as e:
        raise CanvasLoginError(f"Login failed: {str(e)}")
    except Exception as e:
        if isinstance(e, CanvasLoginError):
            raise
        raise CanvasLoginError(f"Login failed: Unexpected error - {str(e)}") 