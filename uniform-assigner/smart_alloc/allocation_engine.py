# -*- coding: utf-8 -*-
"""自动分配求解器 —— Google OR-Tools CP-SAT 全局优化。

硬约束：每人恰好 1 礼服 + 1 马靴；每件装备 ≤2 人；同班不得共用；
不可穿/非 available 不参与；已锁定分配保持不变；礼服性别匹配。
软目标：尺码匹配成本 + 共用惩罚 + 老队员换装惩罚 + 班级风险 + 预测尺码惩罚。

无可行方案时返回 shortage 诊断，绝不强行凑解。
"""
import time
from itertools import combinations

from . import schemas, size_matcher


def _class_of(member):
    c = member.get("duty_class")
    return str(c).strip() if c not in (None, "") else None


def solve(members, equipment, fit_records, locked, cfg):
    """locked: dict member_id -> {"uniform_id":..., "boot_id":...}（已锁定分配）。"""
    t0 = time.time()
    weights = cfg["weights"]

    active = [m for m in members
              if m.get("active_in_hq") and m.get("member_status") != "leaving"]

    uniforms = [e for e in equipment if e["category"] == "uniform" and e["status"] == "available"]
    boots = [e for e in equipment if e["category"] == "boots" and e["status"] == "available"]
    all_uniform_ids = [e["equipment_id"] for e in uniforms]
    all_boot_ids = [e["equipment_id"] for e in boots]
    uniform_ids_by_size = {}
    for e in uniforms:
        uniform_ids_by_size.setdefault(e["size_code"], []).append(e["equipment_id"])
    boot_ids_by_size = {}
    for e in boots:
        boot_ids_by_size.setdefault(e["size_code"], []).append(e["equipment_id"])

    # ── 候选集 ──
    cands = {}
    for m in active:
        u = size_matcher.uniform_candidates(m, uniforms, fit_records, cfg)
        b = size_matcher.boot_candidates(m, boots, fit_records, cfg)
        cands[m["member_id"]] = {"uniform": u, "boots": b}

    # 锁定成员：候选强制为锁定项
    for mid, lk in (locked or {}).items():
        if mid not in cands:
            continue
        uid = lk.get("uniform_id")
        bid = lk.get("boot_id")
        if uid and uid in all_uniform_ids:
            cands[mid]["uniform"] = [{"size_code": schemas.uniform_size_of(uid),
                                      "score": 0, "source": "锁定", "reason": "已锁定", "_id": uid}]
        if bid and bid in all_boot_ids:
            cands[mid]["boots"] = [{"size_code": schemas.parse_boot_size(bid),
                                    "score": 0, "source": "锁定", "reason": "已锁定", "_id": bid}]

    # 预检：无候选队员 → 直接诊断
    empty_u = [m for m in active if not cands[m["member_id"]]["uniform"]]
    empty_b = [m for m in active if not cands[m["member_id"]]["boots"]]
    if empty_u or empty_b:
        return {
            "status": "INFEASIBLE",
            "duration_ms": int((time.time() - t0) * 1000),
            "objective": None,
            "allocations": [], "shared": [],
            "shortage": shortage_diagnosis(active, uniforms, boots, cands, cfg),
            "message": f"有队员缺少候选尺码：礼服 {len(empty_u)} 人、马靴 {len(empty_b)} 人。请补齐身体数据或试穿记录。",
        }

    # 展开候选为 (equipment_id, score, source)
    u_cands = {}
    b_cands = {}
    for m in active:
        ul, bl = [], []
        for c in cands[m["member_id"]]["uniform"]:
            if "_id" in c:
                ul.append((c["_id"], c["score"], c["source"]))
            else:
                for uid in uniform_ids_by_size.get(c["size_code"], []):
                    ul.append((uid, c["score"], c["source"]))
        for c in cands[m["member_id"]]["boots"]:
            if "_id" in c:
                bl.append((c["_id"], c["score"], c["source"]))
            else:
                for bid in boot_ids_by_size.get(c["size_code"], []):
                    bl.append((bid, c["score"], c["source"]))
        u_cands[m["member_id"]] = ul
        b_cands[m["member_id"]] = bl

    # ── 建模型 ──
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return {"status": "ERROR", "shortage": [], "allocations": [], "shared": [],
                "message": "缺少 ortools 依赖，请在 requirements.txt 加入 ortools 后重新部署。"}

    model = cp_model.CpModel()
    x, y = {}, {}
    for m in active:
        for (eid, _sc, _src) in u_cands[m["member_id"]]:
            x[(m["member_id"], eid)] = model.NewBoolVar(f"x_{m['member_id']}_{eid}")
        for (eid, _sc, _src) in b_cands[m["member_id"]]:
            y[(m["member_id"], eid)] = model.NewBoolVar(f"y_{m['member_id']}_{eid}")

    # 硬约束：每人恰好一件
    for m in active:
        model.Add(sum(x[(m["member_id"], eid)] for (eid, _, _) in u_cands[m["member_id"]]) == 1)
        model.Add(sum(y[(m["member_id"], eid)] for (eid, _, _) in b_cands[m["member_id"]]) == 1)

    # 硬约束：每件装备 ≤2 人
    for eid in all_uniform_ids:
        terms = [x[(m["member_id"], eid)] for m in active if (m["member_id"], eid) in x]
        if terms:
            model.Add(sum(terms) <= 2)
    for eid in all_boot_ids:
        terms = [y[(m["member_id"], eid)] for m in active if (m["member_id"], eid) in y]
        if terms:
            model.Add(sum(terms) <= 2)

    # 硬约束：同班不得共用
    by_class = {}
    for m in active:
        c = _class_of(m)
        if c is not None:
            by_class.setdefault(c, []).append(m["member_id"])

    for eid in all_uniform_ids:
        for c, mids in by_class.items():
            terms = [x[(mid, eid)] for mid in mids if (mid, eid) in x]
            if len(terms) > 1:
                model.Add(sum(terms) <= 1)
    for eid in all_boot_ids:
        for c, mids in by_class.items():
            terms = [y[(mid, eid)] for mid in mids if (mid, eid) in y]
            if len(terms) > 1:
                model.Add(sum(terms) <= 1)

    # ── 软目标 ──
    cost = []

    # 尺码匹配成本
    for m in active:
        for (eid, sc, _src) in u_cands[m["member_id"]]:
            cost.append(int(sc) * x[(m["member_id"], eid)])
        for (eid, sc, _src) in b_cands[m["member_id"]]:
            cost.append(int(sc) * y[(m["member_id"], eid)])

    # 老队员换装惩罚
    for m in active:
        if m.get("request_resize") or m.get("member_status") != "returning":
            continue
        prev_u = m.get("previous_uniform_id")
        prev_b = m.get("previous_boot_id")
        if prev_u and (m["member_id"], prev_u) in x:
            cost.append(int(weights["old_change"]) * (1 - x[(m["member_id"], prev_u)]))
        if prev_b and (m["member_id"], prev_b) in y:
            cost.append(int(weights["old_change"]) * (1 - y[(m["member_id"], prev_b)]))

    # 预测尺码惩罚
    for m in active:
        for (eid, _sc, src) in u_cands[m["member_id"]]:
            if src in ("规则预测", "相邻兜底"):
                cost.append(int(weights["predicted"]) * x[(m["member_id"], eid)])
        for (eid, _sc, src) in b_cands[m["member_id"]]:
            if src in ("规则预测", "相邻兜底"):
                cost.append(int(weights["predicted"]) * y[(m["member_id"], eid)])

    # 共用惩罚（每件装备被 2 人使用 → 计数）
    share_u, share_b = {}, {}
    for eid in all_uniform_ids:
        terms = [x[(m["member_id"], eid)] for m in active if (m["member_id"], eid) in x]
        if not terms:
            continue
        s = model.NewBoolVar(f"su_{eid}")
        model.Add(sum(terms) - 1 <= s)
        model.Add(2 * s <= sum(terms))
        share_u[eid] = s
        cost.append(int(weights["sharing"]) * s)
    for eid in all_boot_ids:
        terms = [y[(m["member_id"], eid)] for m in active if (m["member_id"], eid) in y]
        if not terms:
            continue
        s = model.NewBoolVar(f"sb_{eid}")
        model.Add(sum(terms) - 1 <= s)
        model.Add(2 * s <= sum(terms))
        share_b[eid] = s
        cost.append(int(weights["sharing"]) * s)

    # 班级风险惩罚（不同班共用的具体班对）
    class_risk = weights.get("class_risk", {"high": 80, "mid": 30, "low": 5})
    class_matrix = cfg.get("class_matrix", {})
    for c1, c2 in combinations(sorted(by_class.keys()), 2):
        level = class_matrix.get((c1, c2)) or class_matrix.get((c2, c1))
        if level is None:
            continue
        risk = int(class_risk.get(level, 0))
        if not risk:
            continue
        for eid in all_uniform_ids:
            t1 = [x[(mid, eid)] for mid in by_class[c1] if (mid, eid) in x]
            t2 = [x[(mid, eid)] for mid in by_class[c2] if (mid, eid) in x]
            if not t1 or not t2:
                continue
            a, b = sum(t1), sum(t2)
            p = model.NewBoolVar(f"pu_{c1}_{c2}_{eid}")
            model.Add(p <= a)
            model.Add(p <= b)
            model.Add(p >= a + b - 1)
            cost.append(risk * p)
        for eid in all_boot_ids:
            t1 = [y[(mid, eid)] for mid in by_class[c1] if (mid, eid) in y]
            t2 = [y[(mid, eid)] for mid in by_class[c2] if (mid, eid) in y]
            if not t1 or not t2:
                continue
            a, b = sum(t1), sum(t2)
            p = model.NewBoolVar(f"pb_{c1}_{c2}_{eid}")
            model.Add(p <= a)
            model.Add(p <= b)
            model.Add(p >= a + b - 1)
            cost.append(risk * p)

    model.Minimize(sum(cost))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)
    duration_ms = int((time.time() - t0) * 1000)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "INFEASIBLE",
            "duration_ms": duration_ms,
            "objective": None,
            "allocations": [], "shared": [],
            "shortage": shortage_diagnosis(active, uniforms, boots, cands, cfg),
            "message": "无法满足全部硬约束（无可行方案）。详见缺口诊断。",
        }

    # ── 组装结果 ──
    assignments = {}
    for m in active:
        uid = next((eid for (eid, _, _) in u_cands[m["member_id"]]
                    if solver.Value(x[(m["member_id"], eid)]) == 1), None)
        bid = next((eid for (eid, _, _) in b_cands[m["member_id"]]
                    if solver.Value(y[(m["member_id"], eid)]) == 1), None)
        src = next((s for (eid, _, s) in u_cands[m["member_id"]] if eid == uid), "auto")
        assignments[m["member_id"]] = {
            "member_id": m["member_id"], "name": m["name"],
            "uniform_id": uid, "boot_id": bid,
            "uniform_size": schemas.uniform_size_of(uid) if uid else "",
            "boot_size": schemas.parse_boot_size(bid) if bid else "",
            "source": "previous" if src == "锁定" else "auto",
            "locked": bool(m["member_id"] in (locked or {})),
            "fit_explanation": _explain(m, uid, bid, u_cands, b_cands),
        }

    return {
        "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
        "duration_ms": duration_ms,
        "objective": int(solver.ObjectiveValue()) if status == cp_model.OPTIMAL else None,
        "allocations": list(assignments.values()),
        "shared": _compute_shared(assignments),
        "shortage": [],
        "message": "求解成功。",
    }


