# Product Exposure Role Check

Version: `1.0.0`

Use this file as the stable source of truth for product exposure in the production matrix, prompt QC, and handoff.

## Core Principle

Each image first defines its persuasion task, then decides whether the product needs to appear. Product appearance is useful only when it improves recognition, proof, understanding, or trust.

## Required Slot Fields

- `模块任务`: recognition, function proof, parameter explanation, usage scene, user result, detail proof, accessory/package proof, trust building, or closing conversion.
- `产品角色`: hero, evidence, detail, scale reference, background support, or absent.
- `露出等级`: `P0`, `P1`, `P2`, `P3`, or `P4`.
- Product reference and angle.
- Product appearance reason.
- No-product challenge result.
- `重复风险`: low, medium, or high.

## Exposure Levels

- `P0` no product: scene result, user state, parameter structure, icons, brand mood, or abstract proof.
- `P1` product detail: button, port, material, structure, accessory, operation detail, or partial product edge.
- `P2` supporting product: product appears small, backgrounded, cropped, or off-center.
- `P3` complete product: product appears complete and clear as one main information carrier.
- `P4` hero product: product is large, central, and strongly recognizable; use for main hero, structure, size, or core proof slots.

## Gates

- No-product challenge: before assigning `P1`-`P4`, ask whether the image would lose necessary buyer proof if the product disappeared. If not, use `P0` or a detail-only `P1`.
- Visual Repetition Gate: role labels are not enough. If multiple slots reuse the same product reference, angle, size, scene, composition, or corner-anchor pattern, repeat risk is high even when module tasks differ.
- Do not enforce a fixed quota such as "at least N no-product images".
- All slots may show the product only when every appearance has a meaningfully different product role, reference, angle, scale, placement, scene, and proof function.
- For app access, wireless/connectivity diagrams, parameter dashboards, screen-result modules, and scenario carousels, first test a product-free module direction.
- If more than half of non-hero slots rely on the same complete-product reference and similar front angle, revise the matrix before prompting.
- This rule does not weaken product fidelity. When the matrix requires `P1`-`P4`, preserve confirmed product truth and local detail locks; when it assigns `P0`, do not fail the image merely because the product is absent.
