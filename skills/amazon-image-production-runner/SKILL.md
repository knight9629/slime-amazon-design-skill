---
name: amazon-image-production-runner
description: "Use when the Amazon design orchestrator reaches selected-style formal production with a compact context pack, or when the user has already confirmed a selected style and explicitly asks for a complete main-image/A+ production run. Do not use for ordinary 主图+A+ requests that still need research, reference preparation, style comparison, or scope design."
---

# 亚马逊完整出图

Skill version: `1.0.0`


This is the stable `1.0.0` production runner. Ordinary Amazon main-image/A+ requests enter through `amazon-ai-design-workflow-orchestrator`; this runner requires a confirmed selected-style production context.

## Goal

Run the formal production step after a style, scope, Product Facts Gate, and compact production context have already been confirmed. The orchestrator should normally invoke this runner inside the same task.

This skill is the exception to the user's ordinary "one final AI image" default. Use it only for a selected-style formal production context or an explicitly confirmed selected-style production run. Route an ordinary `主图+A+` request to `amazon-ai-design-workflow-orchestrator`; use image generation directly for an ordinary one-image task.

The stable runner inherits the current full-flow gates: `FULL_FLOW_EXCLUSIVE_CONTROL`, `ONE_MESSAGE_SCOPE_INTAKE`, `REFERENCE_FIDELITY_LOCK`, `VISUAL_PREFERENCE_CALIBRATION`, `IMAGE2_PROVENANCE_GATE`, `CANONICAL_PRODUCTION_PLAN`, `FIXED_THREE_LANE`, `PHASE_BOUNDARY_SCHEDULER`, `DETERMINISTIC_PREFLIGHT`, and the positive creative-direction prompt contract. It may not replace formal generation with brainstorming/HTML, collapse visual/layout preferences into one vague style label, accept style files without `generation_ledger.jsonl`, or treat `OCR_UNAVAILABLE` as text `PASS`.

`SCHEDULER_STATE_GATE`: before formal generation, create one `PHASE_BOUNDARY_SCHEDULER` state for the active run. The normal recommendation is 3. Recompute only at a generation/QC boundary, recovery, or material transport error—not after each successful image.

Before generating, first confirm what the user wants to produce:

- Main images or A+ images.
- If main images, `1:1`, `4:5 portrait`, or both; both formats require separate `count_by_ratio` values.
- If A+, Basic A+ or Premium A+.
- How many images are needed for each requested deliverable.
- For Basic A+, the standalone `image_count`.
- For Premium A+, the `module_count`, `desktop_image_count`, and `mobile_image_count`; exact carousel mapping may stay `DEFERRED_TO_LAYOUT_MATRIX` until layout planning, but must become `RESOLVED` before prompts. Each carousel module can contain 1-5 images.

Do not assume a fixed 7-image main set. Basic A+ has up to 7 standalone images. Premium A+ has up to 7 modules, but carousel modules can make the desktop/mobile image count larger than the module count.

Premium A+ production supports fixed static modules and optional carousel modules. Express every requested Premium A+ idea through those module types before prompt writing.

Do not use this skill for pre-branch style recommendation or 3-image style sampling. Those belong to `amazon-creative-style-sampler`.

## Inputs

Use the best available local sources:

- Selected branch style or command context, such as `使用设计风格1完整出图`
- Standard white-background product reference image from `product-reference-composer`
- Product local detail locks, such as `03_product_detail_locks.md` or `产品局部细节锁.md`
- `我的产品信息与卖点优先级文档` or equivalent product brief
- `竞品卖点与展示逻辑整理.md` or equivalent competitor logic document
- `大牌设计案例与版式库.md` or equivalent big-brand design case library
- Approved `visual_preference_profile.json` bound to the current `visual_reference_pool.json`
- The `类目设计思路匹配` / `Category Design Playbook Match` section from the product brief, when present
- `production_context_pack.md` from the orchestrator, when available
- `production_handoff.md` from `amazon-creative-style-sampler`, when available as a compatibility source
- `product_facts_confirmation.md` or equivalent confirmed Product Facts Gate
- `完整出图版式规划矩阵.md` when continuing an approved production plan
- `production_plan.json` as the canonical slot/prompt/task/QC source, with `visual_preference_profile_sha256` matching the current approved profile
- `generation_ledger.jsonl`, `scheduler_state.json`, and `reference_fidelity_lock.json` from the active run
- Output root folder from the user

If the selected style is unclear, ask for the selected style before generating. A new stable run must include an approved `visual_preference_profile.json`; if it is missing, hash-invalid, or does not match `production_plan.json.visual_preference_profile_sha256`, return to `VISUAL_PREFERENCE_CALIBRATION` or rebuild the stale plan. For an explicit legacy selected-style production request with no workflow-version marker and no preference artifacts, record that the profile gate is not available instead of fabricating ratings. Creating either preference artifact opts the project into the full gate. If `product_facts_confirmation.md` is missing or product facts are incomplete in a way that affects claims, visual modules, scale, package/accessory display, compliance, or buyer proof, stop and ask for Product Facts Gate confirmation. Do not treat cautious wording as enough for formal production.

## Agentic Production Mode

Read `references/agentic_production_contract.md` before dispatching production subagents. Before plan/export work, read `references/layout_matrix_contract.md`, `references/product_exposure_role_check.md`, and `references/slot_manifest_contract.md`; scope follows the stable orchestrator `references/production_scope_contract.md`, and preferences follow its `references/reference_discovery.md`. Use the available subagent mechanism such as `spawn_agent` only for independent work with non-overlapping outputs.