def _explain(member, uid, bid, u_cands, b_cands):
    parts = []
    if uid:
        srcu = next((s for (e, _, s) in u_cands[member["member_id"]] if e == uid), "")
        parts.append(f"礼服 {schemas.uniform_size_of(uid)}（{srcu}）")
    if bid:
        srcb = next((s for (e, _, s) in b_cands[member["member_id"]] if e == bid), "")
        parts.append(f"马靴 {schemas.parse_boot_size(bid)}码（{srcb}）")
    return "；".join(parts)


def _compute_shared(assignments):
    from collections import defaultdict
    u_map = defaultdict(list)
    b_map = defaultdict(list)
    for a in assignments.values():
        if a["uniform_id"]:
            u_map[a["uniform_id"]].append(a["name"])
        if a["boot_id"]:
            b_map[a["boot_id"]].append(a["name"])
    shared = []
    for uid, names in u_map.items():
        if len(names) >= 2:
            shared.append({"equipment_id": uid, "category": "uniform", "members": sorted(names)})
    for bid, names in b_map.items():
        if len(names) >= 2:
            shared.append({"equipment_id": bid, "category": "boots", "members": sorted(names)})
    return shared


def shortage_diagnosis(active, uniforms, boots, cands, cfg):
    """无解诊断：逐尺码列出可用量、覆盖上限、单候选需求、受影响人、替代建议、缺口。"""
    shortage = []

    for category, eq_list in (("uniform", uniforms), ("boots", boots)):
        size_ids = {}
        for e in eq_list:
            size_ids.setdefault(e["size_code"], []).append(e["equipment_id"])

        single = {}
        for m in active:
            c = cands[m["member_id"]]["uniform" if category == "uniform" else "boots"]
            if any("_id" in x for x in c):
                continue  # 锁定成员不参与无解诊断
            sizes = [x["size_code"] for x in c]
            if len(set(sizes)) == 1 and sizes:
                single.setdefault(sizes[0], []).append(m)

        for size, ids in size_ids.items():
            max_cover = len(ids) * 2
            demand = len(single.get(size, []))
            if demand > max_cover:
                gap_people = demand - max_cover
                affected = single[size]
                shortage.append({
                    "category": category,
                    "size_code": size,
                    "available": len(ids),
                    "max_cover": max_cover,
                    "demand": demand,
                    "affected": [m["name"] for m in affected],
                    "suggestions": _suggest_alternatives(affected, size, size_ids, category),
                    "gap": gap_people,
                    "add_items": (gap_people + 1) // 2,
                })

    return shortage


def _suggest_alternatives(members, size_code, size_ids, category):
    out = []
    key = schemas.parse_uniform_size if category == "uniform" else int
    try:
        ordered = sorted(size_ids.keys(), key=key)
        idx = ordered.index(size_code)
    except (ValueError, TypeError):
        return out
    neighbors = []
    for d in (1, 2):
        if idx - d >= 0:
            neighbors.append(ordered[idx - d])
        if idx + d < len(ordered):
            neighbors.append(ordered[idx + d])
    for m in members[:5]:
        out.append({"name": m["name"], "suggest": neighbors[0] if neighbors else None})
    return out
