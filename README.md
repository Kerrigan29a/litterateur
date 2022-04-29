# Litterateur

~~~ python main.py prelude
"""
Quick-and-dirty "literate programming" tool to extract code from Markdown files

Copyright (c) 2022 Javier Escalada Gómez  
All rights reserved.
License: BSD 3-Clause Clear License
"""

__author__ = "Javier Escalada Gómez"
__email__ = "kerrigan29a@gmail.com"
__version__ = "0.3.0"
__license__ = "BSD 3-Clause Clear License"
~~~

This script extracts code from Markdown files following the [literate programming](https://www.johndcook.com/blog/2016/07/06/literate-programming-presenting-code-in-human-order/) approach.

It uses a particular format of fenced code blocks to mark the code to extract. The fenced code blocks must also specify the language (used also in Markdown), the file name and a short description of the code that is used to reference it.

```markdown
~~~ python dummy.py short_description
# ...
# python code
# ...
~~~
```

**WARNING**: To find these code blocks, we use the following regular expressions:

~~~ python main.py Code block patterns
FENCE = re.compile(r'( {0,3})(`{3,}|~{3,})(.*)')
OPT = re.compile(r' *(\S+)')
~~~

so, take in mind that this is a very quick and dirty implementation.

# Extracting code blocks

The first step is to extract the code blocks from the Markdown file.

The following function labels each line using the following categories:

* `"TEXT"`: the line is not a code block
* `"BEGIN"`: the line is the beginning of a code block.
* `"CODE"`: the line is a code line.
* `"END"`: the line is the end of a code block.

~~~ python main.py label_markdown_lines
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
~~~

Once we have the labels, we can extract them. With each `"BEGIN"` line, we create a new block that is populated with the following `"CODE"` lines up to the next `"END"` line. As this script makes the *tangling* process we ignore the `"TEXT"` lines. But this function can also be used to extract the `"TEXT"` lines in the *weaving* process.

~~~ python main.py extract_blocks
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
~~~

# Parsing references

To be able to walk properly the code blocks, so we can emit the final source code, we need to parse the references.

~~~ python main.py parse_references
def parse_references(blocks):
    for block in blocks:
        ref_pattern = LANG_REF_PATTERNS[block["lang"]]
        for i in range(len(block["txt"])):
            linenum, line = block["txt"][i]
            if m := ref_pattern.match(line):
                indent, name = m.groups()
                block["txt"][i] = (linenum, (indent, name.strip()))
        yield block
~~~

`LANG_REF_PATTERNS` is a dictionary that maps languages to regular expressions that match references to other code blocks.

~~~ python main.py reference_patterns
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
~~~


# Indexing code blocks

We also need to index the code blocks so that we can find them by their description.

~~~ python main.py index_blocks
def index_blocks(blocks):
    index = {}
    for block in blocks:
        index[(block["filename"], block["desc"])] = block
    return index
~~~

# Walking blocks

The last step to emit the code is to walk the blocks following the links.

~~~ python main.py walk_blocks
def walk_blocks(src_block, dst_blocks, input_filename):

    # <<< line_directive >>>

    src_lang = src_block["lang"]
    src_filename = src_block["filename"]

    yield line_directive(src_block["beg"])
    for linenum, src_line in src_block["txt"]:
        if isinstance(src_line, tuple): 
            dst_indent, dst_name = src_line
            dst_block = dst_blocks[(src_filename, dst_name.strip())]
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
~~~

# Warning message

As this tool generates code files from Markdown files, it is important to warn the users of the code not to make modifications on the generated files but to use the original Markdown files.

This tool uses the regular expression:
```regexp
^// Code generated .* DO NOT EDIT\.$
```

from the [Go command documentation](https://pkg.go.dev/cmd/go#hdr-Generate_Go_files_by_processing_source).

~~~ python main.py compose_warning_message
def compose_warning_message(input, lang):
    comment_format = LANG_COMMENT_FORMATS[lang]
    yield comment_format.format(f"Code generated from {input}; DO NOT EDIT.") + "\n"
    yield comment_format.format(f"Command used: {' '.join(sys.argv)}") + "\n"
~~~

`LANG_COMMENT_FORMATS` is a dictionary that maps languages to the format of the their comment.

~~~ python main.py comment_formats
PYTHON_COMMENT_FORMAT = "# {0}"
C_COMMENT_FORMAT = "// {0}"
LANG_COMMENT_FORMATS = {
    "python": PYTHON_COMMENT_FORMAT,
    "py": PYTHON_COMMENT_FORMAT,
    "c": C_COMMENT_FORMAT,
    "cpp": C_COMMENT_FORMAT,
    "go": C_COMMENT_FORMAT,
}
~~~

# Mapping the generated code with the original Markdown file

~~~ python main.py line_directive
line_format = LANG_LINE_FORMATS[src_block["lang"]]
def line_directive(line):
    return line_format.format(file=input_filename, line=line+1) + "\n"
~~~

`LANG_LINE_FORMATS` is a dictionary that maps languages to the format of the their line directives.

~~~ python main.py line_formats
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
~~~


# Main code

This script is called with the following arguments:

~~~ python main.py parse_arguments
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
~~~

The run function:

~~~ python main.py run
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

def run(args):
    pinfo(f"Reading {CDIM}{args.input}{CEND}")
    with open(args.input, encoding=args.encoding) as f:
        blocks = index_blocks(parse_references(extract_blocks(label_lines(f))))
    if args.dump:
        with open(args.input + ".json", "w", encoding=args.encoding) as f:
            tmp = {":".join(k): v for k, v in blocks.items()}
            kwargs = {"cls": CustomJSONEncoder, "width": 80} if CustomJSONEncoder else {}
            json.dump(tmp, f, indent=2, **kwargs)
    for (filename, desc), block in blocks.items():
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
~~~

<!--
~~~ python main.py main
# -*- coding: utf-8 -*-
# <<< prelude >>>

import re
import sys
import argparse
import os.path
import json
try:
    from custom_json_encoder import CustomJSONEncoder
except ImportError:
    CustomJSONEncoder = None

# <<< Code block patterns >>>

# <<< reference_patterns >>>

# <<< comment_formats >>>

# <<< line_formats >>>

# <<< label_markdown_lines >>>

# <<< extract_blocks >>>

# <<< parse_references >>>

# <<< index_blocks >>>

# <<< walk_blocks >>>

# <<< compose_warning_message >>>

# <<< parse_arguments >>>
    
# <<< run >>>

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
~~~

~~~ python script.py main
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2022 Javier Escalada Gómez  
All rights reserved.
License: BSD 3-Clause Clear License
"""

from litterateur import main

if __name__ == "__main__":
    main()
~~~
-->
