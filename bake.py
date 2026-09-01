# -*- coding: utf-8 -*-
"""페이지에 실제로 쓰인 글자만 골라 Pretendard 를 서브셋하고 파일 안에 넣는다.

    pip install fonttools brotli
    python bake.py                     # site 의 본문 페이지 전부
    python bake.py site/index.html     # 골라서

서브셋에 없는 글자는 시스템 폰트로 폴백돼 한 문장 안에서 서체가 섞인다.
그래서 **본문 글자를 바꾼 뒤에는 반드시 다시 구워야 한다.**
바꾼 페이지만 구우면 되고, 마지막에 빠진 한글이 0자인지 스스로 확인한다.

원본 woff2 는 이 파일 옆에 받아 둔다. 없으면 한 번만 내려받는다 —
저장소에 2MB 짜리 폰트 원본을 넣지 않으려는 것뿐이다.
"""
import io, os, sys, re, base64
from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "PretendardVariable.woff2")
URL  = ("https://github.com/orioncactus/pretendard/raw/main/"
        "packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2")

DEFAULT = ["site/index.html", "site/gallery.html", "site/privacy.html"]

PAT = re.compile(r"(src:url\((?:data:font/woff2;base64,)?)"
                 r"((?:__FONT_DATA__)|(?:[A-Za-z0-9+/=]+))(\))")

# 페이지에 안 쓰였더라도 넣어 두는 것 — 나중에 한 글자 때문에 다시 굽지 않도록
EXTRA  = set(" !\"#$%&'()*+,-./0123456789:;<=>?@"
             "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~")
EXTRA |= set("₩·—–…‘’“”×÷"
             "→←↑↓›‹●○▲▼✕✓▮")


def source():
    if not os.path.exists(SRC):
        import urllib.request
        print("Pretendard 원본을 받는 중…")
        urllib.request.urlretrieve(URL, SRC)
    return SRC


def bake(path):
    s = io.open(path, encoding="utf-8").read()
    m = PAT.search(s)
    if not m:
        sys.exit(path + ": @font-face 의 src:url 을 찾지 못했습니다")

    body  = s[:m.start()] + s[m.end():]          # 폰트 데이터 자신은 세지 않는다
    chars = {c for c in set(body) | EXTRA if c.isprintable() and ord(c) > 31}

    opt = subset.Options()
    opt.flavor = "woff2"
    opt.layout_features = ["*"]
    opt.drop_tables += ["DSIG"]
    opt.notdef_outline = True

    f  = TTFont(source())
    sb = subset.Subsetter(options=opt)
    sb.populate(text="".join(sorted(chars)))
    sb.subset(f)

    tmp = os.path.join(HERE, ".subset.woff2")
    f.flavor = "woff2"
    f.save(tmp)
    b64 = base64.b64encode(io.open(tmp, "rb").read()).decode("ascii")
    os.remove(tmp)

    s = s[:m.start()] + "src:url(data:font/woff2;base64," + b64 + ")" + s[m.end():]
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)

    han = len([c for c in chars if "가" <= c <= "힣"])
    print("%-14s 한글 %d자 · 파일 %dKB" % (os.path.basename(path), han,
                                          os.path.getsize(path) / 1024))


def verify(path):
    """구운 폰트로 이 페이지의 한글을 다 그릴 수 있는지 되짚는다"""
    s = io.open(path, encoding="utf-8").read()
    m = PAT.search(s)
    tmp = os.path.join(HERE, ".check.woff2")
    io.open(tmp, "wb").write(base64.b64decode(m.group(2)))
    cmap = set(TTFont(tmp).getBestCmap().keys())
    os.remove(tmp)

    body = s[:m.start()] + s[m.end():]
    miss = sorted({c for c in body if "가" <= c <= "힣" and ord(c) not in cmap})
    print("%-14s 빠진 한글 %d자 %s" % (os.path.basename(path), len(miss), "".join(miss[:24])))
    return len(miss)


if __name__ == "__main__":
    args = sys.argv[1:] or DEFAULT
    paths = [p if os.path.isabs(p) else os.path.join(HERE, p) for p in args]
    for p in paths:
        bake(p)
    bad = 0
    for p in paths:
        bad += verify(p)
    sys.exit(1 if bad else 0)
