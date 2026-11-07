# 史莱姆亚马逊设计skill 1.0

面向 Codex 的 Amazon 主图与 A+ 完整设计工作流：从真实产品资料、竞品展示分析、参考选择和风格小样，推进到正式出图、质量检查与导出。

**完整安装包：1.0.2 · 核心工作流：1.0.0**

[下载完整安装包](https://github.com/knight9629/slime-amazon-design-skill/releases/download/v1.0.2/slime-amazon-design-skill-v1.0.2.zip) · [查看发布说明](https://github.com/knight9629/slime-amazon-design-skill/releases/tag/v1.0.2) · [中文安装与使用教程](https://rcnbcea2lthm.feishu.cn/docx/UEiYdpB3CouT5Uxj36dcT5R4nvf)

## 1.0.2 修复了什么

- **正式出图可以导出了**：生图工具按固定像素出图，4:5 主图、Premium A+ 电脑端等比例总会差零点几个百分点，旧版会一直判定返工。现在原图比例与目标相差不超过 1% 时直接缩放成精确尺寸并记录，超过 1% 才返工。预检、导出和状态机使用同一规则。
- **状态机不再"看不见"已生成的图**：初始化会为本次运行建立 `输出/<运行名>` 文件夹并加入扫描范围；白底参考图、风格小样和正式出图都放在里面。放错位置时会提示登记文件夹，而不是让 AI 重新生成。
- **实拍图识别更准**：只看项目内部的文件夹名，竞品截图、案例图和输出图不会再被当成实拍图；`实物图`、`IMG_xxxx`、`DSCxxxx` 能被识别；iPhone 的 `.HEIC` 会提示先转成 JPG。
- **Mac 上安装不再误报**：Finder 生成的 `.DS_Store` 等系统文件不会再让校验失败，也不会被装进技能目录。
- **Basic A+ 尺寸更正**：改为 `970x600`（Standard Image Header With Text），最多 5 张（Basic A+ 模块上限）。
- 文档补充 macOS 命令，去掉投影仪专属的固定图位，修正竞品分析模板表格。

1.0.1 起完整包包含 **2 个核心 Skill + 4 个辅助 Skill**，以及各自的脚本、模板、规则和 agent 配置。四个辅助模块保留各自的版本标识，并遵循 1.0 的编排约定；安装不会改写已有商品项目。

| 已包含的 Skill | 负责什么 |
| --- | --- |
| `amazon-ai-design-workflow-orchestrator` | 主入口，统筹资料、参考选择、风格确认、正式生产与验收 |
| `amazon-image-production-runner` | 承接已确认的事实、风格和计划，执行正式出图、QC 与导出 |
| `product-reference-composer` | 根据真实照片制作白底产品参考图、联系表和结构细节记录 |
| `amazon-competitor-creative-research` | 分析竞品主图、副图和 A+ 的卖点、展示顺序与视觉证据 |
| `amazon-product-selling-point-brief` | 整理真实产品参数、卖点优先级、页面内容安排与待确认事项 |
| `amazon-creative-style-sampler` | 推荐 A/B/C 风格，并按主流程需要协助生成可比较的小样 |

四个辅助目录全部安装，由主流程根据阶段调用。已有当前产品的合格材料可从适用阶段接续；产品参考图模块在 `MINIMAL_LIBRARY` 路线中调用。其他路线的功能仍由主流程执行。

## 安装前准备

- 可读取本地文件、浏览参考、查看图片并调用生图工具的 Codex 环境。
- Python 3.10 或更高版本；图像辅助脚本需要 Pillow。依赖列表见 `requirements.txt`。
- 正式生图需要当前环境支持真实图片引用和相应模型使用权限/额度。安装 Skill 文件不会自动开通这些工具。
- 真实商品照片、规格/说明书、品牌与站点信息，以及可用的竞品链接或图片。

包内不包含模型、额度、第三方账号/凭据，也不包含作者的真实商品资料与历史项目。竞品图片可由用户提供；联网收集时需要可用的浏览工具。静态安装检查无法验证账号的实际生图权限。

## 推荐安装方式：交给 Codex

下载上面的 ZIP 并解压，在 Codex 中打开解压后的文件夹，复制：

```text
请安装这个“史莱姆亚马逊设计skill 1.0”完整包。
先阅读 README，使用 Python 3.10+ 运行 verify_package.py 和 install.py --check。
检查 skills 下的全部 6 个 Skill 及它们的脚本、模板和规则，不要只安装两个核心。
缺少 Pillow 时，优先使用已有可用 Python，或在解压目录的独立虚拟环境中
按 requirements.txt 安装依赖。安装时使用同一个 Python。
如果技能目录已有同名项目，使用 install.py --backup 保留旧版本后再安装。
最后回读 6 个入口，分别报告文件安装结果、运行依赖和浏览/生图工具是否可用。
```

安装器默认位置为 `$CODEX_HOME/skills`；未设置时使用用户目录下的 `.codex/skills`。可以用 `--dest` 指定当前 Codex 环境实际使用的技能目录。安装器不修改真实商品项目；已安装同名项时默认拒绝覆盖，`--backup` 会先把旧项移到技能目录外的独立备份文件夹。

完成后重新打开任务，使新安装的 Skill 列表加载。

## 手动安装与检查

在解压后的根目录运行。macOS / Linux 使用 `python3`，Windows 可用 `py -3` 替换；如果当前 Python 版本低于 3.10，先选择较新版本。macOS 自带的 `python3` 通常是 3.9：`verify_package.py` 可以直接运行，`install.py --check` 会提示环境未就绪，正式使用请改用 python.org 或 Homebrew 安装的 3.10+。

```bash
python3 verify_package.py
python3 install.py --check
python3 install.py
```

存在旧版本时，最后一条改为：

```bash
python3 install.py --backup
```

`verify_package.py` 检查六个 Skill 与清单哈希；Finder 的 `.DS_Store`、`._*` 和 Python 缓存会被忽略，也不会被安装。`--check` 不写安装目录，并分别报告文件完整性与 Python/Pillow 情况。运行依赖缺失时，安装文件成功也不代表运行环境已就绪。

如需隔离安装 Python 依赖，可在解压目录创建虚拟环境（macOS / Linux）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python install.py --check
.venv/bin/python install.py
```

Windows 对应命令为：

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe install.py --check
.venv\Scripts\python.exe install.py
```

后续运行图片处理脚本时也使用这个已装依赖的 Python。解压目录中的 `.venv` 是本地运行环境，无需复制进 Skill 目录。使用代码仓库也可以安装：

```bash
git clone --branch v1.0.2 --depth 1 https://github.com/knight9629/slime-amazon-design-skill.git
```

## 开始使用

普通用户只需调用主入口，无需逐个手动运行辅助 Skill：

```text
使用史莱姆亚马逊设计skill 1.0，基于这个文件夹里的真实产品资料，
为美国站制作主图和 A+。先检查运行环境与素材、确认产品事实和制作范围，
再按流程让我选择参考和 A/B/C 风格，确认后继续正式生产。
```

也可以使用固定英文入口：

```text
使用 $amazon-ai-design-workflow-orchestrator，
只做这个产品的 A+。请先检查素材，明确 Basic 或 Premium、语言和电脑/手机端范围。
```

流程会先整理参考图与产品事实，完成竞品与卖点分析，再推荐风格、制作小样并等待选择。确认后在同一个任务中继续正式生产。图片数量、A+ 类型、语言、端别与轮播模块以本次任务确认为准。

最终导出文件是目标精确尺寸：原图比例与目标相差不超过 1% 时直接缩放并记录在清单的 `dimension_corrections`，超过 1% 回到生图返工，不裁切、不补边。内容通过不代表尺寸、文件和人工视觉验收都已通过。

## 验证与文件清单

- `MANIFEST.json` 列出完整包版本、工作流版本、六个模块与每个分发文件的 SHA-256。
- Release 的 `SHA256SUMS.txt` 用于校验 ZIP 下载文件。
- 安装验证包括空目标目录、已有版本备份、文件损坏/缺失拒绝以及安装后的文件回读。
- 源码回归检查覆盖核心工作流合同、评分器兼容、后处理和 stable/beta 规则。
- 安装与脚本检查通过，不等于已在每个平台登录并完成真实商品的整套生图；运行工具与最终作品仍需按本次任务检查。

本仓库供公开查看和下载；当前尚未指定开源许可证。
