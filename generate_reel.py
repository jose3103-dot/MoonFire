#!/usr/bin/env python3
"""
Skeletons in the Closet — Meet Fatso
TikTok reel generator: produces fatso-reel.mp4
"""

import os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import imageio_ffmpeg

# ═══════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════
W, H    = 1080, 1920        # TikTok 9:16
FPS     = 24
CRF     = 22                # quality (lower = better)

UP      = '/root/.claude/uploads/3fbd7e18-ae09-5625-b6a1-e1315253f25a'
OUT     = '/home/user/MoonFire/assets/fatso-reel.mp4'

TITLE   = f'{UP}/d27ba817-27F18AF7051D4186924CF291266B31AC.png'
S1      = f'{UP}/380dd332-IMG_6592.jpeg'          # Randy & Maggie at table
S2      = f'{UP}/65536841-3B4E13293C4E490A8A759F5C88145958.png'  # Fatso reveal

FONT_B  = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_R  = '/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf'

BG      = (9, 9, 11)
WHT     = (255, 255, 255)
BLK     = (0, 0, 0)
ORANGE  = (249, 115, 22)

CHAR_FG = {
    'RANDY':         (251, 146, 60),
    'MAGGIE':        (192, 132, 252),
    'FATSO (IZZY)':  (251, 191, 36),
}
CHAR_BG = {
    'RANDY':         (80, 30, 5),
    'MAGGIE':        (55, 20, 100),
    'FATSO (IZZY)':  (85, 40, 5),
}

# Script beats: (scene_image, character, dialog, seconds)
BEATS = [
    (S1, 'RANDY',        "Maggie, I have someone new\nto introduce to the crew.",              4.5),
    (S1, 'MAGGIE',       "Oh? Another experiment?\nA new gadget? Or... a plant this time?",   5.0),
    (S1, 'RANDY',        "Better. Furrier.\nLouder. Dirtier.",                                3.5),
    (S2, 'RANDY',        "Say hello to Fatso — A.K.A. Izzy.\nThe Professional Soil Rooter.", 5.0),
    (S2, 'MAGGIE',       "Well... that is\ndisturbingly perfect.",                            4.0),
    (S2, 'RANDY',        "I outfitted her with the finest\ngarden tech I could build.",       4.5),
    (S2, 'MAGGIE',       "Randy... those are incredible.",                                    3.5),
    (S2, 'RANDY',        "The world's first canine-powered,\nnose-guided, dirt-detecting,\ntine-tilling marvel.", 6.0),
    (S2, 'FATSO (IZZY)', "I smell adventure...\nand snacks.",                                 4.0),
    (S2, 'MAGGIE',       "Of course you do.",                                                 3.5),
]

GEAR = [
    ('NOSE GRUBBER 3000',  'High-sensitivity soil sniffer.\nDetects roots, voles, snacks, and trouble.'),
    ('DIRT DETECTOR',      'Alerts Fatso when soil is\nloose, compacted, or suspicious.'),
    ('SQUIRREL SENSOR',    'Tracks underground squirrel tunnels.\n(Not that she needs the help.)'),
    ('TINE TURBO TILLER',  'Six rotating tines for maximum\nroot agitation and aeration.'),
    ('TREAT DISPENSER',    'Positive reinforcement module.\nMay backfire. (Prototype)'),
]

FACT = [
    "She rarely understands",
    "why anyone else is concerned.",
    "",
    "She just follows the dirt.",
]

# ═══════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════
def font(size, bold=True):
    path = FONT_B if bold else FONT_R
    return ImageFont.truetype(path, size)

FONTS = {
    'dialog':  font(56),
    'char':    font(24),
    'action':  font(26, bold=False),
    'small':   font(22),
    'gear_h':  font(30),
    'gear_d':  font(26, bold=False),
    'fact':    font(50),
    'fact_lbl':font(28),
    'title':   font(70),
    'sub':     font(32, bold=False),
}

