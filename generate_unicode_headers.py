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
2. Redundant Word Stripping (e.g., removing 'LETTER', 'DIGIT', 'WITH', 'NUMBER')
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
# 1. Configuration & Named Tuple (Unified Definition) ----------------
# --------------------------------------------------------------------

UNICODE_VERSION = ucp.unidata_version
MAX_UNICODE_CP = 0x110000 
UnicodeBlock = namedtuple('UnicodeBlock', ['name', 'start', 'end'])

# --- Layer 1: Block Prefixes (Custom/ISO 639-1) ---
BLOCK_ABBREVIATIONS: Dict[str, str] = {
    # Default/Fallback: "" prevents the redundant "UC_UC_"
    "DEFAULT": "",
    
    # Latin, Greek, Cyrillic Scripts
    "BASIC LATIN": "LA",
    "LATIN-1 SUPPLEMENT": "L1S",
    "LATIN EXTENDED-A": "LXA",
    "LATIN EXTENDED-B": "LXB",
    "LATIN EXTENDED-C": "LXC",
    "LATIN EXTENDED-D": "LXD",
    "LATIN EXTENDED-E": "LXE",
    "LATIN EXTENDED ADDITIONAL": "LXADD",
    
    "GREEK AND COPTIC": "GRC",
    "CYRILLIC": "CY",
    "CYRILLIC SUPPLEMENTARY": "CYS",
    
    # CJK & Symbols
    "CJK UNIFIED IDEOGRAPHS": "CJK",
    "CJK UNIFIED IDEOGRAPHS EXTENSION A": "CJKA",
    "CJK UNIFIED IDEOGRAPHS EXTENSION B": "CJKB",
    "CJK UNIFIED IDEOGRAPHS EXTENSION C": "CJKC",
    "CJK UNIFIED IDEOGRAPHS EXTENSION D": "CJKD",
    "CJK UNIFIED IDEOGRAPHS EXTENSION E": "CJKE",
    "CJK UNIFIED IDEOGRAPHS EXTENSION F": "CJKF",
    "CJK UNIFIED IDEOGRAPHS EXTENSION G": "CJKG",
    "CJK UNIFIED IDEOGRAPHS EXTENSION H": "CJKH",
    "CJK UNIFIED IDEOGRAPHS EXTENSION I": "CJKI",
    
    "IDEOGRAPHIC DESCRIPTION CHARACTERS": "IDC",
    "CJK STROKES": "CJKST",
    "CJK RADICALS SUPPLEMENT": "CJKR",
    "CJK COMPATIBILITY IDEOGRAPHS": "CJKCI",
    "CJK COMPATIBILITY IDEOGRAPHS SUPPLEMENT": "CJKCIS",
    
    "DINGBATS": "DB",
    "MATHEMATICAL OPERATORS": "MOP",
    "SUPPLEMENTAL MATHEMATICAL OPERATORS": "SMOP",
    "MISCELLANEOUS MATHEMATICAL SYMBOLS-A": "MMSA",
    "MISCELLANEOUS MATHEMATICAL SYMBOLS-B": "MMSB",
    "MATHEMATICAL ALPHANUMERIC SYMBOLS": "MA",
    "LETTERLIKE SYMBOLS": "LS",
    "GEOMETRIC SHAPES": "GS",
    "MISCELLANEOUS SYMBOLS": "MS",
    
    # Other Scripts
    "ARABIC": "AR",
    "ARABIC SUPPLEMENT": "ARS",
    "ARABIC EXTENDED-A": "AREXA",
    "ARABIC EXTENDED-B": "AREXB",
    "ARABIC MATHEMATICAL ALPHABETIC SYMBOLS": "ARMAS",
    "SHAVIAN": "SH",
    "INSCRIPTIONAL PAHLAVI": "IP",
    "MANDAIC": "MD",
    "SYRIAC": "SYR",
    "SAMARITAN": "SAM",
    "IMPERIAL ARAMAIC": "IA",
    "ARMENIAN": "AM",
    "GEORGIAN": "GRG",
    "HEBREW": "HEB",
    "ETHIOPIC": "ET",
    "THAI": "TH",
    "LAO": "LAO",
    "KHMER": "KHM",
    "TIBETAN": "TB",
    "DEVANAGARI": "DV",
    "BENGALI": "BN",
    "GURMUKHI": "GK",
    "GUJARATI": "GJ",
    "ORIYA": "OR",
    "TAMIL": "TM",
    "TELUGU": "TLG",
    "KANNADA": "KND",
    "MALAYALAM": "ML",
    "SINHALA": "SI",
    "BURMESE": "BU",
    "HANUNOO": "HAN",
    "BUHID": "BUH",
    "TAGBANWA": "TAG",
    "KHMER": "KH",
    "BALINESE": "BL",
    "SUNDANESE": "SU",
    "BATAK": "BTK",
    "LEPCHA": "LPC",
    "OL CHIKI": "OC",
    "CHAM": "CHM",
    "VAI": "VAI",
    "SAURASHTRA": "SAU",
    "KAYAH LI": "KL",
    "REJANG": "REJ",
    "AVESTAN": "AV",
    "ANATOLIAN HIEROGLYPHS": "AH",
}

