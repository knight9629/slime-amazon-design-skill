# Layout Matrix Contract

Version: `1.0.0`

Use this file as the stable source of truth for `完整出图版式规划矩阵.md`.

## Required Row Fields

Each requested image gets one row. Include:

- Slot id.
- Deliverable type.
- Format and output size.
- Purpose.
- Module task / `模块任务`.
- Product role / `产品角色`.
- Product exposure level `P0`-`P4`.
- Product appearance reason.
- No-product challenge result.
- Repeat risk / `重复风险`.
- Product reference and angle.
- Layout type.
- Product view/angle.
- Scene/background.
- Primary selling point.
- Category design task, buyer result, and proof method.
- Best scene.
- Text hierarchy.
- `image_embedded_copy`: exact copy that should be rasterized into the image, or `none`.
- `native_headline` and `native_body`: Amazon-native text outside the image.
- `alt_text`: concise accessibility text grounded in visible/confirmed facts.
- `mobile_readability`: hierarchy, minimum practical text scale, and safe-content notes.
- Human-use suitability and person expression when relevant.
- Interaction action when relevant.
- Reference subset and role priority.
- Local detail locks to invoke.
- Big-brand design inspiration pattern.
- Misfit tropes to avoid.
- Avoid list.

## Deliverable Fields

- Main images include `format` as `1:1` or `4:5 portrait`.
- Basic A+ includes `a_plus_type` as `Basic` and `image_count`.
- Premium A+ includes `a_plus_type` as `Premium`, `module_count`, `desktop_image_count`, `mobile_image_count`, `module_id`, `module_type` as `static` or `carousel`, and `carousel_slide` when relevant.
- For Premium A+, use only module-level fields and carousel slide fields.
- Premium carousel outputs use normal layout, crop, and readability checks for each slide composition without an automatic reserved band.

## Diversity Rules

- The same layout type may appear at most twice in one production run unless the user explicitly asks for repetition.
- Use varied layout types such as centered hero, left-product/right-copy, right-product/left-copy, top-bottom split, horizontal panorama, three-panel scenario, detail close-up grid, step-by-step strip, comparison band, modular icon row, and full-bleed lifestyle with overlay text.
- Do not use "left text, right product" as the default. Treat it as one possible layout type.
- Human-use scenes are a default recommendation when suitability is `high` or `medium`, not a hard quota. Prefer real interaction over empty room scenes when people improve proof, scale, or emotional readability.
- Do not put `no people`, `no hands`, or `no face` into global negative constraints. Apply those only to product-only slots, pure technical diagrams, package-only images, or explicit user restrictions.