# ═══════════════════════════════════════════════════════════
#  IMAGE CACHE
# ═══════════════════════════════════════════════════════════
_cache = {}

def get_scene(path):
    """Returns (sharp_top, blurred_bg, scene_h)"""
    if path in _cache:
        return _cache[path]

    src = Image.open(path).convert('RGB')
    sw, sh = src.size

    # Scale to frame width
    scale   = W / sw
    scaled  = src.resize((W, int(sh * scale)), Image.LANCZOS)
    scene_h = scaled.height      # height of scene image when full-width

    # Blurred bg fills full frame
    bg_scale = max(W / sw, H / sh)
    bw, bh   = int(sw * bg_scale), int(sh * bg_scale)
    bg_full  = src.resize((bw, bh), Image.LANCZOS)
    # Crop to frame
    x0 = (bw - W) // 2
    y0 = (bh - H) // 2
    bg_crop = bg_full.crop((x0, y0, x0 + W, y0 + H))
    bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(radius=28))
    # Darken
    dark    = Image.new('RGB', (W, H), BG)
    bg_dark = Image.blend(bg_blur, dark, 0.72)

    _cache[path] = (scaled, bg_dark, scene_h)
    return _cache[path]

def get_title():
    if TITLE + '_ready' in _cache:
        return _cache[TITLE + '_ready']
    src  = Image.open(TITLE).convert('RGB')
    sw, sh = src.size
    # Scale to fill height, center horizontally
    scale = H / sh
    nw, nh = int(sw * scale), int(sh * scale)
    scaled = src.resize((nw, nh), Image.LANCZOS)
    x0 = (nw - W) // 2
    cropped = scaled.crop((x0, 0, x0 + W, H))
    _cache[TITLE + '_ready'] = cropped
    return cropped

# ═══════════════════════════════════════════════════════════
#  GRADIENT OVERLAY (generated once per scene height)
# ═══════════════════════════════════════════════════════════
_grads = {}

def get_gradient(scene_h):
    if scene_h in _grads:
        return _grads[scene_h]
    grad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(grad)
    fade_start = max(scene_h - 250, 0)
    fade_end   = scene_h + 80
    for y in range(H):
        if y <= fade_start:
            a = 0
        elif y <= fade_end:
            t = (y - fade_start) / (fade_end - fade_start)
            a = int(t ** 1.5 * 200)
        else:
            extra = min(1.0, (y - fade_end) / 400)
            a = int(200 + extra * 55)
        if a > 0:
            draw.line([(0, y), (W, y)], fill=(*BG, min(255, a)))
    _grads[scene_h] = grad
    return grad

# ═══════════════════════════════════════════════════════════
#  DRAWING HELPERS
# ═══════════════════════════════════════════════════════════

def progress_bar(draw, beat_idx, n_beats, pct):
    """Draw segmented progress bar at top of frame."""
    pad   = 24
    y     = 28
    bh    = 5
    gap   = 5
    total_w = W - 2 * pad
    seg_w = (total_w - gap * (n_beats - 1)) / n_beats

    for i in range(n_beats):
        x0 = int(pad + i * (seg_w + gap))
        x1 = int(x0 + seg_w)
        # track
        draw.rectangle([x0, y, x1, y + bh], fill=(60, 60, 65))
        # fill
        if i < beat_idx:
            draw.rectangle([x0, y, x1, y + bh], fill=ORANGE)
        elif i == beat_idx:
            fx = int(x0 + seg_w * pct)
            if fx > x0:
                draw.rectangle([x0, y, fx, y + bh], fill=ORANGE)


