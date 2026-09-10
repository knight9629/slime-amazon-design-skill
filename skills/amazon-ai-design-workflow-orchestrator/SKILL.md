---
name: amazon-ai-design-workflow-orchestrator
description: "Use when the user invokes the Amazon 主图A+ / 主图+A+ design skill, asks for Amazon main-image and A+ workflow execution, or needs project-stage control across product references, research, style sampling, prompts, image2 generation, QC, and export."
---

# 亚马逊设计师agent

Skill version: `1.0.0`


This is the stable `1.0.0` release and the default for ordinary Amazon main-image/A+ requests.

## Goal

Act as the full-flow controller for Amazon main-image and A+ production.

Calling this skill means `FULL_FLOW` by default. Use `QUICK_TASK` only when the user explicitly asks for a sample, test image, first-screen test, or an ordinary 1-3 image task. A quick task stays in the current task and does not count as full-flow progress.

`FULL_FLOW_EXCLUSIVE_CONTROL`: once a request enters `FULL_FLOW`, generic brainstorming, visual-companion pages, HTML/CSS mockups, and nearby helper workflows may not replace, pause, or relabel the state machine unless the user explicitly requests that separate artifact. “先出样” under time pressure does not silently convert an already-invoked full run into `QUICK_TASK`.

The controller must:

- inspect the project before asking questions;
- ask only for missing production-scope fields;
- protect product truth and local details before style;
- generate at least three white-background reference images from the photographed product images at the beginning of the workflow;
- stop at a dynamic Product Facts Gate before big-brand research, style samples, or full production;
- use the lightest valid reference route;
- research competitors and current big-brand cases for every product;
- find references by visual/layout purpose, reuse explicitly liked favorites, and refresh rejected candidates with minimal user input;
- compare three styles with one representative image per style;
- carry product-exposure role checks into the compact production context and formal production planning;
- continue selected-style formal production in the same task by default;
- generate every approved raw slot before centralized finished-image QC;
- use bounded subagent parallelism for independent research, style, planning, prompt, generation, and QC work when subagents are available;
- keep the controller as the only writer of canonical facts, decisions, state, and final manifests;
- create worker documents only when a worker/subagent is actually dispatched;
- rework only failed slots.

## Operating Modes

### `FULL_FLOW` — default

Use the complete state machine. Do not downgrade it into a quick sample unless the user explicitly asks for a sample/test.

Typical invocation phrases include:

- `调用主图A+设计skill`
- `用主图A+设计skill作图`
- `用实拍图做主图A+`
- `主图+A+`
- `主图A+`
- `亚马逊设计师agent`

### `QUICK_TASK` — explicit only

Use only when the user explicitly asks for `样张`, `小样`, `测试图`, `先试一张`, or another ordinary 1-3 image task.

- Complete it in the current task.
- Do not create production context-pack files.
- Do not require competitor research, big-brand research, full matrix, batch worker packets, worker reports, or production manifests unless the user explicitly expands the task.
- Keep product-truth, reference selection, image2 route, and image QC safeguards.
- Do not mark quick-task artifacts as full-flow progress.

## Agentic Execution Model

Read `references/agentic_workflow_contract.md` before dispatching any subagent. Read `references/reference_discovery.md` before big-brand/reference curation or preference analysis. The controller may use `spawn_agent` or the available equivalent subagent mechanism, but it must preserve these invariants:

- `CONTROLLER_SINGLE_WRITER`: only the controller may write or promote canonical scope, product truth, detail locks, selected style, the official layout matrix, the final prompt set, workflow state, checkpoints, or manifests.
- `CONTROLLER_PLUS_THREE`: Codex allows 4 total concurrent agents. The controller occupies one slot, so use at most 3 child workers; do not reduce the child limit to 2 merely because the controller is active.
- `BOUNDED_PARALLELISM`: parallelize only tasks whose dependencies are complete and whose allowed write paths do not overlap. Use `min(3, available_subagent_slots, ready_independent_tasks)` child workers.
- `FIXED_THREE_LANE`: after prompts and references are frozen, keep all 3 child image lanes filled whenever at least 3 independent slots remain. Refill immediately on completion; successful latency alone never reduces concurrency.
- `PHASE_BOUNDARY_SCHEDULER`: compute `scheduler_state.json` once before a generation phase and again only at a phase boundary, recovery, or material transport error. Do not recompute after each successful image.
- `DELEGATION_GAIN_THRESHOLD`: keep work controller-direct when it is expected to finish in under 120 seconds, has no meaningful parallel gain, or shares a write surface. Delegate only independent heavy research or one-slot image work whose expected gain exceeds dispatch/report overhead.
- `NO_SMOKE_GATES`: do not run reference, MAIN, or A+ smoke tests. Prompt/reference approval is the generation gate; quality review begins after the complete raw set exists.
- `UNIFIED_READY_QUEUE`: place every approved independent MAIN and A+ slot into one generation queue before the first formal image call.
- `THIN_IMAGE_WORKER`: an image worker receives only `task_id`, `slot_id`, immutable prompt, native reference paths, and one unique raw output path. It calls image2 once and does not read Skills/project docs, run QC, refresh state/scheduler, or write a narrative report.
- `FRESH_IMAGE_CONTEXT`: dispatch image workers without inherited conversation history (`fork_turns="none"` or the platform equivalent) and inline the five packet values in the task message. Do not tell the worker to open a packet file.
- `MINIMAL_GENERATION_RECEIPT`: an image worker returns only task/slot, success or standardized error, output path when successful, and elapsed time. The controller batch-records successful receipts and provenance at the generation phase boundary.
- `STANDARD_TRANSPORT_FAILURE`: a failed image receipt must use `AUTH`, `NETWORK`, `RATE_LIMIT`, `TIMEOUT`, `TRANSPORT`, or `OTHER`. At a transport recovery boundary, record that failed attempt immediately before recomputing the scheduler; record the first successful recovery attempt immediately before restoring three lanes.
- `GENERATION_FIRST_QC_AFTER`: no finished-image visual QC consumes child slots while raw generation work remains. After the full raw set is complete, dispatch exactly three dedicated read-only QC profiles: product truth/structure, copy/style, and aspect/dimensions/technical.
- `MACHINE_QC_GATE`: the three QC profiles and separate MAIN/A+ verdicts are hash-bound JSON artifacts. Completion requires all three profiles to cover every planned slot and each verdict to reference all three profile hashes and merge exact `failed_slot_ids`.
- `NORMALIZED_UNIQUE_PATHS`: canonicalize every plan path before collision checks. Path aliases such as `a/../same.png` and `same.png` are the same write target and must be rejected.
- `IMAGE_WORKER_REPORT_FORBIDDEN`: image tasks may not use `required_report_path`, `promoted_output_paths`, or `workers/outputs`; `VERIFIED` requires a successful inline generation receipt.
- `WORKER_PACKET_REQUIRED`: create a task packet only when a worker is actually dispatched. Image packets use the five-field thin contract; non-image workers retain task-scoped inputs, paths, checks, and reports.
- `SEQUENTIAL_FALLBACK`: when subagents are unavailable, capacity is exhausted, or tasks share a write surface, run the same stage sequentially in the controller without creating empty worker artifacts.
- `SAME_TASK_CONTINUATION`: after the user selects a style, prepare the compact production context and continue to layout, prompts, generation, QC, and export in the same task without another human gate.
- `OPTIONAL_CONTEXT_HANDOFF`: create a new-task continuation prompt only when the user explicitly asks for one or the current task cannot continue because of a real technical recovery condition. It is never the default production path.

