# FHCQ Cooperatives Crawler

(THIS WAS ALL VIBE-CODED)

A web crawler that extracts cooperative housing listings from the FHCQ (Fédération de l'habitation coopérative du Québec) website.

## Features

- Crawls listings for 8 specific sectors
- Filters by dwelling types: 5½, 6½, and 7½
- Classifies listings into 4 zones
- Extracts: name, address, email, phone, URL, parking information
- Stores data in SQLite database

## Zone Classification

- **Zone 1**: Rosemont – La Petite-Patrie
- **Zone 2**: Villeray-Saint-Michel - Parc-Extension, Le Plateau-Mont-Royal, Outremont, Le Sud-Ouest
- **Zone 3**: Ahuntsic-Cartierville
- **Zone 4**: Pierrefonds-Roxboro, Dollard-des-Ormeaux

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python crawler.py
```

The crawler will:
1. Create a SQLite database (`cooperatives.db`)
2. Iterate through all sector/dwelling type combinations
3. Extract listing data from each detail page
4. Save data to the database

## Database Schema

The `listings` table contains:
- `id`: Primary key
- `name`: Cooperative name
- `address`: Full address
- `email`: Email address (nullable)
- `phone`: Phone number (nullable)
- `url`: Listing URL
- `has_car_parking`: Boolean (0/1)
- `has_bike_parking`: Boolean (0/1)
- `zone`: Zone number (1-4)
- `sector`: Sector name
- `dwelling_type`: Dwelling type (5, 6, or 7)
- `created_at`: Timestamp

## Web Interface

A PHP web interface is available to display the listings in a nice table format.

### Requirements

- PHP 7.4+ with PDO SQLite support
- Web server (Apache, Nginx, or PHP built-in server)

### Usage

```bash
# Using PHP built-in server
php -S localhost:8000

# Then open http://localhost:8000 in your browser
```

The interface includes:
- Statistics dashboard
- Filtering by zone, sector, dwelling type, and parking
- Sortable columns
- Responsive design
- Clickable email and phone links

## Querying the Database

### Using the Query Utility

```bash
# Show database statistics
python query_db.py stats

# Show all listings
python query_db.py all

# Show listings by zone
python query_db.py zone 2

# Show listings by sector
python query_db.py sector "Le Plateau-Mont-Royal"

# Show listings with parking
python query_db.py parking car
python query_db.py parking bike

# Show listings by dwelling type
python query_db.py dwelling 5
```

### Using Python Directly

```python
import sqlite3

conn = sqlite3.connect('cooperatives.db')
cursor = conn.cursor()

# Get all listings in Zone 2
cursor.execute("SELECT * FROM listings WHERE zone = 2")

# Get listings with car parking
cursor.execute("SELECT * FROM listings WHERE has_car_parking = 1")

# Get listings by sector
cursor.execute("SELECT * FROM listings WHERE sector = ?", ("Le Plateau-Mont-Royal",))
```

