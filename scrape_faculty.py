"""
Faculty Web Scraper for George Mason University

HOW TO USE FOR OTHER COLLEGES:
1. Update TARGET_URL to point to the desired college's faculty page
2. Ensure departments.csv exists in the data/ directory with all relevant departments
3. Run: python3 scrape_faculty.py
4. Output will be appended to data/faculty.csv

REQUIREMENTS:
- data/departments.csv must exist with columns: department_id, department_name
- BeautifulSoup4 and requests packages installed (see requirements.txt)

CONFIGURATION:
- TARGET_URL: The URL of the faculty page to scrape
- OUTPUT_FILE: Where to save the scraped data
- DEPARTMENTS_FILE: Path to departments.csv for matching
- USE_EMPTY_FOR_NO_MATCH: If True, unmatched departments will be empty string.
                           If False, scraped text will be included for manual review.
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import re
from typing import List, Dict, Optional, Set

# ============================================================================
# CONFIGURATION
# ============================================================================

# Target URL - Change this to scrape different colleges
# Format: https://catalog.gmu.edu/about-mason/faculty/#collegenametext
# Examples:
#   College of Engineering: #collegeofengineeringandcomputingtext
#   College of Science: #collegeofsciencetext
#   Antonin Scalia Law School: #antoninscalialawschooltext
# The scraper will look for a container div with ID: collegenametext + "container"
TARGET_URL = "https://catalog.gmu.edu/about-mason/faculty/#collegeofengineeringandcomputingtext"

# Output file path
OUTPUT_FILE = "data/faculty.csv"

# Departments file for matching
DEPARTMENTS_FILE = "data/departments.csv"

# Faculty ID prefix and format
FACULTY_ID_PREFIX = "F"

# If True: unmatched departments will be empty string
# If False: unmatched departments will include the scraped text for manual review
USE_EMPTY_FOR_NO_MATCH = True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_departments(csv_path: str) -> Dict[str, str]:
    """
    Load departments from CSV and return a mapping of department_name -> department_id.
    Returns empty dict if file doesn't exist.
    """
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found. Department matching will be skipped.")
        return {}
    
    departments = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dept_name = row.get('department_name', '').strip()
                dept_id = row.get('department_id', '').strip()
                if dept_name and dept_id:
                    departments[dept_name] = dept_id
    except Exception as e:
        print(f"Error loading departments: {e}")
    
    return departments


def fuzzy_match_department(text: str, departments: Dict[str, str]) -> Optional[str]:
    """
    Fuzzy/partial case-insensitive match of text against department names.
    Returns department_id if match found, None otherwise.
    """
    if not text or not departments:
        return None
    
    text_lower = text.lower().strip()
    
    # Try exact match first (case-insensitive)
    for dept_name, dept_id in departments.items():
        if text_lower == dept_name.lower():
            return dept_id
    
    # Try partial match - check if department name is contained in text
    for dept_name, dept_id in departments.items():
        dept_lower = dept_name.lower()
        if dept_lower in text_lower or text_lower in dept_lower:
            return dept_id
    
    return None


def get_next_faculty_id(existing_csv_path: str) -> int:
    """
    Determine the next faculty ID by reading existing CSV.
    Returns the next number to use (e.g., if F00005 exists, returns 6).
    """
    if not os.path.exists(existing_csv_path):
        return 1
    
    try:
        with open(existing_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            faculty_ids = [row['faculty_id'] for row in reader]
            
        if not faculty_ids:
            return 1
        
        # Extract numbers from faculty IDs (e.g., "F00005" -> 5)
        numbers = [int(fid.replace(FACULTY_ID_PREFIX, '')) for fid in faculty_ids]
        return max(numbers) + 1
    except Exception as e:
        print(f"Warning: Could not read existing CSV: {e}")
        return 1


def format_faculty_id(number: int) -> str:
    """Format faculty ID with leading zeros (e.g., 1 -> F00001)"""
    return f"{FACULTY_ID_PREFIX}{number:05d}"


def parse_faculty_entry(entry_text: str, departments: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Parse a single faculty entry from various formats:
    - Last, First, Title, Department, College. Academic History.
    - Last, First, Title of Department, College. Academic History.
    - Last, First, Title, College. Academic History. (no department)
    
    Returns a dictionary with parsed fields or None if parsing fails.
    """
    # Split by period, handling middle initials (e.g., "Jan M.")
    # Split on ". " followed by uppercase letter or period at end
    sentences = re.split(r'\.\s+(?=[A-Z])|\.(?=\s*$)', entry_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) == 0:
        return None
    
    # Separate main entry from academic history
    # Academic history has years (4 consecutive digits)
    main_candidates = []
    academic_parts = []
    
    for sentence in sentences:
        if re.search(r'\b\d{4}\b', sentence):
            academic_parts.append(sentence)
        else:
            # Main entry should have at least 2 commas (Last, First, ...)
            if sentence.count(',') >= 2:
                main_candidates.append(sentence)
    
    if not main_candidates:
        # Fallback to first sentence if no good candidates
        if sentences:
            main_candidates = [sentences[0]]
    
    # Prefer sentence with "College of"
    main_sentence = None
    for candidate in main_candidates:
        if "College of" in candidate:
            main_sentence = candidate
            break
    
    if main_sentence is None and main_candidates:
        # Use the one with most commas (most detail)
        main_sentence = max(main_candidates, key=lambda s: s.count(','))
    
    if main_sentence is None:
        return None
    
    # Parse comma-separated fields
    fields = [f.strip() for f in main_sentence.split(',')]
    
    if len(fields) < 3:
        return None
    
    # Fields: Last, First, [Title/Department/College mix]
    last_name = fields[0]
    first_name = fields[1]
    full_name = f"{last_name}, {first_name}"
    
    # Find "College of" to identify the college
    college_idx = None
    college = ""
    for i in range(2, len(fields)):
        if "College of" in fields[i]:
            college = fields[i]
            college_idx = i
            break
    
    # Everything after name and before college is title/department mix
    if college_idx is not None:
        # We have a college
        middle_fields = fields[2:college_idx]
    else:
        # No college, everything after name is title/department mix
        middle_fields = fields[2:]
    
    # Try to identify department from middle fields
    # Strategy: Check each field against departments.csv
    title_parts = []
    department_raw = ""
    department_id = None
    
    for field in middle_fields:
        matched_id = fuzzy_match_department(field, departments)
        if matched_id and department_id is None:
            # Found a department match
            department_id = matched_id
            department_raw = field
            # Everything before this is title
            break
        else:
            title_parts.append(field)
    
    # If no department matched, check if we should include raw text
    if department_id is None and middle_fields:
        # Last field might be department
        if USE_EMPTY_FOR_NO_MATCH:
            department_raw = ""
        else:
            # Include the last middle field as potential department
            if len(middle_fields) > 1:
                title_parts = middle_fields[:-1]
                department_raw = middle_fields[-1]
            else:
                title_parts = middle_fields
                department_raw = ""
    
    title = ", ".join(title_parts) if title_parts else (middle_fields[0] if middle_fields else "")
    
    academic_history = '. '.join(academic_parts)
    
    return {
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "title": title,
        "department": department_raw,
        "department_id": department_id if department_id else "",
        "college": college,
        "academic_history": academic_history
    }


