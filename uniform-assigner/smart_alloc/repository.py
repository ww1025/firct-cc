# -*- coding: utf-8 -*-
"""数据访问层（repository）。

v1 用 st.session_state 内存态 + Excel 导入/导出作为持久化手段。
所有读写都经过本模块，未来可无缝替换为 Supabase/PostgreSQL 后端
（只需重写 get/put 两个底层函数）。
"""
import json
import streamlit as st

_KEY = "smart_alloc_store"


def _empty():
    return {
        "members": [],         # list[dict]
        "equipment": [],       # list[dict]
        "fit_records": [],     # list[dict]
        "allocations": [],     # list[dict]，每名有效队员一条
        "config": None,        # dict；None 表示用 DEFAULT_CONFIG
        "seeded": False,       # 是否已从物资仓库数据初始化装备
        "prev_assignment": {}, # name -> {"uniform": id, "boots": id} 上学年分配
        "last_result": None,   # 最近一次求解结果
        "drafts": [],          # 最近若干次求解快照
    }


def get_store():
    if _KEY not in st.session_state:
        st.session_state[_KEY] = _empty()
    return st.session_state[_KEY]


def reset_store():
    st.session_state[_KEY] = _empty()


def get_config(store):
    from . import config as cfg
    return store["config"] if store["config"] else cfg.DEFAULT_CONFIG


# ── members ──
def upsert_member(store, member):
    for i, m in enumerate(store["members"]):
        if m["member_id"] == member["member_id"]:
            store["members"][i] = member
            return
    store["members"].append(member)


def get_member(store, member_id):
    for m in store["members"]:
        if m["member_id"] == member_id:
            return m
    return None


def delete_member(store, member_id):
    store["members"] = [m for m in store["members"] if m["member_id"] != member_id]


# ── equipment ──
def equipment_by_id(store):
    return {e["equipment_id"]: e for e in store["equipment"]}


def upsert_equipment(store, equip):
    for i, e in enumerate(store["equipment"]):
        if e["equipment_id"] == equip["equipment_id"]:
            store["equipment"][i] = equip
            return
    store["equipment"].append(equip)


# ── fit records ──
def fit_records_for(store, member_id, category=None):
    out = [f for f in store["fit_records"] if f["member_id"] == member_id]
    if category:
        out = [f for f in out if f["category"] == category]
    return out


def upsert_fit_record(store, rec):
    for i, f in enumerate(store["fit_records"]):
        if (f["member_id"] == rec["member_id"] and f["category"] == rec["category"]
                and f["size_code"] == rec["size_code"]):
            store["fit_records"][i] = rec
            return
    store["fit_records"].append(rec)


# ── allocations ──
def allocation_for(store, member_id):
    for a in store["allocations"]:
        if a["member_id"] == member_id:
            return a
    return None


def set_allocation(store, alloc):
    for i, a in enumerate(store["allocations"]):
        if a["member_id"] == alloc["member_id"]:
            store["allocations"][i] = alloc
            return
    store["allocations"].append(alloc)


def clear_allocations(store):
    store["allocations"] = []


def save_draft(store):
    """保存当前分配为草稿快照，最多保留 5 份。"""
    snap = json.loads(json.dumps(store["allocations"]))
    store["drafts"].append(snap)
    store["drafts"] = store["drafts"][-5:]


def restore_draft(store, idx):
    if 0 <= idx < len(store["drafts"]):
        store["allocations"] = json.loads(json.dumps(store["drafts"][idx]))
        return True
    return False


# ── 深拷贝工具（供页面/引擎安全拷贝用）──
def deepcopy(obj):
    return json.loads(json.dumps(obj))
