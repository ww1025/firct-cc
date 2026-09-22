# -*- coding: utf-8 -*-
"""独立冲突复核器 —— 不依赖求解器，二次校验分配结果。

检查：三人共用、同班共用、无装备、不可穿分配、损坏装备被使用。
"""
from collections import defaultdict


def check(allocations, members, equipment, fit_records):
    """返回 (violations, summary)。

    summary = {"三人共用": n, "同班共用": n, "无装备": n, "不可穿分配": n, "损坏装备": n}
    全部为 0 才允许标记“最终版”。
    """
    member_by_id = {m["member_id"]: m for m in members}
    eq_by_id = {e["equipment_id"]: e for e in equipment}
    # 不可穿尺码：(member_id, category, size_code) 集合
    forbidden = set()
    for f in fit_records:
        if f.get("fit_level") == "no" and f.get("verified"):
            forbidden.add((f["member_id"], f["category"], f["size_code"]))

    violations = []

    # 1) 装备使用人数（检测三人及以上共用）
    u_use = defaultdict(list)
    b_use = defaultdict(list)
    for a in allocations:
        if a.get("uniform_id"):
            u_use[a["uniform_id"]].append(a)
        if a.get("boot_id"):
            b_use[a["boot_id"]].append(a)

    for eid, asg in u_use.items():
        if len(asg) >= 3:
            violations.append({"type": "三人共用", "detail": f"礼服 {eid} 被 {len(asg)} 人使用"})
    for eid, asg in b_use.items():
        if len(asg) >= 3:
            violations.append({"type": "三人共用", "detail": f"马靴 {eid} 被 {len(asg)} 人使用"})

    # 2) 同班共用（含二人共用中的同班）
    for eid, asg in list(u_use.items()) + list(b_use.items()):
        seen_class = {}
        for a in asg:
            m = member_by_id.get(a["member_id"], {})
            c = (m.get("duty_class") or "").strip()
            if c and c in seen_class:
                violations.append({"type": "同班共用", "detail": f"{eid} 被同班 {seen_class[c]} 与 {m.get('name')} 共用"})
            elif c:
                seen_class[c] = m.get("name")

    # 3) 无装备（有效队员缺少礼服或马靴）
    for m in members:
        if not (m.get("active_in_hq") and m.get("member_status") != "leaving"):
            continue
        a = next((x for x in allocations if x["member_id"] == m["member_id"]), None)
        if not a or not a.get("uniform_id") or not a.get("boot_id"):
            violations.append({"type": "无装备", "detail": f"{m.get('name')} 缺少礼服或马靴"})

    # 4) 不可穿分配
    for a in allocations:
        mid = a["member_id"]
        if a.get("uniform_id"):
            e = eq_by_id.get(a["uniform_id"], {})
            if (mid, "uniform", e.get("size_code")) in forbidden:
                violations.append({"type": "不可穿分配", "detail": f"{member_by_id.get(mid, {}).get('name')} 被分配不可穿礼服尺码"})
        if a.get("boot_id"):
            e = eq_by_id.get(a["boot_id"], {})
            if (mid, "boots", e.get("size_code")) in forbidden:
                violations.append({"type": "不可穿分配", "detail": f"{member_by_id.get(mid, {}).get('name')} 被分配不可穿马靴尺码"})

    # 5) 损坏/维修装备被使用
    for a in allocations:
        for eid in (a.get("uniform_id"), a.get("boot_id")):
            if not eid:
                continue
            e = eq_by_id.get(eid, {})
            if e.get("status") not in ("available", None, ""):
                violations.append({"type": "损坏装备", "detail": f"{eid}（{e.get('status')}）被使用"})

    summary = {"三人共用": 0, "同班共用": 0, "无装备": 0, "不可穿分配": 0, "损坏装备": 0}
    for v in violations:
        if v["type"] in summary:
            summary[v["type"]] += 1

    return violations, summary
