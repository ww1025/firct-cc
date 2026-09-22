# -*- coding: utf-8 -*-
"""礼服智能分配 —— Streamlit 页面渲染入口。"""


def render(get_warehouse_data):
    """app.py 路由到 'smart' 页时调用。"""
    from . import pages
    pages.render(get_warehouse_data)
