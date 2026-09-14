---
name: amazon-creative-style-sampler
description: "创意风格小样 / $amazon-creative-style-sampler / amazon-creative-style-sampler. Recommend three product-driven Amazon creative styles and generate low-cost style samples for main images and A+ pages using product reference images, local detail locks, product selling points, competitor display logic, big-brand design case research, and human-use scene suitability. Use when the user asks for 风格推荐, 风格小样, 生成风格A小样, 生成风格B小样, 生成风格C小样, or wants branch-based Amazon image style testing."
---

# 创意风格小样

Skill version: `0.6.2-compatible`

## Integration with the 1.0 full workflow

When `amazon-ai-design-workflow-orchestrator` 1.0 requests recommendation mode,
produce the three written Style Specs only; do not start image generation.
Inherit the current product's confirmed visual and layout preferences, liked
references, rejected directions, facts, detail locks, and production scope.
Do not replace those choices with an independent reference-selection round.
The controller owns the subsequent `STYLE_SAMPLES` stage: exactly one comparable
representative image per A/B/C style under its current contract. If delegated
sample generation, use Mode 2B and return results to that same run. The bundled
`amazon-image-production-runner` is available for approved formal production;
the standalone modes and older handoff format below remain compatibility paths.

## Goal

Reduce image-generation cost by separating style selection from full production.

Before branches, recommend three styles dynamically from the current product shape, product selling points, and competitor creative patterns. In each branch, generate only the minimum required sample set first. Do not default to fixed style names.

Use this skill for Amazon style recommendation and branch samples, not for ordinary one-off AI image generation. Ordinary AI image requests default to one final image with image2 unless the user asks for Amazon style exploration, branch samples, or full main-image/A+ production.

## Inputs

Prefer these three upstream artifacts:

- Standard white-background product reference image from `product-reference-composer`
- Product local detail locks, such as `03_product_detail_locks.md` or `产品局部细节锁.md`
- `我的产品信息与卖点优先级文档`
- `product_facts_confirmation.md` or equivalent confirmed Product Facts Gate
- `竞品卖点与展示逻辑整理.md`
- `大牌设计案例与版式库.md` when available
- The `类目设计思路匹配` / `Category Design Playbook Match` section from the product brief, when present

If the product brief is missing, use available product facts but state what is missing. If `product_facts_confirmation.md` is missing and critical product facts would affect claims, scene choice, scale, package/accessory display, or compliance, stop and ask for Product Facts Gate confirmation before recommending production styles or generating samples. If the user asks only for low-risk visual exploration, clearly label it as not ready for formal page design.

## Image2 Visual Input Gate

All product-referenced samples must use real image evidence.

- Preferred route: `DIRECT_IMAGE_INPUT`. Pass the exact local product reference/source path(s) through the image-generation tool's native referenced-image input.
- Inspect every selected image before first use. Use the smallest valid subset, label each role, and identify the controlling product reference.
- Fallback route: `VISUAL_CONTEXT_RELAY`. Use it only when native referenced-image attachment is unavailable; open/load the exact source with `view_image` immediately before generation and include the fail-fast canary `NO VIEW_IMAGE INPUT`.
- Chat-visible Markdown images and prompt-only paths are diagnostic only and must not be used as formal product authority.

## Mode 1: Pre-Branch Style Recommendation

Trigger examples:

- `推荐三个设计风格`
- `给我三个适合这个产品的风格`
- `分支前输出风格推荐`

Workflow:

1. Read the product reference image visually.
   - Product shape, color, material, stand, distinctive structure, ports, logo area, package/accessory visibility.
   - Treat the composed white-background product reference image as the standard visual source for downstream image generation.

2. Read product selling points.
   - Prioritize confirmed product facts and allowed claims.
   - Identify unsupported or risky claims that must not drive the style.
   - Check the Product Facts Gate. Do not let a style depend on unconfirmed dimensions, weight, battery/runtime, modes, noise, compatibility, materials, included accessories, certifications, platform/logo authorization, or other category-critical facts.

3. Read competitor design logic.
   - Identify category norms and common visual directions.
   - Avoid direct replication of competitor layouts.

4. Read big-brand design cases when available.
   - Use them for layout maturity, typography hierarchy, scene grammar, product placement, module variety, and design polish.
   - Do not copy exact brand layouts, logos, wording, hero compositions, or protected identity.
   - If missing and web access is allowed, recommend creating `大牌设计案例与版式库.md` before final style decisions.

5. Read matched category design playbook guidance when present.
   - Use it to choose category-appropriate image tasks, buyer results, proof methods, scenes, and human-presence rules.
   - If the match confidence is `medium`, use only the specific borrowed tasks and keep the uncertainty visible.
   - If there is no match or confidence is `low`, do not infer category playbook rules.
   - Avoid rejected playbooks and their tropes. For example, do not use apparel self-appearance or social-attention logic for projectors, appliances, tools, or furniture.

