---
name: amazon-competitor-creative-research
description: "竞品图片卖点分析 / $amazon-competitor-creative-research / amazon-competitor-creative-research. Analyze Amazon competitor main images, secondary images, and A+ screenshots into selling points, content display logic, display priority, and risk notes. Use when the user asks for 竞品主图分析, A+分析, 竞品卖点整理, 内容展现逻辑, or preparation for Amazon main image/A+ creative planning."
---

# 竞品图片卖点分析

## Goal

Turn competitor Amazon image materials into a decision-ready brief for later product selling-point planning and creative design.

Analyze structure, priority, and buyer logic. Do not copy competitor images, layouts, exact copy, brand assets, or protected claims.

## Inputs

Default required input for the Amazon AI design workflow:

- Folders or zip files containing competitor main images, secondary images, and A+ screenshots.

If the user provides local files, work from those files and state the analysis is based on provided materials. If the user asks for current live ASIN collection, browse and record the collection date.

## Workflow

1. Build a source inventory.
   - Group materials by folder, file prefix, ASIN, or competitor name when available.
   - Separate `main images`, `secondary images`, and `A+ images`.
   - Deduplicate repeated zip packages or duplicate images before judging frequency.
   - If many images exist, create or inspect contact sheets before writing conclusions.

2. Extract per-competitor logic.
   - Main image: product angle, props, white-background safety, platform logos, included accessories, first-click hook.
   - Secondary images: feature order, parameter framing, scene order, comparison or diagram strategy.
   - A+ page: module sequence, hero message, feature modules, scenario modules, trust modules.

3. Normalize selling points.
   - Convert competitor claims into generic buyer-facing themes.
   - Separate real product value from marketing noise.
   - Tag each theme as:
     - `P0`: primary conversion point likely to affect click or purchase.
     - `P1`: important supporting point.
     - `P2`: useful but later-page or trust-support point.
     - `risk`: requires proof, authorization, certification, or careful wording.
     - `noise`: vague or low-value expression.

4. Summarize display logic.
   - Main image logic: what needs to appear in the first 1-3 images.
   - A+ logic: module order and narrative flow.
   - Identify which ideas are category conventions and which are real differentiators.

5. Produce a handoff document.
   - Write for the next step: self-product selling-point brief.
   - Include a bottom section named `自家产品信息待填写` with the exact product data the user must fill before using any competitor-inspired claim.
   - Make that section dynamic for the current product category and competitor claim map. Do not use the same fixed questionnaire for appliances, apparel, furniture, beauty, electronics, tools, and outdoor products.
   - Do not create a separate questionnaire/table file unless the user explicitly asks for a separate file.
   - Do not proceed into style recommendation or image generation unless the user explicitly asks.

## Output Format

Use this structure by default:

```markdown
# 竞品卖点与展示逻辑整理

## 核心结论
- 竞品页面的主要成交逻辑：
- 最值得借鉴的展示顺序：
- 最高风险点：

## 竞品素材清单
| 竞品/文件组 | 主图 | 副图 | A+ | 备注 |
|---|---|---|---|---|

## 高频卖点地图
| 优先级 | 卖点主题 | 竞品常见表达 | 买家真实关心点 | 适合展示位置 | 使用前必须确认 |
|---|---|---|---|---|---|

## 主图内容展示逻辑
1. 
2. 
3. 

## A+ 页面内容逻辑
1. 
2. 
3. 

## 自家产品信息待填写
> The user should fill this section directly in this same document. The next step generates `我的产品信息与卖点优先级文档.md` by combining the competitor logic above with the filled self-product facts here.
> Unknown items should be marked `不确定` or `暂无证据`; unsupported features should be marked `没有`.
> Customize the questions to the product category and competitor risk map. Keep only fields that affect claims, visual modules, compliance, scale, package/accessory display, or buyer proof.

### 1. 产品基础信息
- 品牌/型号：
- 颜色：
- 关键尺寸/重量/材质等当前类目必须确认的信息：
- 核心使用场景：
- 目标人群：

### 2. 当前类目关键功能与参数
- Primary functional claims:
- Parameter claims with evidence:
- Category-critical parameters:
- Supported modes, controls, compatibility, or usage constraints:

### 3. User Value And Scene Fit
- Strongest buyer-facing advantage:
- Secondary selling point 1:
- Secondary selling point 2:
- Secondary selling point 3:
- Best scenes to show:
- Scenes that must not be implied:

### 4. Structure, Accessories, And Proof
- Visible structure details that must stay accurate:
- Included accessories:
- Package contents:
- Certificates, badges, platform logos, or authorization claims:
- Proof materials available:

### 5. 由竞品启发但必须确认的高风险点
- 按当前产品列出：例如电器的电池/噪音/档位/安全认证，家具的承重/安装/材料，服饰的尺码/面料/洗护，美容个护的成分/防水/认证，电子设备的端口/兼容/授权等。

### 6. 禁止或谨慎表达
- 不能写的功能：
- 不确定的参数：
- 不想夸大的卖点：
- 不能出现的配件：
- 不能使用的认证、logo 或平台标识：
```

## Rules

- Do not treat competitor claims as true for the user's product.
- Do not rank a point highly only because competitors repeat it; judge buyer impact.
- Do not copy competitor visual compositions or wording.
- Use exact dates if live web data is collected.
- Keep the output concise enough to become a practical upstream document, not a screenshot dump.
- Only analyze competitor main images, secondary images, and A+ screenshots in this skill. Do not expand into brand story, title, bullet, price, rating, or review analysis unless the user explicitly asks for a separate task.
- In the Amazon AI design workflow, collect self-product facts inside `竞品卖点与展示逻辑整理.md` under `自家产品信息待填写`; avoid making a second product-info questionnaire file unless the dynamic Product Facts Gate later needs `product_facts_gate.md`.
