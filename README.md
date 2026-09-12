# woodi-plugins

Claude Code plugins by [@heesun-woodi](https://github.com/heesun-woodi).

## Plugins

| Plugin | Purpose |
|---|---|
| [`product-mockup`](./plugins/product-mockup/) | Turn one flat product design file into lifestyle mockup photos. An AI image model renders the room; the original artwork is then perspective-warped onto the product face, so small type stays pixel-exact instead of being hallucinated. Ships four sub-agents that keep generation and judgment in separate contexts. Requires a Gemini API key and a local Python env. |
| [`cro-hypothesis-backlog`](./plugins/cro-hypothesis-backlog/) | 문제정의 리스트를 입력받아 솔루션 아이데이션(BIAS 전술 매핑) → PSR 가설 조립 → 1차(잠정) ICE 합산 → 가설 백로그 v1을 만드는 CRO 코칭 플러그인. 해빗팩토리 CRO 코칭 전용. |
| [`ecommerce-growth-discovery`](./plugins/ecommerce-growth-discovery/) | 자기 GA4·Meta 광고 계정을 MCP로 연결해 우리 몰의 baseline·전환율·트래픽·채널 효율을 직접 조회하고, 화면의 문제를 정리해 PSR 가설까지 만드는 이커머스 그로스 디스커버리 코칭 플러그인. 스킬 4종(`setup`·`explore`·`screen`·`psr`)과 GA4·Meta MCP 두 서버를 번들합니다. 고객 데이터는 들어 있지 않고, 속성 ID·기간·매출 지표는 작업 폴더의 `growth-discovery.config.json`에서 읽습니다. 필요: uv, gcloud + ADC. |

## Install

In a Claude Code session:

```
/plugin marketplace add heesun-woodi/woodi-plugins
/plugin install product-mockup@woodi-plugins
/reload-plugins
```

This repository is public, so nothing needs to be granted first.

After installing, the plugin's namespaced surfaces become available:

- command: `/product-mockup:product-mockup`
- skill (auto-triggers): `product-mockup:product-mockup`
- agents: `product-mockup:mockup-scene-designer`, `:mockup-verifier`, `:mockup-compositor`, `:mockup-reviewer`

Each plugin's own README covers its environment variables and setup.

## Why `product-mockup` exists

Asking an image model to hang your product on a wall works right up until the
product has text on it. In the run this plugin was built from, every generated
scene came back with the small type corrupted — weekday headers turned into
glyphs that only look like Korean, and the model invented a phone number that
would have been printed on a live listing. A second round with tighter prompts
fixed the artwork and the grid structure and left the small type exactly as
broken.

So the plugin splits the job. The image model does what it is good at — light,
space, props, shadow — and the product face is replaced with the original file
afterward. Text does not get a vote.
