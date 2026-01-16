"""
GMU CEC Grants Web Scraper - Offline Mode

Scrapes grant information from a saved HTML file of the GMU College of Engineering 
and Computing grants page. Creates a CSV file with grant details including funding 
amount, source, reason, date, and awardees.

USAGE:
    python3 scrape_grants.py grants_page.html

HOW TO GET THE HTML FILE:
    1. Open your web browser
    2. Visit: https://cec.gmu.edu/research/grants
    3. Right-click on the page -> "Save Page As..." or Ctrl+S
    4. Save as: grants_page.html (in the same directory as this script)
    5. Run: python3 scrape_grants.py grants_page.html

OUTPUT:
    data/grants_cec.csv - CSV file with columns:
        - grant_id: Unique identifier (G00001, G00002, etc.)
        - funding: Dollar amount (integer, no commas)
        - sponsor: Funding source/organization
        - awardee: Faculty member name
        - title: Grant title/reason (may be blank if no "for" clause)
        - date: Award date in ISO format (YYYY-MM-DD)
        - is_anticipated: Boolean (True if "anticipated funding", False if "award amount")
        - department_id: Department ID (blank for manual review)
        - capabilities_id: Capability ID (blank for manual review)

NOTES:
    - Multiple awardees create separate rows with the same grant data
    - Funding amounts are parsed from strings like "$100,000" or "$1,500"
    - Dates are converted from "January 12, 2026" to "2026-01-12"
"""

