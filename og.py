# -*- coding: utf-8 -*-
"""링크 미리보기 이미지(site/og.png)를 만든다.

카카오톡·슬랙·트위터는 og:image 가 없으면 썸네일 자리를 비워 둔다.
SVG 는 대부분 안 읽으므로 PNG 로 굽는다. 1200x630 은 공통 권장 크기다.

    python og.py

히어로의 고리 모티프와 담금질 산화색(--spectrum)을 그대로 쓴다.
"""
import os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1200, 630
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "og.png")
BG = (8, 9, 13)

# --spectrum 과 같은 정지점
STOPS = [(0.00, (255, 176, 32)), (0.18, (255, 138, 43)), (0.34, (255, 107, 53)),
         (0.54, (232, 70, 124)), (0.76, (168, 85, 247)), (1.00, (59, 158, 255))]

FONT_R = "C:/Windows/Fonts/malgun.ttf"
FONT_B = "C:/Windows/Fonts/malgunbd.ttf"


def spectrum(t):
    t = min(1.0, max(0.0, t))
    for i in range(len(STOPS) - 1):
        a, ca = STOPS[i]
        b, cb = STOPS[i + 1]
        if a <= t <= b:
            u = 0 if b == a else (t - a) / (b - a)
            return tuple(int(ca[j] + (cb[j] - ca[j]) * u) for j in range(3))
    return STOPS[-1][1]


def band(w, h, lo=0.0, hi=1.0):
    """가로 그러데이션 타일 — 글자·마크를 마스크로 뚫어 쓴다"""
    g = Image.new("RGB", (w, h))
    px = g.load()
    for x in range(w):
        c = spectrum(lo + (hi - lo) * (x / max(1, w - 1)))
        for y in range(h):
            px[x, y] = c
    return g


def glow(im, cx, cy, r, color, a):
    """뒤에 깔리는 빛무리"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (a,))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(r * 0.42)))


def particles(im):
    """히어로의 고리 — 점을 흩뿌려 그린다"""
    rnd = random.Random(7)
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy, R = 965, 312, 252

    def put(x, y, dim=1.0):
        if not (620 < x < W + 40 and -40 < y < H + 40):
            return
        rr = rnd.choice([1, 1, 1.5, 1.5, 2, 2, 2.5, 3, 3.5])
        t = (x - (cx - R)) / (2.0 * R)
        c = spectrum(min(0.78, max(0.0, t * 0.78)))
        a = int(rnd.uniform(70, 235) * dim)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c + (a,))

    for _ in range(1500):                       # 고리
        th = rnd.uniform(0, math.tau)
        j = rnd.gauss(0, 9.5)
        put(cx + (R + j) * math.cos(th), cy + (R + j) * math.sin(th))
    for _ in range(520):                        # 가로로 지나는 선
        x = rnd.uniform(cx - R - 26, cx + R + 26)
        put(x, cy + rnd.gauss(0, 8.5))
    for _ in range(300):                        # 흩어진 잔별
        put(rnd.uniform(640, W + 20), rnd.uniform(20, H - 20), 0.5)

    d2 = ImageDraw.Draw(im, "RGBA")             # 배경 별
    for _ in range(150):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        rr = rnd.choice([0.7, 0.9, 1.2])
        d2.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(244, 246, 250, rnd.randint(18, 70)))


def mark(im, x, y, size):
    """화로자리 — 크기 다른 별 셋을 옅은 선으로 잇는다"""
    S, ss = size / 24.0, 4          # 계단이 안 보이게 4배로 그린 뒤 줄인다
    m = Image.new("L", (int(size * ss), int(size * ss)), 0)
    dm = ImageDraw.Draw(m)
    P = [(11.60, 8.62, 4.06), (4.41, 16.74, 2.90), (19.96, 13.02, 2.44)]
    q = lambda i: (P[i][0] * S * ss, P[i][1] * S * ss)
    for a, b in ((1, 0), (0, 2)):
        dm.line([q(a), q(b)], fill=204, width=int(1.70 * S * ss))
    for px, py, pr in P:
        cx, cy, r = px * S * ss, py * S * ss, pr * S * ss
        dm.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    m = m.resize((int(size), int(size)), Image.LANCZOS)
    im.paste(band(int(size), int(size), 0.0, 0.85).convert("RGBA"), (x, y), m)


def spaced(d, xy, text, font, fill, extra):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + extra
    return x


def main():
    im = Image.new("RGBA", (W, H), BG + (255,))
    glow(im, 980, 300, 330, (255, 138, 43), 62)
    glow(im, 150, 590, 300, (232, 70, 124), 26)
    particles(im)

    d = ImageDraw.Draw(im)
    f_word = ImageFont.truetype(FONT_B, 40)
    f_lede = ImageFont.truetype(FONT_R, 52)
    f_head = ImageFont.truetype(FONT_B, 58)
    f_meta = ImageFont.truetype(FONT_R, 21)
    f_site = ImageFont.truetype(FONT_B, 24)

    mark(im, 78, 74, 44)
    spaced(d, (136, 78), "FORNAX", f_word, (244, 246, 250), 5)

    d.text((78, 192), "아이디어를", font=f_lede, fill=(150, 158, 176))
    d.text((78, 264), "출하 가능한 제품으로", font=f_head, fill=(244, 246, 250))

    # 마지막 줄만 담금질색으로 — 사이트 히어로와 같은 처리
    last = "벼립니다."
    wlast = int(d.textlength(last, font=f_head)) + 8
    mk = Image.new("L", (wlast, 84), 0)
    ImageDraw.Draw(mk).text((0, 0), last, font=f_head, fill=255)
    im.paste(band(wlast, 84, 0.02, 0.80).convert("RGBA"), (78, 346), mk)

    d.rectangle([78, 470, 258, 473], fill=(255, 176, 32))
    d.text((78, 496), "웹 · 모바일 · 인프라   ·   2주 스프린트   ·   소유권 전체 이관",
           font=f_meta, fill=(140, 148, 168))
    d.text((78, 542), "fornaxworks.com", font=f_site, fill=(255, 176, 32))

    im.convert("RGB").save(OUT, "PNG", optimize=True)
    print("og.png %d x %d · %.0fKB" % (W, H, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