Use one `agent_task_registry.json` per run only when at least one real subagent is dispatched. The controller owns this registry and task status. Workers may not edit it.

Reusable worker roles:

- `RESEARCH_WORKER`: competitor, big-brand, or self-product research drafts.
- `COPY_WORKER`: selling-point hierarchy, image copy, native Amazon copy, alt text, and copy QC.
- `LAYOUT_WORKER`: layout, product-exposure, scene, and repetition-risk drafts.
- `PROMPT_WORKER`: MAIN or A+ prompt-group drafts from an approved matrix.
- `IMAGE_WORKER`: one reference image, style sample, or production slot per task.
- `QC_WORKER`: read-only fact, copy, visual, reference, or technical QC reports.

Parallel work never weakens the Human Gates, Product Facts Gate, visual-input gate, full-set QC, failed-slot-only rework, or final-manifest rules.

### Execution Efficiency Contract

- `EVENT_DRIVEN_WAIT`: after dispatch, wait for completion events with one bounded 60-120 second wait. Do not run repeated 30-second polls or call agent-list/status tools after every timeout; inspect workers only on completion, error, a materially long timeout, or before reusing capacity.
- `STATE_REFRESH_BUDGET`: run `design_workflow_state.py` only at initialization/recovery, a human-gate transition, a formal phase boundary, a canonical mutation that changes the next phase, and final verification. Do not refresh after every slot, worker report, wait, or read-only QC result.
- `READ_ONCE_PER_TURN`: read each selected Skill and execution contract once per turn. Reread only if the file changed, context was compacted/lost, or a recovery check shows uncertainty.
- `INTERRUPTION_RESUME`: treat Mac sleep, display-off, or network loss as external suspension. Resume from `active_run.json`, the task registry, reports, and files already on disk; do not replay completed skill reads, state scans, generations, or QC.
- `REFERENCE_THREE_WAY_PARALLEL`: generate the main, angle, and structure white-background references together with three thin image workers. Run QC only after all three raw references exist, then ask for one manual approval.

### 1.0.0 Machine Gates

- `ONE_MESSAGE_SCOPE_INTAKE`: run `scripts/bootstrap_run.py` once to create `active_run.json`, `source_inventory.json`, `competitor_zip_inventory.json`, and `production_scope.template.json`. Ask every missing scope field in one consolidated message. After the answer, validate all enabled counts/formats and atomically write `production_scope.json`; invalid data must not touch the canonical file.
- `REFERENCE_FIDELITY_LOCK`: after `reference_strategy.json`, hash-bind the lightweight structural `must_preserve` and `forbidden_drift` rules in `reference_fidelity_lock.json` before generating any white-background reference. Every selected source needs at least one lock row.
- `VISUAL_PREFERENCE_CALIBRATION`: follow `references/reference_discovery.md` v2. AI searches by purpose, tries the curated library first, inspects and deduplicates candidates, then presents source-visible images through `build_visual_reference_rater.py`. Show only applicable visual/layout buttons: 喜欢 / 一般 / 不喜欢. `reference_discovery.py submit` validates a button payload; `chat-submit` accepts an explicit current-batch chat action and named sample/axis choices with the exact user words. Both bind the pending pool SHA-256 and round. `NATIVE_CHAT_FEEDBACK` never requires repeating an already explicit choice by clicking buttons. `CONTINUE` yields `RATED` only when both visual and layout have a positive anchor; the controller then writes the hash-bound profile; otherwise it enters `RESEARCH_REQUIRED`. `RESEARCH_ALL` replaces the batch; `RESEARCH_REJECTED` retains explicit likes and replaces the remainder. Do not require manual image explanations, module assignment, profile approval, fixed source quotas, numeric AI scores, complete-project role counts, or an extra generated pairwise round.
- `IMAGE2_PROVENANCE_GATE`: append every real image2 call to `generation_ledger.jsonl` with run/stage/slot, route, prompt hash, exact reference paths and hashes, timestamps, elapsed time, output dimensions/path/hash, and status. A/B/C filenames without matching successful image2 evidence do not unlock style choice; each `STYLE_SAMPLES` success must also bind the current `visual_preference_profile_sha256`.
- `CANONICAL_PRODUCTION_PLAN`: `production_plan.json` is the single production source for slot facts, sizes, prompts, expected copy, references, task duration, and independence. It must bind the current `visual_preference_profile_sha256`. Run `scripts/derive_production_artifacts.py`; matrix, prompt document, worker packet/report templates, registry template, and preflight spec are derived outputs, not separate facts to maintain by hand.
- `DETERMINISTIC_PREFLIGHT`: run `scripts/preflight_qc.py` before finished-image model/visual QC. It checks file existence, hashes, exact dimensions, exact raw aspect ratio, and expected raster text. `OCR_UNAVAILABLE` or OCR execution failure means `NEEDS_VISUAL_QC`; it is never a text `PASS`.
- `SCHEDULER_STATE_GATE`: `scheduler_state.json` must match the active `run_identity`, declare `PHASE_BOUNDARY_SCHEDULER`, and recommend 1-3 child workers. The normal generation recommendation is 3; only a material transport error may temporarily reduce it.
- `MACHINE_QC_GATE`: require `preview/qc_product_structure.json`, `preview/qc_copy_style.json`, and `preview/qc_technical.json`, followed by `preview/main_batch_qc_verdict.json` and/or `preview/aplus_batch_qc_verdict.json`. Every file is bound to the current `preflight_qc.json` hash.

