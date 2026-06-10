"""utils.py —— 情感分析系统公共模块
提供文本清洗、标签映射、颜色配置、饼图绘制等共用功能。
"""

import re
import jieba
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# -------------------------- 全局配置 --------------------------
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 120

# 情感标签映射（与训练数据完全一致）
LABEL_MAP = {
    0: '愤怒',
    1: '恐惧',
    2: '开心',
    3: '中性',
    4: '悲伤',
    5: '惊讶'
}

# 情感专属配色（心理学上的标准情感颜色）
EMOTION_COLORS = {
    '愤怒': '#FF4D4F',
    '恐惧': '#722ED1',
    '开心': '#FAAD14',
    '中性': '#52C41A',
    '悲伤': '#1890FF',
    '惊讶': '#EB2F96'
}

# 扩展中文停用词表（100+常用无意义词）
STOP_WORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '也', '很', '还', '又', '太', '真', '最',
    '啊', '呀', '呢', '吧', '吗', '哦', '哈', '啦', '哇', '嘛', '哟', '哎', '咦', '呵', '嘿',
    '这', '那', '个', '些', '之', '于', '与', '其', '而', '及', '并', '或', '但', '然', '则', '虽', '既',
    '你', '他', '她', '它', '们', '我们', '你们', '他们', '她们', '它们', '自己', '别人', '大家', '各位',
    '什么', '怎么', '为什么', '哪里', '何时', '多少', '几', '谁', '哪', '怎', '如何', '多么',
    '今天', '昨天', '明天', '现在', '刚才', '以后', '之前', '时候', '时间', '一天', '一年', '一点',
    '可以', '能够', '会', '要', '应该', '必须', '得', '能', '可', '让', '叫', '把', '被',
    '一个', '两个', '三个', '第一', '第二', '第三', '次', '遍', '下', '上', '里', '外', '中', '间',
    '因为', '所以', '如果', '但是', '而且', '虽然', '即使', '只要', '只有', '无论', '不管', '还是'
}

# -------------------------- 公共函数 --------------------------
def clean_text(text):
    """统一的文本清洗函数（训练和预测必须完全一致）"""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""

    # 1. 保留中文、英文、数字和空格
    text = re.sub(r'[^一-龥a-zA-Z0-9\s]', '', str(text))

    # 2. 分词
    words = jieba.lcut(text.strip())

    # 3. 停用词过滤和长度过滤
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    return ' '.join(words)


def identity_tokenizer(text):
    """TF-IDF专用分词器（必须与训练时一致）"""
    return text.split()


def plot_emotion_pie(probabilities, text=None, save_path=None):
    """改进的情感概率饼图绘制函数"""
    labels = []
    sizes = []
    colors = []

    for label, prob in probabilities.items():
        if prob < 0.001:
            continue

        if isinstance(label, (int, np.integer)) and label in LABEL_MAP:
            emotion_name = LABEL_MAP[label]
        elif isinstance(label, str) and label in EMOTION_COLORS:
            emotion_name = label
        else:
            emotion_name = f"情感{label}"
            colors.append('#CCCCCC')
            labels.append(f"{emotion_name}\n{prob:.1%}")
            sizes.append(prob)
            continue

        color = EMOTION_COLORS.get(emotion_name, '#CCCCCC')
        colors.append(color)
        labels.append(f"{emotion_name}\n{prob:.1%}")
        sizes.append(prob)

    if not sizes:
        print("❌ 没有可绘制的情感数据")
        return

    plt.figure(figsize=(8, 8))
    wedges, texts, autotexts = plt.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 11, 'color': 'black', 'fontweight': 'medium'},
        wedgeprops={'linewidth': 1.5, 'edgecolor': 'white'},
        pctdistance=0.85
    )

    if text:
        short_text = text[:35] + ('...' if len(text) > 35 else '')
        plt.title(f"文本情感分析结果\n\"{short_text}\"", fontsize=14, pad=25, fontweight='bold')

    plt.axis('equal')

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ 图表已保存为: {save_path}")
    else:
        plt.show(block=True)

    plt.close()
