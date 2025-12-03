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
# 1. Configuration ---------------------------------------------------
# --------------------------------------------------------------------

# The version is derived directly from the unicodedataplus package data
UNICODE_VERSION = ucp.unidata_version

# Dictionary to map common script/language names to two-letter prefixes (ISO codes or common abbreviations)
SCRIPT_ABBREVIATIONS: Dict[str, str] = {
    # ISO 639-1 Language Codes
    "GREEK": "EL",
    "LATIN": "LA",
    "ARABIC": "AR",
    "HEBREW": "HE",
    "THAI": "TH",
    "KHMER": "KM",
    "TIBETAN": "TB",
    
    # Common Script Abbreviations
    "CYRILLIC": "CY",
    "COPTIC": "CP",
    "DEVANAGARI": "DV",
    "BENGALI": "BN",
    "GUJARATI": "GJ",
    "GURMUKHI": "GK",
    "ORIYA": "OR",
    "TAMIL": "TM",
    "TELUGU": "TL",
    
    # Generic/Block Prefixes
    "GENERAL": "GN",
    "COMBINING": "CM",
    "SUPERSCRIPTS": "SS",
    "SUBSCRIPTS": "SB",
    "MATHEMATICAL": "MA",
    "MISCELLANEOUS": "MS",
    "ENCLOSED": "EN",
    "CJK": "CJK",
}

# --------------------------------------------------------------------
# 2. Helper: printable glyph ----------------------------------------
# --------------------------------------------------------------------

def printable_glyph(cp: int) -> Optional[str]:
    """Return a printable representation of *cp* or None if it is not printable."""
    try:
        ch = chr(cp)
    except ValueError:
        return None
        
    cat = ucp.category(ch)
    if cat[0] in ("C", "Z"):        # Control or Separator
        return None
    if not ch.isprintable():
        return None
    return ch


# --------------------------------------------------------------------
# 3. Helper: case partner --------------------------------------------
# --------------------------------------------------------------------

def find_case_partner(cp: int) -> Tuple[Optional[int], Optional[str]]:
    """
    Return (partner_cp, partner_name). This function anchors only on the 
    lowercase letter (category 'Ll') and confirms its partner is uppercase 
    (category 'Lu'). Returns (None, None) otherwise.
    """
    try:
        ch = chr(cp)
        current_cat = ucp.category(ch)
    except ValueError:
        return None, None

    # 1. Anchor only on lowercase letters (Ll)
    if current_cat != 'Ll':
        return None, None
    
    # 2. Find upper partner
    partner_str = ch.upper()

    # Check if a single, different character was returned
    if len(partner_str) == 1 and partner_str != ch:
        partner_cp = ord(partner_str)
        try:
            partner_ch = chr(partner_cp)
            partner_cat = ucp.category(partner_ch)
            partner_name = ucp.name(partner_ch)
        except ValueError:
            return None, None
        
        # 3. Confirm partner is an Uppercase Letter (Lu)
        if partner_cat == 'Lu':
            return partner_cp, partner_name

    return None, None


# --------------------------------------------------------------------
# 4. Helper: Convert a Unicode name into an identifier ----------------
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
    s_final = re.sub(r"_+", "_", s_final).strip("_") # Squeeze and strip
    
    return f"UC_{s_final}"


# --------------------------------------------------------------------
# 5. Block Iteration (Restored to working original logic) ------------
# --------------------------------------------------------------------

def get_all_blocks():
    """
    Yields blocks with .name, .start, .end by probing unicodedataplus.
    """
    # Use the namedtuple from the original context
    Block = namedtuple('Block', ['name', 'start', 'end'])
    
    current_name = None
    start_cp = 0
    MAX_CP = 0x110000
    
    # Iterate over the entire Unicode range
    for cp in range(MAX_CP):
        try:
            char = chr(cp)
            # Use ucp.block(char) to match the original function signature
            name = ucp.block(char) 
        except Exception:
            name = "No_Block"
        
        if name != current_name:
            if current_name and current_name != "No_Block":
                yield Block(current_name, start_cp, cp - 1)
            current_name = name
            start_cp = cp
            
    # Handle the final block, explicitly ending at 0x10FFFF
    if current_name and current_name != "No_Block":
        yield Block(current_name, start_cp, MAX_CP - 1)