def chip(img, text, fg, bg_col, x, y, pad_h=18, pad_v=12, radius=28):
    """Draw a rounded pill with text; returns bottom y of chip."""
    draw   = ImageDraw.Draw(img)
    bbox   = draw.textbbox((0, 0), text, font=FONTS['char'])
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w      = tw + pad_h * 2
    h      = th + pad_v * 2

    # Draw filled rounded rect on RGBA layer
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld    = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                         fill=(*bg_col, 210), outline=(*fg, 90), width=2)
    img_rgba = img.convert('RGBA')
    img_rgba.alpha_composite(layer)
    out = img_rgba.convert('RGB')
    draw2 = ImageDraw.Draw(out)
    draw2.text((x + pad_h, y + pad_v - 1), text, font=FONTS['char'], fill=fg)
    return out, y + h


def shadow_text(draw, xy, text, font, fill, shadow=(0, 0, 0), offset=2):
    draw.text((xy[0] + offset, xy[1] + offset), text, font=font, fill=shadow)
    draw.text(xy, text, font=font, fill=fill)


def blend_alpha(base, alpha):
    """Blend image toward BG by (1 - alpha)."""
    if alpha >= 1.0:
        return base
    dark = Image.new('RGB', (W, H), BG)
    return Image.blend(base, dark, 1.0 - alpha)


# ═══════════════════════════════════════════════════════════
#  FRAME BUILDERS
# ═══════════════════════════════════════════════════════════

def make_dialog_frame(scene_path, char, dialog, beat_idx, pct, chars_shown):
    sharp, bg, scene_h = get_scene(scene_path)
    grad = get_gradient(scene_h)

    # Base: blurred bg
    frame = bg.copy().convert('RGBA')
    # Paste sharp scene at top
    frame.paste(sharp.convert('RGBA'), (0, 0))
    # Gradient overlay
    frame.alpha_composite(grad)
    frame = frame.convert('RGB')
    draw  = ImageDraw.Draw(frame)

    # Progress bar
    progress_bar(draw, beat_idx, len(BEATS), pct)

    # Brand
    draw.text((26, 52), "SKULL MOUNTAIN", font=FONTS['small'],
              fill=(140, 140, 150))

    # Layout: chip starts just below scene image
    chip_y   = scene_h + 40
    action_y = chip_y + 72
    dialog_y = action_y + 44

    fg  = CHAR_FG.get(char, WHT)
    bgc = CHAR_BG.get(char, (40, 40, 40))

    frame, chip_bottom = chip(frame, char, fg, bgc, 24, chip_y)
    draw = ImageDraw.Draw(frame)

    # Dialog text with typewriter reveal
    visible = dialog[:chars_shown]
    y = dialog_y
    for line in visible.split('\n'):
        shadow_text(draw, (28, y), line, FONTS['dialog'], WHT, offset=3)
        y += 72

    # Bottom bar
    bar_h  = 100
    layer  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld     = ImageDraw.Draw(layer)
    ld.rectangle([0, H - bar_h, W, H], fill=(0, 0, 0, 185))
    frame_rgba = frame.convert('RGBA')
    frame_rgba.alpha_composite(layer)
    frame = frame_rgba.convert('RGB')
    draw  = ImageDraw.Draw(frame)

    icons = [('< 3', '24.1K'), ('[ ]', '1,847'), ('[S]', '8,902'), ('->', 'Share')]
    step = W // 4
    for i, (icon, label) in enumerate(icons):
        ix = step * i + step // 2 - 22
        draw.text((ix, H - 88), icon, font=FONTS['small'], fill=WHT)
        draw.text((ix, H - 52), label, font=FONTS['small'], fill=(130, 130, 140))

    return frame


def make_title_frame(alpha=1.0):
    base = get_title().copy()
    # Dark vignette at top and bottom
    vig  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    vd   = ImageDraw.Draw(vig)
    for y in range(200):
        a = int((1 - y / 200) * 140)
        vd.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    for y in range(H - 200, H):
        a = int(((y - (H - 200)) / 200) * 180)
        vd.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    out  = base.convert('RGBA')
    out.alpha_composite(vig)
    out  = out.convert('RGB')
    return blend_alpha(out, alpha)


