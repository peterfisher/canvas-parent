from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from database.models import AssignmentType, AssignmentStatus
from .base import BaseScraper

class AssignmentScraper(BaseScraper):
    """Scraper for extracting assignment data from Canvas pages."""

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from Canvas format to datetime object."""
        if not date_str:
            return None
            
        # Remove "at" and "by" from the string
        date_str = date_str.replace(" at ", " ").replace(" by ", " ").strip()
        
        try:
            # Try parsing with different formats
            current_year = datetime.now().year
            for fmt in ["%b %d %I:%M%p", "%b %d %Y %I:%M%p"]:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    # Set the current year if year wasn't in the format
                    if fmt == "%b %d %I:%M%p":
                        return parsed_date.replace(year=current_year)
                    return parsed_date
                except ValueError:
                    continue
            return None
        except Exception:
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
        6. MISSING - Assignment is explicitly marked as unsubmitted and past due with visual indicator
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
                    due_date = self._parse_date(due_date_str)
                    if due_date and due_date > datetime.now():
                        return AssignmentStatus.UPCOMING
            
            # 6. Check if explicitly marked as missing with visual indicator
            # Only mark as missing if there's a visual indicator (like a pill/bubble)
            score_cell = row.find("td", class_="assignment_score")
            
            # Check for missing indicator: either a visual pill or special class
            missing_indicator = (
                (status_cell and status_cell.find("span", class_="submission-missing-pill")) or
                "missing_assignment" in row.get("class", []) or
                (status_cell and "missing" in status_cell.get("class", []))
            )
            
            # Check if assignment is pending teacher grading
            is_pending_grading = False
            if score_cell:
                score_text = score_cell.text.strip()
                # Assignments pending grading usually have either "-" or "–" or no score
                is_pending_grading = (
                    "–" in score_text or 
                    "-" in score_text or
                    score_text == ""
                )
            
            if status_text == "unsubmitted" and missing_indicator and not is_pending_grading:
                return AssignmentStatus.MISSING
            
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

                # Extract dates
                due_cell = row.find("td", class_="due")
                submitted_cell = row.find("td", class_="submitted")
                due_date = self._parse_date(due_cell.text.strip() if due_cell else "")
                submitted_date = self._parse_date(submitted_cell.text.strip() if submitted_cell else "")

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