- `CONTROLLER_SINGLE_WRITER`: the production controller alone publishes the official matrix, final prompt set, controller QC verdict, checkpoint, partial manifest, and final manifest.
- `CONTROLLER_PLUS_THREE`: Codex has 4 total concurrent agent slots; the controller uses one and may keep up to 3 child workers active.
- `NO_SMOKE_GATES`: reference, MAIN, and A+ smoke tests are disabled. Approved prompts/references unlock the complete raw queue.
- `UNIFIED_READY_QUEUE`: merge every approved independent MAIN and A+ slot into one cross-batch generation queue before the first call while preserving separate MAIN/A+ QC verdicts.
- `FIXED_THREE_LANE`: under `STEADY_WORKER_POOL`, keep 3 child image workers active whenever at least 3 ready slots remain and refill on completion events.
- `PHASE_BOUNDARY_SCHEDULER`: successful latency does not reduce concurrency or stale the scheduler. Only a transport error/recovery or phase boundary may recompute it.
- `THIN_IMAGE_WORKER`: an image worker receives only task id, slot id, immutable prompt, native reference paths, and one unique raw output path. It does not read Skills/project documents, inspect images, run QC, refresh state/scheduler, or write a long report.
- `FRESH_IMAGE_CONTEXT`: create each image worker with no inherited conversation (`fork_turns="none"` or equivalent) and inline the five packet values. The worker must not open a packet file before image2.
- `MINIMAL_GENERATION_RECEIPT`: an image worker returns only task/slot, status/standardized error, output path when successful, and elapsed time. The controller batch-records successful receipts/provenance when the generation phase closes.
- `STANDARD_TRANSPORT_FAILURE`: failure receipts use `AUTH`, `NETWORK`, `RATE_LIMIT`, `TIMEOUT`, `TRANSPORT`, or `OTHER`. A transport failure is written to the ledger immediately at the recovery boundary before scheduler refresh; the first successful recovery attempt is also written immediately before restoring three lanes.
- `GENERATION_FIRST_QC_AFTER`: do not assign finished-image QC while raw generation slots remain. After all raw outputs exist, dispatch exactly three dedicated read-only QC workers for product truth/structure, copy/style, and aspect/dimensions/technical.
- `MACHINE_QC_GATE`: require three hash-bound profile JSON files and separate MAIN/A+ verdict JSON files that reference all profile hashes and merge exact failed slot ids.
- `DELEGATION_GAIN_THRESHOLD`: applies to non-image supporting work. Approved image2 slots use thin workers because their parallel gain dominates packet overhead.
- `ONE_WORKER_ONE_SLOT`: each `IMAGE_WORKER` owns exactly one `slot_id`, one raw output path, and one minimal receipt.
- `NO_SHARED_WRITES`: workers may not edit shared prompt, matrix, scope, product-truth, detail-lock, checkpoint, or manifest files.
- `DIRECT_UNIQUE_RAW_WRITE`: each image worker writes directly to its unique `raw_generated/<canonical-name>` path; no two tasks share a file, so controller promotion is unnecessary.
- `NORMALIZED_UNIQUE_PATHS`: resolve and normalize all output paths before collision checks; syntactic aliases to one file are a shared write and must fail.
- `IMAGE_WORKER_REPORT_FORBIDDEN`: image tasks cannot use `required_report_path`, `promoted_output_paths`, or `workers/outputs`; successful `VERIFIED` status requires the inline receipt.
- `FAILED_SLOTS_ONLY`: rework packets target only failed slots and preserve passing originals.
- `COPY_QC`: copy review must be independent from prompt drafting and must check meaning, claim support, rasterized readability, native-copy separation, alt text, and mobile readability.
- `VISUAL_PREFERENCE_CALIBRATION`: before plan/prompt work, the controller resolves the profile into separate visual keep/exclude, layout keep/exclude, hybrid rules, anchor ids, and rejected patterns. The canonical plan binds the exact profile SHA-256; a profile change invalidates the plan. Image workers receive the resulting decisions only inside the frozen prompt; they never read the profile directly.
- `CONTEXT_MINIMIZATION`: image workers receive only the five thin-packet fields. Non-image/QC workers receive only task-scoped facts and paths.
- `SEQUENTIAL_FALLBACK`: when workers are unavailable, capacity is exhausted, or write paths overlap, execute the same work sequentially without creating fake worker packets or reports.
- `EVENT_DRIVEN_WAIT`: use one bounded 60-120 second event wait after dispatch, not repeated 30-second polls or status-list calls.
- `STATE_REFRESH_BUDGET`: refresh workflow state only at recovery, a human-gate transition, a formal phase boundary, a canonical phase-changing mutation, and final verification—not after every slot or wait.
- `READ_ONCE_PER_TURN`: read this Skill and its production contract once per turn unless the files changed, context was lost, or recovery requires verification.
- `INTERRUPTION_RESUME`: after Mac sleep/display-off or network loss, resume from the run files, task registry, receipts, and existing outputs without replaying completed work.

Before any prompt writing or image generation, apply `ONE_MESSAGE_SCOPE_INTAKE`: ask all still-missing production questions in one consolidated message and atomically write `production_scope.json` after the answer. A `production_scope.template.json` is never confirmed scope.

- This run should produce `主图`, `A+`, or both?
- If `主图`, should it produce `1:1`, `4:5 portrait`, or both?
- If `A+`, should it be `基础版 A+` or `高级版 A+`?
- If `基础版 A+`, how many standalone images?
- If `高级版 A+`, how many modules, desktop images, and mobile images?
- If Premium page logic already exists, read its exact static/carousel mapping. Otherwise resolve the deferred mapping in the layout matrix; do not ask for a guessed assignment.

## Output Size Rules

- Main `1:1`: export at the highest practical resolution; recommended minimum `2000x2000`.
- Main `4:5 portrait`: fixed `4:5`, export at the highest practical resolution; recommended minimum `2000x2500`.
- Basic A+: fixed `960x600`, up to 7 independent images.
- Premium A+ desktop: fixed `1464x600`, up to 7 modules.
- Premium A+ mobile: fixed `600x450`, corresponding to Premium A+ modules.
- Premium carousel module: 1-5 images inside one module, each with matching desktop/mobile outputs when mobile is requested or required by the workflow.
- `EXACT_RATIO_EXPORT`: Final generated images must have the correct composition and exact target aspect ratio from image2. Stable export may perform deterministic same-aspect resize only; preserve raw sources and never crop, pad, stretch, stitch, composite or rewrite image content. Any ratio mismatch requires image2 rework.

## Main 4:5 Image2 Ratio Prompt Rule

Use this rule for every `4:5 portrait` main-image prompt. It is based on local image2 ratio testing: direct prompts cannot guarantee exact `2000x2500` pixels, but the numeric canvas wording below was the most reliable way to make image2 return a raw image near true `4:5`.

