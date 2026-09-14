---
name: product-reference-composer
description: "Use when the user asks for 产品参考图, 白底参考图, 合成参考图, 主参考图, 结构参考图, 证据参考图, or asks Codex to prepare real product photos as references for Amazon main image or A+ creation."
---

# 产品参考图库

Skill version: `0.6.2-compatible`

## Integration with the 1.0 full workflow

When invoked by `amazon-ai-design-workflow-orchestrator` 1.0, its current-product
scope and reference contract take precedence over the standalone defaults below.
Generate the minimum useful set of at least three references (main, angle,
structure) under `REFERENCE_THREE_WAY_PARALLEL`; do not generate one per source
photo. Follow `NO_SMOKE_GATES`: collect all three raw references before QC and
one set-level user approval, without a separate one-image smoke-test gate.
This does not relax real-image input, provenance, product fidelity, or rejection
of missing visual input. Keep unused detail photos as `SOURCE_ONLY` evidence.
Use the controller's QC statuses and its maximum of two controlled revision rounds.
Resolve this Skill's `scripts/` paths from this installed Skill directory.
The standalone workflow below still applies when this Skill is requested alone.

## Goal

Turn real product photos into a clean white-background reference library for later Amazon main image and A+ generation.

The goal is not to make final marketing images. The goal is to reduce product-structure drift by giving image2 cleaner, named, role-specific references.

Truth priority:

1. Real product photos.
2. `01_product_truth.md`.
3. Human-approved white-background reference images.
4. Later marketing prompts.

White-background reference images are working references, not the only truth source. If a white-background image changes the product structure, mark the risk and keep the source photo as the correction authority.

Image2 product-reference input rule:

- Per-photo white-background references must be created by calling the image2 model with the actual real product photo available to that generation.
- Preferred route: pass the source photo into the same image2 generation/edit call as the image-to-image base, edit target, uploaded asset, mask target, or equivalent image input. Mark provenance as `DIRECT_IMAGE_INPUT`.
- Fallback route when the current Codex image2 tool has no explicit image-input parameter: use the visual-context relay. Mark provenance as `VISUAL_CONTEXT_RELAY` only if the exact source photo is opened with `view_image` immediately before the image2 call, the prompt explicitly refers to the current `view_image` visual context, and the generated result passes the smoke test and reference QC below.
- A prompt that merely mentions a source filename, writes a local path in the prompt, displays a Markdown image in chat, describes the source photo from memory, uses only `01_product_truth.md`, or relies on a contact sheet alone does not count as using the real photo. Mark that attempt as `TEXT_ONLY` and reject it for downstream product-shape use.
- If neither `DIRECT_IMAGE_INPUT` nor a validated `VISUAL_CONTEXT_RELAY` route is available, do not create or approve a generated white-background reference for that slot. Keep the real photo as `SOURCE_ONLY` and stop for a valid image2 route.
- Do not substitute other generation methods for white-background references, including text-only generation, local cutout/background removal as the final reference, Photoshop generative tools, Stable Diffusion, Midjourney, browser image tools, PPT, HTML/CSS, Python canvas, or manual compositing.
- Record the source photo path or uploaded asset id, the route (`DIRECT_IMAGE_INPUT` or `VISUAL_CONTEXT_RELAY`), and `model: image2` for every generated reference. References without this provenance are `REJECT` for downstream product-shape use.
- Chat-visible Markdown images and paths written only in the prompt are diagnostic only and must not be used for formal reference-library output.
- Every `VISUAL_CONTEXT_RELAY` prompt must include this fail-fast canary: if the current `view_image` visual input is unavailable, output a plain white card with large red text `NO VIEW_IMAGE INPUT`.

## Fallback Visual-Context Image Relay

Use this route only as an image2 fallback when no explicit image-input field is available in the current tool. Do not reference old threads, archived conversations, screenshots of old outputs, or a thread named `测试1`; the reusable method must be executed from the current product folder.

