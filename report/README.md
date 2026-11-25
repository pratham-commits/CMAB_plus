# SIGCOMM '27 LaTeX template

This repository contains a minimal LaTeX template for submissions to
[ACM SIGCOMM 2027](https://conferences.sigcomm.org/sigcomm/2027/). It
is based on Shichao Yue's template for [SIGCOMM
'18](https://github.com/scyue/latex-sigcomm18), updated to the current
release of ACM's `acmart` class and pre-configured for the
double-blind submission format.

## Requirements

- A modern TeX distribution. We recommend [TeX
  Live](https://tug.org/texlive/) 2025 or later (MacTeX on macOS);
  Overleaf will also work if the project's TeX Live version is set to
  2025 or later.
- `latexmk`, which ships with TeX Live and MacTeX.
- `make` (optional; see below).

## Building

```sh
make          # builds paper.pdf
make clean    # removes all build products
```

The Makefile is a thin wrapper around `latexmk`, so you can also call
it directly: `latexmk -pdf paper` for a one-off build, or `latexmk
-pdf -pvc paper` to rebuild automatically on every save.

## Layout

| File | Purpose |
|---|---|
| `paper.tex` | main file: document class, submission settings, title and abstract, paper body |
| `reference.bib` | bibliography |
| `figures/` | figures; use PDF where possible and make sure fonts are embedded |
| `acmart.cls`, `ACM-Reference-Format.bst` | pinned copies of the ACM class and bibliography style |
| `Makefile` | build script, which calls `latexmk` |

## Submission Checklist

Fill in the placeholders in `paper.tex`;
- the `\title{...}` line, and 
- the `\author{Paper \# XXX...}` line

Keep in mind that submissions must have:
- At most 12 pages of text, including figures and tables; references
  and appendices do not count against the page limit.
- An abstract of no more than 200 words.
- No identifying names, affiliations, or acknowledgments, and no links
  to non-anonymous repositories; if necessary, refer to your own prior
  work in the third person.
- All fonts embedded, including in figures. 
- Legible figures, even when printed in grayscale.
- A final PDF that is no more than 15 MB in size.

We recommend also running the `banal` format checker on the final PDF;
it catches violations in font size, page numbers, column dimension,
etc.

## Camera-ready

We will provide updated camera-ready information for accepted papers.
