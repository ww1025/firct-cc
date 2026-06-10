import numpy as np
import pickle
import jieba
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# -------------------------- 解决matplotlib中文显示问题 --------------------------
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 120  # 提高图表清晰度

# -------------------------- 关键修复：数字标签到中文情感的映射 --------------------------
# 这是解决饼图全灰问题的核心！根据你的训练数据集调整
LABEL_MAP = {
    0: '愤怒',
    1: '恐惧',
    2: '开心',
    3: '中性',
    4: '悲伤',
    5: '惊讶'
}

# 情感专属配色（与中文名称一一对应）
EMOTION_COLORS = {
    '愤怒': '#FF4D4F',   # 亮红色
    '恐惧': '#722ED1',   # 深紫色
    '开心': '#FAAD14',   # 金黄色
    '中性': '#52C41A',   # 绿色
    '悲伤': '#1890FF',   # 蓝色
    '惊讶': '#EB2F96'    # 粉红色
}

# -------------------------- 必须和训练脚本保持完全一致的tokenizer函数 --------------------------
def identity_tokenizer(text):
    return text.split()

# -------------------------- 修复后的绘制情感概率饼图函数 --------------------------
def plot_emotion_pie(probabilities, text=None, save_path=None):
    """
    绘制情感概率饼图（已修复颜色问题）
    """
    labels = []
    sizes = []
    colors = []
    
    # 遍历所有情感概率
    for label, prob in probabilities.items():
        if prob < 0.0001:  # 忽略极小概率
            continue
            
        # 自动转换数字标签为中文名称
        if isinstance(label, (int, np.integer)) and label in LABEL_MAP:
            emotion_name = LABEL_MAP[label]
        elif isinstance(label, str) and label in EMOTION_COLORS:
            emotion_name = label
        else:
            # 未知标签，使用默认名称和颜色
            emotion_name = f"情感{label}"
            colors.append('#CCCCCC')
            labels.append(f"{emotion_name}\n{prob:.1%}")
            sizes.append(prob)
            continue
        
        # 获取对应颜色
        color = EMOTION_COLORS.get(emotion_name, '#CCCCCC')
        colors.append(color)
        labels.append(f"{emotion_name}\n{prob:.1%}")
        sizes.append(prob)
    
    if not sizes:
        print("❌ 没有可绘制的情感数据")
        return
    
    # 创建饼图
    plt.figure(figsize=(8, 8))
    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 11, 'color': 'black', 'fontweight': 'medium'},
        wedgeprops={'linewidth': 1.5, 'edgecolor': 'white'},
        pctdistance=0.85  # 调整百分比标签位置
    )
    
    # 设置标题
    if text:
        short_text = text[:35] + ('...' if len(text) > 35 else '')
        plt.title(f"文本情感分析结果\n\"{short_text}\"", fontsize=14, pad=25, fontweight='bold')
    
    # 保证饼图是正圆形
    plt.axis('equal')
    
    # 保存或显示
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ 图表已成功保存为: {save_path}")
    else:
        print("\n📊 正在生成彩色饼图...")
        print("💡 提示：关闭饼图窗口后程序才会继续运行")
        plt.show(block=True)
    
    plt.close()

# -------------------------- 1. 加载训练好的模型和TF-IDF向量器 --------------------------
try:
    with open("sklearn_emotion_model.pkl", "rb") as f:
        model = pickle.load(f)
    
    with open("tfidf_vectorizer.pkl", "rb") as f:
        tfidf_vectorizer = pickle.load(f)
    
    print("✅ 模型和向量器加载成功！")
    
    # 自动检测模型标签类型
    print(f"\n🔍 检测到模型输出标签: {model.classes_}")
    if all(isinstance(c, (int, np.integer)) for c in model.classes_):
        print("✅ 自动启用数字标签转中文功能")
    else:
        print("ℹ️ 模型输出为中文标签，直接使用")

except FileNotFoundError:
    print("❌ 错误：找不到模型文件！")
    print("请确保 sklearn_emotion_model.pkl 和 tfidf_vectorizer.pkl 与本脚本在同一目录下")
    exit(1)

# -------------------------- 2. 测试用例 --------------------------
print("\n" + "="*60)
print("【测试用例 5】")
test_text5 = "突然收到了一个惊喜礼物，我完全没想到！"
print(f"原始文本：{test_text5}")
text_vector5 = tfidf_vectorizer.transform([test_text5])
predicted_emotion5 = model.predict(text_vector5)[0]
probabilities5 = model.predict_proba(text_vector5)[0]
emotion_dict5 = dict(zip(model.classes_, probabilities5))