Required sequence:

1. Build and inspect the original-photo contact sheet, but do not use the contact sheet alone as the generation reference.
2. Select one exact source photo for the current output.
3. Open that exact source photo with the local `view_image` tool immediately before the image2 call.
4. Call image2 immediately after the `view_image` step. The prompt must say to use the current `view_image` visual context as the product reference and to ignore Markdown images, path text, unrelated screenshots, previous generated images, and older conversation images.
5. Save the generated file into the project reference folder and record source path, output path, prompt, model, route, and timestamp.
6. Run a one-image smoke test before any batch. If the first relay output fails product similarity, stop the batch and mark the route blocked instead of continuing to spend generations.

Relay smoke test checks:

- Global silhouette, head/base ratio, and source camera angle match the real source photo.
- Visible controls, grille, logo/mark, port, label, feet, hinge, base, and other detail locks are not invented, removed, or moved.
- The output is not a generic redesigned product.
- Background cleanup, lighting, and polish improved without changing the product structure.

Provenance statuses:

| Status | Meaning | Downstream use |
|---|---|---|
| `DIRECT_IMAGE_INPUT` | Source photo was explicitly supplied to image2 as an image input. | Valid if QC passes. |
| `VISUAL_CONTEXT_RELAY` | Source photo was opened with `view_image` immediately before image2 and the relay smoke test passed. | Valid if QC passes. |
| `TEXT_ONLY` | Prompt used filenames, descriptions, memory, or contact sheet only. | Reject. |
| `SOURCE_ONLY` | Real photo retained as product truth because no valid generated reference exists. | Evidence only; not a generated reference. |

## Default Workflow

1. Locate the source photos.
   - If the user gives a folder, use that folder.
   - If not, ask for the folder path.
   - Accept `.jpg`, `.jpeg`, `.png`, and `.webp`.

2. Create or reuse the output folder.
   - Default under the current project: `输出/<product>_white_bg_reference_library/`.
   - If the user gives a target folder, use it.
   - Never leave the only usable generated image in `$CODEX_HOME/generated_images/...`; copy outputs into the project folder.

3. Build the original-photo contact sheet.
   - Run `scripts/build_input_collage.py`.
   - Save `00_all_original_photos_input_for_image2.jpg` and `00_all_original_photos_manifest.json`.
   - Show the contact sheet with `view_image` before image generation.

4. Create `01_product_truth.md`.
   - Record only facts supported by source photos or user text.
   - Mark unknown facts as unknown; do not infer specs, accessories, ports, buttons, labels, or claims.
   - Include a manual inspection checklist.

5. Create `03_product_detail_locks.md`.
   - Extract high-risk local details from real photos and user corrections before any marketing generation.
   - Include only details likely to drift in image generation, such as knobs/buttons, grilles, logos, ports, hinges, labels, seams, feet, vents, handles, screens, accessories, and package contents.
   - For each locked detail, record true shape and location, allowed variants, forbidden distortions, evidence reference, and trigger scenes.
   - If the user corrects a local detail later, update this file first, then rewrite affected prompts/images.

6. Plan the reference library before generation.
   - Create `02_reference_plan.md`.
   - For each useful source photo, assign:
     - role: `main-reference`, `angle-reference`, `structure-reference`, or `evidence-reference`
     - view/angle: `front-full`, `front-three-quarter`, `side-profile`, `top-front`, `top-grille`, `rear-full`, `bottom-label`, etc.
     - downstream use: main image, scene image, A+ structure image, local correction, label/port/button proof
     - risk: likely AI completion, cropped source, unclear text, local-only reference, not suitable as hero reference
   - Do not generate every poor photo if it does not add a new angle or detail.