- Treat the loaded product reference as product-identity authority only, not canvas-ratio authority. This is required when the reference image itself is `1:1`, `3:4`, or any non-`4:5` shape.
- Include this numeric canvas requirement near the top of every `4:5 portrait` main prompt:

```text
Canvas requirement: exact portrait 4:5 aspect ratio. Target canvas: 2000 px wide x 2500 px tall. Width:height must be 4:5.
```

- Include this explicit ratio exclusion in the same prompt:

```text
The image must not be square, not 3:4, not 2:3, not 9:16, and not horizontal.
```

- Do not rely on soft wording such as `vertical product card`, `balanced portrait`, or `not a narrow poster` by itself.
- After image2 returns a raw file, verify pixel dimensions, exact aspect ratio, and visual integrity. Any ratio mismatch must be reworked through image2; never crop, pad, stretch, stitch or compose a wrong image into `4:5`.

## Output Folders

Create one folder per selected style. Use these subfolders:

- `prompts`
- `raw_generated`
- `main_1x1`
- `main_portrait` when portrait main images are requested
- `a_plus_basic` when Basic A+ is requested
- `a_plus_premium_desktop` when Premium A+ is requested
- `a_plus_premium_mobile` when Premium A+ mobile outputs are requested
- `preview`
- `workers/outputs/<task_id>` only for dispatched non-image workers that need a staged draft

If continuing inside a style-sample branch that already has `samples`, leave it intact. Do not put full production outputs into `samples`.

## Image2 Visual Input Gate

Formal production must pass real image evidence through a supported visual-input route.

`IMAGE2_PROVENANCE_GATE`: preserve run/stage/slot, route, prompt hash, exact reference paths/hashes, start/end/elapsed, output dimensions/path/hash, and status for every image2 attempt. During parallel generation, collect successful `MINIMAL_GENERATION_RECEIPT` values and batch-append them at the phase boundary. The recovery exception is `STANDARD_TRANSPORT_FAILURE`: write the failed attempt immediately, refresh scheduler, and write the first successful recovery attempt before restoring three lanes. Prompt prose is not a substitute.

- Preferred route: `DIRECT_IMAGE_INPUT`. Pass the exact selected local path(s) through the image-generation tool's native referenced-image input. Prompt-only path strings do not count.
- Inspect each selected source before its first use. For multi-reference slots, keep the subset minimal, label each reference role, and identify the controlling product reference.
- Fallback route: `VISUAL_CONTEXT_RELAY`. Use it only when native referenced-image attachment is unavailable; open/load the exact source with `view_image` immediately before generation and include the canary `NO VIEW_IMAGE INPUT`.
- For `P0` no-product slots, do not attach product references. Attach a non-product scene/style reference only when it materially controls the result.
- Markdown display, filenames, old chat memory, old screenshots, and prompt-only paths are diagnostic context, not formal product authority.
- Any output that ignores attached evidence, shows the fallback canary, or contradicts product truth fails post-generation QC.

## Workflow

1. Resolve the selected style.
   - Use the current branch context, latest style recommendation, or user command.
   - Prefer the selected branch's `production_context_pack.md`; use `production_handoff.md` as a compatibility source when needed.
   - Keep the style name, inherited `Style Spec`, and strategic role in the prompt document.

2. Read upstream artifacts.
   - Standard white-background product reference image: shape, color, lens, stand, ports, material, visible accessories.
   - Local detail locks: high-risk buttons/knobs, grilles, logos, ports, hinges, labels, accessories, package contents, and forbidden distortions.
   - Product brief: confirmed selling points, risky claims, main image logic, A+ logic.
   - Category design playbook match from the product brief: selected playbook, confidence, category image tasks, buyer results, proof methods, human-presence guidance, and rejected playbooks.
   - Competitor logic: category norms and display priority only. Do not copy competitor layouts.
   - Big-brand design cases: current design patterns, layout variety, hierarchy, scene grammar, and mature module ideas. Do not copy exact brand layouts or assets.
   - Visual preference profile: apply `visual_system.keep/exclude` only to color, light, material, photography, and atmosphere; apply `layout_system.keep/exclude` only to type, copy hierarchy, icons, grid, whitespace, and reading rhythm. Use the corresponding anchor ids and `hybrid_recipe.rules`; enforce every `rejected_patterns` item.
   - Production context pack: approved style cues, elements to preserve, rejected cues if any, reusable mother-image candidates, and non-negotiable prompt constraints.
   - Human-use scene suitability from the selected `Style Spec` or production context; if missing, run the gate below before creating the matrix.
   - Product-exposure role check from the production context when present; otherwise apply the default `P0`-`P4` rule below.

3. Apply the category design playbook gate.
   - If the product brief has a `high` confidence matched playbook, use its category design tasks as inputs to the layout matrix.
   - If the product brief has a `medium` confidence match, use only the explicitly borrowed tasks and keep uncertainty in the matrix.
   - If there is no match or confidence is `low`, do not use category playbook assumptions.
   - Do not use any rejected playbook trope. For example, do not apply apparel self-appearance/social-attention logic to projectors, appliances, tools, or furniture.
   - Product truth, allowed claims, local detail locks, and selected style always outrank the category playbook.
   - Third-party reference anchors provide design grammar only. They never authorize copied logos, brand assets, exact wording, protected layouts, or unsupported product geometry.

4. Run the human-use scene suitability gate.
   - Classify whether real user presence is `high`, `medium`, or `low` value for this product.
   - Use `high` when conversion depends on scale, operation, wearing/holding, comfort, sensory effect, fit, portability, room placement, or daily-use trust. Examples: fans, personal care, beauty tools, kitchen tools, home comfort products, fitness gear, wearables, handheld tools, pet/baby-adjacent products, and furniture.
   - Use `medium` when people help scale or scene credibility but are not the main proof.
   - Use `low` when a person would distract from technical detail, create compliance risk, or conflict with the requested clean product/diagram image.
   - For `high` or `medium`, define allowed person expressions: front face, side face, upper body, hands, partial body, product operation, product placement, user feeling the benefit, or user scale reference.
   - Do not avoid faces or hands by default. image2 can generate people directly; choose the strongest commercial expression for the product.

