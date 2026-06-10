# 中文情感分析系统

基于 TF-IDF + 逻辑回归的六分类中文情感识别，Streamlit Web 界面。

## 📂 文件分工

```
├── emotion_engine.py   ← 🔧 引擎同学改：模型加载、文本清洗、预测
├── app.py              ← 🎨 UI 同学改：Streamlit 界面、CSS 美化（不改引擎逻辑！）
├── predict.py          ← 🖥️ 命令行版（独立使用）
├── train_model.py      ← 🏋️ 训练脚本
├── data_preprocess.py  ← 📦 数据预处理
├── 启动情感分析.bat     ← 🚀 一键启动
│
├── sklearn_emotion_model.pkl   ← 训练好的模型
├── tfidf_vectorizer.pkl       ← TF-IDF 向量器
└── processed_data.npz         ← 处理后的数据
```

## ⚠️ 协作规则

**不！要！越！界！**

- `emotion_engine.py` 放所有可复用的引擎逻辑（clean_text / predict / load_models / 常量）
- `app.py` 只负责 Streamlit UI 渲染，通过 `import emotion_engine` 调用引擎
- 引擎同学改 `emotion_engine.py` → UI 自动适配新逻辑，互不冲突
- Git 合并时各改各的文件，永远不冲突 ✌️

## 🚀 启动方式

```bash
pip install streamlit jieba scikit-learn pandas matplotlib altair

streamlit run app.py
```

或双击 `启动情感分析.bat`。

## 📋 emotion_engine.py API

```python
from emotion_engine import predict, clean_text, load_models, EMOTION_CONFIG

# 预测
emotion, probs = predict("今天心情很好！")
# emotion = "开心"
# probs = {"开心": 0.89, "中性": 0.05, "惊讶": 0.03, ...}

# 清洗
cleaned = clean_text("原始文本")  # → "原始 文本"

# 加载模型
model, vectorizer, classes = load_models()

# 情感配置
EMOTION_CONFIG["开心"]
# → {"emoji": "😊", "color": "#F59E0B", "light": "#FEF3C7"}
```