## Hard Generation Rules

- Preferred formal route: `DIRECT_IMAGE_INPUT`. Pass the exact selected local source/reference paths to the image-generation call through its native referenced-image input, and keep the subset minimal. Local paths written only inside prompt text do not count.
- Inspect every selected local image before its first use. For multiple references, declare each role and identify the controlling product reference; product truth and local-detail sources outrank style references.
- Fallback route: use `VISUAL_CONTEXT_RELAY` only when native referenced-image attachment is unavailable. Immediately inspect/load the exact source with `view_image`, call image generation next, and include the fail-fast canary `NO VIEW_IMAGE INPUT`.
- For a matrix-approved `P0` no-product slot, state that no product reference is used. Attach a non-product scene/style reference only when it materially controls the result.
- `TEXT_ONLY`, Markdown embeds, filenames alone, prompt-only path strings, old chat memory, old screenshots, and text links are not valid product-reference authority for formal output.
- Do not substitute other generative routes such as PPT, HTML/CSS, Python canvas, Photoshop generative tools, Stable Diffusion, Midjourney, browser image tools, or manual compositing.
- Local scripts are allowed only for deterministic contact sheets, size checks, same-aspect resizing, previews, manifests, checkpoints, and packaging.
- `EXACT_RATIO_EXPORT`: stable export requires the raw image to have the exact target aspect ratio. Deterministic same-aspect resize is allowed; crop, pad, stretch, stitching, compositing, or content rewriting is forbidden. Any ratio mismatch returns that slot to image2. The previous 0.6.11 bounded-ratio correction is not supported by this exporter.
- For every `4:5 portrait` main-image prompt, apply the stable runner version `1.0.0` Main 4:5 Image2 Ratio Prompt Rule. This improves raw `4:5` compliance but does not guarantee exact pixels, so raw dimensions still require QC.
- Product truth and confirmed local details outrank style, competitor claims, and category playbooks.
- Do not invent specifications, accessories, ports, controls, screens, apps, package contents, certifications, logos, authorization claims, or unconfirmed capabilities.
- Do not default every image to a full-product composition. Product appearance must serve recognition, proof, understanding, or trust for that slot.
- Do not force a fixed number of no-product images. All slots may show the product only when each product appearance has a different module task, product role, visual role, or proof function.
- Product-free module layouts are valid for app access, parameters, screen results, lifestyle results, trust moods, and scene storytelling when product presence does not add concrete buyer proof.
- Repeating the same product reference and angle across many slots is a visual fatigue failure even if the written module tasks differ.

### 正向提示词写作门禁

- `POSITIVE_CREATIVE_DIRECTION`: 每条正式生图提示词都必须是一份正向、完整、可直接执行的视觉设计方案。直接定义当前图的视觉主体、空间关系、阅读路径和商业完成度，不依赖“更高级”“更有设计感”之类空泛形容词。
- `ONE_VISUAL_MEMORY_POINT`: 每张图只指定一个主导视觉记忆点，并明确第一视觉主体、产品作用、空间关系和阅读顺序。尺寸线、运动轨迹、步骤关系等必要类别语义可以保留，不为追求变化而破坏信息表达。
- `COPY_OCCURRENCE_RULE`: 图片内允许出现的文案必须逐条列出；只能使用 `production_plan.json` 中已批准的 `image_embedded_copy`，`image_embedded_copy` 为空时不得自行新增栅格文字。每条文案以及关键数字默认只出现一次，通过字号、字重、位置和留白建立层级，不通过重复数字制造视觉冲击。
- `EVIDENCE_BASED_OMISSION`: 已确认“事实存在”不等于已确认“外观长什么样”。没有外观依据的配件、内部结构或产品状态只用文字表达，不生成写实物体、通用线稿、轮廓或示意图标。拆卸、打开、内部、连接和装配状态必须有对应视觉证据。

正式提示词按适用性明确以下八项；白底主图或纯数据页可以压缩不适用段落，但不能为了填模板新增事实或装饰：

1. **核心传达目标**：消费者第一眼应理解或感受到什么。
2. **产品事实与参考图分工**：哪张图控制身份、角度、结构、材质或局部细节。
3. **单一视觉记忆点**：缩略图阶段唯一最容易被记住的视觉主角。
4. **正向构图设计**：产品角色、大小、位置、角度、前中后景、阅读路径和元素关系。
5. **光影、色彩与材质**：可见的光线方向、明暗、配色、材质响应、景深和商业完成度。
6. **文案规则**：允许出现的精确文案、次数和层级。
7. **视觉证据边界**：哪些内容可以画，哪些事实只能保留为文字。
8. **禁止项**：只保留产品变形、错误事实、虚构结构、额外文案和平台风险。

## Human Gates

Stop only at these points:

1. Required production scope is missing.
2. A three-image or larger white-background reference set has passed automated QC and needs user approval.
3. Critical product facts are missing or not explicitly confirmed for the current product category.
4. The user gives simple applicable-purpose ratings, continues with liked references, or asks for all/rejected candidates to be replaced; no written reason or per-image module assignment is required.
5. The user must choose one of the three profile-constrained style samples.
6. Product credibility and selling-point clarity pass, but the user must decide whether visual-impact-only rework is worth another generation.
7. The same QC problem still fails after two controlled rework rounds.

Do not stop merely because a brief, matrix, prompt document, checkpoint, or `PASS` / `PASS_WITH_NOTES` report was created.

## Compact State Machine

