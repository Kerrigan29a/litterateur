# Litterateur

###### Copyright
~~~ python
# Copyright (c) 2022 Javier Escalada Gómez  
# All rights reserved.
# License: BSD 3-Clause Clear License
~~~

###### Short description
~~~ text --prefix '"""' --suffix '"""'
Litterateur is a quick-and-dirty "literate programming" tool to extract code
from Markdown files.
~~~

###### Metadata
~~~ python
__author__ = "Javier Escalada Gómez"
__email__ = "kerrigan29a@gmail.com"
__version__ = "0.6.1"
__license__ = "BSD 3-Clause Clear License"
~~~

This tool reads the [ATX headings](https://spec.commonmark.org/0.30/#atx-headings) and a particular format of [fenced code blocks](https://spec.commonmark.org/0.30/#fenced-code-blocks). If a fenced code block immediately follows a heading, this block is considered a code block.

```markdown
###### Code block example 1
~~~ python [--POSIX-arg1 --POSIX-arg2 ... --POSIX-argN]
# ...
# python code
# ...
~~~
```

**WARNING**: To find these code blocks, the script uses regular expressions, which is not a very robust approach.

## Specification of ATX headings

As is described in the [CommonMark specification](https://spec.commonmark.org/0.30/#atx-headings):

> An ATX heading consists of a string of characters, parsed as inline content, between an opening sequence of 1–6 unescaped # characters and an optional closing sequence of any number of unescaped # characters. The opening sequence of # characters must be followed by spaces or tabs, or by the end of line. The optional closing sequence of #s must be preceded by spaces or tabs and may be followed by spaces or tabs only. The opening # character may be preceded by up to three spaces of indentation. The raw contents of the heading are stripped of leading and trailing space or tabs before being parsed as inline content. The heading level is equal to the number of # characters in the opening sequence.

###### Heading regex
~~~ python
r'^( {0,3})(#{1,6})(?:\n|\s+?(.*?)(?:\n|\s+?#+\s*?$))'
~~~
<!-- Source: https://github.com/miyuchina/mistletoe/blob/94022647cd9d80e242db5c93a6567e3155b468bc/mistletoe/block_token.py#L165 -->



## Specification of fenced code blocks

As is described in the [CommonMark specification](https://spec.commonmark.org/0.30/#fenced-code-blocks):

> A code fence is a sequence of at least three consecutive backtick characters (`) or tildes (~). (Tildes and backticks cannot be mixed.) A fenced code block begins with a code fence, preceded by up to three spaces of indentation.

###### Fence regex
~~~ python
r'^( {0,3})(`{3,}|~{3,})(.*)$'
~~~
<!-- Source: https://github.com/miyuchina/mistletoe/blob/94022647cd9d80e242db5c93a6567e3155b468bc/mistletoe/block_token.py#L412 -->

The line with the opening code fence may optionally contain some text following the code fence, this is called the [info string](https://spec.commonmark.org/0.30/#info-string). The first word of the info string is specifies the language of the fenced code block. The rest of them are used to specify the options. The syntax of this options follows the POSIX shell standard. This script uses [shlex](https://docs.python.org/3/library/shlex.html) to split the string and [argparse](https://docs.python.org/3/library/argparse.html) to parse them.

###### Parse block arguments
~~~ python
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
~~~

# Extracting code blocks

The first step to extract the code blocks is to label each line of the file with the following labels:

* `"HEADING"`: A line which is a heading.
* `"TEXT"`: A line which is not code.
* `"BEGIN"`: A line which is the beginning of a code block.
* `"CODE"`: A line which is code.
* `"END"`: A line which is the end of a code block.

###### Label Markdown lines
~~~ python
#<< Parse block arguments >>
~~~

This first line is [a reference](#parsing-references) to the [Parse block arguments](#parse-block-arguments) code block. In the final output script this reference will be replaced by the actual code.

~~~ python --continue
def label_lines(f):
    #<< Template usage example >>

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
~~~

Once we have labels we can use them to extract the code blocks. With each `"BEGIN"` line, we create a new block that is populated with the following `"CODE"` lines up to the next `"END"` line. The `"HEADING"` lines are used to name the **immediately** following blocks. 

###### Extract code blocks
~~~ python
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
~~~

# Parsing references

To connect all the code blocks, we need to parse the references. This is the regular expression used.

###### Reference regex
~~~ python
r'<<([^|>]+)\|?([^>]*)>>'
~~~

Depending on the programming language declared in the block, the reference regex may be slightly different, as the references are embedded in line comments.

###### Language specific reference patterns
~~~ python
(REF :=
    #<<Reference regex>>
)
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
~~~

###### Parse references
~~~ python
#<< Language specific reference patterns >>


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
~~~


# Templates

A template is just a normal code block that uses numeric references as placeholders.

###### Compile regex
~~~ python
(
#<< 0 >>
:= re.compile(
    #<< 1 >>
))
~~~

To populate the placeholders, you have to use `--lit-arg` to provide literals and `--ref-arg` to reference other code blocks.

###### Template usage example
~~~ python
#<< Compile regex | --lit-arg 'HEADING' --ref-arg 'Heading regex' >>
~~~

In this line `"HEADING"` is placed in `<< 0 >>` and the content of [Heading regex](#heading-regex) is placed in `<< 1 >>`.

~~~ python --continue
#<< Compile regex | --lit-arg 'FENCE'   --ref-arg 'Fence regex'   >>
~~~

Here, the arguments are `"FENCE"` and [Fence regex](#fence-regex) respectively.

# Indexing blocks

As references use the name of the code blocks, we need to index them by name.

###### Index code blocks
~~~ python
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
~~~

# Walking blocks

The last step to write the code is to walk the blocks following the references.

###### Walk code blocks
~~~ python
#<< Inject arguments >>


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


#<< Line directive formats >>


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
~~~

`LANG_LINE_FORMATS` is a dictionary that maps languages to the format of the their line directives.

###### Line directive formats
~~~ python
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
~~~

To handle the [templating mechanism](#templates), we need to inject the reference arguments into the code blocks.

###### Inject arguments
~~~ python
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
~~~

# DO NOT EDIT message

As this tool generates code files from Markdown files, it is important to warn the users of the code not to make modifications on the generated files but to use the original Markdown files.

This tool uses the standard [Go format](https://pkg.go.dev/cmd/go#hdr-Generate_Go_files_by_processing_source)
```regexp
^// Code generated .* DO NOT EDIT\.$
```

###### Compose the warning message
~~~ python
#<< Comment formats >>

def compose_warning_message(input, lang):
    comment_format = LANG_COMMENT_FORMATS[lang]
    yield comment_format.format(f"Code generated from {input}; DO NOT EDIT.") + "\n"
    yield comment_format.format(f"Command used: {' '.join(sys.argv)}") + "\n"
    yield "\n"
~~~

`LANG_COMMENT_FORMATS` is a dictionary that maps languages to the format of the their comment.

###### Comment formats
~~~ python
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


# Main code

###### Parse arguments
~~~ python
class ParseError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description=
#<< Short description >>
)
    parser.add_argument("input", metavar='FILE',
        help="Input Markdown file")
    parser.add_argument("selection", metavar='NAME[:NEW_NAME]', nargs='+',
        help="Select the following blocks to extract")
    parser.add_argument("-e", "--encoding", metavar='ENCODING', default="utf-8", 
        help="Encoding (default: %(default)s)")
    parser.add_argument("-o", "--overwrite", action='store_true',
        help="Overwrite output files (default: %(default)s)")
    parser.add_argument("-D", "--dump", action='store_true',
        help="Dump the internal state(default: %(default)s)")
    args = parser.parse_args()
    renames = {}
    for selection in args.selection or []:
        try:
            old, new = selection.split(":")
        except ValueError:
            old, new = selection, selection
        renames[old] = new
    del args.selection
    args.selections = renames
    return args
~~~

###### Run
~~~ python
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
        index = index_blocks(parse_references(extract_blocks(label_lines(f))))

    if args.dump:
        with open(args.input + ".json", "w", encoding=args.encoding) as f:
            json.dump({"version": __version__, "blocks": index}, f, indent=2,
                default=lambda o: o.__dict__)
    
    for filename in args.selections.keys():
        blocks = index[filename]
        filename = args.selections[filename]
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
            try:
                for block in blocks:
                    steps = walk_blocks(block, index, args.input)
                    for l in format(steps, args.input, block["lang"]):
                        f.write(l)
            except ValueError as e:
                perror(e)
                return 1
    return 0
~~~

# Programs skeleton

###### main.py
~~~ python --prelude '#!/usr/bin/env python3' --prelude '# -*- coding: utf-8 -*-'
#<< Copyright >>

#<< Short description >>

#<< Metadata >>

import re
import sys
import shlex
import argparse
import os.path
from setuptools.extern.packaging import version
import json
try:
    from custom_json_encoder import __version__ as cje_version, wrap_dump, wrap_dumps
    if not version.parse("0.3") <= version.parse(cje_version) < version.parse("0.4"):
        raise ValueError(f"custom_json_encoder version must be 0.3, but is {cje_version}")
    def indentation_policy(path, collection, indent, width):
        if len(collection) == 0:
            return False
        if len(path) == 0:
            return False
        if path[-1] in ["blocks", "args", "lines"]:
            return True
        return False
    json.dump = wrap_dump(indentation_policy, width=0)
    json.dumps = wrap_dumps(indentation_policy, width=0)
except ValueError as e:
    import warnings
    warnings.warn(str(e))
    warnings.warn("Disabling custom_json_encoder usage")
except ImportError:
    pass

#<< Label Markdown lines >>

#<< Extract code blocks >>

#<< Parse references >>

#<< Index code blocks >>

#<< Walk code blocks >>

#<< Compose the warning message >>

#<< Parse arguments >>
    
#<< Run >>

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

###### script.py
~~~ python --prelude "#!/usr/bin/env python3" --prelude "# -*- coding: utf-8 -*-"
#<< Copyright >>

from litterateur import main

if __name__ == "__main__":
    main()
~~~