# --- Layer 2: Word Stripping (Redundant Words) ---
# Words to remove from the Unicode name for brevity
REDUNDANT_WORDS: Set[str] = {
    # Redundant descriptor words
    "LETTER", "DIGIT", "NUMBER", "MARK", "SIGN",
    "CHARACTER", "SYMBOL", "POINT", "SEPARATOR", 
    "VARIATION", "SELECTOR", "CONTROL",
    
    # Generic prepositions/conjunctions
    "WITH", "AND", "OF", "IN", "THE", "FOR",
    
    # Common type/style descriptors
    "SMALL", "CAPITAL", "SCRIPT", "FRAKTUR", "DOUBLE-STRUCK",
    "SAN-SERIF", "MONOSPACE", "ITALIC", "BOLD",
    
    # Typographic/Layout words
    "LEFT", "RIGHT", "UPPER", "LOWER", "TOP", "BOTTOM",
    "MIDDLE", "START", "END", "HORIZONTAL", "VERTICAL",
    
    # Specific script-related common words
    "MODIFIER", "COMBINING", "SUPERSCRIPT", "SUBSCRIPT",
    "PUNCTUATION", "BOX", "DRAWINGS",
}

# --- Layer 3: Internal Abbreviations ---
# Common long words/phrases to abbreviate internally
INTERNAL_ABBREVIATIONS: Dict[str, str] = {
    "SANS-SERIF": "SS",
    "DOUBLE-STRUCK": "DS",
    "MATHEMATICAL": "MA",
    "OPERATOR": "OP",
    "IDEOGRAPHIC": "ID",
    "DESCRIPTION": "DESCION",
    "ALPHANUMERIC": "AN",
    "EXTENDED": "EX",
    "SUPPLEMENT": "SUP",
    "ADDITIONAL": "ADD",
    "MISCELLANEOUS": "MISC",
    "COMPATIBILITY": "COMP",
    "SCROLLED": "SC",
    "BLACK-LETTER": "BL",
    "TURNED": "T",
    "REVERSED": "REV",
    "SANS": "SS",
    "SERIF": "SF",
    "FRAKTUR": "FR",
    "MONOSPACE": "MS",
    "ITALIC": "IT",
    "TILDE": "TILD",
    "DIAERESIS": "DIAR",
    "CIRCUMFLEX": "CIRC",
    "ACUTE": "ACU",
    "GRAVE": "GRV",
    "STROKE": "STR",
    "LUNATE": "LUN",
}


