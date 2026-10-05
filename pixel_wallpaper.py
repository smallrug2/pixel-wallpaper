"""pixel_wallpaper.py - Tiny pixel-art wallpapers drawn low-res, then upscaled.

Purpose: generate retro pixel wallpapers in four generic modes:
    chevron  - rainbow stripes with nested chevron overlay
    flag     - horizontal bands from a --colors list
    bands    - smooth vertical gradient through --colors
    progress - dark wallpaper with a progress bar at --pct percent

Usage:
    python pixel_wallpaper.py --mode chevron --w 1920 --h 1080 --out wp.png
    python pixel_wallpaper.py --mode flag --colors "#55CDFC,#F7A8B8,#FFFFFF,#F7A8B8,#55CDFC"
    python pixel_wallpaper.py --mode bands --colors "#7c3aed,#06b6d4"
    python pixel_wallpaper.py --mode progress --pct 65 --colors "#7c3aed,#06b6d4"

Platform: Windows + Linux. Requires Pillow (PIL).
    pip install Pillow
"""
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: Pillow is required. Install it with: pip install Pillow",
          file=sys.stderr)
    sys.exit(1)

DEFAULT_RAINBOW = ["#E40303", "#FF8C00", "#FFED00", "#008026", "#24408E", "#732982"]
DEFAULT_CHEV = ["#000000", "#613915", "#5BCFFB", "#F5ABB9", "#FFFFFF"]
LOW_W, LOW_H = 96, 54  # low-res canvas, upscaled with NEAREST


def parse_hex(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:  # short form e.g. abc
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError("bad color %r (want #RRGGBB)" % s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def parse_colors(s):
    return [parse_hex(c) for c in s.split(",") if c.strip()]


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def chevron_overlay(img, bg_colors, chev_colors):
    """Paint bg_colors as horizontal stripes, then nested chevrons on top."""
    w, h = img.size
    px = img.load()
    n_chev = len(chev_colors)
    tip, anchor = 0.45 * w, 0.18 * w
    step = 0.065 * w
    tips = [tip - k * step for k in range(n_chev)]
    anchors = [anchor - k * step for k in range(n_chev)]
    rows_per = max(1, h // len(bg_colors))
    for y in range(h):
        stripe = bg_colors[min(y // rows_per, len(bg_colors) - 1)]
        yy = y if y <= h / 2 else h - 1 - y
        t = yy / max(1, h / 2)
        for x in range(w):
            col = chev_colors[-1]
            for k in range(n_chev):
                bx = anchors[k] + (tips[k] - anchors[k]) * t
                if x > bx:
                    col = None if k == 0 else chev_colors[k - 1]
                    break
            px[x, y] = stripe if col is None else col


def mode_chevron(w, h, colors):
    img = Image.new("RGB", (LOW_W, LOW_H))
    bg = colors if colors else [parse_hex(c) for c in DEFAULT_RAINBOW]
    chevron_overlay(img, bg, [parse_hex(c) for c in DEFAULT_CHEV])
    return img.resize((w, h), Image.NEAREST)


def mode_flag(w, h, colors):
    cols = colors or [parse_hex(c) for c in
                      ["#55CDFC", "#F7A8B8", "#FFFFFF", "#F7A8B8", "#55CDFC"]]
    low = Image.new("RGB", (LOW_W, LOW_H))
    px = low.load()
    bounds = [i * LOW_H // len(cols) for i in range(len(cols) + 1)]
    for y in range(LOW_H):
        idx = next(i for i in range(len(cols)) if y < bounds[i + 1])
        for x in range(LOW_W):
            px[x, y] = cols[idx]
    return low.resize((w, h), Image.NEAREST)


def mode_bands(w, h, colors):
    cols = colors or [parse_hex(c) for c in ["#7c3aed", "#06b6d4"]]
    if len(cols) == 1:
        cols = [cols[0], cols[0]]
    low = Image.new("RGB", (LOW_W, LOW_H))
    px = low.load()
    for y in range(LOW_H):
        t = y / max(1, LOW_H - 1) * (len(cols) - 1)
        i = min(int(t), len(cols) - 2)
        c = lerp(cols[i], cols[i + 1], t - i)
        for x in range(LOW_W):
            px[x, y] = c
    return low.resize((w, h), Image.NEAREST)


def mode_progress(w, h, pct, colors):
    cols = colors or [parse_hex(c) for c in ["#7c3aed", "#06b6d4"]]
    c1, c2 = cols[0], cols[-1]
    img = Image.new("RGB", (w, h), (10, 11, 14))
    d = ImageDraw.Draw(img)
    # Bar geometry scales with output size.
    bx0, bx1 = int(w * 0.15), int(w * 0.85)
    by0, by1 = int(h * 0.46), int(h * 0.54)
    d.rectangle([bx0, by0, bx1, by1], outline=(60, 60, 70))
    fill_w = int((bx1 - bx0 - 4) * max(0.0, min(1.0, pct / 100.0)))
    for x in range(fill_w):
        t = x / max(1, fill_w - 1)
        d.line([(bx0 + 2 + x, by0 + 2), (bx0 + 2 + x, by1 - 2)],
               fill=lerp(c1, c2, t))
    # Pixel ticks: keep the retro feel with a blocky border.
    tick = max(1, w // 480)
    d.rectangle([bx0 - tick, by0 - tick, bx1 + tick, by1 + tick],
                outline=(200, 200, 210))
    return img


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Generate pixel-art wallpaper")
    p.add_argument("--mode", default="chevron",
                   choices=["chevron", "flag", "bands", "progress"])
    p.add_argument("--w", type=int, default=1920, help="Output width")
    p.add_argument("--h", type=int, default=1080, help="Output height")
    p.add_argument("--out", default="wp.png", help="Output PNG path")
    p.add_argument("--colors", default="",
                   help="Comma-separated #RRGGBB list (flag/bands/progress)")
    p.add_argument("--pct", type=float, default=50.0,
                   help="Fill percent for --mode progress (0-100)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.w < 16 or args.h < 16 or args.w > 7680 or args.h > 4320:
        print("ERROR: --w/--h out of range (16..7680)", file=sys.stderr)
        sys.exit(2)
    colors = parse_colors(args.colors) if args.colors.strip() else None
    if args.mode == "chevron":
        img = mode_chevron(args.w, args.h, colors)
    elif args.mode == "flag":
        img = mode_flag(args.w, args.h, colors)
    elif args.mode == "bands":
        img = mode_bands(args.w, args.h, colors)
    elif args.mode == "progress":
        img = mode_progress(args.w, args.h, args.pct, colors)
    out = Path(args.out)
    if str(out.parent) not in (".", ""):
        out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("saved %s (%dx%d, mode=%s)" % (out, args.w, args.h, args.mode))


if __name__ == "__main__":
    main()