5. Apply the product-exposure role check.
   - Core principle: each image should first define what persuasion task it performs, then decide whether the product needs to appear. Product appearance is useful only when it improves recognition, proof, understanding, or trust.
   - Before prompt writing, mark four fields for every slot:
     - `模块任务`: what this image is responsible for, such as product recognition, function proof, parameter explanation, usage scene, user result, detail proof, accessory/package proof, or trust building.
     - `产品角色`: whether the product is the hero, evidence, detail, scale reference, background support, or absent.
     - `露出等级`: one `P0`-`P4` level.
     - `重复风险`: low, medium, or high; judge whether this slot repeats nearby slots in product angle, size, scene, composition, or product role.
   - No-product challenge: before assigning `P1`-`P4`, ask whether the image would lose necessary buyer proof if the product disappeared. If the answer is no, make it a product-free module (`P0`) or use only local/detail evidence (`P1`) instead of placing another complete product.
   - Visual Repetition Gate: role labels are not enough. If multiple slots use the same product reference and angle, the same front three-quarter product on furniture, or the same small-product-in-corner pattern, repeat risk is high even when module tasks differ.
   - Assign every slot one product exposure level:
     - `P0` no product: scene result, user state, parameter structure, icons, brand mood, or abstract proof.
     - `P1` product detail: button, port, material, structure, accessory, operation detail, or partial product edge.
     - `P2` supporting product: product appears small, backgrounded, cropped, or off-center.
     - `P3` complete product: product appears complete and clear as one main information carrier.
     - `P4` hero product: product is large, central, and strongly recognizable; use for main hero, structure, size, or core proof slots.
   - Do not set a fixed quota such as "at least N images without product". Different products and marketing systems need different exposure frequency.
   - All slots may show the product only when every appearance has a meaningfully different product role, product reference, angle, scale, placement, scene, and proof function. A different `产品角色` label alone does not pass.
   - For app access, wireless/connectivity diagrams, parameter dashboards, screen-result modules, and scenario carousels, first test a product-free module direction. These modules often communicate better through interface, icons, screen result, user state, or environment alone.
   - If more than half of the non-hero slots rely on the same complete-product reference and similar front angle, the matrix must revise before prompting. Use `P0`, `P1`, rear/side/detail references, partial crops, silhouettes, result-led scenes, interface-led layouts, or a truly different product angle.
   - If repeat risk is high, revise the matrix before prompting: remove the product, change the product reference, change the product role, use a local detail, crop the product, reduce scale, change angle, change scene, make parameter/result/user state the visual lead, or use a `P0` no-product composition.
   - This rule does not weaken product-fidelity requirements. When the matrix requires `P1`-`P4`, preserve the confirmed product truth and local detail locks; when it assigns `P0`, do not fail the image merely because the product is absent.

6. Apply `CANONICAL_PRODUCTION_PLAN` before prompts.
   - Apply the preserved stable scope/layout contracts: separate counts for both main ratios; resolve Premium carousel mapping before prompts; derive an explicit `slot_manifest.json` for carousel slides using `references/slot_manifest_contract.md`.
   - Write one approved `production_plan.json` with the current `visual_preference_profile_sha256` and every slot, target, module task, role/exposure, reference subset, prompt, expected copy, estimated duration, and independence flag.
   - Run `derive_production_artifacts.py` to generate `完整出图版式规划矩阵.md`, `prompts/full_production_prompts.md`, worker packet/report templates, `agent_task_registry.template.json`, and `preview/preflight_qc_spec.json`.
   - If a slot fact changes, edit the plan and regenerate derived files; never hand-maintain conflicting copies.
   - A `LAYOUT_WORKER` and `COPY_WORKER` may prepare separate read-only-input drafts in parallel. They must write separate draft paths. The controller resolves conflicts and publishes the only official matrix.
   - Build one row per requested image.
   - Each row must include: slot id, deliverable type, format, purpose, module task / `模块任务`, product role / `产品角色`, product exposure level `P0`-`P4`, product appearance reason, repeat risk / `重复风险`, product reference and angle, output size, layout type, product view/angle, scene/background, primary selling point, category design task, buyer result, proof method, best scene, text hierarchy, `image_embedded_copy`, `native_headline`, `native_body`, `alt_text`, `mobile_readability`, human-use requirement, person expression, interaction action, reference subset and role priority, local detail locks to invoke, big-brand design inspiration pattern, misfit tropes to avoid, and avoid list.
   - For main images, include `format` as `1:1` or `4:5 portrait`.
   - For every `4:5 portrait` main-image row, mark that the prompt must use the Main 4:5 Image2 Ratio Prompt Rule.
   - For Basic A+, include `a_plus_type` as `Basic` and `image_count`.
   - For Premium A+, include `a_plus_type` as `Premium`, `module_count`, `desktop_image_count`, `mobile_image_count`, `module_id`, `module_type` as `static` or `carousel`, and `carousel_slide` when relevant.
   - For Premium A+, use only module-level fields and carousel slide fields.
   - For Premium carousel outputs, use normal layout, crop, and readability checks for the slide composition without adding an automatic reserved band.
   - Layout diversity rule: the same layout type may appear at most twice in one production run unless the user explicitly asks for repetition.
   - Use varied layout types such as centered hero, left-product/right-copy, right-product/left-copy, top-bottom split, horizontal panorama, three-panel scenario, detail close-up grid, step-by-step strip, comparison band, modular icon row, and full-bleed lifestyle with overlay text.
   - Do not use "left text, right product" as the default. Treat it as one possible layout type.
   - Human-use scenes are a recommendation, not a quota. Add people only when they materially improve scale, operation proof, fit, emotional readability, or trust for that slot.
   - Human-use scenes can use clear front faces, side faces, upper bodies, or hands when they improve the picture. Prefer real interaction over empty room scenes.
   - Do not put `no people`, `no hands`, or `no face` into global negative constraints. Apply those only to product-only slots, pure technical diagrams, package-only images, or explicit user restrictions.
   - Save the matrix in the selected style folder or project root.

