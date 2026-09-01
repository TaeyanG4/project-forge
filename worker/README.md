# 문의 접수 Worker

사이트는 GitHub Pages(정적 호스팅)라 폼을 받아 줄 데가 없습니다.
이 Worker 하나만 서버 역할을 합니다. 배포는 Cloudflare 계정에서 합니다 —
저장소 배포(GitHub Actions)와는 무관하고, `_public/` 에도 들어가지 않습니다.

## 왜 이 구조인가

Cloudflare Email Routing 에 **인증해 둔 주소**로 보내는 것은
요금제와 상관없이 무료이고, 월 할당량이나 하루 한도에도 들어가지 않습니다.
`taeyang95@naver.com` 이 이미 인증된 목적지라 조건이 맞습니다.

제3자 폼 서비스(Web3Forms · Formspree)를 쓰지 않는 이유도 같습니다 —
문의 내용이 남의 서버를 거치지 않습니다.

## 배포

1. Cloudflare 대시보드 → **Compute (Workers)** → **Create** → **Start with Hello World**
   - 이름: `fornax-inquiry`
2. 편집기에서 전체를 지우고 [`inquiry.js`](./inquiry.js) 를 붙여넣기 → **Deploy**
3. Worker → **Settings** → **Bindings** → **Add binding** → 메일 발송 바인딩
   - 변수 이름: `EMAIL` (코드가 `env.EMAIL` 로 씁니다)
4. 배포된 주소(`https://fornax-inquiry.<계정>.workers.dev`)를 사이트의
   `FORM_ENDPOINT` 에 넣습니다.

대시보드에 발송 바인딩이 안 보이면 wrangler 로 배포합니다:

```bash
npx wrangler deploy worker/inquiry.js --name fornax-inquiry --compatibility-date 2026-01-01
```

`wrangler.toml` 에 넣을 바인딩:

```toml
[[send_email]]
name = "EMAIL"
```

## 막아 둔 것

| 무엇 | 어떻게 |
|---|---|
| 남의 페이지에서 쏘는 요청 | `Origin` 이 fornaxworks.com 이 아니면 거절 |
| 봇 | 사람에게 안 보이는 칸(`company_website`)이 채워져 있으면 조용히 버림 |
| 자동 제출 | 폼을 연 지 3초 안에 제출되면 조용히 버림 |
| 긴 본문 | 항목마다 길이를 자름 (본문 8,000자) |
| 큰 첨부 | 5개 · 합계 18MB (메시지 한도 25MiB 아래) |

봇으로 판정한 요청에 실패를 돌려주지 않는 이유는, 막혔다는 걸 알려 주면
다음엔 피해서 오기 때문입니다.

## 답장

`replyTo` 에 문의한 사람의 주소를 넣습니다.
네이버 메일에서 **답장**을 누르면 그 사람에게 바로 갑니다.
