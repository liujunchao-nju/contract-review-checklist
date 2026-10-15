# 贡献指南

欢迎提交 Issue 与 Pull Request。这个仓库的价值在于「每一处法条都是查过的」，因此贡献的门槛主要在数据准确性上，不在代码风格上。

## 三条硬规则

1. **不得凭记忆写法条。** 任何新增或修改的 `basis`，都必须先按「法规名称 + 条号」调取原文，确认条号与内容对应、且为现行有效，再写入 `crc/data/laws.yaml`。`crc verify` 与单元测试会拦截未入库的引用。
2. **不得把市场惯例写成法律底线。** `benchmarks.yaml` 只收参照区间与法律硬性上限；法律上限须标注 `legal_limit: true`，并在 `note` 中写明超出后的法律后果。
3. **不得提供脱离交易背景的结论。** 清单项与建议文本应保持「提示风险 + 给出可调整的文本」，不替使用者做商业决策。

## 新增一个合同类型

在 `crc/data/contracts/` 下加一个 YAML 文件即可，不需要改代码。文件至少包含：

```yaml
type: 类型标识          # 小写英文，用于 --type
label: 中文名称
category: 分类
summary: 一句话说明交易实质

legal_basis:            # 主要法条 key，必须已在 laws.yaml 中
  - 民法典第595条

checks:                 # 三个层次都必须非空
  macro:
    - id: 唯一标识
      question: 一句话问句
      risk: fatal|major|minor|note
      guidance: 为什么要看这一项
      basis: [法条 key]
  meso: [...]
  micro: [...]

clauses:                # 条款标准
  - name: 条款名称
    required: true
    keywords: [用于速检匹配的表述]
    elements: [必备要素]
    issues: [常见问题]
    basis: [法条 key]

red_flags:              # 可选
  - id: 唯一标识
    name: 信号名称
    patterns: [信号词]
    risk: 风险等级
    message: 说明
```

`checks` 中的每一项还可带：

- `party_notes`：按甲方、乙方的立场分别给出提示；
- `risk_by_party`：按立场给出不同的风险等级；
- `aliases`：条款标准可带同义词，用于提高速检命中率。

写完先跑：

```bash
python -m crc verify
python -m pytest -q
```

## 修改法条库

1. 按「法规名称 + 条号」调取原文，确认现行有效；
2. 在 `crc/data/laws.yaml` 的对应分组下新增一条，字段齐全（`key` / `law` / `article` / `title` / `text` / `effective_from` / `authority`）；
3. 更新文件头部的 `verified_on`；
4. 如涉及条号与内容的对应关系，在 `tests/test_laws.py` 的 `test_key_article_correspondence` 中补一条抽查。

## 本地验证

```bash
pip install -e ".[dev]"
python -m pytest -q
python -m crc verify
```

提交前请确认测试全绿。CI 会在 Python 3.9 / 3.11 / 3.13 三个版本上跑同样的命令，并额外校验 HTML 产物不含外部资源引用。

## 提交信息

用中文，一行说明改动，例如：

- `新增保密协议与保证合同两类清单`
- `修正民法典第686条条号与原文的对应关系`
- `audit 支持按立场调整风险等级`

## 不接受的改动

- 凭记忆添加或改动的法条引用；
- 把模型输出直接写进数据文件而未经核验；
- 引入外部模型或 API Key 依赖（本项目保持零依赖、可离线运行）；
- 引入 CDN 或外部资源的 HTML 产物。