# --------------------------------------------------------------------
# 6. Header Generation Logic -----------------------------------------
# --------------------------------------------------------------------

def generate_header_content(block_name: str, start_cp: int, end_cp: int) -> Optional[List[str]]:
    """
    Generates the content lines for a single C header block, excluding the 
    boilerplate. Returns None if no defines are generated.
    """
    
    lines: List[str] = []
    processed: Set[int] = set()

    for cp in range(start_cp, end_cp + 1):
        if cp in processed:
            continue
            
        try:
            char = chr(cp)
            name = ucp.name(char)
            cat = ucp.category(char)
        except ValueError:
            # Skip unassigned or reserved code points.
            continue
            
        glyph = printable_glyph(cp)
        partner_cp, partner_name = find_case_partner(cp)

        # --- Skip Capital Letters that defer to a later Lowercase partner ---
        is_capital_cat = cat == 'Lu'
        if is_capital_cat:
            lower_str = char.lower()
            if len(lower_str) == 1 and lower_str != char:
                lower_partner_cp = ord(lower_str)
                # If the lowercase partner comes later, skip the capital 
                if lower_partner_cp > cp:
                    continue
            
        # --- SUCCESSFUL PAIR CASE (Anchor: cp is Lowercase) ---
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

        # --- SINGLE CODE POINT CASE ---
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

def emit_header(block_name: str, start_cp: int, end_cp: int, out_dir: pathlib.Path) -> None:
    """
    Writes one header file for the block, providing console feedback regardless 
    of whether a file is written or skipped.
    """
    
    # 1. Implement robust sanitization for file name
    s_clean = re.sub(r"[^\w]", "_", block_name)
    file_basename = re.sub(r"_+", "_", s_clean).lower().strip("_")
    header_file = out_dir / f"{file_basename}.h"
    
    # Generate the main content first
    content_lines = generate_header_content(block_name, start_cp, end_cp)
    
    if content_lines is None:
        # CONSOLE FEEDBACK for skipped blocks
        print(f"Processed block '{block_name}' (U+{start_cp:04X}...U+{end_cp:04X}): **Skipped** (no defines generated)")
        return
        
    # Define the boilerplate lines
    boilerplate_lines: List[str] = [
        f"/* {header_file.name} – Unicode constants for U+{start_cp:04X} … U+{end_cp:04X}",
        "*",
        f"* Generated by generate_unicode_headers.py (Unicode {UNICODE_VERSION})",
        "*",
        "* See https://www.unicode.org/versions/latest/ for source data.",
        "*/\n",
        "#pragma once\n"
    ]
    
    all_lines = boilerplate_lines + content_lines
    header_file.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    
    # CONSOLE FEEDBACK for written blocks
    print(f"Processed block '{block_name}' (U+{start_cp:04X}...U+{end_cp:04X}): **Written** to {header_file.name}")

# --------------------------------------------------------------------
# 7. Main Execution --------------------------------------------------
# --------------------------------------------------------------------

def main() -> int:
    """
    Main execution function.
    """
    out_dir = pathlib.Path("generated_headers")
    
    try:
        out_dir.mkdir(exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory '{out_dir}': {e}", file=sys.stderr)
        return 1

    print(f"Generating C headers for Unicode {UNICODE_VERSION}...")

    # Build a list of blocks first, preserving the original script's flow
    blocks: List[Tuple[str, int, int]] = []
    for block in get_all_blocks():
        blocks.append((block.name, block.start, block.end))

    # Iterate over the blocks list to emit headers
    for block_name, start_cp, end_cp in blocks:
        emit_header(block_name, start_cp, end_cp, out_dir)

    print("\nAll headers written to", out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
