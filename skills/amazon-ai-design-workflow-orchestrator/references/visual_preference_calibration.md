> Legacy v1 contract for existing 0.6.10/0.6.11 runs only. New 1.0.0 runs use `reference_discovery.md`; never apply the module-card/source-quota/pairwise rules below to a new run.

# 卖货设计参考与视觉偏好校准合同

Version: `1`

本合同用于解决两个问题：参考案例质量不稳定，以及用户对“画面风格”和“信息排版”的偏好被误压成一个模糊风格标签。

`VISUAL_PREFERENCE_CALIBRATION` 是 `FULL_FLOW` 的人工与机器双重门禁。竞品 A+ 负责确定卖货逻辑；专业设计项目负责确定画面语言和排版系统。两类证据不可互相替代，也不可覆盖产品事实。

## 1. 固定来源策略

最终评分池优先来自以下八个固定来源，机器字段使用右侧 `source_key`：

| 来源 | `source_key` | 主要用途 |
|---|---|---|
| 站酷 ZCOOL | `ZCOOL` | 国内电商详情页、品牌视觉、完整项目 |
| 致设计 | `ZHISHEJI` | 电商卖货模块、字体与信息排版 |
| 数英项目库 | `DIGITALING` | 广告创意、品牌战役、卖点表达 |
| Behance | `BEHANCE` | 国际品牌视觉、消费电子、编辑排版 |
| Fonts In Use | `FONTS_IN_USE` | 字体层级、标题与正文关系 |
| Ads of the World | `ADS_OF_THE_WORLD` | 广告摄影、单一传播记忆点 |
| 古田路9号 | `GTN9` | 中文品牌、包装与商业视觉系统 |
| World Brand Design Society | `WBDS` | 国际品牌、包装与完整视觉系统 |

补充来源：

- `PENTAWARDS`：只补充高端相邻品类的材质、配色和包装表现。
- `OTHER_TRACEABLE`：只在固定来源覆盖不足时使用，必须能追溯到完整原始项目。
- 花瓣只用于发现线索。进入最终评分池前必须回溯到原始完整项目，并使用原站 `source_key`；不得把花瓣单图本身当正式来源。

以下网站或素材不作为 A+ 排版主参考：Awwwards、Land-book、Mobbin、SiteInspire、纯网站首页、App UI、Dribbble 单张 shot、无出处 Pinterest/花瓣单图。它们最多用于探索，不得直接进入正式评分池。

## 2. 搜索与筛选负载

不要让用户给无规则的 24-36 张图逐张打分。采用两段式漏斗：

1. AI 在固定来源内收集 16-30 个完整项目候选，只保存标题、来源、原始链接、用途和小预览。
2. 去重、聚类并通过质量门禁后，只把 8-12 张评分卡交给用户；稀缺类目可使用 6-12 张，但必须记录 `selection_mode: SPARSE_CATEGORY` 和无法获得 8 张合格卡的原因。
3. 最终评分单位是“完整项目模块卡”，不是项目封面或单张 hero。每个项目下载 4-6 张互不重复、可读的模块证据，并至少覆盖 `HERO`、`SELLING_MODULE`、`LAYOUT_SYSTEM`、`TYPOGRAPHY_ICON`；可追加 `FULL_PROJECT_OVERVIEW` 或 `CAMPAIGN_VARIATION`。每个 evidence 都写 `source_project_url`，规范化后必须等于本卡 `project_url`，禁止把多个项目拼成一张卡。

最终评分卡中至少 80% 必须来自八个固定核心来源。跨类目参考的顺序是：

1. 同类目优秀卖货设计；
2. 相邻高端产品，如消费电子、高端家电、家居、个护；
3. 广告摄影、编辑设计与品牌视觉；
4. 少量刻意不同的对照方向，防止选择范围过窄。

每张卡还必须标记 `reference_tier`：`SAME_CATEGORY`、`ADJACENT_PREMIUM`、`EDITORIAL_BRAND` 或 `CONTRAST`。STANDARD 池至少覆盖 3 个 tier，SPARSE_CATEGORY 至少覆盖 2 个；`SAME_CATEGORY + ADJACENT_PREMIUM` 至少占 50%，`CONTRAST` 不超过 25%。

