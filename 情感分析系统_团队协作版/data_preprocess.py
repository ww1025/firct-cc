import pandas as pd
import numpy as np
import jieba
import re
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ---------------------- 1. 加载数据集 ----------------------
# 确保merged.csv和此文件在同一目录
data = pd.read_csv("merged.csv", header=None)
# 重命名列：第一列是文本，后面6列对应6种情感
data.columns = ['text', 'angry', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# ---------------------- 2. 文本清洗函数 ----------------------
def clean_text(text):
    if pd.isna(text):
        return ""
    # 保留中文、英文、数字和空格
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', str(text))
    # 分词
    words = jieba.lcut(text)
    # 停用词过滤
    stop_words = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '也', '很', '还', '又', '太', '真', '最'}
    words = [w for w in words if w not in stop_words and len(w) > 1]
    return ' '.join(words)

# ---------------------- 3. 处理数据 ----------------------
# 清洗文本
data['clean_text'] = data['text'].apply(clean_text)

# 生成标签：取每行分数最高的情感
emotion_cols = ['angry', 'fear', 'happy', 'neutral', 'sad', 'surprise']
data['label'] = data[emotion_cols].idxmax(axis=1)

# 标签编码
le = LabelEncoder()
data['label_encoded'] = le.fit_transform(data['label'])
classes = le.classes_  # 保存情感类别顺序

# 划分训练集、验证集、测试集（7:1:2）
X = data['clean_text'].values
y = data['label_encoded'].values

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=2/3, random_state=42, stratify=y_temp)

# ---------------------- 4. 保存预处理后的数据 ----------------------
np.savez(
    "processed_data.npz",
    X_train=X_train,
    y_train=y_train,
    X_val=X_val,
    y_val=y_val,
    X_test=X_test,
    y_test=y_test,
    classes=np.array(classes)  # 转换为数组才能保存
)

print("✅ 数据预处理完成！已保存为 processed_data.npz")
print(f"训练集大小: {len(X_train)}, 验证集大小: {len(X_val)}, 测试集大小: {len(X_test)}")
print(f"情感类别: {classes}")