# 主控与子智能体工作合同

Version: `1.0.0`

## 强制不变量

- `CONTROLLER_SINGLE_WRITER`: 主控是正式事实、状态、QC 结论和 manifest 的唯一写入者。图片子智能体只可写自己唯一的 raw 图片路径。
- `CONTROLLER_PLUS_THREE`: Codex 总并发上限为 4；主控占 1 个槽位，可同时运行 3 个子智能体。
- `BOUNDED_PARALLELISM`: 只有依赖已完成且写入文件不重叠的任务可以并行。
- `FIXED_THREE_LANE`: 正式生图阶段存在至少 3 个 ready slot 时，固定填满 3 个子智能体；任一完成就立即补位，不等小批次栅栏。
- `STEADY_WORKER_POOL`: 生图 ready queue 非空时持续补位；最后不足 3 个 slot 时才自然降至 2/1 路。
- `NO_SMOKE_GATES`: 取消白底参考图、MAIN 和 A+ 的所有首张试跑。已批准的参考、事实、矩阵和 prompt 是生图门禁。
- `UNIFIED_READY_QUEUE`: 正式生图开始前，把全部独立 MAIN/A+ slot 放入一个统一队列；MAIN/A+ 最终 QC 结论仍分开。
- `PHASE_BOUNDARY_SCHEDULER`: 只在生图阶段开始、阶段结束、恢复或真实 transport error 时刷新 scheduler；成功图片的耗时不会让 scheduler 失效。
- `SCHEDULER_STATE_GATE`: scheduler 必须匹配 active run、声明 `PHASE_BOUNDARY_SCHEDULER`，正常值为 3；只允许 transport error 恢复临时降为 2/1。
- `THIN_IMAGE_WORKER`: 图片 worker 只接收 task/slot、不可变 prompt、原生参考路径和唯一输出路径；禁止读取 Skill/项目文档、看图、做 QC、刷新状态/scheduler、写报告或 manifest。
- `FRESH_IMAGE_CONTEXT`: 图片 worker 必须用 `fork_turns="none"` 或等效无继承上下文方式启动；主控把五字段内联到任务消息，禁止只给 packet 文件路径让 worker 再读取。
- `MINIMAL_GENERATION_RECEIPT`: 图片 worker 只返回 task id、slot id、成功/错误、output path 和 elapsed time。
- `STANDARD_TRANSPORT_FAILURE`: 失败回执的 `error_type` 只能是 `AUTH`、`NETWORK`、`RATE_LIMIT`、`TIMEOUT`、`TRANSPORT` 或 `OTHER`。transport error 必须在恢复边界立即写 ledger，再刷新 scheduler；首次恢复成功也在恢复边界立即写入后恢复 3 路。
- `GENERATION_FIRST_QC_AFTER`: 全部 raw 图片完成前不派 finished-image QC。全部完成并通过 preflight 后，固定并行 3 个专职 QC：产品事实/结构、文案/风格、比例尺寸/技术。
- `MACHINE_QC_GATE`: 三份 QC profile 与 MAIN/A+ verdict 都是绑定当前 preflight hash 的 JSON；verdict 必须引用三份 profile 的路径/hash，并合并精确失败 slot。
- `WORKER_PACKET_REQUIRED`: 只有真实派发 worker 才创建 packet/registry。图片 packet 使用五字段薄合同；其他 worker 使用完整任务合同。
- `WORKER_REPORT_REQUIRED`: 只适用于非图片 worker 和 QC worker。图片 worker 使用最小回执，不创建 report file。
- `ONE_WORKER_ONE_SLOT`: 一个图片 worker 只负责一个 `slot_id` 和一个唯一 `raw_generated/<canonical-name>`。
- `DIRECT_UNIQUE_RAW_WRITE`: image worker 直接写 packet 指定的唯一 raw 文件；图片任务不经过 staged output 和逐图 promotion。
- `NORMALIZED_UNIQUE_PATHS`: 路径必须先 resolve/规范化再做冲突检查；`a/../same.png` 与 `same.png` 属于同一目标。
- `IMAGE_WORKER_REPORT_FORBIDDEN`: IMAGE_WORKER 禁止 `required_report_path`、`promoted_output_paths` 和 `workers/outputs`；成功 `VERIFIED` 只能来自内联 generation receipt。
- `NO_SHARED_WRITES`: 任意两个 worker 不得写同一文件；子智能体不得修改 scope、truth、locks、plan、prompt、state、ledger、checkpoint 或 manifest。
- `BRANCH_OUTPUT_ISOLATION`: 并行方案使用独立输出目录、修改脚本和写入归属；公共素材只读复用，独立 run 的状态放在各自根目录。主控将 SKILL.md 的基线保留项及 `ARTIFACT_SCOPED_METHOD` 写入对应任务输入，不把某一产物的方法扩展到其他方案。
- `SHARED_GUI_SERIALIZATION`: Photoshop、Blender、浏览器等共享控制会话同一时刻只有一个操作者；切换前明确交接。独立文件目录不能替代 GUI 操作隔离，无法隔离时顺序执行。
- `FAILED_SLOTS_ONLY`: QC 失败后只返工失败 slot，保留全部 passing raw。
- `COPY_QC`: 文案复核独立于 prompt 起草，检查含义、事实支持、栅格文字可读性、native copy 分离、alt text 和移动端可读性。
- `VISUAL_PREFERENCE_CALIBRATION`: 新 stable run 执行 `references/reference_discovery.md` v2：按画面/排版用途检索，精选库优先并补充新案例；来源和真实 evidence 保留路径/hash。用户只对适用轴点喜欢/一般/不喜欢；按钮默认走 `reference_discovery.py submit`；明确聊天指令走 `NATIVE_CHAT_FEEDBACK` / `chat-submit`，带用户原话并绑定当前 pending hash、round 与 action，不要求重复点击。只提取明确样本/轴分数，全换不伪造逐卡 -1。`CONTINUE` 在画面与排版均有显式正向锚点时标记 `RATED`，再由主控写 hash-bound profile；`RESEARCH_ALL` 全换，`RESEARCH_REJECTED` 保留喜欢并替换其余，无正向则 `RESEARCH_REQUIRED`。不要求用户逐图解释、模块分配、额外 profile 批准或额外生成 pairwise。
- `POSITIVE_CREATIVE_DIRECTION`: 正式 prompt 必须正向定义消费者结果、视觉主体、构图关系、光影材质和商业完成度。
- `ONE_VISUAL_MEMORY_POINT`: 每个 slot 只设一个主导视觉记忆点，并明确第一视觉、产品角色、空间层次与阅读路径。
- `COPY_OCCURRENCE_RULE`: 只能使用 `production_plan.json` 已批准的 `image_embedded_copy`，字段为空时不得自行新增栅格文字；每条栅格文案及关键子数值默认只出现一次，未经批准的新增标题、辅助句、图标文字或数字重复均阻断 prompt QC。
- `EVIDENCE_BASED_OMISSION`: 事实确认不能替代外观或几何证据；无外观依据的配件、内部结构和状态只保留文字，不生成物体、线稿、轮廓、剪影或图标。
- `DELEGATION_GAIN_THRESHOLD`: 120 秒阈值只约束非图片辅助任务；image2 生图默认具有足够并行收益。
- `SEQUENTIAL_FALLBACK`: 子智能体不可用或写入无法隔离时，主控顺序执行，不伪造 packet、receipt 或 report。
- `SAME_TASK_CONTINUATION`: 选定风格后在当前任务继续矩阵、prompt、生图、QC 和导出。
- `OPTIONAL_CONTEXT_HANDOFF`: 只在用户要求或真实技术恢复条件下创建新任务接力。
- `EVENT_DRIVEN_WAIT`: 使用一次 60-120 秒有界事件等待；禁止高频轮询、反复 agent list 和每次 timeout 全量查状态。
- `STATE_REFRESH_BUDGET`: 仅在初始化/恢复、人工门禁、正式阶段边界、阶段变化和最终验证刷新状态。
- `READ_ONCE_PER_TURN`: 同一轮只读取一次 Skill 和合同；仅文件变化、上下文丢失或恢复时重读。
- `INTERRUPTION_RESUME`: Mac 黑屏、休眠或断网后，从现有文件、registry、receipt 和 raw 输出恢复，不重做已完成工作。

