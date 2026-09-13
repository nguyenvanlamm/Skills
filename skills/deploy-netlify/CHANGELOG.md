# Changelog

## v2.1.0 — 2026-09-13

### Fixed
- `--public` was documented but `deploy.sh` rejected it as "Unknown" — never reached `push-to-github.sh`. Now passed through.
- A fresh checkout with no `node_modules` failed the build with "vite: not found". `netlify-client.sh` now runs `npm ci` (lockfile) or `npm install` first.
- A stale `dist/` from an earlier run could be deployed if the new build silently produced nothing; the publish dir is removed before building and `index.html` must exist afterwards.
- `prepare-client.sh` overwrote a project's own `netlify.toml` (custom headers, functions, publish dir) with the template. It now keeps the file and only appends the SPA redirect if missing.
- `.env.production` was replaced wholesale, dropping any other `VITE_*` the app needed. Now only the `VITE_API_URL` line is replaced.
- Site name and env value were interpolated into JSON by string concatenation; now built with `jq -n --arg`.
- `docs/README.md` said `npm install -g netlify-cli` was required (it is not — `npx --yes`), showed an output shape without `verified`, and claimed `VITE_API_URL` is "set on Netlify env" (it is baked in at local build time).

### Added
- `--skip-github`: deploy without touching GitHub.
- Early prerequisite check in `deploy.sh` (`gh` included unless `--skip-github`), `package.json`/`build` script validation, `--api-url` scheme validation — all **before** step 1.
- Publish directory read from `netlify.toml → publish` so a custom `build.outDir` works.
- Verification retries 4× (5 s apart) and requires an HTML body, not just a 200 — a 200 on an empty publish dir is not a working site.

### Breaking Changes
- None. Existing invocations behave the same, minus the bugs above.

## v2.0.0
- Verify URL returns 200, global slug collision handling, env-var semantics explained.
