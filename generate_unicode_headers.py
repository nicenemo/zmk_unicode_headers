#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_unicode_headers.py

Generates C header files with Unicode constants for every code point.
This version is optimized for maximum brevity, collision avoidance, and 
maintainability, featuring:
1. Structured block abbreviations (UC_BL_, UC_SH_, etc.).
2. Aggressive stripping of redundant words (LETTER, DIGIT).
3. Abbreviation of stylistic descriptors (SANS_SERIF -> SS).
4. Pythonic implementation for efficiency and clarity.
"""

import pathlib
import re
import sys
import unicodedataplus as ucp
from typing import Dict, List, Set, Tuple, Optional
from collections import namedtuple

# --------------------------------------------------------------------
# 1. Configuration (Organized for Maintainability) -------------------
# --------------------------------------------------------------------

UNICODE_VERSION = ucp.unidata_version

# Initialize the main dictionary with the mandatory fallback default
BLOCK_ABBREVIATIONS: Dict[str, str] = {
    "DEFAULT": "UC", 
}

# 1.1 Latin, Greek, Cyrillic Scripts
BLOCK_ABBREVIATIONS.update({
    "BASIC LATIN": "BL",
    "LATIN-1 SUPPLEMENT": "L1S",
    "LATIN EXTENDED-A": "LETA",
    "LATIN EXTENDED-B": "LETB",
    "LATIN EXTENDED-C": "LETC",
    "LATIN EXTENDED-D": "LETD",
    "LATIN EXTENDED-E": "LETE",
    "GREEK AND COPTIC": "GRC",
    "GREEK EXTENDED": "GREX",
    "CYRILLIC": "CY",
    "CYRILLIC SUPPLEMENT": "CYS",
})

# 1.2 Other Major Scripts
BLOCK_ABBREVIATIONS.update({
    "ARMENIAN": "AM",
    "HEBREW": "HE",
    "ARABIC": "AR",
    "DEVANAGARI": "DV",
    "SHAVIAN": "SH",
    "ADLAM": "ADL",
    "AVESTAN": "AV",
    "BRAHMI": "BR",
    "EGYPTIAN HIEROGLYPHS": "EGYP",
})

# 1.3 CJK and Hangul
BLOCK_ABBREVIATIONS.update({
    "HANGUL JAMO": "HJ",
    "HANGUL SYLLABLES": "HSY",
    "KATAKANA": "KT",
    "HIRAGANA": "HR",
    "CJK UNIFIED IDEOGRAPHS": "CJK",
    "CJK UNIFIED IDEOGRAPHS EXTENSION A": "CJKA",
})

# 1.4 Symbols and Punctuation
BLOCK_ABBREVIATIONS.update({
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
})

# 1.5 Specials
BLOCK_ABBREVIATIONS.update({
    "HIGH SURROGATES": "HS",
    "LOW SURROGATES": "LS",
    "PRIVATE USE AREA": "PUA",
})


# The set of redundant words to strip from the *body* of the macro name.
REDUNDANT_SCRIPT_WORDS: Set[str] = {
    "LETTER", "DIGIT", "COMMA", "CHARACTER", "SYMBOL", 
    "LATIN", "GREEK", "CYRILLIC", "ARABIC", "HEBREW", "SHAVIAN", "COPTIC",
    "DEVANAGARI", "BENGALI", "GUJARATI", "GURMUKHI", "ORIYA", "TAMIL", "TELUGU",
    "CJK", "HANGUL", "KATAKANA", "HIRAGANA", "MATHEMATICAL", "ENCLOSED", 
    "MISCELLANEOUS", "SUPPLEMENTAL", "EXTENDED", "ADDITIONAL", "COMPATIBILITY",
    "IDEOGRAPHS", "FORMS", "VARIATION", "SELECTOR", "ALPHABETIC", 
    "ABBREVIATION", "TELEGRAM", "EMOJI",
}

# Dictionary to abbreviate long stylistic or descriptive words *within* the macro body.
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

def find_case_partner(cp: int) -> Tuple[Optional[int], str]:
    """
    Return (partner_cp, partner_name). Anchors only on the lowercase letter 
    (category 'Ll') and confirms its partner is uppercase (category 'Lu').
    """
    ch = chr(cp)

    try:
        current_cat = ucp.category(ch)
    except ValueError:
        return None, ""

    if current_cat != 'Ll':
        return None, ""
    
    partner_str = ch.upper()

    if len(partner_str) == 1 and partner_str != ch:
        partner_cp = ord(partner_str)
        try:
            partner_cat = ucp.category(chr(partner_cp))
            partner_name = ucp.name(chr(partner_cp))
        except ValueError:
            return None, ""
        
        if partner_cat == 'Lu':
            return partner_cp, partner_name

    return None, ""


# --------------------------------------------------------------------
# 4. Emit a single header file --------------------------------------
# --------------------------------------------------------------------

def emit_header(block_name: str,
                start_cp: int,
                end_cp: int,
                out_dir: pathlib.Path) -> None:
    """
    Write one header for the block. Skips the file if no defines are generated.
    """
    # File name sanitization
    s_clean = re.sub(r"[^\w]", "_", block_name)
    s_clean = re.sub(r"_+", "_", s_clean)
    file_basename = s_clean.lower().strip("_")
    
    header_file = out_dir / f"{file_basename}.h"

    lines: List[str] = [
        f"/* {header_file.name} – Unicode constants for U+{start_cp:04X} … U+{end_cp:04X}",
        "*",
        f"* Generated by generate_unicode_headers.py (Unicode {UNICODE_VERSION})",
        "*",
        "* See https://www.unicode.org/versions/latest/ for source data.",
        "*/\n",
        "#pragma once\n"
    ]
    
    BOILERPLATE_COUNT = len(lines)
    processed: Set[int] = set()
    block_abbr = BLOCK_ABBREVIATIONS.get(block_name.upper(), BLOCK_ABBREVIATIONS["DEFAULT"])
    
    for cp in range(start_cp, end_cp + 1):
        if cp in processed:
            continue
            
        try:
            name = ucp.name(chr(cp))
        except ValueError:
            continue
            
        glyph = printable_glyph(cp)
        partner_cp, partner_name = find_case_partner(cp)
        partner_glyph = printable_glyph(partner_cp) if partner_cp else None

        # Logic to skip Capital Letters that defer to a later Lowercase partner 
        is_capital_cat = ucp.category(chr(cp)) == 'Lu'
        lower_str = chr(cp).lower()
        if is_capital_cat and len(lower_str) == 1 and lower_str != chr(cp):
            if ord(lower_str) > cp:
                continue
            
        # SUCCESSFUL PAIR CASE
        if partner_cp: 
            cp1, cp2 = cp, partner_cp
            name1 = name
            
            # Determine comment text
            if glyph and partner_glyph:
                comment = f"// {glyph}/{partner_glyph}"
            else:
                comment_parts = [f"U+{cp1:04X} ({name1})", f"U+{cp2:04X} ({partner_name})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            lines.append(
                f"#define {macro_name_from_unicode_name(block_abbr, name1, strip_case=True):<40} 0x{cp1:04X} 0x{cp2:04X}  {comment}" 
            )
            processed.update({cp1, cp2})
            continue

        # SINGLE CODE POINT CASE
        if cp not in processed:
            
            # Determine comment text
            if glyph:
                comment = f"// {glyph}"
            else:
                comment_parts = [f"U+{cp:04X} ({name})"]
                comment = f"/* {' '.join(comment_parts)} */"
            
            lines.append(
                f"#define {macro_name_from_unicode_name(block_abbr, name, strip_case=False):<40} 0x{cp:04X} 0  {comment}" 
            )
            processed.add(cp)

    if len(lines) > BOILERPLATE_COUNT:
        header_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Written {header_file}")
    else:
        print(f"Skipping {header_file} (no defines generated)")


# --------------------------------------------------------------------
# 5. Convert a Unicode name into an identifier ----------------------
# --------------------------------------------------------------------

def macro_name_from_unicode_name(block_abbr: str, unicode_name: str, strip_case: bool) -> str:
    """
    Build a short, clean C‑identifier from the Unicode name.
    """
    s = unicode_name
    
    # 1. Strip case words if generating a pair
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
        
        # Apply internal abbreviation if available
        abbreviated_part = MACRO_BODY_ABBREVIATIONS.get(part, part)
        final_parts.append(abbreviated_part)

    s_final = '_'.join(final_parts)
        
    # Final cleanup of underscores
    s_final = re.sub(r"_+", "_", s_final).strip('_')
    
    # Fallback if filtering removed everything
    if not s_final:
        # Use the original name's last word as a fallback
        s_final = unicode_name.upper().split(' ')[-1]
        if not s_final or s_final in REDUNDANT_SCRIPT_WORDS:
             s_final = "CHAR"

    # Final Macro format: UC_{BLOCK_ABBR}_{NAME_BODY}
    return f"UC_{block_abbr}_{s_final}"


def get_all_blocks():
    """
    Yields blocks with .name, .start, .end by probing unicodedataplus.
    """
    Block = namedtuple('Block', ['name', 'start', 'end'])
    
    current_name = None
    start_cp = 0
    
    # Iterate over the entire Unicode range (0x0 to 0x10FFFF)
    for cp in range(0x110000):
        try:
            char = chr(cp)
            name = ucp.block(char)
        except ValueError: # Specifically handles invalid code points
            name = "No_Block"
        
        if name != current_name:
            if current_name and current_name != "No_Block":
                # End block at cp - 1
                yield Block(current_name, start_cp, cp - 1)
            current_name = name
            start_cp = cp
            
    # Yield the final block
    if current_name and current_name != "No_Block":
        yield Block(current_name, start_cp, 0x10FFFF)
        
# --------------------------------------------------------------------
# 6. Main ---------------------------------------------------------------
# --------------------------------------------------------------------

def main() -> None:
    # Set the output directory
    out_dir = pathlib.Path("generated_headers")
    out_dir.mkdir(exist_ok=True)

    # Process and emit headers for each block (Pythonic direct iteration over the generator)
    for block in get_all_blocks():
        emit_header(block.name, block.start, block.end, out_dir)

    print("\nAll headers written to", out_dir.resolve())


if __name__ == "__main__":
    sys.exit(main())
