from login import login_to_canvas
import os
from load_config import load_config

def fetch_grades_page(course_id):
    config = load_config()
    session = login_to_canvas(config)
    if not session:
        print("Failed to create session")
        return False
        
    response = session.session.get(f'{session.base_url}/courses/{course_id}/grades')
    if response.status_code != 200:
        print(f"Failed to get grades page: {response.status_code}")
        return False
        
    os.makedirs('tests/test_data', exist_ok=True)
    with open('tests/test_data/real_grades_page.html', 'w') as f:
        f.write(response.text)
    print("Successfully saved grades page")
    return True

if __name__ == "__main__":
    fetch_grades_page("102017") 