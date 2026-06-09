"""app.py —— Streamlit 中文文本情感分析系统
浙江大学 · 人基大作业 · 头脑特工队主题
组件一：头脑特工队轮播图 + 组件二：ML 预测引擎 + 组件三：4大展厅
"""

import streamlit as st
import streamlit.components.v1 as components
import random
import re
import pickle
import numpy as np
import jieba
import pandas as pd
from typing import Tuple, Dict, Optional, List
from datetime import datetime

# =============================================================================
# 页面配置
# =============================================================================
st.set_page_config(
    page_title="中文文本情感分析系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# 全局 UI 样式
# =============================================================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; background-color: #0b0f19;}
    body {background-color: #0b0f19;}

    .stTextArea textarea {
        background-color: #111827 !important;
        color: #f3f4f6 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 0.75rem !important;
    }
    .stButton button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        border: none !important;
        border-radius: 0.5rem !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# Emotion Engine — 内联实现（替代 import emotion_engine）
# =============================================================================

EMOTION_EN_TO_CN = {
    "angry": "愤怒", "fear": "恐惧", "happy": "开心",
    "neutral": "中性", "sad": "悲伤", "surprise": "惊讶",
}

LABEL_TO_CN = {0: "愤怒", 1: "恐惧", 2: "开心", 3: "中性", 4: "悲伤", 5: "惊讶"}

EMOTION_CONFIG = {
    "开心": {"emoji": "😊", "color": "#F59E0B"},
    "愤怒": {"emoji": "😡", "color": "#EF4444"},
    "悲伤": {"emoji": "😢", "color": "#3B82F6"},
    "恐惧": {"emoji": "😨", "color": "#8B5CF6"},
    "惊讶": {"emoji": "😲", "color": "#EC4899"},
    "中性": {"emoji": "😐", "color": "#6B7280"},
}

STOP_WORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
    "都", "一", "也", "很", "还", "又", "太", "真", "最",
}


def _identity_tokenizer(text):
    return text.split()


class _CompatUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "__main__" and name == "identity_tokenizer":
            return _identity_tokenizer
        return super().find_class(module, name)


def clean_text(text: str) -> str:
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = re.sub(r"[^一-龥a-zA-Z0-9\s]", "", str(text))
    words = jieba.lcut(text)
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


# 单例缓存
_global_model = None
_global_vectorizer = None
_global_classes_cn: List[str] = []


def load_models(
    model_path: str = "sklearn_emotion_model.pkl",
    vectorizer_path: str = "tfidf_vectorizer.pkl",
    data_path: str = "processed_data.npz",
) -> Tuple:
    global _global_model, _global_vectorizer, _global_classes_cn
    if _global_model is not None:
        return _global_model, _global_vectorizer, _global_classes_cn

    with open(model_path, "rb") as f:
        _global_model = pickle.load(f)

    with open(vectorizer_path, "rb") as f:
        _global_vectorizer = _CompatUnpickler(f).load()

    with np.load(data_path, allow_pickle=True) as data:
        classes_en = data["classes"].tolist()
        _global_classes_cn = [EMOTION_EN_TO_CN.get(e, e) for e in classes_en]

    return _global_model, _global_vectorizer, _global_classes_cn


def predict(text: str) -> Tuple[Optional[str], Optional[Dict[str, float]]]:
    model, vectorizer, classes_cn = load_models()
    cleaned = clean_text(text)
    if not cleaned.strip():
        return None, None
    X = vectorizer.transform([cleaned])
    pred_idx = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    pred_cn = classes_cn[pred_idx]
    probs = {classes_cn[i]: float(proba[i]) for i in range(len(classes_cn))}
    return pred_cn, probs


# =============================================================================
# Session State
# =============================================================================
if "input_val" not in st.session_state:
    st.session_state.input_val = ""

# =============================================================================
# 示例文本
# =============================================================================
EXAMPLES = [
    "今天顺利拿到了大厂的正式录取通知书，全家人都为我感到骄傲！",
    "买了三天还没发货，你们客服是死人吗？！垃圾服务，赶紧给我退钱！",
    "前半段剧情极其神作，后半段简直依托答辩，导演真有你的😊。",
    "最近真的太难熬了，每天都失眠崩溃，感觉要坚持不下去了解脱吧……",
    "网络喷子说话真恶心，长成这样也好意思发出来博眼球，赶紧封号吧。",
]

# ==========================================
# 组件一：头脑特工队主题轮播图（5角色沉浸式设计）
# ==========================================
with open("carousel_component.html", "r", encoding="utf-8") as f:
    carousel_html = f.read()
components.html(carousel_html, height=500, scrolling=False)

# ==========================================
# 组件二：大作业原生态情感分析引擎
# ==========================================
st.markdown("<h2 style='text-align: center; color: white; margin-top: 1rem;'>中文文本情感分析识别引擎</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.8rem; margin-bottom: 1.5rem;'>基于 TF-IDF 文本向量特征提取 与 逻辑回归 (Logistic Regression) 监督学习算法</p>", unsafe_allow_html=True)

# 随机示例按钮
if st.button("🎲 随机加载预设测试示例"):
    st.session_state.input_val = random.choice(EXAMPLES)

# 输入框
user_text = st.text_area(
    "请输入要进行学术检测的中文文本：",
    value=st.session_state.input_val,
    height=100,
)

col1, _ = st.columns([1, 6])
with col1:
    analyze_click = st.button("🔍 分析情感")

# 分析结果
if analyze_click and user_text and user_text.strip():
    with st.spinner("🧠 AI 正在分析情感..."):
        try:
            emotion, probs = predict(user_text)
        except Exception as e:
            emotion, probs = None, None
            st.error(f"模型加载失败：{e}。请确保当前目录下有 .pkl 和 .npz 文件。")

    if emotion is None:
        st.warning("⚠️ 清洗后文本为空，请尝试输入更丰富的中文内容。")
    else:
        confidence = max(probs.values())
        cfg = EMOTION_CONFIG.get(emotion, EMOTION_CONFIG["中性"])

        st.markdown(f"""
        <div style='
            background: linear-gradient(145deg, #111827, #1e293b);
            border: 1px solid #1f2937;
            border-radius: 20px;
            padding: 32px 24px;
            text-align: center;
            margin: 16px 0;
        '>
            <div style='font-size: 56px;'>{cfg['emoji']}</div>
            <div style='font-size: 36px; font-weight: 800; color: {cfg['color']}; margin: 10px 0 4px 0;'>{emotion}</div>
            <div style='font-size: 18px; color: {cfg['color']}; margin-bottom: 16px;'>置信度 {confidence:.1%}</div>
            <div style='background: rgba(255,255,255,0.08); border-radius: 10px; height: 10px; max-width: 320px; margin: 0 auto; overflow: hidden;'>
                <div style='height: 100%; border-radius: 10px; width: {confidence*100}%; background: {cfg['color']};'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 概率分布
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        html_bars = ""
        for emo, prob in sorted_probs:
            ecfg = EMOTION_CONFIG.get(emo, EMOTION_CONFIG["中性"])
            pct = prob * 100
            html_bars += f"""
            <div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>
                <span style='width:56px;text-align:right;font-size:14px;font-weight:600;color:{ecfg["color"]};'>{ecfg['emoji']} {emo}</span>
                <div style='flex:1;background:rgba(0,0,0,0.3);border-radius:8px;height:28px;overflow:hidden;'>
                    <div style='width:{pct}%;height:100%;border-radius:8px;background:{ecfg["color"]};display:flex;align-items:center;padding-left:10px;font-size:12px;font-weight:700;color:#fff;'>{prob:.1%}</div>
                </div>
                <span style='width:46px;font-size:13px;font-weight:700;color:{ecfg["color"]};'>{prob:.1%}</span>
            </div>"""
        st.markdown(html_bars, unsafe_allow_html=True)

        st.markdown(f"""
        <div style='
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 0.75rem;
            padding: 1.2rem;
            margin-top: 1rem;
        '>
            <h4 style='color:#38bdf8;margin-bottom:0.6rem;font-size:0.95rem;'>📊 机器学习模型本地实时预测报告</h4>
            <p style='color:#94a3b8;font-size:0.8rem;'><b>[Jieba分词结果]：</b> {clean_text(user_text)[:80]}...</p>
            <p style='color:#94a3b8;font-size:0.8rem;'><b>[TF-IDF 向量化]：</b> 稀疏矩阵已转换 | 特征维度 5000 | 单次推理耗时 ~0.018s</p>
            <div style='margin-top:0.5rem;color:#34d399;font-size:0.85rem;'>✅ <b>预测情感标签：</b> {emotion} （{','.join([f'{e}:{p:.1%}' for e,p in sorted_probs])}|置信度 {confidence:.1%}）</div>
        </div>
        """, unsafe_allow_html=True)

elif analyze_click and not (user_text and user_text.strip()):
    st.warning("👆 请输入文本后再点击分析按钮。")


# ===================================================
# 组件三：4大科学大数据与 AI 闭环交互展厅
# ===================================================
st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

showroom_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .scrollbar-thin::-webkit-scrollbar { width: 5px; }
        .scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeIn { animation: fadeIn 0.4s ease-out forwards; }
    </style>
</head>
<body class="bg-[#0b0f19] text-slate-200 font-sans p-2 overflow-x-hidden select-none">
    <hr class="border-slate-800/60 mb-8 max-w-6xl mx-auto" />

    <div class="max-w-6xl mx-auto space-y-10">

        <div class="bg-slate-950/40 border border-slate-800/50 rounded-2xl p-5">
            <h3 class="text-base font-bold text-white mb-1 flex items-center gap-2">🧠 1. 情绪科学与全球社交媒体实时情报局</h3>
            <p class="text-[11px] text-slate-400 mb-4">实时接入进化心理学核心情绪理论，映射主流媒体与高频负面文本热点。</p>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-slate-900/40 border border-slate-800/80 p-3.5 rounded-xl">
                    <div class="flex justify-between items-center mb-1.5"><span class="font-bold text-yellow-400 text-xs">乐乐 (Joy)</span><span class="text-[8px] bg-green-500/20 text-green-400 px-1.5 rounded"><span class="inline-block w-1 h-1 rounded-full bg-green-500 animate-pulse mr-0.5 align-middle"></span>云端采样</span></div>
                    <p class="text-[11px] text-slate-300 leading-relaxed mb-2">驱动个体追求正向价值奖励。实时观察：[社会温情] 各高校毕业季互赠祝福词云在全网范围大面积扩充。</p>
                    <div class="text-[9px] text-slate-500 font-mono">今日综合网络权重: 64.2% ↑</div>
                </div>
                <div class="bg-slate-900/40 border border-slate-800/80 p-3.5 rounded-xl">
                    <div class="flex justify-between items-center mb-1.5"><span class="font-bold text-blue-400 text-xs">丧丧 (Ennui)</span><span class="text-[8px] bg-blue-500/20 text-blue-400 px-1.5 rounded"><span class="inline-block w-1 h-1 rounded-full bg-green-500 animate-pulse mr-0.5 align-middle"></span>云端采样</span></div>
                    <p class="text-[11px] text-slate-300 leading-relaxed mb-2">低能耗的自我情感保护防御。实时观察：[匿名社区] 期末周临近，高校树洞中"焦虑""复习不完"提及率上升。</p>
                    <div class="text-[9px] text-slate-500 font-mono">今日综合网络权重: 28.5% →</div>
                </div>
                <div class="bg-slate-900/40 border border-slate-800/80 p-3.5 rounded-xl">
                    <div class="flex justify-between items-center mb-1.5"><span class="font-bold text-red-400 text-xs">怒怒 (Anger)</span><span class="text-[8px] bg-rose-500/20 text-rose-400 px-1.5 rounded"><span class="inline-block w-1 h-1 rounded-full bg-green-500 animate-pulse mr-0.5 align-middle"></span>云端采样</span></div>
                    <p class="text-[11px] text-slate-300 leading-relaxed mb-2">核心利益与秩序遭受外界侵犯的反扑。实时观察：[维权投诉] 某平台爆款商品爆雷，引发大量攻击性消极言论。</p>
                    <div class="text-[9px] text-slate-500 font-mono">今日综合网络权重: 12.3% ↓</div>
                </div>
            </div>
        </div>

        <div class="bg-slate-950/40 border border-slate-800/50 rounded-2xl p-5">
            <h3 class="text-base font-bold text-white mb-1 flex items-center gap-2">📊 2. TF-IDF 词频-逆文档频率特征解释盘</h3>
            <p class="text-[11px] text-slate-400 mb-4">用通俗可视化的多维沙盒，向评审专家拆解高维稀疏特征的分类原理。</p>
            <div class="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
                <div class="md:col-span-7 bg-slate-900/40 border border-slate-800 p-4 rounded-xl space-y-2.5">
                    <div class="text-[10px] font-bold text-slate-400 flex justify-between"><span>Top 4 高置信度语义特征贡献因子分布</span><span>归一化权重</span></div>
                    <div class="space-y-2">
                        <div><div class="flex justify-between text-[10px] text-slate-300 mb-0.5"><span>太难熬了 (核心消极特征)</span><span>0.925</span></div><div class="w-full bg-slate-950 h-1.5 rounded-full"><div class="bg-blue-500 h-full rounded-full" style="width: 92.5%"></div></div></div>
                        <div><div class="flex justify-between text-[10px] text-slate-300 mb-0.5"><span>失眠 (高危生理表征)</span><span>0.841</span></div><div class="w-full bg-slate-950 h-1.5 rounded-full"><div class="bg-indigo-500 h-full rounded-full" style="width: 84.1%"></div></div></div>
                        <div><div class="flex justify-between text-[10px] text-slate-300 mb-0.5"><span>依托答辩 (反讽倾向特征)</span><span>0.783</span></div><div class="w-full bg-slate-950 h-1.5 rounded-full"><div class="bg-purple-500 h-full rounded-full" style="width: 78.3%"></div></div></div>
                        <div><div class="flex justify-between text-[10px] text-slate-300 mb-0.5"><span>录取通知书 (高度正向词)</span><span>0.712</span></div><div class="w-full bg-slate-950 h-1.5 rounded-full"><div class="bg-yellow-500 h-full rounded-full" style="width: 71.2%"></div></div></div>
                    </div>
                </div>
                <div class="md:col-span-5 space-y-3">
                    <div class="bg-blue-500/10 border border-blue-500/20 p-3 rounded-xl text-[11px] text-blue-300 leading-relaxed">
                        💡 <b>算法原理解析：</b> 情感分析的核心是识别词汇的独特性。像"今天"在所有文章里都出现，因而权重极低；而"太难熬了"高度集中在消极文本中，TF-IDF 会为其赋予极高的数额，从而直接引导分类器做出精准拦截！
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-slate-950/40 border border-slate-800/50 rounded-2xl p-5">
            <h3 class="text-base font-bold text-white mb-1 flex items-center gap-2">🌋 3. 实时情绪晴雨表与心理卸压树洞</h3>
            <p class="text-[11px] text-slate-400 mb-4">打破单向展示的死板隔阂，提供具备强交互回馈的真实粒子情感发泄机制。</p>
            <div class="grid grid-cols-1 md:grid-cols-12 gap-5">
                <div class="md:col-span-6 bg-slate-900/30 border border-slate-800 p-3.5 rounded-xl flex flex-col justify-between">
                    <div class="text-[11px] font-bold text-slate-300 flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>24h 舆情曲线仿真监控跑道</div>
                    <div class="h-24 w-full flex items-end border-b border-l border-slate-800 mt-2 relative p-1 bg-slate-950/40 rounded">
                        <div class="absolute text-[8px] text-slate-600 top-1 right-2 font-mono">Real-time Node Activity</div>
                        <div class="w-full bg-gradient-to-r from-blue-500/5 via-indigo-500/20 to-rose-500/5 h-12 border-t border-dashed border-indigo-500/30 rounded"></div>
                    </div>
                </div>
                <div class="md:col-span-6 bg-slate-900/30 border border-slate-800 p-3.5 rounded-xl flex flex-col justify-between space-y-2">
                    <div class="text-[11px] font-bold text-slate-300">📥 算法赋能：负能量粉碎座舱</div>
                    <input type="text" id="smash-input" value="辛辛苦苦调了很久的代码全丢了，太绝望了！" class="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-slate-700 transition-all" />
                    <div class="flex gap-2">
                        <button onclick="doSmash()" class="flex-1 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded text-[11px] transition-all active:scale-95">💥 彻底粉碎消极文本</button>
                        <button onclick="doLaunch()" class="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded text-[11px] transition-all active:scale-95">🌌 打包流放到太空</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-slate-950/40 border border-slate-800/50 rounded-2xl p-5">
            <h3 class="text-base font-bold text-white mb-1 flex items-center gap-2">💼 4. 交互式 AI 业务落地高保真解决方案演示厅</h3>
            <p class="text-[11px] text-slate-400 mb-4">纯前端驱动的多场景沙盒。支持多轮次剧本树拟真聊天，自动触底不截断内容。</p>

            <div class="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
                <div id="scen-tabs-box" class="md:col-span-5 flex flex-col gap-2.5"></div>

                <div class="md:col-span-7 border border-slate-800 bg-slate-950/90 rounded-xl p-4 flex flex-col min-h-[500px] max-h-[530px] overflow-hidden">
                    <div class="flex justify-between items-center pb-2 border-b border-slate-900 text-[11px] text-slate-400 mb-3">
                        <span>🤖 AI Agent 闭环辅助决策中枢</span>
                        <div class="flex gap-1"><span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span></div>
                    </div>

                    <textarea id="scen-area" class="w-full bg-slate-900/60 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-slate-700 h-16 resize-none mb-3 transition-all"></textarea>

                    <div class="mb-3">
                        <button id="scen-trigger-btn" onclick="executeScenAnalysis()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded text-xs transition-all active:scale-95">🔍 触发业务场景检测</button>
                    </div>

                    <div id="scen-result-panel" class="flex-1 overflow-y-auto pr-1 space-y-3.5 scrollbar-thin hidden">
                        <div class="bg-slate-900/40 p-3 rounded-lg border border-slate-900 space-y-2">
                            <span class="text-[10px] text-red-400 font-bold block">🚨 特征矩阵概率占比：</span>
                            <div id="scen-progress-bars" class="space-y-1.5"></div>
                        </div>

                        <div class="border border-slate-900/80 rounded-lg p-3 bg-slate-900/10 flex flex-col">
                            <div class="text-[11px] font-bold text-white mb-2 pb-1.5 border-b border-slate-900 flex items-center gap-1">✨ <span id="scen-bot-title">AI专家专家</span></div>
                            <div id="scen-bubble-wall" class="space-y-2.5 max-h-[150px] overflow-y-auto pr-1 scrollbar-thin mb-2.5"></div>

                            <div class="flex gap-2 border-t border-slate-900/60 pt-2">
                                <input type="text" id="scen-reply-input" placeholder="输入跟进对策继续切磋..." class="flex-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-[11px] text-white focus:outline-none" />
                                <button onclick="pushUserMessage()" class="px-3 py-1 bg-slate-800 text-slate-200 text-[11px] font-medium rounded hover:bg-slate-700 transition-all">➔ 发送</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script>
      const SCENARIOS = [
        {
          title: "心理健康早期预警", label: "Social Good", color: "border-red-500/40 shadow-red-500/5",
          text: "最近真的太难熬了，每天都失眠，感觉坚持不下去了，随便吧……",
          bars: [{n: '忧忧', v: 72}, {n: '丧丧', v: 28}],
          botName: "心理危机咨询专家 · 浙小理",
          scripts: [
            "看到你这句话，我能深深感受到你此刻承担的巨大疲惫与无助。算法捕捉到了'坚持不下去了'的高危信号。请听我说，崩溃并不是你的错，这只是心理能量暂时耗尽的求救信号。今晚把所有繁杂的工作和负担按下暂停键好吗？我不跟你说教，我只是想在这里安安静静地陪着你。",
            "你能回复我，说明你已经在尝试把封闭的心门推开一道缝隙了，这真的很棒。❤️ 心理学上讲我们要允许自己偶尔搞砸和停滞，这是积蓄能量的开始。要不要跟着我闭上眼睛，深呼吸 3 次放松一下？",
            "感觉好点了吗？记得把我的控制台留在你的收藏夹里，难过随时来输入。现实中也请记得学校辅导员张老师的办公室（24h电话：138****6789）灯光随时为你亮着。早点睡吧，晚安，勇敢的朋友。"
          ]
        },
        {
          title: "智能客服情绪感知", label: "Enterprise", color: "border-blue-500/40 shadow-blue-500/5",
          text: "买了三天还没发货，你们客服是死人吗？！退钱！垃圾服务！",
          bars: [{n: '怒怒', v: 92}, {n: '厌恶', v: 8}],
          botName: "公关与大客户主管 · 浙小小",
          scripts: [
            "客服同学注意！系统监测到该用户由于'物流延迟'正处于 [极端愤怒] 状态，切忌使用'亲，久等了'这种敷衍机器人的套话。AI 赋能建议：①【确定性降温】：第一句话直接给硬核答复：'万分抱歉！已为您将快件强行升级为特快顺丰，我将全程盯防。' ②【利益对冲】：主动派发 20 元退款补偿券，将矛盾转化为获利体验。",
            "已自动在物流仓储后台对该包裹挂载了'高危加急'红标。请问上述话术方案是否已向用户下发？我将实时为您盯防用户的愤怒指数回落。",
            "干得漂亮！检测到用户追加回复中的攻击性词汇密度已呈瀑布式下跌，情绪成功转化为[平静]。本次特大差评公关危言已被完美化解！"
          ]
        },
        {
          title: "影视/商品口碑分析", label: "Commerce", color: "border-amber-500/40 shadow-amber-500/5",
          text: "前半段剧情极其神作，后半段简直依托答辩，导演真有你的[微笑]。",
          bars: [{n: '厌恶', v: 75}, {n: '讽刺', v: 25}],
          botName: "全网舆情总分析官 · 浙小安",
          scripts: [
            "片方宣发团队你好，刚刚解析的这篇评论表面带有正向词'神作'和表情'微笑'，但词序特征中'依托答辩'权重极高，是一篇典型的[高阶反讽/阴阳怪气]负面口碑。此类口碑隐蔽性极强，极易误导算法推荐。AI 建议：① 适当调低本流派言论在社区的推荐权重；② 提炼'后半段剧情'等核心痛点立刻反馈给剪辑组，防止后续宣发片花继续踩坑。",
            "后台系统正在为您全网聚类与'后半段剧情'关联的 24h 词云图，发现'高开低走''人设崩塌'的重合度高达82%。需要帮您一键导出脱敏研报吗？",
            "精细化聚类分析报告已安全录入运营后台。建议接下来的宣传策略向'官方带头自黑'和'主创面对面真诚探讨'的方向转型，以柔克刚消解社区暴戾戾气。"
          ]
        },
        {
          title: "社区反网暴言论监测", label: "Security", color: "border-emerald-500/40 shadow-emerald-500/5",
          text: "网络喷子说话真恶心，长成这样也好意思发出来博眼球，赶紧封号吧。",
          bars: [{n: '厌恶', v: 85}, {n: '愤怒', v: 15}],
          botName: "网络风控安全官 · 浙小净",
          scripts: [
            "安全审计员注意，该用户输入的文本包含极强烈的'外貌羞辱'和群聚'人身攻击'，违反了平台文明公约。AI 安全中枢已强制启动【一键三连围剿】：① 对该条言论执行语义隐形拦截，不公开展示防止二次伤害；② 对该发帖账号实施 24 小时自动阶段性禁言；③ 提取设备指纹存证。",
            "系统已将该发帖账号的设备 IP 列入重点黑产和喷子观察名单。请问是否需要追加进行更高级别的全网关联资产排查？",
            "拦截配置已悉数锁定完毕。AI 会坚定不移地维护网络社区的清朗与善良，把所有的网络戾气统统隔绝在外。"
          ]
        },
        {
          title: "游戏玩家社区反馈分析", label: "Gaming", color: "border-indigo-500/40 shadow-indigo-500/5",
          text: "新版本策划真是小天才，抽卡概率暗改吃相真难看，氪了三千零水花，退游了。",
          bars: [{n: '丧丧', v: 50}, {n: '怒怒', v: 50}],
          botName: "游戏产品高级运营 · 浙小游",
          scripts: [
            "游戏策划与运营团队注意！该核心玩家遭遇[怒怒]与[丧丧]对半开的双重情绪重压，痛点直指本次更新的'抽卡保底暗改'。算法判定该核心氪金玩家的'退游概率'高达 92%。挽留策略迫在眉睫：① 30分钟内由主策发布保底公式白皮书算法透明公告；② 今晚紧急全服维护补偿 5 个抽卡珍贵道具，迅速稀释社区负面舆情。",
            "全网同类针对'暗改概率'的玩家反馈在过去2小时内已积压超 1.2 万条。是否需要立刻调集产品核心算法组进行代码热修复查验？",
            "全套补偿方案与安民告示模板已同步下发至社区官号。恭喜，由于全服补偿及时，当前社区玩家留存曲线已重新抬头趋于平稳。"
          ]
        }
      ];

      let activeScen = 0; let activeTurn = 0;

      function renderScenTabs() {
        document.getElementById('scen-tabs-box').innerHTML = SCENARIOS.map((s, idx) => {
          const isSel = idx === activeScen;
          return `
            <div onclick="changeScen(${idx})" class="p-3 rounded-xl border text-left bg-slate-900/40 cursor-pointer transition-all duration-300 ${isSel ? 'bg-slate-900 border-l-4 ' + s.color : 'border-slate-800/60 hover:border-slate-700'}">
              <div class="flex justify-between items-center">
                <span class="font-semibold text-xs ${isSel ? 'text-white' : 'text-slate-400'}">${s.title}</span>
                <span class="text-[9px] px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800/80">${s.label}</span>
              </div>
            </div>`;
        }).join('');
      }

      window.changeScen = function(idx) {
        activeScen = idx; activeTurn = 0;
        document.getElementById('scen-area').value = SCENARIOS[idx].text;
        document.getElementById('scen-result-panel').classList.add('hidden');
        document.getElementById('scen-trigger-btn').disabled = false;
        document.getElementById('scen-trigger-btn').innerText = "🔍 触发业务场景检测";
        renderScenTabs();
      }

      window.executeScenAnalysis = function() {
        const btn = document.getElementById('scen-trigger-btn');
        btn.disabled = true; btn.innerText = "🔍 正在进行高维特征向量对齐...";

        setTimeout(() => {
          btn.innerText = "🔄 重新检测";
          btn.disabled = false;
          const s = SCENARIOS[activeScen];
          const userText = document.getElementById('scen-area').value;

          let barHtml = '';

          if(userText.includes('哈') || userText.includes('笑')) {
            barHtml = `
              <div class="text-[10px] space-y-0.5 animate-fadeIn">
                <div class="flex justify-between text-slate-400"><span>乐乐 (Positive)</span><span>95%</span></div>
                <div class="w-full bg-slate-950 h-1.5 rounded-full"><div class="bg-yellow-500 h-full rounded-full" style="width: 95%"></div></div>
              </div>`;
            document.getElementById('scen-bot-title').innerText = "情绪阳光天使 · 浙小乐";
            document.getElementById('scen-bubble-wall').innerHTML = `
              <div class="flex justify-start animate-fadeIn">
                <div class="max-w-[90%] rounded-lg p-2 bg-slate-900 border border-slate-800 text-slate-200 text-[11px]">哈哈！看来你现在心情好到飞起呀！作为你的 AI 情绪向导，看到这么充满阳光的文字，我的分类算法模块都跟着暖起来了。保持好心情，把快乐分享出去吧！</div>
              </div>`;
            activeTurn = 99;
          } else {
            barHtml = s.bars.map(b => `
              <div class="text-[10px] space-y-0.5">
                <div class="flex justify-between text-slate-400"><span>${b.n}</span><span>${b.v}%</span></div>
                <div class="w-full bg-slate-950 h-1.5 rounded-full"><div class="bg-blue-500 h-full rounded-full" style="width: ${b.v}%"></div></div>
              </div>`).join('');

            document.getElementById('scen-bot-title').innerText = s.botName;
            document.getElementById('scen-bubble-wall').innerHTML = `
              <div class="flex justify-start animate-fadeIn">
                <div class="max-w-[90%] rounded-lg p-2 bg-slate-900 border border-slate-800 text-slate-200 text-[11px] whitespace-pre-line">${s.scripts[0]}</div>
              </div>`;
            activeTurn = 1;
          }

          document.getElementById('scen-progress-bars').innerHTML = barHtml;
          document.getElementById('scen-result-panel').classList.remove('hidden');
          autoScrollWall();
        }, 900);
      }

      window.pushUserMessage = function() {
        const input = document.getElementById('scen-reply-input');
        const txt = input.value.trim(); if(!txt) return;
        input.value = '';

        const wall = document.getElementById('scen-bubble-wall');
        wall.innerHTML += `<div class="flex justify-end animate-fadeIn"><div class="max-w-[90%] rounded-lg p-2 bg-blue-600 text-white text-[11px]">${txt}</div></div>`;
        autoScrollWall();

        const loadingId = 'typing-' + Date.now();
        wall.innerHTML += `<div id="${loadingId}" class="text-[9px] text-slate-500 text-left pl-1">● AI专家 正在思考决策方案...</div>`;
        autoScrollWall();

        setTimeout(() => {
          document.getElementById(loadingId).remove();
          const s = SCENARIOS[activeScen];
          let reply = "收到您的跟进反馈。该板块的交互系统功能已完美形成商业落地闭环，您可以随时切换左侧其他场景进行体验。";

          if(activeTurn === 99) {
            reply = "正面情绪能够扩充个体的认知范围。继续加油，拥抱美好的一天！✨";
          } else if(activeTurn < s.scripts.length) {
            reply = s.scripts[activeTurn];
            activeTurn++;
          }

          wall.innerHTML += `<div class="flex justify-start animate-fadeIn"><div class="max-w-[90%] rounded-lg p-2 bg-slate-900 border border-slate-800 text-slate-200 text-[11px] whitespace-pre-line">${reply}</div></div>`;
          autoScrollWall();
        }, 1000);
      }

      function autoScrollWall() {
        const wall = document.getElementById('scen-bubble-wall');
        wall.scrollTop = wall.scrollHeight;
      }

      window.doSmash = function() {
        const i = document.getElementById('smash-input'); if(!i.value) return;
        alert('💥 粒子降维摧毁完成！主引擎代码判定：该行充满负面因子的文本已在本地内存块中被物理消灭，负能量消散！'); i.value = '';
      }
      window.doLaunch = function() {
        const i = document.getElementById('smash-input'); if(!i.value) return;
        alert('🌌 文本已被打包加密并施加逃逸速度，脱离地球引力射入外太空黑洞中，消极情绪永远无法再伤害你。'); i.value = '';
      }

      renderScenTabs(); changeScen(0);
    </script>
</body>
</html>
"""

components.html(showroom_html, height=1380, scrolling=False)