7. Write prompts first.
   - Save one prompt document in `prompts`, for example `full_production_prompts.md`.
   - Include image slots, size targets, selected style, source paths when used, layout matrix rows, module tasks, product roles, product exposure levels, repeat risk, category design tasks, local detail locks, reusable mother-image plan, fixed prompt constraints, and the prompt preflight result.
   - Apply `POSITIVE_CREATIVE_DIRECTION`: write every image prompt as a positive, complete art-direction brief rather than a list of facts plus vague style adjectives.
   - Apply `ONE_VISUAL_MEMORY_POINT`, `COPY_OCCURRENCE_RULE`, and `EVIDENCE_BASED_OMISSION` before prompt QC. Define composition variety directly from the current slot objective, visual memory point, spatial relationships, and read order.
   - For `4:5 portrait` main images, include the exact numeric canvas requirement and ratio exclusion from the Main 4:5 Image2 Ratio Prompt Rule.
   - Run the prompt preflight check below before writing any production prompt.
   - Do not generate images until the prompt document is written.
   - MAIN and A+ `PROMPT_WORKER` tasks may draft separate prompt groups in parallel after the official matrix and Premium carousel mapping are final.
   - Dispatch independent `QC_WORKER` profiles for fact QC, `COPY_QC`, visual repetition/exposure QC, and platform/ratio QC when capacity is available. The controller must reconcile all blocking findings before publishing the final prompt set.

8. Generate the complete raw set with image2.
   - Use image2 as the complete production path for visuals, text, icons, parameters, badges, and composition.
   - Before every product-referenced image2 call, execute the visual-input gate above, preferring native referenced-image paths.
   - Record the attached source path(s), route, reference roles, and controlling reference in the prompt document and append the machine-verifiable attempt to `generation_ledger.jsonl`.
   - Do not switch to PPT, HTML, canvas, manual local compositing, or hybrid workflows unless the user explicitly asks for a different production method.
   - Freeze the complete slot list, prompts, native reference paths, and unique `raw_generated/<canonical-name>` paths before dispatch.
   - Apply `NO_SMOKE_GATES`; every approved independent MAIN/A+ slot is ready from the first dispatch.
   - Create a five-field thin image packet only: `task_id`, `slot_id`, `prompt`, `referenced_image_paths`, and `output_path`.
   - Under `FIXED_THREE_LANE`, start three thin workers whenever three ready slots exist. Refill a lane immediately on completion without waiting for the other active calls.
   - Each worker calls image2 once, writes only its unique raw file, and returns `MINIMAL_GENERATION_RECEIPT`. It must not read this Skill, inspect the output, run acceptance/QC, update state/scheduler/ledger, or create a report file.
   - Keep successful receipts in the controller until the raw set closes, then batch-append provenance and update the registry/checkpoint once.
   - If a material transport error occurs, write its standardized failed ledger record immediately, then refresh `PHASE_BOUNDARY_SCHEDULER` for recovery. Write the first successful recovery attempt immediately before restoring three lanes. Long successful latency alone is not congestion evidence.
   - Use stable names derived from the user-confirmed scope and counts, such as:
     - `main_01_raw.png` ... `main_<count>_raw.png`
     - `main_portrait_01_raw.png` ... `main_portrait_<count>_raw.png`
     - `aplus_basic_01_raw.png` ... `aplus_basic_<count>_raw.png`
     - `aplus_premium_desktop_01_raw.png` ... for Premium desktop images
     - `aplus_premium_mobile_01_raw.png` ... for Premium mobile images
   - If both square and portrait main images are requested, write separate prompts for each format unless the specific image is explicitly crop-safe.
   - For Premium carousel modules, keep slide logic consistent inside the module and document the module/slide mapping in the prompt document.
   - Use `EVENT_DRIVEN_WAIT` for worker completion and follow `STATE_REFRESH_BUDGET`; a worker timeout alone is not a reason to run another full state scan.
   - Do not assign two workers the same `slot_id` or canonical raw filename.

9. Run batch image QC before export.
   - First run `scripts/preflight_qc.py` and write `preview/preflight_qc.json`. Check files, hashes, dimensions and expected raster copy before visual QC. Stable export requires exact raw aspect ratios; preflight rejects any ratio mismatch and returns that slot to image2.
   - If the OCR executable is absent or fails, record `OCR_UNAVAILABLE` / `OCR_ERROR`, set `requires_visual_qc`, and continue to visual copy review. Never convert missing OCR evidence into `PASS` or `PASS_WITH_NOTES`.
   - Write exactly three machine profiles: `preview/qc_product_structure.json`, `preview/qc_copy_style.json`, and `preview/qc_technical.json`. Each must reference the current `preflight_qc.json` hash and cover every planned slot.
   - The controller writes `preview/main_batch_qc_verdict.json` and/or `preview/aplus_batch_qc_verdict.json`; every verdict references all three profile paths/hashes and merges their exact failed slot ids and blocking findings.
   - Batch QC must score product credibility, selling-point clarity, visual impact, layout maturity, text readability, and size/aspect correctness. `QC_COPY_STYLE` also blocks unapproved extra copy, repeated key values, competing memory points, and visualized objects or product states that lack appearance evidence.
   - Product credibility must be at least 4/5, and the overall average across the scored dimensions must be at least 4/5.
   - If QC fails, rework only the failed slots through image2. Do not blindly regenerate the whole set.
   - Do not export final files until `MACHINE_QC_GATE` validates every required profile and batch verdict. A Markdown `Status: PASS` file is not completion evidence.
   - `GENERATION_FIRST_QC_AFTER`: only after the full raw set and preflight exist, run exactly three parallel read-only `QC_WORKER` tasks: product truth/structure; copy/style/visual selling; aspect/dimensions/technical. Their reports are evidence; the controller writes the authoritative MAIN/A+ batch verdicts.
   - Failed slots may be reworked in parallel only when their write paths are unique. Keep a maximum of two controlled rounds per repeated QC problem.

10. Postprocess locally only for deterministic exact-ratio export.
   - Local tools may create contact sheets, manifests and same-aspect resizing. The raw ratio must already exactly match the target; the previous 0.6.11 bounded-ratio correction is not supported by this stable exporter.
   - Preserve every raw source. Do not crop, pad, stretch, stitch, manually composite, replace text or change layout.
   - If ratio, crop, text placement or visual integrity is wrong, rework only the failed slot through image2.
   - Use `scripts/postprocess_images.py` with the confirmed counts, or `--slot-manifest` for explicit carousel slots. Do not combine the two input modes. See `references/slot_manifest_contract.md` for command and schema.