| State | Exit condition | Next |
|---|---|---|
| `INIT` | Project root and real product photos are known | `SCOPE_CONFIRMATION` |
| `SCOPE_CONFIRMATION` | Valid `production_scope.json` exists | `REFERENCE_ASSESSMENT` |
| `REFERENCE_ASSESSMENT` | Valid `reference_strategy.json` selects `DIRECT_SOURCE` or `MINIMAL_LIBRARY` | `REFERENCE_FIDELITY_LOCK` |
| `REFERENCE_FIDELITY_LOCK` | Source-bound `reference_fidelity_lock.json` passes hash and structural-lock checks | `REFERENCE_LIBRARY_BUILD` |
| `REFERENCE_LIBRARY_BUILD` | At least three white-background reference images generated from photographed source images exist | `REFERENCE_QC` |
| `REFERENCE_QC` | Automated reference QC is `PASS` / `PASS_WITH_NOTES` | `REFERENCE_APPROVAL` |
| `REFERENCE_APPROVAL` | User approval exists | `PRODUCT_DETAIL_LOCKS` |
| `PRODUCT_DETAIL_LOCKS` | `01_product_truth.md` and `03_product_detail_locks.md` exist | `COMPETITOR_RESEARCH` |
| `COMPETITOR_RESEARCH` | Product-specific competitor display-logic brief exists | `PRODUCT_BRIEF` |
| `PRODUCT_BRIEF` | Self-product selling-point brief exists | `PRODUCT_FACTS_GATE` |
| `PRODUCT_FACTS_GATE` | Dynamic critical product facts are confirmed or intentionally excluded | `BIG_BRAND_RESEARCH` |
| `BIG_BRAND_RESEARCH` | Current product-specific big-brand case library exists | `VISUAL_PREFERENCE_CALIBRATION` |
| `VISUAL_PREFERENCE_CALIBRATION` | v2 `CONTINUE` yields a valid `RATED` pool and hash-bound profile; `RESEARCH_REQUIRED` loops to reference search | `STYLE_RECOMMENDATION` or same stage search |
| `STYLE_RECOMMENDATION` | Exactly three reusable Style Specs exist | `STYLE_SAMPLES` |
| `STYLE_SAMPLES` | A/B/C samples each have matching successful image2 evidence in `generation_ledger.jsonl` | `STYLE_CHOICE` |
| `STYLE_CHOICE` | User selects one style | `CONTEXT_PACK_PREP` |
| `CONTEXT_PACK_PREP` | Compact production context files exist | `PRODUCTION_PLAN` automatically in the same task |
| `PRODUCTION_PLAN` | Approved canonical `production_plan.json` exists | Derive `LAYOUT_MATRIX` and prompt/task scaffolding |
| `LAYOUT_MATRIX` | Complete slot matrix exists and any deferred Premium carousel assignment is resolved | `PROMPT_WRITING` |
| `PROMPT_WRITING` | Production prompts exist | `PROMPT_QC` |
| `PROMPT_QC` | Prompt QC is `PASS` / `PASS_WITH_NOTES` | `SCHEDULER_SETUP` |
| `SCHEDULER_SETUP` | Phase-boundary `scheduler_state.json` authorizes the generation pool | `IMAGE_GENERATION` |
| `IMAGE_GENERATION` | Every planned raw production slot exists | `DETERMINISTIC_PREFLIGHT` |
| `DETERMINISTIC_PREFLIGHT` | File/hash/dimension/ratio/OCR report is `PASS` or explicitly routes to visual QC | `IMAGE_QC` |
| `IMAGE_QC` | Three post-generation QC profiles and authoritative MAIN/A+ verdicts pass | Failed-slot rework or `AGENT_TASK_VERIFICATION` |
| `AGENT_TASK_VERIFICATION` | Thin image receipts and any dispatched non-image/QC reports are controller-verified | `FINAL_EXPORT` |
| `FINAL_EXPORT` | Final manifest exists | `COMPLETE` |

Reference-library rule:

- Every `FULL_FLOW` project must create at least three white-background reference images from photographed product images near the beginning of the workflow.
- This requirement applies to both `DIRECT_SOURCE` and `MINIMAL_LIBRARY`.
- `DIRECT_SOURCE` means the original photos remain the authority for local details; it does not skip white-background reference creation, QC, or approval.

## Required Compact Decision Files

### `production_scope.json`

Read `references/production_scope_contract.md` for the stable schema. Use `ONE_MESSAGE_SCOPE_INTAKE`: run `scripts/bootstrap_run.py --project-root <root> --run-identity <id>`, ask only the missing fields together, then validate and atomically write `production_scope.json`; its template is not valid scope evidence.

- Single-ratio main images use `main.count`; both `1:1` and `4:5` require separate `main.count_by_ratio` values, with no ambiguous shared count.
- Basic A+ uses `image_count`, up to 7 standalone `960x600` images.
- Premium A+ records `module_count`, `desktop_image_count`, and `mobile_image_count`; use `carousel_assignment_status: DEFERRED_TO_LAYOUT_MATRIX` when page logic is not ready, then write `RESOLVED` and exact `carousel_modules` before prompt writing.
- Do not invent an image count or carousel mapping.

### `active_run.json`

Create this at the project root after resolving the current project folder. It prevents old `.md`, old prompts, old QC files, and old generated outputs from being mistaken as current progress.

```json
{
  "version": 1,
  "workflow_version": "1.0.0",
  "run_identity": "2026-06-30-product-name-style-a",
  "active_paths": [
    "拍摄图",
    "输出/current_reference_library",
    "full_production/current_style"
  ],
  "include_root_files": true
}
```

Rules:

- `run_identity` must change for a new clean run or new test package.
- `workflow_version: 1.0.0` marks a new stable run and requires the purpose-based v2 reference gate. `bootstrap_run.py` writes it automatically. Existing v1 files are not silently approved or rewritten; use a separate new run and v2 pool when migrating an old project.
- `active_paths` should name only the current source folders, approved reference folder, current style folder, and current output folder.
- The state script may fall back to legacy unscoped scanning when this file is missing. A historical project with no version marker and neither preference artifact remains readable without retroactive regression; creating either preference artifact opts that project into the full gate. Formal new runs must create this file during initialization.
- Do not use old project output folders as `active_paths` unless the user explicitly requests evidence-based reuse.

The same bootstrap creates `source_inventory.json` with image dimensions and hashes, plus `competitor_zip_inventory.json` with archive size/hash evidence. Reuse these inventories within the run instead of rescanning source folders at every stage.

### `reference_strategy.json`

Create this after visually assessing the real source photos. Read `references/reference_strategy_contract.md` for source-path and hash validation.

```json
{
  "strategy": "DIRECT_SOURCE",
  "reason": "Clean, complete and trustworthy source views",
  "selected_sources": ["path/to/front.jpg", "path/to/rear.jpg"]
}
```

Allowed strategies:

- `DIRECT_SOURCE`: real photos are clean and trustworthy enough to serve as authority while generating the required three or more white-background reference images.
- `MINIMAL_LIBRARY`: source photos need a small corrected reference set because direct use is likely to cause drift.

Use `DIRECT_SOURCE` only when the relevant product silhouette, proportions, color/material, angle, controls, ports, labels, and high-risk details are clearly visible and not distorted by clutter, occlusion, reflections, perspective, or poor resolution. Even then, generate at least three white-background references from these photos.

Use `MINIMAL_LIBRARY` when the product is structurally complex, backgrounds obscure the outline, key details are hidden, source angles conflict, or direct use is likely to cause drift.

### `reference_fidelity_lock.json`

