# Code generated from README.md; DO NOT EDIT.
# Command used: litterateur.py README.md
#line README.md:340
# -*- coding: utf-8 -*-
#line README.md:4
"""
Quick-and-dirty "literate programming" tool to extract code from Markdown files

Copyright (c) 2022 Javier Escalada Gómez  
All rights reserved.
License: BSD 3-Clause Clear License
"""

__author__ = "Javier Escalada Gómez"
__email__ = "kerrigan29a@gmail.com"
__version__ = "0.4.0"
__license__ = "BSD 3-Clause Clear License"
#line README.md:342

import re
import sys
import argparse
import os.path
import json
try:
    from custom_json_encoder import CustomJSONEncoder
except ImportError:
    CustomJSONEncoder = None

#line README.md:33
FENCE = re.compile(r'( {0,3})(`{3,}|~{3,})(.*)')
OPT = re.compile(r' *(\S+)')
#line README.md:354

#line README.md:127
REF_PATTERN = re.compile(r'<<<(.+)>>>')
PYTHON_REF_PATTERN = re.compile(r'( *)#[ \t]*' + REF_PATTERN.pattern)
C_REF_PATTERN = re.compile(r'( *)//[ \t]*' + REF_PATTERN.pattern)
LANG_REF_PATTERNS = {
    "python": PYTHON_REF_PATTERN,
    "py": PYTHON_REF_PATTERN,
    "c": C_REF_PATTERN,
    "cpp": C_REF_PATTERN,
    "go": C_REF_PATTERN,
}
#line README.md:356

#line README.md:202
PYTHON_COMMENT_FORMAT = "# {0}"
C_COMMENT_FORMAT = "// {0}"
LANG_COMMENT_FORMATS = {
    "python": PYTHON_COMMENT_FORMAT,
    "py": PYTHON_COMMENT_FORMAT,
    "c": C_COMMENT_FORMAT,
    "cpp": C_COMMENT_FORMAT,
    "go": C_COMMENT_FORMAT,
}
#line README.md:358

#line README.md:224
PYTHON_MAP_FORMAT = "#line {file}:{line}"
C_MAP_FORMAT = "#line {line} {file}"
GO_MAP_FORMAT = "//line {file}:{line}"
LANG_LINE_FORMATS = {
    "python": PYTHON_MAP_FORMAT,
    "py": PYTHON_MAP_FORMAT,
    "c": C_MAP_FORMAT,
    "cpp": C_MAP_FORMAT,
    "go": GO_MAP_FORMAT,
}
#line README.md:360

#line README.md:51
def label_lines(f):
    is_code = False
    is_ignored_code = False
    for i, l in enumerate(f):
        if m := FENCE.match(l):
            indent, leader, rest = m.groups()
            if leader != '~~~' or is_ignored_code:
                yield ("TEXT", l, i+1)
                is_ignored_code = not is_ignored_code
            elif not is_code:
                opts = OPT.findall(rest)
                if len(opts) < 2 or leader != '~~~':
                    yield ("TEXT", l, i+1)
                    is_ignored_code = True
                elif not is_ignored_code:
                    lang, filename, desc = opts[0], opts[1], " ".join(opts[2:])
                    yield ("BEGIN", indent, lang, filename, desc, l, i+1)
                    is_code = True
            else:
                yield ("END", l, i+1)
                is_code = False
        elif is_code:
            yield ("CODE", l, i+1)
        else:
            yield ("TEXT", l, i+1)
#line README.md:362

#line README.md:81
def extract_blocks(lines):
    block = None
    block_indent = None
    for line in lines:
        match line:
            case ("BEGIN", indent, lang, filename, desc, _, linenum):
                block = {
                    "beg": linenum,
                    "end": None,
                    "txt": [],
                    "lang": lang,
                    "filename": filename,
                    "desc": desc,
                }
                block_indent = indent
            case ("END", _, linenum):
                block["end"] = linenum
                yield block
                block = None
                block_indent = None
            case ("CODE", raw_line, linenum):
                block["txt"].append((linenum, raw_line.removeprefix(block_indent)))
#line README.md:364

#line README.md:110
def make_ref(filename, desc):
    return filename + ":" + desc

def parse_references(blocks):
    for block in blocks:
        ref_pattern = LANG_REF_PATTERNS[block["lang"]]
        for i in range(len(block["txt"])):
            linenum, line = block["txt"][i]
            if m := ref_pattern.match(line):
                indent, name = m.groups()
                block["txt"][i] = (linenum, (indent, make_ref(block["filename"], name.strip())))
        yield block
#line README.md:366

#line README.md:145
def index_blocks(blocks):
    index = {}
    for block in blocks:
        index[make_ref(block["filename"], block["desc"])] = block
    return index
#line README.md:368

