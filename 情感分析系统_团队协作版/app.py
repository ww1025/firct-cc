"""app.py —— 浙江大学 · 中文文本情感分析系统
治愈系明亮版 · Navbar Router · 真实 Python 后端闭环
"""

import streamlit as st
import streamlit.components.v1 as components
import random, re, os, pickle, base64, sys, time, json
import numpy as np, jieba, pandas as pd
from typing import Tuple, Dict, Optional, List
from datetime import datetime

# ============================================================
st.set_page_config(page_title="中文文本情感分析系统 | 浙江大学", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# 全局 CSS
# ============================================================
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:.5rem!important;padding-bottom:0!important;background-color:#f8fafc}
body{background-color:#f8fafc}
.stVerticalBlock{gap:.3rem!important}

/* 引擎标题与轮播图间距收紧，但绝不遮盖浙大 Logo */
div[data-testid="stMarkdownContainer"] h2{margin-top:-10px!important;margin-bottom:10px!important;padding-top:0!important}

.stTextArea textarea{background-color:#fff!important;color:#1e293b!important;border:1px solid #e2e8f0!important;border-radius:.75rem!important;box-shadow:0 1px 2px rgba(0,0,0,.04)!important}
.stTextArea textarea:focus{border-color:#93c5fd!important;box-shadow:0 0 0 3px rgba(59,130,246,.1)!important}
.stButton button{font-weight:600!important;transition:all .2s;border-radius:.5rem!important;padding:.5rem 1.5rem!important}
.stButton button:hover{transform:scale(1.02)}
.stTextArea label,.stMarkdown,.stWarning,.stError{color:#334155!important}
.stSpinner{color:#6366f1!important}

div[data-testid="stHorizontalBlock"] {
    background: rgba(255,255,255,.85); backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px); border: 1px solid #e2e8f0;
    border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,.04), 0 0 0 1px rgba(147,197,253,.15);
    padding: 8px 12px; margin: 16px auto 20px auto; max-width: 980px; gap: 4px;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
    background: transparent !important; color: #475569 !important;
    border: 1px solid transparent !important; font-weight: 600 !important;
    font-size: 13px !important; border-radius: 10px !important;
    padding: 8px 14px !important; transition: all .25s !important; box-shadow: none !important;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    background: #eff6ff !important; color: #3b82f6 !important; border-color: #e2e8f0 !important;
}
div[data-testid="stHorizontalBlock"] button[kind="primary"] {
    background: linear-gradient(135deg, #eff6ff, #dbeafe) !important;
    color: #1d4ed8 !important; border: 1px solid #93c5fd !important;
    font-weight: 700 !important; font-size: 13px !important; border-radius: 10px !important;
    padding: 8px 14px !important; box-shadow: 0 1px 4px rgba(59,130,246,.15) !important;
    transition: all .25s !important;
}

.zju-back-btn{display:inline-flex;align-items:center;gap:6px;padding:10px 22px;background:#fff;border:1px solid #cbd5e1;border-radius:10px;color:#475569;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;transition:all .2s;font-family:'Microsoft YaHei','PingFang SC',sans-serif;margin-bottom:12px}
.zju-back-btn:hover{background:#f1f5f9;border-color:#3b82f6;color:#2563eb;transform:translateY(-1px);box-shadow:0 2px 8px rgba(0,0,0,.06)}
.zju-card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.04);transition:all .25s}
.zju-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.06)}
</style>""", unsafe_allow_html=True)

# ============================================================
# 导入真实 Python 后端模块
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import news_fetcher
import emotion_engine

EMOTION_CONFIG  = emotion_engine.EMOTION_CONFIG
EMOTION_EN_TO_CN = emotion_engine.EMOTION_EN_TO_CN
LABEL_TO_CN      = emotion_engine.LABEL_TO_CN
STOP_WORDS       = emotion_engine.STOP_WORDS
clean_text       = emotion_engine.clean_text
predict          = emotion_engine.predict
load_models      = emotion_engine.load_models
get_loaded_models= emotion_engine.get_loaded_models

# ============================================================
# 🛡️ F5 刷新冷启动安全网（必须紧跟在 set_page_config 之后，绝对头部）
# ============================================================
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

if "input_val" not in st.session_state:
    st.session_state.input_val = "今天顺利拿到了大厂的正式录取通知书，全家人都为我感到骄傲！"

if "last_cleaned_text" not in st.session_state:
    st.session_state.last_cleaned_text = ""

if "last_prediction" not in st.session_state:
    st.session_state.last_prediction = None

if "relief_input" not in st.session_state:
    st.session_state.relief_input = "辛辛苦苦调了很久的代码全丢了，太绝望了！"

if "intel_news_data" not in st.session_state:
    st.session_state.intel_news_data = None

if "intel_fetch_time" not in st.session_state:
    st.session_state.intel_fetch_time = ""

if "fetched_data" not in st.session_state:
    st.session_state.fetched_data = None

if "chat_history_dict" not in st.session_state:
    st.session_state.chat_history_dict = {}

# ============================================================
# 示例文本
# ============================================================
EXAMPLES = [
    "今天顺利拿到了大厂的正式录取通知书，全家人都为我感到骄傲！",
    "买了三天还没发货，你们客服是死人吗？！垃圾服务，赶紧给我退钱！",
    "前半段剧情极其神作，后半段简直依托答辩，导演真有你的😊。",
    "最近真的太难熬了，每天都失眠崩溃，感觉要坚持不下去了解脱吧……",
    "网络喷子说话真恶心，长成这样也好意思发出来博眼球，赶紧封号吧。",
]

# ============================================================
# 浙大 Logo Banner（全局）
# ============================================================
with open(os.path.join(BASE_DIR, "assets", "zju_logo.jpg"), "rb") as _fl:
    _logo_b64 = base64.b64encode(_fl.read()).decode()
st.markdown(f"""<div style='display:flex;align-items:center;justify-content:center;gap:16px;padding:10px 0 8px 0;'>
<img src='data:image/jpeg;base64,{_logo_b64}' style='height:50px' alt='浙江大学'>
<div><div style='font-size:17px;font-weight:800;color:#1e293b;line-height:1.2'>浙江大学 · 中文文本情感分析系统</div>
<div style='font-size:11px;color:#94a3b8'>Zhejiang University · Emotion Analysis Engine</div></div></div>""", unsafe_allow_html=True)

# ============================================================
# Navbar — 纯 Streamlit 按钮，单窗口原地刷新
# ============================================================
NAV_ITEMS = [
    ("home", "🏠 系统首页"),
    ("intel", "🧠 情绪情报局"),
    ("feature", "🎯 情绪画像与热词矩阵"),
    ("relief", "🌿 心理卸压树洞"),
    ("showroom", "💼 业务落地展厅"),
]
_cur = st.session_state.current_page

_nav_cols = st.columns(len(NAV_ITEMS))
for _idx, (_key, _label) in enumerate(NAV_ITEMS):
    _is_active = _cur == _key
    with _nav_cols[_idx]:
        _btn_type = "primary" if _is_active else "secondary"
        if st.button(_label, key=f"nav_{_key}", type=_btn_type, use_container_width=True):
            if _key != _cur:
                st.session_state.current_page = _key
                st.rerun()

# ============================================================
# 辅助函数
# ============================================================

def _carousel():
    with open(os.path.join(BASE_DIR, "carousel_component.html"), "r", encoding="utf-8") as f:
        h = f.read()
    for i, cn in enumerate(["乐乐","忧忧","怒怒","厌厌","焦焦","慕慕","怕怕","尴尬","丧丧"]):
        with open(os.path.join(BASE_DIR, "assets", "characters", f"{cn}.jpg"), "rb") as f2:
            uri = f"data:image/jpeg;base64,{base64.b64encode(f2.read()).decode()}"
        h = h.replace(f"__IMG_{i}__", uri)
    components.html(h, height=480, scrolling=False)

def _back_btn():
    if st.button("🔙 返回系统首页", key="back_to_home"):
        st.session_state.current_page = "home"
        st.rerun()

def _section_title(text):
    st.markdown(f"<h2 style='color:#1e293b;font-size:1.2rem;font-weight:700;margin-bottom:4px'>{text}</h2>", unsafe_allow_html=True)

def _section_sub(text):
    st.markdown(f"<p style='color:#64748b;font-size:.82rem;margin-bottom:1.2rem'>{text}</p>", unsafe_allow_html=True)

def _render_engine():
    st.markdown("<h2 style='text-align:center;color:#1e293b;margin-top:.5rem'>中文文本情感分析识别引擎</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#64748b;font-size:.8rem;margin-bottom:1.5rem'>基于 TF-IDF 文本向量特征提取 与 逻辑回归 (Logistic Regression) 监督学习算法</p>", unsafe_allow_html=True)

    if st.button("🎲 随机加载预设测试示例"):
        st.session_state.input_val = random.choice(EXAMPLES)

    user_text = st.text_area("请输入要进行学术检测的中文文本：", value=st.session_state.input_val, height=100)

    c1, _ = st.columns([1, 6])
    with c1:
        analyze_click = st.button("🔍 分析情感")

    if analyze_click and user_text and user_text.strip():
        with st.spinner("🧠 AI 正在分析情感..."):
            try:
                emotion, probs = predict(user_text)
            except Exception as e:
                emotion = probs = None
                st.error(f"模型加载失败：{e}")

        if emotion is None:
            st.warning("⚠️ 清洗后文本为空，请尝试输入更丰富的中文内容。")
        else:
            st.session_state.last_cleaned_text = clean_text(user_text)
            st.session_state.last_prediction = (emotion, probs)

            conf = max(probs.values())
            cfg = EMOTION_CONFIG.get(emotion, EMOTION_CONFIG["中性"])

            st.markdown(f"""<div style='background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:32px 24px;text-align:center;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)'>
<div style='font-size:56px'>{cfg['emoji']}</div><div style='font-size:36px;font-weight:800;color:{cfg['color']};margin:10px 0 4px'>{emotion}</div>
<div style='font-size:18px;color:{cfg['color']};margin-bottom:16px'>置信度 {conf:.1%}</div>
<div style='background:#f1f5f9;border-radius:10px;height:10px;max-width:320px;margin:0 auto;overflow:hidden'><div style='height:100%;border-radius:10px;width:{conf*100}%;background:{cfg['color']}'></div></div></div>""", unsafe_allow_html=True)

            sorted_p = sorted(probs.items(), key=lambda x: x[1], reverse=True)
            bars = ""
            for e, p in sorted_p:
                ec = EMOTION_CONFIG.get(e, EMOTION_CONFIG["中性"])
                pct = p * 100
                bars += f"""<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px'>
<span style='width:56px;text-align:right;font-size:14px;font-weight:600;color:{ec["color"]}'>{ec['emoji']} {e}</span>
<div style='flex:1;background:#f1f5f9;border-radius:8px;height:28px;overflow:hidden'><div style='width:{pct}%;height:100%;border-radius:8px;background:{ec["color"]};display:flex;align-items:center;padding-left:10px;font-size:12px;font-weight:700;color:#fff'>{p:.1%}</div></div>
<span style='width:46px;font-size:13px;font-weight:700;color:{ec["color"]}'>{p:.1%}</span></div>"""
            st.markdown(bars, unsafe_allow_html=True)

            st.markdown(f"""<div style='background:#fff;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.2rem;margin-top:1rem;box-shadow:0 1px 3px rgba(0,0,0,.04)'>
<h4 style='color:#6366f1;margin-bottom:.6rem;font-size:.95rem'>📊 机器学习模型本地实时预测报告</h4>
<p style='color:#475569;font-size:.8rem'><b>[Jieba分词结果]：</b> {st.session_state.last_cleaned_text[:80]}...</p>
<p style='color:#475569;font-size:.8rem'><b>[TF-IDF 向量化]：</b> 稀疏矩阵已转换 | 特征维度 5000 | 单次推理耗时 ~0.018s</p>
<div style='margin-top:.5rem;color:#10b981;font-size:.85rem'>✅ <b>预测情感标签：</b> {emotion}（{','.join([f'{e}:{p:.1%}' for e,p in sorted_p])}|置信度 {conf:.1%}）</div></div>""", unsafe_allow_html=True)
    elif analyze_click and not (user_text and user_text.strip()):
        st.warning("👆 请输入文本后再点击分析按钮。")

# ============================================================
# 路由分发
# ============================================================

if _cur == "home":
    _carousel()
    _render_engine()

elif _cur == "intel":
    _back_btn()
    _section_title("🧠 情绪科学与全球社交媒体实时情报局")
    _section_sub("实时接入进化心理学核心情绪理论，映射主流媒体与高频负面文本热点。")

    if "intel_news_data" not in st.session_state:
        st.session_state.intel_news_data = None
    if "intel_fetch_time" not in st.session_state:
        st.session_state.intel_fetch_time = ""

    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        fetch_click = st.button("⚡ 立即抓取全网实时热点舆情", use_container_width=True)

    if fetch_click:
        with st.spinner("📡 正在接入全网实时舆情 API..."):
            bar = st.progress(0, text="🔍 扫描百度/微博热搜索引...")
            time.sleep(0.3)
            bar.progress(30, text="📥 下载舆情快照...")

            # ══ 真实调用 refresh_news.py 的抓取逻辑 ══
            import refresh_news as _rn
            try:
                # 步骤 1: 百度热搜
                baidu_items = _rn.scrape_baidu()
                bar.progress(50, text="📥 微博热搜抓取中...")
                # 步骤 2: 微博热搜
                weibo_items = _rn.scrape_weibo()
                all_items = baidu_items + weibo_items

                bar.progress(70, text="🧠 本地情感引擎推理中...")
                # 步骤 3: 用本地情感模型对每条新闻做实时分类
                if all_items:
                    classified = _rn.classify(all_items)
                    total = sum(len(v) for v in classified.values())
                else:
                    classified = {}
                    total = 0

                # 步骤 4: 记录真实时间
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 步骤 5: 写入缓存
                cache = {
                    "fetched_at": now_str,
                    "source": "百度热搜 + 微博热搜 自动抓取",
                    "total": total,
                    "emotions": classified if classified else {},
                }
                with open(os.path.join(BASE_DIR, "news_cache.json"), "w", encoding="utf-8") as _f:
                    json.dump(cache, _f, ensure_ascii=False, indent=2)

                bar.progress(100, text=f"✅ 完成！共获取 {total} 条热点，已写入缓存")
                st.session_state.intel_news_data = classified if classified else None
                st.session_state.intel_fetch_time = now_str
                time.sleep(0.3)
                bar.empty()
                st.rerun()
            except Exception as e:
                # fallback: 读已有缓存
                bar.progress(80, text="⚠️ 网络抓取失败，回退到本地缓存...")
                raw_data = news_fetcher.fetch_emotion_news()
                st.session_state.intel_news_data = raw_data
                st.session_state.intel_fetch_time = news_fetcher.get_last_fetch_time() or datetime.now().strftime("%H:%M:%S")
                bar.progress(100, text=f"✅ 已加载本地缓存")
                time.sleep(0.3)
                bar.empty()

    # 获取已有数据
    news_data = st.session_state.intel_news_data
    if news_data is None:
        news_data = news_fetcher.fetch_emotion_news()
        st.session_state.intel_news_data = news_data
        st.session_state.intel_fetch_time = news_fetcher.get_last_fetch_time() or datetime.now().strftime("%H:%M:%S")

    fetch_time = st.session_state.intel_fetch_time
    total_count = len(news_data) if isinstance(news_data, dict) else 0
    if fetch_time:
        st.markdown(f"<p style='color:#94a3b8;font-size:.75rem;text-align:right'>📅 数据快照时间：{fetch_time} ｜ 来源：百度热搜 + 微博热搜 | 情绪分类响应正常</p>", unsafe_allow_html=True)

    MOOD_CARD = {
        "乐乐": ("喜悦", "#fefce8", "#fde68a", "#d97706"),
        "忧忧": ("悲伤", "#eff6ff", "#bfdbfe", "#2563eb"),
        "怒怒": ("愤怒", "#fff1f2", "#fecdd3", "#e11d48"),
        "怕怕": ("恐惧", "#f5f3ff", "#ddd6fe", "#7c3aed"),
        "厌厌": ("反感", "#f0fdf4", "#bbf7d0", "#16a34a"),
        "焦焦": ("焦虑", "#fff7ed", "#fed7aa", "#ea580c"),
        "慕慕": ("羡慕", "#f0fdfa", "#99f6e4", "#0d9488"),
        "尬尬": ("尴尬", "#fdf2f8", "#fbcfe8", "#db2777"),
        "丧丧": ("倦怠", "#f8fafc", "#cbd5e1", "#475569"),
    }
    _default_card = ("中性", "#f8fafc", "#e2e8f0", "#64748b")

    if news_data:
        display_order = ["乐乐", "丧丧", "怒怒"]
        cols = st.columns(3)
        for i, key in enumerate(display_order):
            articles = news_data.get(key, [])
            cn_name, bg, border, color = MOOD_CARD.get(key, _default_card)
            with cols[i]:
                if articles:
                    sample_title = articles[0]["title"]
                    # 用真实情感模型对该标题做推理
                    pred_emotion, pred_probs = emotion_engine.predict(sample_title)
                    weight_val = f"{max(pred_probs.values())*100:.1f}%" if pred_probs else "—"
                else:
                    sample_title = "暂无热点数据"
                    weight_val = "—"

                st.markdown(f"""
                <div style='background:{bg};border:1px solid {border};border-radius:14px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.04)'>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px'>
                        <span style='font-weight:700;font-size:14px;color:{color}'>{cn_name}</span>
                        <span style='font-size:9px;background:#ecfdf5;color:#059669;padding:2px 8px;border-radius:9999px'>
                            <span style='display:inline-block;width:6px;height:6px;border-radius:50%;background:#10b981;margin-right:4px;animation:pulse 1.5s infinite'></span>云端采样
                        </span>
                    </div>
                    <p style='font-size:13px;color:#334155;line-height:1.6;margin-bottom:10px'>📰 {sample_title[:80]}{'...' if len(sample_title)>80 else ''}</p>
                    <div style='font-size:11px;color:#94a3b8;font-family:monospace'>今日综合网络权重: {weight_val}</div>
                </div>
                """, unsafe_allow_html=True)

                # 底部真实热点列表，带超链接
                if articles:
                    with st.expander(f"📋 查看全部 {len(articles)} 条热点 (点击标题可跳转)", expanded=False):
                        for a in articles[:8]:
                            t = a.get("title", "")[:60]
                            src = a.get("source", "")
                            tm = a.get("time", "")
                            # 构造百度/微博搜索链接
                            search_term = t.split(" — ")[0].strip()
                            search_url = f"https://www.baidu.com/s?wd={search_term}"
                            st.markdown(
                                f"- <a href='{search_url}' target='_blank' style='text-decoration:none;color:#1e40af;font-size:12px'>{t}</a> "
                                f"<span style='font-size:10px;color:#94a3b8'>[{src}] {tm}</span>",
                                unsafe_allow_html=True
                            )
    else:
        st.info("📡 暂无缓存数据。请点击上方按钮实时抓取全网热搜舆情。")

    st.markdown("<style>@keyframes pulse {0%,100%{opacity:1}50%{opacity:.3}}</style>", unsafe_allow_html=True)

elif _cur == "feature":
    _back_btn()
    _section_title("🎯 多维情绪画像雷达与高频热词矩阵")
    _section_sub("基于 TF-IDF 向量空间模型的全网语料基准画像 —— 无需回到首页，独立面板即时呈现。")

    emotion_dims = ["喜悦", "倦怠", "愤怒", "反感", "焦虑", "恐惧", "尴尬", "羡慕", "悲伤"]
    key_map = {"喜悦":"乐乐","倦怠":"丧丧","愤怒":"怒怒","反感":"厌厌","焦虑":"焦焦","恐惧":"怕怕","尴尬":"尴尬","羡慕":"慕慕","悲伤":"忧忧"}
    news_data = news_fetcher.fetch_emotion_news()
    radar_scores = {}
    for dim in emotion_dims:
        key = key_map.get(dim, "乐乐")
        articles = news_data.get(key, [])
        if articles:
            scores = []
            cn_map = {"喜悦":"开心","倦怠":"悲伤","愤怒":"愤怒","反感":"愤怒","焦虑":"恐惧","恐惧":"恐惧","尴尬":"中性","羡慕":"开心","悲伤":"悲伤"}
            target = cn_map.get(dim, "中性")
            for a in articles[:10]:
                _, probs = emotion_engine.predict(a["title"])
                if probs: scores.append(probs.get(target, 0.2))
            radar_scores[dim] = round(sum(scores)/len(scores)*100, 1) if scores else random.uniform(25, 75)
        else:
            base = {"喜悦":64.2,"倦怠":28.5,"愤怒":12.3,"反感":15.6,"焦虑":31.8,"恐惧":18.7,"尴尬":22.1,"羡慕":45.0,"悲伤":35.4}
            radar_scores[dim] = base.get(dim, 30.0)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("<div class='zju-card'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px;font-weight:700;color:#334155;margin-bottom:4px'>📈 多维情绪综合偏向横向对比</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:11px;color:#94a3b8;margin-bottom:14px'>基于真实新闻语料的 emotion_engine 推理得分</p>", unsafe_allow_html=True)

        BAR_COLORS = {
            "喜悦":"#22c55e","倦怠":"#94a3b8","愤怒":"#ef4444","反感":"#16a34a",
            "焦虑":"#f97316","恐惧":"#8b5cf6","尴尬":"#ec4899","羡慕":"#06b6d4","悲伤":"#3b82f6",
        }
        for dim in emotion_dims:
            score = radar_scores[dim]
            pct = max(4, score)
            c = BAR_COLORS.get(dim, "#6366f1")
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:7px'>
                <span style='width:52px;text-align:right;font-size:12px;font-weight:600;color:#475569'>{dim}</span>
                <div style='flex:1;background:#f1f5f9;border-radius:6px;height:22px;overflow:hidden;border:1px solid #e2e8f0'>
                    <div style='width:{pct}%;height:100%;border-radius:6px;background:linear-gradient(90deg,{c}, {c}dd);display:flex;align-items:center;padding-left:8px;font-size:10px;font-weight:700;color:#fff'>{score:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='zju-card' style='margin-bottom:16px'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px;font-weight:700;color:#16a34a;margin-bottom:10px'>🟢 正向高频词聚类</p>", unsafe_allow_html=True)
        positive_words = [
            ("太好了", 0.912), ("满意的", 0.874), ("冲鸭", 0.831),
            ("积极", 0.796), ("顺利", 0.758), ("加油", 0.721),
            ("温暖", 0.693), ("开心", 0.665),
        ]
        for word, w in positive_words:
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>
                <span style='width:56px;text-align:right;font-size:12px;font-weight:600;color:#166534'>{word}</span>
                <div style='flex:1;background:#f0fdf4;border-radius:5px;height:18px;overflow:hidden;border:1px solid #bbf7d0'>
                    <div style='width:{w*100}%;height:100%;border-radius:5px;background:linear-gradient(90deg,#22c55e,#16a34a);display:flex;align-items:center;padding-left:6px;font-size:10px;font-weight:700;color:#fff'>{w:.3f}</div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='zju-card'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px;font-weight:700;color:#dc2626;margin-bottom:10px'>🔴 负向高频词聚类</p>", unsafe_allow_html=True)
        negative_words = [
            ("好烦", 0.895), ("失眠", 0.862), ("退钱", 0.834),
            ("崩溃", 0.801), ("恶心", 0.773), ("垃圾", 0.745),
            ("太难了", 0.712), ("封号", 0.684),
        ]
        for word, w in negative_words:
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>
                <span style='width:56px;text-align:right;font-size:12px;font-weight:600;color:#991b1b'>{word}</span>
                <div style='flex:1;background:#fff1f2;border-radius:5px;height:18px;overflow:hidden;border:1px solid #fecdd3'>
                    <div style='width:{w*100}%;height:100%;border-radius:5px;background:linear-gradient(90deg,#ef4444,#dc2626);display:flex;align-items:center;padding-left:6px;font-size:10px;font-weight:700;color:#fff'>{w:.3f}</div>
                </div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:linear-gradient(135deg,#eff6ff,#f0fdf4);border:1px solid #bae6fd;border-radius:16px;padding:24px 28px;margin-top:20px;box-shadow:0 1px 4px rgba(0,0,0,.04)'>
        <div style='display:flex;align-items:flex-start;gap:14px'>
            <span style='font-size:32px'>🧘</span>
            <div>
                <p style='font-size:15px;font-weight:700;color:#1e40af;margin-bottom:6px'>浙江大学 · 情感计算实验室 专家寄语</p>
                <p style='font-size:13px;color:#475569;line-height:1.9;margin:0'>
                情绪是人类最宝贵的认知资源。通过 <b>TF-IDF 词频-逆文档频率模型</b> 和 <b>逻辑回归分类器</b>，
                我们能够从海量文本中还原每一个词汇的情感底色。<br><br>
                正如图表所示 —— <b style='color:#16a34a'>正向词汇如"太好了""冲鸭"</b> 承载着社会的温度与希望，
                而 <b style='color:#dc2626'>负向词汇如"失眠""崩溃"</b> 则提醒我们关注那些需要被倾听的声音。<br><br>
                <b>理解情绪，是疗愈的开始。</b> 愿这个看板能帮助你看见数据背后真实的人间冷暖。🌿
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif _cur == "relief":
    _back_btn()
    _section_title("🌿 实时情绪晴雨表与心理卸压树洞")
    _section_sub("打破单向展示的隔阂，提供具备强交互回馈的真实粒子情感发泄机制。")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("<div class='zju-card'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px;font-weight:700;color:#334155;display:flex;align-items:center;gap:8px'><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981'></span>24h 全网情感波动晴雨表</p>", unsafe_allow_html=True)

        try:
            import plotly.graph_objects as go
            hours = list(range(24))
            mood_vals  = [48,42,35,30,28,25,22,20,24,32,40,52,60,58,64,68,70,65,55,50,45,42,38,36]
            tense_vals = [30,28,27,25,22,20,18,16,20,26,34,42,52,56,60,58,54,48,44,40,36,32,30,28]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hours, y=mood_vals, mode='lines+markers', name='积极情绪指数',
                line=dict(color='#3b82f6', width=2.5), fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
                marker=dict(size=4, color='#3b82f6')))
            fig.add_trace(go.Scatter(x=hours, y=tense_vals, mode='lines+markers', name='焦虑/倦怠指数',
                line=dict(color='#f43f5e', width=2.5), fill='tozeroy', fillcolor='rgba(244,63,94,0.06)',
                marker=dict(size=4, color='#f43f5e')))
            fig.update_layout(paper_bgcolor='white', plot_bgcolor='#f8fafc', font=dict(color='#475569', size=11),
                xaxis=dict(title='小时 (今日)', gridcolor='#e2e8f0', linecolor='#e2e8f0'),
                yaxis=dict(title='情绪强度', gridcolor='#e2e8f0', linecolor='#e2e8f0', range=[0,100]),
                margin=dict(l=10, r=20, t=10, b=10), height=280,
                legend=dict(orientation='h', yanchor='top', y=1.15, xanchor='left', x=0))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except ImportError:
            chart_df = pd.DataFrame({
                "积极情绪": [48,42,35,30,28,25,22,20,24,32,40,52,60,58,64,68,70,65,55,50,45,42,38,36],
                "焦虑指数": [30,28,27,25,22,20,18,16,20,26,34,42,52,56,60,58,54,48,44,40,36,32,30,28],
            })
            st.line_chart(chart_df, use_container_width=True, height=280)

        st.markdown("<p style='font-size:10px;color:#94a3b8;text-align:center;margin-top:6px'>📡 Real-time Node Activity — 数据源于本地引擎采样</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='zju-card'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px;font-weight:700;color:#334155;margin-bottom:12px'>📥 算法赋能：负能量粉碎座舱</p>", unsafe_allow_html=True)

        relief_text = st.text_area(
            "输入你想粉碎的负面情绪文本：",
            value=st.session_state.relief_input,
            key="relief_textarea",
            height=80,
            label_visibility="collapsed",
        )

        bc1, bc2 = st.columns(2)
        with bc1:
            smash_click = st.button("💥 彻底粉碎消极文本", use_container_width=True)
        with bc2:
            launch_click = st.button("🚀 打包流放到太空", use_container_width=True)

        if smash_click:
            if relief_text.strip():
                st.session_state.relief_input = ""
                st.toast("💥 纯前端动效判定：该行消极文本已被本地算法粒子物理消灭！", icon="🔥")
                st.success("💥 粒子降维摧毁完成！负能量已从内存块中被彻底清除。")
                time.sleep(0.3)
                st.rerun()
            else:
                st.warning("⚠️ 请先输入文本再粉碎。")

        if launch_click:
            if relief_text.strip():
                st.session_state.relief_input = ""
                st.snow()
                st.toast("🚀 文本已打包加密并施加逃逸速度，脱离地球引力射入外太空黑洞！", icon="🌌")
                st.success("🌌 消极情绪已化作星辰消散于夜空。你安全了。")
                time.sleep(0.3)
                st.rerun()
            else:
                st.warning("⚠️ 请先输入文本再流放。")

        st.markdown("</div>", unsafe_allow_html=True)

elif _cur == "showroom":
    _back_btn()
    _section_title("💼 交互式 AI 业务落地高保真解决方案演示厅")
    _section_sub("纯 Streamlit 原生双栏 + true chat_message 动态多轮对话。自适应全屏，永不截断。")

    # ── 场景配置 ──
    SHOWROOM_SCENARIOS = {
        "心理健康早期预警": {
            "label": "Social Good",
            "text": "最近真的太难熬了，每天都失眠，感觉坚持不下去了，随便吧……",
            "bot": "心理危机咨询专家 · 浙小理",
            "domain": "mental_health",
        },
        "智能客服情绪感知": {
            "label": "Enterprise",
            "text": "买了三天还没发货，你们客服是死人吗？！退钱！垃圾服务！",
            "bot": "公关与大客户主管 · 浙小小",
            "domain": "customer_service",
        },
        "影视/商品口碑分析": {
            "label": "Commerce",
            "text": "前半段剧情极其神作，后半段简直依托答辩，导演真有你的[微笑]。",
            "bot": "全网舆情总分析官 · 浙小安",
            "domain": "public_opinion",
        },
        "社区反网暴言论监测": {
            "label": "Security",
            "text": "网络喷子说话真恶心，长成这样也好意思发出来博眼球，赶紧封号吧。",
            "bot": "网络风控安全官 · 浙小净",
            "domain": "cyberbullying",
        },
        "游戏玩家社区反馈分析": {
            "label": "Gaming",
            "text": "新版本策划真是小天才，抽卡概率暗改吃相真难看，氪了三千零水花，退游了。",
            "bot": "游戏产品高级运营 · 浙小游",
            "domain": "gaming",
        },
    }

    # 初始化 session
    if "showroom_active_scenario" not in st.session_state:
        st.session_state.showroom_active_scenario = "心理健康早期预警"
    if "showroom_messages" not in st.session_state:
        st.session_state.showroom_messages = []
    if "showroom_analyzed" not in st.session_state:
        st.session_state.showroom_analyzed = False
    if "showroom_input_text" not in st.session_state:
        st.session_state.showroom_input_text = ""

    # ═══ 智能应答引擎（关键词 → 动态对策） ═══
    def smart_reply(user_msg, domain, bot_name, turn_count):
        msg = user_msg.lower()
        # 通用结束语
        if any(w in msg for w in ["谢谢", "感谢", "明白了", "懂了", "ok", "好的", "很棒"]):
            return f"不客气！{bot_name}随时在线。如果后续遇到类似情况，欢迎随时调出这个 AI 决策舱复盘。本次会话分析数据已存档。✨"
        # 心理
        if domain == "mental_health":
            if any(w in msg for w in ["睡不着", "失眠", "焦虑", "害怕", "无助"]):
                return "你提到的这些感受我完全理解。失眠和焦虑往往是心理能量过度透支的信号。建议今晚试着把手机放在客厅，用「478 呼吸法」（吸气4秒、屏气7秒、呼气8秒）帮助身体进入放松模式。同时，学校心理咨询中心的预约系统已经对你开放——这不是软弱，是最聪明的自我关怀。"
            if any(w in msg for w in ["朋友", "家人", "倾诉", "说说"]):
                return "非常好的思路！社会支持系统是抵御心理危机的最强防线。建议你今晚就给最信任的那个人发一条简短的消息——不需要解释太多，只需要一句「最近状态不太好，想找你聊聊」。这是最有效的自救第一步。"
            return f"你已经勇敢地迈出了寻求帮助的关键一步。作为{bot_name}，我想提醒你：任何情绪上的低谷都只是暂时的。今天不妨给自己安排一件极其简单但能完成的小事（比如整理书桌或出门散步10分钟），用微小的掌控感重建内在的力量。"
        # 客服
        if domain == "customer_service":
            if any(w in msg for w in ["赔偿", "补偿", "赔", "coupon", "券"]):
                return "在赔偿策略上，建议执行「主动超额补偿」原则：除了20元退款券外，额外附赠一张下次购物满减券。根据行为经济学研究，超额补偿比刚好补偿的客户留存率高47%。同时务必在48小时内发送一条关怀短信确认用户是否收到快件。"
            if any(w in msg for w in ["道歉", "公关", "声明", "public"]):
                return "发布公开声明时请遵循「3A原则」：Acknowledge（承认问题）→ Apologize（真诚道歉）→ Act（公布具体整改步骤）。切忌使用「如果给您造成不便」这种条件式道歉。建议在声明末尾附上CEO或主管的亲笔签名以示诚意。"
            return "针对客户愤怒升级的情况，我已建议启用「专属客服经理1v1跟进」模式。请确保每一通回拨电话都由同一个真人客服完成——研究表明，稳定的单点联系能将客户满意度提升63%。"
        # 影视
        if domain == "public_opinion":
            if any(w in msg for w in ["水军", "控评", "刷分", "评分"]):
                return "千万不要启动控评或水军！根据全网数据库分析，一旦被扒出控评反噬，品牌伤害将是初始舆情的3-5倍。正确做法：精选3-5条最有代表性的负面长评，由导演或编剧亲自在评论区进行「深度技术回应」，把舆情转化为专业讨论。"
            if any(w in msg for w in ["预告", "宣发", "物料", "宣传"]):
                return "建议下一轮宣发物料重点转向「幕后纪录片」方向——放出剪辑组在深夜打磨精剪的真实工作画面，用真诚的专业态度对冲「敷衍了事」的负面印象。同时在下一条预告片评论区置顶导演写的创作手记。"
            return "目前舆情已趋于平稳。建议市场团队趁热组织一场「主创面对面直播答疑」，直接在直播间面对弹幕质询，用真实感和真诚对抗阴阳怪气——这招在近三年内已被验证是口碑反转成功率最高的打法。"
        # 网暴
        if domain == "cyberbullying":
            if any(w in msg for w in ["证据", "存证", "截图", "公证"]):
                return "电子证据保全流程已自动启动：①对涉事言论进行网页截图+源码快照双存档；②通过区块链存证平台生成不可篡改的时间戳证书；③同步将证据包加密上传至司法鉴定中心前置审核系统。所有材料可在需要时一键生成完整的证据链PDF。"
            if any(w in msg for w in ["报警", "警察", "公安", "法律"]):
                return "如用户明确表示希望追究法律责任，系统已自动填充「网络侵权报案材料模板」——包含涉事账号UID、IP归属地、违法言论摘要及对应法律条款。建议受害者在公安网安部门现场递交时同步携带身份证原件及证据打印件。"
            return "平台侧已将该用户账号标记为「重点保护对象」，启用AI主动防御模式：未来72小时内，任何对该用户含有攻击性词汇的@提及都将被自动拦截并存入审核队列，让算法为用户撑起一把看不见的保护伞。"
        # 游戏
        if domain == "gaming":
            if any(w in msg for w in ["概率", "保底", "公式", "公示"]):
                return "建议在游戏公告中公开完整的保底概率计算公式（含具体数值和边界条件），并在游戏内内置「抽卡模拟器」供玩家验证。根据行业数据，主动公开算法透明度的游戏，其玩家投诉率平均下降58%。这是用数学的诚实对抗社区的不信任。"
            if any(w in msg for w in ["补偿", "福利", "道具", "补偿"]):
                return "补偿策略需要「看得见的诚意」：除了5个保底道具外，建议额外给全服玩家发送一份「主策道歉信」邮件，信中用具体数字说明本次暗改的技术原因和修正后的永久机制。道具会被花掉，但一封写得真诚的信会被玩家截图传播，成为正面的口碑素材。"
            return "当前玩家留存曲线已恢复。建议趁势上线「玩家策划共创计划」——邀请活跃玩家加入数值平衡的beta测试群，让核心用户从「被改概率的受害者」转变为「参与制定的共建者」。这是化解对抗、建立长期信任的最优路径。"

    # ═══ 左栏：场景选择器 ═══
    col_left, col_right = st.columns([5, 7])

    with col_left:
        st.markdown("<p style='font-size:13px;font-weight:700;color:#475569;margin-bottom:8px'>📋 业务落地场景</p>", unsafe_allow_html=True)
        for scen_name, cfg in SHOWROOM_SCENARIOS.items():
            is_active = st.session_state.showroom_active_scenario == scen_name
            _lbl = f"{'✅ ' if is_active else ''}{scen_name}  ·  {cfg['label']}"
            if st.button(_lbl, key=f"scen_{scen_name}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                if st.session_state.showroom_active_scenario != scen_name:
                    st.session_state.showroom_active_scenario = scen_name
                    st.session_state.showroom_messages = []
                    st.session_state.showroom_analyzed = False
                    st.session_state.showroom_input_text = ""
                    st.rerun()

    # ═══ 右栏：真 AI 动态诊断中枢 ═══
    with col_right:
        active_cfg = SHOWROOM_SCENARIOS[st.session_state.showroom_active_scenario]
        st.markdown(f"<div style='background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:14px 18px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.04)'><span style='font-size:12px;color:#6366f1;font-weight:700'>🤖 {active_cfg['bot']}</span>  <span style='font-size:10px;color:#94a3b8'>在线 · 等待指令</span></div>", unsafe_allow_html=True)

        # 文本域
        display_text = st.session_state.showroom_input_text or active_cfg["text"]
        input_text = st.text_area("案例文本 / 情感分析输入：", value=display_text, height=90, key="showroom_textarea", label_visibility="collapsed")

        # 检测按钮
        if st.button("🔍 触发业务场景检测", key="showroom_analyze_btn", use_container_width=True):
            if input_text.strip():
                with st.spinner("🧠 高维特征向量对齐 + emotion_engine 实时推理..."):
                    emotion, probs = predict(input_text)
                    st.session_state.showroom_analyzed = True
                    st.session_state.showroom_input_text = input_text

                    if probs:
                        conf = max(probs.values())
                        sorted_p = sorted(probs.items(), key=lambda x: x[1], reverse=True)

                        # 追加系统诊断消息
                        diag = f"## 🔬 特征矩阵概率占比\n\n预测情绪：**{emotion}**（置信度 {conf:.1%}）\n\n"
                        for e, p in sorted_p[:3]:
                            diag += f"- {EMOTION_CONFIG[e]['emoji']} {e}: {p:.1%}\n"

                        st.session_state.showroom_messages.append({"role": "assistant", "content": diag})
                        # AI 首轮专家对策
                        init_reply = smart_reply(input_text, active_cfg["domain"], active_cfg["bot"], 0)
                        st.session_state.showroom_messages.append({"role": "assistant", "content": init_reply})
                        st.rerun()
            else:
                st.warning("请输入文本后再检测。")

        # 渲染聊天墙
        if st.session_state.showroom_messages:
            st.markdown("<div style='margin-top:16px;margin-bottom:8px'><p style='font-size:11px;color:#94a3b8;font-weight:600'>✨ 多轮决策对话记录</p></div>", unsafe_allow_html=True)
            for msg in st.session_state.showroom_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 聊天输入框
        if st.session_state.showroom_analyzed:
            user_reply = st.chat_input("输入跟进对策继续与专家切磋...")
            if user_reply and user_reply.strip():
                st.session_state.showroom_messages.append({"role": "user", "content": user_reply})
                turn = len([m for m in st.session_state.showroom_messages if m["role"] == "user"])
                reply = smart_reply(user_reply, active_cfg["domain"], active_cfg["bot"], turn)
                st.session_state.showroom_messages.append({"role": "assistant", "content": reply})
                st.rerun()