稀缺类目不得因为“同类目案例少”而降低质量。竞品 A+ 继续提供购买理由、信息顺序和证据逻辑；相邻高端品类提供光影、材质、色彩、字体、图标和版式节奏。

## 3. 卖货设计质量门禁

每个候选项目按五项各 1-5 分，总分必须达到 `20/25`，且五个布尔门禁都为 `true`：

1. `product_subject`：产品或产品结果是明确主体，不是纯 UI 壳或空氛围。
2. `purchase_reason`：画面能传达购买理由、功能、结果或可信证据。
3. `information_hierarchy`：标题、证据、图标、参数和留白存在清晰主次。
4. `amazon_transferability`：可以迁移成 Amazon 主图/A+ 模块，而不依赖网页交互。
5. `traceable_project`：能追溯到原始完整项目与作者/发布页，且固定来源的 `source_key` 必须与原始链接域名一致。

直接排除：

- 纯网站或 App UI；
- 只有情绪、没有产品或购买理由；
- 只有包装 mockup，无法看到完整商业信息层级；
- 单张练习图、AI 练习图、无法追溯来源的截图；
- 字体、图标或关键文案小到无法判断；
- 只截取项目封面、首屏 hero 或单张广告，无法同时判断画面与排版；
- 同项目近似页面、同构图换色、重复 crop；
- 与 Amazon 模块任务无可迁移关系的艺术图。

评分池应覆盖尽量多的结构对照：暖/冷、明亮/深色、对称/非对称、完整产品/大幅裁切/局部特写、场景/影棚/抽象技术、柔光/方向性强光、极简文案/编辑排版/数据图形、人物/无人。

## 4. 用户评分：两个轴分开

每张卡必须使用固定模块评分器：桌面双栏、移动端单栏，卡内显示 4-6 个项目模块、编号、来源、项目名、角色、tier、原项目链接，以及 `visual` / `layout` 两排快捷按钮；支持放大和自动回传。不要用一张小联系表加 `R01 1/0` 文本回复作为正常路径，也不要让用户在长页面里一张张上下滚动找描述。正式证据始终是 JSON。

在发布评分界面前运行：

```bash
python3 scripts/build_visual_reference_rater.py \
  --project-root '<project-root>' \
  --pool '<project-root>/visual_reference_pool.json' \
  --output '<task-owned-visualization-dir>/visual-reference-rater.html' \
  --title '<product> 卖货设计偏好评分'
```

当前 Python 缺少 Pillow 时，使用 Codex bundled workspace Python。生成器会在渲染前复核固定来源、项目链接、质量门禁、tier 配比和模块证据，并拒绝小于 240×160、极端狭长或感知上近似重复的模块；任一不合格都不得展示给用户。生成物必须是小于 1 MB 的自包含 HTML fragment，并在同一轮直接作为内联评分界面展示；如果内联表面真实不可用，渲染为可点击的本地独立页，仍使用相同按钮与自动生成 payload，不退化成手抄评分行。普通 contact sheet 只能用于研究审计，不得替代评分器。

评分器 payload 必须包含 `rater_contract_version: 1`、`interaction_mode: MODULE_CARD_BUTTONS` 和生成评分器时的 `reference_pool_sha256`。生成器会原子保存同字节的 `visual_reference_pool.pending.json`；收到结果后，先确认当前尚未改写的 pool hash 与 payload 一致，再写入评分、把状态改为 `RATED`，并将这三个字段和有序 `sample_ids` 保存到顶层 `rating_submission`。状态机随后重算 pending 快照 hash，并确认除了状态、两轴评分和 submission 外没有其他字段变化。缺少这些字段、快照丢失、pool 已变化，或只收到手写 `R01 1/0` 时，不得转录为正式评分；重新展示当前 pool 的评分器。

统一量表：

- `1`：喜欢，愿意作为锚点；
- `0`：可用，但不是主偏好；
- `-1`：不喜欢，应作为拒绝证据；
- `null`：未评分，不计入统计。

两个评分轴：

- `visual` / 画面风格：色彩、明暗、光线、摄影、材质、空间氛围、产品表现方式。
- `layout` / 信息排版：字体层级、文案密度、图标、网格、留白、阅读顺序、数据组织和整体节奏。

至少 6 张卡必须同时完成 `visual` 和 `layout` 评分。分析时先分别总结两个轴，再生成明确拒绝项；禁止把两个轴直接求和后选一个“总冠军风格”。

