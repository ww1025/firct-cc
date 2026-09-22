# -*- coding: utf-8 -*-
"""数据模型：字段定义、工厂函数、编码解析与轻量校验。

统一用 dict 表示，便于 Excel / JSON 序列化与 st.session_state 存取。
"""
import re
from datetime import datetime

# ── 字段清单 ──
MEMBER_FIELDS = [
    "member_id", "name", "gender", "duty_class", "member_status",
    "active_in_hq", "height_cm", "weight_kg", "head_cm", "chest_cm",
    "waist_cm", "calf_cm", "foot_length_mm",
    "previous_uniform_id", "previous_boot_id", "request_resize", "notes",
]

EQUIPMENT_FIELDS = [
    "equipment_id", "category", "gender", "size_code", "status",
    "location", "paired_belt_id", "legacy_code", "notes",
]

FIT_FIELDS = [
    "fit_id", "member_id", "category", "size_code", "fit_level",
    "fit_score", "detail_note", "verified", "recorded_at",
]

ALLOC_FIELDS = [
    "member_id", "uniform_id", "boot_id", "uniform_shared_with",
    "boot_shared_with", "source", "locked", "fit_explanation", "updated_at",
]

MEMBER_STATUS = ("new", "returning", "leaving")
EQUIP_CATEGORY = ("uniform", "boots")
EQUIP_STATUS = ("available", "repair", "damaged", "borrowed")
FIT_LEVELS = ("best", "wearable", "loose", "tight", "no")


# ── 工厂函数 ──
def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_member(name="", gender="M", **kw):
    m = {f: None for f in MEMBER_FIELDS}
    m.update(name=name, gender=gender, member_status="new", active_in_hq=True,
             request_resize=False, notes="")
    m.update(kw)
    return m


def new_equipment(equipment_id="", category="uniform", **kw):
    e = {f: None for f in EQUIPMENT_FIELDS}
    e.update(equipment_id=equipment_id, category=category, gender="",
             size_code="", status="available", location="", paired_belt_id="",
             legacy_code="", notes="")
    e.update(kw)
    return e


def new_fit_record(member_id="", category="uniform", size_code="", **kw):
    f = {k: None for k in FIT_FIELDS}
    f.update(member_id=member_id, category=category, size_code=size_code,
             fit_level=None, fit_score=None, detail_note="", verified=True,
             recorded_at=_now())
    f.update(kw)
    return f


def new_allocation(member_id="", **kw):
    a = {k: None for k in ALLOC_FIELDS}
    a.update(member_id=member_id, uniform_id=None, boot_id=None,
             uniform_shared_with="", boot_shared_with="", source="auto",
             locked=False, fit_explanation="", updated_at=_now())
    a.update(kw)
    return a


# ── 编码解析 ──
def parse_uniform_code(code):
    """'M185/100-01' -> {'gender':'M','height':185,'chest':100,'serial':'01'}；失败返回 None。"""
    m = re.match(r"^([FM])(\d+)/(\d+)(?:-(\d+))?$", str(code).strip())
    if not m:
        return None
    return {"gender": m.group(1), "height": int(m.group(2)),
            "chest": int(m.group(3)), "serial": m.group(4) or ""}


def uniform_size_of(code):
    """'M185/100-01' -> '185/100'。"""
    p = parse_uniform_code(code)
    return f"{p['height']}/{p['chest']}" if p else str(code)


def parse_uniform_size(size_code):
    """'185/100' -> (185, 100)；无法解析返回 (0, 0)。"""
    m = re.match(r"^(\d+)/(\d+)$", str(size_code).strip())
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def parse_boot_size(code):
    """'N43/43-01' / 'X44-05' / 'J38-01' -> '43' / '44' / '38'（取第一个整数）。"""
    m = re.search(r"(\d+)", str(code))
    return m.group(1) if m else ""


# ── 轻量校验 ──
def to_number(v, default=None):
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def to_int(v, default=None):
    n = to_number(v, default)
    return int(n) if n is not None else default


def to_bool(v, default=False):
    if v is None or v == "":
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "是", "y", "on")
