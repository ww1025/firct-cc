import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.utils.class_weight import compute_class_weight

# 定义tokenizer函数，替代lambda
def identity_tokenizer(text):
    return text.split()

# ---------------------- 1. 加载预处理数据 ----------------------
data = np.load("processed_data.npz", allow_pickle=True)
X_train, y_train = data['X_train'], data['y_train']
X_val, y_val = data['X_val'], data['y_val']
X_test, y_test = data['X_test'], data['y_test']
classes = data['classes'].tolist()

# ---------------------- 2. 文本特征提取（TF-IDF） ----------------------
VOCAB_SIZE = 20000
tfidf = TfidfVectorizer(
    max_features=VOCAB_SIZE,
    ngram_range=(1, 2),
    lowercase=False,
    tokenizer=identity_tokenizer,
    token_pattern=None  # 关键：关闭默认的token_pattern
)

# 拟合训练集并转换所有数据
X_train_tfidf = tfidf.fit_transform(X_train)
X_val_tfidf = tfidf.transform(X_val)
X_test_tfidf = tfidf.transform(X_test)

# ---------------------- 3. 构建并训练逻辑回归模型 ----------------------
class_weights = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
class_weight_dict = dict(enumerate(class_weights))

model = LogisticRegression(
    class_weight=class_weight_dict,
    max_iter=1000,
    solver='saga',
    random_state=42,
    n_jobs=-1
)

print("正在训练模型...")
model.fit(X_train_tfidf, y_train)

# ---------------------- 4. 模型评估 ----------------------
y_val_pred = model.predict(X_val_tfidf)
y_test_pred = model.predict(X_test_tfidf)

val_acc = accuracy_score(y_val, y_val_pred)
test_acc = accuracy_score(y_test, y_test_pred)

print(f"\n✅ 模型训练完成！")
print(f"验证集准确率: {val_acc:.4f}")
print(f"测试集准确率: {test_acc:.4f}")
print("\n详细分类报告（测试集）：")
print(classification_report(y_test, y_test_pred, target_names=classes))

# ---------------------- 5. 保存模型和向量器 ----------------------
with open("tfidf_vectorizer.pkl", "wb") as f:
    pickle.dump(tfidf, f)

with open("sklearn_emotion_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("\n✅ 模型已保存为 sklearn_emotion_model.pkl")
print("✅ TF-IDF向量器已保存为 tfidf_vectorizer.pkl")