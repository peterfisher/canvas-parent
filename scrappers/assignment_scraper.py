from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re
import json
from bs4 import BeautifulSoup, Tag
from dateutil import parser as dateutil_parser
from database.models import AssignmentType, AssignmentStatus
from .base import BaseScraper

class AssignmentScraper(BaseScraper):
    """Scraper for extracting assignment data from Canvas pages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._env_data_cache = None

    def _extract_structured_date(self, assignment_id: str) -> Optional[datetime]:
        """Try to extract due date from structured JSON data in the page."""
        if not self.soup or not assignment_id:
            return None
        
        env_data = self._get_env_data()
        if not env_data:
            return None
        
        # Try assignment groups first
        due_date = self._find_due_date_in_assignment_groups(env_data, assignment_id)
        if due_date:
            return due_date
        
        # Try effective due dates as fallback
        return self._find_due_date_in_effective_dates(env_data, assignment_id)

    def _get_env_data(self) -> Optional[Dict]:
        """Extract and cache ENV data from script tags."""
        if self._env_data_cache is not None:
            return self._env_data_cache
        
        self._env_data_cache = self._extract_env_data_from_scripts()
        return self._env_data_cache

    def _extract_env_data_from_scripts(self) -> Optional[Dict]:
        """Extract ENV data from script tags."""
        script_tags = self.soup.find_all('script')
        
        for script in script_tags:
            if not self._script_contains_env_data(script):
                continue
                
            env_match = re.search(r'ENV\s*=\s*({.*?});', script.string, re.DOTALL)
            if env_match:
                try:
                    return json.loads(env_match.group(1))
                except json.JSONDecodeError:
                    continue
        
        return None

    def _script_contains_env_data(self, script) -> bool:
        """Check if script tag contains relevant ENV data."""
        if not script.string:
            return False
        return 'ENV' in script.string and 'assignment_groups' in script.string

    def _find_due_date_in_assignment_groups(self, env_data: Dict, assignment_id: str) -> Optional[datetime]:
        """Find due date in assignment groups data."""
        assignment_groups = env_data.get('assignment_groups', [])
        
        for group in assignment_groups:
            for assignment in group.get('assignments', []):
                if str(assignment.get('id')) == assignment_id:
                    due_at = assignment.get('due_at')
                    if due_at:
                        return self._parse_iso_date_to_datetime(due_at)
        
        return None

    def _find_due_date_in_effective_dates(self, env_data: Dict, assignment_id: str) -> Optional[datetime]:
        """Find due date in effective due dates data."""
        effective_dates = env_data.get('effective_due_dates', {})
        
        if assignment_id not in effective_dates:
            return None
        
        # Effective dates have student IDs as keys
        for student_data in effective_dates[assignment_id].values():
            due_at = student_data.get('due_at')
            if due_at:
                return self._parse_iso_date_to_datetime(due_at)
        
        return None

    def _parse_iso_date_to_datetime(self, iso_date_str: str) -> Optional[datetime]:
        """Parse ISO date string to datetime object (date only, midnight)."""
        try:
            parsed_date = dateutil_parser.parse(iso_date_str)
            return datetime(parsed_date.year, parsed_date.month, parsed_date.day)
        except (ValueError, TypeError):
            return None

    def _parse_date_with_dateutil(self, date_str: str) -> Optional[datetime]:
        """Parse date using dateutil.parser for flexible parsing."""
        if not date_str:
            return None
            
        # Clean up the date string - remove time-related text
        date_str = date_str.replace("Due: ", "").replace("Due ", "")
        date_str = re.sub(r'\s+at\s+.*$', '', date_str)  # Remove "at XX:XX" and everything after
        date_str = re.sub(r'\s+by\s+.*$', '', date_str)  # Remove "by XX:XX" and everything after
        date_str = re.sub(r'\d{1,2}:\d{2}.*$', '', date_str)  # Remove time patterns
        date_str = re.sub(r'\s+(am|pm).*$', '', date_str, flags=re.IGNORECASE)  # Remove am/pm
        date_str = re.sub(r'\s+(midnight|noon|end of day).*$', '', date_str, flags=re.IGNORECASE)  # Remove time keywords
        date_str = date_str.strip()
        
        # Handle explicit "No Due Date" indicators
        no_date_indicators = {
            "No Due Date", "TBD", "N/A", "-", "No due date", 
            "no due date", "tbd", "n/a", "None", "none"
        }
        if date_str.strip() in no_date_indicators:
            return None
        
        # Basic validation - must have at least a month and day-like pattern
        if not re.search(r'(\w+)\s+\d+|(\d+[-/.]\d+)', date_str):
            return None
            
        try:
            # Use dateutil.parser for flexible parsing
            current_year = datetime.now().year
            parsed_date = dateutil_parser.parse(date_str, default=datetime(current_year, 1, 1))
            
            # Additional validation: ensure we actually got a meaningful date
            if parsed_date.year == current_year and parsed_date.month == 1 and parsed_date.day == 1:
                # Check if the original string contains meaningful date components
                if not re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2})', date_str.lower()):
                    return None
            
            # Return only the date part as datetime at midnight
            return datetime(parsed_date.year, parsed_date.month, parsed_date.day)
            
        except (ValueError, TypeError):
            return None

    def _parse_date_with_regex(self, date_str: str) -> Optional[datetime]:
        """Fall back to regex parsing for edge cases."""
        if not date_str:
            return None
            
        try:
            # Clean up the date string - remove time-related text
            date_str = date_str.replace("Due: ", "").replace("Due ", "")
            date_str = re.sub(r'\s+at\s+.*$', '', date_str)  # Remove "at XX:XX" and everything after
            date_str = re.sub(r'\s+by\s+.*$', '', date_str)  # Remove "by XX:XX" and everything after
            date_str = re.sub(r'\d{1,2}:\d{2}.*$', '', date_str)  # Remove time patterns
            date_str = re.sub(r'\s+(am|pm).*$', '', date_str, flags=re.IGNORECASE)  # Remove am/pm
            date_str = re.sub(r'\s+(midnight|noon|end of day).*$', '', date_str, flags=re.IGNORECASE)  # Remove time keywords
            date_str = date_str.strip()
            
            # Numeric date patterns: MM.DD.YYYY, MM-DD-YYYY, MM/DD/YYYY
            numeric_pattern = r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})'
            numeric_match = re.search(numeric_pattern, date_str)
            
            if numeric_match:
                month, day, year = map(int, numeric_match.groups())
                return datetime(year, month, day)
            
            # Text-based date patterns: Month Day Year, Month Day, etc.
            pattern = r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?'
            match = re.search(pattern, date_str, re.IGNORECASE)
            
            if not match:
                return None
                
            month_str, day_str, year_str = match.groups()
            
            # Month mapping
            month_map = {
                'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
                'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
                'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'sept': 9, 'oct': 10, 'october': 10,
                'nov': 11, 'november': 11, 'dec': 12, 'december': 12
            }
            
            month = month_map.get(month_str.lower())
            if not month:
                return None
                
            day = int(day_str)
            year = int(year_str) if year_str else datetime.now().year
                        
            return datetime(year, month, day)
            
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_str: str, assignment_id: str = None) -> Optional[datetime]:
        """Parse date string using multiple strategies in order of preference."""
        if not date_str:
            return None
        
        # Strategy 1: Try to extract from structured JSON data if we have assignment ID
        if assignment_id:
            structured_date = self._extract_structured_date(assignment_id)
            if structured_date:
                return structured_date
        
        # Strategy 2: Use dateutil.parser for flexible parsing
        dateutil_date = self._parse_date_with_dateutil(date_str)
        if dateutil_date:
            return dateutil_date
            
        # Strategy 3: Fall back to regex parsing
        regex_date = self._parse_date_with_regex(date_str)
        if regex_date:
            return regex_date
            
        return None

    def _determine_assignment_type(self, context: str) -> AssignmentType:
        """Determine the assignment type based on the context string."""
        context = context.lower() if context else ""
        
        if "quiz" in context:
            return AssignmentType.QUIZ
        elif "project" in context or "writing" in context:
            return AssignmentType.PROJECT
        elif "homework" in context or "assignment" in context:
            return AssignmentType.HOMEWORK
        elif "lab" in context:
            return AssignmentType.LAB
        elif "test" in context:
            return AssignmentType.TEST
        else:
            return AssignmentType.OTHER

    def _determine_status(self, row: Tag) -> AssignmentStatus:
        """Determine the assignment status based on the HTML row.
        
        The status is determined in the following priority order:
        1. EXCUSED - Assignment has been excused by instructor
        2. LATE - Assignment was submitted after the due date
        3. GRADED - Assignment has been submitted and graded
        4. SUBMITTED - Assignment has been submitted but not yet graded
        5. UPCOMING - Assignment is not yet due
        6. MISSING - Assignment is explicitly marked as missing with visual indicator
        7. UNKNOWN - Assignment status cannot be determined with confidence
        
        Args:
            row: BeautifulSoup Tag object representing an assignment row
            
        Returns:
            AssignmentStatus enum value representing the assignment's status
        """
        try:
            # 1. Check if assignment is excused (highest priority)
            if "excused" in row.get("class", []):
                return AssignmentStatus.EXCUSED
            
            # Get common elements we'll need
            status_cell = row.find("td", class_="status")
            submission_status = row.find("span", class_="submission_status")
            status_text = submission_status.text.strip() if submission_status else ""
            
            # 2. Check if assignment is late but submitted
            if status_cell and status_cell.find("span", class_="submission-late-pill"):
                return AssignmentStatus.LATE
            
            # 3. Check graded status
            if status_text == "graded" or "assignment_graded" in row.get("class", []):
                return AssignmentStatus.GRADED
            
            # 4. Check if submitted but not graded
            if status_text == "submitted":
                return AssignmentStatus.SUBMITTED
            
            # 5. Check if assignment is upcoming (not yet due)
            due_date_cell = row.find("td", class_="due")
            if due_date_cell:
                due_date_str = due_date_cell.text.strip()
                if due_date_str:
                    # Try to extract assignment ID for better date parsing
                    assignment_id = None
                    row_id = row.get('id', '')
                    if row_id.startswith('submission_'):
                        assignment_id = row_id.replace('submission_', '')
                    
                    due_date = self._parse_date(due_date_str, assignment_id)
                    if due_date and due_date > datetime.now():
                        return AssignmentStatus.UPCOMING
            
            # 6. Check if explicitly marked as missing with visual indicator
            # Check for missing indicator: either a visual pill or special class
            missing_pill = (status_cell and status_cell.find("span", class_="submission-missing-pill"))
            missing_assignment_class = "missing_assignment" in row.get("class", [])
            missing_status_class = (status_cell and "missing" in status_cell.get("class", []))
            
            # If there's a missing pill, the assignment is definitely missing
            if missing_pill:
                return AssignmentStatus.MISSING
            
            # Check for other missing indicators (class-based) with unsubmitted status
            if status_text == "unsubmitted" and (missing_assignment_class or missing_status_class):
                return AssignmentStatus.MISSING
            
            # Check if assignment is pending teacher grading (only if no missing indicators)
            if status_text == "unsubmitted":
                score_cell = row.find("td", class_="assignment_score")
                if score_cell:
                    score_text = score_cell.text.strip()
                    # Assignments pending grading usually have either "-" or "–" or no score
                    is_pending_grading = (
                        "–" in score_text or 
                        "-" in score_text or
                        score_text == ""
                    )
                    if is_pending_grading:
                        return AssignmentStatus.UNKNOWN
                
                # If unsubmitted but no pending grading indicators, might be missing
                # but we'll mark as UNKNOWN since we can't be certain without visual indicators
                return AssignmentStatus.UNKNOWN
            
            # Special case: If it's a final grade or group total row, mark as UNKNOWN
            if any(cls in row.get("class", []) for cls in ["final_grade", "group_total"]):
                return AssignmentStatus.UNKNOWN
            
            # If we can't determine the status but there's a submission date, mark as SUBMITTED
            submitted_cell = row.find("td", class_="submitted")
            if submitted_cell and submitted_cell.text.strip():
                return AssignmentStatus.SUBMITTED
            
            # Default case: If we can't determine the status, mark as UNKNOWN
            return AssignmentStatus.UNKNOWN
            
        except Exception as e:
            print(f"Error determining assignment status: {str(e)}")
            # In case of error, default to UNKNOWN as we can't determine the status
            return AssignmentStatus.UNKNOWN

    def _parse_score(self, score_cell: Tag) -> Tuple[Optional[float], Optional[float]]:
        """Parse the score and max score from the score cell."""
        if not score_cell:
            return None, None
            
        try:
            grade_span = score_cell.find("span", class_="grade")
            if not grade_span:
                return None, None
                
            # Check if the grade is excused
            if grade_span.text.strip() == "EX":
                return None, None
                
            # Get the actual score
            score_text = grade_span.text.strip()
            score = float(score_text) if score_text and score_text != "EX" else None
            
            # Get the max score
            max_score_span = score_cell.find("span", string=lambda s: s and "/" in s)
            if max_score_span:
                max_score = float(max_score_span.text.strip("/ "))
                return score, max_score
                
        except (ValueError, AttributeError):
            pass
            
        return None, None

    def extract_data(self) -> Dict[str, Any]:
        """Extract assignment data from the page."""
        if not self.soup:
            raise ValueError("Page content must be set before extraction")

        assignments = []
        assignment_rows = self.soup.find_all("tr", class_="student_assignment")

        for row in assignment_rows:
            try:
                # Extract basic information
                title_cell = row.find("th", class_="title")
                if not title_cell:
                    continue

                name_link = title_cell.find("a")
                if not name_link:
                    continue

                name = name_link.text.strip()
                context_div = title_cell.find("div", class_="context")
                context = context_div.text.strip() if context_div else ""
                assignment_type = self._determine_assignment_type(context)

                # Extract assignment ID from various sources
                assignment_id = None
                
                # Try to get assignment ID from row id (format: "submission_123456")
                row_id = row.get('id', '')
                if row_id.startswith('submission_'):
                    assignment_id = row_id.replace('submission_', '')
                
                # If not found, try to extract from assignment URL
                if not assignment_id and name_link:
                    href = name_link.get('href', '')
                    if '/assignments/' in href:
                        # Extract from URL like "/courses/102017/assignments/7167381/submissions/149157"
                        assignment_match = re.search(r'/assignments/(\d+)', href)
                        if assignment_match:
                            assignment_id = assignment_match.group(1)
                
                # If still not found, try to get from hidden assignment_id span
                if not assignment_id:
                    assignment_id_span = row.find("span", class_="assignment_id")
                    if assignment_id_span:
                        assignment_id = assignment_id_span.text.strip()

                # Extract dates with assignment ID for better parsing
                due_cell = row.find("td", class_="due")
                submitted_cell = row.find("td", class_="submitted")
                due_date = self._parse_date(due_cell.text.strip() if due_cell else "", assignment_id)
                submitted_date = self._parse_date(submitted_cell.text.strip() if submitted_cell else "", assignment_id)

                # Extract status and score
                status = self._determine_status(row)
                score_cell = row.find("td", class_="assignment_score")
                score, max_score = self._parse_score(score_cell)

                assignment_data = {
                    "name": name,
                    "assignment_type": assignment_type,
                    "due_date": due_date,
                    "submitted_date": submitted_date,
                    "status": status,
                    "score": score,
                    "max_score": max_score,
                    "is_missing": status == AssignmentStatus.MISSING
                }
                assignments.append(assignment_data)
            except Exception as e:
                print(f"Error processing assignment row: {str(e)}")
                continue

        return {"assignments": assignments} 