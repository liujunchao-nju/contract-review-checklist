# 更新日志

本项目的版本号遵循语义化版本：数据文件结构变化或命令行为变化为次版本，新增合同类型与数据为修订或次版本，法条库更新为修订版本。

## v0.2.0

本次更新的主题是**降低使用门槛**与**让审查结论依附立场**。

### 新增

- **Agent Skill 形态**：顶层 `SKILL.md`，`npx skills add https://github.com/liujunchao-nju/contract-review-checklist` 一行装上，可在 Claude Code、Codex、Cursor 等工具中直接使用。Python 包形态保留，两种形态共用同一套数据。
- **HTML 产物**：`crc checklist --format html` 生成单文件可勾选清单，带核对进度条；`crc audit --format html` 生成单文件审查报告，带指标卡、三级证据表格与基准比对表。两者内联 CSS 与 JS，不引用外部资源，可离线打开。CI 增加一步校验产物不含外部引用。
- **三级证据与位置证据**（`crc/evidence.py`）：条款匹配从「关键词在不在」升级为标题命中 / 正文命中 / 缺失三态，并给出命中行号、命中词与原文摘录，便于人工复核。条款可带 `aliases` 同义词。
- **立场维度**：`--party 甲方|乙方`。审查项支持 `party_notes`（按立场的提示）与 `risk_by_party`（按立场的风险等级），同一条款在不同立场下可以给出不同的严重性判断。
- **市场基准区间**：新增 `crc/data/benchmarks.yaml` 与 `crc bench` 命令，收录 9 项量化条款的参照区间（违约金比例、质量保证期、检验与验收期、付款账期、自动续约提前通知期、竞业限制期限、保密期限、租赁期限、借款年利率），支持中文数字与阿拉伯数字两种写法。`crc audit` 默认一并扫描并在报告中列出偏离项。
- **条款建议文本**：条款标准新增 `redline` 字段，给出可直接取用的替代文本（含变量占位），在清单与报告的缺失条款处一并输出。
- **新增 6 类合同**：保密协议 `nda`、保证合同 `guarantee`、委托合同 `entrust`、承揽合同 `work`、增资扩股协议 `capital_increase`、物业服务合同 `property`，合同类型由 9 类增至 15 类。
- **法条库扩充**：52 条增至 63 条，新增民法典第 501、681、686、692、772、787、919、933、937、938 条与公司法第 227 条，均为按「法规名称 + 条号」调取原文并确认现行有效后写入。
- `crc bench` 命令：查看基准区间总表或某一项的完整阈值与依据。
- `CHANGELOG.md` 与 `CONTRIBUTING.md`。

### 变更

- `compose()` 与 `audit()` 新增 `party` 参数；`audit()` 新增 `benchmarks` 开关。
- `audit()` 返回值新增 `details`（逐条证据）、`benchmarks`、`blocking`、`party`，保留 `covered` / `missing_required` / `missing_optional` / `coverage` / `clean` 的原有语义。
- `crc audit` 的 `--format` 支持 `text|json|md|html`，`--json` 保留为 `--format json` 的简写。
- `crc verify` 现在同时校验基准库的结构与法条引用。
- 条款标准表改为分条排版，新增必备要素勾选与建议文本。

### 说明

基准区间是市场惯例与法律硬性上限的参照值，与法条库性质不同：法条库是法律规定，引用错误是硬错误；基准库用于发现明显偏离，不得作为裁判标准或谈判依据写进对外文件。

## v0.1.0

首个版本。三观四步分层框架、9 类合同的审查项与条款标准、`crc` 六条命令、52 条经核验的法条库，以及把「引用法条」从凭记忆变成查白名单的校验机制。
