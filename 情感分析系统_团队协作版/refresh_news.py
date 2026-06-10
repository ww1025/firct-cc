"""refresh_news.py —— 新闻缓存刷新脚本

从百度/微博热搜抓取真实数据，写入 news_cache.json。
运行方式: python refresh_news.py

抓取策略（按优先级）：
  1. urllib (Python 标准库，无需安装依赖)
  2. requests (更可靠，但需 pip install requests)
  3. 失败则保留现有缓存
"""

import json
import os
import re
import time
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(DIR, "news_cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
TIMEOUT = 5


def fetch_text(url):
    """尝试用 urllib 抓取文本。"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [urllib] {url[:50]}... → {e}")
        return None


def fetch_json(url):
    """尝试用 urllib 抓取 JSON。"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [urllib] {url[:50]}... → {e}")
        return None


# =============================================================================
# 百度热搜
# =============================================================================
def scrape_baidu():
    """从百度热搜页面提取数据。"""
    print("[百度热搜] 抓取中...")
    html = fetch_text("https://top.baidu.com/board?tab=realtime")
    if not html:
        return []

    match = re.search(r'<!--s-data:(.*?)-->', html, re.DOTALL)
    if not match:
        print("  [百度] 未找到 s-data 标记")
        return []

    try:
        data = json.loads(match.group(1))
        cards = data.get("data", {}).get("cards", [])
        results = []
        for card in cards:
            for item in card.get("content", [])[:15]:
                word = item.get("word", "")
                desc = item.get("desc", "")
                hot_score = item.get("hotScore", "")
                if word:
                    results.append({
                        "title": f"{word} — {desc}" if desc else word,
                        "source": f"百度热搜",
                        "time": "实时",
                    })
        print(f"  [百度] 获取 {len(results)} 条热搜")
        return results
    except Exception as e:
        print(f"  [百度] 解析失败: {e}")
        return []


# =============================================================================
# 微博热搜
# =============================================================================
def scrape_weibo():
    """从微博热搜 API 抓取。"""
    print("[微博热搜] 抓取中...")
    data = fetch_json("https://weibo.com/ajax/side/hotSearch")
    if not data:
        return []

    try:
        results = []
        for item in data.get("data", {}).get("realtime", [])[:15]:
            word = item.get("word", "")
            if word:
                results.append({
                    "title": word,
                    "source": "微博热搜",
                    "time": "实时",
                })
        print(f"  [微博] 获取 {len(results)} 条热搜")
        return results
    except Exception as e:
        print(f"  [微博] 解析失败: {e}")
        return []


# =============================================================================
# 情绪分类
# =============================================================================
EMOTION_TERMS = {
    "乐乐": ["暖心", "感人", "幸福", "治愈", "美好", "正能量", "救助", "团圆",
             "快乐", "开心", "温暖", "感动", "涨了", "新高", "走红", "火了"],
    "怒怒": ["维权", "投诉", "曝光", "不公平", "公愤", "违规", "谴责", "抗议",
             "怒", "愤", "争议", "冲突", "约谈", "调查", "查处", "立案"],
    "忧忧": ["悲伤", "告别", "思念", "遗憾", "去世", "悼念", "泪目", "回忆",
             "哭", "难过", "最后", "离开", "关门", "空"],
    "怕怕": ["地震", "台风", "暴雨", "预警", "事故", "恐怖", "灾害", "危险",
             "惊", "高温", "红色", "应急", "紧急", "警告", "死亡"],
    "厌厌": ["食品", "卫生", "假货", "污染", "质检", "召回", "超标", "过期",
             "恶心", "臭", "曝光", "不合格", "安全", "违规", "脏"],
    "尬尬": ["翻车", "社死", "尴尬", "乌龙", "失误", "打脸", "出丑", "丢脸",
             "认错", "忘关", "不小心", "囧", "意外", "爆笑"],
    "丧丧": ["躺平", "佛系", "emo", "社畜", "精神离职", "摸鱼", "摆烂",
             "累", "没劲", "无聊", "周一", "内卷", "压力大", "不想"],
    "慕慕": ["首富", "豪宅", "成功", "逆袭", "学霸", "暴富", "限量", "巅峰",
             "羡慕", "别人家", "片酬", "身价", "富豪", "创业"],
    "焦焦": ["高考", "就业", "房价", "裁员", "考研", "内卷", "焦虑", "压力",
             "紧张", "竞争", "淘汰", "AI替代", "分数线", "经济"],
}


def classify(items):
    classified = {k: [] for k in EMOTION_TERMS}
    for item in items:
        text = item.get("title", "")
        best, best_score = None, 0
        for emo, terms in EMOTION_TERMS.items():
            s = sum(len(t) for t in terms if t in text)
            if s > best_score:
                best_score, best = s, emo
        if best and best_score > 0 and len(classified[best]) < 6:
            classified[best].append(dict(item))
    return classified


# =============================================================================
# 主流程
# =============================================================================
def main():
    print("=" * 50)
    print("情绪新闻缓存刷新")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    all_items = []

    # 并行抓取（简单顺序，避免依赖 concurrent.futures）
    baidu = scrape_baidu()
    if baidu:
        all_items.extend(baidu)

    weibo = scrape_weibo()
    if weibo:
        all_items.extend(weibo)

    print(f"\n共获取 {len(all_items)} 条热搜")

    if not all_items:
        print("\n❌ 未能获取到任何热搜数据。")
        print("可能原因：")
        print("  1. 网络连接问题（无法访问 baidu.com / weibo.com）")
        print("  2. SSL 证书问题")
        print("  3. 需要配置代理")
        print("\n将保留现有缓存文件不变。")
        return

    classified = classify(all_items)
    total = sum(len(v) for v in classified.values())

    cache = {
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "百度热搜 + 微博热搜 自动抓取",
        "total": total,
        "emotions": classified,
    }

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"✅ 缓存已更新 → {CACHE_FILE}")
    print(f"   情绪分类覆盖: {total} 条 / {sum(1 for v in classified.values() if v)} 个类别")
    for emo, items in classified.items():
        if items:
            print(f"   {emo}: {len(items)} 条")


if __name__ == "__main__":
    main()