6. Run the human-use scene suitability gate.
   - Decide whether real user presence improves conversion, scale perception, operation clarity, or outcome proof.
   - Classify the product as `high`, `medium`, or `low` suitability for real-person scenes.
   - For `high` or `medium`, define the best person expression: face, side face, upper body, hands, product-in-use action, distance/scale scene, or before/after usage context.
   - Do not default to avoiding faces or hands. image2 can generate people directly; choose the human expression that best communicates the product.
   - Reserve `no people` only for white-background hero shots, pure structure/detail diagrams, compliance-sensitive contexts, or explicit user restrictions.

7. Recommend exactly three styles.
   - Style names must be created for this product, not copied from a fixed list.
   - Each style should have a different strategic role, such as mainstream conversion, product-structure differentiation, or lifestyle trust.
   - Include a reusable `Style Spec` for each style so branch samples inherit the same strategic intent instead of re-deriving it later.
   - Include layout variety seeds so full production has multiple composition options rather than one repeated structure.
   - Include the branch command the user can paste later.
   - When this recommendation is used by the Amazon main-image/A+ full flow, rely on the upstream approved white-background reference library; do not move white-background reference creation into style choice.

Output format:

```markdown
# 三个风格推荐

## 推荐结论
- 最推荐：
- 备选：
- 差异化测试：

## 风格 A：<dynamic name>
- 适合原因：
- 主打卖点：
- 视觉关键词：
- 不适合/风险：
- 分支执行口令：`生成风格A小样`

## 风格 B：<dynamic name>
- 适合原因：
- 主打卖点：
- 视觉关键词：
- 不适合/风险：
- 分支执行口令：`生成风格B小样`

## 风格 C：<dynamic name>
- 适合原因：
- 主打卖点：
- 视觉关键词：
- 不适合/风险：
- 分支执行口令：`生成风格C小样`
```

Each recommended style must also include a reusable `Style Spec` with:

- Strategic role
- Primary selling point
- Category design tasks to emphasize, or `none` when no category playbook matched
- Buyer result and proof method inherited from the matched category playbook, when present
- Visual grammar
- Scene boundary
- Human-use scene suitability: `high`, `medium`, or `low`, with the reason.
- Person expression plan: whether to use front face, side face, upper body, hands, or no person, plus the interaction action.
- Full-production human-use recommendation: identify which slot tasks materially benefit from people; do not set a fixed quota.
- Copy tone
- Must preserve
- Must avoid
- Layout variety seed: 3-5 possible layout patterns for this style; do not lock the full production set into one layout.

## Mode 2: Branch Style Sample Generation

Trigger examples:

- `生成风格A小样`
- `生成风格B小样`
- `生成风格C小样`

Workflow:

1. Resolve the selected style from the latest style recommendation in the thread or project files.
   - Reuse the selected style's `Style Spec` directly when it exists.
   - If no prior recommendation exists, reconstruct three styles from the upstream artifacts and use the requested letter.

2. Write prompts first.
   - Save a prompt document before image generation when working in a local project folder.
   - Include source paths, selected style, inherited `Style Spec`, three sample prompts, size targets, and fixed constraints.
   - Include relevant product detail locks for any visible knob/button, grille, logo, port, hinge, label, accessory, or package detail.
   - Apply the human-use scene suitability from the `Style Spec`; include a person only when it materially improves the proof or comparison value of that sample.
   - Run the prompt preflight check below before writing any sample prompt.
   - If the A+ format is not yet known, ask whether the sample should use Basic A+ or Premium A+ before generating the A+ sample.
   - Only ask about separate mobile A+ when the user chooses Premium A+.

3. Generate only three samples:
   - `white_main`: 1:1 white-background main image sample.
   - `core_feature`: 1:1 core selling-point or feature image sample.
   - `aplus_hero`: A+ hero sample in the user-selected A+ format:
     - Basic A+: `960x600`, shared by desktop/mobile
     - Premium A+ desktop: `1464x600`
     - Premium A+ mobile: `600x450`, only when the user requests a mobile sample
   - Before each product-referenced sample, execute the visual-input gate above, preferring native referenced-image paths.

4. Save outputs by style.
   - Use directories like:
     - `prompts`
     - `samples`
     - `raw_generated`
     - `preview`
   - Keep original generated files and processed files.

5. Stop after the three samples.
   - Do not generate full production unless the user explicitly chooses the style and confirms which deliverables and counts they want.

### Full-flow reference assumption

When this skill is called from `amazon-ai-design-workflow-orchestrator` during `STYLE_SAMPLES`, assume the orchestrator has already created and approved at least three current-product white-background reference images from photographed source images.

- If those references are missing, return to the orchestrator's `REFERENCE_LIBRARY_BUILD` stage instead of asking the user to choose a style.
- Style comparison samples may be A+ hero, secondary main, or feature visuals; they do not replace the upstream white-background reference library.
- The branch-level `white_main` sample remains useful when the user explicitly asks for a per-style branch package, but it is not the full-flow reference-library gate.

## Mode 2B: FULL_FLOW_STYLE_COMPARISON

Use `FULL_FLOW_STYLE_COMPARISON` only when the orchestrator is in the full main-image/A+ workflow and the current stage is `STYLE_SAMPLES`.