11. Stop after QC-passing export.
   - Final response should list where prompts, raw files, QC reports, processed no-crop files, previews, and manifests were saved.
   - If any slot still needs image2 rework, say that instead of calling the production complete.
   - Only the controller may run or approve the final export and write `production_manifest.json`.

## Full Production Slots

Build the slot list after the user confirms the requested deliverables and counts.

### Main Image Slot Pool

Choose only as many as the user requested:

1. White-background hero product image.
2. Core conversion selling point image.
3. Smart system or built-in content image, only if confirmed.
4. Picture quality image.
5. Setup, adjustment, support, placement, or operation image; depict only mechanisms and automation explicitly confirmed for the current product.
6. Connectivity and compatibility image.
7. Scenario, package, service, or differentiator image.

### Main Image Format Variants

Use this distinction throughout planning, prompting, and export:

- `1:1`: primary compliant upload-safe format; recommended minimum `2000x2000`.
- `4:5 portrait`: fixed portrait format; recommended minimum `2000x2500`.
- When both formats are requested, do not mechanically crop every `1:1` image. Create format-specific compositions for text-heavy, lifestyle, comparison, and infographic slots.
- The first MAIN image should remain product-only and square unless the user explicitly chooses otherwise.

### Basic A+ Rules, `960x600`

Use when the user chooses Basic A+:

- Fixed output size: `960x600`.
- Maximum: 7 independent images.
- Do not plan Amazon module templates for Basic A+; treat it as a sequence of standalone images.
- Choose only as many images as the user requested.

### Premium A+ Rules, `1464x600` Desktop and `600x450` Mobile

Use when the user chooses Premium A+:

- Premium A+ has up to 7 modules.
- A normal module has one desktop image `1464x600` and one matching mobile image `600x450`.
- A carousel module is still one module, but can contain 1-5 images/slides.
- Every carousel slide in the same module must share one display logic and one user journey.
- Use the full desktop or mobile canvas for carousel slides by default, and place key content according to the slide composition.
- Resolve any deferred carousel assignment from the page-display/layout logic before writing prompts, then update `production_scope.json` to `RESOLVED` with exact `carousel_modules`.
- Premium A+ modules are either fixed static modules or carousel modules.

## Mother-Image Reuse

Reduce quota use by planning reusable visuals before generation:

- One clean white-background product render can support multiple same-aspect export sizes.
- One scenario mother image can serve a main image and an A+ module only when both requested outputs were planned as crop-safe and no local crop is needed.
- Generate product, scene, copy hierarchy, icons, specs, badges, and final visual composition directly with image2 by default.
- Do not switch to local manual layout or mixed workflows unless the user explicitly asks for a different production method.
- Mother-image reuse must not override layout diversity. Reuse a product/scene concept only when the matrix still produces visibly different compositions.

## Fixed Prompt Constraints

Always include these constraints when relevant:

- When a slot shows product (`P1`-`P4`), use the standard white-background product reference image as the single source of product form.
- When a slot shows product (`P1`-`P4`), pass that exact local source through `DIRECT_IMAGE_INPUT`; use adjacent `view_image` relay only as fallback. Path text or Markdown display is not enough.
- Preserve actual product body, lens, stand, ports, logo area, materials, and distinctive structure.
- Preserve local detail locks exactly when visible; do not let image2 reinterpret a locked button, knob, grille, logo, port, hinge, label, or package item.
- Apply category-specific physical and compliance constraints only when supported by the current product truth, matched playbook, or confirmed brief; do not carry another SKU's constraints into this run.
- Do not imply built-in battery or cordless outdoor use unless confirmed in the product brief.
- Do not invent accessories, cables, handles, buttons, ports, screens, apps, or package contents.
- Do not use unauthorized platform logos, certification badges, Dolby/Hi-Res/HDR/ANSI claims, or official authorization claims unless confirmed.
- Put the required text, parameters, icons, badge intent, and layout hierarchy directly into the image2 prompt by default.
- Main image white-background slot must stay product-centered, clean, and Amazon-safe.
- Main `4:5 portrait` prompts must apply the Main 4:5 Image2 Ratio Prompt Rule.
- Final composition and exact aspect ratio must come from image2. Exact pixels may come from same-aspect resize; local crop, pad, stretch, stitching, manual compositing or resizing to hide a failure is forbidden.

## Prompt Preflight Check

Before writing any production prompt, separate and verify:

1. Product truth
   - Confirmed structure, proportions, materials, colors, visible details, supported states, package contents, and approved claims.
   - Details not visible in the source images or not confirmed in the product brief.
   - Product Facts Gate confirmation and any facts intentionally excluded from claims.
   - For slots that show product (`P1`-`P4`), use the standard white-background product reference image as the single visual source for downstream product form unless the user explicitly replaces it.
   - Confirm the selected product reference/source can be passed as a native referenced-image path; record `VISUAL_CONTEXT_RELAY` only when fallback is necessary.

2. Category design task
   - Matched playbook and confidence, or `none`.
   - Category image task, buyer result, proof method, and best scene for this slot.
   - Misfit tropes to avoid, especially rejected category playbooks.
   - Confirm the category task supports the product truth instead of forcing an unrelated emotional or lifestyle trope.

3. Product exposure
   - Module task for this slot: recognition, function proof, experience, parameter, scene, accessory, trust, or closing conversion.
   - Product role: hero, evidence, detail, scale reference, background support, or absent.
   - Exposure level `P0`-`P4` and the reason this level is needed.
   - No-product challenge: if product removal does not weaken recognition, proof, understanding, or trust, use `P0` or a detail-only `P1` instead of another full product.
   - Repeat risk: low, medium, or high. Check whether this slot repeats a prior product reference, product angle, product size, scene, composition, placement, or product role.
   - Visual Repetition Gate: if the slot repeats the same product reference and angle used by prior non-hero slots, mark repeat risk high unless the product is cropped/detail-only or the buyer proof truly depends on that angle.
   - If repeat risk is high, lower exposure or change product role, reference, angle, distance, crop, scene, or information lead before prompting.
   - For `P0`, state what replaces product presence: user result, environment, icon/parameter structure, brand mood, or benefit proof.

