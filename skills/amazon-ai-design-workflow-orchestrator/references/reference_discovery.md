# Purpose-based Reference Discovery

Version: `1.0.0`
Rater contract: `2`

This is the stable source of truth for finding design references, collecting simple preferences, refreshing an unsuitable batch and building a curated library. It replaces the v1 fixed-source/full-project-module-card preference workflow for new 1.0.0 runs. Existing v1 projects retain their legacy validation boundary.

## User interaction

The default interface lets the user choose **喜欢 / 一般 / 不喜欢**, then **继续 / 全部换一批 / 保留喜欢，重找其余**. The same explicit choices in chat are valid through `NATIVE_CHAT_FEEDBACK`; do not ask the user to repeat them by clicking buttons. Show only the axes for which a candidate has real evidence. Do not ask the user to identify an image location, explain why it works, assign a reference to a production module, fill a scoring rubric, or approve a second inferred preference summary. A voluntary explanation may steer the search, but is never required.

- `visual`: composition, lighting, color, material, photography and atmosphere.
- `layout`: visible headline hierarchy, parameters, type, icons, spacing, grids and reading order.
- A case may serve one purpose or both. A pure render may be useful visual evidence; it is not layout evidence merely because its file name says typography.
- Keep the two purposes separate. Different visual and layout favorites are valid; never add the two scores to select one overall winner.

## Search and AI screening

1. Read the current product facts and intended deliverables. Write a few short search needs for visual and layout separately; do not turn this into another user questionnaire.
2. Search the curated library first for applicable-purpose matches. Add new candidates to cover gaps and explore fresh approaches. If the library is empty, proceed with new research immediately.
3. Search by what the design must communicate: product material/finish, portability, charging context, headline hierarchy, dimension information, parameter grouping, setup steps or another current need. Combine product-category and adjacent-category terms; do not search only the product name.
4. Follow suitable original projects to their authors, studios and related work. ZCOOL, 致设计, 数英, Behance, Fonts In Use, Ads of the World, 古田路9号, WBDS, brand sites and studio portfolios are useful entry points; there is no mandatory site list, source percentage or tier quota.
5. Inspect the actual image before including it. Check that the claimed purpose is visibly supported, the image is readable, and the original project can be traced. Deduplicate by image hash/project and avoid a batch of nearly identical treatments. Machine checks confirm files/hashes; AI still must inspect image content and must not claim that metadata validation proves design quality.
6. Present a compact varied batch, normally about 6-10 candidates when useful, within the 1-12 candidate limit; this is a presentation guide, not a minimum gate or quota. Stop with fewer strong options if they cover the requested purposes. Never fill a numerical quota with weak work.

A candidate contains 1-6 readable images from one source project, at least one for each declared purpose. Full project context is useful when available but no candidate must supply a fixed number of modules or all four old role labels. Do not cross-mix projects under one project URL. A layout image needs visible information organization; a visual image needs useful visible composition/finish. Do not manufacture a 20/25 AI score or ask the user to validate an AI explanation.

Record current references in `大牌设计案例与版式库.md` with source links and brief AI-owned search notes. These notes may guide production, but per-image position/mapping/rationale fields are not an intake requirement or user approval gate.

## Runtime files and integrity

- `visual_reference_pool.json`: current v2 candidate pool and explicit ratings.
- `visual_reference_pool.pending.json`: frozen pre-submission pool produced with the rater.
- `visual_preference_profile.json`: approved preference evidence produced only after an accepted `CONTINUE`; it binds the current pool SHA-256 and run.
- `reference_discovery.py`: the controller-owned CLI for initialization, button/chat submission, replacement and favorites. Use `submit` for an unchanged button payload or `chat-submit` for an explicit chat instruction. Never invent ratings or edit receipt/hash fields to skip validation.

The pool uses `version: 2`, the active `run_identity`, an increasing `round`, and `status` in `PENDING_RATING`, `RATED`, or `RESEARCH_REQUIRED`. Each sample has a stable `id`, `project`, original `project_url`, `purposes`, `tags`, real `evidence`, and separate `visual` / `layout` values.

Example sample:

```json
{
  "id": "R01",
  "project": "Portable electronics campaign",
  "project_url": "https://example.com/projects/portable-electronics",
  "purposes": ["visual"],
  "tags": ["material", "studio-light"],
  "evidence": [
    {
      "path": "设计参考/R01/visual.jpg",
      "sha256": "<actual file SHA-256>",
      "purpose": "visual"
    }
  ],
  "visual": null,
  "layout": null
}
```

