# Releases

## v1.13.0

Homepage search bar gets a hero variant, matching the sister literature
site's `.lit-search--hero` proportions: roughly double the regular input
height (96px), 2rem typography, a larger pill button, and the same
viewport-aware shrink at 768px / 480px breakpoints. The goal is the same
as on the literature side — make search the obvious primary action when
a visitor lands on the dataset list.

- **`datasetapp/templates/datasetapp/base.html`** — add a
  `.dataset-search--hero` modifier with hero-sized padding, 2rem font,
  `--radius-lg` corners, `--shadow` elevation, and a matching submit
  button (96px min-height, 140px min-width). Tablet (≤768px) drops to a
  ~h3-sized 60px row; phone (≤480px) drops to a touchable 48px row
  without stacking. The base `.dataset-search` stays unchanged for any
  future non-hero use.
- **`datasetapp/templates/datasetapp/all_datasets.html`** — apply the
  hero modifier (`class="dataset-search dataset-search--hero"`) on the
  homepage form so the bigger sizing only kicks in on the main visitor
  entry point.

Pure CSS + a single class addition; no model / view / URL changes.

## v1.12.0

Visual refresh: swap the teal palette for the sister literature site's
"Oxford navy" palette, and bring the dataset detail page's navigation in
line with literature's design — a single top-of-page topbar with three
chip buttons (Previous / Back to home / Next) on a 1fr-auto-1fr grid, so
the centre "home" chip stays anchored even when prev or next is missing.

- **`datasetapp/templates/datasetapp/base.html`** — replace the teal
  light- and dark-mode `--color-*` tokens with the literature site's
  Oxford navy values (`#1f4e7a` / `#7ea2c4` accent), retarget
  `--chart-line` and `--chart-area` to the same navy, and restyle
  `.detail-topbar` from a single text link into a three-column chip
  grid (`.detail-topbar__btn` chips in `--color-accent-soft`, hover to
  `--color-accent`, plus a `.detail-topbar__spacer` cell for when one
  side is absent so "home" stays centred). The legacy bottom `.detail-nav`
  block is removed — prev/next have moved up into the topbar.
- **`datasetapp/templates/datasetapp/dataset_info.html`** — top-of-page
  topbar now renders three chips (Previous / Back to home / Next), with
  `__spacer` placeholders when `prev_dataset` / `next_dataset` are
  missing. Bottom `<nav class="detail-nav">` is removed.

No behaviour, URL, model, or view changes — purely visual + template
markup. Tag chips, search bar, download CTA, sparkline, share button,
quickstart copy button, and table styling all pick up the new accent
through existing CSS variable references.

## v1.11.0

Dataset detail page (`/info/<slug>`) now has a **Share** button next to
the dataset title — pill-styled like the existing quickstart `Copy`
button, with a share-graph icon. Clicking it invokes the browser's
native share sheet via the [Web Share
API](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share)
on supporting platforms (iOS Safari, Android Chrome, recent desktop
Safari/Edge), so visitors can hand off the dataset URL to Messages /
Mail / WhatsApp / etc. in one tap. On browsers without `navigator.share`
(most desktop Chrome/Firefox), it falls back to copying the URL to the
clipboard and flashes a "Copied" confirmation on the button for 1.5s.

- **`datasetapp/views.py`** — `about_dataset` now also exports
  `share_url` into the template context, computed via
  `request.build_absolute_uri(reverse(...))` so it picks up the same
  scheme + host the visitor is already on (works for both `openmv.net`
  and `test.openmv.net` without configuration).
- **`datasetapp/templates/datasetapp/dataset_info.html`** — the
  bare `<h3>{{ ds.name }}</h3>` is wrapped in a flex `.detail-title`
  container with the new `<button class="share-btn">` to its right; the
  button carries the canonical URL on `data-share-url`. A small inline
  `<script>` wires up the click handler: `navigator.share` first, then
  `navigator.clipboard.writeText`, and finally a textarea+execCommand
  fallback for the long tail. `AbortError` from `navigator.share` (user
  dismissed the OS sheet) deliberately does **not** fall back to copy
  — that would surprise the user.
- **`datasetapp/templates/datasetapp/base.html`** — `.detail-title`
  / `.share-btn` styles added alongside the existing `.code-copy-btn`
  rules. The button reuses the project's `--color-accent-soft` /
  `is-copied` palette, so the "Copied" feedback matches the rest of
  the detail page in both light and dark themes.
- **`datasetapp/tests/test_views.py`** — new
  `test_about_renders_share_button_with_absolute_url` asserts the
  detail page rendering carries a `.share-btn` element with the
  absolute URL on `data-share-url` and the dataset name on
  `data-share-title`. Existing detail-page tests still pass (24 / 24
  green locally with `SECRET_KEY=… uv run pytest`).
- **`pyproject.toml`** / **`RELEASES.md`**: MINOR bump (additive
  user-visible feature, no URL / schema / template-structure break),
  per the policy in `CLAUDE.md`.

## v1.10.1

Documentation: rename the off-host backup S3 bucket from `openmv-backups`
to `kgd-backups` in docs and the `bin/backup-openmv.sh` header comment,
reflecting the actual shared-bucket name used in production. The bucket
itself was renamed when the live backup setup was wired up on the Hetzner
host on 2026-05-10; this PR brings the docs in sync. The script reads
the bucket name from `$BACKUP_S3_BUCKET` in `.env`, so no runtime / CI /
template / dependency change.

- **`docs/backup.md`** — every reference to `openmv-backups` (intro
  paragraph, S3 layout block, IAM policy ARNs in 1b, `.env` example
  block, verify / restore commands, real-disaster-recovery commands,
  troubleshooting) updated to `kgd-backups`. Part 1's bucket-creation
  section also gains a "skip if already created for literature" note
  that mirrors the symmetric pattern in the literature stack's runbook
  (`kgdunn/Django-app-Literature-database` `docs/backup.md`).
