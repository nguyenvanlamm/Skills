# Website Analyzer — logic reference

Implemented by `scripts/analyze-website.py` (stdlib, one HTTP fetch). Read this when you need to understand or debug what it extracted; run the script rather than doing these steps by hand.

## Extraction order

| Field | Order | Recorded in `source.*` |
|-------|-------|------------------------|
| `name` | `og:site_name` → `application-name` → JSON-LD `Organization/Brand/WebSite.name` → `<title>` (split on ` | - – — : ·`, first part) → header `<img alt*=logo>` → domain | `name_from` |
| `logo_url` | `apple-touch-icon` (largest `sizes`) → `link[rel=icon]` (largest) → `msapplication-TileImage` → `<img>` inside `<header>/<nav>` whose class/id/alt/src contains `logo`/`brand` | `logo_from` (with px) |
| `cover_url` | `og:image` → `twitter:image` | `cover_from` |
| `colors.primary` | CSS custom property `--primary|--brand|--color-primary|--brand-color|--accent` → `<meta name=theme-color>` (if hex) | `color_from` |
| `favicon_url` | first `rel*=icon` → `/favicon.ico` | — |

Relative URLs are resolved against the final URL after redirects. Anything not found is `null` and listed in `missing[]`. `spa_hint` is set when the HTML has no `<img>` and no `og:image` — a client-rendered site whose assets must be supplied with `--logo-url`.

## Output

`<output-dir>/brand-info.json` — see SKILL.md § Output.

## Edge cases

- Non-UTF-8 pages: decoded with the declared charset, errors replaced.
- `<title>` with a tagline ("Acme — Ship faster") → `Acme`.
- Multiple icons → the largest declared `sizes` wins; `sizes="any"` (SVG) counts as 0 and loses to a sized PNG.
- Fetch failure → exit 1 with `{"error": …}`; the orchestrator stops.