# --------------------------------------------------------------------
# 2. Name Sanitization -----------------------------------------------
# --------------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    """
    Sanitizes a Unicode name (e.g., 'LATIN SMALL LETTER A') into a C
    macro-style identifier (e.g., 'LATIN_SMALL_LETTER_A').
    """
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Replace hyphens with underscores, e.g., 'MINUS-SIGN' -> 'MINUS_SIGN'
    name = name.replace('-', '_')
    return name

def _abbreviate_name(name: str, block_name: str) -> str:
    """
    Applies the three layers of abbreviation/sanitization.
    1. Apply Block Prefix (Layer 1)
    2. Strip redundant words (Layer 2)
    3. Apply internal abbreviations (Layer 3)
    """
    # 1. Apply Block Prefix
    prefix = BLOCK_ABBREVIATIONS.get(block_name.upper(), BLOCK_ABBREVIATIONS["DEFAULT"])
    if prefix:
        final_name = [prefix]
    else:
        final_name = []
        
    # Standardize the name words
    words = name.split('_')
    
    for word in words:
        if not word:
            continue
            
        # 2. Strip redundant words (Layer 2)
        if word in REDUNDANT_WORDS:
            continue
            
        # 3. Apply internal abbreviations (Layer 3)
        abbreviated = INTERNAL_ABBREVIATIONS.get(word, word)
        final_name.append(abbreviated)
        
    # Fallback to the full name if all abbreviation layers resulted in an empty string
    if not final_name and prefix:
         final_name.append(prefix)
    if not final_name:
        final_name = name.split('_')
        
    # Re-join, removing multiple underscores
    result = '_'.join(final_name)
    result = re.sub(r'_{2,}', '_', result) # Remove double+ underscores
    result = result.strip('_')
    
    return result


def get_macro_name(cp: int, block_name: str) -> str:
    """
    Fetches and processes the Unicode name for a code point.
    """
    try:
        # Get the canonical name from unicodedataplus
        canonical_name = ucp.name(chr(cp))
        
        # Handle <control> and other special names (e.g., U+E0000..U+E007F)
        if canonical_name.startswith('<'):
            # For named control codes, use the full name
            if canonical_name.endswith('>'):
                # Extract the name part without angle brackets
                base_name = canonical_name[1:-1]
            else:
                # Fallback for un-named codes (shouldn't happen with ucp)
                return f"RESERVED_U{cp:04X}" 
        else:
            base_name = canonical_name
            
        # Clean up the base name
        sanitized_name = _sanitize_name(base_name)
        
        # Apply abbreviations
        abbreviated_name = _abbreviate_name(sanitized_name, block_name)
        
        # Prepend the main prefix
        return f"UC_{abbreviated_name}"
        
    except ValueError:
        # Happens for unassigned code points
        return f"RESERVED_U{cp:04X}"
    except Exception:
        # Catch-all for unexpected issues
        return f"UNKNOWN_U{cp:04X}"

# --------------------------------------------------------------------
# 3. Utility - Case Mapping ------------------------------------------
# --------------------------------------------------------------------

def get_case_pair(cp: int) -> Tuple[int, int]:
    """
    Finds the lowercase and uppercase code point for a given character.
    If a character is not case-pairable, the non-existent case is 0.
    
    Returns: (lower_cp, upper_cp)
    """
    try:
        char = chr(cp)
        lower_char = char.lower()
        upper_char = char.upper()
        
        lower_cp = ord(lower_char) if lower_char != char else 0
        upper_cp = ord(upper_char) if upper_char != char else 0

        # Special logic to handle single-case characters that are part of a pair,
        # e.g., GREEK SMALL LETTER ALPHA (U+03B1) should pair with GREEK CAPITAL LETTER ALPHA (U+0391)
        # However, unicodedataplus's .lower()/.upper() handles this correctly.
        # We also need to handle the case where .upper() returns the lowercase character, 
        # which means it is a cased character, but has no distinct uppercase form 
        # (e.g., 'ſ' which uppercases to 'S'). The current logic should handle this.
        # But we need the *other* case.

        # If lower_cp is 0 (i.e., char.lower() == char), try ucp.lookup_other_case()
        if lower_cp == 0:
            try:
                # Tries to find the other case mapping, which is typically the opposite case
                other_case_char = ucp.lookup_other_case(char)
                if other_case_char:
                    # If the current char is 'a' and other is 'A', then we want ord('A')
                    if upper_char == char: # current char is already upper, looking for lower
                         return (ord(other_case_char), cp) if other_case_char.islower() else (0, cp)
                    else: # current char is lower, looking for upper
                         return (cp, ord(other_case_char)) if other_case_char.isupper() else (cp, 0)
                         
            except AttributeError:
                # Older unicodedataplus versions may lack lookup_other_case
                pass
            except Exception:
                pass
                
        # Final check to ensure we only return a valid pair (one is 0, the other is cp)
        # This is for characters that are their own case (e.g., '1', '§')
        if lower_cp == cp and upper_cp == cp:
            return (cp, 0) if char.islower() else (0, cp)
        
        # Prioritize the default lower/upper logic
        if lower_cp != cp and upper_cp == cp: # Is a lowercase char
            return (cp, upper_cp)
        if upper_cp != cp and lower_cp == cp: # Is an uppercase char
            return (lower_cp, cp)
            
        # If both are the same, treat as single case for now unless specific rule applies
        if lower_cp == cp and upper_cp == cp:
            return (cp, 0) if char.islower() else (0, cp)
            
        return (lower_cp, upper_cp)

    except ValueError:
        return (0, 0)
    except Exception:
        return (0, 0)


# --------------------------------------------------------------------
# 4. Data Gathering --------------------------------------------------
# --------------------------------------------------------------------

def get_all_blocks() -> Iterator[UnicodeBlock]:
    """
    Yields blocks with .name, .start, .end by probing unicodedataplus.
    """
    Block = namedtuple('Block', ['name', 'start', 'end'])
    
    current_name = None
    start_cp = 0
    
    # Iterate over the entire Unicode range
    for cp in range(MAX_UNICODE_CP):
        try:
            char = chr(cp)
            name = ucp.block(char)
        except Exception:
            name = "No_Block"
        
        if name != current_name:
            if current_name and current_name != "No_Block":
                # Handle the case where the block range ends one before the last code point
                yield Block(current_name, start_cp, cp - 1)
            current_name = name
            start_cp = cp
            
    # Yield the last block if it exists
    if current_name and current_name != "No_Block":
        yield Block(current_name, start_cp, 0x10FFFF)
        
# --------------------------------------------------------------------
# 5. Output Generation -----------------------------------------------
# --------------------------------------------------------------------

def emit_header(block: UnicodeBlock, out_dir: pathlib.Path) -> None:
    """
    Generates a single C header file for a Unicode block.
    """
    content_lines: List[str] = []
    
    # Generate the header file name (e.g., 'basic_latin.h')
    file_name = block.name.lower().replace(' ', '_').replace('-', '_') + ".h"
    header_file = out_dir / file_name

    # 1. Gather all code points and generate the content
    for cp in range(block.start, block.end + 1):
        macro_name = get_macro_name(cp, block.name)
        
        # Get case pairing for C++ comment
        lower_cp, upper_cp = get_case_pair(cp)
        
        # Determine the C++ comment based on case and printability
        try:
            char = chr(cp)
            
            # Check for printable/visible characters
            is_visible = ucp.category(char) not in ('Cc', 'Cf', 'Cn', 'Co', 'Cs')
            
            if lower_cp != 0 and upper_cp != 0:
                # Cased pair (e.g., 'a/A')
                comment = f"// {chr(lower_cp)}/{chr(upper_cp)}"
                # Use the current code point as the lowercase constant
                # and the other one (upper_cp) as the other case constant
                other_case_value = upper_cp
            elif is_visible:
                # Visible single character (e.g., '1', '§')
                comment = f"// {char}"
                other_case_value = 0
            else:
                # Non-visible, named control, or format character
                comment = f"/* U+{cp:04X} ({ucp.name(char)}) */"
                other_case_value = 0
                
        except ValueError:
            # Unassigned code points
            comment = f"/* U+{cp:04X} (Unassigned) */"
            other_case_value = 0
        except Exception:
            comment = f"/* U+{cp:04X} (Error) */"
            other_case_value = 0

        # The macro definition line: #define MACRO_NAME 0xXXXXXX OTHER_CASE_CP // comment
        # Format: 40 chars for macro name, 8 chars for hex, 1 char space, 8 chars for other case hex
        line = f"#define {macro_name:<40} 0x{cp:04X} {other_case_value:04X}  {comment}"
        content_lines.append(line)
        
    # 3. Create boilerplate header text
    boilerplate_lines: List[str] = f"""\
/* {header_file.name} – Unicode constants for U+{block.start:04X} … U+{block.end:04X}
*
* Generated by {pathlib.Path(__file__).name} (Unicode {UNICODE_VERSION})
*
* See https://www.unicode.org/versions/latest/ for source data.
*/

#pragma once

""".splitlines()
    
    all_lines = boilerplate_lines + content_lines
    header_file.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    
    print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Written** to {header_file.name}")


# --------------------------------------------------------------------
# 6. Main Execution --------------------------------------------------
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
        out_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        print(f"Error creating output directory '{out_dir}': {e}", file=sys.stderr)
        return 1

    print(f"Generating C headers for Unicode {UNICODE_VERSION}...")

    for block in get_all_blocks():
        emit_header(block, out_dir)

    print("\nAll headers written to specified directory.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
