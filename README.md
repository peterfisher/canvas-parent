# Canvas Grade Scraper

## Project Description

The overall purpose of this system is to help parents quickly inform themselves of their students' grades and identify where there might be missing assignments. 

## Design

The application follows a modular design, centered around the `main.py` script, which orchestrates the entire process.

1.  **Configuration Loading**: The application starts by loading configuration from a `config.ini` file using `load_config.py`. This configuration includes student details and Canvas credentials.
2.  **Database Initialization**: A SQLite database is initialized (if it doesn't exist) via `init_database.py`, and a database session is obtained using `database.py`. The student's information is retrieved or created in the database (canvas.db).
3.  **Canvas Login**: The system logs into Canvas using credentials from the configuration. The `login_to_canvas` function in `login.py` handles this and returns an authenticated `requests.Session` object.
4.  **Scraper Initialization**: A `GradeScraper` instance is created (from `grade_scraper.py`). This central scraper is responsible for fetching course information and coordinating individual data scrapers. The authenticated session and student ID are passed to its constructor.
5.  **Scraping Process**:
    *   The `GradeScraper` retrieves a list of active courses and their IDs using the Canvas API (`/api/v1/courses`).
    *   For each course, it fetches the grades page HTML.
    *   It then delegates the actual data extraction to registered sub-scrapers.
6.  **Data Storage**: Scraped data (e.g., assignments) is saved to the SQLite database via the `DatabaseManager` in `database/manager.py`.
7.  **Results and Logging**: The application logs its progress and the final results, including statistics about the scraped courses and assignments.

### Scrapers

The scraping logic is extensible through a base class `BaseScraper` located in `scrappers/base.py`.

**Interface:**

*   `__init__(self)`: Constructor.
*   `set_page_content(self, html_content: str, course_id: str) -> None`: This method is called by the `GradeScraper` to provide the HTML content of a specific course's grades page and the corresponding `course_id`. The implementation should parse this `html_content` (e.g., using BeautifulSoup) and store it for `extract_data`.
*   `extract_data(self) -> Dict[str, Any]`: This abstract method must be implemented by concrete scraper subclasses. It should perform the actual scraping logic on the previously set page content and return a dictionary of the extracted data.
*   `scrape(self) -> Dict[str, Any]`: This is the main method called by `GradeScraper`. It ensures `set_page_content` has been called and then calls `extract_data`.

**Extending with a New Scraper:**

1.  Create a new Python file in the `scrappers/` directory (e.g., `my_new_scraper.py`).
2.  Define a new class that inherits from `BaseScraper`.
    ```python
    from .base import BaseScraper
    from typing import Dict, Any

    class MyNewScraper(BaseScraper):
        def __init__(self):
            super().__init__()
            # Your initialization logic

        def extract_data(self) -> Dict[str, Any]:
            if not self.soup:
                raise ValueError("Page content not set")
            
            # Implement your scraping logic using self.soup
            # and self.course_id
            extracted_info = {}
            # ... populate extracted_info ...
            return {"my_data_key": extracted_info}
    ```
3.  Implement the `extract_data` method to parse the `self.soup` (a BeautifulSoup object of the grades page) and return the desired data. You can also use `self.course_id` if needed.
4.  In `grade_scraper.py`, within the `create_grade_scraper` function, import your new scraper and register it:
    ```python
    from scrappers import AssignmentScraper # Existing
    from scrappers.my_new_scraper import MyNewScraper # Add this

    # ...

    def create_grade_scraper(session: requests.Session, student_id: int) -> GradeScraper:
        scraper = GradeScraper(session, student_id)
        
        scraper.register_scraper(AssignmentScraper)
        scraper.register_scraper(MyNewScraper) # Add this line
        
        return scraper
    ```
5.  The `GradeScraper` will then automatically call your new scraper's methods for each course.
6.  You'll also need to update `GradeScraper.scrape_course` to handle the data returned by your new scraper, potentially saving it to the database using `DatabaseManager`. This might involve adding a new method to `DatabaseManager` to handle your specific data structure.

This modular approach allows for different types of data to be scraped from Canvas pages without altering the core `GradeScraper` logic significantly. 


### Testing

In order to run the unit tests perform the following command
```
python -m pytest tests/ -v
```