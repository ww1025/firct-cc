# -*- coding: utf-8 -*-
"""礼服智能分配 —— 9 个子页面的 Streamlit 渲染。"""
import io
import base64

import streamlit as st
import pandas as pd
import openpyxl

from . import (schemas, repository, seed, size_matcher, allocation_engine,
               conflict_checker, export_service)

SUB_PAGES = [
    ("dashboard", "📊 分配总览"),
    ("members", "👥 队员管理"),
    ("lock", "🔒 老队员锁定"),
    ("equipment", "📦 装备库存"),
    ("allocate", "⚙️ 自动预分配"),
    ("fitting", "👟 试穿工作台"),
    ("conflicts", "⚠️ 冲突与缺口"),
    ("final", "✅ 最终分配"),
    ("export", "📁 归置与导出"),
]

MEMBER_IMPORT_COLS = ["姓名", "性别", "班级", "新老队员", "是否本部执勤", "身高_cm",
                      "体重_kg", "头围_cm", "胸围_cm", "腰围_cm", "小腿围_cm",
                      "脚长_mm", "上一年礼服ID", "上一年马靴ID", "申请换码", "备注"]


# ═══════════════ 工具函数 ═══════════════
def _next_member_id(store):
    nums = [int(m["member_id"][1:]) for m in store["members"]
            if m.get("member_id") and str(m["member_id"][1:]).isdigit()]
    return f"M{max(nums) + 1 if nums else 1:04d}"