Create this immediately after `reference_strategy.json`. Each lightweight lock binds `feature`, `source_path`, `source_sha256`, `must_preserve`, and `forbidden_drift` to one selected real source. Every selected source must have lock coverage. White-background generation is blocked until the file matches the active run and selected-source hashes.

### `generation_ledger.jsonl`

Append exactly one `SUCCEEDED`, `FAILED`, or `BLOCKED` evidence record for every image2 attempt. Successful records include `version`, `provider: image2`, `run_identity`, `generation_id`, `stage`, `slot_id`, `route`, `prompt_sha256`, exact `reference_inputs` and hashes, `started_at`, `completed_at`, `elapsed_ms`, output width/height/path, and `output_sha256`. `STYLE_SAMPLES` records also include the current `visual_preference_profile_sha256`. `scripts/generation_ledger.py` writes these bindings when supplied the current project/profile. Missing timing/identity/dimension/binding fields invalidate evidence. File existence, Markdown embeds, worker prose, or HTML previews never substitute for this ledger.

### `visual_reference_pool.json` and `visual_preference_profile.json`

Use `references/reference_discovery.md` as the v2 source of truth. Keep source/evidence hashes and separate purpose-specific anchors, while removing the old fixed-source quota, mandatory full-project collage, AI score threshold, universal dual-axis scoring, and pre-style pairwise gate.

- Use `reference_discovery.py init` for the current run; search visual and layout needs separately. AI owns searching, inspection, classification and deduplication.
- Search the curated library before adding new candidates. Only explicit `1` ratings authorize a purpose-specific favorite; a library hit remains an unrated current-project candidate.
- Evidence is one or more real readable local images with a project URL, SHA-256 and `purpose`. A visual-only render is valid for visual inspiration and must not receive layout controls.
- Run `build_visual_reference_rater.py` to preserve the pending snapshot and display only applicable-purpose buttons. Apply its payload through `reference_discovery.py submit`, or use `NATIVE_CHAT_FEEDBACK` / `chat-submit` for explicit chat choices. Never invent ratings, infer unmentioned axes, convert `null` to neutral, or require the user to repeat an explicit chat choice by clicking again.
- User actions are `CONTINUE`, `RESEARCH_ALL`, and `RESEARCH_REJECTED`. A requested refresh invalidates downstream preference approval until the next accepted round. No positive anchor for a required purpose means search again, without image generation.
- After accepted `CONTINUE`, the controller creates the current pool/profile hash binding from explicit ratings and visible evidence; it does not require a second profile-approval question. Valid visual and layout anchors may come from different cases.
- Style-sample ledger and formal plan still bind the current `visual_preference_profile_sha256`; old images and plans cannot bypass a changed preference profile.

### `production_plan.json`

After style selection and compact context preparation, write one approved plan containing the current `visual_preference_profile_sha256` plus every slot's group, canonical output path, target size, module task, product role/exposure, exact references, prompt, raster copy, estimated duration, and independence. `scripts/derive_production_artifacts.py` rejects a stale profile binding; edit the plan and regenerate when the profile or a slot fact changes.

## Workflow

### 1. Initialization and Scope

1. Resolve the project root and locate real product photos.
2. Run `scripts/bootstrap_run.py` to create the active run, source/hash inventory, competitor ZIP inventory, and scope template in one pass.
3. Run `scripts/design_workflow_state.py` once for initialization.
4. If `production_scope.json` is missing or invalid, ask all missing counts/formats in one message and atomically write the completed JSON after the answer. For Premium A+ without page-display logic, record aggregate totals with `DEFERRED_TO_LAYOUT_MATRIX` and do not ask for a guessed carousel mapping.
5. Refresh state only if scope creation changes the phase, then continue automatically.

### 2. Reference Assessment And White-Background Reference Build

Visually inspect the available real product photos before deciding how to build the required white-background reference set.

Before either route generates an image, create and validate `reference_fidelity_lock.json`. Do not defer this lightweight lock until the later detailed product-truth stage.

#### `DIRECT_SOURCE`

- Select only the few real source photos needed for downstream slots.
- `REFERENCE_THREE_WAY_PARALLEL`: generate the `main-reference`, `angle-reference`, and `structure-reference` together with three thin image workers immediately after `reference_strategy.json`.
- Default set: one `main-reference` front/global image, one `angle-reference` three-quarter or side image, and one `structure-reference` rear/top/bottom/detail image.
- Use `DIRECT_IMAGE_INPUT` for each reference by attaching the exact photographed source path to image generation. Use `VISUAL_CONTEXT_RELAY` with `view_image` and the canary only as a fallback.
- Do not generate one white-background image for every source photo; make the smallest useful set, but never fewer than three.
- Run QC only after all three raw references exist. Then show the complete set for one manual approval before `PRODUCT_DETAIL_LOCKS`.
- Create `01_product_truth.md` and `03_product_detail_locks.md` directly from real photos and confirmed user facts.

#### `MINIMAL_LIBRARY`

Invoke `product-reference-composer` with these limits:

- Default target: one `main-reference` plus at least two `angle-reference` / `structure-reference` images.
- Generate those three white-background images together under `REFERENCE_THREE_WAY_PARALLEL`.
- Keep logo, label, button, interface, port, QR, bottom, or rear close-ups as `SOURCE_ONLY` evidence unless background removal is genuinely needed.
- Do not generate one white-background image for every source photo.
- Use `DIRECT_IMAGE_INPUT` for each corrected reference by attaching the exact photographed source path to image generation. Use `VISUAL_CONTEXT_RELAY` with `view_image` and the canary only as a fallback.
- Run automated QC with `PASS`, `PASS_WITH_NOTES`, `REVISE`, or `REJECT`.
- After automated QC passes, stop for user approval.
- Revise only failed references or failed local details, with a maximum of two controlled rounds.

For both strategies, the approved white-background reference set must exist before research/style work. Then complete `01_product_truth.md` and `03_product_detail_locks.md` using both real photos and the approved white-background references, with real photos retaining authority over local details.

### 3. Product-Specific Research

Run these stages for every product; do not reuse another product's research as the current product's completed stage unless the user explicitly requests reuse. After product truth and local detail locks exist, competitor research and the self-product brief may be dispatched in parallel because they write separate drafts. The controller must reconcile both before creating the Product Facts Gate.

#### Competitor research

Invoke `amazon-competitor-creative-research` when `竞品卖点与展示逻辑整理.md` is missing.

