#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_unicode_headers.py

Generate C header files with Unicode constants for every code point.
The script uses the `unicodedata2` package for core properties and loads
Unicode block data from a JSON file to provide the missing 'block' function.

This version uses a three-layered abbreviation system for maximal brevity and
collision avoidance, and a robust two-pass system for case pairing that ensures
correct ordering (small letter first) for all scripts, including Beria Erfe.
"""

import pathlib
import re
import sys
import argparse
import json 
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import namedtuple

# Import all standard functions from unicodedata2 for updated Unicode data.
# Added 'lookup' for robust name-based case mapping.
from unicodedata2 import name, category, unidata_version, lookup


# Global constant for unicodedata version (from package)
UNICODE_VERSION = unidata_version

# Global variable for block version (set from JSON file)
UNICODE_BLOCK_VERSION: str = "N/A (not loaded)" 

# Define the structure for a Unicode Block
# Includes 'description' for content read from the JSON file
UnicodeBlock = namedtuple('UnicodeBlock', ['name', 'start', 'end', 'description'])

# --------------------------------------------------------------------
# 0. Block Data Loading, Caching, and 'block' function
# --------------------------------------------------------------------

BLOCKS_DATA_FILE = "unicode_blocks.json"
_CACHED_BLOCK_DATA: Optional[List[Dict]] = None

def load_block_data() -> None:
    """
    Loads and caches the block data from the JSON file. Converts hexadecimal 
    start/end strings to integers for fast lookup and sets the global Unicode block version.
    
    Handles the new JSON format: {"unicode_version": "...", "blocks": [...]}.
    """
    global _CACHED_BLOCK_DATA
    global UNICODE_BLOCK_VERSION

    if _CACHED_BLOCK_DATA is None:
        try:
            with open(BLOCKS_DATA_FILE, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
                # 1. Pull the Unicode version from the JSON object
                UNICODE_BLOCK_VERSION = json_data.get('unicode_version', 'Unknown (JSON key missing)')

                # 2. Extract the blocks array
                blocks_list = json_data.get('blocks', [])
                
                # 3. Process the blocks
                processed_blocks = []
                for block_entry in blocks_list:
                    # Convert 'start' and 'end' hex strings to integers for comparison
                    block_entry['start_cp'] = int(block_entry['start'], 16)
                    block_entry['end_cp'] = int(block_entry['end'], 16)
                    processed_blocks.append(block_entry)
                    
                _CACHED_BLOCK_DATA = processed_blocks

        except FileNotFoundError:
            print(f"Error: Block data file '{BLOCKS_DATA_FILE}' not found.", file=sys.stderr)
            print("Please run generate_blocks_data.py first to create the block data.", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in '{BLOCKS_DATA_FILE}'.", file=sys.stderr)
            sys.exit(1)
        except KeyError as e:
            print(f"Error: Missing key {e} in a block entry in JSON file. Check block format.", file=sys.stderr)
            sys.exit(1)

def block(cp: int) -> str:
    """
    Custom 'block' function that determines the Unicode block name for a code point.
    """
    if _CACHED_BLOCK_DATA is None:
        load_block_data()
        
    for entry in _CACHED_BLOCK_DATA:
        if entry['start_cp'] <= cp <= entry['end_cp']:
            return entry['name']
    return 'No_Block'

def get_all_blocks() -> Iterator[UnicodeBlock]:
    """
    Generator yielding UnicodeBlock namedtuples from the cached data.
    """
    if _CACHED_BLOCK_DATA is None:
        load_block_data()
        
    for entry in _CACHED_BLOCK_DATA:
        yield UnicodeBlock(
            name=entry['name'], 
            start=entry['start_cp'], 
            end=entry['end_cp'],
            description=entry.get('description', '')
        )

# --------------------------------------------------------------------
# 1. Configuration & Named Tuple (Unified Definition) ----------------
# --------------------------------------------------------------------

MAX_UNICODE_CP = 0x110000 


# --------------------------------------------------------------------
# 2. Utility Class for Macro Generation (Encapsulation)
# --------------------------------------------------------------------

class MacroGenerator:
    """
    Manages the configuration and logic for converting Unicode names into 
    short, clean C-style macro identifiers (UC_ABBR_NAME).
    """

    # --- Manual Override for ASCII/C1 Control Character Names ---
    # These names are known to cause ValueError in unicodedata.name(), 
    # but they must be generated with their common three-letter abbreviations.
    CONTROL_CHARACTER_NAMES: Dict[int, str] = {
        # ASCII C0 Controls (U+0000 - U+001F, U+007F)
        0x0000: "NULL", 0x0001: "SOH", 0x0002: "STX", 0x0003: "ETX",
        0x0004: "EOT", 0x0005: "ENQ", 0x0006: "ACK", 0x0007: "BEL",
        0x0008: "BS", 0x0009: "HT", 0x000A: "LF", 0x000B: "VT",
        0x000C: "FF", 0x000D: "CR", 0x000E: "SO", 0x000F: "SI",
        0x0010: "DLE", 0x0011: "DC1", 0x0012: "DC2", 0x0013: "DC3",
        0x0014: "DC4", 0x0015: "NAK", 0x0016: "SYN", 0x0017: "ETB",
        0x0018: "CAN", 0x0019: "EM", 0x001A: "SUB", 0x001B: "ESC",
        0x001C: "FS", 0x001D: "GS", 0x001E: "RS", 0x001F: "US",
        0x007F: "DEL",
        # C1 Control Codes (U+0080 - U+009F)
        0x0080: "PAD", 0x0081: "HOP", 0x0082: "BPH", 0x0083: "NBH",
        0x0084: "IND", 0x0085: "NEL", 0x0086: "SSA", 0x0087: "ESA",
        0x0088: "HTS", 0x0089: "HTJ", 0x008A: "VTS", 0x008B: "PLD",
        0x008C: "PLU", 0x008D: "RI", 0x008E: "SS2", 0x008F: "SS3",
        0x0090: "DCS", 0x0091: "PU1", 0x0092: "PU2", 0x0093: "STS",
        0x0094: "CCH", 0x0095: "MW", 0x0096: "EFB", 0x0097: "ESI",
        0x0098: "SOS", 0x0099: "SGCI", 0x009A: "SCI", 0x009B: "CSI",
        0x009C: "ST", 0x009D: "OSC", 0x009E: "PM", 0x009F: "APC",
    }
    # -------------------------------------------------------


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
            # Note: We must strip both 'SMALL'/'LOWERCASE' and 'CAPITAL'/'UPPERCASE' 
            # if we are generating a pair macro name.
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
    """
    Returns the character if it's displayable (Letter, Number, Symbol, Punctuation), 
    otherwise returns None. Used only for comment formatting.
    """
    try:
        ch = chr(cp)
        cat = category(ch)
    except ValueError:
        return None
        
    # Filter out all C (Control, Format, Unassigned, Private Use, Surrogate)
    # and all Z (Separator), except for the standard space (U+0020).
    if cat[0] in ("C", "Z"):
        # Special case: allow the standard space U+0020 for the comment
        if cat == 'Zs' and ch == ' ':
            return ch
        return None
        
    # All other categories (L, N, S, P) are displayable.
    return ch
    
def resolve_char_name(cp: int, char: str, cat: str, macro_generator: 'MacroGenerator') -> str:
    """Helper to get the name of a character using the manual control map or unicodedata, with fallbacks."""
    if cp in macro_generator.CONTROL_CHARACTER_NAMES:
        return macro_generator.CONTROL_CHARACTER_NAMES[cp]
    else:
        try:
            return name(char)
        except ValueError:
            # Fallback for assigned characters (like non-ASCII Cc or Cf) if name fails
            return f"{cat}_U{cp:04X}"


def find_case_partner(cp: int, name1: str) -> Optional[int]:
    """
    Find the uppercase partner code point if *cp* is a single, mappable 
    lowercase letter ('Ll'), by substituting 'SMALL' with 'CAPITAL' in the name 
    and using unicodedata2.lookup(). Returns None otherwise.
    """
    try:
        ch = chr(cp)
        # 1. Must be a lowercase letter.
        if category(ch) != 'Ll':
            return None
    except ValueError:
        return None
        
    # 2. Try the robust name-to-code-point lookup strategy.
    # This covers Beria Erfe (SMALL -> CAPITAL) and similar scripts.
    if ('SMALL' in name1) or ('LOWERCASE' in name1):
        partner_name = name1.replace('SMALL', 'CAPITAL').replace('LOWERCASE', 'UPPERCASE')
        try:
            partner_ch = lookup(partner_name)
            partner_cp = ord(partner_ch)
            
            # Final check: ensure the partner is indeed an uppercase letter.
            if category(partner_ch) == 'Lu':
                return partner_cp

        except (KeyError, ValueError):
            # Name substitution failed, fall through to default casing check
            pass

    # 3. Fallback to standard Python casing (for Latin, etc.)
    partner_str = ch.upper()

    if len(partner_str) == 1 and partner_str != ch:
        partner_cp = ord(partner_str)
        try:
            partner_ch = chr(partner_cp)
            partner_cat = category(partner_ch)
        except ValueError:
            return None
        
        if partner_cat == 'Lu':
            return partner_cp

    return None


# --------------------------------------------------------------------
# 4. Header Generation Logic (Two-Pass System)
# --------------------------------------------------------------------

def generate_header_content(block: UnicodeBlock, block_abbr: str, macro_generator: MacroGenerator) -> Tuple[Optional[List[str]], int, int]:
    """
    Generates the content lines (#define macros) for a single C header block using 
    a robust two-pass system to handle all case-pairing orders.
    
    Returns a tuple of (lines, defined_code_points, significant_hex_values).
    """
    
    lines: List[str] = []
    # Dict to store Ll -> Lu pairings: {Ll_CP: Lu_CP}
    case_pairs: Dict[int, int] = {} 
    # Set to track all CPs that belong to a pair (Ll and Lu)
    paired_cps: Set[int] = set() 
    
    defined_code_points = 0
    significant_hex_values = 0

    # Categories to EXCLUDE (Unassigned, Private Use, Surrogate, Specific Separators)
    EXCLUDE_CATEGORIES = {'Cn', 'Co', 'Cs', 'Zl', 'Zp'}

    # =======================================================
    # PASS 1: IDENTIFY AND STORE ALL CASE PAIRS (Ll -> Lu)
    # This pass is order-independent and ensures Ll is the key.
    # =======================================================
    for cp in range(block.start, block.end + 1):
        try:
            char = chr(cp)
        except ValueError: continue
            
        cat = category(char)
        if cat != 'Ll': continue # Only interested in Lowercase Letters here
        
        # 1. Resolve Name (must succeed for lookup in helper to work)
        # This handles C0/C1 and ValueError fallbacks.
        name1 = resolve_char_name(cp, char, cat, macro_generator)
        
        # 2. Find partner using the name substitution strategy
        partner_cp = find_case_partner(cp, name1) 

        if partner_cp is not None and partner_cp not in paired_cps:
            # Found a valid, unprocessed pair
            case_pairs[cp] = partner_cp
            paired_cps.add(cp)
            paired_cps.add(partner_cp)
            
    # =======================================================
    # PASS 2: GENERATE MACROS (Paired, then Single)
    # =======================================================
    for cp in range(block.start, block.end + 1):
        if cp in case_pairs:
            # A. PAIR CASE (cp is the Ll char, acting as cp1)
            cp1 = cp
            cp2 = case_pairs[cp]
            
            # --- Resolve names for the pair ---
            char1 = chr(cp1)
            char2 = chr(cp2)
            cat1 = category(char1)
            cat2 = category(char2)
            
            name1 = resolve_char_name(cp1, char1, cat1, macro_generator)
            name2 = resolve_char_name(cp2, char2, cat2, macro_generator)
            
            glyph1, glyph2 = printable_glyph(cp1), printable_glyph(cp2)

            if glyph1 and glyph2:
                comment = f"// {glyph1}/{glyph2}"
            else:
                comment_parts = [f"U+{cp1:04X} ({name1})", f"U+{cp2:04X} ({name2})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            # Strip case from macro name for the pair definition
            macro_name = macro_generator.generate_name(block_abbr, name1, strip_case=True)
            lines.append(
                f"#define {macro_name:<40} 0x{cp1:04X} 0x{cp2:04X}  {comment}" 
            )
            
            defined_code_points += 2
            significant_hex_values += 2
            
        elif cp not in paired_cps:
            # B. SINGLE CODE POINT CASE (cp is not part of any pair)
            
            # 1. Skip excluded categories
            try:
                char = chr(cp)
            except ValueError: continue
            cat = category(char)
            if cat in EXCLUDE_CATEGORIES: continue
            
            # 2. Resolve Name
            char_name = resolve_char_name(cp, char, cat, macro_generator)
            
            if printable_glyph(cp):
                comment = f"// {printable_glyph(cp)}"
            else:
                # Since glyph is None, use the correct name (either manual or fallback)
                comment_parts = [f"U+{cp:04X} ({char_name})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_generator.generate_name(block_abbr, char_name, strip_case=False)
            lines.append(
                f"#define {macro_name:<40} 0x{cp:04X} 0  {comment}" 
            )
            
            defined_code_points += 1
            significant_hex_values += 1 
            
    if not lines:
        return None, 0, 0
    
    return lines, defined_code_points, significant_hex_values

def emit_header(block: UnicodeBlock, out_dir: pathlib.Path, macro_generator: MacroGenerator) -> None:
    """
    Writes one header file for the block, providing console feedback and
    including a consistency check and description within the header's comments.
    """
    
    # --- FILE NAMING LOGIC ---
    s_clean = re.sub(r"[^\w]", "_", block.name)
    file_basename = re.sub(r"_+", "_", s_clean).lower().strip("_")
    header_file = out_dir / f"{file_basename}.h"
    # -------------------------
    
    block_abbr = macro_generator.get_block_abbr(block.name)
    
    content_lines, defined_code_points, significant_hex_values = generate_header_content(block, block_abbr, macro_generator)
    
    # --- Consistency Check ---
    consistency_message = ""
    if defined_code_points != significant_hex_values:
        consistency_message = (
            f"\n* !! CONSISTENCY ERROR !!\n"
            f"* Code Points Defined: {defined_code_points}\n"
            f"* Significant Hex Values: {significant_hex_values}\n"
            f"* Description: Counts should be equal for a clean header.\n"
        )
        print(f"ERROR: Block '{block.name}' consistency check failed! Code Points ({defined_code_points}) != Hex Values ({significant_hex_values})", file=sys.stderr)
    else:
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
        
    # --- Description Comment ---
    description_comment = ""
    if block.description.strip():
        # Format the description to fit within the C comment block
        lines = block.description.strip().split('\n\n') # Split by double newline (paragraph)
        wrapped_lines = []
        
        for line in lines:
            current_line = []
            max_width = 75 
            
            words = line.split()
            for word in words:
                if not current_line or len(' '.join(current_line) + ' ' + word) > max_width:
                    if current_line:
                        wrapped_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    current_line.append(word)
            if current_line:
                wrapped_lines.append(" ".join(current_line))

        # Prefix each line with ' * ' and add leading/trailing newline for formatting
        description_comment = "\n * ".join([""] + wrapped_lines)
        description_comment += "\n *"
    # ---------------------------

    boilerplate = f"""\
/* {header_file.name} – Unicode constants for U+{block.start:04X} … U+{block.end:04X}
*
* Generated by generate_unicode_headers.py
* Character Properties Data (Names/Categories): Unicode {UNICODE_VERSION} (via unicodedata2)
* Block Range Data (Boundaries): Unicode {UNICODE_BLOCK_VERSION} (via {BLOCKS_DATA_FILE})
*
* See https://www.unicode.org/versions/latest/ for source data.
{description_comment}
{consistency_message}
*/

#pragma once

"""
    
    all_content = boilerplate + "\n".join(content_lines) + "\n"
    header_file.write_text(all_content, encoding="utf-8")
    
    print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Written** to {header_file.name}")


# --------------------------------------------------------------------\
# 5. Main Execution
# --------------------------------------------------------------------\

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
    
    # Pre-check: attempt to load data early (this now populates UNICODE_BLOCK_VERSION)
    load_block_data() 
    
    try:
        out_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        print(f"Error creating output directory '{out_dir}': {e}", file=sys.stderr)
        return 1
        
    # Instantiate the MacroGenerator once in main()
    generator = MacroGenerator()

    # Print version loaded from JSON
    print(f"Generating C headers for Unicode (Properties: {UNICODE_VERSION} / Blocks: {UNICODE_BLOCK_VERSION})...")

    # Pass the generator instance to the emission function
    for u_block in get_all_blocks():
        emit_header(u_block, out_dir, generator)

    print("\nAll headers written to", out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
