# 正式生产子智能体合同

Version: `1.0.0`

本合同只在真实派发 worker 时生效。主控顺序执行不得创建空 packet、receipt、report 或 registry。

## 强制生产规则

- `FULL_FLOW_EXCLUSIVE_CONTROL`: 正式生产不得被临时样图、brainstorming 或 HTML 旁路替换。
- `ONE_MESSAGE_SCOPE_INTAKE`: 生产范围必须已一次性确认。
- `REFERENCE_FIDELITY_LOCK`: 产品结构和参考 hash 必须已锁定。
- `LEGACY_VISUAL_PREFERENCE_COMPATIBILITY`: 新 stable run 或已经存在 `visual_reference_pool.json` / `visual_preference_profile.json` 时才强制视觉偏好门禁。无版本标记且两份偏好产物都不存在的显式历史 selected-style 项目沿既有生产路径继续，记录该门禁不可用，不伪造评分、profile 或 profile hash。
- `VISUAL_PREFERENCE_CALIBRATION`: 新 stable run 使用 orchestrator `references/reference_discovery.md` v2；不要求额外 pairwise、人工逐图理由或 profile 确认。在视觉偏好门禁适用时，orchestrator `FULL_FLOW` 必须有已批准且绑定当前参考池 hash 的 `visual_preference_profile.json`；`production_plan.json.visual_preference_profile_sha256` 必须匹配当前 profile，profile 变化后旧 plan 失效；主控把画面 keep/exclude、排版 keep/exclude、混合规则与拒绝项写入 plan/prompt，图片 worker 不直接读取 profile。
- `IMAGE2_PROVENANCE_GATE`: 每个 image2 call 都必须保留 prompt/reference/time/output/hash 证据；并行阶段由主控在边界批量写 ledger。
- `CANONICAL_PRODUCTION_PLAN`: `production_plan.json` 是全部 slot 的唯一事实源；视觉偏好门禁适用时必须绑定当前 `visual_preference_profile_sha256`，显式 legacy 例外不得伪造该字段。
- `CONTROLLER_SINGLE_WRITER`: 主控独占正式 plan、prompt、state、ledger、QC 结论、checkpoint 和 manifest。
- `CONTROLLER_PLUS_THREE`: 总并发 4，主控占 1，生图可用 3 个子智能体。
- `BOUNDED_PARALLELISM`: 不重叠的唯一 raw 文件才可并行写入。
- `NO_SMOKE_GATES`: 不执行 MAIN 或 A+ 首张试跑。Prompt QC 通过后，所有独立 slot 一次性 ready。
- `UNIFIED_READY_QUEUE`: 所有 MAIN/A+ slot 进入同一个生图队列。
- `FIXED_THREE_LANE`: `STEADY_WORKER_POOL` 有至少 3 个 ready slot 时必须保持 3 路；任一完成立即补位。
- `PHASE_BOUNDARY_SCHEDULER`: 正常值 3；只在阶段边界、恢复或真实 transport error 时刷新。成功延迟不触发降并发。
- `SCHEDULER_STATE_GATE`: scheduler 匹配 active run 并声明 `PHASE_BOUNDARY_SCHEDULER`。
- `THIN_IMAGE_WORKER`: 图片 worker 只带五字段 packet 调用 image2 一次；不读 Skill/项目文档、不看图、不做 QC、不刷新状态、不写长报告。
- `FRESH_IMAGE_CONTEXT`: 图片 worker 使用 `fork_turns="none"` 或等效无历史上下文；五字段必须内联传入，不得让 worker 先打开 packet 文件。
- `MINIMAL_GENERATION_RECEIPT`: 图片 worker 只返回 task/slot、status/error、output path 和 elapsed time。
- `STANDARD_TRANSPORT_FAILURE`: 失败回执使用 `AUTH`、`NETWORK`、`RATE_LIMIT`、`TIMEOUT`、`TRANSPORT` 或 `OTHER`。transport 失败在恢复边界立即写 ledger 后刷新 scheduler；首次恢复成功也立即写入后再恢复 3 路。
- `GENERATION_FIRST_QC_AFTER`: 全 raw 完成并跑 preflight 后，才并行派发产品结构、文案风格、尺寸技术 3 个 QC worker。
- `MACHINE_QC_GATE`: 三份 QC profile 与 MAIN/A+ verdict 必须是 hash-bound JSON；verdict 引用三份 profile 并合并 exact failed slots。
- `ONE_WORKER_ONE_SLOT`: 一个 worker 对应一个 `slot_id` 和唯一 `raw_generated/<canonical-name>`。
- `NO_SHARED_WRITES`: worker 不得写共享事实、plan、prompt、state、ledger、checkpoint、QC 结论或 manifest。
- `DIRECT_UNIQUE_RAW_WRITE`: image worker 直接写唯一 raw 路径，不经过 `workers/outputs` 暂存和主控逐图提升。
- `NORMALIZED_UNIQUE_PATHS`: 输出路径先规范化再查重，任何语法别名都视为同一写入目标。
- `IMAGE_WORKER_REPORT_FORBIDDEN`: IMAGE_WORKER 禁止 report path、promoted paths 和 worker staging；成功 VERIFIED 必须有内联 receipt。
- `FAILED_SLOTS_ONLY`: 返工只进入失败 slot；passing raw 不动。
- `COPY_QC`: 文案 QC 检查事实支持、含义、栅格可读性、native copy 分离、alt text 和移动端。
- `POSITIVE_CREATIVE_DIRECTION`: 每条冻结 prompt 都必须正向说明消费者结果、唯一视觉主角、构图关系、光影材质和商业完成度。
- `ONE_VISUAL_MEMORY_POINT`: 每张图只允许一个主导视觉记忆点，并明确产品角色、前中后景和阅读顺序。
- `COPY_OCCURRENCE_RULE`: 只能使用 `production_plan.json` 已批准的 `image_embedded_copy`，字段为空时不得自行新增栅格文字；每条允许文案和关键子数值默认只出现一次，未批准的额外标题、说明、标签、图标文字或数值重复都属于失败。
- `EVIDENCE_BASED_OMISSION`: 只有事实确认而没有外观/几何证据时，只保留文字，不生成配件、内部结构、产品状态、通用线稿、轮廓、剪影或示意图标。
- `CONTEXT_MINIMIZATION`: 图片 worker 只接收五字段；非图片/QC worker 只接收任务相关事实。
- `DELEGATION_GAIN_THRESHOLD`: 120 秒阈值只用于非图片辅助任务；正式 image2 slot 默认值得并行。
- `SEQUENTIAL_FALLBACK`: 子智能体不可用时主控顺序生成，不伪造 worker 产物。
- `EVENT_DRIVEN_WAIT`: 使用有界事件等待，不做反复 30 秒轮询或每次 timeout 全局扫描。
- `STATE_REFRESH_BUDGET`: 仅在恢复、人工门禁、正式阶段边界、阶段变化和最终验证刷新。
- `READ_ONCE_PER_TURN`: 同轮只读一次 Skill/合同。
- `INTERRUPTION_RESUME`: Mac 黑屏、休眠或断网后，从现有 raw、receipt、registry 和 run 文件恢复。
- `DETERMINISTIC_PREFLIGHT`: 全 raw 完成后一次执行；`OCR_UNAVAILABLE` 转视觉 QC，不能当 PASS。

