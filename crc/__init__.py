"""中文合同审查清单引擎。

把「合同审查该看什么」这件事拆成可加载的规则与可复用的代码：
  - data/dimensions.yaml  三观四步审查框架
  - data/laws.yaml        经核验的法条库（引用白名单）
  - data/contracts/*.yaml 各合同类型的审查项与条款标准

对外 API：
  list_contracts() / load_contract(name) / compose(name) / validate_all()
  audit(type, text) / render_checklist(composed) / render_audit(result)
  load_laws() / look_up(key) / verify_references(keys)
"""

from __future__ import annotations

from .audit import audit, format_audit
from .checklist import (
    DIMENSION_ORDER,
    RISK_ORDER,
    compose,
    list_contracts,
    load_contract,
    load_dimensions,
    risk_labels,
    validate_all,
)
from .laws import format_law, load_laws, look_up, meta, verify_references
from .report import render_audit, render_checklist

__version__ = "0.1.0"

__all__ = [
    "DIMENSION_ORDER",
    "RISK_ORDER",
    "audit",
    "compose",
    "format_audit",
    "format_law",
    "list_contracts",
    "load_contract",
    "load_dimensions",
    "load_laws",
    "look_up",
    "meta",
    "render_audit",
    "render_checklist",
    "risk_labels",
    "validate_all",
    "verify_references",
    "__version__",
]
