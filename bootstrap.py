#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2022 Javier Escalada Gómez  
# All rights reserved.
# License: BSD 3-Clause Clear License

import re
import sys
import shlex
import argparse


def parse_block_args(args):
    parser = BlockArgumentParser(prog="Valid Block Arguments", add_help=False)
    # Common
    parser.add_argument("--prefix", metavar="STR", dest="prefixes",
        action='append', default=[],
        help="Add a prefix before the block")
    parser.add_argument("--suffix", metavar="STR", dest="suffixes",
        action='append', default=[],
        help="Add a suffix after the block")
    # Specific
    parser.add_argument("--prelude", metavar="STR", dest="preludes",
        action='append', default=[],
        help="Add a prelude before the block (and before the location (or line) directive)")
    parser.add_argument("--continue", dest="kontinue", action="store_true",
        help="Continue the previous block")

    return parser.parse_args(args)


class BlockArgumentError(Exception):
    def __init__(self, usage, *args) -> None:
        super().__init__(*args)
        self.usage = usage


class BlockArgumentParser(argparse.ArgumentParser):
    def error(self, msg):
        raise BlockArgumentError(self.format_help(), msg)


def label_lines(f):
    HEADING = re.compile(r'^( {0,3})(#{1,6})(?:\n|\s+?(.*?)(?:\n|\s+?#+\s*?$))')
    FENCE = re.compile(r'^( {0,3})(`{3,}|~{3,})(.*)$')

    is_code = False
    is_ignored_code = False
    for line in f:
        if m := FENCE.match(line):
            indent, fence, args = m.groups()
            if fence != '~~~' or is_ignored_code:
                yield ("TEXT", line)
                is_ignored_code = not is_ignored_code
            elif is_code:
                yield ("END", line)
                is_code = False
            else:
                args = shlex.split(args)
                if len(args) < 1:
                    yield ("TEXT", line)
                    is_ignored_code = True
                else:
                    lang, args = args[0], parse_block_args(args[1:])
                    yield ("BEGIN", indent, lang, args, line)
                    is_code = True
        elif is_code:
            yield ("CODE", line)
        elif m := HEADING.match(line):
            indent, level, text = m.groups()
            yield ("HEADING", indent, level, text, line)
        else:
            yield ("TEXT", line)


def extract_blocks(lines):
    name = None 
    block = None
    for i, line in enumerate(lines):
        match line:
            case ("BEGIN", indent, lang, args, _):
                block = {
                    "name": name,
                    "beg": i+1,
                    "end": None,
                    "lang": lang,
                    "args": args,
                    "indent": indent,
                    "lines": [],
                }
            case ("END", _):
                block["end"] = i+1
                yield block
            case ("CODE", raw_line):
                block["lines"].append({
                    "row": i+1,
                    "txt": raw_line.removeprefix(block["indent"])
                })
            case ("HEADING", indent, _, text, _):
                name = text
            case ("TEXT", _):
                name = None


REF = r'<<([^|>]+)\|?([^>]*)>>'
WS = r'[ \t]*'
TXT_REF = re.compile(fr'^({WS}){REF}{WS}$')
PYTHON_REF = re.compile(fr'^({WS})#{REF}{WS}$')
C_REF = re.compile(fr'^({WS})//{REF}{WS}$')
LANG_REFS = {
    "python": PYTHON_REF,
    "py": PYTHON_REF,
    "c": C_REF,
    "cpp": C_REF,
    "go": C_REF,
    "txt": TXT_REF,
    "text": TXT_REF,
    "md": TXT_REF,
}


def parse_references(blocks):
    for block in blocks:
        ref_re = LANG_REFS[block["lang"]]
        for i, line in enumerate(block["lines"]):
            if m := ref_re.match(line["txt"]):
                indent, name, args = m.groups()
                block["lines"][i] = {
                    **line,
                    "indent": indent,
                    "name": name.strip(),
                    "args": parse_ref_args(shlex.split(args.strip())),
                }
        yield block


def parse_ref_args(args):
    parser = RefArgumentParser(prog="Valid Ref Arguments", add_help=False)
    # Common
    parser.add_argument("--prefix", metavar="STR", dest="prefixes",
        action='append', default=[],
        help="Add a prefix before the ref")
    parser.add_argument("--suffix", metavar="STR", dest="suffixes",
        action='append', default=[],
        help="Add a suffix after the ref")

    # Args
    def label(kind):
        def _(x):
            return (kind, x)
        return _

    parser.add_argument("--lit-arg", metavar="STR", dest="args",
        action='append', type=label("LIT"), default=[],
        help="Add a literal argument to the current ref")
    parser.add_argument("--ref-arg", metavar="STR", dest="args",
        action='append', type=label("REF"), default=[],
        help="Add a reference argument to the current ref") 
    return parser.parse_args(args)


class RefArgumentError(Exception):
    def __init__(self, usage, *args) -> None:
        super().__init__(*args)
        self.usage = usage


class RefArgumentParser(argparse.ArgumentParser):
    def error(self, msg):
        raise BlockArgumentError(self.format_help(), msg)


