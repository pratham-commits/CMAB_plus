#!/usr/bin/env python3
"""Build final-review.pptx (16:9) with speaker notes.

Numbers come from report/paper.tex. Figures: report/figures converted to PNG in
assets/, fig-*.png from make_slide_figures.py, and demo-ui screenshots.
Run: python make_slide_figures.py && python build_deck.py  (needs python-pptx, matplotlib)
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt
from PIL import Image

from notes import SLIDES, notes_text

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

NAVY = RGBColor(0x1F, 0x2A, 0x44)
GREY = RGBColor(0x5F, 0x66, 0x73)
LIGHT = RGBColor(0xF2, 0xF4, 0xF7)
RULE = RGBColor(0xD0, 0xD5, 0xDD)
ORANGE = RGBColor(0xD5, 0x5E, 0x00)  # old CMAB in every figure
BLUE = RGBColor(0x00, 0x72, 0xB2)    # CMAB+ in every figure
GREEN = RGBColor(0x00, 0x9E, 0x73)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]
slide_no = 0


def tb(slide, x, y, w, h, paras, size=20, color=NAVY, bold=False,
       align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=6):
    """Text box. paras: list of str or (str, dict) with keys size/color/bold."""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, p in enumerate(paras):
        text, opt = (p, {}) if isinstance(p, str) else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = opt.get("align", align)
        para.space_after = Pt(opt.get("spacing", spacing))
        run = para.add_run()
        run.text = text
        f = run.font
        f.name = FONT
        f.size = Pt(opt.get("size", size))
        f.bold = opt.get("bold", bold)
        f.color.rgb = opt.get("color", color)
    return box


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def box_text(shape, text, size=16, color=WHITE, bold=True):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = line
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color


def picture(slide, path, x, y, w, h):
    """Fit image inside (x, y, w, h), centred, keeping aspect ratio."""
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    pw, ph = int(iw * scale), int(ih * scale)
    return slide.shapes.add_picture(str(path), x + (w - pw) // 2,
                                    y + (h - ph) // 2, pw, ph)


def new_slide(title, speaker, subtitle=None):
    global slide_no
    slide_no += 1
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, Inches(0.18), SH, NAVY)
    tb(s, Inches(0.55), Inches(0.35), Inches(12.3), Inches(0.9),
       [title], size=32, bold=True, anchor=MSO_ANCHOR.TOP)
    if subtitle:
        tb(s, Inches(0.55), Inches(1.15), Inches(11.5), Inches(0.5),
           [subtitle], size=18, color=GREY)
    ln = s.shapes.add_connector(1, Inches(0.55), Inches(7.0), SW - Inches(0.5), Inches(7.0))
    ln.line.color.rgb = RULE
    ln.line.width = Pt(0.75)
    tb(s, Inches(0.55), Inches(7.03), Inches(9), Inches(0.35),
       ["CS G525 Advanced Computer Networks · Track A7 · Final review"],
       size=11, color=GREY)
    tb(s, Inches(8.5), Inches(7.03), Inches(3.2), Inches(0.35),
       [f"Speaker: {speaker}"], size=11, color=GREY, align=PP_ALIGN.RIGHT)
    tb(s, SW - Inches(1.5), Inches(7.03), Inches(1.0), Inches(0.35),
       [str(slide_no)], size=11, color=GREY, align=PP_ALIGN.RIGHT)
    return s


def table(slide, rows, x, y, w, h, widths, size, color_fn=None, align_fn=None):
    t = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, h).table
    for j, wdt in enumerate(widths):
        t.columns[j].width = wdt
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (LIGHT if i % 2 else WHITE)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = c.margin_right = Inches(0.08)
            p = c.text_frame.paragraphs[0]
            p.alignment = align_fn(i, j) if align_fn else PP_ALIGN.LEFT
            r = p.add_run()
            r.text = val
            f = r.font
            f.name, f.size, f.bold = FONT, Pt(size), i == 0
            f.color.rgb = WHITE if i == 0 else NAVY
            if i and color_fn:
                color_fn(i, j, val, f)
    return t


def caption(slide, x, y, w, text):
    tb(slide, x, y, w, Inches(0.5), [text], size=12, color=GREY)


def result_slide(title, speaker, fig, key, cap):
    """Full-width figure, one bold line of key numbers, then a source caption."""
    s = new_slide(title, speaker)
    picture(s, ASSETS / fig, Inches(0.55), Inches(1.2), Inches(12.25), Inches(4.95))
    tb(s, Inches(0.6), Inches(6.18), Inches(12.2), Inches(0.45), [key], size=17, bold=True)
    tb(s, Inches(0.6), Inches(6.6), Inches(12.2), Inches(0.35), [cap], size=12, color=GREY)
    return s


def card(slide, x, y, w, h, head, body, accent=NAVY, body_size=17):
    rect(slide, x, y, w, h, LIGHT)
    rect(slide, x, y, Inches(0.08), h, accent)
    tb(slide, x + Inches(0.25), y + Inches(0.15), w - Inches(0.4), Inches(0.5),
       [head], size=20, bold=True, color=accent)
    tb(slide, x + Inches(0.25), y + Inches(0.7), w - Inches(0.4), h - Inches(0.8),
       body, size=body_size, color=NAVY)


def big_number(slide, x, y, w, value, label, color):
    tb(slide, x, y, w, Inches(1.1), [value], size=54, bold=True, color=color,
       align=PP_ALIGN.CENTER)
    tb(slide, x, y + Inches(1.1), w, Inches(0.8), [label], size=17, color=GREY,
       align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------- 1. Title
slide_no += 1
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, SH, NAVY)
rect(s, Inches(0.8), Inches(1.55), Inches(1.2), Inches(0.08), ORANGE)
tb(s, Inches(0.8), Inches(1.8), Inches(11.8), Inches(1.9),
   ["Repairing forced-rung collapse in contextual-bandit live streaming over Starlink-like links"],
   size=38, bold=True, color=WHITE)
tb(s, Inches(0.8), Inches(3.75), Inches(11.5), Inches(0.6),
   ["CS G525 Advanced Computer Networks · Track A7 · Final review"],
   size=22, color=RGBColor(0xC9, 0xD3, 0xE3))
tb(s, Inches(0.8), Inches(4.6), Inches(11.5), Inches(2.4),
   ["Pratham Shah (2026H1030063P)", "Vidhu Kant Sharma (2026H1030053P)",
    ("Ved Pahune (2026H1030056P)", {"spacing": 18}),
    ("Tutor: Dr. Yash Sinha  ·  BITS Pilani", {"color": RGBColor(0xC9, 0xD3, 0xE3)})],
   size=19, color=WHITE, spacing=4)

# ---------------------------------------------------------------- 2. Problem
s = new_slide("Starlink reschedules satellites every 15 s", "Ved")
# handover clock diagram
x0, y0, wbar = Inches(0.9), Inches(2.3), Inches(11.5)
rect(s, x0, y0, wbar, Inches(0.5), LIGHT, line=RULE)
for sec in (12, 27, 42, 57):
    hx = x0 + int(wbar * sec / 60)
    r = rect(s, hx, y0 - Inches(0.1), int(wbar / 60), Inches(0.7), ORANGE)
    tb(s, hx - Inches(0.45), y0 - Inches(0.6), Inches(1.0), Inches(0.4),
       [f":{sec}"], size=18, bold=True, color=ORANGE, align=PP_ALIGN.CENTER)
for sec in (0, 15, 30, 45, 60):
    tx = x0 + int(wbar * sec / 60)
    tb(s, tx - Inches(0.4), y0 + Inches(0.6), Inches(0.8), Inches(0.4),
       [f"{sec} s"], size=14, color=GREY, align=PP_ALIGN.CENTER)
tb(s, x0, y0 + Inches(1.0), wbar, Inches(0.4),
   ["One wall-clock minute. Orange: handover second, RTT and loss rise."],
   size=14, color=GREY, align=PP_ALIGN.CENTER)
card(s, Inches(0.9), Inches(4.0), Inches(5.5), Inches(2.7), "Low-latency live DASH",
     ["3 s target behind the live edge", "Buffer holds 1–2 segments of 2 s",
      "A slow download becomes a stall"], accent=NAVY)
card(s, Inches(6.9), Inches(4.0), Inches(5.5), Inches(2.7), "CMAB (Zhao & Pan, MMSys '24)",
     ["LinTS contextual bandit, one arm per rung", "Ladder: 300 … 6000 kbps (8 rungs)",
      "History reset at every 15 s slot"], accent=BLUE)

# ---------------------------------------------------------------- 3. Review I
s = new_slide("Review I: we reproduced the paper's emulation", "Ved")
card(s, Inches(0.9), Inches(1.7), Inches(5.6), Inches(4.9), "Setup",
     ["160 sessions × 300 s, TCP CUBIC", "4 ABRs × 4 targets (3–6 s) × 10 rounds",
      "Clock shaper: 100 Mbit/s, 40 ms, 0.1% loss",
      "Handover second: 50 Mbit/s, 100 ms, 1% loss"], accent=NAVY, body_size=19)
big_number(s, Inches(7.0), Inches(1.8), Inches(5.4), "3.19 s", "CMAB live latency at a 3 s target, 0% rebuffer", BLUE)
rect(s, Inches(7.0), Inches(4.3), Inches(5.4), Inches(2.3), LIGHT)
tb(s, Inches(7.25), Inches(4.45), Inches(5.0), Inches(2.1),
   [("Not reproduced", {"bold": True, "color": ORANGE, "size": 20}),
    "Paper: every ABR misses 3 s by ≥ 1.5 s.",
    "Ours: worst miss 0.19 s."], size=19)

# ---------------------------------------------------------------- 4. First BBR run
s = new_slide("Review II: the first BBR run looked like a failure", "Ved", subtitle="CMAB at a 3 s target, first BBR matrix (dataset D2)")
big_number(s, Inches(0.9), Inches(2.0), Inches(3.8), "7.19 s", "live latency", ORANGE)
big_number(s, Inches(4.75), Inches(2.0), Inches(3.8), "28.32%", "rebuffer ratio", ORANGE)
big_number(s, Inches(8.6), Inches(2.0), Inches(3.8), "5795", "kbps requested", ORANGE)
rect(s, Inches(0.9), Inches(4.5), Inches(11.5), Inches(2.1), LIGHT)
tb(s, Inches(1.2), Inches(4.65), Inches(11.0), Inches(1.9),
   [("Check before blaming BBR", {"bold": True, "size": 20}),
    "Same stack under CUBIC: CMAB also failed (about 16.6 s, 86% rebuffer).",
    "A CUBIC failure is not a BBR effect, so we audited the testbed."], size=19)

# ---------------------------------------------------------------- 5. Root causes
s = new_slide("Two testbed faults explained the first run", "Ved")
card(s, Inches(0.9), Inches(1.7), Inches(5.6), Inches(3.4), "1. Wrong shaper",
     ["Run used SHAPER=trace: ISL trace, median RTT ≈ 130 ms, 100% loss at handover rows",
      "Review I used the clock shaper"], accent=ORANGE, body_size=18)
card(s, Inches(6.85), Inches(1.7), Inches(5.6), Inches(3.4), "2. tc restart bug",
     ["Docker restart keeps old qdiscs", "Trace init only added classes, so it crashed",
      "Link could stay at 100% loss"], accent=ORANGE, body_size=18)
rect(s, Inches(0.9), Inches(5.35), Inches(11.55), Inches(1.3), LIGHT)
tb(s, Inches(1.2), Inches(5.5), Inches(11.0), Inches(1.1),
   [("Fix", {"bold": True, "color": GREEN, "size": 20}),
    "Rebuild the HTB root on init · check shaper mode in the container · rerun 160 sessions on the clock shaper"],
   size=18)

# ---------------------------------------------------------------- 6. Datasets
s = new_slide("On the clock shaper, BBR changes little", "Ved")
picture(s, ASSETS / "review2-cmab.png", Inches(0.6), Inches(1.5), Inches(7.4), Inches(4.4))
caption(s, Inches(0.7), Inches(5.95), Inches(7.3),
        "CMAB, mean of 10 sessions, 95% t intervals. Source: report Fig. 1.")
rows = [("", "Latency", "Rebuffer", "kbps"),
        ("D1 CUBIC, clock", "3.19 s", "0%", "4955"),
        ("D3 BBR, clock", "3.29 s", "0%", "5223"),
        ("D2 BBR, trace", "7.19 s", "28.32%", "5795")]

def _d2_orange(i, j, val, f):
    if i == 3:
        f.color.rgb = ORANGE


table(s, rows, Inches(8.15), Inches(1.7), Inches(4.75), Inches(2.0),
      [Inches(1.75), Inches(0.95), Inches(1.2), Inches(0.85)], 14, _d2_orange,
      lambda i, j: PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT)
tb(s, Inches(8.25), Inches(3.85), Inches(4.6), Inches(0.4),
   ["CMAB at a 3 s target"], size=13, color=GREY)
rect(s, Inches(8.25), Inches(4.45), Inches(4.6), Inches(2.2), LIGHT)
tb(s, Inches(8.45), Inches(4.55), Inches(4.3), Inches(2.0),
   [("Lesson", {"bold": True, "size": 20}),
    "Separate testbed faults from transport effects. D2 supports no BBR claim."],
   size=18)

# ---------------------------------------------------------------- 6b. Review II, all ABRs
result_slide("On D2, only CMAB kept requesting ~5800 kbps", "Ved",
             "fig-review2-abrs.png",
             "D2 at 3 s: CMAB 28.32% rebuffer at 5795 kbps · Dynamic 1.10% at 619 kbps · L2A-LL 0.59% at 359 kbps",
             "All four ABRs at a 3 s target, mean of 10 sessions, 95% t intervals. Data: report/results/review12-aggregate.csv.")

# ---------------------------------------------------------------- 7. Forced-rung collapse
s = new_slide("Diagnosis: forced-rung collapse", "Ved")
tb(s, Inches(0.7), Inches(1.4), Inches(12), Inches(0.5),
   ["One 15 s slot after a handover, 2 s segments, on a 4 Mbit/s link"], size=18, color=GREY)
lx, bx, bw, gap = Inches(0.7), Inches(2.6), Inches(1.12), Inches(0.08)
for row, (label, color, vals) in enumerate([
        ("old CMAB", ORANGE, ["6000"] * 7 + ["LinTS"]),
        ("CMAB+", BLUE, ["1500"] * 7 + ["LinTS\n≤ T̂"])]):
    y = Inches(2.55) + row * Inches(1.25)
    tb(s, lx, y + Inches(0.2), Inches(1.9), Inches(0.6), [label], size=20, bold=True, color=color)
    for k, v in enumerate(vals):
        fill = color if k < 7 else GREY
        b = rect(s, bx + k * (bw + gap), y, bw, Inches(0.95), fill)
        box_text(b, v, size=17 if k < 7 else 14)
br_w = 7 * bw + 6 * gap
tb(s, bx, Inches(2.0), br_w, Inches(0.45),
   ["first |A|−1 = 7 decisions: LinTS is skipped"], size=15, color=GREY, align=PP_ALIGN.CENTER)
ln = s.shapes.add_connector(1, bx, Inches(2.45), bx + br_w, Inches(2.45))
ln.line.color.rgb = GREY
ln.line.width = Pt(1.5)
tb(s, Inches(0.7), Inches(4.95), Inches(12), Inches(0.5),
   ["old CMAB: top rung at STRONG priority, no throughput check.  CMAB+: highest rung ≤ measured throughput T̂."],
   size=15, color=GREY)
rect(s, Inches(0.7), Inches(5.5), Inches(11.9), Inches(1.2), LIGHT)
tb(s, Inches(1.0), Inches(5.6), Inches(11.4), Inches(1.0),
   ["6000 kbps × 2 s = 12 Mbit  →  ≥ 3 s to fetch at 4 Mbit/s  →  buffer drains each forced decision"],
   size=18, bold=True, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 8. Timeline evidence
s = new_slide("On 4 Mbit/s, old CMAB never leaves 6000 kbps", "Vidhu")
picture(s, ASSETS / "timeline-4mbit.png", Inches(0.6), Inches(1.35), Inches(8.6), Inches(5.3))
tb(s, Inches(9.45), Inches(1.7), Inches(3.5), Inches(4.8),
   [("Top: requested bitrate", {"bold": True}),
    ("old CMAB stays at 6000 kbps, above the 4 Mbit/s link", {"spacing": 18}),
    ("Bottom: buffer", {"bold": True}),
    "old CMAB sits at the 0.05 s floor; CMAB+ stays ≈ 0.5–2.5 s"],
   size=17)
caption(s, Inches(0.7), Inches(6.6), Inches(8.5),
        "One session per player, CUBIC, 3 s target, round 0. Source: report Fig. 2.")

# ---------------------------------------------------------------- 9. CMAB+
s = new_slide("CMAB+: same LinTS bandit, five rules around it", "Vidhu")
card(s, Inches(0.7), Inches(1.5), Inches(3.6), Inches(5.15), "Unchanged",
     ["LinTS learner", "Context vector", "QoE reward", "15 s slot reset", "Catch-up policy"],
     accent=GREY, body_size=19)
rules = [("1", "Feasible probe", "first 7 decisions request i★ = highest rung ≤ T̂"),
         ("2", "Throughput clamp", "LinTS arm capped at i★"),
         ("3", "Step-down", "if playing rung > T̂: one rung down, no rise"),
         ("4", "Switch priority", "clamped up-switch uses DEFAULT, others STRONG"),
         ("5", "Stall guard", "buffer ≤ 0.05 s: cap at 0.9 × worst of last 8 throughputs")]
for k, (n, head, body) in enumerate(rules):
    y = Inches(1.5) + k * Inches(1.04)
    c = rect(s, Inches(4.6), y, Inches(0.8), Inches(0.88), BLUE, shape=MSO_SHAPE.OVAL)
    box_text(c, n, size=22)
    tb(s, Inches(5.6), y - Inches(0.02), Inches(7.3), Inches(0.5), [head], size=20, bold=True, color=BLUE)
    tb(s, Inches(5.6), y + Inches(0.42), Inches(7.3), Inches(0.5), [body], size=17)

# ---------------------------------------------------------------- 10. Rejected
s = new_slide("Eight trials before the final rules", "Vidhu", subtitle="Results at a 3 s target; old CMAB on the same shaper: 3.19 s / 4955 kbps (CUBIC)")
rows = [("Trial", "Change", "Result", "Verdict"),
        ("1", "No top-rung probe", "900 kbps at every target", "rejected"),
        ("2", "Feasible probe + clamp only", "4.99 s at 3 s target (BBR)", "needs step-down"),
        ("3", "Step down if latency > target", "walked to 300 kbps", "rejected"),
        ("4–7", "Step down if > 1 s late", "CUBIC: 4.02 s, 3009 kbps", "rejected"),
        ("8", "Throughput-triggered step-down", "collapse fixed at 4 Mbit/s", "kept"),
        ("+", "Stall guard (worst of 8, hold 12)", "trace rebuffer down", "kept")]

def _verdict(i, j, val, f):
    if j == 3:
        f.color.rgb = GREEN if val == "kept" else ORANGE
        f.bold = True


table(s, rows, Inches(0.7), Inches(1.85), Inches(11.9), Inches(4.4),
      [Inches(1.0), Inches(4.4), Inches(4.2), Inches(2.3)], 17, _verdict)
tb(s, Inches(0.7), Inches(6.35), Inches(11.9), Inches(0.5),
   ["Latency is a poor down-switch trigger: a healthy player runs a little above its target."],
   size=17, bold=True)

# ---------------------------------------------------------------- 11. Method
s = new_slide("Method: three shapers, two transports, 450 runs", "Vidhu")
rows = [("Shaper", "Rate", "Delay / loss", "Targets", "Sessions"),
        ("Paper clock", "100 Mbit/s (50 in handover s)", "40 ms, 0.1% · 100 ms, 1%", "3–6 s", "120"),
        ("Capacity clock", "8 / 4 / 1 Mbit/s fixed", "same schedule", "3 s", "90"),
        ("4 Mbit/s targets", "4 Mbit/s fixed", "same schedule", "3–6 s", "120"),
        ("Starlink ISL trace", "50 Mbit/s cap (20 in handover)", "trace RTT ≈ 130 ms · 100% loss at handover", "3–6 s", "120")]
table(s, rows, Inches(0.7), Inches(1.5), Inches(11.9), Inches(3.0),
      [Inches(2.3), Inches(3.2), Inches(3.9), Inches(1.1), Inches(1.4)], 15)
card(s, Inches(0.7), Inches(4.75), Inches(5.8), Inches(1.95), "Every cell",
     ["old CMAB, CMAB+, L2A-LL · CUBIC and BBR", "5 rounds × 300 s · 450 sessions total"],
     accent=BLUE, body_size=17)
card(s, Inches(6.8), Inches(4.75), Inches(5.8), Inches(1.95), "Metrics",
     ["Drop first 20% · latency, rebuffer ratio (buffer ≤ 0.05 s), bitrate",
      "95% Student-t intervals, n = 5"], accent=BLUE, body_size=17)

# ---------------------------------------------------------------- 12. Results at a glance
s = new_slide("Results at a glance: CMAB+ against old CMAB", "Vidhu")
glance = [
    ("Paper clock, 100 Mbit/s", "≤ 0.15 s", "latency gap to old CMAB in any cell; 0% rebuffer under CUBIC", BLUE),
    ("4 Mbit/s, targets 3–6 s", "62–82% → 0%", "rebuffer ratio, CUBIC and BBR, all 40 CMAB+ sessions", BLUE),
    ("1 Mbit/s, 3 s target", "99% → 0% / 17%", "rebuffer ratio under BBR / CUBIC", BLUE),
    ("Starlink ISL trace, 3–6 s", "71–86% less", "rebuffering at every target; latency 1.1–13.5 s lower", BLUE),
]
for k, (head, big, label, col) in enumerate(glance):
    x = Inches(0.7) + (k % 2) * Inches(6.1)
    y = Inches(1.4) + (k // 2) * Inches(2.7)
    rect(s, x, y, Inches(5.8), Inches(2.45), LIGHT)
    rect(s, x, y, Inches(0.08), Inches(2.45), col)
    tb(s, x + Inches(0.3), y + Inches(0.15), Inches(5.3), Inches(0.5), [head], size=19, bold=True)
    tb(s, x + Inches(0.3), y + Inches(0.65), Inches(5.3), Inches(0.9), [big], size=40, bold=True, color=col)
    tb(s, x + Inches(0.3), y + Inches(1.6), Inches(5.3), Inches(0.8), [label], size=16, color=GREY)

# ---------------------------------------------------------------- 13. Paper clock latency
result_slide("Paper clock: CMAB+ latency tracks old CMAB", "Vidhu", "fig-clock-latency.png",
             "Within 0.15 s of old CMAB in every cell · 0.28 s faster under BBR at a 5 s target",
             "100 Mbit/s clock shaper, rules 1–4, mean of 5 sessions, 95% t intervals. Data: review-3/results/clock-nonreg.")

# ---------------------------------------------------------------- 14. Paper clock bitrate
result_slide("Paper clock: CMAB+ keeps old CMAB's bitrate", "Vidhu", "fig-clock-bitrate.png",
             "CMAB+ bitrate −11 to +141 kbps against old CMAB · 0% rebuffer in every CUBIC cell",
             "100 Mbit/s clock shaper, rules 1–4, mean of 5 sessions, 95% t intervals. Data: review-3/results/clock-nonreg.")

# ---------------------------------------------------------------- 15. 4 Mbit rebuffer
result_slide("4 Mbit/s: rebuffering 62–82% → 0% at every target", "Vidhu", "fig-4mbit-rebuffer.png",
             "old CMAB: 62–82% at 6000 kbps · CMAB+: 0% in all 40 sessions at 1457–1477 kbps",
             "Fixed 4 Mbit/s link, rules 1–4, mean of 5 sessions, 95% t intervals. Data: review-3/results/capacity-4mbit-targets.")

# ---------------------------------------------------------------- 16. 4 Mbit latency
result_slide("4 Mbit/s: CMAB+ cuts latency by 46.5–58.7%", "Vidhu", "fig-4mbit-latency.png",
             "CMAB+ 0.20–0.23 s above the 4–6 s targets and 0.54–0.62 s above 3 s · old CMAB 5.6–5.9 s above",
             "Fixed 4 Mbit/s link, rules 1–4, mean of 5 sessions, 95% t intervals. Dash-dot line: target. Data: review-3/results/capacity-4mbit-targets.")

# ---------------------------------------------------------------- 17. Capacity rebuffer
result_slide("Capacity: rebuffering drops where 6000 kbps cannot fit", "Pratham", "fig-capacity-rebuffer.png",
             "4 Mbit/s: 82% → 0% (CUBIC), 66% → 0% (BBR) · 1 Mbit/s: 99% → 17% (CUBIC), 99% → 0% (BBR)",
             "3 s target, rules 1–4, mean of 5 sessions, 95% t intervals. At 8 Mbit/s the top rung fits. Data: review-3/results/capacity.")

# ---------------------------------------------------------------- 18. Capacity bitrate
result_slide("Capacity: CMAB+ picks a rung below the link rate", "Pratham", "fig-capacity-bitrate.png",
             "old CMAB requests 6000 kbps at 4 and 1 Mbit/s · CMAB+ ≈ 1475 kbps at 4 Mbit/s, 450–888 kbps at 1 Mbit/s",
             "3 s target, rules 1–4, mean of 5 sessions, 95% t intervals. Dash-dot line: link rate. Data: review-3/results/capacity.")

# ---------------------------------------------------------------- 19. Trace rebuffer
result_slide("Starlink trace: rebuffering cut by 71–86% at every target", "Pratham", "fig-trace-rebuffer.png",
             "3 s target: 81% → 15% under CUBIC, 29% → 8% under BBR",
             "ISL trace shaper, rules 1–5, mean of 5 sessions, 95% t intervals. Data: review-3/results/trace-targets.")

# ---------------------------------------------------------------- 20. Trace bitrate
result_slide("Starlink trace: CMAB+ leaves the 6000 kbps lock", "Pratham", "fig-trace-bitrate.png",
             "CMAB+ 832–935 kbps (CUBIC) and 2499–2917 kbps (BBR) · old CMAB 5882–6000 kbps",
             "ISL trace shaper, rules 1–5, mean of 5 sessions, 95% t intervals. Data: review-3/results/trace-targets.")

# ---------------------------------------------------------------- 21. Stall guard before/after
result_slide("Stall guard more than halves CUBIC rebuffering", "Pratham", "fig-stallguard.png",
             "Rebuffer: CUBIC 31–35% → 12–15%, BBR 9–12% → 5–8% · bitrate cost: CUBIC 1578–1776 → 832–935 kbps",
             "CMAB+ only, ISL trace, mean of 5 sessions, 95% t intervals. Data: report/results/trace-pre-stallguard-aggregate.csv and review-3/results/trace-targets.")

# ---------------------------------------------------------------- 22. Trace timeline
result_slide("Trace session: after a stall, CMAB+ holds a low rung", "Pratham", "fig-trace-timeline.png",
             "Buffer empties at ~105 s · CMAB+ holds 450 kbps until ~127 s · old CMAB stays at 6000 kbps",
             "ISL trace, CUBIC, 3 s target, round 0, one session per player. Dash-dot line: 0.05 s rebuffer threshold. Data: review-3/demo-ui/public/sessions.")

# ---------------------------------------------------------------- 23. Demo
s = new_slide("Demo: side-by-side replay of logged sessions", "Pratham")
picture(s, ASSETS / "demo-ui-4mbit.png", Inches(0.5), Inches(1.35), Inches(9.0), Inches(5.2))
caption(s, Inches(0.6), Inches(6.55), Inches(8.9),
        "4 Mbit/s, 3 s target, CUBIC, round 0. Panes: old CMAB, CMAB+, L2A-LL (reference).")
tb(s, Inches(9.75), Inches(1.5), Inches(3.3), Inches(5.0),
   [("What it shows", {"bold": True, "size": 19}),
    ("Recorded bitrate and stalls per pane", {"spacing": 4}),
    ("15 s handover countdown", {"spacing": 18}),
    ("Run it", {"bold": True, "size": 19}),
    ("cd review-3/demo-ui", {"size": 15}),
    ("npm install", {"size": 15}),
    ("npm run dev", {"size": 15}),
    ("localhost:5173", {"size": 15})], size=16)

# ---------------------------------------------------------------- 24. Scope and next steps
s = new_slide("Scope and next steps", "Pratham")
items = [("Emulation only", "Trace replay through tc: one hour, one site  →  measure on a Starlink dish"),
         ("Five rounds per cell", "Intervals wide on some trace and 1 Mbit/s cells  →  ten rounds per cell"),
         ("Stall guard spot-checked on clock and 4 Mbit/s", "Those matrices used rules 1–4  →  rerun them with rules 1–5"),
         ("Clamp has no safety margin", "1 Mbit/s CUBIC still rebuffers 16.54%  →  margin or variance-aware cap"),
         ("Sample-based rebuffer metric", "Share of buffer samples ≤ 0.05 s  →  add wall-clock stall time")]
for k, (head, body) in enumerate(items):
    y = Inches(1.45) + k * Inches(1.08)
    rect(s, Inches(0.7), y, Inches(0.12), Inches(0.85), BLUE)
    tb(s, Inches(1.05), y - Inches(0.02), Inches(11.5), Inches(0.5), [head], size=21, bold=True)
    tb(s, Inches(1.05), y + Inches(0.43), Inches(11.5), Inches(0.5), [body], size=17, color=GREY)

# ---------------------------------------------------------------- 25. Conclusion
s = new_slide("Conclusion", "Pratham")
takeaways = [
    ("1", "Check the testbed first", "The first BBR “failure” was the wrong shaper. On the clock shaper BBR moves CMAB by 0.1 s."),
    ("2", "The flaw was in the controller", "old CMAB forces 6000 kbps for 7 decisions after every handover."),
    ("3", "Bound exploration by delivered throughput", "4 Mbit/s: 62–82% → 0% rebuffer. Trace: 71–86% less rebuffering than old CMAB."),
]
for k, (n, head, body) in enumerate(takeaways):
    y = Inches(1.5) + k * Inches(1.45)
    c = rect(s, Inches(0.7), y, Inches(0.85), Inches(0.85), NAVY, shape=MSO_SHAPE.OVAL)
    box_text(c, n, size=24)
    tb(s, Inches(1.8), y - Inches(0.05), Inches(11), Inches(0.5), [head], size=22, bold=True)
    tb(s, Inches(1.8), y + Inches(0.45), Inches(11), Inches(0.8), [body], size=18, color=GREY)
rect(s, Inches(0.7), Inches(5.95), Inches(11.9), Inches(0.85), LIGHT)
tb(s, Inches(0.9), Inches(5.95), Inches(11.5), Inches(0.85),
   ["Artifact: github.com/pratham-commits/CMAB_plus     ·     Questions?"],
   size=20, bold=True, color=BLUE, anchor=MSO_ANCHOR.MIDDLE)

assert len(prs.slides) == len(SLIDES)
for i, sl in enumerate(prs.slides):
    sl.notes_slide.notes_text_frame.text = notes_text(i)

out = HERE / "final-review.pptx"
prs.save(out)
print(f"wrote {out} with {len(prs.slides)} slides")