7. Generate per-photo white-background references with a valid image2 product-reference route.
   - Default: one generated white-background reference per selected source photo.
   - First try `DIRECT_IMAGE_INPUT`: the exact selected source photo is supplied to image2 as the image-to-image base, edit target, uploaded asset, mask target, or equivalent image input for that specific output.
   - If direct image input is not exposed by the current Codex tool, try `VISUAL_CONTEXT_RELAY`: open the exact source photo with `view_image` immediately before the image2 call, then reference the current `view_image` visual context in the prompt.
   - Run one relay smoke test before batch generation. If it fails product similarity, skip further relay generation and mark remaining real photos as `SOURCE_ONLY` until a better image2 route is available.
   - Do not generate from text-only prompts, filename references, path-only prompts, Markdown image display, memory of inspected images, old threads, screenshots, or the original-photo contact sheet alone.
   - If only a text-to-image tool or any non-image2 image tool is available, or if visual-context relay fails the smoke test, skip generation for that slot and mark the real photo as `SOURCE_ONLY` for human/product-truth reference.
   - Preserve the original angle and reference purpose.
   - For close-up, cropped, bottom, rear, port, label, or side evidence photos, do not ask image2 to turn them into a complete hero product.
   - Only ask for a complete product silhouette when the source photo already supports that purpose, and label the output as a `main-reference`.
   - Do not create marketing imagery in this stage.
   - Do not add dimensions, arrows, labels, dense copy, badges, props, lifestyle scenes, or claims.
   - Local scripts may build contact sheets, manifests, previews, crops, or deterministic exports only. They must not create, replace, redraw, retouch, or composite the product reference image.
   - Save the prompt or instruction with an explicit `Model: image2` line, a `Route:` line, and an `Input image:` or `Visible source image:` line containing the source path or asset id used.

8. Name generated references by role and angle.
   - Use this pattern:
     - `<nn>_<role>_<view>_white-bg_from-<source-stem>.png`
   - Examples:
     - `10_main-reference_front-full_white-bg_from-96790426.png`
     - `11_main-reference_front-three-quarter_white-bg_from-b9ebd221.png`
     - `20_structure-reference_side-profile_white-bg_from-53fac0de.png`
     - `30_angle-reference_top-front_white-bg_from-7a7a37b7.png`
     - `40_evidence-reference_rear-full_white-bg_from-d6f475e2.png`
     - `41_evidence-reference_bottom-label_white-bg_from-8b3d35c3.png`
   - If using an existing numbered naming scheme, keep it consistent and document the role in `90_reference_selection_guide.md`.

9. Build a white-background output contact sheet.
   - Use `scripts/build_reference_contact_sheet.py` when available.
   - Save as `80_white_bg_reference_contact_sheet.jpg`.
   - Use it to inspect the set quickly.

10. Run the automated white-background reference QC loop.
   - Inspect generated references against source photos, `01_product_truth.md`, `02_reference_plan.md`, and `03_product_detail_locks.md`.
   - Save `91_reference_qc_report.md`.
   - Use generated-reference statuses only: `PASS`, `REVISE`, `REJECT`, or `EVIDENCE_ONLY`.
   - Use `SOURCE_ONLY` only for real product photos retained as authority when no valid generated reference exists.
   - Automatically revise failed references for up to 2 rounds.
   - Rebuild `80_white_bg_reference_contact_sheet.jpg` after any revised output.
   - If a reference still fails after 2 rounds, keep the best available version, keep the closest valid QC status, add `Escalation: USER_REVIEW_REQUIRED`, and require user review.

11. Create `90_reference_selection_guide.md`.
   - List every generated reference and its QC status.
   - Explain which files are primary references, which are evidence-only references, and which are rejected.
   - Include selection rules for downstream image generation.