## 主控独占文件

worker 不得修改：

- `production_scope.json`
- `reference_fidelity_lock.json`
- `visual_reference_pool.json`
- `visual_preference_profile.json`
- `generation_ledger.jsonl`
- `production_plan.json`
- `scheduler_state.json`
- `01_product_truth.md`
- `03_product_detail_locks.md`
- `完整出图版式规划矩阵.md`
- 正式 prompts、controller QC verdict、checkpoint、partial manifest 和 `production_manifest.json`

图片 worker 唯一可写例外是 packet 指定的唯一 `raw_generated/<canonical-name>`。

## 图片 worker 五字段 packet

`LATEST_IMAGE_MODEL`: 主控先核对当前官方模型文档并验证可执行路线，再在 worker 任务消息中内联“已解析的目标模型、支持该模型的执行路线、版本验证状态”。这些是独立于五字段业务 packet 的执行指令，不追加 packet 字段，也不把模型名称塞进生图 prompt 冒充模型选择。`image2` / `provider: image2` 是兼容路线标识，不是真实模型版本。worker 不读额外文件；无法执行指定路线时返回标准 `OTHER` 失败，`error_message` 包含 `model_selection_unavailable`。严格要求最新模型而路线不可选择/核实时，主控在派发前标记 blocked，实际模型记为 `unknown` / `unverified`；不得偷偷改用付费 API。目标/实际模型、验证依据与官方来源由主控记录在既有 run notes，最小回执不构成底层版本证明。

