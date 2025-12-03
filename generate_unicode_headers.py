#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_unicode_headers.py

Generate C header files with Unicode constants for every code point.
The script expects no external data files – it pulls everything from the
`unicodedataplus` package (Unicode data).

Each block gets its own header under `generated_headers/`.
"""

import pathlib
import re
import sys
import unicodedataplus as ucp
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import namedtuple

# --------------------------------------------------------------------
# 1. Configuration & Named Tuple -------------------------------------
# --------------------------------------------------------------------

# The version is derived directly from the unicodedataplus package data
UNICODE_VERSION = ucp.unidata_version

# Named tuple for blocks
UnicodeBlock = namedtuple('UnicodeBlock', ['name', 'start', 'end'])

# Dictionary to map common script/language names to two-letter prefixes
SCRIPT_ABBREVIATIONS: Dict[str, str] = {
    # ISO 639-1 Language Codes
    "GREEK": "EL", "LATIN": "LA", "ARABIC": "AR", "HEBREW": "HE", 
    "THAI": "TH", "KHMER": "KM", "TIBETAN": "TB",
    
    # Common Script Abbreviations
    "CYRILLIC": "CY", "COPTIC": "CP", "DEVANAGARI": "DV", "BENGALI": "BN", 
    "GUJARATI": "GJ", "GURMUKHI": "GK", "ORIYA": "OR", "TAMIL": "TM", 
    "TELUGU": "TL",
    
    # Generic/Block Prefixes
    "GENERAL": "GN", "COMBINING": "CM", "SUPERSCRIPTS": "SS", "SUBSCRIPTS": "SB",
    "MATHEMATICAL": "MA", "MISCELLANEOUS": "MS", "ENCLOSED": "EN", "CJK": "CJK",
}


# --------------------------------------------------------------------
# 2. Helper: Printable Glyphs and Case Mapping -----------------------
# --------------------------------------------------------------------

def printable_glyph(cp: int) -> Optional[str]:
    """Return a printable representation of *cp* or None if it is not printable."""
    try:
        ch = chr(cp)
    except ValueError:
        return None
        
    cat = ucp.category(ch)
    # Skip Control ('C') or Separator ('Z') characters
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
        current_cat = ucp.category(ch)
    except ValueError:
        return None, None

    if current_cat != 'Ll':
        return None, None
    
    partner_str = ch.upper()

    if len(partner_str) == 1 and partner_str != ch:
        partner_cp = ord(partner_str)
        try:
            partner_ch = chr(partner_cp)
            partner_cat = ucp.category(partner_ch)
            partner_name = ucp.name(partner_ch)
        except ValueError:
            return None, None
        
        # Confirm partner is an Uppercase Letter (Lu)
        if partner_cat == 'Lu':
            return partner_cp, partner_name

    return None, None


# --------------------------------------------------------------------
# 3. Helper: Convert a Unicode name into an identifier ----------------
# --------------------------------------------------------------------

def macro_name_from_unicode_name(unicode_name: str, strip_case: bool) -> str:
    """
    Build a C‑identifier from the Unicode name, conditionally removing the case
    identifier, and abbreviating the script/language name.
    """
    s = unicode_name
    
    # 1. Remove case properties ONLY if requested (for successful pairs)
    if strip_case:
        s = re.sub(r"(SMALL|CAPITAL|LOWERCASE|UPPERCASE)\s", "", s)
    
    # 2. Convert to uppercase and abbreviate prefix
    s_upper = s.upper()
    s_words = s_upper.split()
    if s_words and s_words[0] in SCRIPT_ABBREVIATIONS:
        abbr = SCRIPT_ABBREVIATIONS[s_words[0]]
        s_upper = abbr + ' ' + ' '.join(s_words[1:])
    
    # 3. Normalize (replace spaces/non-word characters with underscores)
    s_final = re.sub(r"[^\w]", "_", s_upper)
    s_final = re.sub(r"_+", "_", s_final).strip("_") 
    
    return f"UC_{s_final}"


# --------------------------------------------------------------------
# 4. Block Iteration (Fixed and Refined) -----------------------------
# --------------------------------------------------------------------

def get_all_blocks() -> Iterator[UnicodeBlock]:
    """
    Yields UnicodeBlock named tuples by probing unicodedataplus.
    (Uses specific exception handling for robustness.)
    """
    current_name = None
    start_cp = 0
    MAX_CP = 0x110000
    
    for cp in range(MAX_CP):
        try:
            char = chr(cp)
            name = ucp.block(char)
        # NARROWED EXCEPTION: Catching ValueError for invalid code points
        except ValueError:
            name = "No_Block"
        
        if name != current_name:
            if current_name and current_name != "No_Block":
                yield UnicodeBlock(current_name, start_cp, cp - 1)
            current_name = name
            start_cp = cp
            
    # Handle the final block
    if current_name and current_name != "No_Block":
        yield UnicodeBlock(current_name, start_cp, MAX_CP - 1)


# --------------------------------------------------------------------
# 5. Header Generation Logic -----------------------------------------
# --------------------------------------------------------------------

def generate_header_content(block: UnicodeBlock) -> Optional[List[str]]:
    """
    Generates the content lines for a single C header block.
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

        # Skip Capital Letters that defer to a later Lowercase partner
        is_capital_cat = cat == 'Lu'
        if is_capital_cat:
            lower_str = char.lower()
            if len(lower_str) == 1 and lower_str != char:
                lower_partner_cp = ord(lower_str)
                if lower_partner_cp > cp:
                    continue
            
        # SUCCESSFUL PAIR CASE (Anchor: cp is Lowercase)
        if partner_cp is not None: 
            cp1, cp2 = cp, partner_cp
            name1, name2 = name, partner_name 
            glyph1, glyph2 = glyph, printable_glyph(cp2)

            if glyph1 and glyph2:
                comment = f"// {glyph1}/{glyph2}"
            else:
                comment_parts = [f"U+{cp1:04X} ({name1})", f"U+{cp2:04X} ({name2})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_name_from_unicode_name(name1, strip_case=True)
            lines.append(
                f"#define {macro_name:<40} 0x{cp1:04X} 0x{cp2:04X}  {comment}" 
            )
            processed.update({cp1, cp2})
            continue

        # SINGLE CODE POINT CASE
        if cp not in processed:
            if glyph:
                comment = f"// {glyph}"
            else:
                comment_parts = [f"U+{cp:04X} ({name})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            macro_name = macro_name_from_unicode_name(name, strip_case=False)
            lines.append(
                f"#define {macro_name:<40} 0x{cp:04X} 0  {comment}" 
            )
            processed.add(cp)
            
    return lines if lines else None

def emit_header(block: UnicodeBlock, out_dir: pathlib.Path) -> None:
    """
    Writes one header file for the block, providing console feedback.
    """
    
    # 1. Implement robust sanitization for file name
    s_clean = re.sub(r"[^\w]", "_", block.name)
    file_basename = re.sub(r"_+", "_", s_clean).lower().strip("_")
    header_file = out_dir / f"{file_basename}.h"
    
    # Generate the main content
    content_lines = generate_header_content(block)
    
    if content_lines is None:
        print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Skipped** (no defines generated)")
        return
        
    # Define the boilerplate lines
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
# 6. Main Execution --------------------------------------------------
# --------------------------------------------------------------------

def main() -> int:
    """
    Main execution function. Iterates directly over the block generator.
    """
    out_dir = pathlib.Path("generated_headers")
    
    try:
        out_dir.mkdir(exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory '{out_dir}': {e}", file=sys.stderr)
        return 1

    print(f"Generating C headers for Unicode {UNICODE_VERSION}...")

    # Iterate directly over the generator, saving memory and complexity
    for block in get_all_blocks():
        emit_header(block, out_dir)

    print("\nAll headers written to", out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
