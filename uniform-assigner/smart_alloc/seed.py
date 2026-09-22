# -*- coding: utf-8 -*-
"""从物资仓库数据（warehouse_data_json）生成装备实体表，并推导上学年分配。"""
import re
from . import schemas


def _record_prev(prev, person_text, key, code):
    """把 person 文本解析成姓名，记录其上学年装备。"""
    if not person_text:
        return
    for name in re.split(r"[、,，/]", str(person_text)):
        name = name.strip()
        if not name or name.startswith("（") or "损坏" in name or "坏" in name:
            continue
        prev.setdefault(name, {})[key] = code


def build_equipment(wh_data):
    """wh_data: dict（json.loads(warehouse_data_json()) 的结果）。

    返回 (equipment_list, prev_assignment)。
    - equipment_list：礼服 + 马靴的实体清单（腰带随礼服，不独立建实体）
    - prev_assignment：{姓名: {"uniform": id, "boots": id}} 上学年分配
    """
    equipment = []
    prev = {}

    # 礼服
    for u in wh_data.get("uniforms", []):
        code = str(u.get("code", ""))
        p = schemas.parse_uniform_code(code)
        e = schemas.new_equipment(
            equipment_id=code,
            category="uniform",
            gender=p["gender"] if p else "",
            size_code=f"{p['height']}/{p['chest']}" if p else code,
            status="available",
            location=str(u.get("cabinet", "")),
            paired_belt_id=str(u.get("belt", "")),
            legacy_code=code,
        )
        equipment.append(e)
        _record_prev(prev, u.get("person", ""), "uniform", code)

    # 马靴
    for row in wh_data.get("grid", []):
        for cell in row:
            if not cell or not cell.get("code"):
                continue
            code = str(cell.get("code", ""))
            person = str(cell.get("person", ""))
            status = "damaged" if ("损坏" in person or "坏" in person) else "available"
            e = schemas.new_equipment(
                equipment_id=code,
                category="boots",
                gender="",
                size_code=schemas.parse_boot_size(code),
                status=status,
                location="",
                legacy_code=code,
                notes="" if status == "available" else "鞋面损坏",
            )
            equipment.append(e)
            _record_prev(prev, person, "boots", code)

    return equipment, prev