- Analyze display order, visual proof, message priority, A+ structure, scene logic, and risk points.
- Do not copy competitor images, wording, layouts, brand assets, claims, ratings, or reviews.
- Keep the output focused on decisions that affect the current image set.

#### Self-product brief

Invoke `amazon-product-selling-point-brief` when `我的产品信息与卖点优先级文档.md` is missing.

- Product facts outrank competitor claims.
- Latest explicit user facts outrank older notes.
- Unknown or unsupported facts remain unknown; do not infer them as confirmed.
- Use only a clearly matched category playbook section from `references/category_design_playbooks.md`.

#### Dynamic Product Facts Gate

After the self-product brief exists, create or update `product_facts_gate.md` and stop for confirmation before big-brand research, style recommendation, style samples, or full production.

This is not a fixed questionnaire. Generate the shortest useful question set from the current product:

1. Identify the product category from product truth, competitor set, visible form, Amazon use case, and buyer purchase reason.
2. List only the facts that materially change claims, visual modules, compliance risk, scale, included items, or user-result proof.
3. Group questions by claim family instead of asking every possible parameter.
4. Ask for source-backed values when possible: spec sheet, manual, package label, official page, test data, certification, or user confirmation.
5. If a fact is unknown but the user accepts excluding that claim, record it under `Unknown but intentionally excluded`.
6. Do not proceed until `product_facts_confirmation.md` exists with `Status: CONFIRMED`, `APPROVED`, `PASS`, or `NO_BLOCKING_MISSING_FACTS`.

Examples of dynamic fact families:

- Electrical appliance: dimensions, weight, power/input, battery/cord limits, runtime, modes/gears, noise, adjustable angle, cleaning, safety/certification, package contents.
- Furniture/storage: dimensions, material, load capacity, installation, included hardware, room fit, safety limits, package contents.
- Apparel/accessory: size chart, fabric/material, fit, care, color variants, closure, model/body guidance, compliance claims.
- Beauty/personal care: ingredients/material contact, mode levels, waterproof rating, charging, use areas, safety/certification, before/after claim proof.
- Electronics/projector/device: core specs, ports, connectivity, OS/app support, power, compatibility, heat/noise, accessories, certifications, content/logo authorization.

`product_facts_gate.md` should contain:

- Detected category and buyer purchase reason.
- Confirmed facts already supported by evidence.
- Missing critical facts and why each affects images or claims.
- Claims to avoid unless confirmed.
- The exact minimal questions for the user.

`product_facts_confirmation.md` should contain:

- Status.
- Confirmed facts and sources.
- Unknown but intentionally excluded facts.
- Forbidden claims.
- Whether the product brief must be revised before proceeding.

#### Purpose-based design references and favorites

Create `大牌设计案例与版式库.md` for the current product before style recommendation and follow `references/reference_discovery.md`.

- Use competitor A+/listing material for selling-point order, purchase reasons and proof logic.
- Search `visual` needs such as product finish, lighting, material and scene composition separately from `layout` needs such as headlines, parameter hierarchy, icons and reading rhythm. A case may serve one purpose only.
- First retrieve compatible favorites, then add new cases and explore authors, studios and related projects. Design sites are useful sources, not a fixed list or quota.
- Inspect the actual images and remove duplicates, broken sources and unreadable evidence. For layout candidates, visible typography or information organization must exist. Do not ask the user to identify image positions, assign production modules, or explain suitability.
- Present a compact useful batch; stop searching once it covers the current needs with varied choices. Never fill a quota with weak candidates.
- Third-party images contribute design grammar only. They do not change current product facts or authorize copying brand assets, wording or complete compositions.
- Research and copy-architecture drafts may run independently; the controller alone publishes the pool.

#### Simple preference selection and re-search

1. Build the v2 rater with real images, stable ids, visible source links, zoom and applicable-purpose buttons. User choices are 喜欢 / 一般 / 不喜欢; explanation fields are optional and never requested as a gate.
2. Apply a button response through `reference_discovery.py submit`; for explicit current-batch chat instructions use `chat-submit --action ... --user-message ...` and optional explicit sample/axis `--ratings`. Preserve the exact original words; both routes bind pending snapshot hash and round. Whole-batch rejection does not fabricate per-card `-1` values.
3. For `RESEARCH_ALL`, change search terms/sources/directions and replace the current batch. For `RESEARCH_REJECTED`, preserve liked candidate evidence and ratings and replace the rest. A mixed-purpose card keeps only its liked axis for carryover.
4. If a required purpose has no positive anchor, continue reference research automatically after reporting that result. Do not generate images to compensate for a weak reference pool.
5. Once `CONTINUE` succeeds, derive the hash-bound profile from explicit ratings and proceed to the existing A/B/C `STYLE_SAMPLES` comparison. Different visual/layout favorites are valid and do not create an extra pairwise gate or a profile-approval question.
6. Add explicitly liked purpose/evidence to the curated library. New library matches must be rated again for the current project; automatic library retrieval never means current approval.

### 4. Three Comparable Style Samples

1. Generate exactly three written Style Specs: A, B, and C. All three must inherit the approved visual system, layout system, hybrid recipe, and rejected patterns from `visual_preference_profile.json`; vary only a bounded execution dimension so the user is not asked to re-choose already rejected styles.
2. Use the same representative slot, product angle, selling point, and copy burden across all three styles so the comparison is fair.
3. Generate exactly one representative image per style, three images total. When subagent capacity is available, dispatch A, B, and C as three independent `IMAGE_WORKER` tasks from one immutable comparison packet and generate them in parallel.
4. Prefer an A+ hero slot when A+ is requested; otherwise use a secondary-main/core-feature slot.
5. Do not use the strict white-background MAIN image as the default style-comparison slot because it reveals too little style difference. The required white-background references should already have been created and approved near the beginning of the workflow.
6. Each sample must use `DIRECT_IMAGE_INPUT` with the smallest valid reference subset from the approved library and/or source photos. Use `VISUAL_CONTEXT_RELAY` only as the documented fallback.
7. After all three return, batch-append the image2 route, prompt hash, exact reference paths/hashes, elapsed time, dimensions, output hash, and current `visual_preference_profile_sha256` to `generation_ledger.jsonl`.
8. Style image workers use `MINIMAL_GENERATION_RECEIPT`, not narrative reports. Run a read-only `QC_WORKER` comparison only after all three samples return; the controller owns the recommendation.
9. Stop only after all three files and ledger records validate, then ask the user to choose A, B, or C. Evaluate visual and layout separately when explaining the choice.

Do not generate three representative images per style unless the user explicitly asks for expanded style validation.

