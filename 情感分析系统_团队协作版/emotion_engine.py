"""emotion_engine.py —— 情感分析引擎（共享业务逻辑层）

其他组员优化模型/清洗/特征时改这个文件。
UI 同学（app.py）import 这个模块即可，不用改引擎代码。
"""

import pickle
import re
import sys
import numpy as np
import jieba
import pandas as pd
from typing import Tuple, Dict, Optional, List

# =============================================================================
# pickle 兼容：sklearn 1.8 → 1.9 版本迁移
# 训练脚本中 TfidfVectorizer(tokenizer=identity_tokenizer)，pickle 序列化为
# __main__.identity_tokenizer 引用。使用自定义 Unpickler 子类，100% 可靠。
# =============================================================================
def _identity_tokenizer(text):
    return text.split()


class _CompatUnpickler(pickle.Unpickler):
    """自定义 Unpickler：拦截 __main__.identity_tokenizer 查找"""
    def find_class(self, module, name):
        if module == "__main__" and name == "identity_tokenizer":
            return _identity_tokenizer
        return super().find_class(module, name)


# =============================================================================
# 情感常量配置
# =============================================================================
# 英文 → 中文映射
EMOTION_EN_TO_CN = {
    "angry": "愤怒",
    "fear": "恐惧",
    "happy": "开心",
    "neutral": "中性",
    "sad": "悲伤",
    "surprise": "惊讶",
}

# 数字标签 → 中文映射（用于 predict.py 兼容）
LABEL_TO_CN = {0: "愤怒", 1: "恐惧", 2: "开心", 3: "中性", 4: "悲伤", 5: "惊讶"}

# 情感视觉配置（UI 渲染用）
EMOTION_CONFIG = {
    "开心": {"emoji": "😊", "color": "#F59E0B", "light": "#FEF3C7"},
    "愤怒": {"emoji": "😡", "color": "#EF4444", "light": "#FEE2E2"},
    "悲伤": {"emoji": "😢", "color": "#3B82F6", "light": "#DBEAFE"},
    "恐惧": {"emoji": "😨", "color": "#8B5CF6", "light": "#EDE9FE"},
    "惊讶": {"emoji": "😲", "color": "#EC4899", "light": "#FCE7F3"},
    "中性": {"emoji": "😐", "color": "#6B7280", "light": "#F3F4F6"},
}

# =============================================================================
# 文本清洗
# =============================================================================
STOP_WORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
    "都", "一", "也", "很", "还", "又", "太", "真", "最",
}


def clean_text(text: str) -> str:
    """清洗文本：去除非中英文数字、jieba 分词、去停用词"""
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = re.sub(r"[^一-龥a-zA-Z0-9\s]", "", str(text))
    words = jieba.lcut(text)
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


# =============================================================================
# 模型管理（单例缓存，避免重复加载）
# =============================================================================
_global_model = None
_global_vectorizer = None
_global_classes_cn: List[str] = []


def load_models(
    model_path: str = "sklearn_emotion_model.pkl",
    vectorizer_path: str = "tfidf_vectorizer.pkl",
    data_path: str = "processed_data.npz",
) -> Tuple:
    """加载模型、TF-IDF 向量器和中文类别标签。

    使用模块级缓存：多次调用不会重复加载。
    返回 (model, vectorizer, classes_cn)
    """
    global _global_model, _global_vectorizer, _global_classes_cn

    if _global_model is not None:
        return _global_model, _global_vectorizer, _global_classes_cn

    with open(model_path, "rb") as f:
        _global_model = pickle.load(f)

    # 使用自定义 Unpickler 加载 tfidf_vectorizer.pkl
    # ——这是解决 sklearn 1.8→1.9 pickle 兼容问题的关键
    with open(vectorizer_path, "rb") as f:
        _global_vectorizer = _CompatUnpickler(f).load()

    with np.load(data_path, allow_pickle=True) as data:
        classes_en = data["classes"].tolist()
        _global_classes_cn = [EMOTION_EN_TO_CN.get(e, e) for e in classes_en]

    return _global_model, _global_vectorizer, _global_classes_cn


def get_loaded_models() -> Optional[Tuple]:
    """获取已加载的模型（不触发加载）。未加载时返回 None。"""
    if _global_model is None:
        return None
    return _global_model, _global_vectorizer, _global_classes_cn


# =============================================================================
# 预测
# =============================================================================
def predict(text: str) -> Tuple[Optional[str], Optional[Dict[str, float]]]:
    """对输入文本进行情感预测。

    Args:
        text: 原始中文文本

    Returns:
        (predicted_emotion_cn, probabilities_dict)
        — 清洗后文本为空时返回 (None, None)
        — probabilities_dict 的 key 为中文情感名
    """
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.svm import LinearSVC
    from sklearn.preprocessing import MinMaxScaler

    model, vectorizer, classes_cn = load_models()

    cleaned = clean_text(text)
    if not cleaned.strip():
        return None, None

    X = vectorizer.transform([cleaned])
    pred_idx = model.predict(X)[0]

    # ========== 关键兼容逻辑：区分 LinearSVC（无 predict_proba）==========
    is_linear_svc = False
    if isinstance(model, OneVsRestClassifier):
        first_estimator = model.estimators_[0]
        if isinstance(first_estimator, LinearSVC):
            is_linear_svc = True

    if is_linear_svc:
        # LinearSVC 用 decision_function 模拟概率
        decision_vals = model.decision_function(X)[0]
        if len(model.classes_) == 2 and len(decision_vals.shape) == 0:
            decision_vals = np.array([-decision_vals, decision_vals])

        scaler = MinMaxScaler()
        probabilities = scaler.fit_transform(decision_vals.reshape(-1, 1)).flatten()
        probabilities = probabilities / np.sum(probabilities)
    else:
        # 其他模型（LogisticRegression 等）用原生 predict_proba
        probabilities = model.predict_proba(X)[0]
    # ================================================================

    pred_cn = classes_cn[pred_idx]
    probs = {classes_cn[i]: float(probabilities[i]) for i in range(len(classes_cn))}
    return pred_cn, probs


def predict_top_k(text: str, k: int = 3) -> List[Tuple[str, float]]:
    """返回概率最高的 k 个情感。"""
    _, probs = predict(text)
    if probs is None:
        return []
    return sorted(probs.items(), key=lambda x: x[1], reverse=True)[:k]
