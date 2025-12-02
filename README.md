# Unicode Header Generator

> **unicode_headers.py** – A lightweight utility that downloads the latest Unicode Character Database (UCD) and produces one C/C++ header file per Unicode block.  
> The headers expose a macro for every code point in the form `UC_<UNICODE_NAME>` that expands to its hexadecimal value, e.g. `#define UC_LATIN_SMALL_LETTER_A 0x0061`.

---

## Table of Contents

- [Why this project?](#why-this-project)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)

---

## Why this project?

Working with Unicode in C/C++ can be tedious – you have to remember the exact code‑point values, and maintaining a manual list is error‑prone.  
This script automates the entire process:

1. **Download** After downloading the latest UCD files manually (`Blocks.txt`, `UnicodeData.txt`) from the official Unicode website. You are ready to go.
   Automating this failed even with spoofing the user agent headers.
2. **Parse** the data into a convenient mapping of block → start/end code points and CP → name.
3. **Generate** a header per block that contains one macro per character, complete with comments showing the glyph (if printable) and its canonical name.

The result is a set of headers you can drop straight into any C/C++ project and use constants like `UC_EMOJI_RED_HEART` or `UC_GREEK_CAPITAL_LETTER_ALPHA`.

The aimed use is urob's ZMK unicode extention.

---

## Features

| Feature | Description |
|---------|-------------|
| **Automatic download** | The script checks for the data files locally; if missing, it downloads them on demand. |
| **Retry logic** | Up to 3 attempts per file with a configurable delay. |
| **User‑Agent spoofing** | Uses a modern browser UA to avoid being blocked by `unicode.org`. |
| **Clean macro names** | Unicode names are sanitized into valid C identifiers (`UC_…`). |
| **Glyph comments** | Printable glyphs are shown in the comment for quick visual reference. |
| **Cross‑platform** | Pure Python 3, no external dependencies beyond the standard library. |

---

## Prerequisites

- **Python 3.8+** (the script uses type hints and `list[tuple]` syntax).  
- Internet connection for the first run to download the UCD files.

No other third‑party libraries are required – everything is in the Python stdlib.

---

## Getting Started

```bash
# Clone the repository (or copy unicode_headers.py into your project)
git clone https://github.com/yourname/unicode-header-generator.git
cd unicode-header-generator

# Run the script
python3 unicode_headers.py