## 1.0.0 证据门禁

- `FULL_FLOW_EXCLUSIVE_CONTROL`: FULL_FLOW 不得被 brainstorming、HTML/CSS 或临时样图替换。
- `ONE_MESSAGE_SCOPE_INTAKE`: 一次收齐 scope 并原子写入 `production_scope.json`。
- `REFERENCE_FIDELITY_LOCK`: 白底参考生图前，把结构锁与选中源图 hash 绑定。
- `REFERENCE_THREE_WAY_PARALLEL`: main、angle、structure three white-background references 同时生成；QC only after all three raw references exist，再进行一次人工批准。
- `VISUAL_PREFERENCE_CALIBRATION`: 新 stable run 执行 `references/reference_discovery.md` v2：按画面/排版用途检索，精选库优先并补充新案例；来源和真实 evidence 保留路径/hash。用户只对适用轴点喜欢/一般/不喜欢；按钮默认走 `reference_discovery.py submit`；明确聊天指令走 `NATIVE_CHAT_FEEDBACK` / `chat-submit`，带用户原话并绑定当前 pending hash、round 与 action，不要求重复点击。只提取明确样本/轴分数，全换不伪造逐卡 -1。`CONTINUE` 在画面与排版均有显式正向锚点时标记 `RATED`，再由主控写 hash-bound profile；`RESEARCH_ALL` 全换，`RESEARCH_REJECTED` 保留喜欢并替换其余，无正向则 `RESEARCH_REQUIRED`。不要求用户逐图解释、模块分配、额外 profile 批准或额外生成 pairwise。
- `IMAGE2_PROVENANCE_GATE`: 每次 image2 都保留 prompt、参考、时间、输出和 hash 证据；并行阶段在边界批量写 `generation_ledger.jsonl`。`STYLE_SAMPLES` 记录必须绑定当前 `visual_preference_profile_sha256`。
- `CANONICAL_PRODUCTION_PLAN`: `production_plan.json` 是 slot、尺寸、prompt、文案、参考和输出路径的唯一事实源，并绑定当前 `visual_preference_profile_sha256`；profile 变化后旧 plan 自动失效。
- `DETERMINISTIC_PREFLIGHT`: 全 raw 完成后一次运行 `preflight_qc.json`；`OCR_UNAVAILABLE` 只能转视觉 QC，不能当文字 PASS。

