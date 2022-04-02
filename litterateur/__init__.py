# Code generated from README.md; DO NOT EDIT.
# Command used: litterateur.py README.md


#line README.md:271
import re
import sys
import argparse
import os.path

#line README.md:4
__version__ = '0.0.1'
#line README.md:277

#line README.md:22
FENCE = re.compile(r'( {0,3})(`{3,}|~{3,})(.*)')
OPT = re.compile(r' *(\S+)')
#line README.md:279

#line README.md:137
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
#line README.md:281

#line README.md:170
PYTHON_COMMENT_FORMAT = "# {0}"
C_COMMENT_FORMAT = "// {0}"
LANG_COMMENT_FORMATS = {
    "python": PYTHON_COMMENT_FORMAT,
    "py": PYTHON_COMMENT_FORMAT,
    "c": C_COMMENT_FORMAT,
    "cpp": C_COMMENT_FORMAT,
    "go": C_COMMENT_FORMAT,
}
#line README.md:283

#line README.md:192
PYTHON_MAP_FORMAT = "#line {file}:{line}"
C_MAP_FORMAT = "#line {line} {file}"
GO_MAP_FORMAT = "//line {file}:{line}"
LANG_MAP_FORMATS = {
    "python": PYTHON_MAP_FORMAT,
    "py": PYTHON_MAP_FORMAT,
    "c": C_MAP_FORMAT,
    "cpp": C_MAP_FORMAT,
    "go": GO_MAP_FORMAT,
}
#line README.md:285

#line README.md:40
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
#line README.md:287

#line README.md:70
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
#line README.md:289

#line README.md:99
def index_blocks(blocks):
    index = {}
    for block in blocks:
        index[(block["filename"], block["desc"])] = block
    return index
#line README.md:291

#line README.md:111
def walk_blocks(src_block, dst_blocks, input_filename):

    #line README.md:184
    map_format = LANG_MAP_FORMATS[src_block["lang"]]
    def map(line):
        return map_format.format(file=input_filename, line=line+1) + "\n"
    #line README.md:114

    src_lang = src_block["lang"]
    src_filename = src_block["filename"]
    ref_pattern = LANG_REF_PATTERNS[src_lang]

    yield map(src_block["beg"])
    for linenum, src_line in src_block["txt"]:
        if m := ref_pattern.match(src_line):
            dst_indent, dst_name = m.groups()
            dst_block = dst_blocks[(src_filename, dst_name.strip())]
            dst_lang = dst_block["lang"]
            if src_lang != dst_lang:
                raise ValueError(f"language mismatch: {src_lang} != {dst_lang}")
            for l in walk_blocks(dst_block, dst_blocks, input_filename):
                yield dst_indent + l
            yield dst_indent + map(linenum)
        else:
            yield src_line
#line README.md:293

#line README.md:161
def compose_warning_message(input, lang):
    comment_format = LANG_COMMENT_FORMATS[lang]
    yield comment_format.format(f"Code generated from {input}; DO NOT EDIT.") + "\n"
    yield comment_format.format(f"Command used: {' '.join(sys.argv)}") + "\n"
#line README.md:295

#line README.md:210
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
#line README.md:297
    
#line README.md:239
def run(args):
        print("Reading", args.input)
        with open(args.input, encoding=args.encoding) as f:
            blocks = index_blocks(extract_blocks(label_lines(f)))
        for (filename, desc), block in blocks.items():
            if desc.lower() == "main":
                filename = args.rename.get(filename, filename)
                if os.path.exists(filename):
                    if not args.overwrite:
                        print(f"ERROR: {filename} already exists.")
                        print("Skipping", filename)
                        return 1
                    else:
                        print(f"WARNING: {filename} already exists.")
                        print("Overwriting", filename)
                else:
                    print("Writing", filename)
                with open(filename, "w", encoding=args.encoding) as f:
                    for l in compose_warning_message(args.input, block["lang"]):
                        f.write(l)
                    f.write("\n\n")
                    try:
                        for l in walk_blocks(block, blocks, args.input):
                            f.write(l)
                    except ValueError as e:
                        print(f"ERROR: {e}")
                        return 1
        return 0
#line README.md:299

def main():
    try:
        exit(run(parse_args()))
    except ParseError as e:
        print(f"ERROR: {e}")
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
    exit(1)

if __name__ == "__main__":
    main()