- Evidence paths must be project-relative and resolve to readable project-local image files, and hashes must match their bytes. Copy reusable library assets into the project before referencing them; a mutable external-library path is not current pool evidence.
- The whole pool must cover both `visual` and `layout`, which may be supplied by separate cards. Every declared purpose requires evidence with that purpose. Do not show a layout button for a visual-only candidate. A non-applicable rating remains `null`.
- Ratings use `1` for 喜欢, `0` for 一般, `-1` for 不喜欢 and `null` for unscored/non-applicable. `null` is never neutral or approval.
- Ratings are bound to the pending snapshot, run and round. A stale response, swapped source/image or mismatched sample set must fail without approving the pool.
- `RATED` means the current batch has an accepted continuation and usable positive anchors for both visual and layout. A historical favorite alone does not qualify it.
- Each anchor belongs to the same purpose as an explicit `1`. Never upgrade `0`, `null`, a file name, an AI inference or historical memory into a positive anchor.

## Commands and structured interaction

Resolve `<orchestrator-dir>` to this installed stable skill directory; these commands target the installed stable skill.

```bash
python3 '<orchestrator-dir>/scripts/bootstrap_run.py' \
  --project-root '<project-root>' --run-identity '<new-stable-run-id>'

python3 '<orchestrator-dir>/scripts/reference_discovery.py' init \
  --project-root '<project-root>'
```

Prepare `reference_candidates.json` as a sample list (or an object with a `samples` list), using AI-screened candidates and actual evidence hashes. Use the same `replace` command for initial population and later approved re-search; do not overwrite a populated pending pool by hand:

```bash
python3 '<orchestrator-dir>/scripts/reference_discovery.py' replace \
  --project-root '<project-root>' \
  --candidates '<project-root>/reference_candidates.json'
```

Then render the rater:

```bash
python3 '<orchestrator-dir>/scripts/build_visual_reference_rater.py' \
  --project-root '<project-root>' \
  --pool '<project-root>/visual_reference_pool.json' \
  --output '<project-root>/设计参考/reference_rater.html' \
  --title '选择参考方向'
```

Show real image previews with zoom, project/source links and applicable-purpose buttons. Keep the batch actions visible; a user can reject the whole batch without writing reasons or completing individual ratings. If automatic submission is unavailable, accept the exact structured copy fallback generated by the rater. When the user has already given an explicit action or specific sample-and-axis choices in chat, use `chat-submit` below instead of requiring another button interaction. Never infer unstated scores from vague praise, filenames or historical memory.

Payload shape:

```json
{
  "rater_contract_version": 2,
  "reference_pool_sha256": "<pending pool SHA-256>",
  "round": 1,
  "action": "CONTINUE",
  "ratings": [
    {"id": "R01", "visual": 1, "layout": null}
  ]
}
```

Apply it through the controller CLI:

```bash
python3 '<orchestrator-dir>/scripts/reference_discovery.py' submit \
  --project-root '<project-root>' \
  --payload '<project-root>/reference_rating_submission.json'
```

An accepted `CONTINUE` with positive anchors writes the pool as `RATED`. The CLI does not infer or write the profile; the controller now derives and writes it from the visible reference evidence and explicit ratings. Summarize the chosen visual/layout direction briefly and continue; do not ask for another profile approval. AI may translate visible evidence into a concise recipe, but do not infer why a user disliked something without support or turn speculative pattern labels into a new restriction.

## `NATIVE_CHAT_FEEDBACK`: explicit chat choices

Buttons are the default, but a clear current-batch instruction in chat is sufficient. The controller can proceed immediately using the dedicated CLI; no second approval, written reason or repeated button click is needed.

```bash
python3 '<orchestrator-dir>/scripts/reference_discovery.py' chat-submit \
  --project-root '<project-root>' \
  --action RESEARCH_ALL \
  --user-message '全部不好，换一批'
```

This records the user's exact words and binds the submission to the current pending snapshot hash and round. It marks a re-search action without fabricating a separate `-1` for every card. Do not copy ratings from an old run or manufacture a pending snapshot to apply stale feedback.

For “R01 画面喜欢、排版不喜欢；R02 排版喜欢，保留喜欢换其余”, save only the explicitly named sample/axis choices to a ratings JSON list:

```json
[
  {"id": "R01", "visual": 1, "layout": -1},
  {"id": "R02", "layout": 1}
]
```

```bash
python3 '<orchestrator-dir>/scripts/reference_discovery.py' chat-submit \
  --project-root '<project-root>' \
  --action RESEARCH_REJECTED \
  --user-message 'R01 画面喜欢、排版不喜欢；R02 排版喜欢，保留喜欢换其余' \
  --ratings '<project-root>/reference_chat_ratings.json'
```

- Map only unambiguous current-batch actions: all-replace → `RESEARCH_ALL`; retain likes and replace the rest → `RESEARCH_REJECTED`; explicitly continue → `CONTINUE`.
- Extract a score only when the sample id and applicable axis are explicitly clear. Preserve exact user wording with `--user-message`; do not add a rationale on the user's behalf. Omit unmentioned axes so existing values remain; when there is no previous score, they remain `null`.
- A whole-batch rejection does not require a ratings file. Never synthesize per-card negative ratings from it.
- `CONTINUE` retains the same positive-anchor and applicable-rating checks as the button route. If the user only requests replacement, unfinished ratings do not block re-search.
- Missing, changed or stale pending evidence still blocks a receipt. Inspect the current run/state and show the matching batch if needed; never bypass integrity checks or ask the user to explain taste as a substitute.

