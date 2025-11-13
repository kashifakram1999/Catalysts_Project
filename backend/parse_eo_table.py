#!/usr/bin/env python3
"""
Parse EO search results HTML to see table structure
"""
from bs4 import BeautifulSoup

# Read the saved HTML
with open('eo_search_result.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# Find the results table
table = soup.find('table', id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData')

if table:
    print("="*80)
    print("TABLE HEADERS")
    print("="*80)

    # Get header row
    headers = table.find_all('th')
    for idx, header in enumerate(headers):
        print(f"Column {idx}: {header.text.strip()}")

    print("\n" + "="*80)
    print("FIRST DATA ROW")
    print("="*80)

    # Get first data row
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if cells and len(cells) > 5:  # Data row
            for idx, cell in enumerate(cells):
                print(f"Cell {idx}: {cell.text.strip()}")
            break
else:
    print("Table not found!")
