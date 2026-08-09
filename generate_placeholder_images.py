import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), 'static', 'public', 'images')
os.makedirs(OUT_DIR, exist_ok=True)

NAVY = (10, 37, 68)
NAVY_DEEP = (7, 26, 48)
BLUE = (13, 110, 253)
BLUE_LIGHT = (79, 156, 249)
GOLD = (245, 185, 66)
WHITE = (255, 255, 255)

FONT_DIR = 'C:/Windows/Fonts'


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(size, c1, c2, diagonal=True):
    w, h = size
    img = Image.new('RGB', size, c1)
    draw = ImageDraw.Draw(img)
    span = (w + h) if diagonal else h
    for y in range(h):
        for_t = y / h
        color = lerp(c1, c2, for_t)
        draw.line([(0, y), (w, y)], fill=color)
    return img


def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def person_avatar(path, size, initials, c1, c2):
    img = gradient(size, c1, c2)
    draw = ImageDraw.Draw(img)
    w, h = size
    cx, cy = w // 2, h // 2

    # soft head + shoulders silhouette
    head_r = int(h * 0.16)
    draw.ellipse([cx - head_r, cy - int(h * 0.14) - head_r, cx + head_r, cy - int(h * 0.14) + head_r],
                 fill=(255, 255, 255, 60))
    body_top = cy - int(h * 0.14) + head_r - 4
    draw.ellipse([cx - int(w * 0.32), body_top, cx + int(w * 0.32), body_top + int(h * 0.55)],
                 fill=(255, 255, 255, 40))

    f = font('segoeuib.ttf', int(min(w, h) * 0.22))
    bbox = draw.textbbox((0, 0), initials, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2 - int(h * 0.04)), initials, font=f, fill=WHITE)

    img.save(path, quality=88)


def dept_card(path, size, label, icon_char, c1, c2):
    img = gradient(size, c1, c2)
    draw = ImageDraw.Draw(img)
    w, h = size

    # icon circle
    r = int(min(w, h) * 0.16)
    cx, cy = w // 2, int(h * 0.42)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 230))

    f_icon = font('segoeui.ttf', int(r * 1.1))
    bbox = draw.textbbox((0, 0), icon_char, font=f_icon)
    iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - iw / 2, cy - ih / 2 - int(r * 0.1)), icon_char, font=f_icon, fill=c1)

    f_label = font('segoeuisl.ttf', int(min(w, h) * 0.09))
    bbox = draw.textbbox((0, 0), label, font=f_label)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((w / 2 - lw / 2, cy + r + int(h * 0.08)), label, font=f_label, fill=WHITE)

    img.save(path, quality=88)


def logo():
    size = (256, 256)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, 248, 248], radius=56, fill=NAVY)
    # medical cross
    bar_w = 44
    draw.rounded_rectangle([128 - bar_w / 2, 60, 128 + bar_w / 2, 196], radius=14, fill=GOLD)
    draw.rounded_rectangle([60, 128 - bar_w / 2, 196, 128 + bar_w / 2], radius=14, fill=GOLD)
    img.save(os.path.join(OUT_DIR, 'logo.png'))


def hero_doctor():
    size = (640, 760)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx = w // 2

    # backdrop blob
    draw.ellipse([cx - 260, 40, cx + 260, 560], fill=(13, 110, 253, 40))

    # body
    draw.rounded_rectangle([cx - 150, 380, cx + 150, 740], radius=90, fill=WHITE)
    draw.rounded_rectangle([cx - 150, 380, cx + 150, 740], radius=90, outline=BLUE, width=6)

    # head
    draw.ellipse([cx - 110, 120, cx + 110, 340], fill=(255, 219, 186))

    # hair
    draw.pieslice([cx - 110, 100, cx + 110, 300], 180, 360, fill=NAVY_DEEP)

    # stethoscope
    draw.arc([cx - 90, 360, cx + 90, 480], 0, 180, fill=(60, 60, 60), width=10)
    draw.ellipse([cx - 18, 460, cx + 18, 496], fill=(60, 60, 60))

    # collar / coat
    draw.polygon([(cx - 60, 380), (cx, 430), (cx + 60, 380), (cx + 30, 400), (cx, 380), (cx - 30, 400)], fill=BLUE_LIGHT)

    img.save(os.path.join(OUT_DIR, 'hero-doctor.png'))


