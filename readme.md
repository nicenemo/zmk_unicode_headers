# Unicode Header Generator

> **generate_unicode_headers.py** – A lightweight utility that produces one C/C++ header file per Unicode block.
> The headers expose highly abbreviated, clean C macros for every code point in the form `UC_<BLOCK_PREFIX>_<CLEAN_NAME>` that expands to its hexadecimal value.
>
> **Example of Abbreviation (Before → After):**
> `#define UC_MATHEMATICAL_ALPHANUMERIC_SYMBOLS_SANS_SERIF_BOLD_DIGIT_ZERO 0x1D7EC`
> **↓**
> `#define UC_MA_SS_BOLD_ZERO 0x1D7EC`

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

Working with Unicode in C/C++ often requires manually looking up and maintaining exact code-point values, which is tedious and error-prone. This script automates the entire process and now provides C macros that are both clean and short.

1.  **Data Source:** The script is now fully self-contained, using the modern **`unicodedata2`** Python package to pull all official Unicode Character Database (UCD) information, including character names, code points, and block definitions, ensuring it is always up-to-date with the latest standard.
2.  **Abbreviation:** A multi-layered abbreviation process sanitizes the long, verbose Unicode character names into macros that are suitable for use in restricted identifier environments.
3.  **Generate:** A single C/C++ header is generated for every Unicode block, ready to be dropped into any project.

The result is a set of headers you can use constants like `UC_MA_DS_CAPITAL_C` (for `DOUBLE-STRUCK CAPITAL C` in the Mathematical Alphanumeric Symbols block) or `UC_LA_SMALL_A` (for `LATIN SMALL LETTER A`).

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Layer Abbreviation** | A three-layer system shortens macro names significantly by applying: **1.** A 2-4 letter block prefix (e.g., `UC_MA_` for Mathematical Alphanumeric Symbols). **2.** Script/Language abbreviations (e.g., `CY` for CYRILLIC, `EL` for GREEK). **3.** Word-specific abbreviations (`DS` for DOUBLE_STRUCK, `SS` for SANS_SERIF) and removal of highly redundant words (`DIGIT`, `NUMBER`).|
| **Clean Macro Names** | Unicode names are sanitized, converted to uppercase, and separated by underscores (`UC_…`), resulting in valid C identifiers.|
| **Data Source** | Data is pulled directly from the **`unicodedata2`** package, eliminating the need for manual downloads or **maintaining local UCD files (like `Blocks.txt`)**.|
| **Glyph Comments** | Printable glyphs are shown in the comment for quick visual reference (e.
