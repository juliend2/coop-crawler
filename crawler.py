#!/usr/bin/env python3
"""
FHCQ Cooperatives Crawler
Crawls the FHCQ cooperatives website and extracts listing data.
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import urllib.parse
from typing import Optional, Dict, List
import re

# Set up a session with headers
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})


# Configuration
BASE_URL = "https://fhcq.coop/fr/cooperatives"
DB_NAME = "cooperatives.db"

# Sector mapping: sector_id -> sector_name
SECTORS = {
    34: "Ahuntsic-Cartierville",
    55: "Dollard-des-Ormeaux",
    40: "Le Plateau-Mont-Royal",
    56: "Outremont",
    45: "Pierrefonds-Roxboro",
    47: "Rosemont – La Petite-Patrie",
    41: "Le Sud-Ouest",
    52: "Villeray-Saint-Michel - Parc-Extension",
}

# Zone mapping: sector_name -> zone_number
ZONE_MAPPING = {
    "Rosemont – La Petite-Patrie": 1,
    "Villeray-Saint-Michel - Parc-Extension": 2,
    "Le Plateau-Mont-Royal": 2,
    "Outremont": 2,
    "Le Sud-Ouest": 2,
    "Ahuntsic-Cartierville": 3,
    "Pierrefonds-Roxboro": 4,
    "Dollard-des-Ormeaux": 4,
}

# Dwelling types to crawl
DWELLING_TYPES = [5, 6, 7]  # 5½, 6½, 7½


def init_database():
    """Initialize the SQLite database with the listings table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            url TEXT NOT NULL UNIQUE,
            has_car_parking INTEGER DEFAULT 0,
            has_bike_parking INTEGER DEFAULT 0,
            zone INTEGER,
            sector TEXT,
            dwelling_type INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    return conn


def get_listing_urls(sector_id: int, dwelling_type: int) -> List[str]:
    """
    Get all listing URLs for a given sector and dwelling type.
    Handles pagination.
    """
    listing_urls = []
    page = 1
    
    while True:
        # Build query parameters
        params = {
            'utf8': '✓',
            'q[feature_available_true]': '0',
            'q[feature_reduced_mobility_true]': '0',
            'q[sector_id_eq]': str(sector_id),
            'q[dwelling_types_id_eq]': str(dwelling_type),
            'commit': 'Rechercher',
            'page': str(page) if page > 1 else None
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = session.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all listing links
            # Looking for links that go to /fr/cooperatives/{slug}
            # Try multiple patterns to find listing links
            listing_links = soup.find_all('a', href=re.compile(r'/fr/cooperatives/[^/?]+$'))
            
            # Also check for links in listing cards/items
            listing_cards = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'coop|listing|item', re.I))
            for card in listing_cards:
                link = card.find('a', href=re.compile(r'/fr/cooperatives/'))
                if link:
                    listing_links.append(link)
            
            page_listings = []
            seen_urls = set(listing_urls)
            for link in listing_links:
                href = link.get('href', '')
                # Normalize href (remove query params, ensure it starts with /)
                if href.startswith('/fr/cooperatives/'):
                    # Remove query parameters and fragments
                    href = href.split('?')[0].split('#')[0]
                    if href != '/fr/cooperatives' and len(href) > len('/fr/cooperatives/'):
                        full_url = f"https://fhcq.coop{href}"
                        if full_url not in seen_urls:
                            page_listings.append(full_url)
                            listing_urls.append(full_url)
                            seen_urls.add(full_url)
            
            # Check if there's a next page
            # Look for pagination links
            next_page_link = (
                soup.find('a', class_=re.compile(r'next', re.I)) or
                soup.find('a', string=re.compile(r'Suivant|Next|›|»', re.I)) or
                soup.find('a', {'rel': 'next'})
            )
            
            if not page_listings:
                break
                
            if not next_page_link and page > 1:
                break
                
            page += 1
            time.sleep(1)  # Be polite to the server
            
        except requests.RequestException as e:
            print(f"Error fetching page {page} for sector {sector_id}, dwelling {dwelling_type}: {e}")
            break
    
    return listing_urls