## 角色

| 角色 | 任务范围 | 禁止事项 |
|---|---|---|
| `RESEARCH_WORKER` | 竞品、大牌或本产品研究草案 | 不得确认产品参数或声明 |
| `COPY_WORKER` | 卖点、图片文案、native copy、alt text | 不得新增产品事实 |
| `LAYOUT_WORKER` | 模块任务、P0-P4、版式和重复风险 | 不得发布正式矩阵 |
| `PROMPT_WORKER` | MAIN 或 A+ prompt 草案 | 不得改变 scope、数量或风格 |
| `IMAGE_WORKER` | 一个白底参考、风格样图或正式 slot | 只调用一次 image2，不得 QC 或扩展任务 |
| `QC_WORKER` | 只读产品结构、文案风格或技术 QC | 不得生图、返工或写 manifest |

## 图片 worker 五字段任务包

`LATEST_IMAGE_MODEL`: 主控先核对当前官方模型文档并验证可执行路线，再在 worker 任务消息中内联“已解析的目标模型、支持该模型的执行路线、版本验证状态”。这些是独立于五字段业务 packet 的执行指令，不追加 packet 字段，也不把模型名称塞进生图 prompt 冒充模型选择。`image2` / `provider: image2` 是兼容路线标识，不是真实模型版本。worker 不读额外文件；无法执行指定路线时返回标准 `OTHER` 失败，`error_message` 包含 `model_selection_unavailable`。严格要求最新模型而路线不可选择/核实时，主控在派发前标记 blocked，实际模型记为 `unknown` / `unverified`；不得偷偷改用付费 API。目标/实际模型、验证依据与官方来源由主控记录在既有 run notes，最小回执不构成底层版本证明。

