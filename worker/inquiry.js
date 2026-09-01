/* ============================================================
   Fornax 문의 접수 — Cloudflare Worker

   GitHub Pages 는 파일을 내려줄 뿐 받아 주지 못한다.
   그래서 이 한 조각만 서버로 둔다. 하는 일은 셋뿐이다.
     1) 우리 사이트에서 온 요청인지 본다
     2) 봇이 아닌지 본다
     3) 메일로 넘긴다

   메일은 Email Routing 에 인증해 둔 주소로만 나간다.
   인증된 주소로 보내는 건 요금제와 무관하게 무료이고, 하루 한도에도
   안 들어간다. 그래서 이 구조를 골랐다.
   ============================================================ */

const TO      = "taeyang95@naver.com";        /* Email Routing 에서 인증한 주소 */
const FROM    = "form@fornaxworks.com";
const ORIGINS = ["https://fornaxworks.com", "https://www.fornaxworks.com"];

const MAX_FILES = 5;
const MAX_TOTAL = 18 * 1024 * 1024;   /* 메시지 한도 25MiB 아래로 여유를 둔다 */
const MIN_MS    = 3000;               /* 3초도 안 걸려 제출됐으면 사람이 쓴 게 아니다 */

const cors = (o) => ({
  "Access-Control-Allow-Origin": ORIGINS.indexOf(o) >= 0 ? o : ORIGINS[0],
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
});

const json = (body, status, o) =>
  new Response(JSON.stringify(body), {
    status,
    headers: Object.assign({ "Content-Type": "application/json; charset=utf-8" }, cors(o)),
  });

/* 보낸 사람이 쓴 글자를 그대로 HTML 에 넣지 않는다 */
const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (request.method !== "POST") return json({ ok: false, error: "POST 만 받습니다" }, 405, origin);

    /* 우리 사이트에서 온 것만 받는다. 열어 두면 남의 페이지에서 폼을 만들어 쏜다 */
    if (ORIGINS.indexOf(origin) < 0) return json({ ok: false, error: "허용되지 않은 출처입니다" }, 403, origin);

    let form;
    try {
      form = await request.formData();
    } catch (e) {
      return json({ ok: false, error: "본문을 읽지 못했습니다" }, 400, origin);
    }

    /* 사람에게는 안 보이는 칸. 채워져 있으면 봇이다.
       조용히 성공으로 돌려준다 — 막혔다는 걸 알려 주면 다음엔 피해서 온다 */
    if (String(form.get("company_website") || "").trim()) return json({ ok: true }, 200, origin);
    const elapsed = Number(form.get("elapsed") || 0);
    if (elapsed > 0 && elapsed < MIN_MS) return json({ ok: true }, 200, origin);

    const get = (k, max) => String(form.get(k) || "").trim().slice(0, max);
    const name = get("name", 80);
    const org = get("org", 120);
    const mail = get("mail", 160);
    const kind = get("kind", 60);
    const when = get("when", 60);
    const msg = get("msg", 8000);

    if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail) || msg.length < 10)
      return json({ ok: false, error: "필수 항목을 확인해 주세요" }, 400, origin);

    /* 첨부 */
    const attachments = [];
    let total = 0;
    for (const f of form.getAll("files")) {
      if (typeof f === "string" || !f || !f.name) continue;
      if (attachments.length >= MAX_FILES) break;
      total += f.size;
      if (total > MAX_TOTAL)
        return json({ ok: false, error: "첨부 용량이 큽니다. 합계 18MB 이하로 보내주세요" }, 413, origin);
      attachments.push({
        filename: f.name,
        type: f.type || "application/octet-stream",
        disposition: "attachment",
        content: await f.arrayBuffer(),
      });
    }

    const rows = [
      ["성함", name],
      ["회사 / 팀", org || "—"],
      ["회신 이메일", mail],
      ["만들려는 것", kind || "—"],
      ["희망 착수", when || "—"],
      ["첨부", attachments.length ? attachments.map((a) => a.filename).join(", ") : "없음"],
    ];

    const text = rows.map(([k, v]) => k + "\t" + v).join("\n") + "\n\n" + msg;
    const html =
      '<table style="border-collapse:collapse;font-family:system-ui,sans-serif;font-size:14px">' +
      rows
        .map(
          ([k, v]) =>
            '<tr><td style="padding:6px 16px 6px 0;color:#8b8681;white-space:nowrap">' +
            esc(k) +
            '</td><td style="padding:6px 0"><b>' +
            esc(v) +
            "</b></td></tr>"
        )
        .join("") +
      '</table><hr style="border:0;border-top:1px solid #e3e0d9;margin:18px 0">' +
      '<div style="font-family:system-ui,sans-serif;font-size:15px;line-height:1.85;white-space:pre-wrap">' +
      esc(msg) +
      "</div>";

    try {
      await env.EMAIL.send({
        to: TO,
        from: FROM,
        replyTo: mail,   /* 네이버에서 답장을 누르면 문의한 사람에게 바로 간다 */
        subject: "[문의] " + (org || name) + (kind ? " · " + kind : ""),
        text: text,
        html: html,
        attachments: attachments,
      });
    } catch (e) {
      return json({ ok: false, error: "보내지 못했습니다: " + ((e && e.message) || e) }, 502, origin);
    }

    return json({ ok: true }, 200, origin);
  },
};