def make_gear_frame(items_shown):
    frame = Image.new('RGB', (W, H), BG)
    draw  = ImageDraw.Draw(frame)

    # Orange bar at top
    draw.rectangle([0, 0, W, 8], fill=ORANGE)

    draw.text((38, 40), "FATSO'S OFFICIAL GEAR", font=FONTS['gear_h'], fill=ORANGE)
    draw.text((38, 85), "Built by Randy Rattle", font=FONTS['fact_lbl'], fill=WHT)
    draw.line([(38, 135), (W - 38, 135)], fill=(50, 50, 58), width=2)

    y = 158
    for i, (name, desc) in enumerate(GEAR):
        if i >= items_shown:
            break
        alpha = 1.0

        # Number badge
        draw.ellipse([38, y + 2, 68, y + 32], fill=ORANGE)
        draw.text((45, y + 4), str(i + 1), font=FONTS['small'], fill=BLK)

        name_col = tuple(int(c * alpha) for c in (251, 146, 60))
        draw.text((82, y), name, font=FONTS['gear_h'], fill=name_col)

        desc_lines = desc.split('\n')
        for j, dl in enumerate(desc_lines):
            draw.text((82, y + 38 + j * 30), dl, font=FONTS['gear_d'],
                      fill=(160, 160, 170))

        y += 145

    # Footer
    draw.text((38, H - 80), "SKELETONS IN THE CLOSET", font=FONTS['small'],
              fill=(60, 62, 68))

    return frame