def about_hospital():
    size = (1000, 700)
    img = gradient(size, NAVY, BLUE, diagonal=False)
    draw = ImageDraw.Draw(img)
    w, h = size

    # building
    bw, bh = 560, 380
    bx, by = (w - bw) // 2, h - bh - 80
    draw.rectangle([bx, by, bx + bw, by + bh], fill=WHITE)

    cols = 6
    rows = 5
    pad = 24
    cell_w = (bw - pad * (cols + 1)) / cols
    cell_h = (bh - pad * (rows + 1)) / rows
    for r in range(rows):
        for c in range(cols):
            x0 = bx + pad + c * (cell_w + pad)
            y0 = by + pad + r * (cell_h + pad)
            draw.rectangle([x0, y0, x0 + cell_w, y0 + cell_h], fill=BLUE_LIGHT)

    # entrance
    draw.rectangle([bx + bw / 2 - 60, by + bh - 90, bx + bw / 2 + 60, by + bh], fill=NAVY)

    # cross sign on roof
    draw.rounded_rectangle([bx + bw / 2 - 45, by - 70, bx + bw / 2 + 45, by - 10], radius=10, fill=GOLD)
    draw.rectangle([bx + bw / 2 - 8, by - 60, bx + bw / 2 + 8, by - 20], fill=NAVY)
    draw.rectangle([bx + bw / 2 - 28, by - 44, bx + bw / 2 + 28, by - 36], fill=NAVY)

    img.save(os.path.join(OUT_DIR, 'about-hospital.jpg'), quality=90)


DEPARTMENTS = [
    ('dept-cardiology.jpg', 'Cardiology', '\u2665', (185, 30, 60), (230, 80, 100)),
    ('dept-dental.jpg', 'Dental', '\u2039\u2022\u203a', (30, 130, 150), (80, 190, 200)),
    ('dept-dermatology.jpg', 'Dermatology', '\u2726', (150, 90, 40), (220, 150, 90)),
    ('dept-emergency.jpg', 'Emergency', '+', (200, 40, 40), (255, 90, 60)),
    ('dept-general-medicine.jpg', 'General Medicine', '\u2695', (13, 110, 253), (79, 156, 249)),
    ('dept-neurology.jpg', 'Neurology', '\u2733', (90, 40, 150), (150, 90, 220)),
    ('dept-ophthalmology.jpg', 'Ophthalmology', '\u25c9', (20, 120, 100), (60, 190, 160)),
    ('dept-orthopedics.jpg', 'Orthopedics', '\u2699', (150, 100, 20), (220, 160, 60)),
    ('dept-pediatrics.jpg', 'Pediatrics', '\u2605', (20, 140, 160), (100, 200, 210)),
]

DOCTORS = [
    ('doctor-1.jpg', 'SM', (13, 110, 253), (79, 156, 249)),   # Sarah Mitchell
    ('doctor-2.jpg', 'AR', (185, 30, 60), (230, 90, 100)),     # Arjun Rao
    ('doctor-3.jpg', 'JC', (90, 40, 150), (150, 90, 220)),     # James Carter
    ('doctor-4.jpg', 'MI', (20, 120, 100), (60, 190, 160)),    # Meera Iyer
    ('doctor-5.jpg', 'MR', (150, 100, 20), (220, 160, 60)),    # Michael Reyes
    ('doctor-6.jpg', 'KM', (150, 60, 20), (220, 120, 60)),     # Karan Malhotra
    ('doctor-7.jpg', 'EC', (20, 140, 160), (100, 200, 210)),   # Emily Chen
    ('doctor-8.jpg', 'LS', (150, 90, 40), (220, 150, 90)),     # Laura Simmons
]

PATIENTS = [
    ('patient-1.jpg', 'PT', (13, 110, 253), (79, 156, 249)),
    ('patient-2.jpg', 'PT', (90, 40, 150), (150, 90, 220)),
    ('patient-3.jpg', 'PT', (20, 140, 160), (100, 200, 210)),
]

logo()
hero_doctor()
about_hospital()

for filename, label, icon, c1, c2 in DEPARTMENTS:
    dept_card(os.path.join(OUT_DIR, filename), (500, 380), label, icon, c1, c2)

for filename, initials, c1, c2 in DOCTORS:
    person_avatar(os.path.join(OUT_DIR, filename), (400, 480), initials, c1, c2)

for filename, initials, c1, c2 in PATIENTS:
    person_avatar(os.path.join(OUT_DIR, filename), (400, 400), initials, c1, c2)

print('Generated', len(DEPARTMENTS) + len(DOCTORS) + len(PATIENTS) + 3, 'images in', OUT_DIR)