只允许：

```json
{
  "task_id": "IMG-M01",
  "slot_id": "M01",
  "prompt": "approved immutable prompt",
  "referenced_image_paths": ["/absolute/product-reference.png"],
  "output_path": "/absolute/project/raw_generated/main_01_raw.png"
}
```

目标比例、尺寸、产品事实、局部锁、允许/禁止声明、版式、文案和负面约束必须在主控冻结的 prompt 中表达。不得让图片 worker 再读 `production_plan.json`、`01_product_truth.md`、`03_product_detail_locks.md` 或本合同来补全任务。

图片 worker 只能：

1. 用 `referenced_image_paths` 作为 native image input 调用 image2 一次。
2. 保存到唯一 `output_path`。
3. 返回：

```json
{
  "task_id": "IMG-M01",
  "slot_id": "M01",
  "status": "SUCCEEDED",
  "output_path": "/absolute/project/raw_generated/main_01_raw.png",
  "elapsed_ms": 120000
}
```

禁止 `view_image`、OCR、像素检查、视觉检查、acceptance checks、Skill 重读、scheduler/state/ledger 更新和 narrative report。

失败回执不含输出路径，必须含标准化 `error_type`、非空 `error_message` 与正 `elapsed_ms`。

## 非图片 / QC worker packet

这些任务继续使用：

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

它们写入独立 `workers/outputs/<task_id>` 和 report path。只有主控能核验 report 并发布正式结论。

## `agent_task_registry.json`

只有真实派发时创建，主控独占写入。允许状态：`PLANNED`、`DISPATCHED`、`RUNNING`、`REPORTED`、`VERIFIED`、`FAILED`、`CANCELLED`。

图片 task：

- 禁止 `required_report_path`、`promoted_output_paths` 和 `workers/outputs`。
- `allowed_write_paths` 是唯一 raw 图片文件，而不是共享目录。
- 生图阶段结束时，主控批量写成功 `generation_receipt` 并把成功 task 设为 `VERIFIED`。
- 失败 task 使用标准失败 receipt 并设为 `FAILED`；transport 失败在恢复边界立即入 ledger。
- receipt 必须匹配 task/slot，status 成功，elapsed 正数，output 存在且位于 `raw_generated`。

非图片/QC task：

- 仍要求唯一 `required_report_path`、非空 checks 和 path-bounded outputs。
- `REPORTED` 不等于 `VERIFIED`。

registry 必须拒绝重复 task id、slot id、raw output、report path 和重叠 write path。

## 正式生图

