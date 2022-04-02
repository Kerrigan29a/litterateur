# Copyright (c) 2022 Javier Escalada Gómez
# All rights reserved.

import re
import sys


FENCE = re.compile(r'( {0,3})(`{3,}|~{3,})(.*)')
OPT = re.compile(r' *(\S+)')

LANG_REF_PATTERNS = {
    "python": re.compile(r'( *)#[ \t]*<<<(.+)>>>'),
}

def label_lines(f):
    is_code = False
    for l in f:
        if m := FENCE.match(l):
            indent, leader, rest = m.groups()
            if not is_code:
                opts = OPT.findall(rest)
                if len(opts) < 2 or leader != '~~~':
                    continue
                else:
                    lang, filename, desc = opts[0], opts[1], " ".join(opts[2:])
                    yield ("BEGIN", indent, lang, filename, desc, l)
                    is_code = True
            else:
                yield ("END", l)
                is_code = False
        elif is_code:
            yield ("CODE", l)


def extract_blocks(lines):
    block = None
    block_indent = None
    for line in lines:
        match line:
            case ("BEGIN", indent, lang, filename, desc, _):
                block = {
                    "lines": [],
                    "lang": lang,
                    "filename": filename,
                    "desc": desc,
                }
                block_indent = indent
            case ("END", _):
                yield block
                block = None
                block_indent = None
            case ("CODE", raw_line):
                block["lines"].append(raw_line.removeprefix(block_indent))


def index_blocks(blocks):
    index = {}
    for block in blocks:
        index[(block["filename"], block["desc"])] = block
    return index


def walk_blocks(src_block, dst_blocks):
    src_lang = src_block["lang"]
    src_filename = src_block["filename"]
    ref_pattern = LANG_REF_PATTERNS[src_lang]
    for src_line in src_block["lines"]:
        if m := ref_pattern.match(src_line):
            dst_indent, dst_name = m.groups()
            dst_block = dst_blocks[(src_filename, dst_name.strip())]
            dst_lang = dst_block["lang"]
            if src_lang != dst_lang:
                raise ValueError(f"language mismatch: {src_lang} != {dst_lang}")
            for l in walk_blocks(dst_block, dst_blocks):
                yield dst_indent + l
        else:
            yield src_line


with (open(sys.argv[1], "r", encoding="utf-8") as fin,
        open(sys.argv[2], "w", encoding="utf-8") as fout):
    blocks = index_blocks(extract_blocks(label_lines(fin)))
    for l in walk_blocks(blocks[("main.py", "Main")], blocks):
        fout.write(l)