## 5. 受控两两对比

满足任一情况时进入第二轮；机器最低判定是：任一轴少于 2 张 `1`、两轴正向卡没有交集、或出现 `1/-1` 交叉冲突时，`pairwise_round.status` 不得为 `NOT_REQUIRED`，必须先进入冻结控制项的 `PENDING`，完成真实对比和用户选择后再改为 `APPROVED`：

- 画面赢家与排版赢家来自不同方向；
- 某一轴没有稳定正向信号；
- 用户对某一候选出现 `visual=1` 但 `layout=-1`，或反向冲突；
- 用户明确拒绝第一轮推导出的排版或画面系统；
- 两个以上方向无法从第一轮区分。

第二轮每组只能改变一个主要变量，并锁定四个控制项：

- `same_product`
- `same_copy`
- `same_slot`
- `same_canvas`

四个控制项不能只写名称。先把 `pairwise_round.status` 设为 `PENDING`，冻结 `pairwise_round.control_values`：项目内产品参考路径及其 hash、非空完整对比文案及其 hash、slot id 和目标画布；此时 `candidates` 与 `comparisons` 必须为空。机器重新计算文件与文案 hash；只有这些基础证据全部有效，状态机才开放本轮 image2。再按 JSON key 排序、无多余空格计算 `pairwise_controls_sha256`。每张候选必须通过 image2 生成，写入实际文件路径、输出 hash、prompt hash，并在 `generation_ledger.jsonl` 记录 `stage: VISUAL_PREFERENCE_PAIRWISE`、相同 controls hash、相同 slot 和受控产品参考。每个候选的 generation id、输出路径、输出 hash 和 prompt hash 都必须唯一；只有文件、尺寸、时间、参考与 ledger 都能对上的候选才可进入比较。

优先安排 2 组两两对比，而不是再给一批无关案例。画面系统与排版系统分别选择。只有第二轮仍存在实质歧义时才做第三轮；如果两个系统已经稳定，记录 `NOT_REQUIRED` 或 `APPROVED`，不要为了流程完整继续消耗用户时间和生图额度。

每组 comparison 必须列出两个真实 `candidate_ids`；`visual_choice` 和 `layout_choice` 只能选择该组中的候选 id 或 `REJECT`。不得写未生成的候选、形式化占位符或组外选择。`PENDING` 时只有已验证的 `control_values` 非空，`candidates` 和 `comparisons` 都必须为空；生成、记账并取得用户选择后，主控一次性写入候选/比较并切换为 `APPROVED`。`NOT_REQUIRED` 时 `control_values`、`candidates` 和 `comparisons` 都必须为空。

## 6. 可执行混合风格配方

`visual_preference_profile.json` 必须把结果写成可执行设计系统，而不是“高级、简约、科技感”这类形容词：

- `visual_system.keep`：保留的色彩、光线、材质、摄影和产品表现规则。
- `visual_system.exclude`：有该轴负向证据时记录明确排除的画面模式；没有负向证据时使用空数组，禁止从 `0` 推断拒绝项。
- `layout_system.keep`：保留的字体层级、留白、网格、图标和阅读节奏。
- `layout_system.exclude`：有该轴负向证据时记录明确排除的排版模式；没有负向证据时使用空数组。
- `hybrid_recipe.visual_anchor_sample_ids`：只负责画面语言的正向样本锚点。
- `hybrid_recipe.layout_anchor_sample_ids`：只负责排版语言的正向样本锚点。
- 某一轴没有任何评分为 `1` 的卡片时，对应 `*_anchor_sample_ids` 必须保持 `[]`，不得把 `0` 分卡提升为正向锚点。该轴只能通过冻结控制项的真实两两候选、`VISUAL_PREFERENCE_PAIRWISE` ledger 和用户比较结果完成解析；`PENDING` 只开放受控生成，不能通过最终偏好门禁。
- `hybrid_recipe.rules`：说明如何把两个系统组合到当前产品与模块中。
- `rejected_patterns`：跨模块持续生效且有评分证据的拒绝项；没有任何负向证据时使用空数组。

如果某轴存在 `-1`，对应 exclude 不得为空；如果任一轴存在 `-1`，`rejected_patterns` 不得为空。反过来，没有该轴负向证据时禁止填写该轴 exclude。