def extract_listing_data(url: str) -> Optional[Dict]:
    """
    Extract data from a listing detail page.
    Returns a dictionary with the listing data.
    """
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        data = {
            'url': url,
            'name': '',
            'address': '',
            'email': None,
            'phone': None,
            'has_car_parking': False,
            'has_bike_parking': False,
        }
        
        # Extract name - usually in an h1 or title
        # Try multiple selectors
        name_elem = (
            soup.find('h1') or 
            soup.find('h2', class_=re.compile(r'title|name', re.I)) or
            soup.find('div', class_=re.compile(r'title|name', re.I)) or
            soup.find('title')
        )
        if name_elem:
            name_text = name_elem.get_text(strip=True)
            # Clean up title tag (remove " | FHCQ" or similar)
            if '|' in name_text:
                name_text = name_text.split('|')[0].strip()
            data['name'] = name_text
        
        # Extract address - look for address patterns
        # The address might be in various formats, try multiple approaches
        address_patterns = [
            soup.find('address'),
            soup.find('div', class_=re.compile(r'address|adresse', re.I)),
            soup.find('p', class_=re.compile(r'address|adresse', re.I)),
        ]
        
        for pattern in address_patterns:
            if pattern:
                # Use get_text with separator to preserve all text including nested elements
                address_text = pattern.get_text(separator=' ', strip=True)
                # Also try to get all strings from the element to catch any missing parts
                if address_text:
                    # Get all strings to ensure we capture everything
                    all_strings = list(pattern.stripped_strings)
                    if all_strings:
                        # Join all strings to ensure we get the complete address
                        full_address = ' '.join(all_strings)
                        # Use the longer version (more complete)
                        if len(full_address) > len(address_text):
                            address_text = full_address
                
                if address_text and len(address_text) > 10:  # Basic validation
                    data['address'] = address_text
                    break
        
        # If no address found, try to find text that looks like an address by postal code
        if not data['address']:
            # Look for postal code pattern (H1A 1A1) and extract full address context
            postal_code_pattern = re.compile(r'[A-Z]\d[A-Z]\s?\d[A-Z]\d')
            
            # First, try to find the element containing the postal code
            all_elements = soup.find_all(string=postal_code_pattern)
            for element in all_elements:
                parent = element.find_parent()
                if parent:
                    # Get all text from the parent element
                    parent_text = parent.get_text(separator=' ', strip=True)
                    if len(parent_text) > 10:
                        data['address'] = parent_text
                        break
            
            # Fallback: search in full text
            if not data['address']:
                all_text = soup.get_text(separator=' ')
                matches = postal_code_pattern.findall(all_text)
                if matches:
                    # Try to extract surrounding text as address
                    for match in matches:
                        idx = all_text.find(match)
                        if idx > 0:
                            # Get more text before postal code to capture full address
                            start = max(0, idx - 100)
                            end = min(len(all_text), idx + 20)
                            potential_address = all_text[start:end].strip()
                            # Clean up - remove any leading/trailing punctuation
                            potential_address = re.sub(r'^[,\s]+|[,\s]+$', '', potential_address)
                            if len(potential_address) > 10:
                                data['address'] = potential_address
                                break
        
        # Extract email - look for mailto links or email patterns
        email_link = soup.find('a', href=re.compile(r'^mailto:'))
        if email_link:
            data['email'] = email_link['href'].replace('mailto:', '').strip()
        else:
            # Look for email pattern in text
            email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
            email_match = email_pattern.search(soup.get_text())
            if email_match:
                data['email'] = email_match.group(0)
        
        # Extract phone - look for tel: links or phone patterns
        phone_link = soup.find('a', href=re.compile(r'^tel:'))
        if phone_link:
            phone = phone_link['href'].replace('tel:', '').strip()
            # Clean up phone number (remove spaces, normalize)
            phone = re.sub(r'[\s\-\(\)]', '', phone)
            if phone.startswith('1'):
                phone = phone[1:]  # Remove leading 1 for North American numbers
            data['phone'] = phone
        else:
            # Look for phone pattern (various formats)
            # Quebec format: (514) 123-4567, 514-123-4567, 514.123.4567, etc.
            phone_patterns = [
                re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),  # Standard format
                re.compile(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'),  # Without parentheses
            ]
            for pattern in phone_patterns:
                phone_match = pattern.search(soup.get_text())
                if phone_match:
                    phone = phone_match.group(0).strip()
                    # Clean up phone number
                    phone = re.sub(r'[\s\-\(\)\.]', '', phone)
                    if len(phone) == 10:  # Valid 10-digit number
                        data['phone'] = phone
                        break
        
        # Extract parking information from specific HTML elements
        # Look for the features section with icon classes
        features_section = soup.find('p', class_=re.compile(r'coop--features', re.I))
        if features_section:
            # Check for car parking icon
            car_icon = features_section.find('span', class_=re.compile(r'icon-car-side', re.I))
            if car_icon:
                # If the icon doesn't have 'disabled' class, parking is available
                if 'disabled' not in car_icon.get('class', []):
                    data['has_car_parking'] = True
            
            # Check for bike parking icon
            bike_icon = features_section.find('span', class_=re.compile(r'icon-bicycle', re.I))
            if bike_icon:
                # If the icon doesn't have 'disabled' class, parking is available
                if 'disabled' not in bike_icon.get('class', []):
                    data['has_bike_parking'] = True
        else:
            # Fallback: Look for individual icon elements anywhere on the page
            car_icons = soup.find_all('span', class_=re.compile(r'icon-car-side', re.I))
            for car_icon in car_icons:
                if 'disabled' not in car_icon.get('class', []):
                    data['has_car_parking'] = True
                    break
            
            bike_icons = soup.find_all('span', class_=re.compile(r'icon-bicycle', re.I))
            for bike_icon in bike_icons:
                if 'disabled' not in bike_icon.get('class', []):
                    data['has_bike_parking'] = True
                    break
        
        return data
        
    except requests.RequestException as e:
        print(f"Error fetching listing {url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing listing {url}: {e}")
        return None


