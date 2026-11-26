"""World Front Page - 26 November 2026.

Draws a magazine cover of Thursday 26 November 2026 with pure Python
standard library: its own rasterizer, bitmap font and PNG writer. No
network, no fonts, no dependencies. Writes entry.png to
$MAKEFUN_OUTPUT_DIR (default "out"). Deterministic: two runs write
identical bytes.
"""

import binascii
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs, '.' off, '#' on. Written for this cover.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


# ------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x0, x1, y, c):
        self.fill_rect(min(x0, x1), y, abs(x1 - x0) + 1, 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = math.isqrt(max(0, r * r - dy * dy))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, t, c):
        for dy in range(-r, r + 1):
            outer = math.isqrt(max(0, r * r - dy * dy))
            inner = math.isqrt(max(0, (r - t) * (r - t) - dy * dy)) if r - t > 0 else 0
            self.fill_rect(cx - outer, cy + dy, outer - inner, 1, c)
            self.fill_rect(cx + inner + 1, cy + dy, outer - inner, 1, c)

    def fill_ellipse(self, cx, cy, rx, ry, c):
        for dy in range(-ry, ry + 1):
            dx = int(rx * math.sqrt(max(0.0, 1.0 - (dy * dy) / float(ry * ry))))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def fill_triangle(self, p0, p1, p2, c):
        pts = sorted([p0, p1, p2], key=lambda p: p[1])
        (x0, y0), (x1, y1), (x2, y2) = pts
        if y2 == y0:
            return
        for y in range(max(0, y0), min(self.h, y2 + 1)):
            if y < y1:
                xa = x0 + (x1 - x0) * (y - y0) / float(y1 - y0) if y1 != y0 else x0
            else:
                xa = x1 + (x2 - x1) * (y - y1) / float(y2 - y1) if y2 != y1 else x1
            xb = x0 + (x2 - x0) * (y - y0) / float(y2 - y0)
            self.hline(int(min(xa, xb)), int(max(xa, xb)), y, c)

    def vgrad(self, x, y, w, h, top, bottom):
        for i in range(h):
            t = i / float(max(1, h - 1))
            c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
            self.fill_rect(x, y + i, w, 1, c)

    def vgrad3(self, x, y, w, h, top, mid, bottom):
        half = h // 2
        self.vgrad(x, y, w, half, top, mid)
        self.vgrad(x, y + half, w, h - half, mid, bottom)

    def glyph(self, x, y, ch, scale, c):
        g = FONT.get(ch)
        if g is None:
            return
        for row in range(7):
            line = g[row]
            for col in range(5):
                if line[col] == "#":
                    self.fill_rect(x + col * scale, y + row * scale, scale, scale, c)

    def text(self, x, y, s, scale, c, outline=None):
        if outline is not None:
            d = max(1, scale // 3)
            for ox, oy in ((-d, 0), (d, 0), (0, -d), (0, d)):
                cx = x + ox
                cy = y + oy
                for i, ch in enumerate(s):
                    self.glyph(cx + i * 6 * scale, cy, ch, scale, outline)
        for i, ch in enumerate(s):
            self.glyph(x + i * 6 * scale, y, ch, scale, c)

    def text_center(self, s, y, scale, c, x0, x1, outline=None):
        w = text_width(s, scale)
        self.text(x0 + (x1 - x0 - w) // 2, y, s, scale, c, outline)


# -------------------------------------------------------------- colors
NAVY = (13, 21, 36)
GOLD = (232, 169, 12)
WHITE = (245, 245, 240)
BLACK = (5, 5, 5)
INK = (10, 10, 12)


def flame(cv, cx, base_y, w, h):
    """Layered teardrop flame rising from base_y."""
    red = (198, 52, 12)
    orange = (232, 110, 14)
    yellow = (250, 196, 38)
    cv.fill_ellipse(cx, base_y - int(h * 0.30), w // 2, int(h * 0.32), red)
    cv.fill_triangle((cx - w // 2, base_y - int(h * 0.25)),
                     (cx + w // 2, base_y - int(h * 0.25)),
                     (cx, base_y - h), red)
    cv.fill_ellipse(cx, base_y - int(h * 0.22), int(w * 0.34), int(h * 0.24), orange)
    cv.fill_triangle((cx - int(w * 0.34), base_y - int(h * 0.18)),
                     (cx + int(w * 0.34), base_y - int(h * 0.18)),
                     (cx, base_y - int(h * 0.78)), orange)
    cv.fill_ellipse(cx, base_y - int(h * 0.14), int(w * 0.20), int(h * 0.15), yellow)
    cv.fill_triangle((cx - int(w * 0.20), base_y - int(h * 0.10)),
                     (cx + int(w * 0.20), base_y - int(h * 0.10)),
                     (cx, base_y - int(h * 0.55)), yellow)


def burst(cv, cx, cy, r):
    """Explosion starburst: radiating triangles plus hot core."""
    for k in range(8):
        ang = k * math.pi / 4.0
        tipx = cx + int(r * math.cos(ang))
        tipy = cy + int(r * math.sin(ang))
        px = cx + int(r * 0.45 * math.cos(ang + 0.35))
        py = cy + int(r * 0.45 * math.sin(ang + 0.35))
        qx = cx + int(r * 0.45 * math.cos(ang - 0.35))
        qy = cy + int(r * 0.45 * math.sin(ang - 0.35))
        cv.fill_triangle((tipx, tipy), (px, py), (qx, qy), (240, 120, 20))
    cv.fill_circle(cx, cy, int(r * 0.45), (250, 196, 38))
    cv.fill_circle(cx, cy, int(r * 0.22), (255, 240, 170))


def jet(cv, x, y, s, facing_right, c):
    """Small fighter-jet silhouette, nose pointing right or left."""
    d = 1 if facing_right else -1
    body = (x, y)
    nose = (x + d * 46 * s // 4, y)
    tail = (x - d * 20 * s // 4, y)
    cv.fill_triangle(nose, (x + d * 10 * s // 4, y - 4 * s // 4),
                     (x - d * 20 * s // 4, y - 2 * s // 4), c)
    cv.fill_triangle(nose, (x + d * 10 * s // 4, y + 4 * s // 4),
                     (x - d * 20 * s // 4, y + 2 * s // 4), c)
    cv.fill_triangle((x - d * 2 * s // 4, y - 2 * s // 4),
                     (x - d * 14 * s // 4, y - 18 * s // 4),
                     (x + d * 8 * s // 4, y - 2 * s // 4), c)
    cv.fill_triangle((x - d * 2 * s // 4, y + 2 * s // 4),
                     (x - d * 14 * s // 4, y + 18 * s // 4),
                     (x + d * 8 * s // 4, y + 2 * s // 4), c)
    cv.fill_triangle((x - d * 20 * s // 4, y - 2 * s // 4),
                     (x - d * 28 * s // 4, y - 12 * s // 4),
                     (x - d * 12 * s // 4, y - 2 * s // 4), c)
    cv.fill_triangle((x - d * 20 * s // 4, y + 2 * s // 4),
                     (x - d * 28 * s // 4, y + 12 * s // 4),
                     (x - d * 12 * s // 4, y + 2 * s // 4), c)
    del body, tail


# -------------------------------------------------------------- scenes
def draw_masthead(cv):
    cv.fill_rect(0, 0, W, 112, NAVY)
    cv.text_center("THE WORLD TODAY", 12, 8, WHITE, 0, W)
    cv.text_center("THURSDAY 26 NOVEMBER 2026", 78, 3, (232, 200, 106), 0, W)
    cv.fill_rect(0, 108, W, 4, GOLD)


def draw_cairo(cv):
    # Night sky over Cairo.
    cv.vgrad(0, 112, W, 360, (11, 16, 32), (42, 26, 32))
    stars = [(60, 140), (150, 180), (230, 130), (330, 165), (430, 135),
             (620, 150), (720, 130), (820, 175), (920, 140), (980, 200),
             (90, 230), (270, 210), (560, 200), (760, 230), (880, 260),
             (180, 290), (940, 320)]
    for sx, sy in stars:
        cv.set(sx, sy, (220, 220, 200))
        cv.set(sx + 1, sy, (160, 160, 150))
    # Distant skyline silhouettes.
    for bx, bw, bh in [(0, 120, 46), (150, 90, 70), (760, 110, 58),
                       (890, 134, 40)]:
        cv.fill_rect(bx, 470 - bh, bw, bh, (13, 17, 32))
    for wx, wy in [(170, 420), (195, 435), (800, 425), (830, 440),
                   (920, 440), (60, 440)]:
        cv.fill_rect(wx, wy, 5, 6, (240, 200, 90))
    # Fire glow behind the tanker.
    cv.fill_ellipse(512, 470, 430, 190, (122, 46, 13))
    cv.fill_ellipse(512, 470, 330, 140, (168, 62, 11))
    cv.fill_ellipse(512, 470, 220, 95, (217, 93, 15))
    # Road.
    cv.fill_rect(0, 470, W, 50, (28, 31, 36))
    for dx in range(20, W, 90):
        cv.fill_rect(dx, 494, 46, 4, (200, 170, 40))
    # Fuel tanker: red cab, silver tank, red stripe.
    cv.fill_rect(300, 398, 400, 66, (185, 190, 198))
    cv.fill_ellipse(300, 431, 12, 33, (185, 190, 198))
    cv.fill_ellipse(700, 431, 12, 33, (185, 190, 198))
    cv.fill_rect(300, 424, 400, 10, (150, 30, 22))
    cv.fill_rect(238, 414, 62, 50, (138, 47, 35))
    cv.fill_rect(246, 420, 34, 20, (26, 42, 58))
    for wx in (286, 420, 560, 668):
        cv.fill_circle(wx, 466, 17, (12, 12, 14))
        cv.fill_circle(wx, 466, 7, (120, 126, 134))
    # Flames rising from the tank.
    for fx, fw, fh in [(340, 74, 190), (430, 96, 240), (512, 110, 270),
                       (596, 92, 225), (676, 70, 175)]:
        flame(cv, fx, 404, fw, fh)
    # Smoke drifting up and right.
    smoke = [(352, 190, 30, (58, 58, 64)), (436, 168, 36, (66, 66, 72)),
             (524, 156, 38, (74, 74, 80)), (606, 172, 32, (58, 58, 64)),
             (682, 200, 26, (52, 52, 58)), (470, 160, 24, (82, 82, 88)),
             (580, 158, 22, (82, 82, 88))]
    for sx, sy, sr, sc in smoke:
        cv.fill_circle(sx, sy, sr, sc)
    # Emergency lights on the road.
    cv.fill_circle(150, 468, 26, (120, 20, 20))
    cv.fill_circle(150, 468, 12, (220, 40, 40))
    cv.fill_circle(884, 468, 26, (20, 40, 120))
    cv.fill_circle(884, 468, 12, (60, 110, 230))
    # Headline band.
    cv.fill_rect(0, 520, W, 120, INK)
    cv.fill_rect(0, 520, W, 3, GOLD)
    cv.text_center("CAIRO TANKER FIRE", 534, 7, WHITE, 0, W, outline=BLACK)
    cv.text_center("KILLS 30+ ON RING ROAD", 592, 5, (255, 196, 60), 0, W,
                   outline=BLACK)


def draw_tariffs(cv):
    cv.vgrad(0, 640, 512, 320, (15, 42, 51), (10, 30, 38))
    cv.text_center("US PLANS TARIFFS", 656, 4, WHITE, 0, 512, outline=BLACK)
    cv.text_center("ON 14 NATIONS", 692, 4, WHITE, 0, 512, outline=BLACK)
    cv.text_center("CHINA FACES THE HIGHEST RATES", 732, 2, (232, 200, 106),
                   0, 512)
    # Ground.
    cv.fill_rect(0, 920, 512, 40, (10, 20, 24))
    # Container stacks.
    cols = [(180, 85, 45), (200, 155, 60), (78, 122, 138), (107, 127, 94)]
    stacks = [(28, [0, 1]), (168, [2, 3, 0]), (308, [1, 2])]
    for sx, rows in stacks:
        for level, ci in enumerate(rows):
            by = 874 - level * 46
            cv.fill_rect(sx, by, 120, 46, cols[ci])
            cv.fill_rect(sx, by, 120, 3, (0, 0, 0))
            cv.fill_rect(sx, by + 43, 120, 3, (0, 0, 0))
            for vx in range(sx + 14, sx + 120, 16):
                cv.fill_rect(vx, by + 3, 2, 40, (0, 0, 0))
    # Red 25% stamp.
    cv.fill_circle(420, 806, 58, (185, 28, 28))
    cv.ring(420, 806, 58, 5, (245, 245, 240))
    cv.text_center("25%", 788, 5, WHITE, 362, 478, outline=(120, 10, 10))


def draw_ukraine(cv):
    cv.vgrad3(512, 640, 512, 320, (198, 90, 30), (90, 42, 74), (36, 20, 38))
    cv.text_center("5 RUSSIAN JETS", 656, 4, WHITE, 512, W, outline=BLACK)
    cv.text_center("HIT AT SAVASLEYKA", 692, 4, WHITE, 512, W, outline=BLACK)
    cv.text_center("KYIV: MIG-31S AND SU-34S DAMAGED", 732, 2, (245, 201, 107),
                   512, W)
    # Runway.
    cv.fill_rect(512, 900, 512, 60, (20, 16, 28))
    for dx in range(530, W, 80):
        cv.fill_rect(dx, 928, 40, 4, (230, 230, 220))
    # Intact jet on the runway.
    jet(cv, 640, 878, 5, True, (14, 11, 22))
    # Burning jet: flames, smoke and a burst.
    jet(cv, 880, 862, 4, False, (14, 11, 22))
    flame(cv, 880, 862, 90, 120)
    burst(cv, 952, 812, 34)
    burst(cv, 812, 800, 24)
    for sx, sy, sr in [(952, 792, 24), (1004, 808, 18), (898, 786, 16)]:
        cv.fill_circle(sx, sy, sr, (64, 58, 66))


def draw_footer(cv):
    cv.fill_rect(0, 960, W, 64, NAVY)
    cv.fill_rect(0, 960, W, 3, GOLD)
    cv.text_center("THE WORLD TODAY - 26 NOVEMBER 2026", 984, 3,
                   (232, 232, 228), 0, W)


# --------------------------------------------------------------- png
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    cv = Canvas(W, H)
    draw_masthead(cv)
    draw_cairo(cv)
    cv.fill_rect(0, 637, W, 3, GOLD)
    draw_tariffs(cv)
    draw_ukraine(cv)
    cv.fill_rect(511, 640, 2, 320, (232, 232, 228))
    draw_footer(cv)
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"), cv)


if __name__ == "__main__":
    main()
