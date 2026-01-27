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
    
    # 系統提示詞設定
    st.subheader("📝 系統提示詞")
    
    # 預設的法規查詢系統提示詞
    default_system_prompt = """你是一個專業的法規查詢助手。請遵循以下規則回答問題:

1. **直接列出相關法規條文**: 完整引用條文內容,不要省略
2. **不要解釋說明**: 只提供法條原文,不需要額外解釋或評論
3. **明確標註出處**: 每條法規必須標註法規名稱、條號和項次

回答格式範例:
【勞動基準法第30條】
勞工正常工作時間,每日不得超過八小時,每週不得超過四十小時。

【勞動基準法第32條第1項】
雇主有使勞工在正常工作時間以外工作之必要者,雇主經工會同意,如事業單位無工會者,經勞資會議同意後,得將工作時間延長之。

請嚴格遵循以上格式,確保引用準確。"""
    
    use_custom_prompt = st.checkbox("自訂系統提示詞", value=False)
    
    if use_custom_prompt:
        system_prompt = st.text_area(
            "系統提示詞",
            value=default_system_prompt,
            height=300,
            help="定義 AI 助手的行為和回答風格"
        )
    else:
        system_prompt = default_system_prompt
        with st.expander("查看預設提示詞"):
            st.code(default_system_prompt, language="text")
    
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

# 初始化 chunks 記錄
if "chunks_history" not in st.session_state:
    st.session_state.chunks_history = []

# 顯示對話歷史
for idx, message in enumerate(st.session_state.messages):
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
        
        # 顯示檢索到的 chunks
        if message["role"] == "assistant" and idx < len(st.session_state.chunks_history):
            chunks_data = st.session_state.chunks_history[idx]
            if chunks_data:
                with st.expander(f"🔍 查看檢索內容 ({len(chunks_data)} 個區塊)", expanded=False):
                    for i, chunk in enumerate(chunks_data, 1):
                        st.markdown(f"### 📄 區塊 {i}")
                        st.markdown(f"**來源:** {chunk.get('source', 'Unknown')}")
                        st.markdown("**內容:**")
                        st.text_area(
                            f"chunk_{idx}_{i}",
                            value=chunk.get('text', ''),
                            height=150,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                        if i < len(chunks_data):
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
                    
                    # 準備訊息內容 (加入系統提示詞)
                    contents = [
                        types.Content(
                            role="user",
                            parts=[types.Part(text=system_prompt)]
                        ),
                        types.Content(
                            role="model",
                            parts=[types.Part(text="我了解。我會嚴格遵循您的指示:只列出法規條文原文,不做解釋,並明確標註出處。")]
                        ),
                        types.Content(
                            role="user",
                            parts=[types.Part(text=query)]
                        )
                    ]
                    
                    # 呼叫 Gemini API
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=contents,
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
                    chunks_data = []
                    
                    if hasattr(response.candidates[0], 'grounding_metadata'):
                        grounding = response.candidates[0].grounding_metadata
                        
                        # 提取引用
                        if grounding and hasattr(grounding, 'grounding_chunks'):
                            for chunk in grounding.grounding_chunks:
                                # 提取引用資訊
                                if hasattr(chunk, 'web') and chunk.web:
                                    citations.append({
                                        'document': chunk.web.uri if hasattr(chunk.web, 'uri') else 'Unknown',
                                        'chunk_id': chunk.web.title if hasattr(chunk.web, 'title') else ''
                                    })
                                
                                # 提取 chunk 內容
                                chunk_info = {}
                                if hasattr(chunk, 'web') and chunk.web:
                                    chunk_info['source'] = chunk.web.uri if hasattr(chunk.web, 'uri') else 'Unknown'
                                    chunk_info['text'] = chunk.web.title if hasattr(chunk.web, 'title') else ''
                                
                                # 嘗試獲取實際文本內容
                                if hasattr(chunk, 'retrieved_context'):
                                    chunk_info['text'] = chunk.retrieved_context.text if hasattr(chunk.retrieved_context, 'text') else str(chunk.retrieved_context)
                                elif hasattr(chunk, 'text'):
                                    chunk_info['text'] = chunk.text
                                
                                if chunk_info:
                                    chunks_data.append(chunk_info)
                        
                        # 如果有 grounding_supports,也嘗試提取
                        if grounding and hasattr(grounding, 'grounding_supports'):
                            for support in grounding.grounding_supports:
                                if hasattr(support, 'segment'):
                                    chunk_info = {
                                        'source': 'Grounding Support',
                                        'text': support.segment.text if hasattr(support.segment, 'text') else str(support.segment)
                                    }
                                    chunks_data.append(chunk_info)
                    
                    # 顯示引用
                    if citations:
                        with st.expander("📖 引用來源", expanded=False):
                            for i, citation in enumerate(citations, 1):
                                st.markdown(f"**來源 {i}:**")
                                st.markdown(f"- 文件: `{citation['document']}`")
                                if citation.get('chunk_id'):
                                    st.markdown(f"- 區塊: `{citation['chunk_id']}`")
                                st.markdown("---")
                    
                    # 顯示檢索到的 chunks
                    if chunks_data:
                        with st.expander(f"🔍 查看檢索內容 ({len(chunks_data)} 個區塊)", expanded=False):
                            for i, chunk in enumerate(chunks_data, 1):
                                st.markdown(f"### 📄 區塊 {i}")
                                st.markdown(f"**來源:** {chunk.get('source', 'Unknown')}")
                                st.markdown("**內容:**")
                                st.text_area(
                                    f"chunk_new_{i}",
                                    value=chunk.get('text', ''),
                                    height=150,
                                    disabled=True,
                                    label_visibility="collapsed"
                                )
                                if i < len(chunks_data):
                                    st.markdown("---")
                    
                    # 儲存到對話歷史
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "citations": citations
                    })
                    
                    # 儲存 chunks 到歷史
                    # 需要為每個 assistant 訊息儲存對應的 chunks
                    # 計算當前是第幾個 assistant 訊息
                    assistant_msg_count = sum(1 for m in st.session_state.messages if m["role"] == "assistant")
                    while len(st.session_state.chunks_history) < assistant_msg_count:
                        st.session_state.chunks_history.append(None)
                    st.session_state.chunks_history[-1] = chunks_data
                    
                except Exception as e:
                    error_msg = f"❌ 查詢失敗: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    st.session_state.chunks_history.append(None)

else:
    st.info("👈 請先在側邊欄選擇知識庫")

# 清除對話按鈕
if st.session_state.messages:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🗑️ 清除對話歷史", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chunks_history = []
            st.rerun()
    with col2:
        if st.button("💾 匯出對話記錄", use_container_width=True):
            import json
            from datetime import datetime
            
            export_data = {
                "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "knowledge_base": selected_display if selected_store else "None",
                "conversation": st.session_state.messages
            }
            
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 下載 JSON",
                data=json_str,
                file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# 頁尾
st.markdown("---")
st.caption(f"💡 提示: 您可以詢問法規相關問題,系統會從知識庫中搜尋相關內容並提供答案 | 當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")