12. Stop for manual inspection.
   - AI QC reduces obvious reference problems but does not replace the user's final approval of the reference library.
   - Return the output folder, contact sheet, `01_product_truth.md`, `02_reference_plan.md`, `03_product_detail_locks.md`, `90_reference_selection_guide.md`, and `91_reference_qc_report.md`.
   - Ask the user to confirm pass/fail or give concrete correction notes.
   - If the user reports defects, edit only the failed local parts and keep the approved angle, shape, and role unchanged.
   - When approved, record `95_manual_approval.md` with approved reference paths and remaining usage notes.
   - Do not proceed to Amazon main image or A+ production until the reference library is approved.

## Reference Roles

- `main-reference`
  - Use for global product shape, hero view, main image, and broad scene generation.
  - Should usually show a complete product, stable proportions, and the default state.

- `angle-reference`
  - Use to force a camera angle, perspective, or product pose.
  - Good for top-front, low angle, angled tabletop, folded/unfolded state, etc.

- `structure-reference`
  - Use to preserve thickness, hinge, bracket, seam, neck, grille depth, handle, stand, base, or side profile.
  - Usually not enough to drive the entire image alone.

- `evidence-reference`
  - Use for local correction only: logo, label, button, port, bottom, rear, interface side, accessory connection, vent, lens, foot, QR/barcode.
  - Do not treat evidence references as equal to the main reference.

## Automated Reference QC Loop

Run this after building the white-background output contact sheet and before asking for manual approval.

Use only these statuses:

- `PASS`: safe for the documented role.
- `REVISE`: useful but needs local correction or visual cleanup.
- `REJECT`: should not be used downstream.
- `EVIDENCE_ONLY`: useful only for named local proof, not as a product-shape reference.

Check:

- Overall product shape, proportion, source angle, and camera view match the real source photo.
- The generated reference has documented image2 provenance: `model: image2`, source photo path or uploaded asset id, and route `DIRECT_IMAGE_INPUT` or `VISUAL_CONTEXT_RELAY`.
- Named local details from `03_product_detail_locks.md` are preserved when visible.
- The generated reference did not invent or remove buttons, ports, labels, screens, accessories, cables, logos, or package contents.
- `main-reference` images show a complete stable product; `angle-reference` images control view only; `structure-reference` images control named structure only; `evidence-reference` images are not expanded into invented complete products.
- Background is clean white, edges are clear, and no hands, table remnants, props, marketing copy, badges, arrows, dimensions, or lifestyle elements remain.
- Product lighting is smooth and the material finish feels polished enough for downstream use.

Blocking failures:

- The reference was made from text-only prompting, a filename mention, a contact sheet alone, model memory, old thread context, screenshots, a non-image2 generator, local cutout/background removal, or manual compositing rather than a valid `DIRECT_IMAGE_INPUT` or QC-passing `VISUAL_CONTEXT_RELAY` route.
- Overall product structure or proportions changed.
- High-risk local detail locks are wrong.
- An evidence-only crop was turned into an invented complete product.
- The image invents unconfirmed accessories, interface details, labels, screens, claims, badges, or extra product parts.

Rework rules:

- Missing valid image2 provenance -> reject that generated reference, regenerate from the original source photo using `DIRECT_IMAGE_INPUT`, try one controlled `VISUAL_CONTEXT_RELAY` smoke test if direct input is unavailable, or keep the real photo as `SOURCE_ONLY`.
- Minor background, edge, lighting, or finish issues -> revise the generated reference.
- Local detail failure -> run an image2 correction using the relevant source/evidence reference via `DIRECT_IMAGE_INPUT` or validated `VISUAL_CONTEXT_RELAY` plus detail-lock text.
- Whole shape or role failure -> regenerate from the original source photo with a valid image2 route.
- Role mismatch but useful local proof -> mark `EVIDENCE_ONLY` instead of forcing it into a main reference.
- After 2 failed revision rounds, keep the best version, keep the closest valid QC status, add `Escalation: USER_REVIEW_REQUIRED` inside `91_reference_qc_report.md`, and stop trying to fix that reference automatically.

`91_reference_qc_report.md` must include:

```markdown
# Reference QC Report

## Summary
| Reference | Intended role | QC status | Revision round | Final use | Escalation | Notes |
|---|---|---|---|---|---|---|

## Findings
### <reference file>
- Source photo:
- Image2 provenance:
- Route:
- Checked against:
- Product-shape result:
- Local-detail result:
- Background/edge result:
- Lighting/material result:
- Decision:
- Rework action:
```

## Product Truth File Pattern

Create `01_product_truth.md`:

```markdown
# Product Truth

## Basic Facts
- Product/category:
- Default state:
- Known dimensions:
- Confirmed accessories:

## Must Preserve
- Overall shape/proportion:
- Logo/brand/model text:
- Buttons/controls:
- Ports/interfaces:
- Back/bottom/hinge/connection details:
- Color/material/finish:

## Must Not Invent
- ...

## Reference Library Route
- Selected source photos:
- Main-reference candidates:
- Angle/structure/evidence references:
- Known risks:

## Manual Inspection Checklist
- Does each main reference preserve the real overall silhouette and proportions?
- Does each reference preserve its source angle and purpose?
- Are button/control count and positions correct?
- Are ports/interfaces on the correct side with no invented ports?
- Are back, bottom, hinge, bracket, vent, lens, feet, grille, or connection structures correct when visible?
- Did the output turn a close-up evidence photo into an invented complete product?
- Did it add unconfirmed accessories, cables, badges, labels, claims, or scene elements?
- Which references are approved for downstream use, and which are evidence-only?
```

## Reference Plan Pattern

Create `02_reference_plan.md`:

```markdown
# Reference Plan

| Source file | Role | View/angle | Downstream use | Generation note | Risk |
|---|---|---|---|---|---|
| ...jpg | main-reference | front-three-quarter | main image, scene | complete product, white background | may standardize perspective |
| ...jpg | structure-reference | side-profile | thickness, side structure | preserve side angle, do not make hero view | local-only |
| ...jpg | evidence-reference | rear-full | back button, label, port | preserve rear view | text may be soft |
```

## Product Detail Locks Pattern

Create `03_product_detail_locks.md`:

```markdown
# 产品局部细节锁

## 使用规则
- 后续主图、A+、场景图、信息图只要出现下列局部，就必须把对应锁写进提示词。
- 真实照片和本文件优先于白底参考图、风格要求和营销构图。
- 如果用户指出局部变形，先更新本文件，再重写相关提示词。

## Detail Locks
| 局部 | 真实形态与位置 | 允许表现 | 禁止变形 | 证据参考 | 触发场景 |
|---|---|---|---|---|---|
| 旋钮/按钮 | 例如：橙色圆球形凸起旋钮，位于底座前侧低位 | 可有真实高光和投影 | 不变成椭圆、扁片、多层旋钮、偏位按钮 | source_xxx.jpg / evidence-reference_xxx.png | 正面、斜正面、控制方式图 |
| 格栅 | 例如：密集放射状前网罩 | 可随透视变化 | 不变成蜂窝、稀疏横条、封闭圆盘 | ... | 所有正面产品图 |
| logo | ... | ... | ... | ... | ... |
| 接口 | ... | ... | ... | ... | 背面、充电、结构图 |
```

## Per-Photo White-Background Prompt Pattern

Adapt this structure for each source photo:

```text
Edit the provided product photo into a clean white-background reference image.

Image2 route:
- Model: image2.
- Route: <DIRECT_IMAGE_INPUT / VISUAL_CONTEXT_RELAY>.
- DIRECT_IMAGE_INPUT: use this exact source photo as the image-to-image/edit target: <source photo path or uploaded asset id>.
- VISUAL_CONTEXT_RELAY: use the product photo currently visible in the `view_image` tool context as the only product visual reference: <source photo path>. If that `view_image` visual input is unavailable, output a plain white card with large red text: NO VIEW_IMAGE INPUT. Ignore Markdown images, path text, unrelated screenshots, old generated images, and older conversation images.
- A valid image route is mandatory. Do not run this prompt as pure text-to-image or through any non-image2 generation/edit method.

Task: retouch this exact <role/view> source photo of <product> into a white-background product reference.

Reference purpose:
- Role: <main-reference / angle-reference / structure-reference / evidence-reference>
- View/angle: <front-full / front-three-quarter / side-profile / top-front / rear-full / bottom-label>
- Downstream use: <main image / A+ structure / scene image / local correction>

Critical preservation requirements:
- Preserve the source camera angle and product proportions.
- Preserve these visible product structures: <specific parts from product truth>.
- Do not turn this into a different angle or generic hero pose.
- Do not redesign, simplify, remove, or add <buttons / ports / grilles / labels / screens / accessories / cables / logos>.
- For cropped or local evidence photos, keep the evidence character. Do not invent hidden product structure outside the source.

Retouching only:
- Remove background clutter, hands, table, props, reflections, and environment.
- Replace the environment with pure white background.
- Improve exposure, sharpness, and product edge clarity.
- Keep real material, color, finish, and confirmed markings.

Output:
- One white-background reference image.
- No marketing copy, no badges, no extra labels, no scene, no props.
- Soft natural grounding shadow only if needed.
```

## Downstream Selection Rules

For each later main image or A+ image, choose references by the current image need and call image2 with the selected references through a valid route (`DIRECT_IMAGE_INPUT` preferred, `VISUAL_CONTEXT_RELAY` fallback) plus the prompt. Do not feed the whole library by default.

Default selection:

- 1 image: use one `main-reference` when the product is simple and the requested view matches.
- 2 images: use one `main-reference` plus one `angle-reference` or `structure-reference` when the view or shape needs control.
- 3 images: use one `main-reference`, one angle/structure reference, and one evidence reference when local details are likely to drift.
- More than 3 images only when the product is complex and each added reference has a named role. Explain conflict priority.

Conflict priority:

1. Main reference controls global shape, proportion, default state, and broad view.
2. Angle reference controls camera angle only.
3. Structure reference controls the named physical structure only.
4. Evidence reference controls the named local detail only.
5. If references conflict, do not blend them into a fake product; keep the main reference globally and apply local references only to their named areas.

## Image2 Correction Prompt Pattern

Use only after the user reports specific defects:

```text
Model: image2.
Route: <DIRECT_IMAGE_INPUT / VISUAL_CONTEXT_RELAY>.

Input images or visible reference images:
- Approved current reference or generated image: <path or uploaded asset id>
- Source/evidence reference for the defect: <path or uploaded asset id>
For VISUAL_CONTEXT_RELAY: open the approved current reference and the source/evidence reference with `view_image` immediately before the correction call, then reference the current `view_image` visual context in the prompt.

Only correct these local issues and keep everything else unchanged:
- <user defect 1>
- <user defect 2>

Keep unchanged:
- Approved product shape and proportions
- Approved source angle and camera view
- White background
- Lighting, shadow, and placement
- Approved local details

Do not add any unconfirmed structure, text, accessory, claim, badge, or scene element.
```

## Important Judgment

The new default is a reference library, not a single reference board.

This library reduces structure drift because later prompts can select the few references that match the current image. It does not eliminate drift. Manual inspection is still required, and real source photos plus `01_product_truth.md` remain the authority.

## Scripts

Build original-photo contact sheet:

```powershell
& '<python.exe>' '<skill-dir>\scripts\build_input_collage.py' `
  --input-dir '<photo-folder>' `
  --out-dir '<output-folder>' `
  --product-name '<product-name>'
```

Build white-background output contact sheet:

```powershell
& '<python.exe>' '<skill-dir>\scripts\build_reference_contact_sheet.py' `
  --input-dir '<output-folder>' `
  --output '<output-folder>\80_white_bg_reference_contact_sheet.jpg'
```
