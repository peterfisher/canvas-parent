from typing import Any, Dict, Optional, List
from bs4 import BeautifulSoup, Tag
import re
import json
from .base import BaseScraper

class GradeScraper(BaseScraper):
    """Scraper for extracting grade data from Canvas grades pages."""

    def extract_data(self) -> Dict[str, Any]:
        """Extract grade data from the page."""
        if not self.soup:
            raise ValueError("Page content must be set before extraction")

        grade_data = {
            "overall_grade": None,
            "overall_letter_grade": None,
            "grade_breakdown": [],
            "assignment_weights": {},
            "total_weight": 0,
            "course_grade": None,
            "course_letter_grade": None,
            "has_course_grade": False
        }

        # Extract overall grade by calculating weighted grades from assignment groups
        overall_grade = self._extract_overall_grade()
        if overall_grade and overall_grade.get("has_grade"):
            grade_data["overall_grade"] = overall_grade.get("percentage")
            grade_data["overall_letter_grade"] = overall_grade.get("letter_grade")
            grade_data["course_grade"] = overall_grade.get("percentage")
            grade_data["course_letter_grade"] = overall_grade.get("letter_grade")
            grade_data["has_course_grade"] = overall_grade.get("has_grade", False)

        # Extract grade breakdown from the bottom section
        grade_breakdown = self._extract_grade_breakdown()
        if grade_breakdown:
            grade_data["grade_breakdown"] = grade_breakdown

        # Extract assignment weights
        weights = self._extract_assignment_weights()
        if weights:
            grade_data["assignment_weights"] = weights
            grade_data["total_weight"] = sum(weights.values())

        return grade_data

    def _extract_overall_grade(self) -> Optional[Dict[str, Any]]:
        """Extract the overall grade by calculating weighted grades from assignment groups."""
        try:
            # First try to get the grading scheme from ENV data
            env_data = self._extract_env_data()
            if not env_data:
                return None
            
            # Get the grading scheme
            grading_scheme = env_data.get('course_active_grading_scheme', {})
            grading_data = grading_scheme.get('data', [])
            
            # Get assignment groups and their weights
            assignment_groups = env_data.get('assignment_groups', [])
            if not assignment_groups:
                return None
            
            # Get submissions data
            submissions = env_data.get('submissions', [])
            if not submissions:
                return None
            
            # Create a mapping of assignment_id to submission data
            submission_map = {sub['assignment_id']: sub for sub in submissions}
            
            # Calculate weighted grade
            total_weighted_score = 0
            total_weight = 0
            
            for group in assignment_groups:
                group_weight = group.get('group_weight', 0)
                if group_weight <= 0:
                    continue
                
                group_assignments = group.get('assignments', [])
                if not group_assignments:
                    continue
                
                # Calculate group total
                group_earned = 0
                group_possible = 0
                
                for assignment in group_assignments:
                    assignment_id = assignment.get('id')
                    if assignment_id and str(assignment_id) in submission_map:
                        submission = submission_map[str(assignment_id)]
                        score = submission.get('score')
                        if score is not None:  # Only count graded assignments
                            group_earned += score
                            points_possible = assignment.get('points_possible', 0)
                            if points_possible > 0:
                                group_possible += points_possible
                
                # Calculate group percentage
                if group_possible > 0:
                    group_percentage = (group_earned / group_possible) * 100
                    # Apply weight to this group
                    weighted_score = (group_percentage * group_weight) / 100
                    total_weighted_score += weighted_score
                    total_weight += group_weight
            
            if total_weight == 0:
                return None
            
            # Calculate final weighted percentage
            final_percentage = (total_weighted_score / total_weight) * 100
            
            # Convert to letter grade using the grading scheme
            letter_grade = self._percentage_to_letter_grade_with_scheme(final_percentage, grading_data)
            
            return {
                "percentage": final_percentage,
                "letter_grade": letter_grade,
                "has_grade": True,
                "raw_text": f"{final_percentage:.1f}% ({letter_grade})",
                "total_weighted_score": total_weighted_score,
                "total_weight": total_weight
            }
            
        except Exception as e:
            print(f"Error extracting overall grade: {str(e)}")
            return None

    def _extract_grade_breakdown(self) -> List[Dict[str, Any]]:
        """Extract the grade breakdown from the bottom section."""
        breakdown = []
        
        try:
            # First try to extract from ENV data (most reliable)
            env_data = self._extract_env_data()
            if env_data:
                breakdown = self._extract_from_env_data(env_data)
            
            # If no breakdown from ENV, try to extract from assignment groups
            if not breakdown:
                breakdown = self._extract_from_assignment_groups()
            
            # If still no breakdown, try to extract from the page structure
            if not breakdown:
                breakdown = self._extract_from_page_structure()
                
        except Exception as e:
            print(f"Error extracting grade breakdown: {str(e)}")
        
        return breakdown

    def _extract_env_data(self) -> Optional[Dict]:
        """Extract ENV data from script tags."""
        try:
            script_tags = self.soup.find_all('script')
            
            for script in script_tags:
                if not script.string:
                    continue
                    
                # Look for ENV data
                env_match = re.search(r'ENV\s*=\s*({.*?});', script.string, re.DOTALL)
                if env_match:
                    try:
                        return json.loads(env_match.group(1))
                    except json.JSONDecodeError:
                        continue
            
            return None
        except Exception as e:
            print(f"Error extracting ENV data: {str(e)}")
            return None

    def _extract_from_env_data(self, env_data: Dict) -> List[Dict[str, Any]]:
        """Extract grade breakdown from ENV data."""
        breakdown = []
        
        try:
            # Look for assignment groups in ENV data
            assignment_groups = env_data.get('assignment_groups', [])
            
            for group in assignment_groups:
                group_name = group.get('name', '')
                group_weight = group.get('group_weight', 0)
                
                # Calculate group grade if possible
                assignments = group.get('assignments', [])
                if assignments:
                    total_points = 0
                    earned_points = 0
                    
                    for assignment in assignments:
                        points_possible = assignment.get('points_possible', 0)
                        if points_possible > 0:
                            total_points += points_possible
                            # Note: We don't have individual assignment scores in this data
                    
                    if total_points > 0:
                        breakdown.append({
                            "category": group_name,
                            "percentage": None,  # We can't calculate without individual scores
                            "letter_grade": None,
                            "score": None,
                            "max_score": total_points,
                            "weight": group_weight
                        })
            
        except Exception as e:
            print(f"Error extracting from ENV data: {str(e)}")
        
        return breakdown

    def _extract_from_assignment_groups(self) -> List[Dict[str, Any]]:
        """Extract grade breakdown from assignment groups."""
        breakdown = []
        
        try:
            # Look for assignment group headers
            group_headers = self.soup.find_all("tr", class_=re.compile(r"group.*header|assignment.*group"))
            
            for header in group_headers:
                # Extract group name
                name_cell = header.find("th") or header.find("td")
                if name_cell:
                    group_name = name_cell.get_text(strip=True)
                    
                    # Look for grade in the same row or next row
                    grade_cell = header.find("td", class_="assignment_score")
                    if grade_cell:
                        grade_info = self._extract_category_grade(grade_cell)
                        if grade_info:
                            breakdown.append({
                                "category": group_name,
                                "percentage": grade_info.get("percentage"),
                                "letter_grade": grade_info.get("letter_grade"),
                                "score": grade_info.get("score"),
                                "max_score": grade_info.get("max_score")
                            })
                            
        except Exception as e:
            print(f"Error extracting from assignment groups: {str(e)}")
        
        return breakdown

    def _extract_from_page_structure(self) -> List[Dict[str, Any]]:
        """Extract grade breakdown from page structure."""
        breakdown = []
        
        try:
            # Look for grade breakdown sections
            breakdown_sections = self.soup.find_all("div", class_=re.compile(r"grade.*breakdown|assignment.*group"))
            
            for section in breakdown_sections:
                # Look for category names and their grades
                category_name = self._extract_category_name(section)
                if category_name:
                    category_grade = self._extract_category_grade(section)
                    if category_grade:
                        breakdown.append({
                            "category": category_name,
                            "percentage": category_grade.get("percentage"),
                            "letter_grade": category_grade.get("letter_grade"),
                            "score": category_grade.get("score"),
                            "max_score": category_grade.get("max_score")
                        })
                        
        except Exception as e:
            print(f"Error extracting from page structure: {str(e)}")
        
        return breakdown

    def _extract_category_name(self, section: Tag) -> Optional[str]:
        """Extract category name from a section."""
        # Look for common patterns in category names
        name_selectors = [
            "h3", "h4", ".category-name", ".group-name", 
            "[class*='category']", "[class*='group']"
        ]
        
        for selector in name_selectors:
            element = section.find(selector)
            if element:
                return element.get_text(strip=True)
        
        return None

    def _extract_category_grade(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract grade information from a category section."""
        try:
            # Look for grade patterns
            grade_text = section.get_text()
            
            # Look for percentage
            percentage_match = re.search(r'(\d+(?:\.\d+)?)%', grade_text)
            percentage = float(percentage_match.group(1)) if percentage_match else None
            
            # Look for letter grade
            letter_match = re.search(r'([A-Z][+-]?)', grade_text)
            letter_grade = letter_match.group(1) if letter_match else None
            
            # Look for score/max_score pattern
            score_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', grade_text)
            score = float(score_match.group(1)) if score_match else None
            max_score = float(score_match.group(2)) if score_match else None
            
            return {
                "percentage": percentage,
                "letter_grade": letter_grade,
                "score": score,
                "max_score": max_score
            }
            
        except Exception as e:
            print(f"Error extracting category grade: {str(e)}")
            return None

    def _extract_assignment_weights(self) -> Dict[str, float]:
        """Extract assignment weights from the page."""
        weights = {}
        
        try:
            # First try to extract from ENV data
            env_data = self._extract_env_data()
            if env_data:
                weights = self._extract_weights_from_env(env_data)
            
            # If no weights from ENV, try to extract from page text
            if not weights:
                weights = self._extract_weights_from_text()
            
            # If still no weights, try to extract from structured elements
            if not weights:
                weights = self._extract_weights_from_structure()
                
        except Exception as e:
            print(f"Error extracting assignment weights: {str(e)}")
        
        return weights

    def _extract_weights_from_env(self, env_data: Dict) -> Dict[str, float]:
        """Extract weights from ENV data."""
        weights = {}
        
        try:
            assignment_groups = env_data.get('assignment_groups', [])
            
            for group in assignment_groups:
                group_name = group.get('name', '')
                group_weight = group.get('group_weight', 0)
                
                if group_weight > 0:
                    weights[group_name] = group_weight
                    
        except Exception as e:
            print(f"Error extracting weights from ENV: {str(e)}")
        
        return weights

    def _extract_weights_from_text(self) -> Dict[str, float]:
        """Extract weights from text content."""
        weights = {}
        
        try:
            # Look for weight information in the right sidebar or assignment groups
            weight_elements = self.soup.find_all(text=re.compile(r'.*weight.*%|.*%.*weight', re.IGNORECASE))
            
            for element in weight_elements:
                # Extract category name and weight
                text = element.strip()
                weight_match = re.search(r'(\d+(?:\.\d+)?)%', text)
                if weight_match:
                    weight = float(weight_match.group(1))
                    # Try to extract category name
                    category_match = re.search(r'([A-Za-z\s]+)(?:\s*weight|\s*%)', text)
                    if category_match:
                        category = category_match.group(1).strip()
                        weights[category] = weight
                        
        except Exception as e:
            print(f"Error extracting weights from text: {str(e)}")
        
        return weights

    def _extract_weights_from_structure(self) -> Dict[str, float]:
        """Extract weights from structured elements."""
        weights = {}
        
        try:
            # Look for weight elements in the right sidebar
            weight_divs = self.soup.find_all("div", class_=re.compile(r"weight|assignment.*weight"))
            
            for div in weight_divs:
                text = div.get_text(strip=True)
                weight_match = re.search(r'(\d+(?:\.\d+)?)%', text)
                if weight_match:
                    weight = float(weight_match.group(1))
                    # Try to extract category name from parent or sibling elements
                    category_element = div.find_previous_sibling() or div.find_parent()
                    if category_element:
                        category = category_element.get_text(strip=True)
                        weights[category] = weight
                        
        except Exception as e:
            print(f"Error extracting weights from structure: {str(e)}")
        
        return weights

    def _percentage_to_letter_grade_with_scheme(self, percentage: float, grading_data: List[Dict]) -> str:
        """Convert percentage to letter grade using the course's grading scheme."""
        try:
            # Convert percentage to decimal (0.0 to 1.0)
            decimal_grade = percentage / 100.0
            
            # Sort grading data by value (highest to lowest)
            sorted_grades = sorted(grading_data, key=lambda x: x.get('value', 0), reverse=True)
            
            # Find the appropriate letter grade
            for grade_info in sorted_grades:
                grade_value = grade_info.get('value', 0)
                if decimal_grade >= grade_value:
                    return grade_info.get('name', 'F')
            
            # If no match found, return F
            return 'F'
            
        except Exception as e:
            print(f"Error converting percentage to letter grade: {str(e)}")
            # Fallback to basic conversion
            return self._percentage_to_letter_grade(percentage)

    def _percentage_to_letter_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade using standard scale."""
        if percentage >= 94:
            return "A"
        elif percentage >= 90:
            return "A-"
        elif percentage >= 87:
            return "B+"
        elif percentage >= 84:
            return "B"
        elif percentage >= 80:
            return "B-"
        elif percentage >= 77:
            return "C+"
        elif percentage >= 74:
            return "C"
        elif percentage >= 70:
            return "C-"
        elif percentage >= 67:
            return "D+"
        elif percentage >= 64:
            return "D"
        elif percentage >= 60:
            return "D-"
        else:
            return "F"
