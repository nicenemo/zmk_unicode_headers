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
import json 
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import namedtuple

# Import all standard functions from unicodedata2 for updated Unicode data.
from unicodedata2 import name, category, unidata_version 
# The function 'block' is non-standard and is defined below using the loaded data.


# Global constant for unicodedata version (from package)
UNICODE_VERSION = unidata_version

# Global variable for block version (set from JSON file)
UNICODE_BLOCK_VERSION: str = "N/A (not loaded)" # New Global variable

# Define the structure for a Unicode Block
# ADDED 'description' field to hold the scraped summary
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
    Exits with an error if the file is not found or is invalid JSON.
    
    UPDATED: Now reads the top-level object to get 'unicode_version' and 'blocks'.
    """
    global _CACHED_BLOCK_DATA
    global UNICODE_BLOCK_VERSION

    if _CACHED_BLOCK_DATA is None:
        try:
            with open(BLOCKS_DATA_FILE, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
                # 1. Pull the Unicode version
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
            description=entry.get('description', '') # Include the new description field
        )

# --------------------------------------------------------------------
# 1. Helper Function: Check for printable glyph
# --------------------------------------------------------------------

def printable_glyph(cp: int) -> str:
    """Returns the character if it's considered 'printable', otherwise returns an empty string."""
    char = chr(cp)
    # Filter out most non-printable, control, or private use characters
    if char.isprintable() and category(char)[0] not in ("C", "Z"):
        return char
    return ""


# --------------------------------------------------------------------
# 2. Utility Class for Macro Generation (Encapsulation)
# --------------------------------------------------------------------

class MacroGenerator:
    """ 
    Manages the configuration and logic for converting Unicode names into short, 
    clean C macro definitions using a three-layered abbreviation system.
    """

    # ... (The rest of the MacroGenerator class methods: __init__, get_macro_name,
    # find_case_partner, and abbreviation dictionaries are assumed to be here,
    # as they were not explicitly provided for modification.) ...
    
    # NOTE: The full MacroGenerator class is omitted for brevity but its methods are 
    # required for the script to run. Assuming it correctly uses the imported 
    # 'name', 'category', and 'block' functions.
    
    def __init__(self):
        # Placeholder for the actual implementation details
        pass 
        
    def get_macro_name(self, cp: int) -> str:
        # Placeholder for the actual implementation details
        # This function should perform the 3-layer abbreviation
        return f"UC_MACRO_NAME_{cp:X}"

# --------------------------------------------------------------------
# 3. Code Point Processing and Filtering
# --------------------------------------------------------------------

# ... (Functions like process_code_points are assumed to be here) ...


# --------------------------------------------------------------------
# 4. Main Generation Loop
# --------------------------------------------------------------------

# ... (The main loop logic that calls process_code_points is assumed to be here) ...


# --------------------------------------------------------------------
# 5. Header Emission
# --------------------------------------------------------------------

def emit_header(block: UnicodeBlock, output_dir: pathlib.Path, generator: 'MacroGenerator'):
    """
    Generates the C header file content for a given Unicode block and writes it to disk.
    
    UPDATED: Now includes the block's description and the UNICODE_BLOCK_VERSION.
    """
    # 1. Determine file name and macro guard
    macro_name = block.name.upper().replace(' ', '_').replace('-', '_')
    file_name = f"uc_{macro_name.lower()}.h"
    guard_macro = f"UC_H_{macro_name}"
    header_file = output_dir / file_name

    # 2. --- Prepare Description Comment (NEW LOGIC) ---
    description_comment = ""
    if block.description.strip():
        # Format the description to fit within the C comment block
        lines = block.description.strip().split('\n')
        
        # Simple word wrap for better readability in the C header file
        wrapped_lines = []
        for line in lines:
            if line:
                current_line = []
                max_width = 70 # Max line length for content after '* ' prefix
                
                words = line.split()
                if not words: continue

                current_line.append(words[0])
                for word in words[1:]:
                    if len(' '.join(current_line) + ' ' + word) > max_width:
                        wrapped_lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
                if current_line:
                    wrapped_lines.append(" ".join(current_line))

        # Prefix each line with ' * ' and add leading/trailing newline for formatting
        description_comment = "\n * ".join([""] + wrapped_lines)
        description_comment += "\n *"
    # -------------------------------------------------

    # 3. Generate all macro definitions (Placeholder - actual loop is complex)
    # The actual implementation involves iterating over code points and calling 
    # generator.get_macro_name(), but here we use a placeholder:
    
    macro_definitions = ""
    for cp in range(block.start, block.end + 1):
        try:
            char_name = name(chr(cp))
            macro_name_str = generator.get_macro_name(cp)
            glyph = printable_glyph(cp)
            macro_definitions += f"#define {macro_name_str} 0x{cp:04X} // {glyph} {char_name}\n"
        except ValueError:
            # Skip unassigned or non-character code points
            continue


    # 4. Final Content Construction (UPDATED BOILERPLATE)
    all_content = f"""/*
 * Unicode Block: {block.name}
 * Range: U+{block.start:04X}..U+{block.end:04X}
 * Properties: Unicode {UNICODE_VERSION}
 * Block Data: Unicode {UNICODE_BLOCK_VERSION}
 * -------------------------------------------------------------{description_comment}
 */
#ifndef {guard_macro}
#define {guard_macro}

{macro_definitions}

#endif // {guard_macro}
"""

    # 5. Write to file
    header_file.write_text(all_content, encoding="utf-8")
    
    print(f"Processed block '{block.name}' (U+{block.start:04X}...U+{block.end:04X}): **Written** to {header_file.name}")


# --------------------------------------------------------------------
# 6. Main Execution
# --------------------------------------------------------------------

# Note: UNICODE_VERSION is available from unicodedata2 import.
# UNICODE_BLOCK_VERSION is set inside load_block_data().

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
        out_dir.mkdir(exist_ok=True, parents=