4. Scene request
   - Environment, camera angle, support surface, nearby objects, lighting, and desired composition.
   - For `4:5 portrait` main images, confirm the prompt includes the numeric `2000 px wide x 2500 px tall` canvas wording and the ratio exclusions before generation.

5. Fusion requirements
   - Contact point, scale, perspective, light direction, shadow direction, reflection behavior, and material response.

6. Human-use scene check
   - Suitability level and whether this slot must include a real user.
   - Person framing: front face, side face, upper body, hands, partial body, or no person.
   - User action and product relationship: operating a control, feeling airflow, holding, placing, charging, cleaning, sitting at desk, reading beside product, or other product-specific interaction.
   - Person-product scale, gaze/attention, contact point, and distance. The person should strengthen the product benefit, not become unrelated decoration.

7. Conflict scan
   - Remove or soften any request that conflicts with confirmed product truth, visible reference images, package contents, or allowed claims.
   - Do not request hidden structures, unsupported states, or unconfirmed functions just to satisfy a selling-point composition.
   - Product truth outranks scene style and marketing expression.

8. Layout diversity
   - Check whether the proposed image repeats a prior layout.
   - If more than two images use the same structure, change the layout before prompting.
   - Check whether too many adjacent slots use `P3` or `P4` with similar product size, angle, scene, and role; revise before prompting.
   - Check whether more than half of non-hero slots rely on the same complete-product reference and similar front angle; if yes, revise before prompting even if the written product roles differ.
   - Do not force a fixed P0/P1 quota. The check is whether product appearances are visually and functionally different, not whether the set reaches a fixed no-product count.

9. Local detail locks
   - List every lock triggered by the image.
   - Include forbidden distortions in the negative constraints.

10. Creative direction
   - Define the buyer's first-glance takeaway and one dominant visual memory point.
   - Define the first visual lead, product role, product scale/placement, foreground-midground-background relationship, and reading order.
   - Specify visible art-direction choices: light direction, tonal contrast, restrained palette, material response, depth, texture, and commercial finish.

11. Copy occurrence and evidence boundary
   - List every exact rasterized copy string and confirm that every string and key sub-value appears once unless repetition is explicitly required.
   - If an included accessory, internal structure, or changed product state lacks appearance evidence, keep the confirmed fact as copy only and omit every invented object/icon/diagram shape.

## Prompt Structure

`POSITIVE_CREATIVE_DIRECTION` requires a complete positive visual brief. Use the following Chinese structure by default; compress sections that genuinely do not apply, but never fill a section by inventing facts, copy, icons, objects, or decoration.

```text
生成一张完整的【图片类型】，画面比例为【比例】，目标尺寸为【尺寸】。

【核心传达目标】
消费者第一眼应该理解或感受到：【本图唯一核心信息】。
说明本图的模块任务、消费者结果和证明方式；不要让一张图承担多个平级说服任务。

【产品事实与参考图分工】
参考图1负责锁定：【产品身份、结构或整体比例】。
参考图2只负责锁定：【角度、材质或局部细节】。
必须保留：【可见的关键产品特征】。
已确认事实只有：【允许表达的参数、功能、包装内容和声明】。
同时注明产品角色、P0-P4 露出等级、出现原因、使用角度和重复风险；P0 说明由什么替代产品露出。

【单一视觉记忆点】
`ONE_VISUAL_MEMORY_POINT`：本图唯一最容易被记住的视觉主角是【产品、局部细节、数字、运动路径、空间关系或使用结果】。
产品、人物、数字、图标和装饰不得同时争夺第一视觉。尺寸线、运动轨迹、步骤关系等必要类别语义可以保留，但要服从同一个视觉主次。

【正向构图设计】
第一视觉主体是：【内容】。
产品以【角色、大小、位置、角度、完整或局部状态】出现。
前景是：【内容】；中景是：【内容】；背景是：【内容】。
阅读顺序为：【第一视觉】→【核心文案】→【辅助信息】。
明确产品、文案、人物、场景和图形如何连接、重叠或分离，并说明接触点、尺度和透视关系。优先描述相对关系，不用不必要的坐标和百分比把画面锁成模板。

【光影、色彩与材质】
采用：【明确的商业视觉方向】。
主光从【方向】进入，形成【明暗、阴影和空间效果】。
画面以【主色】为主，【强调色】只用于【位置和作用】。
表现【产品材质、环境材质、景深、纹理和商业修图完成度】。
不能只写“高级、简约、有质感”；必须把这些词翻译成可见的光影、材料、比例和层次决策。

【文案规则】
`COPY_OCCURRENCE_RULE`：画面只允许出现以下精确文案，并且每条文案以及关键数字默认只出现一次：
“【文案1】”
“【文案2】”
只能使用 `production_plan.json` 中已批准的 `image_embedded_copy`；`image_embedded_copy` 为空时不得自行新增栅格文字。不得根据卖点自行创作标题、辅助句、脚注、徽章或图标文字。
通过字号、字重、位置和留白建立层级，不通过重复数字制造视觉冲击。若要突出完整文案中的数值，只放大该完整文案内部的数值，不在别处复制一份。
栅格文案与 Amazon 原生 `native_headline`、`native_body` 分开；同时单独写 `alt_text` 和 `mobile_readability`，不要把原生正文重复塞进图片。

【视觉证据边界】
`EVIDENCE_BASED_OMISSION`：只展示有视觉参考支持的产品外观、配件和状态。
已确认某物存在，但没有外观依据时，只用精确文案表达，不生成写实物体、通用轮廓、线稿、剪影或示意图标。
拆卸、打开、内部、连接和装配状态必须有对应视觉证据；文字事实不能代替几何证据。

【禁止项】
只列真正影响商用真实性的禁止内容：产品变形、错误或未确认功能、虚构结构和配件、多余文案、错误参数、平台合规风险、乱码和水印。
```

### 八项写作检查