def make_fact_frame(alpha=1.0):
    frame = Image.new('RGB', (W, H), BG)

    # Amber glow behind center
    glow  = Image.new('RGB', (W, H), BG)
    gd    = ImageDraw.Draw(glow)
    for r in range(550, 0, -25):
        t = 1 - r / 550
        c = (int(t * 100 * alpha), int(t * 45 * alpha), int(t * 2 * alpha))
        gd.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r], fill=c)
    frame = Image.blend(frame, glow, 0.85)

    draw  = ImageDraw.Draw(frame)

    cy    = H // 2 - 280

    amber = tuple(int(c * alpha) for c in (217, 119, 6))
    white = tuple(int(c * alpha) for c in WHT)
    dim   = tuple(int(c * alpha) for c in (82, 82, 91))

    draw.text((W // 2 - 18, cy), "*", font=FONTS['title'],
              fill=tuple(int(c * alpha) for c in ORANGE))

    draw.text((W // 2 - 65, cy + 100), "FATSO FACT", font=FONTS['fact_lbl'],
              fill=amber)

    line_y = cy + 145
    draw.line([(120, line_y), (W - 120, line_y)],
              fill=tuple(int(c * alpha) for c in (90, 55, 10)), width=2)

    ty = line_y + 28
    for line in FACT:
        if line:
            bbox = draw.textbbox((0, 0), line, font=FONTS['fact'])
            tx   = (W - (bbox[2] - bbox[0])) // 2
            shadow_text(draw, (tx, ty), line, FONTS['fact'], white, offset=2)
        ty += 68

    draw.line([(120, ty + 20), (W - 120, ty + 20)],
              fill=tuple(int(c * alpha) for c in (90, 55, 10)), width=2)

    # Show title
    title_w = draw.textbbox((0, 0), "SKELETONS IN THE CLOSET",
                             font=FONTS['fact_lbl'])[2]
    draw.text(((W - title_w) // 2, H - 180),
              "SKELETONS IN THE CLOSET", font=FONTS['fact_lbl'], fill=amber)

    sub_w = draw.textbbox((0, 0), "Skull Mountain", font=FONTS['sub'])[2]
    draw.text(((W - sub_w) // 2, H - 135),
              "Skull Mountain", font=FONTS['sub'], fill=dim)

    return frame


# ═══════════════════════════════════════════════════════════
#  VIDEO ENCODER
# ═══════════════════════════════════════════════════════════

def encode():
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd    = [
        ffmpeg, '-y',
        '-f',       'rawvideo',
        '-vcodec',  'rawvideo',
        '-s',       f'{W}x{H}',
        '-pix_fmt', 'rgb24',
        '-r',       str(FPS),
        '-i',       'pipe:0',
        '-vcodec',  'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf',     str(CRF),
        '-preset',  'fast',
        OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    total = 0

    def w(img):
        nonlocal total
        proc.stdin.write(img.tobytes())
        total += 1

    def frames(n, builder):
        for _ in range(n):
            w(builder())

    # Pre-warm image cache
    print("  Caching images...")
    get_scene(S1); get_scene(S2); get_title()
    get_gradient(get_scene(S1)[2]); get_gradient(get_scene(S2)[2])

    # ── TITLE (fade in, hold, fade out) ──────────────────────
    print("  Title card...")
    FADE = int(FPS * 0.7)
    HOLD = int(FPS * 2.5)

    for f in range(FADE):
        w(make_title_frame(f / FADE))
    frames(HOLD, lambda: make_title_frame(1.0))
    for f in range(FADE):
        w(make_title_frame(1.0 - f / FADE))

    # ── DIALOG BEATS ─────────────────────────────────────────
    CHARS_PER_SEC = 16

    for bi, (scene_path, char, dialog, secs) in enumerate(BEATS):
        print(f"  Beat {bi+1}/{len(BEATS)}: {char}...")
        beat_frames = int(FPS * secs)
        clean       = dialog.replace('\n', ' ')
        total_chars = len(dialog)           # typewriter counts raw chars incl \n
        type_frames = min(
            int(total_chars / CHARS_PER_SEC * FPS),
            int(beat_frames * 0.52)
        )
        type_frames = max(type_frames, 1)

        for f in range(beat_frames):
            pct = f / beat_frames
            if f < type_frames:
                shown = max(1, int((f / type_frames) * total_chars))
            else:
                shown = total_chars

            w(make_dialog_frame(scene_path, char, dialog, bi, pct, shown))

    # ── BRIEF BLACK TRANSITION ────────────────────────────────
    black = Image.new('RGB', (W, H), BG)
    frames(int(FPS * 0.45), lambda: black)

    # ── GEAR REVEAL ──────────────────────────────────────────
    print("  Gear reveal...")
    PER_ITEM = int(FPS * 1.3)
    GEAR_HOLD = int(FPS * 2.0)
    frames(int(FPS * 0.4), lambda: make_gear_frame(0))
    for i in range(1, len(GEAR) + 1):
        frames(PER_ITEM, lambda i=i: make_gear_frame(i))
    frames(GEAR_HOLD, lambda: make_gear_frame(len(GEAR)))

    # ── BLACK TRANSITION ──────────────────────────────────────
    frames(int(FPS * 0.45), lambda: black)

    # ── FATSO FACT ───────────────────────────────────────────
    print("  Fatso Fact...")
    FACT_IN   = int(FPS * 1.2)
    FACT_HOLD = int(FPS * 4.5)
    FACT_OUT  = int(FPS * 0.9)
    for f in range(FACT_IN):
        w(make_fact_frame(f / FACT_IN))
    frames(FACT_HOLD, lambda: make_fact_frame(1.0))
    for f in range(FACT_OUT):
        w(make_fact_frame(1.0 - f / FACT_OUT))

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        print("ffmpeg error (check stderr)")
    else:
        size_mb = os.path.getsize(OUT) / 1024 / 1024
        print(f"\n  Done — {total} frames, {size_mb:.1f} MB")
        print(f"  Output: {OUT}")


if __name__ == '__main__':
    print(f"Skeletons in the Closet — Meet Fatso Reel")
    print(f"Resolution: {W}x{H}  FPS: {FPS}\n")
    encode()
