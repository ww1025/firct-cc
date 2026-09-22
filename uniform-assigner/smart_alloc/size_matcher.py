# -*- coding: utf-8 -*-
"""候选尺码生成与评分。

优先级：实际试穿确认 > 上学年沿用 > 可配置尺码规则 > 相邻尺码兜底。
不可穿（fit_level='no'）尺码从候选中剔除；规则预测/兜底标注为“仅预测”。
"""
from . import schemas


# ── 内部工具 ──
def _eligible_sizes(equipment, category, gender):
    """返回 (category, gender) 下、状态 available 的尺码集合。"""
    sizes = set()
    for e in equipment:
        if e["category"] != category or e["status"] != "available":
            continue
        if category == "uniform":
            if e["gender"] and gender and e["gender"] != gender:
                continue
        sizes.add(str(e["size_code"]))
    return sizes


def _fit_for(fit_records, member_id, category, size_code):
    """返回该人该码的试穿记录 dict，无则 None。"""
    for f in fit_records:
        if (f["member_id"] == member_id and f["category"] == category
                and f["size_code"] == size_code and f.get("verified")):
            return f
    return None


def _forbidden_sizes(fit_records, member_id, category):
    """该人该类别被标记为「不可穿」的尺码集合（任何来源都不得纳入候选）。"""
    out = set()
    for f in fit_records:
        if (f["member_id"] == member_id and f["category"] == category
                and f.get("fit_level") == "no" and f.get("verified")):
            out.add(str(f["size_code"]))
    return out


def _foot_to_size(foot_table, foot_mm):
    """脚长(mm) -> 推荐鞋码。"""
    best, best_diff = None, None
    for mm, size in foot_table:
        diff = abs(mm - foot_mm)
        if best_diff is None or diff < best_diff:
            best, best_diff = size, diff
    return best


def _uniform_sizes_sorted(sizes):
    return sorted(sizes, key=schemas.parse_uniform_size)


def _boot_sizes_sorted(sizes):
    nums = sorted(int(s) for s in sizes if str(s).isdigit())
    return [str(n) for n in nums]


# ── 候选生成 ──
def uniform_candidates(member, equipment, fit_records, cfg):
    """礼服候选，返回 [{size_code, score, source, reason}]（按分值升序）。"""
    gender = member.get("gender", "")
    sizes = _uniform_sizes_sorted(_eligible_sizes(equipment, "uniform", gender))
    fit_scores = cfg["fit_scores"]
    forbidden = _forbidden_sizes(fit_records, member["member_id"], "uniform")
    cand = {}

    # 1) 实际试穿
    for s in sizes:
        if s in forbidden:
            continue
        f = _fit_for(fit_records, member["member_id"], "uniform", s)
        if f and f["fit_level"] != "no" and f["fit_level"] in fit_scores:
            cand[s] = {"size_code": s, "score": fit_scores[f["fit_level"]],
                       "source": "试穿", "reason": f"试穿记录：{f['fit_level']}"}

    # 2) 上学年沿用
    prev = member.get("previous_uniform_id")
    if prev and not member.get("request_resize"):
        ps = schemas.uniform_size_of(prev)
        if ps in sizes and ps not in cand and ps not in forbidden:
            cand[ps] = {"size_code": ps, "score": 0, "source": "上年沿用",
                        "reason": "上学年合身沿用"}

    # 3) 尺码规则
    height = schemas.to_number(member.get("height_cm"))
    chest = schemas.to_number(member.get("chest_cm"))
    if height is not None and chest is not None:
        u = cfg["uniform"]
        for s in sizes:
            if s in forbidden:
                continue
            sh, sc = schemas.parse_uniform_size(s)
            if sh == 0:
                continue
            if abs(sh - height) <= u["height_tol"] and abs(sc - chest) <= u["chest_tol"]:
                score = cfg["predicted_score"] + abs(sh - height) * 4 + abs(sc - chest) * 5
                if s not in cand:
                    cand[s] = {"size_code": s, "score": score, "source": "规则预测",
                               "reason": f"身高{int(height)}/胸围{int(chest)} 匹配"}
                else:
                    cand[s]["score"] = min(cand[s]["score"], score)

    # 4) 相邻兜底
    u = cfg["uniform"]
    if cand and sizes:
        best_s = min(cand.values(), key=lambda c: c["score"])["size_code"]
        try:
            idx = sizes.index(best_s)
        except ValueError:
            idx = 0
        for d in range(1, u["neighbor_count"] + 1):
            for ni in (idx - d, idx + d):
                if 0 <= ni < len(sizes):
                    ns = sizes[ni]
                    if ns not in cand and ns not in forbidden:
                        sh, sc = schemas.parse_uniform_size(ns)
                        score = cfg["predicted_score"] + 30 + abs(sh - (height or sh)) * 4 + abs(sc - (chest or sc)) * 5
                        cand[ns] = {"size_code": ns, "score": score, "source": "相邻兜底",
                                    "reason": "库存紧缺相邻尺码，需试穿确认"}

    return sorted(cand.values(), key=lambda c: c["score"])


def boot_candidates(member, equipment, fit_records, cfg):
    """马靴候选，返回 [{size_code, score, source, reason}]。"""
    sizes = _boot_sizes_sorted(_eligible_sizes(equipment, "boots", ""))
    fit_scores = cfg["fit_scores"]
    forbidden = _forbidden_sizes(fit_records, member["member_id"], "boots")
    cand = {}

    # 1) 实际试穿
    for s in sizes:
        if s in forbidden:
            continue
        f = _fit_for(fit_records, member["member_id"], "boots", s)
        if f and f["fit_level"] != "no" and f["fit_level"] in fit_scores:
            cand[s] = {"size_code": s, "score": fit_scores[f["fit_level"]],
                       "source": "试穿", "reason": f"试穿记录：{f['fit_level']}"}

    # 2) 上学年沿用
    prev = member.get("previous_boot_id")
    if prev and not member.get("request_resize"):
        ps = schemas.parse_boot_size(prev)
        if ps in sizes and ps not in cand and ps not in forbidden:
            cand[ps] = {"size_code": ps, "score": 0, "source": "上年沿用",
                        "reason": "上学年合身沿用"}

    # 3) 尺码规则（脚长 -> 推荐码 ± 相邻）
    foot = schemas.to_number(member.get("foot_length_mm"))
    if foot is not None:
        b = cfg["boots"]
        rec = _foot_to_size(b["foot_table"], foot)
        if rec is not None:
            for s in sizes:
                if s in forbidden:
                    continue
                sn = int(s)
                if abs(sn - rec) <= b["neighbor_count"]:
                    score = cfg["predicted_score"] + abs(sn - rec) * 5
                    if s not in cand:
                        cand[s] = {"size_code": s, "score": score, "source": "规则预测",
                                   "reason": f"脚长{int(foot)}mm → {rec}码"}
                    else:
                        cand[s]["score"] = min(cand[s]["score"], score)

    # 4) 相邻兜底（脚长数据缺失时，给推荐码附近）
    return sorted(cand.values(), key=lambda c: c["score"])
