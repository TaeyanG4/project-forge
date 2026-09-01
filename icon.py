# -*- coding: utf-8 -*-
"""프로필 아이콘을 굽는다 (brand/).

    python icon.py

카카오톡 채널·깃허브·노션 같은 데 올릴 정사각 이미지다. 이런 곳은 대부분
원형으로 잘라 보여 주므로, 별 셋이 **가운데 원 안에** 다 들어가도록
배율을 계산해서 앉힌다 — 모서리로 삐져나가면 잘린다.

favicon·헤더 로고와 같은 그림이다. 화로자리 — 크기가 다른 별 셋을
옅은 선으로 이은 것.
"""
import os, math, random
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "brand")

# 24 단위 좌표. index.html 의 마스크와 같은 값이다
STARS = [(11.60, 8.62, 4.06), (4.41, 16.74, 2.90), (19.96, 13.02, 2.44)]
LINKS = [(1, 0), (0, 2)]
LINE_W, LINE_OP = 0.78, 0.32   # 큰 크기에선 실처럼, 40px 에선 셋이 이어져 보일 만큼
                               # (헤더 로고보다 가늘다 — 28px 에서 곱던 굵기가 1024px 에선 막대가 된다)

DARK  = [(0.00, (255, 176, 32)), (0.18, (255, 138, 43)), (0.34, (255, 107, 53)),
         (0.54, (232, 70, 124)), (0.76, (168, 85, 247)), (1.00, (59, 158, 255))]
LIGHT = [(0.00, (166, 96, 0)),   (0.18, (163, 78, 20)),  (0.34, (176, 67, 42)),
         (0.54, (163, 35, 85)),  (0.76, (107, 41, 168)), (1.00, (26, 95, 168))]

SAFE = 0.33      # 원형으로 잘려도 남는 반지름 (캔버스 폭 대비)
SS   = 4         # 계단이 안 보이게 4배로 그린 뒤 줄인다


def ramp(stops, t):
    t = min(1.0, max(0.0, t))
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        if a <= t <= b:
            u = 0 if b == a else (t - a) / (b - a)
            return tuple(int(ca[j] + (cb[j] - ca[j]) * u) for j in range(3))
    return stops[-1][1]


def band(w, h, stops, lo=0.0, hi=1.0):
    g = Image.new("RGB", (w, h))
    px = g.load()
    for x in range(w):
        c = ramp(stops, lo + (hi - lo) * (x / max(1, w - 1)))
        for y in range(h):
            px[x, y] = c
    return g


def fit(size):
    """별의 반지름까지 넣어, 안전 원 안에 딱 차도록 배율과 중심을 낸다"""
    cx = sum(x for x, _, _ in STARS) / 3.0     # 배치용 임시 기준
    bx0 = min(x - r for x, _, r in STARS); bx1 = max(x + r for x, _, r in STARS)
    by0 = min(y - r for _, y, r in STARS); by1 = max(y + r for _, y, r in STARS)
    mx, my = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
    reach = max(math.hypot(x - mx, y - my) + r for x, y, r in STARS)
    k = (SAFE * size) / reach
    return k, mx, my


def mark_mask(size):
    """별자리를 알파 마스크로 그린다. 색은 나중에 그러데이션으로 통과시킨다"""
    k, mx, my = fit(size)
    m = Image.new("L", (size * SS, size * SS), 0)
    d = ImageDraw.Draw(m)
    put = lambda i: ((STARS[i][0] - mx) * k * SS + size * SS / 2,
                     (STARS[i][1] - my) * k * SS + size * SS / 2)
    for a, b in LINKS:
        d.line([put(a), put(b)], fill=int(255 * LINE_OP), width=int(LINE_W * k * SS))
    for i, (_, _, r) in enumerate(STARS):
        x, y = put(i); rr = r * k * SS
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    return m.resize((size, size), Image.LANCZOS)


def haze(im, stops, size):
    """별빛 번짐. 이게 없으면 큰 크기에서 그냥 동그라미 세 개로 읽힌다"""
    lay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    lay.paste(band(size, size, stops, 0.02, 0.92).convert("RGBA"), (0, 0), mark_mask(size))
    lay = lay.filter(ImageFilter.GaussianBlur(size * 0.035))
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.55)))
    im.alpha_composite(lay)


def stars_bg(im, seed, color, n=110):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        r = rnd.uniform(0.0010, 0.0022) * w
        d.ellipse([x - r, y - r, x + r, y + r], fill=color + (rnd.randint(16, 62),))


def glow(im, color, a=70):
    w, h = im.size
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    r = w * 0.36
    ImageDraw.Draw(lay).ellipse([w/2 - r, h/2 - r*0.92, w/2 + r, h/2 + r*0.92], fill=color + (a,))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(w * 0.16)))


def tile(size, bg, stops, glowc, starc=None, night=True):
    """night=False 는 밝은 판. 밝은 하늘엔 별이 안 보이므로 별밭도 번짐도 넣지 않는다 —
       넣으면 먼지와 얼룩처럼 읽힌다."""
    im = Image.new("RGBA", (size, size), bg + (255,))
    glow(im, glowc, 44 if night else 26)
    if night:
        stars_bg(im, 11, starc, 92)
        haze(im, stops, size)
    im.paste(band(size, size, stops, 0.02, 0.92).convert("RGBA"), (0, 0), mark_mask(size))
    return im.convert("RGB")


def clear(size, stops):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    im.paste(band(size, size, stops, 0.02, 0.92).convert("RGBA"), (0, 0), mark_mask(size))
    return im


def main():
    if not os.path.isdir(OUT):
        os.mkdir(OUT)
    made = []

    for n in (1024, 640):                       # 640 은 카카오톡 채널 권장 크기
        p = os.path.join(OUT, "profile-dark-%d.png" % n)
        tile(n, (11, 12, 16), DARK, (255, 138, 43), (244, 246, 250)).save(p, "PNG", optimize=True)
        made.append(p)

    p = os.path.join(OUT, "profile-light-1024.png")
    tile(1024, (247, 246, 243), LIGHT, (255, 176, 32), night=False).save(p, "PNG", optimize=True)
    made.append(p)

    p = os.path.join(OUT, "mark-1024.png")      # 배경 없이 마크만
    clear(1024, DARK).save(p, "PNG", optimize=True)
    made.append(p)

    for p in made:
        print("%-28s %dKB" % (os.path.basename(p), os.path.getsize(p) / 1024))


if __name__ == "__main__":
    main()