图片 packet 只能包含：

```json
{
  "task_id": "IMG-M01",
  "slot_id": "M01",
  "prompt": "approved immutable prompt",
  "referenced_image_paths": ["/absolute/reference.png"],
  "output_path": "/absolute/project/raw_generated/main_01_raw.png"
}
```

禁止向图片 worker 追加 `read_only_inputs`、`fact_authority`、整份 `production_plan.json`、Skill 路径、项目说明、`acceptance_checks` 或 `required_report_path`。这些内容必须在 prompt 冻结前由主控处理。

图片 worker 的唯一动作：

1. 使用 packet 内原生参考路径调用 image2 一次。
2. 将结果保存到唯一 `output_path`。
3. 返回 `MINIMAL_GENERATION_RECEIPT`：

```json
{
  "task_id": "IMG-M01",
  "slot_id": "M01",
  "status": "SUCCEEDED",
  "output_path": "/absolute/project/raw_generated/main_01_raw.png",
  "elapsed_ms": 120000
}
```

worker 不打开输出、不判断结构/文案/比例、不重读任何规则、不更新 registry/ledger/scheduler/state。

失败时回执不含 `output_path`，必须包含标准化错误：

```json
{
  "task_id": "IMG-M01",
  "slot_id": "M01",
  "status": "FAILED",
  "error_type": "NETWORK",
  "error_message": "connection reset",
  "elapsed_ms": 30000
}
```

## 非图片 worker 任务包

研究、文案、版式、prompt 和 QC 任务保留：

- `run_identity`
- `task_id`
- `role`
- `stage`
- `depends_on`
- `objective`
- `read_only_inputs`
- `fact_authority`
- `allowed_claims`
- `forbidden_claims`
- `allowed_write_paths`
- `acceptance_checks`
- `required_report_path`
- `estimated_seconds >= 120`
- `independent: true`
- `parallel_gain: true`

它们写入独立 `workers/outputs/<task_id>` / report 路径，并返回 machine-readable report。

## `agent_task_registry.json`

只有真实派发时创建，主控独占写入。允许状态：`PLANNED`、`DISPATCHED`、`RUNNING`、`REPORTED`、`VERIFIED`、`FAILED`、`CANCELLED`。

- 图片 task 禁止 `required_report_path`、`promoted_output_paths` 和 `workers/outputs`；完成后主控在阶段边界把成功 receipt 作为 `generation_receipt` 写入 registry，并设为 `VERIFIED`。
- 图片失败 task 必须带标准化失败 receipt 并设为 `FAILED`。transport error 在恢复边界立即写 ledger，不等整批结束。
- 非图片/QC task 仍需独立 report，主控核验后才设为 `VERIFIED`。
- 拒绝重复 `task_id`、图片 `slot_id`、raw output path、report path 和重叠 write path。
- receipt 的 output 必须存在、位于 `raw_generated`、匹配 task/slot 并有正 elapsed time。

## 阶段并行规则

`bootstrap_run.py` 创建的 `active_run.json` 必须写 `workflow_version: 1.0.0`。新正式 run 使用 `rater_contract_version: 2`；不要自动改写或批准正式版 v1 pool，也不要把旧文件的存在当作当前 stable 进度。