- **`CLAUDE.md`** — Backups-section `BACKUP_S3_BUCKET=` example
  updated, and a sentence added noting the bucket is shared with the
  literature stack via prefix isolation (so a leak in either stack's
  IAM credentials cannot reach the other's data).
- **`bin/backup-openmv.sh`** — header comment example for
  `BACKUP_S3_BUCKET` updated. Runtime behaviour unchanged; the script
  reads the bucket name from `.env`.
- **`pyproject.toml`** / **`RELEASES.md`**: PATCH bump (docs +
  comment, no user-visible behaviour change), per the policy in
  `CLAUDE.md`.
- The matching docs rename in the literature stack
  (`kgdunn/Django-app-Literature-database`) shipped as a sibling PR
  on the same branch name (#101 there, merged 2026-05-10).

## v1.10.0

Detail-page download counter now reads `<N> downloads since <Mon YYYY>`,
where the suffix is the month and year of the earliest `Hit` recorded
for the dataset. The clause is omitted entirely when the dataset has
never been downloaded — the counter just shows `0 downloads`.

- **`datasetapp/views.py`** — `about_dataset` adds a `first_hit_at`
  to the template context, sourced from the earliest
  `Hit.date_and_time` filtered by the whole dataset (across every
  associated `DataFile`, not just the first one). The query is one
  extra row read per detail-page request — no aggregate, just an
  `ORDER BY date_and_time LIMIT 1` against the existing
  `(dataset_hit, date_and_time)` shape — so it doesn't need its own
  cache layer the way the sparkline does.
- **`datasetapp/templates/datasetapp/dataset_info.html`** —
  `download-meta` paragraph appends `since {{ first_hit_at|date:"M Y" }}`
  via Django's date filter when `first_hit_at` is truthy. No CSS or
  layout change.
- **`datasetapp/tests/test_views.py`** — adds two regressions:
  `test_about_renders_download_meta_with_first_hit_month` (earliest
  of two backdated hits drives the suffix) and
  `test_about_omits_since_clause_when_no_hits` (no hits → no
  `since` text).
- **`pyproject.toml`** / **`RELEASES.md`**: MINOR bump per the policy
  in `CLAUDE.md` (additive change to a public-facing widget; no URL
  or template-structure break).

## v1.9.1

Follow-up to v1.9.0: the sparkline now plots the **total** number of
downloads in each week, instead of the average daily download count
(`weekly_count / 7`). Same seven-year window and weekly buckets — only
the y-axis units change. Issue #104 follow-up.

- **`datasetapp/views.py`** — `_download_series` no longer divides
  the per-week count by 7; emits `[yyyy-mm-dd, total]` integer
  pairs. Cache key bumped to
  `download_series:<pk>:weekly_total:<weeks>` so any v1.9.0 entry
  still warm in `django_cache_table` after deploy can't deliver the
  old fractional values.
- **`datasetapp/templates/datasetapp/dataset_info.html`** — tooltip
  reverts to `Week of <Monday> / <N> download(s)` (singular when
  `N === 1`), matching the integer values.
- **`datasetapp/tests/test_views.py`**,
  **`datasetapp/tests/test_security.py`** — assertions updated to
  the integer-total shape (sum of values equals the number of `Hit`
  rows recorded in the current week).
- **`CLAUDE.md`** — Project shape entry now describes the sparkline
  as "total weekly download count" with the v1.9.1 attribution.
- **`pyproject.toml`** / **`RELEASES.md`**: PATCH bump (units-only
  refinement of an existing visible widget; no URL or
  template-structure change), per the policy in `CLAUDE.md`.

## v1.9.0

Detail-page sparkline now spans seven years and smooths the noise out
by switching from per-day download counts to per-week averages of the
daily download count (issue #104).

- **`datasetapp/views.py`** — `_download_series` aggregates `Hit` rows
  with `TruncWeek("date_and_time")` (instead of `TruncDate`), keeps a
  rolling window of `7 * 52` weekly buckets anchored on Monday, and
  emits `[yyyy-mm-dd, avg_per_day]` pairs (`weekly_count / 7`,
  rounded to 4 dp). The cache key was renamed to
  `download_series:<pk>:weekly:<weeks>` so the new shape can't collide
  with any pre-bump cached entry that's still warm in
  `django_cache_table` after deploy.
- **`datasetapp/templates/datasetapp/dataset_info.html`** — tooltip
  now reads `Week of <Monday>` / `<value>.toFixed(2) downloads/day`,
  matching the new bucket semantics. ECharts category x-axis still
  hides labels, so the visible sparkline shape is unchanged apart
  from being smoother and longer.
- **`datasetapp/tests/test_views.py`** —
  `test_about_includes_download_series_for_sparkline` updated to assert
  the new shape (`len == 7 * 52`, sum of values ≈ `1 / 7` for one
  recorded `Hit`).
- **`CLAUDE.md`** — Project shape / Templates entries refreshed to
  describe the seven-year weekly sparkline rather than the old
  365-day daily one.
- **`pyproject.toml`** / **`RELEASES.md`**: MINOR bump per the policy
  in `CLAUDE.md` (visible behaviour change to a public-facing widget,
  no URL or template-structure break).

## v1.8.3

Documentation: capture the on-disk volume implications of the
v1.8.2 compose project-name pin, plus the migration playbook used
to move the live Postgres data from the old project's volume to
the new one.

- **`CLAUDE.md`** — "Production deployment" section gets a new
  bullet calling out `name: openmv` and the resulting volume name
  (`openmv_openmv_postgres_data`); the Gotchas list gets a new
  entry #11 with the full migration shape (stop/rm without `-v`,
  `docker volume create`, `docker run --rm -v old:/from:ro
  -v new:/to alpine cp -a /from/. /to/`, then bring the new stack
  up). Bind mounts (`data/media`, `data/static`, `data/public`)
  are explicitly noted as project-rename-immune because they're
  addressed by host path.
- The 2026-05-09 migration (`repo_openmv_postgres_data` →
  `openmv_openmv_postgres_data`) is documented inline as a
  worked example of when the playbook is needed.
- **`pyproject.toml`** / **`RELEASES.md`**: PATCH bump (docs only,
  no runtime / CI / template / dependency change), per the policy
  in `CLAUDE.md`.
- The matching deploy-doc update on the literature side
  (`kgdunn/Django-app-Literature-database`) lives in
  `docs/deploy.md` under the new "Compose project name and
  on-disk volumes" section, with a cross-reference to this
  migration as the worked example.

## v1.8.2

Operational fix: pin the compose project name so the openmv stack
isn't accidentally torn down by sibling stacks on the same Hetzner VPS.

The literature.learnche.org stack lives at
`/home/deploy/literature/repo/` and the openmv stack lives at
`/home/deploy/openmv/repo/` — both checkout directories end in `repo/`,
so without an explicit `name:` key in the compose files Compose
defaults the project name to the parent directory's basename and
both stacks resolve to project=`repo`. That made
`docker compose -f docker-compose.prod.yml down` in *either* repo
remove the *other* stack's containers (`openmv-app` +
`openmv-postgres` were observed disappearing while operating on the
literature stack).

- **`docker-compose.yml`**, **`docker-compose.prod.yml`**: add a
  top-level `name: openmv` directive (with a comment explaining the
  collision the directive prevents). Scopes every Compose
  invocation in this repo to the openmv project.
- The companion fix lives in
  `kgdunn/Django-app-Literature-database` (`name: literature` in its
  two compose files); the two PRs together fully decouple the
  stacks' teardown scopes.
- No runtime behaviour change, no schema change, no template change
  — `docker compose ps`, `up`, `down`, `restart` all keep working
  with the existing service names (`web`, `db`) and container
  names (`openmv-app`, `openmv-postgres`).
- **`pyproject.toml`** / **`RELEASES.md`**: PATCH bump (operational
  hygiene, no user-visible change), per the policy in `CLAUDE.md`.

## v1.8.1

Supply-chain hardening for issues #79 (Issue J) and #77 (Issue H) —
every third-party GitHub Action and Docker base image is now pinned by
immutable identifier (40-char commit SHA / `@sha256:` digest) instead of
a floating tag the upstream owner can re-point. No runtime behaviour
change, no schema change, no template change.

- **`.github/workflows/ci.yml`**: `actions/checkout@v4` →
  `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1`;
  `astral-sh/setup-uv@v6` →
  `astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e  # v6.8.0`.
  The `TODO(security): swap the floating tags below for full commit
  SHAs` block is removed (the work it described is now done) and
  replaced with a one-paragraph rationale comment pointing at
  Dependabot. The Postgres service container's `image: postgres:16-alpine`
  is digest-pinned to the same SHA used in `docker-compose.prod.yml` so
  CI's database byte-matches prod's.
- **`.github/workflows/release.yml`**: `actions/checkout@v4` pinned to
  the same SHA / version comment as in `ci.yml`.
- **`.github/workflows/deploy.yml`**: unchanged — uses zero third-party
  actions (only an SSH session to a forced-command key).
- **`Dockerfile`**: both stages of the multi-stage build pinned to
  `python:3.11-slim@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2`
  (the multi-arch manifest list digest, so amd64 / arm64 / arm builds
  all resolve from the same parent). Comment styled after the existing
  `ghcr.io/astral-sh/uv:0.8.17` rationale on line 8.
- **`docker-compose.prod.yml`**: `postgres:16-alpine@sha256:4e6e670bb069649261c9c18031f0aded7bb249a5b6664ddec29c013a89310d50`.
- **`.github/dependabot.yml`** (new): two ecosystems on a weekly
  schedule — `github-actions` (covers Issue J / `ci.yml`+`release.yml`)
  and `docker` (covers Issue H / `Dockerfile` + `docker-compose.prod.yml`).
  Dependabot will open bump PRs as new SHAs / digests appear; CI
  catches breakage before merge.
- **`docs/SECURITY.md`**: finding 11 row updated from "Partially fixed
  in v1.5.0" to "Fixed in v1.8.1"; Issue H and Issue J each gain a
  `**Status:** **Fixed in v1.8.1** — …` entry mirroring the Issue I /
  Issue K format already in the file.
- **`pyproject.toml`** / **`RELEASES.md`**: PATCH bump (supply-chain
  hygiene, no user-visible change), per the policy in `CLAUDE.md`.

## v1.8.0

Adds a homepage free-text search bar (issue #94). The homepage view
(`/`) now honours an optional `?q=<terms>` query string and filters the
dataset table by substring across six fields: dataset `name`,
`description`, `data_source`, `author_name`, plus tag `name` and
`description`. Whitespace splits the query into tokens that must all
match (each token may match in any of the six fields). Empty or missing
`q` returns the full table — pre-existing URLs and behaviour are
unchanged.

- **`datasetapp/views.py`**: `display_all` now reads `request.GET["q"]`,
  builds a `Q` expression that ANDs whitespace tokens, ORed across the
  six text fields with `icontains`, and applies `.distinct()` before
  `_annotate_with_downloads` so the `Count(distinct=True)` aggregate
  sees a deduped row set. `icontains` was chosen deliberately over
  Postgres FTS (`SearchVector` / trigram) so SQLite dev, Postgres CI,
  and Postgres prod stay in lock-step — the catalogue is small enough
  that the cost is negligible. The query is silently truncated to
  100 characters and 8 tokens to bound the worst case.
- **`datasetapp/templates/datasetapp/all_datasets.html`**: renders a
  `<form method="get" role="search">` with an `<input name="q">` and a
  Submit button above the homepage intro paragraph; when a search is
  active, also renders an "N results for …" summary, a "Clear" link
  back to `/`, and a "No datasets matched" empty state when there are
  no hits. The search bar is scoped to the homepage only — tag pages
  (`/tag/<slug>`) are unchanged.
- **`datasetapp/templates/datasetapp/base.html`**: small inline CSS
  block for `.dataset-search`, `.dataset-search__summary`,
  `.dataset-search__empty`, `.dataset-search__clear`, and
  `.visually-hidden`, reusing the existing `--sp-*` / `--color-*` /
  `--fs-*` variables. No new static file, no new dependency, no CSP
  edits required (the CSP already allows a same-origin GET form).
- **`datasetapp/tests/test_views.py`**: added six tests covering
  substring match on `name`, on `description`, via a tag name, the
  no-results empty state, a `.distinct()` regression guard for a
  dataset whose two tags both match the query (mirrors
  `test_tag_view_does_not_double_count_downloads`), and the intro
  paragraph still rendering when no search is active.
- **CLAUDE.md**: updated the `display_all` bullet under "Project
  shape → Views" to mention the optional `?q=` search and the fields
  covered.
- No schema, migration, URL, settings, or admin changes — read path
  only. Without `?q=` the homepage queryset, ordering, and download
  annotation are byte-identical to v1.7.1.

## v1.7.1

Docs-only patch for issue #95 — the v1.6.4 origin-side fix for
`HTTPError: HTTP Error 403: Forbidden` on
`pandas.read_csv("https://openmv.net/file/<slug>.csv")` was necessary
but not sufficient: Cloudflare's Bot Fight Mode (BFM) continued to 403
the `Python-urllib/*` User-Agent from AWS / GitHub Actions ASNs even
after `/file/*` stopped redirecting through `/media/*`. The actual cure
turned out to be two pure-Cloudflare configuration changes (no code
change, no client-side workaround needed). This release records what is
now configured on the production zone.

- **`docs/SECURITY.md`**: rewrote the "Bot Fight Mode and dataset
  downloads" subsection to document the production configuration:
  (1) BFM is **off** site-wide on the Free plan because BFM cannot be
  skipped per-path by WAF Custom Rules or Configuration Rules on Free
  — the "Skip" action only exempts **Super** BFM (Pro+); (2) a
  Configuration Rule on `URI Path starts_with /file/` sets Browser
  Integrity Check to Off. Added the `curl -A 'Python-urllib/3.12'`
  verification command, the trade-offs of turning BFM off, and the
  caveat that an edge Cache Rule on `/file/*` would under-count the
  per-dataset `Hit` counter. Removed the previous (incorrect)
  recommendation to use a WAF Custom Rule with
  `Skip → "Bot Fight Mode"` on Free, and qualified the
  `/admin/*` recommendations to no longer suggest enabling BFM.
- No code, dependency, settings, CI, or deploy script changes — this
  is a documentation-only release that records the operational state
  of the Cloudflare zone after issue #95 was resolved.

## v1.7.0

Feature for issue #92 — the homepage table (and the per-tag filter view at
`/tag/<slug>`) now includes a sortable **Downloads** column showing the
all-time number of downloads per dataset. The count is the same value the
detail page already exposes (one row per `Hit`), so visitors can sort the
catalogue by popularity without leaving the index. Scoped to the desktop
layout per the issue; the mobile card view hides the column to avoid
crowding cards that already condense Rows/Cols inline.

- **`datasetapp/views.py`**: new `_annotate_with_downloads(queryset)`
  helper that adds a `num_downloads=Count("datafile__hit", distinct=True)`
  annotation. `display_all` and `display_by_tag` route their queryset
  through it before handing the list to the template. `distinct=True` is
  required because `display_by_tag` filters via the `tags` M2M, and a
  multi-tag match would otherwise multiply the Hit count by the number of
  matching tags.
- **`datasetapp/templates/datasetapp/all_datasets.html`**: new `<col
  class="col-downloads">`, new sortable `<th>` with
  `data-sort-key="downloads" data-sort-type="number"`, new `<td
  class="dataset-downloads">` rendering `dataset.num_downloads|default:0`
  with the same `data-sort-value` shape the existing JS sorter expects.
- **`datasetapp/templates/datasetapp/base.html`**: column widths
  rebalanced to fit the new column (Name 17%, Rows 8%, Cols 9%, Downloads
  11%, Tags 24%); `.dataset-downloads` cells inherit the right-aligned
  monospaced styling already used by `.dataset-rows` / `.dataset-cols`.
  Inside the `@media (max-width: 767px)` block,
  `.dataset-table tbody td.dataset-downloads` is set to `display: none`
  so the mobile card layout is unchanged.
- **`datasetapp/tests/test_views.py`**: new
  `test_home_renders_downloads_column_with_per_dataset_counts` asserts
  the column markers and the per-dataset count surface in the homepage
  HTML; new `test_tag_view_does_not_double_count_downloads` locks the
  `distinct=True` requirement against regressions where the M2M tag join
  silently multiplies the Hit count.

## v1.6.4

Bugfix for issue #86 — `pandas.read_csv("https://openmv.net/file/<slug>.csv")`
and any other `urllib`-based client returned `HTTPError: HTTP Error 403:
Forbidden`. The cause was the public download flow doing a 302 from `/file/*`
to `/media/datasets/...`: every download was evaluated by Cloudflare's Bot
Fight Mode twice, on two different paths, and the redirect target on
`/media/*` was the one getting blocked for non-browser User-Agents. The
public download view now streams the file body directly instead of
redirecting, so there is only one Cloudflare-visible round-trip and the
`/media/*` surface is no longer exposed to legitimate Python clients at all.

- **`datasetapp/views.py`**: `download_dataset` now returns
  `FileResponse(file_obj.link_to_file.open("rb"), as_attachment=True,
  filename=file_name)` instead of `HttpResponseRedirect(...)`. All upstream
  validation (`_DOWNLOAD_FILENAME_RE`, slug + file-type lookup, `Hit`
  increment, 404 paths) is unchanged. `FileResponse` from `django.http`
  added to the imports; `HttpResponseRedirect` is kept for the
  unknown-slug branch in `about_dataset`. Browsers see
  `Content-Disposition: attachment; filename="<slug>.<ext>"`; Django
  infers `Content-Type` from the filename suffix via the stdlib
  `mimetypes` module, so CSV / XLS / XLSX / XML / MAT all map correctly.
- **`datasetapp/tests/test_views.py`**: `csv_file` fixture now writes the
  CSV to a real `tmp_path/datasets/iris.csv` and overrides
  `settings.MEDIA_ROOT` so `FileResponse` has bytes to stream. Existing
  download test renamed to
  `test_download_known_file_streams_bytes_and_increments_hits` and now
  asserts `200`, the `Content-Disposition` header, and the response body
  bytes (in addition to the `Hit` count). New
  `test_download_malformed_filename_returns_404_without_hit` locks the
  pre-DB-lookup regex check so a hostile `/file/NOT-A-SLUG` still returns
  404 and does not record a hit.
- **`docs/SECURITY.md`**: new "Bot Fight Mode and dataset downloads"
  subsection under the Cloudflare guidance, recording why the redirect
  was the problem and pre-staging the WAF "Skip" rule for `/file/*` if
  Bot Fight Mode ever starts blocking that path too.
- **`CLAUDE.md`**: Views section + Gotcha #2 updated to describe the
  streaming flow and the test-fixture requirement (real bytes under
  `MEDIA_ROOT`).

## v1.6.3

Bugfix for v1.5.0's bleach allowlist: `<img>` was not on the list, so any
image an admin had embedded in `Dataset.description` or `Dataset.data_source`
disappeared from the detail page after the security-hardening release. The
allowlist now permits `<img>` with a tightly scoped attribute set, so legacy
dataset figures render again without re-opening the XSS hole that finding 1
in `docs/SECURITY.md` closed.

- **`datasetapp/templatetags/extra_tags.py`**: `"img"` added to
  `_ALLOWED_TAGS`; `_ALLOWED_ATTRS["img"]` set to
  `["src", "alt", "title", "width", "height"]`. Event-handler attributes
  (`onerror`, `onload`, …) are not on the list, so bleach drops them; `src`
  values are filtered against `_ALLOWED_PROTOCOLS` (`http`, `https`,
  `mailto`), so `javascript:` URLs are rejected. The CSP `img-src 'self'
  data:` in `openmv/middleware.py` is unchanged — same-origin `/media/...`
  references are what admins use in practice.
- **`datasetapp/tests/test_security.py`**: new
  `test_sanitise_markup_strips_event_handlers_from_img` pins the
  attribute-stripping contract; `test_sanitise_markup_preserves_allowed_tags`
  parametrised with a benign `<img src="/media/datasets/foo.png" alt="…">`
  case; `test_detail_page_does_not_render_admin_supplied_script` updated to
  expect `<img` to survive but `onerror` / `onload` / `javascript:` to be
  stripped (the original assertion that *no* `<img` survived is what locked
  the regression in).
- **`docs/SECURITY.md`**: finding 1's "Fixed in v1.5.0" cell amended with a
  pointer to the v1.6.3 follow-up.

## v1.6.2

Defence-in-depth follow-up to v1.5.0's CDN pinning. Adds Subresource
Integrity (SRI) `sha384` hashes to the two `<script>` tags that load
ECharts and MathJax from `cdn.jsdelivr.net`, so a tampered or substituted
CDN response is refused by the browser. Closes Issue K in
`docs/SECURITY.md` (and the SRI half of finding 10).

- **`datasetapp/templates/datasetapp/base.html`**: ECharts `<script>`
  gets `integrity="sha384-Mx5lkUEQPM1pOJCwFtUICyX45KNojXbkWdYhkKUKsbv391mavbfoAmONbzkgYPzR"`.
  Comment block above the tag is updated — the old "add this once the
  maintainer has network access" TODO is gone, replaced with a one-liner
  pointing readers at `make sri` if the pinned version ever changes.
- **`datasetapp/templates/datasetapp/dataset_info.html`**: MathJax
  `<script>` gets `integrity="sha384-vi9R4hb1goLJPJDHY+dOmXxcY3HGv6tJIwHxy5JunOTxJGHbsSuubPgl++SNxYYi"`.
  The comment notes that the hash is over `MathJax.js`'s bytes and that
  the `?config=TeX-AMS-MML_HTMLorMML` query string is ignored by jsDelivr
  for static files (so SRI still matches).
- **`docs/SECURITY.md`**: Issue K marked **Fixed in v1.6.2**; finding 10
  closed for the CDN-script half. Vendoring (Issue D / #72) remains the
  fuller fix and is still open.
- The `make sri` target in `Makefile` (added in v1.5.0) is unchanged —
  it remains the canonical way to recompute hashes if either CDN script
  is ever bumped to a new patch version.

## v1.6.1

Operational follow-up to v1.5.0's audit. Adds a Docker liveness probe so a
half-broken container (gunicorn workers blocked on a slow query, OOM-killed,
etc.) flips to `(unhealthy)` and `restart: unless-stopped` can recycle it.
Closes Issue I in `docs/SECURITY.md`.

- **`datasetapp/views.py`**: new `healthz(request)` view, decorated with
  `@never_cache`, returning `HttpResponse("ok\n", content_type="text/plain")`.
  No DB, no template, no auth — pure liveness signal.
- **`datasetapp/urls.py`**: wired at `/healthz` (reverse name
  `datasetapp:healthz`). Mounted at the top of the patterns; outside `/admin/`
  so any future Caddy or Cloudflare admin rate-limit doesn't touch it.
- **`Dockerfile`**: runtime stage installs `curl` (alongside `libpq5`) and
  adds `HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3
  CMD curl -fsS http://127.0.0.1:8000/healthz`. The `-f` flag is required so
  a 5xx still fails the check.
- **`datasetapp/tests/test_views.py`**: three smoke tests pin the contract —
  200 + `ok\n` + `text/plain`, `Cache-Control: no-cache, no-store, max-age=0`
  (proves `@never_cache` is applied), and no `Hit` row written (proves the
  view doesn't accidentally exercise the download codepath).
- **`docs/SECURITY.md`**: Issue I marked **Fixed in v1.6.1**.

## v1.6.0

Sortable columns on the homepage / tag-filter table (issue #81). Click any
column header (Name, Description, Rows, Columns, Tags) to sort ascending;
click again to flip to descending. The active column shows an up/down
arrow; the others are unsorted.

- **`datasetapp/templates/datasetapp/all_datasets.html`**: header `<td>`s
  promoted to `<th scope="col">` wrapping a `<button class="col-sort">`,
  body cells annotated with `data-sort-key` + `data-sort-value` (lower-cased
  text for textual columns, raw integers for `Rows` / `Columns`, joined tag
  names for the tag column). Inline script reorders `<tr>` elements in
  place — no network calls, no re-render of the row body, and tag links
  stay clickable. Default order on load is the server-side `slug`
  ordering, marked `aria-sort="ascending"` on the Name column.
- **`datasetapp/templates/datasetapp/base.html`**: CSS for the new
  `.col-sort` button (full-width hit target, hover affordance) and the
  up/down/unsorted arrow indicator driven by `aria-sort` (mask-image SVG,
  inherits `currentColor` so it tracks light / dark theme).

Behaviour-preserving for visitors with JavaScript disabled: the table
still renders in the existing slug order and column header text remains
visible — only the click-to-sort affordance is lost.

## v1.5.1

Documentation-only follow-up to v1.4.0's S3 backup work. No code changes.

- **`docs/backup.md`**: new end-to-end backup runbook for a future
  maintainer. Covers AWS bucket creation, IAM user + scoped policy,
  access-key generation, the Hetzner-side AWS CLI v2 install, `.env`
  population, smoke-test, S3 verification, cron install, nightly run
  verification, restore drill, full disaster recovery, and a
  troubleshooting block.
- **CLAUDE.md** *Backups → Host prerequisite*: the previous `sudo apt
  install awscli` line was wrong on Ubuntu 24.04 (the `awscli` apt
  package was dropped). Replaced with `sudo snap install aws-cli
  --classic` (the supported v2 path on Ubuntu 24.04) and a cross-link
  to `docs/backup.md` for the full runbook.

## v1.5.0

Security audit and hardening pass. Behaviour-preserving for normal visitors;
removes a stored-XSS surface, two reliability cliffs in the public download
path, and adds browser-side defence-in-depth headers. Full audit record in
`docs/SECURITY.md`.

### Highlights

- **Stored XSS removed** — `dataset_info.html` no longer applies `|safe` to
  admin-authored `name`, `description`, or `data_source`. A new
  `sanitise_markup` template filter (`datasetapp/templatetags/extra_tags.py`)
  passes the two text fields through `bleach` with a small tag/attribute
  allowlist (`a, b, i, em, strong, sub, sup, code, br, p, span, ul, ol, li,
  dl, dt, dd`); LaTeX in `\(...\)` still renders via MathJax. The contradictory
  `|safe|escape` chain on `special_message` is removed entirely — the
  homepage intro markup is now inlined in `all_datasets.html`.
- **`download_dataset` reliability** — input is now validated against
  `^[a-z0-9-]+\.[a-z]{3}$` before any DB lookup, so requests like
  `/file/foo`, `/file/foo.bar.csv`, or `/file/.csv` return 404 instead of
  raising `ValueError → 500`. `split(".")` was replaced with `rsplit(".", 1)`.
- **CSV preview ReDoS removed** — `_csv_preview` no longer calls
  `csv.Sniffer().sniff(...)`, which had catastrophic-backtracking behaviour
  on adversarial input and was reachable from any visitor hitting a detail
  page. The default `csv.excel` dialect is used unconditionally.
- **`_download_series` cached** — the 365-day per-dataset aggregation is
  now cached for one hour via `django.core.cache`, removing the
  unbounded-scan-per-request future-DoS as the `Hit` table grows.
- **File upload validation** — `DataFile.link_to_file` gains a
  `FileExtensionValidator(["csv","xls","xlsx","xml","mat"])`, and
  `DataFile.clean()` rejects mismatches between the declared `file_type`
  and the actual extension. Stops an admin from uploading `.html` masquerading
  as `.csv`.
- **Admin tightened** — `list_per_page` reduced from 2000 to 100 on all
  three admins. `HitAdmin` gains `readonly_fields = ("dataset_hit",
  "date_and_time")` (audit log, append-only), plus `date_hierarchy` +
  `list_filter` so scoping doesn't require loading the whole table.
- **Security headers** — new `openmv.middleware.SecurityHeadersMiddleware`
  emits `Content-Security-Policy`, `Permissions-Policy`, and
  `Cross-Origin-Opener-Policy: same-origin`. The CSP keeps `'unsafe-inline'`
  for `script-src` / `style-src` because `base.html` and `dataset_info.html`
  inline both today; externalising those is the follow-up that lets us drop
  the relaxation.
- **Cookie flags** — `prod.py` now explicitly sets
  `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE = "Lax"`,
  `CSRF_COOKIE_HTTPONLY`, `CSRF_COOKIE_SAMESITE = "Lax"`. Matches Django
  defaults but is now documented and immune to upstream default changes.
- **Upload limits** — `base.py` adds `DATA_UPLOAD_MAX_MEMORY_SIZE`,
  `FILE_UPLOAD_MAX_MEMORY_SIZE` (both 5 MiB), and `FILE_UPLOAD_PERMISSIONS = 0o644`.
- **CDN scripts pinned** — MathJax `2.7.9` and ECharts `5.5.1` instead of
  the floating `mathjax@2` / `echarts@5`. SRI hashes can be added with
  `make sri` once a network-connected maintainer runs it (the templates
  ship with `crossorigin="anonymous"` already in place).
- **Supply chain** — `Dockerfile` pins `ghcr.io/astral-sh/uv` to `0.8.17`
  instead of `:latest`. `ci.yml` adds `permissions: contents: read` and a
  non-blocking `pip-audit` step. `pyproject.toml` adds lower bounds to the
  three previously unpinned runtime deps and adds `pip-audit` to the dev
  group.
- **Tests** — new `datasetapp/tests/test_security.py` pins each finding so
  future refactors can't quietly re-open them: bleach allowlist behaviour,
  detail-page rendering, `download_dataset` 404 paths, `DataFile.clean`,
  `_csv_preview` error path, security-header presence, cache behaviour,
  removed `special_message` context.
- **Docs** — `docs/SECURITY.md` is now the canonical security record:
  full audit table (severity, file:line, status), host-side recommendations
  (Caddy admin rate-limit, Cloudflare WAF, fail2ban), and the vulnerability
  reporting paragraph. Top-level `SECURITY.md` points GitHub's "Security"
  tab at it. CLAUDE.md updated to match.

### Operational notes

- **SRI hashes are pending**: `make sri` prints the values to insert into
  the two CDN `<script>` tags. Documented as a one-line follow-up edit.
- **GitHub Actions are still tag-pinned** (`@v4`, `@v6`); SHA-pinning is
  documented as a follow-up issue (`docs/SECURITY.md` issue J).
- **HSTS preload** is intentionally not flipped on yet — the staged
  rollout in `prod.py`'s comment still applies.

## v1.4.0

Off-host backups to AWS S3 — closes #49 and replaces the frozen Linode
`backup-datasets.sh` cron that had been backing up a stale copy since the
2026-05-03 Hetzner cutover.

### Highlights

- **`bin/backup-openmv.sh`** (#49): a single host-side bash script that
  runs nightly under `deploy` from cron. On every invocation it:
  - dumps Postgres via `docker compose exec -T db pg_dump --clean
    --if-exists`, gzips the result, and uploads it to
    `s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/db/daily/db_openmv-YYYY-MM-DD.sql.gz`;
  - promotes the same dump to `db/monthly/db_openmv-YYYY-MM.sql.gz` on the
    1st of each month and to `db/yearly/db_openmv-YYYY.sql.gz` on Jan 1
    via a server-side `aws s3 cp` (no second `pg_dump`);
  - mirrors `data/media/` and `data/public/` to the matching S3 prefixes
    via `aws s3 sync` *without* `--delete`, so an accidental local rm or a
    detached bind-mount doesn't propagate to the off-host copy;
  - prunes `db/daily/` to the 15 most recent objects and `db/monthly/` to
    the 12 most recent, by S3 `LastModified`. `db/yearly/` is never pruned.
  Replaces the old `manage.py dumpdata`-based script — `pg_dump` is faster
  on the ~300k-row `Hit` table and round-trips cleanly across Django
  versions.
- **AWS S3, deliberately not Hetzner Object Storage**: the destination
  sits in a different cloud account from the production VPS so a
  compromise of one doesn't reach the other.
- **`data/static/` is intentionally skipped**: `collectstatic` regenerates
  it on every container start, so it has nothing worth preserving.
- **`.env.example`**: five new commented-out keys
  (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`,
  `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX`). The script sources the same
  `.env` the prod stack uses, so secrets stay in one place.
- **CLAUDE.md** gains a `## Backups` section (S3 layout, IAM scope, host
  `awscli` install, cron entry, restore commands) and a new Gotcha (#7)
  documenting the deliberate `data/static/` skip.

The cron entry itself is **not** auto-installed — it lives outside the
repo as operational state, documented in CLAUDE.md so the next maintainer
knows where to put it. No visitor-visible behaviour change.

## v1.3.0

Privacy fix for the `Hit` table — closes #17 and clears the last
remaining D-batch item in the modernization roadmap (#42).

### Highlights

- **Hit schema trimmed** (#17): `datasetapp.models.Hit` no longer stores
  `UA_string`, `IP_address`, or `referrer`. The table is now
  `(id, dataset_hit_id, date_and_time)` — exactly the columns the public
  site uses to render the per-dataset download counter and the 365-day
  sparkline (`_download_series` in `datasetapp/views.py` groups rows by
  `TruncDate("date_and_time")`). The `download_dataset` view writes one
  row per download via `Hit(dataset_hit=file_obj).save()`; the unused
  `get_IP_address` helper was removed.
- **Migration `0002_drop_hit_pii`** runs three `RemoveField` ops on the
  `Hit` model. On any database that pre-dates this release, applying the
  migration drops the columns and destroys all legacy IP / UA / referrer
  values in one step — there is no separate retention job because the
  schema itself no longer holds PII.
- **Admin tightened** (`datasetapp/admin.py`): `HitAdmin.list_display`
  and `list_filter` only reference the surviving columns. Admin users no
  longer see PII because the database no longer holds any.
- **Tests**: `Hit.objects.create(...)` calls in
  `datasetapp/tests/test_views.py` updated to the trimmed schema; the
  365-day sparkline assertion (`sum(point[1] for point in series) == 1`)
  still passes against the new model.
- **CLAUDE.md** + **README.md**: the "Models" line and the README
  bullet now describe the privacy posture of the `Hit` table; a Gotcha
  documents the migration as the place legacy PII gets dropped.

No visitor-visible behaviour change — both the count and the sparkline
render identically. Download history is preserved indefinitely; only the
PII columns go away.

## v1.2.0

Django bumped from 4.2 LTS to 5.2 LTS, closing the E1 item on the
modernization roadmap (#42). Django 4.2 LTS reaches EOL in April 2026;
5.2 LTS (released April 2025) is the current LTS series and keeps the
project on the same LTS-only cadence.

### Highlights

- **Django 5.2 LTS** (#35): `pyproject.toml` pin moved from `>=4.2,<5.0`
  to `>=5.2,<5.3`; `uv.lock` refreshed (django 4.2.30 → 5.2.13). The
  smoke test suite (`datasetapp/tests/test_views.py`) passes unchanged
  against 5.2; `manage.py check` and `manage.py check --deploy` report
  no new warnings beyond the pre-existing `SECURE_HSTS_PRELOAD=False`
  (deliberate staged HSTS rollout from C3). No code changes were needed
  — the pre-flight audit found no usage of the APIs Django 5.x removed
  (`USE_L10N`, `django.utils.timezone.utc`, `index_together`, etc.).
- **CLAUDE.md**: the "Tooling" section now reflects the new pin and notes
  the bump rationale; the "Outstanding work" referent (#35) is now closed.

## v1.1.1

Documentation cleanup: bring `README.md`, `CLAUDE.md`, and the
`docker-compose.prod.yml` comments back into sync with the production stack.

- `README.md`: the production-notes paragraph still claimed "the live site
  has Apache serving `/static/` and `/media/` directly" and that "in
  production Apache must be configured to intercept `/media/`" — both stale
  since the May 2026 Hetzner cutover, when host-installed Caddy took over
  TLS, static files, and `/media/` from Apache on Linode. Updated to refer
  to Caddy and to the `data/static/` + `data/media/` bind mounts; also
  corrected the dev-server condition from the legacy `DJANGO_DEBUG=1` to
  the actual `DEBUG=True`.
- `CLAUDE.md` + `docker-compose.prod.yml`: rewrote the `.env` bind-mount
  paragraph and the matching compose comment. Both still implied the
  bind-mount was required because `openmv/settings/base.py` read the file
  at import time. After #22 landed (PR #60), settings read `os.environ`
  first, and `env_file: .env` in the compose file already exposes every
  key as a process env var. The bind-mount is now a redundant fallback for
  the `dotenv_values()` codepath, not a requirement.

No behaviour change — docs only, hence PATCH.

## v1.1.0

CI now runs the test suite against Postgres 16 to match production, closing
the C4 item on the modernization roadmap (#42).

### Highlights

- **Postgres in CI** (#30): `.github/workflows/ci.yml` boots a
  `postgres:16-alpine` service container and points pytest at a new
  `openmv.settings.ci` module. The new module derives from `prod.py` —
  Postgres engine, `DEBUG=False`, the same `POSTGRES_*` + `SQL_*` env-var
  contract — but disables `SECURE_SSL_REDIRECT`, HSTS, and the
  secure-cookie flags so the Django test client (which speaks plain HTTP)
  doesn't get 301-redirected on every request. Postgres-only behaviour
  (datatypes, transaction semantics, parameter quoting, migrations) is now
  exercised by the smoke suite on every push and PR.
- **Versioning policy**: CLAUDE.md gains a "Versioning and releases"
  section codifying the every-PR `pyproject.toml` + `RELEASES.md` bump
  rule, the patch/minor/major heuristic, and the requirement to ask the
  human reviewer (or `AskUserQuestion` when running as Claude Code) when
  unsure. Tag + GitHub Release continue to be produced automatically by
  `release.yml`.

## v1.0.0

First tagged release. Captures the 2026 modernization of the long-standing
codebase that powers <https://openmv.net> — the docs, repo hygiene, tooling,
and CI work needed to make further development safe.

### Highlights

- **Docs**: added `README.md`, `CLAUDE.md`, and `LICENSE`. CLAUDE.md is the
  canonical orientation for new contributors and points at the GitHub issue
  tracker for outstanding work.
- **Dependency management**: `requirements.txt` removed in favour of
  `pyproject.toml` + `uv.lock`. Django pinned `>=4.2,<5.0`. Python 3.11 pinned
  via `.python-version`.
- **CI/CD foundation**: `.github/workflows/ci.yml` runs `pre-commit` and
  `pytest` on every push and PR.
- **Smoke tests**: `datasetapp/tests/test_views.py` covers the homepage, tag
  filter, dataset detail, and download redirect paths via `pytest-django`.
- **Local Docker**: `Dockerfile` (multi-stage uv builder + gunicorn runtime)
  and `docker-compose.yml` for dev parity with prod's Postgres backend.
  Production still ships behind Apache.
- **Pre-commit hygiene**: `flake8` hook moved from `gitlab.com` to GitHub;
  `click<8.1` pinned to keep the legacy `black==21.12b0` hook working until
  the broader hook refresh lands.
- **Bug fixes**: corrected the broken `%`-format log call in
  `about_dataset` that swallowed dataset slugs in the log output.
- **Repo conventions**: added `.editorconfig` so editors agree on
  indentation, line endings, and trailing whitespace without per-editor
  setup.

### Versioning

From here, the project follows semver:

- **PATCH** for bugfixes and dependency security bumps.
- **MINOR** for additive features (new views, template tweaks, schema
  additions).
- **MAJOR** for URL or template structure breaks.

### How v1.0.0 was tagged

Once the v1.0.0-prep PR was merged to `master`:

```
git checkout master && git pull
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

A matching GitHub Release was published at
<https://github.com/kgdunn/Django-dataset-download-app/releases/tag/v1.0.0>
with the contents of this section as the release body.