def _members_df(store):
    rows = []
    for m in store["members"]:
        rows.append({
            "ID": m["member_id"], "姓名": m["name"], "性别": m["gender"],
            "班级": m["duty_class"], "状态": m["member_status"],
            "本部执勤": "是" if m["active_in_hq"] else "否",
            "身高": m["height_cm"], "胸围": m["chest_cm"], "脚长": m["foot_length_mm"],
            "上年礼服": m["previous_uniform_id"], "上年马靴": m["previous_boot_id"],
            "申请换码": "是" if m["request_resize"] else "否",
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _member_by_id(store):
    return {m["member_id"]: m for m in store["members"]}


def _name_of(store, mid):
    m = _member_by_id(store).get(mid)
    return m["name"] if m else mid


def _size_inventory(equipment, category, gender, size_code):
    ids, locs = [], []
    for e in equipment:
        if e["category"] != category or e["status"] != "available":
            continue
        if str(e["size_code"]) != str(size_code):
            continue
        if category == "uniform" and e["gender"] and gender and e["gender"] != gender:
            continue
        ids.append(e["equipment_id"])
        if e["location"]:
            locs.append(e["location"])
    return len(ids), sorted(set(locs))


def _run_allocation(store, cfg):
    locked = {}
    for a in store["allocations"]:
        if a.get("locked") and a.get("uniform_id"):
            locked[a["member_id"]] = {"uniform_id": a.get("uniform_id"),
                                      "boot_id": a.get("boot_id")}
    result = allocation_engine.solve(store["members"], store["equipment"],
                                     store["fit_records"], locked, cfg)
    store["last_result"] = result
    if result["status"] in ("OPTIMAL", "FEASIBLE"):
        repository.clear_allocations(store)
        for a in result["allocations"]:
            a["locked"] = bool(a["member_id"] in locked or a.get("locked"))
            repository.set_allocation(store, a)
        repository.save_draft(store)
    return result


# ═══════════════ 主入口 ═══════════════
def render(get_warehouse_data):
    store = repository.get_store()
    cfg = repository.get_config(store)

    st.markdown("""
    <div class="flag-header">
      <div class="brand"><div class="stars">&#9733;</div><h1>礼服智能分配</h1></div>
      <div class="stars">&#9733;</div>
    </div>
    """, unsafe_allow_html=True)

    col_back, col_year = st.columns([1, 4])
    if col_back.button("← 返回首页", key="smart_back"):
        st.session_state.page = 'home'
        st.rerun()
    col_year.markdown(f"**学年批次：{cfg['year']}**")

    if not store["seeded"]:
        _render_init(store, get_warehouse_data)
        return

    # 子页导航（懒加载，只渲染选中页）
    labels = [label for _, label in SUB_PAGES]
    keys = [key for key, _ in SUB_PAGES]
    if "smart_tab" not in st.session_state or st.session_state.smart_tab not in keys:
        st.session_state.smart_tab = "dashboard"
    cur = st.selectbox("功能页", labels, index=keys.index(st.session_state.smart_tab),
                       key="smart_tab_sel")
    st.session_state.smart_tab = keys[labels.index(cur)]

    fn = {
        "dashboard": _page_dashboard, "members": _page_members, "lock": _page_lock,
        "equipment": _page_equipment, "allocate": _page_allocate,
        "fitting": _page_fitting, "conflicts": _page_conflicts,
        "final": _page_final, "export": _page_export_settings,
    }[st.session_state.smart_tab]
    fn(store, cfg)


def _render_init(store, get_warehouse_data):
    st.info("首次使用需要先从「物资仓库」数据初始化装备实体表，再导入队员信息。")
    if st.button("🚀 初始化装备（从物资仓库数据生成）", use_container_width=True):
        raw = get_warehouse_data()
        import json
        wh = json.loads(raw)
        equipment, prev = seed.build_equipment(wh)
        store["equipment"] = equipment
        store["prev_assignment"] = prev
        store["seeded"] = True
        st.success(f"已初始化 {len(equipment)} 件装备实体，识别到 {len(prev)} 名上学年使用人。")
        st.rerun()


# ═══════════════ 1. 分配总览 ═══════════════
def _page_dashboard(store, cfg):
    n_total = len(store["members"])
    n_locked = sum(1 for a in store["allocations"] if a.get("locked"))
    active = [m for m in store["members"] if m.get("active_in_hq") and m.get("member_status") != "leaving"]
    n_alloc = len(store["allocations"])
    n_pending = len(active) - n_alloc
    u_avail = sum(1 for e in store["equipment"] if e["category"] == "uniform" and e["status"] == "available")
    b_avail = sum(1 for e in store["equipment"] if e["category"] == "boots" and e["status"] == "available")
    shared = store["last_result"].get("shared", []) if store["last_result"] else []
    shortage = store["last_result"].get("shortage", []) if store["last_result"] else []

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("队员总数", n_total)
    c2.metric("已锁定", n_locked)
    c3.metric("待分配", max(n_pending, 0))
    c4.metric("共用装备", len(shared))

    c5, c6, c7 = st.columns(3)
    c5.metric("礼服可用", u_avail)
    c6.metric("马靴可用", b_avail)
    c7.metric("未解决缺口", len(shortage))

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    if col1.button("⚙️ 开始预分配", use_container_width=True):
        with st.spinner("正在求解（CP-SAT 全局优化）..."):
            res = _run_allocation(store, cfg)
        st.rerun()
    if col2.button("🔁 重新计算", use_container_width=True, help="仅重算未锁定人员"):
        with st.spinner("正在重新计算..."):
            res = _run_allocation(store, cfg)
        st.rerun()
    with col3:
        _download_final(store)

    # 紧缺尺码 Top N
    if shortage:
        st.markdown("### 紧缺尺码")
        st.dataframe(pd.DataFrame([{
            "类别": "礼服" if s["category"] == "uniform" else "马靴",
            "尺码": s["size_code"], "可用": s["available"],
            "最多覆盖": s["max_cover"], "缺口": s["gap"]} for s in shortage]),
            use_container_width=True, hide_index=True)


# ═══════════════ 2. 队员管理 ═══════════════
def _page_members(store, cfg):
    st.markdown("#### 导入队员")
    c1, c2 = st.columns([2, 1])
    up = c1.file_uploader("上传队员 Excel（.xlsx）", type=["xlsx"], key="member_xlsx",
                          label_visibility="collapsed")
    c2.download_button("⬇ 下载导入模板", data=_member_template_bytes(),
                       file_name="队员信息导入模板.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)
    if up is not None:
        members, errors = _parse_members(up.getvalue())
        if errors:
            for e in errors:
                st.warning(e)
        else:
            existing = {m["name"]: m for m in store["members"]}
            n_new = 0
            for m in members:
                if m["name"] in existing:
                    m["member_id"] = existing[m["name"]]["member_id"]  # 同名更新，不重复建档
                else:
                    m["member_id"] = _next_member_id(store)
                    n_new += 1
                repository.upsert_member(store, m)
            st.success(f"已导入 {len(members)} 人（新增 {n_new} 人，更新 {len(members) - n_new} 人）。")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 队员列表")
    df = _members_df(store)
    if df.empty:
        st.caption("暂无队员，请先导入。")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("#### 编辑单个队员")
        names = [m["name"] for m in store["members"]]
        sel = st.selectbox("选择队员", names, key="member_edit_sel")
        m = next((x for x in store["members"] if x["name"] == sel), None)
        if m:
            _member_edit_form(store, m)


def _member_edit_form(store, m):
    with st.form("member_edit_form"):
        c1, c2, c3 = st.columns(3)
        gender = c1.selectbox("性别", ["M", "F"], index=0 if m["gender"] != "F" else 1)
        duty = c2.text_input("班级", value=m["duty_class"] or "")
        status = c3.selectbox("新老状态", ["new", "returning", "leaving"],
                              index=["new", "returning", "leaving"].index(m["member_status"] or "new"))
        active = st.checkbox("是否本部执勤", value=bool(m["active_in_hq"]))
        c4, c5, c6 = st.columns(3)
        h = c4.number_input("身高 cm", value=float(m["height_cm"] or 0.0), step=1.0)
        chest = c5.number_input("胸围 cm", value=float(m["chest_cm"] or 0.0), step=1.0)
        foot = c6.number_input("脚长 mm", value=float(m["foot_length_mm"] or 0.0), step=1.0)
        c7, c8, c9 = st.columns(3)
        w = c7.number_input("体重 kg", value=float(m["weight_kg"] or 0.0), step=1.0)
        waist = c8.number_input("腰围 cm", value=float(m["waist_cm"] or 0.0), step=1.0)
        calf = c9.number_input("小腿围 cm", value=float(m["calf_cm"] or 0.0), step=1.0)
        c10, c11 = st.columns(2)
        prev_u = c10.text_input("上一年礼服ID", value=m["previous_uniform_id"] or "")
        prev_b = c11.text_input("上一年马靴ID", value=m["previous_boot_id"] or "")
        resize = st.checkbox("申请换码", value=bool(m["request_resize"]))
        notes = st.text_input("备注", value=m["notes"] or "")
        if st.form_submit_button("保存"):
            m.update(gender=gender, duty_class=duty, member_status=status,
                     active_in_hq=active, height_cm=h or None, chest_cm=chest or None,
                     foot_length_mm=foot or None, weight_kg=w or None,
                     waist_cm=waist or None, calf_cm=calf or None,
                     previous_uniform_id=prev_u or None, previous_boot_id=prev_b or None,
                     request_resize=resize, notes=notes)
            repository.upsert_member(store, m)
            st.success("已保存")
            st.rerun()


def _member_template_bytes():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "队员"
    ws.append(MEMBER_IMPORT_COLS)
    ws.append(["叶宇轩", "男", "周一班", "returning", 1, 178, 68, 57, 92, 78, 36, 265,
               "M175/96-02", "N41/42-05", 0, "示例行，可删除"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _parse_members(data_bytes):
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data_bytes))
    except Exception as e:
        return [], [f"无法读取 Excel：{e}"]
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["文件为空"]
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    col = {h: i for i, h in enumerate(headers)}

    def get(row, name):
        i = col.get(name)
        return row[i] if i is not None and i < len(row) else None

    members, errors = [], []
    for r in rows[1:]:
        name = str(get(r, "姓名") or "").strip()
        if not name:
            continue
        g = str(get(r, "性别") or "").strip()
        gender = "M" if g in ("男", "M", "m") else ("F" if g in ("女", "F", "f") else "")
        status_raw = str(get(r, "新老队员") or "").strip()
        status = "returning" if status_raw in ("老", "老队员", "returning", "留队") else \
                 ("leaving" if status_raw in ("退队", "leaving") else "new")
        m = schemas.new_member(
            name=name, gender=gender or "M",
            duty_class=str(get(r, "班级") or "").strip() or None,
            member_status=status,
            active_in_hq=schemas.to_bool(get(r, "是否本部执勤"), True),
            height_cm=schemas.to_number(get(r, "身高_cm")),
            weight_kg=schemas.to_number(get(r, "体重_kg")),
            head_cm=schemas.to_number(get(r, "头围_cm")),
            chest_cm=schemas.to_number(get(r, "胸围_cm")),
            waist_cm=schemas.to_number(get(r, "腰围_cm")),
            calf_cm=schemas.to_number(get(r, "小腿围_cm")),
            foot_length_mm=schemas.to_number(get(r, "脚长_mm")),
            previous_uniform_id=str(get(r, "上一年礼服ID") or "").strip() or None,
            previous_boot_id=str(get(r, "上一年马靴ID") or "").strip() or None,
            request_resize=schemas.to_bool(get(r, "申请换码"), False),
            notes=str(get(r, "备注") or "").strip() or None,
        )
        # 必填校验
        if m["height_cm"] is None or m["chest_cm"] is None or m["foot_length_mm"] is None:
            errors.append(f"{name}：缺少身高/胸围/脚长（必填），已跳过")
            continue
        if not gender:
            errors.append(f"{name}：性别无法识别，已按男处理")
        members.append(m)
    return members, errors


# ═══════════════ 3. 老队员锁定 ═══════════════
def _page_lock(store, cfg):
    st.markdown("#### 建议沿用原装备的老队员")
    eq_by_id = {e["equipment_id"]: e for e in store["equipment"]}
    candidates = [m for m in store["members"]
                  if m.get("member_status") == "returning"
                  and not m.get("request_resize")
                  and (m.get("previous_uniform_id") or m.get("previous_boot_id"))]

    if not candidates:
        st.caption("暂无建议锁定的老队员。")
        return

    rows = []
    for m in candidates:
        pu = m.get("previous_uniform_id")
        pb = m.get("previous_boot_id")
        ok_u = pu in eq_by_id and eq_by_id[pu]["status"] == "available"
        ok_b = pb in eq_by_id and eq_by_id[pb]["status"] == "available"
        locked = any(a["member_id"] == m["member_id"] and a.get("locked") for a in store["allocations"])
        rows.append({"姓名": m["name"], "班级": m["duty_class"], "上年礼服": pu,
                     "上年马靴": pb, "装备可用": "是" if (ok_u and ok_b) else "部分不可用",
                     "已锁定": "是" if locked else "否"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    names = [m["name"] for m in candidates]
    sel_names = st.multiselect("选择要锁定的老队员", names, key="lock_sel")
    col1, col2 = st.columns(2)
    if col1.button("🔒 批量锁定（沿用原装备）", use_container_width=True):
        n = 0
        for m in candidates:
            if m["name"] not in sel_names:
                continue
            pu, pb = m.get("previous_uniform_id"), m.get("previous_boot_id")
            if (pu and pu in eq_by_id and eq_by_id[pu]["status"] == "available") or \
               (pb and pb in eq_by_id and eq_by_id[pb]["status"] == "available"):
                a = repository.allocation_for(store, m["member_id"]) or schemas.new_allocation(m["member_id"])
                a.update(uniform_id=pu, boot_id=pb, source="previous", locked=True,
                         fit_explanation="上学年合身沿用（已锁定）")
                repository.set_allocation(store, a)
                n += 1
        st.success(f"已锁定 {n} 人。")
        st.rerun()
    if col2.button("🔓 取消全部锁定", use_container_width=True):
        for a in store["allocations"]:
            a["locked"] = False
        st.success("已取消全部锁定。")
        st.rerun()


# ═══════════════ 4. 装备库存 ═══════════════
def _page_equipment(store, cfg):
    st.markdown("#### 装备实体清单（复用物资仓库数据）")
    cat = st.radio("类别", ["全部", "礼服", "马靴"], horizontal=True, key="eq_cat")
    rows = []
    for e in store["equipment"]:
        if cat == "礼服" and e["category"] != "uniform":
            continue
        if cat == "马靴" and e["category"] != "boots":
            continue
        rows.append({"实体ID": e["equipment_id"], "类别": "礼服" if e["category"] == "uniform" else "马靴",
                     "性别": e["gender"] or "-", "尺码": e["size_code"], "状态": e["status"],
                     "位置": e["location"], "配套腰带": e["paired_belt_id"] or "-"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"共 {len(rows)} 件；数量由实体装备汇总而来。")

    st.markdown("#### 修改装备状态")
    ids = [e["equipment_id"] for e in store["equipment"]]
    sel = st.selectbox("装备", ids, key="eq_edit_sel")
    e = next((x for x in store["equipment"] if x["equipment_id"] == sel), None)
    if e:
        c1, c2 = st.columns(2)
        new_status = c1.selectbox("状态", ["available", "repair", "damaged", "borrowed"],
                                  index=["available", "repair", "damaged", "borrowed"].index(e["status"]),
                                  key="eq_status")
        new_loc = c2.text_input("位置", value=e["location"] or "", key="eq_loc")
        if st.button("保存", key="eq_save"):
            e["status"] = new_status
            e["location"] = new_loc
            repository.upsert_equipment(store, e)
            st.success("已保存")
            st.rerun()


# ═══════════════ 5. 自动预分配 ═══════════════
def _page_allocate(store, cfg):
    st.markdown("#### 自动预分配（CP-SAT 全局优化）")
    st.caption("只优化未锁定队员；已锁定/人工确认的分配保持不变。")
    if st.button("⚙️ 开始预分配", use_container_width=True, type="primary"):
        with st.spinner("正在求解..."):
            res = _run_allocation(store, cfg)
        st.rerun()

    res = store["last_result"]
    if not res:
        st.info("尚未运行分配。点击上方按钮开始。")
        return

    st.markdown(f"**状态：** {res['status']} ｜ 耗时 {res['duration_ms']} ms" +
                (f" ｜ 目标值 {res['objective']}" if res.get("objective") is not None else ""))
    if res.get("message"):
        st.info(res["message"])

    if res["shared"]:
        st.markdown("#### 共用情况")
        st.dataframe(pd.DataFrame([{"装备ID": s["equipment_id"],
                                    "类别": "礼服" if s["category"] == "uniform" else "马靴",
                                    "使用人": "、".join(s["members"])} for s in res["shared"]]),
                     use_container_width=True, hide_index=True)

    if res.get("shortage"):
        st.markdown("#### 无解诊断 / 缺口")
        for s in res["shortage"]:
            st.error(f"「{'男/女' if s['category']=='uniform' else ''}{s['size_code']}」"
                     f"{'礼服' if s['category']=='uniform' else '马靴'}：可用 {s['available']} 件，"
                     f"最多覆盖 {s['max_cover']} 人，仅能穿该码者 {s['demand']} 人，缺口 {s['gap']} 人"
                     f"（建议新增 {s['add_items']} 件）。受影响：{'、'.join(s['affected'])}")
            sug = "；".join(f"{x['name']} → 试穿 {x['suggest']}" for x in s["suggestions"])
            if sug:
                st.caption(f"建议优先试穿：{sug}")

    if res.get("allocations"):
        st.markdown("#### 分配结果")
        df = pd.DataFrame([{
            "姓名": a["name"], "礼服": a["uniform_size"], "礼服ID": a["uniform_id"],
            "马靴": a["boot_size"], "马靴ID": a["boot_id"],
            "来源": a["source"], "锁定": "是" if a["locked"] else "否",
            "解释": a["fit_explanation"]} for a in res["allocations"]])
        st.dataframe(df, use_container_width=True, hide_index=True)
        _download_final(store)


def _download_final(store):
    st.download_button("⬇ 导出最终分配表", data=export_service.final_allocation_xlsx(
        store, store["members"], store["equipment"]),
        file_name="最终分配表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True)


# ═══════════════ 6. 试穿工作台 ═══════════════
def _page_fitting(store, cfg):
    st.markdown("#### 试穿工作台")
    names = [m["name"] for m in store["members"]]
    if not names:
        st.caption("请先在「队员管理」导入队员。")
        return
    sel = st.selectbox("搜索/选择队员", names, key="fit_sel")
    m = next((x for x in store["members"] if x["name"] == sel), None)
    if not m:
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("身高", f"{m['height_cm']} cm")
    c2.metric("胸围", f"{m['chest_cm']} cm")
    c3.metric("腰围", f"{m['waist_cm'] or '-'} cm")
    c4.metric("脚长", f"{m['foot_length_mm']} mm")
    st.caption(f"班级：{m['duty_class'] or '-'} ｜ 性别：{'男' if m['gender']=='M' else '女'}")

    uniforms = [e for e in store["equipment"] if e["category"] == "uniform" and e["status"] == "available"]
    boots = [e for e in store["equipment"] if e["category"] == "boots" and e["status"] == "available"]
    u_cand = size_matcher.uniform_candidates(m, uniforms, store["fit_records"], cfg)
    b_cand = size_matcher.boot_candidates(m, boots, store["fit_records"], cfg)

    st.markdown("#### 礼服候选")
    _render_candidates(store, m, "uniform", u_cand, cfg)
    st.markdown("#### 马靴候选")
    _render_candidates(store, m, "boots", b_cand, cfg)

    st.markdown("#### 保存并重新计算")
    if st.button("🔁 保存试穿记录并重新计算", use_container_width=True):
        with st.spinner("重新计算..."):
            _run_allocation(store, cfg)
        st.rerun()


def _render_candidates(store, m, category, cands, cfg):
    equipment = store["equipment"]
    gender = m["gender"]
    if not cands:
        st.caption("（无候选尺码）")
        return
    for c in cands:
        size = c["size_code"]
        cnt, locs = _size_inventory(equipment, category, gender, size)
        c1, c2, c3 = st.columns([2, 3, 4])
        c1.markdown(f"**{size}**  `{c['source']}`")
        c2.markdown(f"库存余量：{cnt} ｜ 位置：{'、'.join(locs) if locs else '-'}")
        c3.caption(c["reason"])
        btns = st.columns(5)
        for i, (lvl, label) in enumerate([("best", "最合适"), ("wearable", "可穿"),
                                          ("loose", "偏大"), ("tight", "偏小"), ("no", "不可穿")]):
            if btns[i].button(f"{label}", key=f"fit_{category}_{size}_{lvl}_{m['member_id']}"):
                rec = schemas.new_fit_record(member_id=m["member_id"], category=category,
                                             size_code=size, fit_level=lvl,
                                             fit_score=cfg["fit_scores"].get(lvl, None),
                                             verified=True)
                repository.upsert_fit_record(store, rec)
                st.rerun()
    st.markdown("---")


# ═══════════════ 7. 冲突与缺口 ═══════════════
def _page_conflicts(store, cfg):
    st.markdown("#### 独立冲突复核")
    violations, summary = conflict_checker.check(store["allocations"], store["members"],
                                                 store["equipment"], store["fit_records"])
    c = st.columns(5)
    for i, (k, v) in enumerate(summary.items()):
        c[i].metric(k, v)

    if all(v == 0 for v in summary.values()) and store["allocations"]:
        st.success("全部硬约束校验通过（三人共用=0、同班共用=0、无装备=0、不可穿=0、损坏装备=0）。")
    else:
        for v in violations:
            st.error(f"{v['type']}：{v['detail']}")

    res = store["last_result"]
    if res and res.get("shortage"):
        st.markdown("#### 库存缺口（来自最近一次求解）")
        for s in res["shortage"]:
            st.warning(f"{s['size_code']}（{'礼服' if s['category']=='uniform' else '马靴'}）："
                       f"可用 {s['available']}，最多覆盖 {s['max_cover']}，缺口 {s['gap']} 人。"
                       f"受影响：{'、'.join(s['affected'])}")


# ═══════════════ 8. 最终分配 ═══════════════
def _page_final(store, cfg):
    st.markdown("#### 最终分配表")
    if not store["allocations"]:
        st.info("暂无分配结果。请先到「自动预分配」求解。")
        return

    violations, summary = conflict_checker.check(store["allocations"], store["members"],
                                                 store["equipment"], store["fit_records"])
    ok = all(v == 0 for v in summary.values())
    st.markdown("**校验摘要：** " + " ｜ ".join(f"{k}={v}" for k, v in summary.items()))
    if ok:
        st.success("✅ 校验通过，可标记为最终版。")
    else:
        st.error("存在冲突，需处理后方可标记为最终版。")

    eq_by_id = {e["equipment_id"]: e for e in store["equipment"]}
    m_by_id = {m["member_id"]: m for m in store["members"]}
    rows = []
    for a in store["allocations"]:
        m = m_by_id.get(a["member_id"], {})
        rows.append({
            "姓名": m.get("name", ""), "班级": m.get("duty_class", ""),
            "礼服ID/尺码": f"{a['uniform_id']} / {a.get('uniform_size','')}",
            "礼服共用人": _share_with(store, a, "uniform"),
            "马靴ID/尺码": f"{a['boot_id']} / {a.get('boot_size','')}",
            "马靴共用人": _share_with(store, a, "boots"),
            "状态": "锁定" if a.get("locked") else a.get("source", ""),
            "解释": a.get("fit_explanation", ""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 人工换装
    st.markdown("#### 人工换装")
    names = [m_by_id[a["member_id"]]["name"] for a in store["allocations"] if a["member_id"] in m_by_id]
    sel = st.selectbox("队员", names, key="final_sel")
    a = next((x for x in store["allocations"]
              if m_by_id.get(x["member_id"], {}).get("name") == sel), None)
    if a:
        m = m_by_id[a["member_id"]]
        uniforms = [e for e in store["equipment"]
                    if e["category"] == "uniform" and e["status"] == "available"
                    and (not e["gender"] or not m.get("gender") or e["gender"] == m["gender"])]
        boots = [e for e in store["equipment"] if e["category"] == "boots" and e["status"] == "available"]
        u_options = ["（不变）"] + [f"{e['equipment_id']}（{e['size_code']}）" for e in uniforms]
        b_options = ["（不变）"] + [f"{e['equipment_id']}（{e['size_code']}）" for e in boots]
        c1, c2 = st.columns(2)
        new_u = c1.selectbox("礼服", u_options, key="final_u")
        new_b = c2.selectbox("马靴", b_options, key="final_b")
        lock = st.checkbox("锁定该队员分配", value=bool(a.get("locked")), key="final_lock")
        if st.button("💾 保存换装（保存前自动校验）", key="final_save"):
            if new_u != "（不变）":
                a["uniform_id"] = new_u.split("（")[0]
                a["uniform_size"] = schemas.uniform_size_of(a["uniform_id"])
            if new_b != "（不变）":
                a["boot_id"] = new_b.split("（")[0]
                a["boot_size"] = schemas.parse_boot_size(a["boot_id"])
            a["locked"] = lock
            a["source"] = "manual" if not lock else "manual"
            a["fit_explanation"] = "人工指定"
            # 校验
            v2, s2 = conflict_checker.check(store["allocations"], store["members"],
                                            store["equipment"], store["fit_records"])
            if any(x > 0 for x in s2.values()):
                st.error("换装后产生冲突，已阻止保存：")
                for v in v2:
                    st.error(f"{v['type']}：{v['detail']}")
            else:
                repository.set_allocation(store, a)
                st.success("已保存，校验通过。")
                st.rerun()


def _share_with(store, a, category):
    key = "uniform_id" if category == "uniform" else "boot_id"
    eid = a.get(key)
    if not eid:
        return "-"
    others = []
    for x in store["allocations"]:
        if x["member_id"] != a["member_id"] and x.get(key) == eid:
            others.append(_name_of(store, x["member_id"]))
    return "、".join(others) if others else "-"


# ═══════════════ 9. 归置与导出 ═══════════════
def _page_export_settings(store, cfg):
    st.markdown("#### 导出")
    try:
        files = export_service.export_all(store, store["members"], store["equipment"], cfg)
    except Exception as e:
        files = {}
        st.warning(f"导出生成失败：{e}")

    c = st.columns(2)
    labels = {
        "最终分配表.xlsx": "📥 最终分配表",
        "共用清单.xlsx": "📥 共用清单",
        "缺口与待采购参考.xlsx": "📥 缺口参考",
        "各班装备归置表.xlsx": "📥 各班归置表",
        "试穿记录.xlsx": "📥 试穿记录",
    }
    for i, (fname, data) in enumerate(files.items()):
        c[i % 2].download_button(labels.get(fname, fname), data=data, file_name=fname,
                                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 use_container_width=True)

    st.markdown("---")
    st.markdown("#### 草稿回滚（最近 5 次求解快照）")
    if store["drafts"]:
        labels = [f"第 {i + 1} 次求解（{len(d)} 人）" for i, d in enumerate(store["drafts"])]
        sel = st.selectbox("选择快照", labels, key="draft_sel")
        if st.button("↩ 恢复该草稿", key="draft_restore"):
            if repository.restore_draft(store, labels.index(sel)):
                st.success("已恢复草稿。")
            st.rerun()
    else:
        st.caption("暂无草稿（运行一次预分配后自动保存）。")

    st.markdown("---")
    st.markdown("#### 系统设置（尺码规则 / 权重 / 班级冲突矩阵）")
    st.caption("普通使用时无需进入。修改后即时生效，保存到当前会话。")
    with st.form("settings_form"):
        c1, c2, c3 = st.columns(3)
        u = cfg["uniform"]
        h_tol = c1.number_input("礼服身高容差(cm)", value=int(u["height_tol"]), step=1)
        c_tol = c2.number_input("礼服胸围容差(cm)", value=int(u["chest_tol"]), step=1)
        pred = c3.number_input("预测尺码基础分", value=int(cfg["predicted_score"]), step=1)
        c4, c5, c6 = st.columns(3)
        w = cfg["weights"]
        sh = c4.number_input("共用惩罚", value=int(w["sharing"]), step=1)
        oc = c5.number_input("老队员换装惩罚", value=int(w["old_change"]), step=1)
        pr = c6.number_input("预测尺码惩罚", value=int(w["predicted"]), step=1)
        c7, c8 = st.columns(2)
        yr = c7.text_input("学年批次", value=cfg["year"])
        cm = c8.text_area("班级冲突矩阵（JSON，如 {\"周一班,周二班\":\"high\"}）",
                          value=_matrix_to_text(cfg.get("class_matrix", {})), height=90)
        if st.form_submit_button("保存设置"):
            cfg["uniform"]["height_tol"] = int(h_tol)
            cfg["uniform"]["chest_tol"] = int(c_tol)
            cfg["predicted_score"] = int(pred)
            cfg["weights"]["sharing"] = int(sh)
            cfg["weights"]["old_change"] = int(oc)
            cfg["weights"]["predicted"] = int(pr)
            cfg["year"] = yr
            cfg["class_matrix"] = _text_to_matrix(cm)
            store["config"] = cfg
            st.success("设置已保存。")
            st.rerun()


def _matrix_to_text(m):
    import json
    return json.dumps(m, ensure_ascii=False) if m else "{}"


def _text_to_matrix(s):
    import json
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}
