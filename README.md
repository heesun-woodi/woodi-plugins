# woodi-plugins

Claude Code plugins by [@heesun-woodi](https://github.com/heesun-woodi).

## Plugins

| Plugin | Purpose |
|---|---|
| [`product-mockup`](./plugins/product-mockup/) | Turn one flat product design file into lifestyle mockup photos. An AI image model renders the room; the original artwork is then perspective-warped onto the product face, so small type stays pixel-exact instead of being hallucinated. Ships four sub-agents that keep generation and judgment in separate contexts. Requires a Gemini API key and a local Python env. |

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
