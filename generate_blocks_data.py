#!/usr/bin/env python3
"""
This script parses the Unicode Blocks.txt file, extracts Unicode block ranges
and names, generates relevant Wikipedia and official Unicode charts URLs,
and then performs web scraping on the Wikipedia URLs to fetch a two-paragraph
summary for each block.

The structured data, including the scraped description, is written to a JSON
file named unicode_blocks.json.
"""
import json
import re
import os
import time
from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup, Tag

# --- Configuration ---
# Define the input and output file names
INPUT_FILE = "Blocks.txt"
OUTPUT_FILE = "unicode_blocks.json"

# Base URLs for generating links
WIKI_BASE_URL = "https://en.wikipedia.org/wiki/"
CHART_BASE_URL = "https://www.unicode.org/charts/PDF/"

# Regular expression to parse lines in the format: Start..End; Block Name
BLOCK_RE = re.compile(r'([0-9A-Fa-f]+)\.\.([0-9A-Fa-f]+);\s*([^#]+)')

# Define a delay between web requests to be a polite scraper (e.g., 0.5 seconds)
SLEEP_DELAY = 0.5

# Define a common User-Agent string to help Wikipedia identify the request
# Note: Falsifying a User-Agent is discouraged, but a standard one is helpful.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- URL Generation Helpers ---

def generate_wikipedia_url(block_name: str) -> str:
    """Generates a Wikipedia URL-friendly string from the Unicode block name."""
    # Replace spaces and hyphens with underscores, strip whitespace, and URL encode the result
    sanitized_name = block_name.strip().replace(' ', '_').replace('-', '_')
    return f"{WIKI_BASE_URL}{quote(sanitized_name)}"

def generate_charts_url(start_code_hex: str) -> str:
    """Generates the official Unicode charts URL from the starting code point."""
    # Format the start code (e.g., '0000' -> 'U0000')
    u_code = f"U{start_code_hex}"
    return f"{CHART_BASE_URL}{u_code}.pdf"

# --- Web Scraper Function ---

def scrape_wikipedia_summary(url: str, num_paragraphs: int = 2) -> str:
    """
    Fetches a Wikipedia article and extracts the first N paragraphs of the summary.

    Args:
        url: The full URL of the Wikipedia article.
        num_paragraphs: The number of paragraphs to extract for the description.

    Returns:
        A string containing the concatenated paragraphs, or a failure message.
    """
    try:
        # Send a GET request with a user agent
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        # Handle connection errors, timeouts, and bad status codes
        return f"Error fetching Wikipedia page: {e}"

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Wikipedia article content is typically within a div with class 'mw-parser-output'
    parser_output: Optional[Tag] = soup.find('div', class_='mw-parser-output')
    if not parser_output:
        return "Could not find main article content on the page."

    paragraphs: List[str] = []
    # Find all direct paragraph children
    for tag in parser_output.find_all('p', recursive=False):
        # Skip empty paragraphs or those that are part of other elements (e.g., tables)
        if not tag.text.strip():
            continue

        # Extract text, removing Wikipedia reference tags (e.g., [1], [2])
        # .get_text() with separator ' ' handles complex tags (like links) well
        text = tag.get_text(separator=' ', strip=True)

        # Simple regex to remove citation brackets like [1], [2], [A], etc.
        clean_text = re.sub(r'\[.*?\]', '', text).strip()
        
        if clean_text:
            paragraphs.append(clean_text)
        
        if len(paragraphs) >= num_paragraphs:
            break
    
    if paragraphs:
        # Join the paragraphs with a double newline for separation
        return "\n\n".join(paragraphs)
    else:
        return "Summary content not found or page structure is unexpected."

# --- Main Logic ---

def generate_block_data(input_file: str, output_file: str):
    """
    Parses Blocks.txt, generates metadata, scrapes Wikipedia for descriptions,
    and writes the structured data (list of dictionaries) to a JSON file.

    Args:
        input_file: The path to the source Blocks.txt file.
        output_file: The path to the destination JSON file.
    """
    blocks_data: List[Dict[str, str]] = []
    
    print(f"Starting data generation and scraping...")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                match = BLOCK_RE.match(line)

                if match:
                    start_code_raw = match.group(1).upper()
                    block_name = match.group(3).strip()
                    
                    # Generate URLs
                    wiki_url = generate_wikipedia_url(block_name)

                    # --- New: Web Scraping Step ---
                    print(f"-> Scraping summary for: {block_name}...")
                    description = scrape_wikipedia_summary(wiki_url)
                    
                    # Be a polite scraper: wait for a moment between requests
                    time.sleep(SLEEP_DELAY) 
                    # -----------------------------
                    
                    # ... (rest of data extraction)
                    end_code_raw = match.group(2).upper()
                    start_code_hex = start_code_raw.zfill(4)
                    end_code_hex = end_code_raw.zfill(4)
                    
                    block_entry = {
                        "name": block_name,
                        "start": start_code_hex,
                        "end": end_code_hex,
                        "wikipedia_url": wiki_url,
                        "unicode_charts_url": generate_charts_url(start_code_hex),
                        "description": description
                    }
                    blocks_data.append(block_entry)

    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_file}' not found. Please ensure it exists.")
        return
    except Exception as e:
        print(f"❌ An unexpected error occurred while processing '{input_file}': {e}")
        # Note: If an error occurs during scraping, it is handled within the
        # scrape_wikipedia_summary function, so it shouldn't stop the main loop
        # unless it's a critical I/O error here.
        return

    # Write the collected data to the JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(blocks_data, f, indent=4)

        print(f"\n✅ Successfully generated block data for {len(blocks_data)} blocks into '{output_file}'.")
    except Exception as e:
        print(f"❌ Error writing to output file '{output_file}': {e}")


if __name__ == "__main__":
    generate_block_data(INPUT_FILE, OUTPUT_FILE)
