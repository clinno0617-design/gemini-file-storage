import streamlit as st
from google import genai
from google.genai import types
import json
import os
from datetime import datetime

# 頁面配置
st.set_page_config(
    page_title="企業法規查詢系統",
    page_icon="📚",
    layout="wide"
)

# 初始化 Gemini 客戶端
@st.cache_resource
def init_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("請設定 GEMINI_API_KEY 環境變數")
        st.info("請在終端執行: export GEMINI_API_KEY='your-api-key'")
        st.stop()
    return genai.Client(api_key=api_key)

try:
    client = init_client()
except Exception as e:
    st.error(f"初始化客戶端失敗: {str(e)}")
    st.info("請確認已正確設定 GEMINI_API_KEY 環境變數")
    st.stop()

# 側邊欄配置
with st.sidebar:
    st.header("⚙️ 系統設定")
    
    # 取得所有可用的 FileSearchStore
    @st.cache_data(ttl=60)
    def get_file_search_stores():
        try:
            stores = []
            for store in client.file_search_stores.list():
                stores.append({
                    "name": store.name,
                    "display_name": store.display_name or store.name
                })
            return stores
        except Exception as e:
            st.error(f"無法載入檔案搜尋商店: {str(e)}")
            return []
    
    stores = get_file_search_stores()
    
    if not stores:
        st.warning("⚠️ 尚未建立任何檔案搜尋商店")
        st.info("請先使用後端管理程式上傳檔案")
        selected_store = None
    else:
        store_options = {s["display_name"]: s["name"] for s in stores}
        selected_display = st.selectbox(
            "選擇知識庫",
            options=list(store_options.keys())
        )
        selected_store = store_options[selected_display]
        
        # 顯示商店資訊
        st.success(f"✅ 已選擇: {selected_display}")
    
    st.divider()
    
    # 搜尋設定
    st.subheader("🔍 搜尋設定")
    
    use_metadata_filter = st.checkbox("使用中繼資料篩選", value=False)
    metadata_filter = ""
    
    if use_metadata_filter:
        metadata_filter = st.text_input(
            "篩選條件",
            placeholder='例如: author="法務部"',
            help="使用 AIP-160 語法,例如: author=\"法務部\" AND year>=2023"
        )
    
    # 模型選擇
    model_choice = st.selectbox(
        "選擇模型",
        options=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3-pro-preview"
        ],
        index=0
    )
    
    if st.button("🔄 重新整理商店列表"):
        st.cache_data.clear()
        st.rerun()

# 主要內容區
st.title("📚 企業法規查詢系統")
st.markdown("---")

# 初始化對話歷史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示對話歷史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # 顯示引用來源
        if "citations" in message and message["citations"]:
            with st.expander("📖 引用來源", expanded=False):
                for i, citation in enumerate(message["citations"], 1):
                    st.markdown(f"**來源 {i}:**")
                    st.markdown(f"- 文件: `{citation['document']}`")
                    if citation.get('chunk_id'):
                        st.markdown(f"- 區塊: `{citation['chunk_id']}`")
                    st.markdown("---")

# 查詢輸入
if selected_store:
    query = st.chat_input("請輸入您的問題...")
    
    if query:
        # 顯示使用者訊息
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # 生成回應
        with st.chat_message("assistant"):
            with st.spinner("🤔 正在思考..."):
                try:
                    # 準備工具配置
                    file_search_config = types.FileSearch(
                        file_search_store_names=[selected_store]
                    )
                    
                    if use_metadata_filter and metadata_filter:
                        file_search_config.metadata_filter = metadata_filter
                    
                    # 呼叫 Gemini API
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=query,
                        config=types.GenerateContentConfig(
                            tools=[
                                types.Tool(file_search=file_search_config)
                            ]
                        )
                    )
                    
                    # 顯示回應
                    answer = response.text
                    st.markdown(answer)
                    
                    # 處理引用資訊
                    citations = []
                    if hasattr(response.candidates[0], 'grounding_metadata'):
                        grounding = response.candidates[0].grounding_metadata
                        if grounding and hasattr(grounding, 'grounding_chunks'):
                            for chunk in grounding.grounding_chunks:
                                if hasattr(chunk, 'web') and chunk.web:
                                    citations.append({
                                        'document': chunk.web.uri if hasattr(chunk.web, 'uri') else 'Unknown',
                                        'chunk_id': chunk.web.title if hasattr(chunk.web, 'title') else ''
                                    })
                    
                    # 顯示引用
                    if citations:
                        with st.expander("📖 引用來源", expanded=False):
                            for i, citation in enumerate(citations, 1):
                                st.markdown(f"**來源 {i}:**")
                                st.markdown(f"- 文件: `{citation['document']}`")
                                if citation.get('chunk_id'):
                                    st.markdown(f"- 區塊: `{citation['chunk_id']}`")
                                st.markdown("---")
                    
                    # 儲存到對話歷史
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "citations": citations
                    })
                    
                except Exception as e:
                    error_msg = f"❌ 查詢失敗: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

else:
    st.info("👈 請先在側邊欄選擇知識庫")

# 清除對話按鈕
if st.session_state.messages:
    if st.button("🗑️ 清除對話歷史"):
        st.session_state.messages = []
        st.rerun()

# 頁尾
st.markdown("---")
st.caption(f"💡 提示: 您可以詢問法規相關問題,系統會從知識庫中搜尋相關內容並提供答案 | 當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")