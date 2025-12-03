#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_unicode_headers.py

Generate C header files with Unicode constants for every code point.
The script expects no external data files – it pulls everything from the
`unicodedataplus` package (Unicode data).

This version uses a three-layered abbreviation system for maximal brevity and
collision avoidance:
1. Block Prefix (e.g., 'LA' for Latin, 'SH' for Shavian)
2. Redundant Word Stripping (e.g., removing 'LETTER', 'DIGIT', 'WITH')
3. Internal Abbreviation (e.g., 'SANS_SERIF' -> 'SS')
"""

import pathlib
import re
import sys
import argparse
import unicodedataplus as ucp
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import namedtuple

# --------------------------------------------------------------------
# 1. Configuration & Named Tuple
# --------------------------------------------------------------------

UNICODE_VERSION = ucp.unidata_version
MAX_UNICODE_CP = 0x110000 
UnicodeBlock = namedtuple('UnicodeBlock', ['name', 'start', 'end'])

# --- Layer 1: Block Prefixes (Custom/ISO 639-1) ---
BLOCK_ABBREVIATIONS: Dict[str, str] = {
    "DEFAULT": "", # Setting the default to "" prevents the redundant "UC_UC_"
    
    # Latin, Greek, Cyrillic Scripts
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
    "SHAVIAN": "SH",
    
    # Major Indic Scripts
    "DEVANAGARI": "DV",
    "BENGALI": "BN",
    "GUJARATI": "GJ",
    "GURMUKHI": "GK",
    "ORIYA": "OR",
    "TAMIL": "TM",
    "TELUGU": "TL",

    # CJK and Hangul
    "HANGUL JAMO": "HJ",
    "HANGUL SYLLABLES": "HSY",
    "KATAKANA": "KT",
    "HIRAGANA": "HR",
    "CJK UNIFIED IDEOGRAPHS": "CJK",
    "CJK UNIFIED IDEOGRAPHS EXTENSION A": "CJKA",

    # Symbols and Punctuation
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

    # Specials
    "HIGH SURROGATES": "HS",
    "LOW SURROGATES": "LS",
    "PRIVATE USE AREA": "PUA",
}

# --- Layer 2: Redundant Word Stripping ---
REDUNDANT_SCRIPT_WORDS: Set[str] = {
    "LETTER", "DIGIT", "COMMA", "CHARACTER", "SYMBOL", "WITH", "FORMS", 
    "ALPHABETIC", "TELEGRAM", "EMOJI",
    "LATIN", "GREEK", "CYRILLIC", "ARABIC", "HEBREW", "SHAVIAN", "COPTIC",
    "DEVANAGARI", "MATHEMATICAL", "MISCELLANEOUS", "SUPPLEMENTAL", "EXTENDED", 
    "ADDITIONAL", "COMPATIBILITY", "IDEOGRAPHS", "VARIATION", "SELECTOR",
}

# --- Layer 3: Internal Abbreviation (Stylistic) ---
MACRO_BODY_ABBREVIATIONS: Dict[str, str] = {
    "SANS_SERIF": "SS",
    "DOUBLE_STRUCK": "DS",
    "FRAKTUR": "FR",
    "MONOSPACE": "MS",
    "ITALIC": "IT",
    "SCRIPT": "SC",
    "CALIGRAPHIC": "CA",
    "CIRCLED": "C",
    "PARENTHESIZED": "P",
    "FULLWIDTH": "FW",
}


# --------------------------------------------------------------------
# 2. Helper: Printable Glyphs and Case Mapping
# --------------------------------------------------------------------

def printable_glyph(cp: int) -> Optional[str]:
    """Return a printable representation of *cp* or None if it is not printable."""
    try:
        ch = chr(cp)
    except ValueError:
        return None
        
    # Check if the category is Control (C) or Separator (Z) or generally not printable
    cat = ucp.category(ch)
    if cat[0] in ("C", "Z") or not ch.isprintable():
        return None
        
    return ch

# Refined implementation for cleaner structure and consistent Optional return type
def find_case_partner(cp: int) -> Tuple[Optional[int], Optional[str]]:
    """
    Find the uppercase partner (cp, name) if *cp* is a single, mappable 
    lowercase letter ('Ll'). Returns (None, None) otherwise.
    """
    try:
        ch = chr(cp)
        current_cat = ucp.category(ch)
    except ValueError:
        return None, None

    # Only look for partners for lowercase letters
    if current_cat != 'Ll':
        return None, None
    
    partner_str = ch.upper()

    # Check for 1:1 mapping that results in a different character
    if len(partner_str) == 1 and partner_str != ch:
        partner_cp = ord(partner_str)
        try:
            partner_ch = chr(partner_cp)
            partner_cat = ucp.category(partner_ch)
            partner_name = ucp.name(partner_ch)
        except ValueError:
            return None, None
        
        # Ensure the partner is indeed an uppercase letter
        if partner_cat == 'Lu':
            return partner_cp, partner_name

    return None, None


# --------------------------------------------------------------------
# 3. Helper: Convert a Unicode name into an identifier (Layered Logic)
# --------------------------------------------------------------------

def macro_name_from_unicode_name(block_abbr: str, unicode_name: str, strip_case: bool) -> str:
    """
    Build a short, clean C‑identifier from the Unicode name using the three-layer
    abbreviation system: UC + Block Abbr + Name Body.
    """
    s = unicode_name
    
    # 1. Strip case words if generating a pair (LOWERCASE/UPPERCASE)
    if strip_case:
        s = re.sub(r"(SMALL|CAPITAL|LOWERCASE|UPPERCASE)\s", "", s)
    
    s_upper = s.upper()
    
    # 2. Initial cleanup: spaces/hyphens/non-word chars to single underscores
    s_final = re.sub(r"[^\w]+", "_", s_upper).strip("_")
    
    # 3. Filter out redundant words and apply internal abbreviations
    s_parts = s_final.split('_')
    final_parts = []
    
    for part in s_parts:
        if part in REDUNDANT_SCRIPT_WORDS:
            continue
        
        abbreviated_part = MACRO_BODY_ABBREVIATIONS.get(part, part)
        final_parts.append(abbreviated_part)

    s_final = '_'.join(final_parts)
        
    # Final cleanup of internal underscores
    s_final = re.sub(r"_+", "_", s_final).strip('_')
    
    # Fallback if filtering removed everything
    if not s_final:
        s_final = "CHAR"

    # 4. Assemble the final macro name robustly: UC + Block Abbr (if not empty) + Name Body
    parts = ["UC"]
    
    # Append block abbreviation if it is non-empty (prevents UC_UC_NAME)
    if block_abbr:
        parts.append(block_abbr)
    
    parts.append(s_final)

    return "_".join(parts)


# --------------------------------------------------------------------
# 4. Block Iteration (Generator)
# --------------------------------------------------------------------

def get_all_blocks() -> Iterator[UnicodeBlock]:
    """
    Yields UnicodeBlock named tuples (name, start, end) by probing unicodedataplus.
    """
    current_name: Optional[str] = None
    start_cp = 0
    
    for cp in range(MAX_UNICODE_CP):
        try:
            char = chr(cp)
            name = ucp.block(char)
        except ValueError:
            name = "No_Block"
        
        if name != current_name:
            if current_name and current_name != "No_Block":
                # Yield the completed block range
                yield UnicodeBlock(current_name, start_cp, cp - 1)
            current_name = name
            start_cp = cp
            
    # Yield the final block if it was not No_Block
    if current_name and current_name != "No_Block":
        yield UnicodeBlock(current_name, start_cp, MAX_UNICODE_CP - 1)


# --------------------------------------------------------------------
# 5. Header Generation Logic
# --------------------------------------------------------------------

def generate_header_content(block: UnicodeBlock, block_abbr: str) -> Optional[List[str]]:
    """
    Generates the content lines (#define macros) for a single C header block.
    """
    
    lines: List[str] = []
    processed: Set[int] = set()

    for cp in range(block.start, block.end + 1):
        if cp in processed:
            continue
            
        try:
            char = chr(cp)
            name = ucp.name(char)
            cat = ucp.category(char)
        except ValueError:
            continue
            
        glyph = printable_glyph(cp)
        partner_cp, partner_name = find_case_partner(cp)

        # --- Case Pairing Logic Check ---
        
        # 1. Skip Capital Letters that are the UPPERCASE partner of a later LOWERCASE letter.
        is_capital_cat = cat == 'Lu'
        if is_capital_cat:
            lower_str = char.lower()
            # If the lowercase form is a single character different from the capital
            if len(lower_str) == 1 and lower_str != char:
                lower_partner_cp = ord(lower_str)
                # If the lowercase partner comes LATER in the code point range, skip this capital.
                if lower_partner_cp > cp:
                    continue
            
        # 2. SUCCESSFUL PAIR CASE (Lowercase and its Uppercase Partner found)
        if partner_cp is not None: 
            cp1, cp2 = cp, partner_cp
            name1, name2 = name, partner_name 
            glyph1, glyph2 = glyph, printable_glyph(cp2)

            if glyph1 and glyph2:
                comment = f"// {glyph1}/{glyph2}"
            else:
                comment_parts = [f"U+{cp1:04X} ({name1})", f"U+{cp2:04X} ({name2})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_name_from_unicode_name(block_abbr, name1, strip_case=True)
            lines.append(
                f"#define {macro_name:<40} 0x{cp1:04X} 0x{cp2:04X}  {comment}" 
            )
            processed.update({cp1, cp2})
            continue

        # 3. SINGLE CODE POINT CASE
        if cp not in processed:
            if glyph:
                comment = f"// {glyph}"
            else:
                comment_parts = [f"U+{cp:04X} ({name})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_name_from_unicode_name(block_abbr, name, strip_case=False)
            lines.append(
                f"#define {macro_name:<40} 0x{cp:04X} 0  {comment}" 
            )
            processed.add(cp)
            
    return lines if lines else None

def emit_header(block: UnicodeBlock, out_dir: pathlib.Path) -> None:
    """
    Writes one header file for the block, providing console feedback.
    """
    
    # File name sanitization
    s_clean = re.sub(r"[^\w]", "_", block.name)
    file_basename = re.sub(r"_+", "_", s_clean).lower().strip("_")
    header_file = out_dir / f"{file_basename}.h"
    
    # Determine the block abbreviation
    block_abbr = BLOCK_ABBREVIATIONS.get(block.name.upper(), BLOCK_ABBREVIATIONS["DEFAULT"])
    
    content_lines = generate_header_content(block, block_abbr)
    
    if content_lines is None:
        print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Skipped** (no defines generated)")
        return
        
    boilerplate_lines: List[str] = [
        f"/* {header_file.name} – Unicode constants for U+{block.start:04X} … U+{block.end:04X}",
        "*",
        f"* Generated by generate_unicode_headers.py (Unicode {UNICODE_VERSION})",
        "*",
        "* See https://www.unicode.org/versions/latest/ for source data.",
        "*/\n",
        "#pragma once\n"
    ]
    
    all_lines = boilerplate_lines + content_lines
    header_file.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    
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
    
    try:
        # Create directory with parent folders if necessary
        out_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        print(f"Error creating output directory '{out_dir}': {e}", file=sys.stderr)
        return 1

    print(f"Generating C headers for Unicode {UNICODE_VERSION}...")

    # Process and emit headers for each block using the generator
    for block in get_all_blocks():
        emit_header(block, out_dir)

    # Use resolve() for the absolute path in the final output message
    print("\nAll headers written to", out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
