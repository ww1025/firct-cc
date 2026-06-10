"""news_fetcher.py —— 新闻数据读取层

架构：从本地 news_cache.json 读取预抓取的热搜数据。
页面调用 fetch_emotion_news() 瞬间返回（读文件 < 1ms）。

新闻刷新方式：运行 refresh_news.py 脚本更新 news_cache.json。
该脚本尝试多种方式（urllib → requests → 手动）抓取百度/微博热搜。
"""

import json
import os
import time
import threading
from typing import List, Dict

# =============================================================================
# 缓存文件路径
# =============================================================================
_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_cache.json")

# 内存缓存
_cache_data: Dict[str, List[Dict]] = {}
_cache_time: str = ""
_cache_lock = threading.Lock()
_loaded = False


def _load_cache() -> Dict[str, List[Dict]]:
    """从 JSON 文件加载新闻缓存。"""
    if not os.path.exists(_CACHE_FILE):
        return {}
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("emotions", {})
    except Exception:
        return {}


def _auto_reload():
    """检查文件修改时间，如文件已更新则重新加载。"""
    global _cache_data, _cache_time, _loaded
    try:
        mtime = os.path.getmtime(_CACHE_FILE)
        mtime_str = time.strftime("%H:%M", time.localtime(mtime))
    except OSError:
        mtime_str = ""
        mtime = 0

    with _cache_lock:
        if not _loaded or mtime_str != _cache_time:
            _cache_data = _load_cache()
            _cache_time = mtime_str
            _loaded = True


# =============================================================================
# 对外接口 —— 纯文件读取
# =============================================================================

def fetch_emotion_news() -> Dict[str, List[Dict]]:
    """
    从本地缓存文件读取新闻数据。瞬间返回，绝不阻塞。

    Returns:
        {"乐乐": [{title, source, time}, ...], ...}
        缓存文件不存在时返回空 dict。
    """
    _auto_reload()
    with _cache_lock:
        return dict(_cache_data)


def get_last_fetch_time() -> str:
    """返回缓存文件的最后更新时间。"""
    try:
        mtime = os.path.getmtime(_CACHE_FILE)
        return time.strftime("%H:%M", time.localtime(mtime))
    except OSError:
        return ""


def get_cache_total() -> int:
    """返回缓存中的新闻总数。"""
    data = fetch_emotion_news()
    return sum(len(v) for v in data.values())