### 5. Production Context Pack And Same-Task Continuation

After style choice:

- Confirm that `production_scope.json` has complete aggregate counts; a Premium carousel assignment may remain `DEFERRED_TO_LAYOUT_MATRIX` until the formal layout matrix.
- Create compact `production_handoff.md` and `production_context_pack.md`.
- Treat those files as the controller's compact production context for subagents and recovery, not as a reason to start another task.
- Include the version `1.0.0` direct visual-input and provenance gates, `visual_preference_profile.json` visual/layout systems and rejected patterns, positive creative-direction prompt rules, product-exposure role check, thin-worker production contract, and `4:5 portrait` main-image numeric ratio prompt rule in the context. Before prompt writing, each formal production slot must define `模块任务` / image task, `产品角色` / product role, product exposure level `P0`-`P4`, product reference and angle, and `重复风险` / repeat risk.
- Include the No-product challenge: if removing the product does not weaken necessary buyer proof, the slot should become a product-free module (`P0`) or a local/detail proof (`P1`), not another complete product.
- Include the Visual Repetition Gate: if many slots use the same product reference and angle, the same small product on furniture, or the same complete-product corner anchor, repeat risk is high and the matrix must revise before prompts.
- Do not require a fixed P0/P1 count. If every slot shows the product, the context pack must explain why each appearance is visually and functionally different; role-label differences alone are not enough.
- `SAME_TASK_CONTINUATION`: perform the phase-boundary state refresh and immediately continue from `CONTEXT_PACK_PREP` to the canonical `PRODUCTION_PLAN`, derive the matrix/prompts/task scaffolding, then invoke `amazon-image-production-runner` inside the current task. Do not stop for another user message merely because the context files were written.
- Pass only immutable facts, selected-style decisions, exact paths, current stage, and task-specific inputs to each subagent. Do not paste the full conversation into worker packets.
- `OPTIONAL_CONTEXT_HANDOFF`: offer or create a compact new-task continuation only when the user explicitly requests it, or when the current task has a real technical recovery condition that prevents safe continuation. Context length by itself is not a mandatory gate.

If `OPTIONAL_CONTEXT_HANDOFF` is actually triggered, use this compact continuation structure:

```markdown
请在新任务继续这个 Amazon 主图/A+ 正式生产项目。
项目根目录：`<root>`
选中风格：`<style>`
生产范围：读取 `<production_scope.json>`
必须读取：`<production_context_pack.md>`、`<production_handoff.md>`、`<01_product_truth.md>`、`<03_product_detail_locks.md>`、`<90_reference_selection_guide.md if present>`
恢复位置：`<next slot or from scratch>`
生成规则：优先使用 `DIRECT_IMAGE_INPUT`，把该 slot 的精确本地参考图/源图通过生图工具原生引用输入传入；只有原生附件不可用时才回退到 `VISUAL_CONTEXT_RELAY`，紧邻生图前用 `view_image` 加载并带 `NO VIEW_IMAGE INPUT` canary；读取并执行 `visual_preference_profile.json` 的画面系统、排版系统、混合规则和拒绝项；在生图阶段边界批量写入 `generation_ledger.jsonl`；禁止把 Markdown 贴图、文件名、prompt 路径文字、旧聊天视觉上下文或 `TEXT_ONLY` 当作正式参考输入；正式提示词执行 `POSITIVE_CREATIVE_DIRECTION`、`ONE_VISUAL_MEMORY_POINT`、`COPY_OCCURRENCE_RULE` 和 `EVIDENCE_BASED_OMISSION`；`4:5 portrait` 主图 prompt 必须 apply stable runner 1.0.0 Main 4:5 Image2 Ratio Prompt Rule；以 `production_plan.json` 为唯一槽位事实源；Premium A+ 只使用 static modules / carousel modules；如果 `carousel_assignment_status` 为 `DEFERRED_TO_LAYOUT_MATRIX`，先根据页面展示逻辑完成计划，再写回 `RESOLVED` 和精确 `carousel_modules`，禁止在解析前写 prompt。
执行：调用 `amazon-image-production-runner` 并读取 `references/agentic_production_contract.md`；先矩阵、prompt、prompt QC；取消所有 smoke，把全部独立 MAIN/A+ slot 一次加入统一队列，固定 3 个薄生图子智能体持续补位；所有 raw 图完成后再并行派发产品结构、文案风格、尺寸技术 3 个专职 QC；只返工失败 slot。
导出规则：image2 负责构图和内容；stable 原图必须与目标比例精确一致，只允许等比例 resize。不得裁切、补边、拉伸、拼接或手工排版；任何比例不符回到 image2 返工该 slot。
Worker 规则：图片 worker 只接收 task/slot、prompt、原生参考路径和唯一输出路径，只返回最小回执；非图片/QC worker 只有实际派发时才创建 packet/report。
```

### 6. Formal Production

The formal production controller must:

1. Read the handoff/context files and `production_scope.json`.
2. Read stable runner `references/layout_matrix_contract.md`, `references/product_exposure_role_check.md`, and `references/slot_manifest_contract.md`. Create one approved `production_plan.json`, binding the current `visual_preference_profile_sha256` and including module task, product role, product exposure level, product reference and angle, product appearance reason, repeat risk, prompt, expected copy, duration, and independence for every slot. Resolve any deferred Premium carousel assignment first.
3. Run `derive_production_artifacts.py`; it publishes the matrix, prompts, task/registry scaffolding, and preflight spec. Change the plan and rederive instead of editing duplicates.
4. MAIN and A+ `PROMPT_WORKER` tasks may run in parallel from the approved matrix. Fact, copy, visual-planning, and platform `QC_WORKER` reviews may also run in parallel, but the controller must publish one reconciled final prompt set.
5. Apply `NO_SMOKE_GATES`: add all approved independent MAIN/A+ slots to `UNIFIED_READY_QUEUE` before the first formal image call.
6. Freeze every prompt, native reference path, and unique `raw_generated/<canonical-name>` path before dispatch.
7. Run `PHASE_BOUNDARY_SCHEDULER` once, then keep three `THIN_IMAGE_WORKER` lanes filled under `FIXED_THREE_LANE` / `STEADY_WORKER_POOL`. Refill on completion events; do not wait for fixed mini-batches.
8. Each image worker calls image2 once and returns `MINIMAL_GENERATION_RECEIPT`; it does no Skill reading, visual inspection, QC, scheduler refresh, state scan, report writing, or manifest work.
9. After every raw slot exists, batch-record successful receipts/provenance, run deterministic preflight once, and only then apply `GENERATION_FIRST_QC_AFTER`. The only mid-phase ledger writes are standardized transport failures and their successful recovery boundary.
10. Dispatch exactly three QC workers concurrently: product truth/structure, copy/style, and aspect/dimensions/technical. Each writes its named JSON profile; the controller writes separate hash-bound MAIN/A+ verdict JSON files that merge exact failed slot ids.
11. Rework only failed slot ids, then rerun preflight and only the affected QC profiles. Update state, checkpoint, partial manifest, and final manifest only at phase boundaries.

