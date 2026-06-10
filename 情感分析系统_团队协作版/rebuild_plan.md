# app.py 重建方案

## 架构
- Streamlit 多页面：`st.session_state.active_page` 路由
- 5 个页面：主页 / 百科 / 数据看板 / 晴雨表 / 场景沙盒
- 共用侧边栏（品牌头 + 历史 + 设置）
- CSS 注入（浙大蓝主题）

## 页面分解

### 1. 主页 (active_page = None)
- 情感分析输入区（原 temp_extract 版本）
- 四个模块导航按钮：百科 / 数据看板 / 晴雨表 / 场景沙盒
- 分析结果展示+历史记录

### 2. 百科 (encyclopedia)
- 头脑特工队 9 角色轮播图
- 角色卡片：乐乐/忧忧/怒怒/怕怕/厌厌/丧丧/焦焦/慕慕/尬尬
- 角色信息：情绪特征、心理学依据、生存意义
- 情绪科学知识

### 3. 数据看板 (algorithm)
- 模型统计：训练样本、TF-IDF 特征维度、准确率
- 词云可视化
- 逻辑回归原理图解
- 新闻热搜情绪分布

### 4. 晴雨表 (moodbar)
- 24h 情绪波动模拟曲线
- 情绪树洞互动区

### 5. 场景沙盒 (scenarios)
- st.components.v1.html(build_scenarios_dashboard_html())
- 完整场景模拟沙盒（从 _final_fix.py 提取）

## 关键数据源
- emotion_engine.py: clean_text, predict, EMOTION_CONFIG, load_models, LABEL_TO_CN
- news_fetcher.py: fetch_emotion_news(), get_last_fetch_time()
- _final_fix.py: build_scenarios_dashboard_html() 完整代码
- news_cache.json: 新闻缓存数据