def scrape_faculty(url: str, departments: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Scrape faculty entries from the given URL.
    If URL contains an anchor (#...), attempts to find and scrape only that section.
    
    Structure expected:
    - Container div with ID ending in 'textcontainer' (e.g., collegeofengineeringandcomputingtextcontainer)
    - Inside: may have WordSection divs (WordSection1, WordSection2, etc.) OR just <p> tags
    
    Returns a list of faculty dictionaries.
    """
    print(f"Fetching faculty data from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    faculty_list = []
    
    # Extract anchor from URL (e.g., #collegeofengineeringandcomputingtext)
    anchor_id = None
    container_id = None
    if '#' in url:
        anchor_id = url.split('#')[1]
        # The container typically has 'container' appended to the anchor
        # e.g., collegeofengineeringandcomputingtext -> collegeofengineeringandcomputingtextcontainer
        container_id = anchor_id + 'container'
        print(f"Looking for container with ID: {container_id}")
    
    # Try to find the specific container for this college
    target_container = None
    if container_id:
        target_container = soup.find(id=container_id)
        if target_container:
            print(f"✓ Found college container: {container_id}")
        else:
            # Try just the anchor ID
            target_container = soup.find(id=anchor_id)
            if target_container:
                print(f"✓ Found college section: {anchor_id}")
            else:
                print(f"⚠ Warning: Could not find container '{container_id}' or anchor '{anchor_id}'")
    
    # Determine which sections to scrape
    if target_container:
        # Found the specific college container
        # Check if it has WordSection divs inside
        word_sections = target_container.find_all('div', class_=lambda x: x and x.startswith('WordSection'))
        
        if word_sections:
            sections_to_scrape = word_sections
            print(f"  Found {len(word_sections)} WordSection divs inside container")
        else:
            # No WordSection divs, use the container itself
            sections_to_scrape = [target_container]
            print(f"  No WordSection divs, scraping container directly")
    else:
        # Fallback: scrape all WordSection divs on page (risky - may include other colleges!)
        print(f"⚠ WARNING: Falling back to scraping ALL WordSection divs on page")
        print(f"⚠ This may include faculty from other colleges!")
        word_sections = soup.find_all('div', class_=lambda x: x and x.startswith('WordSection'))
        if word_sections:
            sections_to_scrape = word_sections
            print(f"  Found {len(word_sections)} WordSection divs total")
        else:
            # Last resort: scrape entire page
            sections_to_scrape = [soup]
            print(f"  No WordSection divs found, scraping entire page")
    
    # Scrape paragraphs from target sections
    for i, section in enumerate(sections_to_scrape):
        paragraphs = section.find_all('p')
        print(f"  Section {i+1}: found {len(paragraphs)} paragraphs")
        
        for p in paragraphs:
            # Get the text content
            text = p.get_text(strip=True)
            
            # Skip empty paragraphs
            if not text:
                continue
            
            # Parse the entry
            faculty_data = parse_faculty_entry(text, departments)
            
            if faculty_data:
                faculty_list.append(faculty_data)
            else:
                print(f"  ⚠ Could not parse: {text[:60]}...")
    
    print(f"✓ Successfully parsed {len(faculty_list)} faculty entries")
    return faculty_list


def save_to_csv(faculty_list: List[Dict[str, str]], output_path: str, start_id: int):
    """
    Save faculty data to CSV file.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Check if file exists to determine if we append or write new
    file_exists = os.path.exists(output_path)
    mode = 'a' if file_exists else 'w'
    
    fieldnames = [
        'faculty_id',
        'full_name',
        'first_name',
        'last_name',
        'title',
        'department',
        'department_id',
        'college',
        'academic_history'
    ]
    
    with open(output_path, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header only if creating new file
        if not file_exists:
            writer.writeheader()
        
        # Write faculty entries with sequential IDs
        for i, faculty in enumerate(faculty_list, start=start_id):
            faculty['faculty_id'] = format_faculty_id(i)
            writer.writerow(faculty)
    
    print(f"Saved {len(faculty_list)} faculty entries to {output_path}")
    print(f"Faculty IDs: {format_faculty_id(start_id)} to {format_faculty_id(start_id + len(faculty_list) - 1)}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    print("=" * 70)
    print("GMU Faculty Web Scraper")
    print("=" * 70)
    
    # Load departments for matching
    print(f"Loading departments from: {DEPARTMENTS_FILE}")
    departments = load_departments(DEPARTMENTS_FILE)
    print(f"Loaded {len(departments)} departments for matching")
    
    # Determine starting faculty ID
    start_id = get_next_faculty_id(OUTPUT_FILE)
    print(f"Starting faculty ID: {format_faculty_id(start_id)}")
    
    # Scrape faculty data
    faculty_list = scrape_faculty(TARGET_URL, departments)
    
    if not faculty_list:
        print("No faculty data scraped. Exiting.")
        return
    
    # Report department matching stats
    matched = sum(1 for f in faculty_list if f.get('department_id'))
    print(f"Department matching: {matched}/{len(faculty_list)} faculty matched to departments")
    
    # Save to CSV
    save_to_csv(faculty_list, OUTPUT_FILE, start_id)
    
    print("=" * 70)
    print("Scraping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()