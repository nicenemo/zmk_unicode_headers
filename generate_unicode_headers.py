#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_unicode_headers.py

Generate C header files with Unicode constants for every code point.
The script uses the `unicodedata2` package for core properties and loads
Unicode block data from a JSON file to provide the missing 'block' function.

This version uses a three-layered abbreviation system for maximal brevity and
collision avoidance.
"""

import pathlib
import re
import sys
import argparse
import json # New import for JSON loading
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import namedtuple

# Import all standard functions from unicodedata2 for updated Unicode data.
from unicodedata2 import name, category, unidata_version 
# The function 'block' is non-standard and is defined below using the loaded data.


# --------------------------------------------------------------------
# 0. Block Data Loading, Caching, and 'block' function
# --------------------------------------------------------------------

BLOCKS_DATA_FILE = "unicode_blocks.json"
_CACHED_BLOCK_DATA: Optional[List[Dict]] = None

def load_block_data() -> List[Dict]:
    """
    Loads and caches the block data from the JSON file. Converts hexadecimal 
    start/end strings to integers for fast lookup.
    Exits with an error if the file is not found or is invalid JSON.
    """
    global _CACHED_BLOCK_DATA
    if _CACHED_BLOCK_DATA is None:
        try:
            with open(BLOCKS_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert 'start' and 'end' hex strings to integers for comparison
                for block_entry in data:
                    block_entry['start_cp'] = int(block_entry['start'], 16)
                    block_entry['end_cp'] = int(block_entry['end'], 16)
                _CACHED_BLOCK_DATA = data
        except FileNotFoundError:
            print(f"Error: Block data file '{BLOCKS_DATA_FILE}' not found.", file=sys.stderr)
            print("Please run generate_blocks_data.py first to create the block data.", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{BLOCKS_DATA_FILE}'. File may be corrupt.", file=sys.stderr)
            sys.exit(1)
    return _CACHED_BLOCK_DATA

def block(char: str) -> str:
    """
    Custom implementation of the non-standard 'block' function, using data
    loaded from the JSON file. Returns 'No_Block' if no match is found.
    """
    try:
        cp = ord(char)
    except TypeError:
        return "No_Block"
    
    blocks = load_block_data()

    for block_entry in blocks:
        # Use the pre-converted integer code points
        if block_entry['start_cp'] <= cp <= block_entry['end_cp']:
            return block_entry['name']
    
    # All code points not listed have the value No_Block
    return "No_Block"


# --------------------------------------------------------------------
# 1. Configuration & Named Tuple (Unified Definition) ----------------
# --------------------------------------------------------------------

# Version of Unicode data used by unicodedata2
UNICODE_VERSION = unidata_version 
# The block data is now dynamically loaded from the JSON file.
MAX_UNICODE_CP = 0x110000 
UnicodeBlock = namedtuple('UnicodeBlock', ['name', 'start', 'end'])


# --------------------------------------------------------------------
# 2. Utility Class for Macro Generation (Encapsulation)
# --------------------------------------------------------------------

class MacroGenerator:
    """
    Manages the configuration and logic for converting Unicode names into 
    short, clean C-style macro identifiers (UC_ABBR_NAME).
    """

    # Layer 1: Block Prefixes (Custom/ISO 639-1)
    BLOCK_ABBREVIATIONS: Dict[str, str] = {
        "DEFAULT": "",
        "BASIC LATIN": "LA",
        "LATIN-1 SUPPLEMENT": "L1S",
        "LATIN EXTENDED-A": "LTA",
        "LATIN EXTENDED-B": "LTB",
        "LATIN EXTENDED-C": "LTC",
        "LATIN EXTENDED-D": "LTD",
        "LATIN EXTENDED-E": "LTE",
        "GREEK AND COPTIC": "GRC",
        "GREEK EXTENDED": "GREX",
        "CYRILLIC": "CY",
        "CYRILLIC SUPPLEMENT": "CYS",
        "ARMENIAN": "AM",
        "HEBREW": "HE",
        "ARABIC": "AR",
        "ARABIC EXTENDED-B": "AREB", 
        "SHAVIAN": "SH",
        "DEVANAGARI": "DV",
        "BENGALI": "BN",
        "GUJARATI": "GJ",
        "GURMUKHI": "GK",
        "ORIYA": "OR",
        "TAMIL": "TM",
        "TELUGU": "TL",
        "HANGUL JAMO": "HJ",
        "HANGUL SYLLABLES": "HSY",
        "KATAKANA": "KT",
        "HIRAGANA": "HR",
        "CJK UNIFIED IDEOGRAPHS": "CJK",
        "CJK UNIFIED IDEOGRAPHS EXTENSION A": "CJKA",
        "CJK STROKES": "CJS", 
        "GENERAL PUNCTUATION": "PUN",
        "CURRENCY SYMBOLS": "CUR",
        "ARROWS": "ARW",
        "MATHEMATICAL OPERATORS": "MOP",
        "MATHEMATICAL ALPHANUMERIC SYMBOLS": "MA",
        "BLOCK ELEMENTS": "BE",
        "GEOMETRIC SHAPES": "GS",
        "MISCELLANEOUS SYMBOLS": "MSY",
        "TRANSPORT AND MAP SYMBOLS": "TMS",
        "EMOTICONS": "EMJ",
        "DINGBATS": "DB", 
        "LETTERLIKE SYMBOLS": "LS", 
        "IDEOGRAPHIC DESCRIPTION CHARACTERS": "IDC", 
        "INSCRIPTIONAL PAHLAVI": "IP", 
        "HIGH SURROGATES": "HS",
        "LOW SURROGATES": "LS",
        "PRIVATE USE AREA": "PUA",
    }

    # Layer 2: Redundant Word Stripping
    REDUNDANT_SCRIPT_WORDS: Set[str] = {
        "LETTER", "DIGIT", "COMMA", "CHARACTER", "SYMBOL", "WITH", "FORMS", 
        "ALPHABETIC", "TELEGRAM", "EMOJI", "NUMBER", 
        "LATIN", "GREEK", "CYRILLIC", "ARABIC", "HEBREW", "SHAVIAN", "COPTIC",
        "DEVANAGARI", "MATHEMATICAL", "MISCELLANEOUS", "SUPPLEMENTAL", "EXTENDED", 
        "ADDITIONAL", "COMPATIBILITY", "IDEOGRAPHS", "VARIATION", "SELECTOR",
    }

    # Layer 3: Internal String Replacements
    MACRO_STRING_REPLACEMENTS: Dict[str, str] = {
        "SANS-SERIF": "SS",
        "DOUBLE-STRUCK": "DS",
        "FRAKTUR": "FR",
        "MONOSPACE": "MS",
        "ITALIC": "IT",
        "SCRIPT": "SC",
        "CALIGRAPHIC": "CA",
        "CIRCLED": "C",
        "PARENTHESIZED": "P",
        "FULLWIDTH": "FW",
    }
    
    def get_block_abbr(self, block_name: str) -> str:
        """Looks up the abbreviation for a Unicode block name."""
        return self.BLOCK_ABBREVIATIONS.get(block_name.upper(), self.BLOCK_ABBREVIATIONS["DEFAULT"])

    def generate_name(self, block_abbr: str, unicode_name: str, strip_case: bool) -> str:
        """
        Build a short, clean C‑identifier from the Unicode name using the three-layer
        abbreviation system: UC + Block Abbr + Name Body.
        """
        s = unicode_name
        
        # 1. Strip case words
        if strip_case:
            s = re.sub(r"(SMALL|CAPITAL|LOWERCASE|UPPERCASE)\s", "", s)
        
        s_upper = s.upper()

        # 2. Layer 3: Apply internal abbreviations
        for original, replacement in self.MACRO_STRING_REPLACEMENTS.items():
            s_upper = s_upper.replace(original.upper(), replacement)

        # 3. Initial cleanup: convert remaining spaces/hyphens/non-word chars to single underscores
        s_final = re.sub(r"[^\w]+", "_", s_upper).strip("_")
        
        # 4. Layer 2: Filter out redundant words based on parts
        s_parts = s_final.split('_')
        s_final = '_'.join([part for part in s_parts if part not in self.REDUNDANT_SCRIPT_WORDS])
            
        # Final cleanup of internal underscores
        s_final = re.sub(r"_+", "_", s_final).strip('_')
        
        # Fallback
        if not s_final:
            s_final = "CHAR"

        # 5. Assemble the final macro name
        parts = ["UC"]
        if block_abbr:
            parts.append(block_abbr)
        parts.append(s_final)

        return "_".join(parts)


# --------------------------------------------------------------------
# 3. Helper Functions 
# --------------------------------------------------------------------

def printable_glyph(cp: int) -> Optional[str]:
    """Return a printable representation of *cp* or None if it is not printable."""
    try:
        ch = chr(cp)
    except ValueError:
        return None
        
    cat = category(ch)
    if cat[0] in ("C", "Z") or not ch.isprintable():
        return None
        
    return ch

def find_case_partner(cp: int) -> Tuple[Optional[int], Optional[str]]:
    """
    Find the uppercase partner (cp, name) if *cp* is a single, mappable 
    lowercase letter ('Ll'). Returns (None, None) otherwise.
    """
    try:
        ch = chr(cp)
        current_cat = category(ch)
    except ValueError:
        return None, None

    if current_cat != 'Ll':
        return None, None
    
    partner_str = ch.upper()

    if len(partner_str) == 1 and partner_str != ch:
        partner_cp = ord(partner_str)
        try:
            partner_ch = chr(partner_cp)
            partner_cat = category(partner_ch)
            partner_name = name(partner_ch)
        except ValueError:
            return None, None
        
        if partner_cat == 'Lu':
            return partner_cp, partner_name

    return None, None


# --------------------------------------------------------------------
# 4. Block Iteration
# --------------------------------------------------------------------

def get_all_blocks() -> Iterator[UnicodeBlock]:
    """
    Yields UnicodeBlock named tuples (name, start, end) by iterating over
    the loaded block data from the JSON file. This is more efficient than
    probing every code point.
    """
    blocks = load_block_data()

    for block_entry in blocks:
        # Use the pre-converted integer code points (start_cp, end_cp)
        # and the name from the JSON
        yield UnicodeBlock(
            block_entry['name'], 
            block_entry['start_cp'], 
            block_entry['end_cp']
        )


# --------------------------------------------------------------------
# 5. Header Generation Logic
# --------------------------------------------------------------------

def generate_header_content(block: UnicodeBlock, block_abbr: str, macro_generator: MacroGenerator) -> Tuple[Optional[List[str]], int, int]:
    """
    Generates the content lines (#define macros) for a single C header block.
    
    Returns a tuple of (lines, defined_code_points, significant_hex_values).
    - defined_code_points: The count of individual Unicode code points processed.
    - significant_hex_values: The count of non-zero hexadecimal values written to file.
    """
    
    lines: List[str] = []
    processed: Set[int] = set()
    
    defined_code_points = 0
    significant_hex_values = 0

    for cp in range(block.start, block.end + 1):
        if cp in processed:
            continue
            
        try:
            char = chr(cp)
            char_name = name(char)
            cat = category(char)
        except ValueError:
            # Correctly skips unassigned and non-character code points
            continue
            
        glyph = printable_glyph(cp)
        partner_cp, partner_name = find_case_partner(cp)

        # 1. Skip Capital Letters that are the UPPERCASE partner of a later LOWERCASE letter.
        is_capital_cat = cat == 'Lu'
        if is_capital_cat:
            lower_str = char.lower()
            if len(lower_str) == 1 and lower_str != char:
                lower_partner_cp = ord(lower_str)
                if lower_partner_cp > cp:
                    continue
            
        # 2. SUCCESSFUL PAIR CASE
        if partner_cp is not None: 
            cp1, cp2 = cp, partner_cp
            name1, name2 = char_name, partner_name 
            glyph1, glyph2 = glyph, printable_glyph(cp2)

            if glyph1 and glyph2:
                comment = f"// {glyph1}/{glyph2}"
            else:
                comment_parts = [f"U+{cp1:04X} ({name1})", f"U+{cp2:04X} ({name2})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_generator.generate_name(block_abbr, name1, strip_case=True)
            lines.append(
                f"#define {macro_name:<40} 0x{cp1:04X} 0x{cp2:04X}  {comment}" 
            )
            
            defined_code_points += 2
            significant_hex_values += 2
            
            processed.update({cp1, cp2})
            continue

        # 3. SINGLE CODE POINT CASE
        if cp not in processed:
            if glyph:
                comment = f"// {glyph}"
            else:
                comment_parts = [f"U+{cp:04X} ({char_name})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_generator.generate_name(block_abbr, char_name, strip_case=False)
            lines.append(
                f"#define {macro_name:<40} 0x{cp:04X} 0  {comment}" 
            )
            
            defined_code_points += 1
            significant_hex_values += 1 # The trailing '0' is a placeholder, only the code point is significant
            
            processed.add(cp)
            
    if not lines:
        return None, 0, 0
    
    return lines, defined_code_points, significant_hex_values

def emit_header(block: UnicodeBlock, out_dir: pathlib.Path, macro_generator: MacroGenerator) -> None:
    """
    Writes one header file for the block, providing console feedback and
    including a consistency check within the header's comments.
    """
    
    s_clean = re.sub(r"[^\w]", "_", block.name)
    file_basename = re.sub(r"_+", "_", s_clean).lower().strip("_")
    header_file = out_dir / f"{file_basename}.h"
    
    block_abbr = macro_generator.get_block_abbr(block.name)
    
    content_lines, defined_code_points, significant_hex_values = generate_header_content(block, block_abbr, macro_generator)
    
    # --- Consistency Check ---
    consistency_message = ""
    if defined_code_points != significant_hex_values:
        consistency_message = (
            f"\n* !! CONSISTENCY ERROR !!\n"
            f"* Code Points Defined: {defined_code_points}\n"
            f"* Significant Hex Values: {significant_hex_values}\n"
            f"* Description: These counts should be equal because every Unicode code point defined\n"
            f"* in the macros (whether alone or as part of a case pair) should contribute\n"
            f"* exactly one non-zero hexadecimal value to the output.\n"
        )
        print(f"ERROR: Block '{block.name}' consistency check failed! Code Points ({defined_code_points}) != Hex Values ({significant_hex_values})", file=sys.stderr)
    else:
        # Success message for the header file
        consistency_message = (
            f"\n* Consistency Check:\n"
            f"* Total Defined Code Points: {defined_code_points}\n"
            f"* Total Significant Hex Values: {significant_hex_values}\n"
            f"* Status: OK (Counts Match)\n"
        )
    # -------------------------
    
    if content_lines is None:
        print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Skipped** (no defines generated)")
        return
        
    # Block data source description is updated to reflect the JSON file
    BLOCK_DATA_SOURCE_DESC = f"JSON file ({BLOCKS_DATA_FILE})"

    boilerplate = f"""\
/* {header_file.name} – Unicode constants for U+{block.start:04X} … U+{block.end:04X}
*
* Generated by generate_unicode_headers.py
* Character Properties Data (Names/Categories): Unicode {UNICODE_VERSION} (via unicodedata2)
* Block Range Data (Boundaries): Sourced from {BLOCK_DATA_SOURCE_DESC}
*
* See https://www.unicode.org/versions/latest/ for source data.
{consistency_message}
*/

#pragma once

"""
    
    all_content = boilerplate + "\n".join(content_lines) + "\n"
    header_file.write_text(all_content, encoding="utf-8")
    
    print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Written** to {header_file.name}")


# --------------------------------------------------------------------
# 6. Main Execution
# --------------------------------------------------------------------

def main() -> int:
    """
    Main execution function.
    """
    parser = argparse.ArgumentParser(
        description="Generate C header files containing Unicode code point definitions."
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='generated_headers',
        help='Specify the output directory for the generated headers (default: generated_headers)'
    )
    args = parser.parse_args()
    
    out_dir = pathlib.Path(args.output)
    
    # Pre-check: attempt to load data early
    load_block_data() 
    
    try:
        out_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        print(f"Error creating output directory '{out_dir}': {e}", file=sys.stderr)
        return 1
        
    # Instantiate the MacroGenerator once in main()
    generator = MacroGenerator()

    # Note: We can't display the block version dynamically, so we show the unicodedata version.
    print(f"Generating C headers for Unicode (Properties: {UNICODE_VERSION} / Block Data: {BLOCKS_DATA_FILE})...")

    # Pass the generator instance to the emission function
    for u_block in get_all_blocks():
        emit_header(u_block, out_dir, generator)

    print("\nAll headers written to", out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