from bs4 import BeautifulSoup
import csv
import os
import re
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_FILE = "../data/csv/grants_cec.csv"
GRANT_ID_PREFIX = "G"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_date(date_str: str) -> str:
    """
    Convert date from 'January 12, 2026' to '2026-01-12' (ISO format).
    
    Args:
        date_str: Date string in format "Month DD, YYYY"
    
    Returns:
        ISO format date string "YYYY-MM-DD"
    """
    try:
        date_obj = datetime.strptime(date_str.strip(), "%B %d, %Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        # If parsing fails, return the original string
        print(f"  ⚠ Warning: Could not parse date '{date_str}'")
        return date_str.strip()


def parse_funding_amount(amount_str: str) -> Tuple[Optional[int], bool]:
    """
    Parse funding amount from strings like "$100,000" or "Anticipated funding: $1,500".
    
    Args:
        amount_str: String containing funding amount
    
    Returns:
        Tuple of (amount as integer, is_anticipated boolean)
    """
    # Check if it's anticipated or awarded
    is_anticipated = "anticipated" in amount_str.lower()
    
    # Extract the dollar amount
    # Match patterns like $100,000 or $1,500 or $1.5M
    match = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*([MmKk])?', amount_str)
    
    if match:
        amount_str = match.group(1).replace(',', '')
        multiplier = match.group(2)
        
        try:
            amount = float(amount_str)
            
            # Handle M (millions) and K (thousands) suffixes
            if multiplier:
                if multiplier.upper() == 'M':
                    amount *= 1_000_000
                elif multiplier.upper() == 'K':
                    amount *= 1_000
            
            return (int(amount), is_anticipated)
        except ValueError:
            print(f"  ⚠ Warning: Could not parse amount '{amount_str}'")
            return (None, is_anticipated)
    
    return (None, is_anticipated)


def parse_awardees(awardee_str: str) -> List[str]:
    """
    Parse awardee string to extract individual faculty names.
    
    Handles cases like:
    - "Kai Zeng"
    - "Brian L. Mark and Kai Zeng"
    - "Bo Han, Parth Pathak, and Lap Fai Yu"
    
    Args:
        awardee_str: String containing one or more names
    
    Returns:
        List of individual faculty names
    """
    # Split on " and " and commas
    # First replace " and " with a comma for uniform splitting
    normalized = awardee_str.replace(' and ', ', ')
    
    # Split on commas
    names = [name.strip() for name in normalized.split(',')]
    
    # Filter out empty strings and common words
    names = [name for name in names if name and name.lower() not in ['', 'and']]
    
    return names


def parse_grant_entry(entry_text: str) -> Optional[Dict[str, any]]:
    """
    Parse a single grant entry from the HTML text.
    
    Handles two formats:
    
    NEW FORMAT (2023-2026):
    [Name] receives/received funding from [Source]
    [Name] receives/received funding from [Source] for [Title].
    Anticipated funding: $X
    Date
    
    OLD FORMAT (2022-2023):
    [Name] receive(s)/received funding from [Source] for [Title]. Grant total: $X.
    Date
    
    Args:
        entry_text: Text content of a grant entry
    
    Returns:
        Dictionary with parsed grant data or None if parsing fails
    """
    lines = [line.strip() for line in entry_text.split('\n') if line.strip()]
    
    if len(lines) < 2:
        return None
    
    # Try to find the detail line (contains "received funding from" or "receives funding from")
    # Prefer lines that also contain "for" (those have the title)
    detail_line = None
    detail_line_idx = -1
    
    # First pass: look for lines with both "receive" and "for"
    for i, line in enumerate(lines):
        if re.search(r'receive[sd]?\s+funding\s+from', line, re.IGNORECASE) and ' for ' in line.lower():
            detail_line = line
            detail_line_idx = i
            break
    
    # Second pass: if not found, accept any line with "receive"
    if not detail_line:
        for i, line in enumerate(lines):
            if re.search(r'receive[sd]?\s+funding\s+from', line, re.IGNORECASE):
                detail_line = line
                detail_line_idx = i
                break
    
    if not detail_line:
        return None
    
    # Pattern: [Name(s)] receive(s)/received funding from [Source] for [Title]
    # Title should stop before funding amount keywords
    pattern = r'^(.+?)\s+receive[sd]?\s+funding\s+from\s+(.+?)(?:\s+for\s+(.+?))?(?:\s*(?:Anticipated funding|Grant total|Award amount|Award))?\.?\s*$'
    match = re.search(pattern, detail_line, re.IGNORECASE)
    
    if not match:
        return None
    
    awardee_str = match.group(1)
    sponsor = match.group(2)
    title = match.group(3) if match.group(3) else ""
    
    # Clean up title - remove quotes, funding amounts, and trailing periods
    # Remove funding information if it got captured in title
    title = re.sub(r'[."\']?\s*(?:Anticipated funding|Grant total|Award amount|Award)[:\s]+\$.*$', '', title, flags=re.IGNORECASE)
    title = title.strip().strip('"').strip("'").rstrip('.')
    
    # Find funding amount
    # Can be in the detail line (old format) or separate line (new format)
    funding = None
    is_anticipated = False
    
    # Check detail line first (old format: "... for Title. Grant total: $X.")
    detail_funding_match = re.search(r'(Grant total|Anticipated funding|Award amount)[:\s]+\$\s*([\d,]+)', detail_line, re.IGNORECASE)
    if detail_funding_match:
        funding, is_anticipated = parse_funding_amount(detail_funding_match.group(0))
    else:
        # Check other lines (new format)
        for line in lines:
            if '$' in line and ('funding' in line.lower() or 'award' in line.lower() or 'grant' in line.lower()):
                funding, is_anticipated = parse_funding_amount(line)
                if funding:
                    break
    
    # Find date (should be last line or part of detail line)
    date = None
    
    # Try to find date in separate line first
    for line in reversed(lines):
        # Skip lines with dollar signs or "funding" (those are amount lines)
        if '$' in line or 'funding' in line.lower():
            continue
        # Try to parse as date
        try:
            # Date might have period at end
            clean_line = line.rstrip('.')
            parsed_date = parse_date(clean_line)
            if parsed_date != clean_line:  # Successfully parsed
                date = parsed_date
                break
        except:
            continue
    
    # Parse individual awardees
    awardees = parse_awardees(awardee_str)
    
    return {
        'awardees': awardees,
        'sponsor': sponsor.strip(),
        'title': title.strip(),
        'funding': funding,
        'is_anticipated': is_anticipated,
        'date': date
    }


def format_grant_id(number: int) -> str:
    """Format grant ID with leading zeros (e.g., 1 -> G00001)"""
    return f"{GRANT_ID_PREFIX}{number:05d}"


def scrape_grants_from_file(file_path: str) -> List[Dict[str, any]]:
    """
    Scrape grant entries from a saved HTML file.
    
    Args:
        file_path: Path to the HTML file
    
    Returns:
        List of grant dictionaries
    """
    print(f"Reading grants data from file: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"✗ Error: File not found: {file_path}")
        print("\nHow to get the HTML file:")
        print("  1. Open your web browser")
        print("  2. Visit: https://cec.gmu.edu/research/grants")
        print("  3. Right-click -> 'Save Page As...' or press Ctrl+S")
        print(f"  4. Save as: {file_path}")
        print(f"  5. Run: python3 scrape_grants.py {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return []
    
    print(f"  File size: {len(html_content):,} characters")
    return parse_html_content(html_content)


def parse_html_content(html_content) -> List[Dict[str, any]]:
    """
    Parse grant entries from HTML content.
    
    Args:
        html_content: HTML content (bytes or string)
    
    Returns:
        List of grant dictionaries
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    grants_list = []
    
    # Find the main content div
    # Based on the HTML structure, grants are in <p> tags with various formats:
    # - Newer entries: <p class="MsoNormal"> or <p class="p1">
    # - Older entries: <p><span> (no class attribute)
    # Each grant is typically 2-4 lines separated by <hr> tags
    
    # Find all paragraph tags that might contain grants
    # Include both paragraphs with classes AND paragraphs without classes
    all_paragraphs = soup.find_all('p')
    
    print(f"  Found {len(all_paragraphs)} paragraph elements total")
    
    # Filter to only content paragraphs (skip navigation, headers, etc.)
    # Keep paragraphs that either:
    # 1. Have a class like MsoNormal, p1, p2
    # 2. Have a <span> child (older grant format)
    # 3. Have <strong> child (grant headers)
    paragraphs = []
    for p in all_paragraphs:
        has_class = p.get('class') and any(cls in ['MsoNormal', 'p1', 'p2'] for cls in p.get('class', []))
        has_span = p.find('span') is not None
        has_strong = p.find('strong') is not None
        
        if has_class or has_span or has_strong:
            paragraphs.append(p)
    
    print(f"  Filtered to {len(paragraphs)} relevant paragraphs")
    
    current_entry_lines = []
    entry_count = 0
    
    for i, p in enumerate(paragraphs):
        # Use separator to properly handle <br> tags
        text = p.get_text(separator='\n', strip=True)
        
        # Skip empty paragraphs
        if not text:
            continue
        
        # Check if this is the start of a new grant entry (bold header with "receives")
        # This is typically in a <strong> tag
        is_header = p.find('strong') is not None and 'receive' in text.lower()
        
        if is_header:
            # This is the start of a new entry
            if current_entry_lines:
                # Parse the previous entry
                entry_text = '\n'.join(current_entry_lines)
                parsed = parse_grant_entry(entry_text)
                if parsed:
                    grants_list.append(parsed)
                    entry_count += 1
            
            # Start new entry
            current_entry_lines = [text]
        else:
            # Continue building current entry
            if current_entry_lines:
                current_entry_lines.append(text)
                
                # Old format entries are only 2 lines, new format can be 3-4 lines
                # Try to parse after collecting 2-4 lines
                if len(current_entry_lines) >= 2:
                    # Check if this looks complete (has both funding and date)
                    entry_text = '\n'.join(current_entry_lines)
                    
                    # Old format: detail line contains both funding amount and date info
                    # New format: separate lines for funding and date
                    has_funding = any('$' in line for line in current_entry_lines)
                    has_date = any(re.search(r'\b\d{4}\b', line) for line in current_entry_lines)
                    
                    # If we have both funding and date, or we've collected 4+ lines, try to parse
                    if (has_funding and has_date) or len(current_entry_lines) >= 4:
                        parsed = parse_grant_entry(entry_text)
                        if parsed and parsed.get('date'):  # Only accept if we got a date
                            grants_list.append(parsed)
                            entry_count += 1
                            current_entry_lines = []  # Reset for next entry
    
    # Don't forget the last entry
    if current_entry_lines and len(current_entry_lines) >= 2:
        entry_text = '\n'.join(current_entry_lines)
        parsed = parse_grant_entry(entry_text)
        if parsed:
            grants_list.append(parsed)
            entry_count += 1
    
    print(f"✓ Successfully parsed {len(grants_list)} grant entries")
    return grants_list


def save_to_csv(grants_list: List[Dict[str, any]], output_path: str):
    """
    Save grants data to CSV file.
    Creates separate rows for each awardee when there are multiple awardees.
    
    Args:
        grants_list: List of grant dictionaries
        output_path: Path to output CSV file
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fieldnames = [
        'grant_id',
        'funding',
        'sponsor',
        'awardee',
        'title',
        'date',
        'is_anticipated',
        'department_id',
        'capabilities_id'
    ]
    
    rows = []
    grant_counter = 1
    
    # Expand grants with multiple awardees into separate rows
    for grant in grants_list:
        awardees = grant.get('awardees', [])
        
        if not awardees:
            # No awardees found, create one row with empty awardee
            rows.append({
                'grant_id': format_grant_id(grant_counter),
                'funding': grant.get('funding', ''),
                'sponsor': grant.get('sponsor', ''),
                'awardee': '',
                'title': grant.get('title', ''),
                'date': grant.get('date', ''),
                'is_anticipated': grant.get('is_anticipated', False),
                'department_id': '',
                'capabilities_id': ''
            })
            grant_counter += 1
        else:
            # Create one row per awardee
            for awardee in awardees:
                rows.append({
                    'grant_id': format_grant_id(grant_counter),
                    'funding': grant.get('funding', ''),
                    'sponsor': grant.get('sponsor', ''),
                    'awardee': awardee,
                    'title': grant.get('title', ''),
                    'date': grant.get('date', ''),
                    'is_anticipated': grant.get('is_anticipated', False),
                    'department_id': '',
                    'capabilities_id': ''
                })
                grant_counter += 1
    
    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Saved {len(rows)} grant records to {output_path}")
    print(f"  (From {len(grants_list)} unique grants with multiple awardees expanded)")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    print("=" * 70)
    print("GMU CEC Grants Web Scraper - Offline Mode")
    print("=" * 70)
    
    # Check for file path argument
    if len(sys.argv) < 2:
        print("\n✗ Error: No HTML file specified")
        print("\nUsage:")
        print("  python3 scrape_grants.py FILENAME.html")
        print("\nExample:")
        print("  python3 scrape_grants.py grants_page.html")
        print("\nHow to get the HTML file:")
        print("  1. Open your web browser")
        print("  2. Visit: https://cec.gmu.edu/research/grants")
        print("  3. Right-click -> 'Save Page As...' or press Ctrl+S")
        print("  4. Save as: grants_page.html")
        print("  5. Run: python3 scrape_grants.py grants_page.html")
        return
    
    if sys.argv[1] in ['-h', '--help', 'help']:
        print("\nUsage:")
        print("  python3 scrape_grants.py FILENAME.html")
        print("\nExample:")
        print("  python3 scrape_grants.py grants_page.html")
        print("\nHow to get the HTML file:")
        print("  1. Visit https://cec.gmu.edu/research/grants in your browser")
        print("  2. Right-click -> 'Save Page As...'")
        print("  3. Save as grants_page.html")
        print("  4. Run the scraper on the saved file")
        return
    
    file_path = sys.argv[1]
    
    # Scrape from file
    grants_list = scrape_grants_from_file(file_path)
    
    if not grants_list:
        print("\n✗ No grants data scraped. Exiting.")
        return
    
    # Save to CSV
    save_to_csv(grants_list, OUTPUT_FILE)
    
    print("\n" + "=" * 70)
    print("✓ Scraping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()