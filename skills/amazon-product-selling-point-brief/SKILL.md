---
name: amazon-product-selling-point-brief
description: "产品卖点简报 / $amazon-product-selling-point-brief / amazon-product-selling-point-brief. Merge Amazon competitor selling-point logic with the user's own product facts into a product information and selling-point priority brief for main images, A+ pages, and brand story planning. Use when the user provides 自家产品信息, 产品参数, 产品卖点, 竞品卖点与展示逻辑整理.md, or asks to summarize my product's selling points before Amazon image design."
---

# 产品卖点简报

## Goal

Create the upstream product document used before style recommendation and image generation.

The brief must convert competitor display logic and the user's actual product facts into a truthful, usable selling-point hierarchy for Amazon main images, A+ pages, and brand story.

## Inputs

Use the available sources:

- `竞品卖点与展示逻辑整理.md` or equivalent competitor logic document
- User-provided product parameters and claims
- Product reference board or white-background product image
- Matched category design playbook guidance from `amazon-ai-design-workflow-orchestrator/references/category_design_playbooks.md`, when the orchestrator has run the category gate
- Existing listing title, bullets, QA, reviews, manual, spec sheet, or packaging list

If key product facts are missing, create a dynamic Product Facts Gate and stop before style recommendation or image generation. Ask only for facts that materially affect claims, compliance, visual modules, scale, included items, or user-result proof. Do not invent unknown parameters.

## Workflow

1. Extract competitor logic.
   - Identify P0/P1/P2 themes and display positions.
   - Note which themes require proof, authorization, or careful wording.

2. Normalize self-product facts dynamically by product category.
   - Start from visible product truth, user facts, competitor expectations, and buyer purchase reason.
   - Do not use a fixed projector/electronics questionnaire for every product.
   - For each likely selling point, classify whether it needs a confirmed parameter, a source document, user approval, or exclusion.
   - Product-specific examples:
     - Electrical appliance: dimensions, weight, power/input, battery/cord limits, runtime, modes/gears, noise, adjustable angle, cleaning, safety/certification, package contents.
     - Furniture/storage: dimensions, material, load capacity, installation, included hardware, room fit, safety limits, package contents.
     - Apparel/accessory: size chart, fabric/material, fit, care, color variants, closure, model/body guidance, compliance claims.
     - Beauty/personal care: ingredients/material contact, mode levels, waterproof rating, charging, use areas, safety/certification, before/after claim proof.
     - Electronics/projector/device: core specs, ports, connectivity, OS/app support, power, compatibility, heat/noise, accessories, certifications, content/logo authorization.

3. Run the category design playbook match when enough category evidence exists.
   - Detect the product category from product name, Amazon category, competitor set, use case, visible form, and buyer purchase reason.
   - Use category playbook guidance only when match confidence is `high`; for `medium`, borrow only specific tasks and mark uncertainty; for `low`, use no playbook.
   - Record selected and rejected playbooks so category-specific tropes are not applied to mismatched products.
   - Convert the matched playbook into image tasks: category design task, buyer result, proof method, best scene, human presence guidance, and misfit tropes to avoid.

4. Separate claim types.
   - `confirmed`: user gave enough facts to use.
   - `usable with cautious wording`: useful but should avoid strong claims.
   - `needs proof`: requires certificate, test data, authorization, or clear policy.
   - `avoid`: unsupported, risky, misleading, or contradicted by product facts.

5. Rank self-product selling points.
   - Prioritize by buyer impact, competitor expectation, product truth, visual demonstrability, and risk.
   - Main image priority is not the same as A+ priority.
   - Favor truthful advantages over generic category noise.

6. Produce the brief.
   - This document becomes the source of truth for style recommendation and image generation.
   - Include a `Product Facts Gate` section when critical facts are missing.
   - Also write or update `product_facts_gate.md` when working inside a project folder.
   - Do not generate images or recommend visual styles unless the dynamic gate is confirmed or the user explicitly accepts excluding the unknown claims.

## Product Facts Gate Rules

- The gate is product-dependent. Do not ask all possible facts for every product.
- Ask only facts that change image strategy, claims, compliance, scale, module choice, package/accessory display, or buyer proof.
- Keep the question count small by grouping related facts.
- A missing fact can be resolved in three ways:
  - confirmed with source or user statement;
  - marked `unknown but intentionally excluded from claims`;
  - marked `unsupported/forbidden`.
- Proceed only when `product_facts_confirmation.md` exists with a passing status, or when the user explicitly gives equivalent confirmation in the current turn and the confirmation file is written.
- If important facts remain unknown, the brief may contain low-risk style exploration ideas, but must not be treated as ready for formal page design.

## Output Format

Use this structure by default:

```markdown
# 我的产品信息与卖点优先级文档

## 核心结论
- 最适合主打的 3 个卖点：
- 不建议主打的点：
- 最需要补证据的点：

## 产品事实表
| 模块 | 已知事实 | 置信度 | 备注 |
|---|---|---|---|

## 卖点优先级
| 优先级 | 卖点 | 用户价值 | 展示位置 | 证据/限制 | 推荐表达 |
|---|---|---|---|---|---|

## 类目设计思路匹配
- 判断类目：
- 匹配证据：
- 匹配置信度：high / medium / low
- 调用类目库：
- 不调用的相近类目及原因：

| 类目设计任务 | 用户结果 | 证明方式 | 最适合场景 | 人物出现建议 | 禁止误用 |
|---|---|---|---|---|---|

## 主图展示逻辑
> 按本产品卖点优先级和类目设计任务命名每张图，不照抄其他类目的图位（例如投影仪的“画质图、连接兼容图”只适用于投影仪）。张数以用户确认的范围为准。
1. 白底主图：
2. 核心卖点图：
3. <本产品第二卖点或功能证明>：
4. <效果/结果证明，如画质、风力、容量、舒适度、清洁效果>：
5. <使用、安装、尺寸或操作说明>：
6. <细节、材质、配件或兼容性证明，仅在相关时>：
7. 场景/包装/服务图：

## A+ 展示逻辑
1. 首屏：
2. 核心功能总览：
3. <按卖点优先级排列的功能/证明模块>：
4. <效果或使用结果模块>：
5. 易用性/使用方式：
6. <细节、材质、尺寸或兼容性模块，仅在相关时>：
7. 场景：
8. 服务/包装：

## 品牌故事方向
- 可用叙事：
- 不建议叙事：

## 禁用与谨慎表达
- 禁用：
- 谨慎：
- 需要用户确认：

## Product Facts Gate
- Detected category:
- Buyer purchase reason:
- Confirmed facts already supported:
- Missing critical facts:
- Claims to avoid unless confirmed:
- Minimal questions for user:
```

## Judgment Rules

- Do not let competitor selling points override product truth.
- Do not use platform logos, official app claims, licensed technology marks, standards or certification claims (for example Dolby, HDR, ANSI, FDA, UL, CE) unless the user confirms support or proof.
- Do not imply capabilities the product lacks, such as cordless or outdoor use without a built-in battery, or waterproofing without a rating.
- If the user gives a weak or incomplete spec, prefer cautious wording over strong claims.
- Keep the final document practical for image prompts and design planning.
- Category playbooks are advisory. They must not override confirmed product facts, claim risk, local detail locks, or competitor category norms.
