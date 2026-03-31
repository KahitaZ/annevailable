import os
import subprocess
import tempfile
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw

CORAL = (255, 107, 80)
BG    = (14, 14, 14)

# ── 1. Render logo.svg → PNG ──────────────────────────────────────────────────
tmpdir = tempfile.mkdtemp()
subprocess.run(
    ["qlmanage", "-t", "-s", "1200", "-o", tmpdir, "claudeassets/logo.svg"],
    capture_output=True
)
logo_raw = Image.open(os.path.join(tmpdir, "logo.svg.png")).convert("RGBA")

def recolor(src, fill_rgb, opacity=1.0):
    """
    Dark pixels → fill_rgb at given opacity, transparent/white pixels → transparent.
    Handles both transparent-bg and white-bg qlmanage renders.
    """
    out = []
    for r, g, b, a in src.getdata():
        if a < 10:                          # transparent bg pixel
            out.append((0, 0, 0, 0))
            continue
        # For opaque pixels: dark = visible, light = background
        brightness = int((r + g + b) / 3)
        alpha = max(0, 255 - brightness)    # black→255, white→0
        if alpha < 20:
            out.append((0, 0, 0, 0))
        else:
            out.append((*fill_rgb, int(alpha * opacity)))
    result = src.copy()
    result.putdata(out)
    return result

# ── 2. Build QR ───────────────────────────────────────────────────────────────
qr = qrcode.QRCode(
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=12,
    border=4,
)
qr.add_data("https://annevailable.com")
qr.make(fit=True)

img = qr.make_image(
    image_factory=StyledPilImage,
    module_drawer=RoundedModuleDrawer(),
    color_mask=SolidFillColorMask(front_color=CORAL, back_color=BG),
).convert("RGBA")

qr_w, qr_h = img.size

# ── 3. Scale logo — card ~28% of QR width (well within H error correction) ───
padding    = 14
shadow_off = 5                              # shadow goes bottom-right, matching site
target_card_w = int(qr_w * 0.28)
target_logo_w = target_card_w - 2 * padding - shadow_off
target_logo_h = int(target_logo_w * logo_raw.height / logo_raw.width)

logo_sized  = logo_raw.resize((target_logo_w, target_logo_h), Image.LANCZOS)
logo_main   = recolor(logo_sized, CORAL, opacity=1.0)    # full coral
logo_shadow = recolor(logo_sized, CORAL, opacity=0.25)   # 25 % coral, same as website

# ── 4. Build card: shadow first, main logo on top ────────────────────────────
card_w = target_logo_w + 2 * padding + shadow_off
card_h = target_logo_h + 2 * padding + shadow_off
border = 3
radius = 12

card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
draw = ImageDraw.Draw(card)
draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=radius, fill=CORAL)
draw.rounded_rectangle(
    [border, border, card_w - 1 - border, card_h - 1 - border],
    radius=max(2, radius - border),
    fill=BG,
)

lx, ly = padding, padding
card.paste(logo_shadow, (lx + shadow_off, ly + shadow_off), logo_shadow)  # shadow: offset
card.paste(logo_main,   (lx, ly),                           logo_main)    # main: on top

# ── 5. Composite centered on QR ───────────────────────────────────────────────
img.paste(card, ((qr_w - card_w) // 2, (qr_h - card_h) // 2), card)

img.save("annevailable_qr_styled.png")
print(f"Done — card {card_w}×{card_h} ({card_w*card_h*100//(qr_w*qr_h)}% area) on QR {qr_w}×{qr_h}")
