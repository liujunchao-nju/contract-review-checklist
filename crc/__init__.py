"""中文合同审查清单引擎。

把「合同审查该看什么」这件事拆成可加载的规则与可复用的代码：
  - data/dimensions.yaml   三观四步审查框架
  - data/laws.yaml         经核验的法条库（引用白名单）
  - data/benchmarks.yaml   市场惯例区间与法律上限的参照值
  - data/contracts/*.yaml  各合同类型的审查项与条款标准

对外 API：
  list_contracts() / load_contract(name) / compose(name[, party]) / validate_all()
  audit(type, text[, party]) / render_checklist(composed) / render_checklist_html(composed)
  render_audit(result) / render_audit_html(result)
  load_benchmarks() / evaluate(text) / load_laws() / look_up(key) / verify_references(keys)
"""

from __future__ import annotations

from .audit import audit, format_audit
from .bench import evaluate, load_benchmarks, validate_benchmarks
from .checklist import (
    DIMENSION_ORDER,
    PARTIES,
    RISK_ORDER,
    compose,
    list_contracts,
    load_contract,
    load_dimensions,
    risk_labels,
    validate_all,
)
from .evidence import STATUS_BODY, STATUS_HEADING, STATUS_MISSING
from .laws import format_law, load_laws, look_up, meta, verify_references
from .report import (
    FORMATS,
    render_audit,
    render_audit_html,
    render_checklist,
    render_checklist_html,
)

__version__ = "0.2.0"

__all__ = [
    "DIMENSION_ORDER",
    "FORMATS",
    "PARTIES",
    "RISK_ORDER",
    "STATUS_BODY",
    "STATUS_HEADING",
    "STATUS_MISSING",
    "audit",
    "compose",
    "evaluate",
    "format_audit",
    "format_law",
    "list_contracts",
    "load_benchmarks",
    "load_contract",
    "load_dimensions",
    "load_laws",
    "look_up",
    "meta",
    "render_audit",
    "render_audit_html",
    "render_checklist",
    "render_checklist_html",
    "risk_labels",
    "validate_all",
    "validate_benchmarks",
    "verify_references",
    "__version__",
]
