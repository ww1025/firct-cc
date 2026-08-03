"""
Streamlit Cloud 部署入口 —— Flask 网站通过 iframe 完整呈现
所有页面内容、功能、样式完全不变
"""
import streamlit as st
import threading
import time
import socket
import os

st.set_page_config(
    page_title="浙江大学国旗仪仗队",
    page_icon="🇨🇳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 找空闲端口
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

# 启动 Flask 服务
if 'flask_ready' not in st.session_state:
    port = find_free_port()
    st.session_state.flask_port = port

    from waitress import serve
    from server import app

    def run():
        serve(app, host='0.0.0.0', port=port, threads=4, channel_timeout=300)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(3)
    st.session_state.flask_ready = True

# 全屏 iframe 内嵌 Flask 网站
url = f"http://localhost:{st.session_state.flask_port}"

st.markdown(f"""
<style>
    #MainMenu {{display: none !important;}}
    header[data-testid="stHeader"] {{display: none !important;}}
    footer {{display: none !important;}}
    .stApp {{margin: 0 !important; padding: 0 !important; overflow: hidden !important;}}
    .stApp > header {{display: none !important;}}
    section.main {{padding: 0 !important;}}
    .block-container {{padding: 0 !important; max-width: 100% !important; margin: 0 !important;}}
    iframe {{
        border: none;
        width: 100vw;
        height: 100vh;
        display: block;
        position: fixed;
        top: 0;
        left: 0;
    }}
</style>
<iframe src="{url}"></iframe>
""", unsafe_allow_html=True)
