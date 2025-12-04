# Unicode Data and Header Generator

> This project contains two utility scripts for working with the Unicode Character Database (UCD) and generating useful C/C++ headers and structured JSON data.
>
> 1.  **`generate_unicode_headers.py`** – A lightweight utility that produces one C/C++ header file per Unicode block. The headers expose highly abbreviated, clean C macros for every code point in the form `UC_<BLOCK_PREFIX>_<CLEAN_NAME>` that expands to its hexadecimal value.
> 2.  **`generate_blocks_data.py`** – A utility that parses the official `Blocks.txt` and enhances the data by scraping two-paragraph summaries from Wikipedia. The output is a structured JSON file (`unicode_blocks.json`).

---

## Table of Contents

- [Why this project?](#why-this-project)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Virtual Environment Setup (Recommended)](#virtual-environment-setup-recommended)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)

---

## Why this project?

Working with Unicode in C/C++ often requires manually looking up and maintaining exact code-point values, which is tedious and error-prone. This project addresses two major needs:

* **Header Generation:** Automates the creation of clean, short, C-compatible macros for every Unicode code point. It uses **`unicodedata2`** to ensure it's up-to-date with the latest UCD.
* **Data Enrichment:** Automates the gathering of block-level data from **`Blocks.txt`** and enriches it with descriptive, summarized content scraped from Wikipedia, providing a comprehensive JSON resource for block metadata.

The result is a powerful toolset for developers needing simplified access to Unicode constants and structured block information.

---

## Features

| Feature | Script | Description |
|---------|--------|-------------|
| **C/C++ Header Output** | `generate_unicode_headers.py` | Generates a C/C++ header file for every Unicode block, containing constants for each code point. |
| **Multi-Layer Abbreviation** | `generate_unicode_headers.py` | A system to shorten macro names significantly using block prefixes, script abbreviations, and word-specific abbreviations. |
| **JSON Data Output** | `generate_blocks_data.py` | Produces a clean, structured JSON file (`unicode_blocks.json`) containing block ranges, URLs, and descriptions. |
| **Web Scraping** | `generate_blocks_data.py` | Uses `requests` and `beautifulsoup4` to crawl Wikipedia and extract a two-paragraph summary for each Unicode block's description. |
| **Polite Scraping** | `generate_blocks_data.py` | Includes a delay between requests to avoid overwhelming Wikipedia's servers. |
| **Data Source** | `generate_unicode_headers.py` | Pulls data directly from the **`unicodedata2`** package, eliminating the need for manual downloads of UCD files. |
| **Glyph Comments** | `generate_unicode_headers.py` | Printable glyphs are shown in the comment for quick visual reference (e.g., `// ℀`). |

---

## Prerequisites

- **Python 3.8+**
- The libraries listed in `requirements.txt`: **`requests`** (for web fetching), **`beautifulsoup4`** (for HTML parsing), and **`unicodedata2`** (for up-to-date Unicode character data).

---

## Virtual Environment Setup (Recommended)

It is highly recommended to use a **Python virtual environment** (`venv`) to isolate dependencies and prevent conflicts with your system's Python installation.

First, create a `requirements.txt` file in the root directory with the following contents:
```text
unicodedata2
requests
beautifulsoup4