1. **核心传达目标**：第一眼只传达一个主要结果。
2. **产品事实与参考图分工**：事实和每张参考图的权威范围清楚。
3. **单一视觉记忆点**：只有一个主导视觉概念。
4. **正向构图设计**：主角、产品角色、空间关系和阅读路径具体。
5. **光影、色彩与材质**：审美词已经翻译成可见决定。
6. **文案规则**：精确文案、关键数值和允许次数清楚。
7. **视觉证据边界**：没有外观依据的内容不生成示意图标或实物造型。
8. **禁止项**：负面约束仅保护事实、结构、文案和合规，不承担创意设计。

## Scene Fusion Rules

For any non-white-background production image, explicitly define when relevant:

- Where the product is placed and what supports its weight.
- How the product touches the surface.
- Product scale relative to nearby objects.
- Camera angle and perspective relationship with the surface lines.
- Main light direction, color temperature, and shadow direction.
- Reflection/highlight behavior that matches the real material.

Avoid vague-only instructions such as `natural`, `realistic`, or `well integrated` without the physical details above.

## Conflict Resolution Rules

- If style, copy, or scene requirements conflict with confirmed product facts, preserve product facts and revise the visual idea.
- If the source does not clearly show a detail, do not ask image2 to invent it.
- Do not combine mutually exclusive lighting requests, such as warm ambient dusk lighting plus cold shadowless studio lighting, in the same prompt unless the user explicitly wants a stylized contradiction.
- Do not ask for a product to appear both physically supported and floating, both matte and mirror-glossy, or both viewed from one angle and exposing surfaces impossible from that angle.

## Prompt Document Format

Use this structure by default:

```markdown
# Full Production Prompts - <style name>

## Sources
- Product reference:
- Visual input route (`DIRECT_IMAGE_INPUT` preferred; `VISUAL_CONTEXT_RELAY` fallback):
- Attached source path(s):
- Product brief:
- Competitor logic:
- Output folder:

## Selected Style
- Name:
- Strategic role:
- Inherited Style Spec:
- Visual keywords:
- Selling-point focus:

## Production Context Pack
- Visual elements to preserve:
- Approved sample cues:
- Rejected sample cues:
- Reusable mother-image candidates:
- Non-negotiable prompt constraints:
- Product-exposure role-check notes:

## Reuse Plan
- Mother image 1:
- Mother image 2:
- Same-aspect reuse notes:

## Prompt Preflight
- Product truth:
- Unknown or not-visible details:
- Product exposure module task / product role / level / no-product challenge / product reference and angle / repeat risk / reason:
- Scene request:
- Fusion requirements:
- Human-use scene suitability:
- Person expression and interaction plan:
- Conflicts removed or softened:

## Layout Matrix
| Slot | Deliverable | Format | Size | A+ module count / image count | Module type | Carousel slide | Module task | Product role | Product exposure | Product reference / angle | Repeat risk | Product appearance reason | Layout type | Product view | Scene | Primary message | Text hierarchy | Image-embedded copy | Native headline | Native body | Alt text | Mobile readability | Human-use requirement | Person expression / action | References | Detail locks | Big-brand pattern | Avoid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Main Images, 1:1
### main_01_raw.png
- Purpose:
- Prompt:
- Negative constraints:

...

## Main Images, 4:5 Portrait
### main_portrait_01_raw.png
- Purpose:
- Target size:
- 4:5 ratio rule:
  - Use the viewed image only as product-identity reference, not as canvas-ratio reference.
  - `Canvas requirement: exact portrait 4:5 aspect ratio. Target canvas: 2000 px wide x 2500 px tall. Width:height must be 4:5.`
  - `The image must not be square, not 3:4, not 2:3, not 9:16, and not horizontal.`
- Prompt:
- Negative constraints:

...

## Basic A+ Images, 960x600
### aplus_basic_01_raw.png
- Purpose:
- Prompt:
- Negative constraints:

...

## Premium A+ Desktop Images, 1464x600
### aplus_premium_desktop_01_raw.png
- Module:
- Module type:
- Carousel slide:
- Carousel layout notes:
- Purpose:
- Prompt:
- Negative constraints:

...

## Premium A+ Mobile Images, 600x450
### aplus_premium_mobile_01_raw.png
- Module:
- Module type:
- Carousel slide:
- Purpose:
- Prompt:
- Negative constraints:

...
```

## Postprocess Script

For Premium carousel slides or explicit slot names, use the `--slot-manifest` command from `references/slot_manifest_contract.md`. For a sequential count-based set, run:

```powershell
$env:PYTHONUTF8='1'
& '<python.exe>' '<skill-dir>\scripts\postprocess_images.py' `
  --base-dir '<style-output-folder>' `
  --main-count '<main-count>' `
  --main-portrait-count '<portrait-main-count>' `
  --basic-aplus-count '<basic-aplus-count>' `
  --premium-aplus-desktop-count '<premium-desktop-count>' `
  --premium-aplus-mobile-count '<premium-mobile-count>' `
  --main-size 2000 2000 `
  --main-portrait-size 2000 2500
```

Set counts to `0` for formats the user did not request. `--main-portrait-size` must stay `4:5`; use larger values when useful, such as `2400 3000`.

It writes:

- `main_1x1/main_01_1x1.png` ... based on the requested count
- `main_portrait/main_portrait_01_<width>x<height>.png` ... for `4:5` portrait main images
- `a_plus_basic/aplus_basic_01_960x600.png` ... for Basic A+
- `a_plus_premium_desktop/aplus_premium_desktop_01_1464x600.png` ... for Premium A+ desktop
- `a_plus_premium_mobile/aplus_premium_mobile_01_600x450.png` ... for Premium A+ mobile
- `preview/main_contact_sheet.png`
- `preview/main_portrait_contact_sheet.png`
- A+ contact sheets for each requested A+ group
- `preview/production_manifest.json`

Use the user-confirmed scope. Basic A+ is fixed `960x600` and remains limited to 7 standalone images. Premium A+ desktop is fixed `1464x600`; Premium A+ mobile is fixed `600x450`.

`preview/production_manifest.json` is written only when every requested output is present, exported at the exact target ratio, and recorded with its SHA-256 hash. Any missing or rework-required slot writes `preview/partial_production_manifest.json` instead and must not be reported as complete.
