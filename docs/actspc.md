# ACTSPC Action Source Formatter

`actspc` is a Linux-side, in-place formatter for Action source. It accepts one
or more filenames or filespecs:

```sh
actspc hello.act
actspc hello
actspc *.act
actspc '*.act'
actspc 'SRC/*.act' 'LIB/*.act'
```

An omitted extension on a literal name implies `.act`. Shell-expanded file
lists and quoted wildcards both work. When ACTSPC expands a filespec itself,
the `.act`/`.ACT` extension is matched case-insensitively, which lets
`actspc '*.act'` format the uppercase files in the exported `PLAYGROUND/`.
Duplicate matches are processed once in deterministic path order.

ACTSPC resolves every filespec and reads/formats every matched source before it
replaces the first file. A missing filespec therefore cannot leave the earlier
matches half-formatted. Each changed file is then written to a temporary file
in the same directory and atomically renamed over the source with its original
permissions. Already canonical files are reported as `UNCHANGED` and are not
rewritten.

The canonical layout is:

- four spaces for each routine, conditional, or loop body;
- one continuation level for multiline declarations, calls, and bracketed
  data;
- `ELSEIF`, `ELSE`, `FI`, `OD`, and routine terminators aligned with their
  opening construct;
- compact symbolic operators, commas, and parentheses, with one space between
  language words;
- LF line endings, indentation made from spaces, no trailing whitespace, at
  most one adjacent blank line, and one final newline;
- unchanged string contents and comment text; and
- ASMBLOCK instructions one level below the ASMBLOCK line, with local labels
  and the closing bracket aligned to the ASMBLOCK line.

Formatting is idempotent: running ACTSPC again produces `UNCHANGED`. It is a
formatter, not a compiler or repair tool; malformed Action block structure is
indented on a best-effort basis and should still be checked with `actc`.

ACTEDIT invokes the same engine on F6. That operation formats the current
unsaved buffer, marks it dirty when text changes, and leaves the save decision
to `Ctrl-S`.
