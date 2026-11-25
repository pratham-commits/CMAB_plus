#!/usr/bin/env python3
"""Convert the ground-up guide (index plus guide/*.md) to one LaTeX file and build it with tectonic.

Handles the markdown subset the guide uses: ATX headings, paragraphs, bullet and
numbered lists, pipe tables, fenced code blocks, inline code, links, images and
horizontal rules.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "guide"
BUILD = ROOT / "build"
PARTS = [ROOT / "GROUND_UP_GUIDE.md"] + sorted(GUIDE.glob("0*.md"))

TEXT_SYMBOLS = {
    "T̂": r"$\hat{T}$",
    "√": r"$\surd$",
    "≈": r"$\approx$",
    "≤": r"$\le$",
    "≥": r"$\ge$",
    "−": r"$-$",
    "×": r"$\times$",
    "±": r"$\pm$",
    "…": r"\ldots{}",
    "·": r"$\cdot$",
}


def esc(s):
    out = []
    for ch in s:
        if ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "\\":
            out.append(r"\textbackslash{}")
        elif ch == "~":
            out.append(r"\textasciitilde{}")
        elif ch == "^":
            out.append(r"\textasciicircum{}")
        elif ch == "|":
            out.append(r"\textbar{}")
        elif ch == "<":
            out.append(r"\textless{}")
        elif ch == ">":
            out.append(r"\textgreater{}")
        else:
            out.append(ch)
    s = "".join(out)
    for k, v in TEXT_SYMBOLS.items():
        s = s.replace(k, v)
    return s


def code_inline(s):
    s = esc(s)
    s = s.replace("/", "/\\allowbreak{}").replace("\\_", "\\_\\allowbreak{}").replace("-", "-\\allowbreak{}")
    return r"\texttt{" + s + "}"


INLINE = re.compile(r"`([^`]+)`|!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*([^*\s][^*]*)\*")


def inline(s):
    out, pos = [], 0
    for m in INLINE.finditer(s):
        out.append(esc(s[pos:m.start()]))
        if m.group(1) is not None:
            out.append(code_inline(m.group(1)))
        elif m.group(3) is not None:
            out.append(esc(m.group(2)))
        elif m.group(4) is not None:
            text, url = m.group(4), m.group(5)
            if url.startswith("http"):
                out.append(r"\href{" + url.replace("%", r"\%").replace("#", r"\#") + "}{" + inline(text) + "}")
            else:
                out.append(inline(text))
        else:
            out.append(r"\emph{" + esc(m.group(6)) + "}")
        pos = m.end()
    out.append(esc(s[pos:]))
    return "".join(out)


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], cells[2:]
    n = len(header)
    lens = [max(len(r[i]) if i < len(r) else 0 for r in [header] + body) for i in range(n)]
    lens = [min(max(l, 4), 60) for l in lens]
    total = sum(lens)
    size = r"\small" if n <= 4 else (r"\footnotesize" if n <= 6 else r"\scriptsize")
    usable = 0.98 - 0.02 * n
    spec = "".join(r">{\raggedright\arraybackslash}p{%.3f\linewidth}" % (usable * l / total) for l in lens)
    out = ["{" + size, r"\setlength{\tabcolsep}{3pt}", r"\begin{longtable}{" + spec + "}", r"\toprule"]
    out.append(" & ".join(r"\textbf{" + inline(h) + "}" for h in header) + r" \\")
    out += [r"\midrule", r"\endhead"]
    for r in body:
        r = (r + [""] * n)[:n]
        out.append(" & ".join(inline(c) for c in r) + r" \\")
    out += [r"\bottomrule", r"\end{longtable}", "}"]
    return "\n".join(out)


def convert(md, part_dir):
    lines = md.split("\n")
    out, i, para = [], 0, []

    def flush():
        if para:
            out.append(inline(" ".join(para)) + "\n")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            width = max((len(c) for c in code), default=0)
            size = "small" if width <= 80 else ("footnotesize" if width <= 92 else "scriptsize")
            out.append("\\begin{%s}\\begin{verbatim}\n" % size + "\n".join(code) + "\n\\end{verbatim}\\end{%s}" % size)
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            flush()
            level = len(m.group(1))
            cmd = {1: "section", 2: "subsection", 3: "subsubsection", 4: "paragraph"}[level]
            out.append("\\%s*{%s}" % (cmd, inline(m.group(2))))
            if level == 1:
                out.append(r"\addcontentsline{toc}{section}{" + inline(m.group(2)) + "}")
            elif level == 2:
                out.append(r"\addcontentsline{toc}{subsection}{" + inline(m.group(2)) + "}")
            if level == 4:
                out.append(r"\mbox{}\\")
            i += 1
            continue
        img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if img:
            flush()
            path = (part_dir / img.group(2)).resolve()
            out.append(r"\begin{center}\includegraphics[width=0.95\linewidth]{" + str(path) + r"}\\[2pt]\small " + esc(img.group(1)) + r"\end{center}")
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(table(rows))
            continue
        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", line)
        if lm:
            flush()
            env = "itemize" if lm.group(2) in "-*" else "enumerate"
            items = []
            while i < len(lines):
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", lines[i])
                if mm:
                    items.append(mm.group(3))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            out.append("\\begin{%s}\n" % env + "\n".join(r"\item " + inline(t) for t in items) + "\n\\end{%s}" % env)
            continue
        if re.match(r"^-{3,}\s*$", line):
            flush()
            out.append(r"\medskip\noindent\rule{\linewidth}{0.4pt}\medskip")
            i += 1
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        if re.match(r"^\[Back to the index\]", line):
            i += 1
            continue
        para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage{fontspec}
\setmainfont{Georgia}
\setmonofont[Scale=0.85]{Menlo}
\usepackage{graphicx,longtable,booktabs,array,xcolor}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\setcounter{tocdepth}{2}
\sloppy
\begin{document}
\tableofcontents
\clearpage
"""


def main():
    BUILD.mkdir(exist_ok=True)
    body = []
    for p in PARTS:
        body.append(convert(p.read_text(), p.parent))
        body.append(r"\clearpage")
    tex = BUILD / "GROUND_UP_GUIDE.tex"
    tex.write_text(PREAMBLE + "\n".join(body) + "\n\\end{document}\n")
    r = subprocess.run(["tectonic", "--keep-logs", "--outdir", str(BUILD), str(tex)])
    if r.returncode != 0:
        sys.exit(r.returncode)
    (BUILD / "GROUND_UP_GUIDE.pdf").replace(ROOT / "GROUND_UP_GUIDE.pdf")
    print("wrote", ROOT / "GROUND_UP_GUIDE.pdf")


if __name__ == "__main__":
    main()
