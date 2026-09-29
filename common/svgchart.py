"""Tiny dependency-free SVG chart helpers (dark card style, readable on GitHub light and dark themes)."""
from html import escape

BG, CARD, GRID = "#0b1b33", "#10233f", "#24406a"
INK, INK2, MUTED = "#ffffff", "#c3c2b7", "#8fb3dd"
BLUE, ORANGE, AQUA = "#3987e5", "#d95926", "#199e70"
STATUS = {"critical": "#e66767", "serious": "#d95926", "warning": "#c98500", "good": "#199e70", "neutral": "#5b7aa6"}
FONT = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"


def _frame(w, h, title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">',
            f'<style>text{{font-family:{FONT}}}</style>',
            f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>',
            f'<text x="24" y="34" font-size="17" font-weight="700" fill="{INK}">{escape(title)}</text>',
            f'<text x="24" y="56" font-size="12.5" fill="{MUTED}">{escape(subtitle)}</text>']


def _nice(v):
    """Smallest 'round' axis top >= v with 4 even gridline steps (1, 2, 2.5, 5 x 10^n per step)."""
    import math
    if v <= 0:
        return 4
    raw = v / 4
    e = 10 ** math.floor(math.log10(raw))
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= raw:
            step = m * e
            break
    if step < 1:
        step = 1
    return step * 4


def bars(path, title, subtitle, labels, values, colors=None, unit="", w=860, h=360, annotate=True):
    """Vertical bars, 4px rounded tops, value labels on top, one y-axis."""
    colors = colors or [BLUE] * len(values)
    s = _frame(w, h, title, subtitle)
    L, R, T, B = 60, 24, 80, 58
    pw, ph = w - L - R, h - T - B
    top = _nice(max(values) * 1.08)
    for i in range(5):
        v = top * i / 4
        y = T + ph - ph * i / 4
        s.append(f'<line x1="{L}" x2="{w-R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{L-8}" y="{y+4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{v:,.0f}{unit}</text>')
    n = len(values)
    slot = pw / n
    bw = min(56, slot * 0.62)
    for i, (lab, v, c) in enumerate(zip(labels, values, colors)):
        x = L + slot * i + (slot - bw) / 2
        bh = ph * v / top
        y = T + ph - bh
        r = min(4, bh / 2)
        s.append(f'<path d="M{x:.1f},{T+ph:.1f} V{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} H{x+bw-r:.1f} Q{x+bw:.1f},{y:.1f} {x+bw:.1f},{y+r:.1f} V{T+ph:.1f} Z" fill="{c}"><title>{escape(str(lab))}: {v:,}{unit}</title></path>')
        if annotate:
            s.append(f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" font-size="11.5" font-weight="600" fill="{INK}" text-anchor="middle">{v:,}{unit}</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{T+ph+18:.1f}" font-size="11" fill="{INK2}" text-anchor="middle">{escape(str(lab))}</text>')
    s.append('</svg>')
    open(path, "w").write("\n".join(s))


def grouped(path, title, subtitle, labels, series, unit="", w=860, h=360):
    """series: list of (name, color, values). Legend top-right; one y-axis."""
    s = _frame(w, h, title, subtitle)
    L, R, T, B = 60, 24, 84, 58
    pw, ph = w - L - R, h - T - B
    top = _nice(max(max(v) for _, _, v in series) * 1.08)
    for i in range(5):
        v = top * i / 4
        y = T + ph - ph * i / 4
        s.append(f'<line x1="{L}" x2="{w-R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-8}" y="{y+4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{v:,.0f}{unit}</text>')
    lx = w - R
    for name, col, _ in reversed(series):
        tw = 7 * len(name) + 22
        lx -= tw
        s.append(f'<rect x="{lx}" y="24" width="12" height="12" rx="3" fill="{col}"/><text x="{lx+17}" y="34" font-size="12" fill="{INK2}">{escape(name)}</text>')
    n, k = len(labels), len(series)
    slot = pw / n
    bw = min(26, slot * 0.7 / k)
    for i, lab in enumerate(labels):
        x0 = L + slot * i + (slot - bw * k - 2 * (k - 1)) / 2
        for j, (name, col, vals) in enumerate(series):
            v = vals[i]
            x = x0 + j * (bw + 2)
            bh = ph * v / top
            y = T + ph - bh
            r = min(4, bh / 2)
            s.append(f'<path d="M{x:.1f},{T+ph:.1f} V{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} H{x+bw-r:.1f} Q{x+bw:.1f},{y:.1f} {x+bw:.1f},{y+r:.1f} V{T+ph:.1f} Z" fill="{col}"><title>{escape(lab)} · {escape(name)}: {v:,}{unit}</title></path>')
        s.append(f'<text x="{L+slot*i+slot/2:.1f}" y="{T+ph+18:.1f}" font-size="11" fill="{INK2}" text-anchor="middle">{escape(lab)}</text>')
    s.append('</svg>')
    open(path, "w").write("\n".join(s))


def hbars(path, title, subtitle, labels, values, color=BLUE, unit="", w=860, row=34):
    """Horizontal bars sorted by caller; labels left, values at bar end."""
    h = 84 + row * len(values) + 20
    s = _frame(w, h, title, subtitle)
    L, R, T = 230, 70, 80
    pw = w - L - R
    top = max(values)
    for i, (lab, v) in enumerate(zip(labels, values)):
        y = T + i * row
        bw = max(4, pw * v / top)
        s.append(f'<text x="{L-10}" y="{y+17}" font-size="12.5" fill="{INK2}" text-anchor="end">{escape(lab)}</text>')
        s.append(f'<rect x="{L}" y="{y+4}" width="{bw:.1f}" height="{row-12}" rx="4" fill="{color}"><title>{escape(lab)}: {v:,}{unit}</title></rect>')
        s.append(f'<text x="{L+bw+8:.1f}" y="{y+17}" font-size="12" font-weight="600" fill="{INK}">{v:,}{unit}</text>')
    s.append('</svg>')
    open(path, "w").write("\n".join(s))