1. 主控完成 scope、facts、layout、prompt 和 prompt QC。
2. 冻结所有 slot 的 prompt、native refs 和唯一 raw output。
3. 运行一次 `PHASE_BOUNDARY_SCHEDULER`，正常 recommendation 为 3。
4. 将所有独立 MAIN/A+ slot 放进 `UNIFIED_READY_QUEUE`。
5. 同时派发 3 个 `THIN_IMAGE_WORKER`；收到 completion event 就补下一张。
6. worker 只生图并返回 `MINIMAL_GENERATION_RECEIPT`；主控不在两张图之间做视觉 QC、state scan、scheduler refresh 或长报告验证。
7. 全部 raw 完成后，主控一次批量核对文件/成功 receipt，写 ledger、registry 和 generation checkpoint。
8. 发生 transport error 时，立即把标准失败记录写 ledger，再刷新 scheduler 并只重派失败 call；首次恢复成功也立即写入后恢复 3 路。成功 latency 慢不算 transport error。

## 成品 QC

`GENERATION_FIRST_QC_AFTER` 要求 raw queue 清空后才开始：

1. `DETERMINISTIC_PREFLIGHT`: 一次检查文件、hash、尺寸、比例和 OCR。
2. `QC_PRODUCT_STRUCTURE`: 产品轮廓、比例、材质、controls、ports、labels、accessories 和禁止发明。
3. `QC_COPY_STYLE`: claim support、文案含义/可读性、selling-point clarity、单一视觉记忆点、版式成熟度、文案/关键数值出现次数、无证据物体省略和移动端。
4. `QC_TECHNICAL`: filename、presence、raw dimensions、aspect error、target size、hash 和 correction eligibility。

第 2-4 项使用 3 个只读 QC workers 同时执行。主控合并为独立 MAIN/A+ authoritative verdict。任一 blocking failure 都不能被其他 profile 的 PASS 覆盖。

机器证据固定为：

- `preview/qc_product_structure.json`
- `preview/qc_copy_style.json`
- `preview/qc_technical.json`
- `preview/main_batch_qc_verdict.json`（有 MAIN 时）
- `preview/aplus_batch_qc_verdict.json`（有 A+ 时）

每份 profile 必须绑定当前 `preflight_qc.json` hash、覆盖完整 plan slots，并列出 `failed_slot_ids` 与 `blocking_findings`。每份 batch verdict 必须引用三份 profile 的路径/hash，并逐 slot 合并所有 blocking findings。缺一、hash 失配、失败 slot 超出 plan 或旧 Markdown PASS 都不能完成。

Profile schema：

```json
{
  "version": 1,
  "run_identity": "active run identity",
  "profile_id": "QC_TECHNICAL",
  "status": "PASS",
  "preflight_sha256": "current preflight_qc.json sha256",
  "reviewed_slot_ids": ["M01", "APB01"],
  "failed_slot_ids": [],
  "blocking_findings": []
}
```

Verdict schema：

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

Profile 有失败时 `status=FAIL` 且 `failed_slot_ids` 与 `blocking_findings[].slot_id` 完全一致；每条 profile finding 含非空 `finding`。Verdict 有失败时每条 merged finding 含 `slot_id`、全部来源 `profile_ids` 和非空 `findings`，且失败 slot 并集必须精确匹配。

`BOUNDED_RATIO_EXPORT`: 导出文件必须是目标精确像素。生图工具按固定像素预算出图，非正方形目标的原图比例会有零点几的偏差（例如 4:5 得到 `1122x1402`，`1464x600` 得到 `1959x803`）。原图宽高比与目标相差不超过 1% 时直接缩放到目标像素，并在 `dimension_corrections` 记录；同比例原图直接缩放。超过 1%、需裁切/补边/拼接/合成或有可见失真时回到 image2。

## 返工

- 只把 QC 指定的 failed slot id 放回 thin-worker queue。
- 新一轮使用唯一 attempt/task id，避免与原 task/slot 登记冲突。
- 返工后重跑 preflight 和受影响的 QC profile；passing slot 不重做。
- 同一问题最多自动两轮，然后回用户门禁。

## 完成

只有主控能确认 receipts/ledger/registry、合并 QC、执行 deterministic export、验证 bounded-ratio export 并写 `production_manifest.json`。任何 worker 都不得宣布整套完成。