def save_listing(conn: sqlite3.Connection, listing_data: Dict, sector: str, dwelling_type: int):
    """Save a listing to the database."""
    cursor = conn.cursor()
    zone = ZONE_MAPPING.get(sector, None)
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO listings 
            (name, address, email, phone, url, has_car_parking, has_bike_parking, zone, sector, dwelling_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing_data['name'],
            listing_data['address'],
            listing_data['email'],
            listing_data['phone'],
            listing_data['url'],
            1 if listing_data['has_car_parking'] else 0,
            1 if listing_data['has_bike_parking'] else 0,
            zone,
            sector,
            dwelling_type
        ))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving listing {listing_data['url']}: {e}")
        return False


def main():
    """Main crawler function."""
    print("Initializing database...")
    conn = init_database()
    
    total_combinations = len(SECTORS) * len(DWELLING_TYPES)
    current = 0
    
    print(f"Starting crawl for {len(SECTORS)} sectors × {len(DWELLING_TYPES)} dwelling types = {total_combinations} combinations")
    
    for sector_id, sector_name in SECTORS.items():
        for dwelling_type in DWELLING_TYPES:
            current += 1
            print(f"\n[{current}/{total_combinations}] Processing: {sector_name} - {dwelling_type}½")
            
            # Get all listing URLs for this combination
            listing_urls = get_listing_urls(sector_id, dwelling_type)
            print(f"  Found {len(listing_urls)} listings")
            
            # Process each listing
            for i, url in enumerate(listing_urls, 1):
                print(f"  [{i}/{len(listing_urls)}] Processing: {url}")
                listing_data = extract_listing_data(url)
                
                if listing_data:
                    if save_listing(conn, listing_data, sector_name, dwelling_type):
                        print(f"    ✓ Saved: {listing_data['name']}")
                    else:
                        print(f"    ✗ Failed to save")
                else:
                    print(f"    ✗ Failed to extract data")
                
                time.sleep(1)  # Be polite to the server
    
    conn.close()
    print("\n✓ Crawl completed!")


if __name__ == "__main__":
    main()

