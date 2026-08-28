"""편집기를 띄우고, 버튼 하나로 커밋·푸시까지 한다.

    python publish.py

브라우저는 보안상 스스로 git 을 돌릴 수 없다. 그래서 아주 작은 서버를 하나
띄워 두고, 편집기가 여기에 '공개해 달라'고 부탁하는 구조로 만들었다.

무엇을 조심했나
  - 127.0.0.1 에만 귀를 연다. 같은 공유기에 있는 다른 기기도 닿지 못한다.
  - 켤 때마다 임시 열쇠를 만들어 편집기에만 심는다. 브라우저에 열려 있는
    다른 사이트가 몰래 이 서버를 두드려도 열쇠가 없어 거절된다.
  - Origin 도 함께 본다.
  - 받는 것은 커밋 메시지 한 줄뿐이다. 아무 명령이나 대신 실행해 주지 않는다.
"""
import http.server, socketserver, subprocess, secrets, json, os, sys, webbrowser
import urllib.parse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PORT = 8787
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOKEN = secrets.token_urlsafe(24)
OK_ORIGINS = {"http://127.0.0.1:%d" % PORT, "http://localhost:%d" % PORT}


def git(*args):
    """저장소 안에서 git 을 돌리고 (성공여부, 출력) 을 돌려준다."""
    p = subprocess.run(("git",) + args, cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode == 0, ((p.stdout or "") + (p.stderr or "")).strip()


def changed():
    """바뀐 파일 목록. status --porcelain 은 앞 두 칸이 상태이고 세 번째부터 경로다.
       출력을 strip 하면 첫 줄의 앞 공백이 날아가 경로가 한 글자 잘리므로 여기서 따로 읽는다."""
    p = subprocess.run(("git", "status", "--porcelain"), cwd=REPO, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return None
    return [l[3:].strip() for l in p.stdout.splitlines() if len(l) > 3]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            sys.stderr.write("  %s\n" % (fmt % args))

    # 편집기에만 열쇠를 심어 내보낸다
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/ping":
            return self.reply(200, {"ok": True})
        if path == "/api/status":
            if self.headers.get("X-Forge-Token") != TOKEN:
                return self.reply(403, {"error": "열쇠가 맞지 않습니다."})
            files = changed()
            ok2, br = git("rev-parse", "--abbrev-ref", "HEAD")
            return self.reply(200, {"ok": files is not None, "files": files or [],
                                    "branch": br if ok2 else "?"})
        if path in ("/admin.html", "/admin"):
            return self.serve_admin()
        return super().do_GET()

    def serve_admin(self):
        f = os.path.join(HERE, "admin.html")
        if not os.path.exists(f):
            return self.reply(404, {"error": "admin.html 이 없습니다"})
        html = open(f, encoding="utf-8").read()
        tag = '<meta name="forge-publish-token" content="%s">\n' % TOKEN
        html = html.replace("<head>", "<head>\n" + tag, 1)
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/publish":
            return self.reply(404, {"error": "그런 길은 없습니다"})

        if self.headers.get("X-Forge-Token") != TOKEN:
            return self.reply(403, {"error": "열쇠가 맞지 않습니다. 편집기를 "
                                             "http://127.0.0.1:%d/admin.html 로 다시 여세요." % PORT})
        origin = self.headers.get("Origin")
        if origin and origin not in OK_ORIGINS:
            return self.reply(403, {"error": "다른 곳에서 온 요청입니다: %s" % origin})

        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            payload = {}
        msg = str(payload.get("message") or "").strip() or "견본 등록"
        msg = msg.replace("\r", " ").replace("\n", " ")[:120]

        return self.reply(200, publish(msg))

    def reply(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if self.headers.get("Origin") in OK_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Forge-Token")
        self.end_headers()
        self.wfile.write(body)


def publish(msg):
    files = changed()
    if files is None:
        return {"ok": False, "step": "status", "log": "git status 에 실패했습니다."}
    if not files:
        return {"ok": True, "nothing": True, "log": "바뀐 것이 없습니다."}

    log = ["바뀐 파일 %d개" % len(files)] + ["  " + c for c in files[:12]]

    for step, args in (("add", ("add", "-A")),
                       ("commit", ("commit", "-m", msg)),
                       ("push", ("push",))):
        ok, out = git(*args)
        log.append("$ git %s" % step)
        if out:
            log.append(out)
        if not ok:
            return {"ok": False, "step": step, "log": "\n".join(log)}

    return {"ok": True, "log": "\n".join(log)}


if __name__ == "__main__":
    ok, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not ok:
        sys.exit("git 저장소가 아닙니다: %s" % REPO)

    url = "http://127.0.0.1:%d/admin.html" % PORT
    print("FORGE 편집기")
    print("  저장소   %s  (%s)" % (REPO, branch))
    print("  주소     %s" % url)
    print("  열쇠     이 창을 닫으면 사라집니다. 편집기는 위 주소로만 여세요.")
    print("  끄기     Ctrl+C")
    print()

    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as srv:
            try:
                webbrowser.open(url)
            except Exception:
                pass
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\n껐습니다.")
    except OSError as e:
        sys.exit("포트 %d 를 열지 못했습니다: %s" % (PORT, e))
