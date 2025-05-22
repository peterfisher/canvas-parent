from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import Any, Dict, Optional

class BaseScraper(ABC):
    """Base class for all scrapers that extract data from Canvas pages."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.soup: Optional[BeautifulSoup] = None
        self.course_id: Optional[str] = None
    
    def set_page_content(self, html_content: str, course_id: str) -> None:
        """Set the HTML content to be scraped and the course ID.
        
        Args:
            html_content: Raw HTML content of the page
            course_id: Canvas course ID for the current page
        """
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.course_id = course_id
    
    @abstractmethod
    def extract_data(self) -> Dict[str, Any]:
        """Extract data from the page.
        
        Returns:
            Dictionary containing the extracted data
        """
        pass
    
    def scrape(self) -> Dict[str, Any]:
        """Main method to execute the scraping process.
        
        Returns:
            Dictionary containing the extracted data
        
        Raises:
            ValueError: If page content hasn't been set
        """
        if not self.soup or not self.course_id:
            raise ValueError("Page content must be set before scraping")
        
        return self.extract_data() 