- Generate exactly one representative image per style, total three images for styles A/B/C.
- Use the same slot task, product reference subset, selling point, output ratio, and copy burden for all three styles so the user compares style direction instead of different image tasks.
- Before each representative image2 call, execute the visual-input gate above, preferring native referenced-image paths.
- Save one prompt per style and one output per style in the current project style-sample area.
- Do not run the normal Branch Style Sample Generation package of three samples per branch unless the user explicitly asks for expanded branch validation.
- After the three representative images are ready, stop and ask the user to choose A, B, or C before full production handoff.

## Prompt Constraints

Always include these constraints in sample prompts when relevant:

- Use the standard white-background product reference image as the single product shape source.
- Pass that product reference through `DIRECT_IMAGE_INPUT`; use adjacent `view_image` relay only as fallback. Markdown display or prompt-only paths are not enough.
- Preserve the actual product body, lens, stand, ports, logo area, materials, and distinctive structure.
- Preserve locked local details from `03_product_detail_locks.md` or `产品局部细节锁.md`; do not simplify them into generic buttons, grilles, ports, logos, or accessories.
- Apply category-specific physical/compliance constraints only when supported by current product truth, the matched playbook, or the confirmed brief; do not inherit another SKU's constraints.
- Do not imply built-in battery unless confirmed.
- Do not invent accessories, cables, handles, buttons, ports, or extra screens.
- Do not use real platform logos or authorization claims unless the product brief confirms they are allowed.
- Follow the global AI image rule: when the user asks for AI image generation, put the needed copy, layout hierarchy, parameters, and icon/badge intent directly into the image-generation prompt by default.
- Use image2 directly for text, icons, parameters, badges, and final composition by default.
- If the human-use suitability is `high` or `medium`, do not write generic negative constraints such as `no people`, `no hands`, or `no face` unless that exact image slot is a white-background hero, pure diagram, or compliance-sensitive detail shot.
- For real-person scenes, specify the user role, action, body framing, product contact point, gaze/attention, distance from product, and how the person proves scale or usage benefit.

## Prompt Preflight Check

Before writing any sample prompt, separate and verify:

1. Product truth
   - Confirmed structure, proportions, materials, colors, visible details, supported states, and approved claims.
   - Details not visible in the source images or not confirmed in the product brief.
   - Use the standard white-background product reference image as the single visual source for downstream generation unless the user explicitly replaces it.

2. Scene request
   - Environment, camera angle, support surface, nearby objects, lighting, and desired composition.

3. Fusion requirements
   - Contact point, scale, perspective, light direction, shadow direction, reflection behavior, and material response.

4. Human-use scene gate
   - Suitability level and reason.
   - Whether this sample should include a real person, hands, face, side face, or no person.
   - User action: operating, feeling airflow, reading beside the fan, working at a desk, carrying, charging, cleaning, or other product-specific use.
   - Person must support the product story and must not steal the hero role unless the style intentionally uses a people-first lifestyle shot.

5. Conflict scan
   - Remove or soften any request that conflicts with confirmed product truth, visible reference images, or allowed claims.
   - Do not request hidden structures, unsupported states, or unconfirmed functions just to satisfy a marketing composition.
   - Product truth outranks scene style and marketing expression.

## Prompt Structure

Write each generated-image prompt in this order by default:

```text
[Product truth]
State the non-negotiable product facts to preserve.

[Scene]
Describe the allowed environment, camera angle, and composition.

[Fusion]
Specify contact, scale, perspective, lighting, shadow, reflection, and material behavior.

[Do not]
List structural, factual, and physical conflicts to avoid.
```

## Scene Fusion Rules

For any non-white-background scene sample, explicitly define when relevant:

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

## Mode 3: Full Production Handoff

When the user chooses a style and asks to continue:

- Confirm the selected style branch.
- Create a `Production Handoff` before handing off to full production.
- Save it in the selected style branch folder as `production_handoff.md` when working in a local project.
- Include:
  - Selected style
  - Inherited `Style Spec`
  - Visual elements to preserve from the approved samples
  - Approved sample cues
  - Rejected sample cues, if the user provided any
  - Matched category design playbook, confidence, category design tasks, buyer results, proof methods, and rejected playbook tropes to avoid
  - Human-use scene suitability, recommended person expressions, and the slot tasks that materially benefit from people
  - Reusable mother-image candidates
  - Non-negotiable prompt constraints
- Hand off to full production only after the user confirms whether they want main images, Basic A+, Premium A+, or a combination, plus the required counts.
- Prefer mother-image reuse: one visual concept can be reused across requested sizes where practical.
- This skill may hand off to a future `amazon-image-production-runner` if it exists.

## Rules

- Do not use a fixed style list by default; styles must come from product shape, product facts, and competitor creative direction.
- Do not treat one successful sample composition as approved for every production image. Style samples validate style direction; full production still needs a layout matrix.
- Run a lightweight product-fidelity and reference-input check before presenting samples; the user still chooses the style direction.
- Keep sample generation low-cost by default.
- If the user only asks for style recommendation, output text only and do not call image generation.