Style Specs、样图、正式矩阵与提示词必须读取这份 profile。参考图只提供设计语法，禁止复制品牌识别、商标、受保护图形、原文案或完整构图；产品事实、产品参考图与局部细节锁始终拥有更高权重。

## 7. 机器证据

### `visual_reference_pool.json`

```json
{
  "version": 1,
  "run_identity": "active run identity",
  "status": "RATED",
  "source_policy_version": "1",
  "rater_contract_version": 1,
  "selection_mode": "STANDARD",
  "rating_submission": {
    "rater_contract_version": 1,
    "interaction_mode": "MODULE_CARD_BUTTONS",
    "reference_pool_sha256": "sha256 of the exact PENDING_RATING pool used to build the rater",
    "sample_ids": ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08"]
  },
  "samples": [
    {
      "id": "R01",
      "source_key": "BEHANCE",
      "project": "Traceable complete project title",
      "project_url": "https://www.behance.net/gallery/original-project",
      "role": "VISUAL_STYLE",
      "reference_tier": "ADJACENT_PREMIUM",
      "quality_score": 23,
      "quality_flags": {
        "product_subject": true,
        "purchase_reason": true,
        "information_hierarchy": true,
        "amazon_transferability": true,
        "traceable_project": true
      },
      "module_card": {
        "mode": "MODULE_COLLAGE",
        "evidence": [
          {
            "path": "reference-modules/R01/01-hero.jpg",
            "sha256": "sha256 of the exact downloaded project module",
            "module_role": "HERO",
            "source_project_url": "https://original-project-page.example/work/123"
          },
          {
            "path": "reference-modules/R01/02-selling.jpg",
            "sha256": "sha256 of the exact downloaded project module",
            "module_role": "SELLING_MODULE",
            "source_project_url": "https://original-project-page.example/work/123"
          },
          {
            "path": "reference-modules/R01/03-layout.jpg",
            "sha256": "sha256 of the exact downloaded project module",
            "module_role": "LAYOUT_SYSTEM",
            "source_project_url": "https://original-project-page.example/work/123"
          },
          {
            "path": "reference-modules/R01/04-type-icon.jpg",
            "sha256": "sha256 of the exact downloaded project module",
            "module_role": "TYPOGRAPHY_ICON",
            "source_project_url": "https://original-project-page.example/work/123"
          }
        ]
      },
      "visual": 1,
      "layout": 0
    }
  ]
}
```

允许的 `role`：`SELLING_LOGIC`、`VISUAL_STYLE`、`LAYOUT`、`TYPOGRAPHY_ICON`、`CONTRAST`。

### `visual_preference_profile.json`

```json
{
  "version": 1,
  "run_identity": "active run identity",
  "status": "APPROVED",
  "reference_pool_sha256": "sha256 of visual_reference_pool.json",
  "visual_system": {
    "keep": ["directional soft light with controlled highlights"],
    "exclude": ["muddy dark lifestyle collage"]
  },
  "layout_system": {
    "keep": ["editorial hierarchy with measured whitespace"],
    "exclude": ["equal-weight dense feature blocks"]
  },
  "hybrid_recipe": {
    "visual_anchor_sample_ids": ["R01"],
    "layout_anchor_sample_ids": ["R04"],
    "rules": ["Use R01 only for light and material; use R04 only for hierarchy and spacing"]
  },
  "rejected_patterns": ["low-contrast copy on dark panels"],
  "pairwise_round": {
    "status": "APPROVED",
    "reason": "Positive anchors diverged across the two axes",
    "control_values": {
      "product_reference_path": "pairwise/product_reference.png",
      "product_reference_sha256": "sha256 of the locked product reference",
      "copy_text": "Pocket power, ready when you are.",
      "copy_sha256": "sha256 of the frozen comparison copy",
      "slot_id": "PAIRWISE-A01",
      "target_size": [1464, 600]
    },
    "candidates": [
      {
        "candidate_id": "S1",
        "generation_id": "PAIRWISE-S1",
        "output_path": "pairwise/S1.png",
        "output_sha256": "sha256 of pairwise/S1.png",
        "prompt_sha256": "sha256 of the frozen S1 prompt"
      },
      {
        "candidate_id": "S2",
        "generation_id": "PAIRWISE-S2",
        "output_path": "pairwise/S2.png",
        "output_sha256": "sha256 of pairwise/S2.png",
        "prompt_sha256": "sha256 of the frozen S2 prompt"
      }
    ],
    "comparisons": [
      {
        "pair_id": "PAIR1",
        "candidate_ids": ["S1", "S2"],
        "visual_choice": "S1",
        "layout_choice": "S2"
      }
    ],
    "controls": ["same_product", "same_copy", "same_slot", "same_canvas"]
  }
}
```