Worker/subagent rules:

- Read `references/agentic_workflow_contract.md` in the main task and carry its immutable facts into the runner context.
- The production controller may execute a batch directly under `SEQUENTIAL_FALLBACK`.
- Create a worker packet and registry entry only when a worker is actually dispatched (`WORKER_PACKET_REQUIRED`).
- Image workers write one unique raw file directly and return a minimal receipt; do not create image report templates or require narrative reports.
- Non-image and QC workers still require their matching task-scoped reports.
- Apply `CONTROLLER_SINGLE_WRITER`, `BOUNDED_PARALLELISM`, `ONE_WORKER_ONE_SLOT`, and `NO_SHARED_WRITES` throughout production.
- Apply `EVENT_DRIVEN_WAIT`; do not busy-poll dispatched workers or rerun the state scanner after every result.
- The three post-generation QC workers are required for full formal production and do not replace the controller verdict. A legacy Markdown `Status: PASS` report cannot satisfy `MACHINE_QC_GATE`.
- No extra user-visible QC task is needed.

## Batch and QC Rules

- The normal path is one unified three-lane raw generation queue, then one centralized three-profile QC phase.
- Do not default to arbitrary 3-5 image mini-batches.
- Prompt QC must pass before the full raw generation queue starts.
- Prompt QC must include Product Exposure Role QC plus the Visual Repetition Gate: check whether adjacent or high-similarity slots repeat the same product reference, angle, size, scene, placement, and product role. This QC must not require any fixed P0/P1 count, but it must fail or revise generic "show the product" reasoning, role-label-only differences, or repeated same-angle complete-product anchors.
- Finished-image QC must score product credibility, selling-point clarity, visual impact, layout maturity, text readability, and size/aspect correctness.
- Product credibility must be at least 4/5; the overall average across the scored dimensions must be at least 4/5. For `P0` slots, product credibility means claim accuracy, no unsupported product implication, and no unintended product depiction.
- Blocking failures include structural drift, wrong selling point, unreadable/garbled key text, missing product when the matrix requires `P1`-`P4`, any raw aspect-ratio mismatch, visible distortion, any need for crop/pad/manual composition, or layout/readability failure.
- Route failures back to reference strategy, product truth/detail locks, matrix, prompt, generation variation, or export as appropriate.
- Do not blindly regenerate the whole set.
- If only visual impact is weak while product credibility and selling-point clarity pass, ask before spending another generation.
- Default maximum: two automatic rework rounds per QC problem.

## Output Format Gates

### Main images

- Ask for the actual number and whether `1:1`, `4:5`, or both are required.
- Keep the first strict Amazon MAIN image clean and product-only unless the user explicitly requests another compliant test.
- Recommended export minimums: `2000x2000` for `1:1`, `2000x2500` for `4:5`.
- For `4:5` main prompts, carry the stable version `1.0.0` numeric canvas wording into the runner context and require raw-size/aspect QC after image2.
- When both ratios are requested, use separate matrix rows/prompts unless the composition is demonstrably crop-safe.

### Basic A+

- Ask for the actual image count.
- Each image is `960x600`.

### Premium A+

- Ask for the actual module count.
- Standard desktop/mobile pair: `1464x600` and `600x450`.
- Ask for total desktop/mobile image counts at scope confirmation. Decide carousel modules and slide counts only after page-display logic exists; otherwise defer them to the layout matrix.
- Carousel images use the full canvas by default; place important content according to the slide composition and normal readability/crop checks.
- Premium A+ uses fixed static modules or carousel modules in this workflow.

## Reference Selection Gate

Before every sample or production image:

1. Define the product view, slot purpose, selling point, high-risk details, module task, product role, product exposure level, product reference and angle, No-product challenge result, and repeat risk when a production matrix exists.
2. Choose the smallest valid subset:
   - one main/source reference for global shape;
   - one angle reference only when the view differs;
   - one structure reference only when a named structure matters;
   - one evidence/source-only image only for a named local detail.
3. For `P0` production slots, use zero product references unless a non-product visual reference is needed for scene/style; do not describe or imply the product in the prompt.
4. For `P2` supporting-product slots, do not reuse the default complete front angle by habit. If the product is only a visual anchor, remove it, crop it, switch to a local/detail reference, or use a result/interface/scene-led composition.
5. State each reference role in the prompt.
6. If references conflict, global shape follows the main/source reference; local evidence controls only the named area.
7. Load relevant rows from `03_product_detail_locks.md`.
8. Execute the visual-input gate: prefer native referenced-image attachment with the selected local path(s); use the adjacent `view_image` relay only as fallback. Markdown display and prompt-only path text do not satisfy this gate.

Typical reference count:

- `P0` no-product production slot: 0 product references.
- Simple front/main image: 1.
- Angled or lifestyle image: 1-2.
- Technical/A+ detail image: 2-3.
- Rarely exceed 3.

## State and Response Contract

`design_workflow_state.json` is the canonical machine-readable state. `design_workflow_state.md` is a compact human summary and must not repeat the full transition table, fixed rules, or artifact inventory. Generate both only at the boundaries listed in `STATE_REFRESH_BUDGET`, not as a polling mechanism.

Every state response must include only:

```markdown
## Stage
- Code:
- Label:
- Image Generation Allowed:

## Completed
- ...

## Blocked
- Yes/No:
- Reason:

## Missing
- ...

## Next Step
<one concrete action>
```

Do not repeat questions already answered in `production_scope.json`, `reference_strategy.json`, state JSON, or project files.

## Script

```powershell
$env:PYTHONUTF8='1'
& '<python.exe>' '<skill-dir>\scripts\design_workflow_state.py' --project-root '<project-root>'
```

Options:

- `--dry-run --json`: print canonical JSON without writing files.
- `--dry-run`: print compact Markdown without writing files.
- `--selected-style '<style name>'`: record the user-selected style.
- `--legacy-copy`: also write the old `设计流程状态.md` compatibility copy.
