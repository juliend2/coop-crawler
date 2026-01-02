#!/usr/bin/env python3
"""
Utility script to query the cooperatives database.
"""

import sqlite3
import sys
from tabulate import tabulate


def query_listings(query_type="all", **kwargs):
    """Query listings from the database."""
    conn = sqlite3.connect("cooperatives.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if query_type == "all":
        cursor.execute("SELECT * FROM listings ORDER BY name")
    elif query_type == "zone":
        zone = kwargs.get("zone")
        cursor.execute("SELECT * FROM listings WHERE zone = ? ORDER BY name", (zone,))
    elif query_type == "sector":
        sector = kwargs.get("sector")
        cursor.execute("SELECT * FROM listings WHERE sector = ? ORDER BY name", (sector,))
    elif query_type == "parking":
        parking_type = kwargs.get("parking_type", "car")
        if parking_type == "car":
            cursor.execute("SELECT * FROM listings WHERE has_car_parking = 1 ORDER BY name")
        else:
            cursor.execute("SELECT * FROM listings WHERE has_bike_parking = 1 ORDER BY name")
    elif query_type == "dwelling":
        dwelling_type = kwargs.get("dwelling_type")
        cursor.execute("SELECT * FROM listings WHERE dwelling_type = ? ORDER BY name", (dwelling_type,))
    else:
        print(f"Unknown query type: {query_type}")
        return
    
    rows = cursor.fetchall()
    
    if not rows:
        print("No listings found.")
        return
    
    # Convert to list of dicts for tabulate
    data = []
    for row in rows:
        data.append({
            "ID": row["id"],
            "Name": row["name"],
            "Address": row["address"][:50] + "..." if len(row["address"]) > 50 else row["address"],
            "Email": row["email"] or "N/A",
            "Phone": row["phone"] or "N/A",
            "Zone": row["zone"] or "N/A",
            "Sector": row["sector"],
            "Dwelling": f"{row['dwelling_type']}½",
            "Car Parking": "Yes" if row["has_car_parking"] else "No",
            "Bike Parking": "Yes" if row["has_bike_parking"] else "No",
        })
    
    print(tabulate(data, headers="keys", tablefmt="grid"))
    print(f"\nTotal: {len(rows)} listings")
    
    conn.close()


def stats():
    """Show database statistics."""
    conn = sqlite3.connect("cooperatives.db")
    cursor = conn.cursor()
    
    # Total listings
    cursor.execute("SELECT COUNT(*) FROM listings")
    total = cursor.fetchone()[0]
    
    # By zone
    cursor.execute("SELECT zone, COUNT(*) FROM listings GROUP BY zone ORDER BY zone")
    by_zone = cursor.fetchall()
    
    # By sector
    cursor.execute("SELECT sector, COUNT(*) FROM listings GROUP BY sector ORDER BY sector")
    by_sector = cursor.fetchall()
    
    # By dwelling type
    cursor.execute("SELECT dwelling_type, COUNT(*) FROM listings GROUP BY dwelling_type ORDER BY dwelling_type")
    by_dwelling = cursor.fetchall()
    
    # Parking stats
    cursor.execute("SELECT COUNT(*) FROM listings WHERE has_car_parking = 1")
    with_car_parking = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE has_bike_parking = 1")
    with_bike_parking = cursor.fetchone()[0]
    
    print("=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)
    print(f"\nTotal listings: {total}")
    
    print("\nBy Zone:")
    for zone, count in by_zone:
        print(f"  Zone {zone}: {count}")
    
    print("\nBy Sector:")
    for sector, count in by_sector:
        print(f"  {sector}: {count}")
    
    print("\nBy Dwelling Type:")
    for dwelling, count in by_dwelling:
        print(f"  {dwelling}½: {count}")
    
    print("\nParking:")
    print(f"  With car parking: {with_car_parking}")
    print(f"  With bike parking: {with_bike_parking}")
    print("=" * 50)
    
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python query_db.py stats                    # Show statistics")
        print("  python query_db.py all                      # Show all listings")
        print("  python query_db.py zone <zone_number>       # Show listings by zone")
        print("  python query_db.py sector <sector_name>    # Show listings by sector")
        print("  python query_db.py parking [car|bike]       # Show listings with parking")
        print("  python query_db.py dwelling <type>          # Show listings by dwelling type")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "stats":
        stats()
    elif command == "all":
        query_listings("all")
    elif command == "zone":
        if len(sys.argv) < 3:
            print("Error: Zone number required")
            sys.exit(1)
        query_listings("zone", zone=int(sys.argv[2]))
    elif command == "sector":
        if len(sys.argv) < 3:
            print("Error: Sector name required")
            sys.exit(1)
        query_listings("sector", sector=sys.argv[2])
    elif command == "parking":
        parking_type = sys.argv[2] if len(sys.argv) > 2 else "car"
        query_listings("parking", parking_type=parking_type)
    elif command == "dwelling":
        if len(sys.argv) < 3:
            print("Error: Dwelling type required (5, 6, or 7)")
            sys.exit(1)
        query_listings("dwelling", dwelling_type=int(sys.argv[2]))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