#line README.md:157
def walk_blocks(src_block, dst_blocks, input_filename):

    #line README.md:216
    line_format = LANG_LINE_FORMATS[src_block["lang"]]
    def line_directive(line):
        return line_format.format(file=input_filename, line=line+1) + "\n"
    #line README.md:160

    src_lang = src_block["lang"]
    src_filename = src_block["filename"]

    yield line_directive(src_block["beg"])
    for linenum, src_line in src_block["txt"]:
        if isinstance(src_line, tuple): 
            dst_indent, dst_ref = src_line
            dst_block = dst_blocks[dst_ref]
            if dst_block == src_block:
                raise ValueError(f"detected self-reference in {input_filename} at line {linenum}")
            dst_lang = dst_block["lang"]
            if src_lang != dst_lang:
                raise ValueError(f"language mismatch: {src_lang} != {dst_lang}")
            for l in walk_blocks(dst_block, dst_blocks, input_filename):
                yield dst_indent + l
            yield dst_indent + line_directive(linenum)
        else:
            yield src_line
#line README.md:370

#line README.md:193
def compose_warning_message(input, lang):
    comment_format = LANG_COMMENT_FORMATS[lang]
    yield comment_format.format(f"Code generated from {input}; DO NOT EDIT.") + "\n"
    yield comment_format.format(f"Command used: {' '.join(sys.argv)}") + "\n"
#line README.md:372

#line README.md:242
class ParseError(Exception):
    pass

def parse_args():
    parser = argparse.ArgumentParser(
        description='Quick-and-dirty "literate programming" tool to extract code from Markdown files')
    parser.add_argument("input", metavar='FILE',
        help="Input Markdown file")
    parser.add_argument("-e", "--encoding", metavar='ENCODING', default="utf-8", 
        help="Encoding (default: %(default)s)")
    parser.add_argument("-r", "--rename", metavar='OLD_NAME:NEW_NAME', action='append',
        help="Rename a file in the input Markdown file")
    parser.add_argument("-o", "--overwrite", action='store_true',
        help="Overwrite output files (default: %(default)s)")
    parser.add_argument("-D", "--dump", action='store_true',
        help="Dump the internal state(default: %(default)s)")
    args = parser.parse_args()
    rename = {}
    for r in args.rename or []:
        try:
            old, new = r.split(":")
        except ValueError:
            raise ParseError(f"invalid rename format: {r}\nIt must follow the format OLD_NAME:NEW_NAME")
        rename[old] = new
    args.rename = rename
    return args
#line README.md:374
    
#line README.md:273
CRED = "\033[31m"
CGREEN = "\033[32m"
CYELLOW = "\033[33m"
CBOLD = "\033[1m"
CDIM = "\033[2m"
CEND = "\033[0m"

def perror(msg):
    print(f"{CRED}  ERROR{CEND} - {msg}")

def pwarning(msg):
    print(f"{CYELLOW}WARNING{CEND} - {msg}")

def pinfo(msg):
    print(f"{CGREEN}   INFO{CEND} - {msg}")

if CustomJSONEncoder is not None:
    def indent_hint(path, collection, indent, width):
        if len(collection) == 0:
            return False
        if len(path) == 0:
            return True
        if path[-1] in ["txt"]:
            return True
        return False

def run(args):
    pinfo(f"Reading {CDIM}{args.input}{CEND}")
    with open(args.input, encoding=args.encoding) as f:
        blocks = index_blocks(parse_references(extract_blocks(label_lines(f))))
    if args.dump:
        with open(args.input + ".json", "w", encoding=args.encoding) as f:
            kwargs = {
                "cls": CustomJSONEncoder,
                "width": 120,
                "indent_hint": indent_hint,
            } if CustomJSONEncoder is not None else {}
            json.dump(blocks, f, indent=2, **kwargs)
    for block in blocks.values():
        filename = block["filename"]
        desc = block["desc"]    
        if desc.lower() == "main":
            filename = args.rename.get(filename, filename)
            if os.path.exists(filename):
                if not args.overwrite:
                    perror(f"{CDIM}{filename}{CEND} already exists.")
                    pinfo(f"Skipping {CDIM}{filename}{CEND}")
                    return 1
                else:
                    pwarning(f"{CDIM}{filename}{CEND} already exists.")
                    pinfo(f"Overwriting {CDIM}{filename}{CEND}")
            else:
                pinfo(f"Writing {CDIM}{filename}{CEND}")
            with open(filename, "w", encoding=args.encoding) as f:
                for l in compose_warning_message(args.input, block["lang"]):
                    f.write(l)
                try:
                    for l in walk_blocks(block, blocks, args.input):
                        f.write(l)
                except ValueError as e:
                    perror(e)
                    return 1
    return 0
#line README.md:376

def main():
    try:
        exit(run(parse_args()))
    except ParseError as e:
        perror(e)
    except Exception as e:
        import traceback
        perror(e)
        traceback.print_exc()
    exit(1)

if __name__ == "__main__":
    main()