# 自动转换预测结果为中文
if isinstance(predicted_emotion5, (int, np.integer)) and predicted_emotion5 in LABEL_MAP:
    predicted_emotion5 = LABEL_MAP[predicted_emotion5]

print(f"预测情感：{predicted_emotion5}")
print(f"置信度：{max(probabilities5):.4f}")
print(f"所有情感概率：{emotion_dict5}")

print("\n" + "-"*60)
print("【测试用例 6】")
test_text6 = "晚上一个人走在漆黑的小巷里，有点害怕。"
print(f"原始文本：{test_text6}")
text_vector6 = tfidf_vectorizer.transform([test_text6])
predicted_emotion6 = model.predict(text_vector6)[0]
probabilities6 = model.predict_proba(text_vector6)[0]
emotion_dict6 = dict(zip(model.classes_, probabilities6))

if isinstance(predicted_emotion6, (int, np.integer)) and predicted_emotion6 in LABEL_MAP:
    predicted_emotion6 = LABEL_MAP[predicted_emotion6]

print(f"预测情感：{predicted_emotion6}")
print(f"置信度：{max(probabilities6):.4f}")
print(f"所有情感概率：{emotion_dict6}")

# -------------------------- 3. 主交互循环 --------------------------
print("\n" + "="*60)
print("🎉 情感分析系统已就绪！")
print("📝 使用说明：")
print("  1. 直接输入任意文本进行情感分析")
print("  2. 输入 'plot 文本' 生成彩色情绪饼状图")
print("     示例：plot 突然收到了一个惊喜礼物，我完全没想到！")
print("  3. 输入 'save 文本 文件名.png' 保存图表到文件")
print("     示例：save 今天真的太开心了！ happy_mood.png")
print("  4. 输入 'quit' 退出程序")
print("="*60)

while True:
    user_input = input("\n请输入要分析的文本：").strip()
    
    if user_input.lower() == 'quit':
        print("\n👋 感谢使用，程序已退出")
        break
    
    if not user_input:
        print("❌ 请输入非空文本")
        continue
    
    # 处理 plot 命令
    if user_input.lower().startswith('plot '):
        text = user_input[5:].strip()
        if not text:
            print("❌ 格式错误！正确格式：plot 要分析的文本")
            continue
        
        text_vector = tfidf_vectorizer.transform([text])
        probabilities = model.predict_proba(text_vector)[0]
        emotion_dict = dict(zip(model.classes_, probabilities))
        predicted_emotion = model.predict(text_vector)[0]
        
        # 转换为中文显示
        if isinstance(predicted_emotion, (int, np.integer)) and predicted_emotion in LABEL_MAP:
            predicted_emotion = LABEL_MAP[predicted_emotion]
        
        print(f"\n📝 预测结果：")
        print(f"  情感类别：{predicted_emotion}")
        print(f"  置信度：{max(probabilities):.4f}")
        
        plot_emotion_pie(emotion_dict, text)
    
    # 处理 save 命令
    elif user_input.lower().startswith('save '):
        parts = user_input.split(maxsplit=2)
        if len(parts) < 3:
            print("❌ 格式错误！正确格式：save 要分析的文本 文件名.png")
            continue
        
        text = parts[1]
        filename = parts[2]
        
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        text_vector = tfidf_vectorizer.transform([text])
        probabilities = model.predict_proba(text_vector)[0]
        emotion_dict = dict(zip(model.classes_, probabilities))
        predicted_emotion = model.predict(text_vector)[0]
        
        if isinstance(predicted_emotion, (int, np.integer)) and predicted_emotion in LABEL_MAP:
            predicted_emotion = LABEL_MAP[predicted_emotion]
        
        print(f"\n📝 预测结果：")
        print(f"  情感类别：{predicted_emotion}")
        print(f"  置信度：{max(probabilities):.4f}")
        
        plot_emotion_pie(emotion_dict, text, filename)
    
    # 普通文本分析
    else:
        text_vector = tfidf_vectorizer.transform([user_input])
        probabilities = model.predict_proba(text_vector)[0]
        emotion_dict = dict(zip(model.classes_, probabilities))
        predicted_emotion = model.predict(text_vector)[0]
        
        if isinstance(predicted_emotion, (int, np.integer)) and predicted_emotion in LABEL_MAP:
            predicted_emotion = LABEL_MAP[predicted_emotion]
        
        print(f"\n📝 预测结果：")
        print(f"  情感类别：{predicted_emotion}")
        print(f"  置信度：{max(probabilities):.4f}")
        print(f"  详细概率：{emotion_dict}")