## Preference profile written by the controller

After accepted continuation, create this evidence-bound shape without another approval question:

```json
{
  "version": 1,
  "status": "APPROVED",
  "run_identity": "<active stable run>",
  "reference_pool_sha256": "<current RATED pool SHA-256>",
  "visual_system": {"keep": ["<visible visual rule from a liked reference>"], "exclude": []},
  "layout_system": {"keep": ["<visible layout rule from a liked reference>"], "exclude": []},
  "hybrid_recipe": {
    "visual_anchor_sample_ids": ["R01"],
    "layout_anchor_sample_ids": ["R02"],
    "rules": ["<how to combine the liked visual and layout evidence>"]
  },
  "rejected_patterns": []
}
```

`visual_system.keep`, `layout_system.keep` and `hybrid_recipe.rules` contain nonempty strings grounded in visible accepted evidence. Each anchor id must have a `1` on that corresponding axis. When an axis has a `-1`, its exclude list must be nonempty and refer to rejected evidence; if it has none, use `[]`. Likewise `rejected_patterns` is nonempty only when negative evidence exists. Prefer conservative references to the rejected candidate/purpose over inventing a global taste explanation. The state/bundle validator checks the pool submission plus profile run/hash/anchors before opening style work.

## Re-search instead of premature generation

- `CONTINUE`: validate all applicable ratings and positive anchors for both visual and layout. If either visual or layout has no explicit like, return `RESEARCH_REQUIRED` and search that gap. This does not authorize image generation.
- `RESEARCH_ALL`: no reason required. Replace the current batch with genuinely different candidates by changing search terms, sources, authors or direction. Do not carry current-batch approvals into the replacement.
- `RESEARCH_REJECTED`: preserve explicitly liked evidence and its corresponding purpose rating. Replace neutral, disliked and unscored candidates. On a mixed-purpose card, preserve only the liked purpose; do not carry the other axis as approved. A retained favorite is not rescored unless its source/evidence changes.
- Any refreshed batch increments the round, produces a new pending snapshot and requires a fresh accepted submission before downstream use. Old style images, profiles and plans cannot satisfy the new preference state.
- If a search is blocked by login or access, say `auth_required` or `blocked` and use accessible traceable sources when available. Do not invent results or repackage the same rejected batch as new.

Save replacement candidates with real local evidence, then apply them:

```bash
python3 '<orchestrator-dir>/scripts/reference_discovery.py' replace \
  --project-root '<project-root>' \
  --candidates '<project-root>/reference_candidates.json'
```

No-positive-anchor, different visual/layout winners or a mixed `1/-1` card creates no extra generated pairwise requirement. Once accepted references exist, use the existing A/B/C `STYLE_SAMPLES` stage with the same product, representative slot, copy and canvas; every successful sample ledger record binds the current profile hash. This is the existing style-choice gate, not an added reference-selection round.

## Curated library

Default library root: `~/.codex/reference-libraries/amazon-design`.

```bash
python3 '<orchestrator-dir>/scripts/reference_discovery.py' favorites-add \
  --project-root '<project-root>' \
  --library-root '<library-root>'

python3 '<orchestrator-dir>/scripts/reference_discovery.py' favorites-find \
  --library-root '<library-root>' \
  --query 'portable electronics studio light' \
  --purpose visual \
  --project-root '<project-root>'
```

- Add only reference evidence the user explicitly rated `1`, for that corresponding purpose. The user-approved stable workflow authorizes this operational library update; it does not authorize editing long-term Codex memory or unrelated skills.
- Record source/project URL, purpose, search tags, image hashes and rating provenance. Save reusable reference images within the library; runtime assets are not committed to the skill repository.
- Do not store current-product facts, specifications, account data, user-private product photos or unsupported taste guesses in this reference library.
- Do not bootstrap the library from old project folders, chat memory or files called “liked” without a verifiable explicit rating. Freshly retrieving an old asset does not retroactively approve it.
- `favorites-find` verifies library evidence and copies trusted assets into the current project, returning draft candidates for current screening. It never sets the current pool to `RATED`, creates current positive ratings, or approves the current profile.
- Deduplicate by evidence hash and purpose; preserve traceable source metadata. Keep an option to discover new authors/styles so the library does not make every product look the same.

## Downstream and stable boundary

The `visual_preference_profile.json` hash remains mandatory in `STYLE_SAMPLES` ledger records and `production_plan.json`. A profile change invalidates stale samples/plans. Product truth, exact references, prompt provenance, thin-worker concurrency and full-set QC remain in force.

Stable `1.0.0` retains the reference discovery and interaction introduced in stable `0.7.0` from the user-approved `0.7.0-beta.3` release. Synthetic tests verify contracts and state transitions; they do not prove improved reference quality or image sharpness. The separate beta entry remains available for explicitly requested legacy beta runs.