机器门禁要求：

- `STANDARD` 最终评分池 8-12 张；只有 `SPARSE_CATEGORY` 加非空原因时可降到 6-12 张；`rater_contract_version: 1` 的池必须每张完成双轴评分，历史兼容池至少 6 张；
- 至少 80% 来自八个固定核心来源；
- 所有入池卡达到 `20/25` 且五项质量门禁为真；
- `rater_contract_version: 1`；`RATED` 池必须有来自匹配 `visual_reference_pool.pending.json` hash 的 `rating_submission`，交互方式为 `MODULE_CARD_BUTTONS` 且 `sample_ids` 与卡片顺序一致；每张卡有 4-6 个项目内、hash 正确且路径唯一的 `module_card.evidence`，至少覆盖 `HERO`、`SELLING_MODULE`、`LAYOUT_SYSTEM`、`TYPOGRAPHY_ICON`；每个 `source_project_url` 规范化后等于本卡 `project_url`，跨项目混拼或单封面卡不得进入评分；
- 固定 `source_key` 与原始项目域名一致，池内至少包含一张 `VISUAL_STYLE` 和一张 `LAYOUT` 卡；
- 项目链接规范化为 HTTPS、标准 host/path，删除 `utm_*`、`fbclid` 等跟踪参数和 fragment，同时保留决定项目身份的查询参数；规范化后必须唯一；
- STANDARD 至少覆盖 3 个 `reference_tier`，SPARSE_CATEGORY 至少 2 个；同类目/相邻高端至少占 50%，对照卡不超过 25%；
- profile 的 `run_identity` 与参考池一致，并绑定当前参考池 SHA-256；
- 两套 keep 必须非空；exclude 与拒绝项必须与 `-1` 证据一致：有负向证据必须非空，无负向证据必须为 `[]`；
- 画面锚点必须引用 `visual=1` 的卡，排版锚点必须引用 `layout=1` 的卡；
- 两两对比状态只能是 `PENDING`、`APPROVED` 或 `NOT_REQUIRED`，必须写原因并声明四个控制项；`PENDING` 只有在非空完整控制值及 hash 全部有效、candidates/comparisons 为空时才开放生成，但不能通过最终偏好门禁；`APPROVED` 必须保留冻结的 `pairwise_round.control_values`，`pairwise_round.candidates` 至少有两个 generation id、输出路径、输出 hash 和 prompt hash 均唯一且 hash 正确的真实候选，每个候选都匹配 `VISUAL_PREFERENCE_PAIRWISE` 成功 ledger 记录及 controls hash；`pairwise_round.comparisons` 只能从本组候选或 `REJECT` 中选择；`NOT_REQUIRED` 的 control values、candidates 和 comparisons 必须为空；机器判定存在冲突/弱信号时不得使用 `NOT_REQUIRED`。

批准后还要向下游绑定：每条 `STYLE_SAMPLES` 成功 ledger 记录和 `production_plan.json` 都必须写当前 `visual_preference_profile_sha256`。profile 内容变化后，旧样图证据与旧生产计划自动失效，必须重新生成或重新批准，不能继续沿用旧偏好。

`bootstrap_run.py` 创建的 `active_run.json` 使用 `workflow_version: 0.6.11`，因此新 run 强制执行模块评分卡与双轴偏好门禁。已批准的 0.6.10 `RATED` bundle 继续可读；0.6.10 中尚未评分的 pool 必须先升级为 `rater_contract_version: 1` 模块卡再展示，不得沿用单缩略图联系表。一旦创建其他偏好产物，仍视为主动迁移并完整执行本合同。

缺少或不合格时，状态停在 `VISUAL_PREFERENCE_CALIBRATION`。不得用一段自由文本总结、HTML 评分页、旧项目偏好或一个“总体最喜欢”编号绕过门禁。