1. 白底参考：3 个 thin image workers 同时生成 main/angle/structure；三张齐后自动 QC，再人工批准。
2. 产品锁定后：竞品研究和本产品卖点研究可并行。
3. 产品事实确认后：按画面/排版用途搜索与文案架构可并行；主控按 `references/reference_discovery.md` 调用精选库、补新、看图、去重并发布 v2 pool。
4. 通过 v2 按钮提交后：需要重搜就保留喜欢/替换其余或全换；没有某轴喜欢时继续找参考。`CONTINUE` 校验成功后直接建立 `visual_preference_profile.json`，不加一次批准或生图 gate。
5. Profile 通过后：A/B/C 只在批准的混合配方内做有边界变化，由 3 个 thin image workers 同时生成；每条成功 ledger 绑定当前 profile hash，全部完成后比较 QC。
6. 选中风格后：版式和文案草案可并行；主控发布唯一、绑定当前 profile hash 的 plan。
7. 正式矩阵后：MAIN/A+ prompt 草案可并行；每条草案先通过 `POSITIVE_CREATIVE_DIRECTION`、`ONE_VISUAL_MEMORY_POINT`、`COPY_OCCURRENCE_RULE`、`EVIDENCE_BASED_OMISSION`，主控再冻结全部 prompt/reference/output。
8. 正式生图：全部 slot 进入统一队列，固定 3 路持续补位；无任何 smoke 或逐图 QC。
9. 全 raw 完成：一次 preflight，然后 3 个专职 QC profile 并行，分别写 `qc_product_structure.json`、`qc_copy_style.json`、`qc_technical.json`。
10. 主控写 `main_batch_qc_verdict.json` / `aplus_batch_qc_verdict.json`，引用三份 profile hash 并合并 exact `failed_slot_ids`；旧 Markdown PASS 不构成门禁。
11. 返工：只把失败 slot 放回 thin-worker 队列；同一问题最多两轮。

## 集中 QC JSON schema

三份 profile 分别使用 `QC_PRODUCT_STRUCTURE`、`QC_COPY_STYLE`、`QC_TECHNICAL`：

```json
{
  "version": 1,
  "run_identity": "active run identity",
  "profile_id": "QC_PRODUCT_STRUCTURE",
  "status": "PASS",
  "preflight_sha256": "current preflight_qc.json sha256",
  "reviewed_slot_ids": ["M01", "APB01"],
  "failed_slot_ids": [],
  "blocking_findings": []
}
```

有 blocking failure 时，`status` 必须为 `FAIL`，`failed_slot_ids` 与 `blocking_findings[].slot_id` 必须完全一致，每条 finding 含非空 `finding`。

MAIN/A+ verdict schema：

```json
{
  "version": 1,
  "run_identity": "active run identity",
  "batch": "MAIN",
  "status": "PASS",
  "preflight_sha256": "current preflight_qc.json sha256",
  "slot_ids": ["M01"],
  "failed_slot_ids": [],
  "profile_reports": [
    {"profile_id": "QC_PRODUCT_STRUCTURE", "path": "preview/qc_product_structure.json", "sha256": "profile sha256"},
    {"profile_id": "QC_COPY_STYLE", "path": "preview/qc_copy_style.json", "sha256": "profile sha256"},
    {"profile_id": "QC_TECHNICAL", "path": "preview/qc_technical.json", "sha256": "profile sha256"}
  ],
  "blocking_findings": []
}
```

失败 verdict 的每个 `blocking_findings` 项必须含 `slot_id`、所有来源 `profile_ids` 和非空 `findings` 列表。`failed_slot_ids` 必须等于三份 profile 在该 batch 上的失败 slot 并集。

## 主控独占文件

子智能体只读或不可写：

- `active_run.json`
- `production_scope.json`
- `reference_strategy.json`
- `reference_fidelity_lock.json`
- `visual_reference_pool.json`
- `visual_preference_profile.json`
- `generation_ledger.jsonl`
- `production_plan.json`
- `scheduler_state.json`
- `01_product_truth.md`
- `03_product_detail_locks.md`
- `product_facts_confirmation.md`
- `selected_style.md`
- `完整出图版式规划矩阵.md`
- 正式 prompts
- `design_workflow_state.json` / `.md`
- checkpoint、partial manifest、final manifest

唯一例外：图片 worker 可写 packet 指定的、互不重叠的 `raw_generated/<canonical-name>`。