def index_blocks(blocks):
    index = {}
    last_named = None
    for block in blocks:
        if not block["name"]:
            if last_named is None:
                raise ValueError("First block must have a name")
            if not block["args"].kontinue:
                raise ValueError(f"Block without name at line {block['beg']}. Use --continue to continue the previous block.")
            if block["lang"] != last_named["lang"]:
                raise ValueError(
                    f"Languages do not match between the block at line {last_named['beg']} and the one at line {block['beg']}")
            if block["indent"] != last_named["indent"]:
                raise ValueError(
                    f"Indentation does not match between the block at line {last_named['beg']} and the one at line {block['beg']}")
            index[last_named["name"]].append(block)
        else:
            index[block["name"]] = [block]
            last_named = block
    return index


def inject_args(dst_block, src_line, index, args):
    d = {}
    for i, arg in enumerate(args):
        match arg:
            case ("LIT", arg):
                d[str(i)] = [{
                    "name": str(i),
                    "beg": src_line["row"] - 1,
                    "end": src_line["row"] - 1,
                    "lang": dst_block["lang"],
                    "args": argparse.Namespace(
                        prefixes=[],
                        suffixes=[],
                        preludes=[],
                    ),
                    "lines": [{
                        "row": src_line["row"] - 1,
                        "txt": arg + "\n",
                    }],
                }]
            case ("REF", arg):
                d[str(i)] = index[arg]
            case _:
                raise ValueError(f"Unknown argument kind: {arg}")
    return {**index, **d}


def walk_blocks(src_block, index, filename, is_root=True, prev_indents=None):
    prev_indents = prev_indents or []
    src_block_args = src_block["args"]

    if src_block_args.preludes:
        for prelude in src_block_args.preludes:
            yield ("TXT", prelude + "\n")
        yield ("TXT", "\n")
    
    if is_root:
        for l in compose_warning_message(filename, src_block["lang"]):
            yield ("TXT", l)

    yield ("LOCATION", src_block["beg"] + 1)

    for prefix in src_block_args.prefixes:
        yield ("TXT", prefix + "\n")

    for src_line in src_block["lines"]:
        src_row = src_line["row"]
        if "name" in src_line: # Is a reference
            ref_args = src_line["args"]
            for dst_block in index[src_line["name"]]:
                if dst_block == src_block:
                    raise ValueError(f"[ line {src_row} ] detected self-reference in {filename}")
                for prefix in ref_args.prefixes:
                    yield ("TXT", prefix + "\n")
                yield ("REF", walk_blocks(dst_block, inject_args(dst_block, src_line, index, ref_args.args), filename,
                    False, [*prev_indents, src_line["indent"]]))
                for suffix in ref_args.suffixes:
                    yield ("TXT", suffix + "\n")
                yield ("LOCATION", src_row + 1)
        else: # Is a normal line
            yield ("INDENT", prev_indents)
            yield ("TXT", src_line["txt"])
    
    for suffix in src_block_args.suffixes:
        yield ("TXT", suffix + "\n")


PYTHON_MAP_FORMAT = "#line {file}:{line}"
C_MAP_FORMAT = '#line {line} "{file}"'
GO_MAP_FORMAT = "//line {file}:{line}"
LANG_LINE_FORMATS = {
    "python": PYTHON_MAP_FORMAT,
    "py": PYTHON_MAP_FORMAT,
    "c": C_MAP_FORMAT,
    "cpp": C_MAP_FORMAT,
    "go": GO_MAP_FORMAT,
}


def format(steps, filename, lang):
    for step in steps:
        match step:
            case ("LOCATION", line, *_):
                yield LANG_LINE_FORMATS[lang].format(file=filename, line=line)
                yield "\n"
            case ("INDENT", indent, *_):
                yield "".join(indent)
            case ("TXT", txt, *_):
                yield txt
            case ("REF", steps):
                yield from format(steps, filename, lang)
            case _:
                raise AssertionError(f"Unknown step: {step}")


PYTHON_COMMENT_FORMAT = "# {0}"
C_COMMENT_FORMAT = "// {0}"
LANG_COMMENT_FORMATS = {
    "python": PYTHON_COMMENT_FORMAT,
    "py": PYTHON_COMMENT_FORMAT,
    "c": C_COMMENT_FORMAT,
    "cpp": C_COMMENT_FORMAT,
    "go": C_COMMENT_FORMAT,
}


def compose_warning_message(input, lang):
    comment_format = LANG_COMMENT_FORMATS[lang]
    yield comment_format.format(f"Code generated from {input}; DO NOT EDIT.") + "\n"
    yield comment_format.format(f"Command used: {' '.join(sys.argv)}") + "\n"
    yield "\n"


################################################################################

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


################################################################################

# def flatten(steps):
#     for step in steps:
#         if step[0] == "REF":
#             yield from flatten(step[1])
#         else:
#             yield step

if __name__ == '__main__':
    with (open(sys.argv[1], "r", encoding="utf-8") as fin,
        open(sys.argv[2], "w", encoding="utf-8") as fout):
        index = index_blocks(parse_references(extract_blocks(label_lines(fin))))

        for target_block in index["main.py"]:
            steps = walk_blocks(target_block, index, sys.argv[1])

            for l in format(steps, sys.argv[1], target_block["lang"]):
                fout.write(l)
