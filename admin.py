import streamlit as st
from google import genai
from google.genai import types
import time
import os
import tempfile
from pathlib import Path

# 頁面配置
st.set_page_config(
    page_title="檔案搜尋商店管理系統",
    page_icon="🗄️",
    layout="wide"
)

# 初始化客戶端
@st.cache_resource
def init_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("請設定 GEMINI_API_KEY 環境變數")
        st.stop()
    return genai.Client(api_key=api_key)

try:
    client = init_client()
except Exception as e:
    st.error(f"初始化客戶端失敗: {str(e)}")
    st.info("請確認已正確設定 GEMINI_API_KEY 環境變數")
    st.stop()

st.title("🗄️ 檔案搜尋商店管理系統")
st.markdown("管理您的知識庫和法規文件")
st.markdown("---")

# 標籤頁
tab1, tab2, tab3 = st.tabs(["📁 商店管理", "⬆️ 上傳檔案", "📊 統計資訊"])

# ===== 標籤頁 1: 商店管理 =====
with tab1:
    st.header("管理檔案搜尋商店")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("建立新商店")
        with st.form("create_store_form"):
            new_store_name = st.text_input(
                "商店名稱",
                placeholder="例如: 勞動法規知識庫"
            )
            create_btn = st.form_submit_button("➕ 建立商店", use_container_width=True)
            
            if create_btn and new_store_name:
                with st.spinner("正在建立商店..."):
                    try:
                        store = client.file_search_stores.create(
                            config={'display_name': new_store_name}
                        )
                        st.success(f"✅ 成功建立商店: {new_store_name}")
                        st.info(f"商店 ID: `{store.name}`")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 建立失敗: {str(e)}")
    
    with col2:
        st.subheader("快速操作")
        if st.button("🔄 重新整理列表", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # 顯示現有商店
    st.subheader("現有商店列表")
    
    @st.cache_data(ttl=30)
    def get_stores():
        stores = []
        for store in client.file_search_stores.list():
            create_time = getattr(store, 'create_time', None)
            # 處理 datetime 物件
            if create_time:
                if hasattr(create_time, 'strftime'):
                    create_time_str = create_time.strftime('%Y-%m-%d')
                else:
                    create_time_str = str(create_time)[:10]
            else:
                create_time_str = "未知"
            
            stores.append({
                "name": store.name,
                "display_name": store.display_name or "未命名",
                "create_time": create_time_str
            })
        return stores
    
    stores = get_stores()
    
    if not stores:
        st.info("目前沒有任何商店,請建立一個新商店")
    else:
        for i, store in enumerate(stores):
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.markdown(f"### 📦 {store['display_name']}")
                    st.caption(f"ID: `{store['name']}`")
                
                with col2:
                    if store['create_time'] and store['create_time'] != "未知":
                        st.metric("建立時間", store['create_time'])
                    else:
                        st.caption("建立時間: 未知")
                
                with col3:
                    delete_key = f"delete_{store['name']}"
                    if st.button("🗑️ 刪除", key=delete_key, type="secondary"):
                        try:
                            client.file_search_stores.delete(
                                name=store['name'],
                                config={'force': True}
                            )
                            st.success(f"已刪除商店: {store['display_name']}")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"刪除失敗: {str(e)}")
                
                st.divider()

# ===== 標籤頁 2: 上傳檔案 =====
with tab2:
    st.header("上傳檔案到商店")
    
    # 選擇目標商店
    stores = get_stores()
    
    if not stores:
        st.warning("⚠️ 請先建立一個商店")
    else:
        store_options = {s["display_name"]: s["name"] for s in stores}
        selected_display = st.selectbox(
            "選擇目標商店",
            options=list(store_options.keys())
        )
        selected_store = store_options[selected_display]
        
        st.info(f"將上傳至: **{selected_display}**")
        
        # 上傳方式選擇
        upload_method = st.radio(
            "選擇上傳方式",
            options=["直接上傳", "先上傳後匯入"],
            horizontal=True
        )
        
        # 檔案上傳
        uploaded_files = st.file_uploader(
            "選擇檔案",
            accept_multiple_files=True,
            type=['txt', 'pdf', 'docx', 'xlsx', 'pptx', 'md', 'html', 'json', 'csv']
        )
        
        # 進階設定
        with st.expander("⚙️ 進階設定"):
            col1, col2 = st.columns(2)
            
            with col1:
                use_custom_chunking = st.checkbox("自訂分塊設定")
                if use_custom_chunking:
                    max_tokens = st.slider("每塊最大 Token 數", 100, 1000, 200)
                    overlap_tokens = st.slider("重疊 Token 數", 0, 100, 20)
            
            with col2:
                use_metadata = st.checkbox("新增中繼資料")
                metadata_items = []
                if use_metadata:
                    st.markdown("**中繼資料設定**")
                    author = st.text_input("作者", key="meta_author")
                    year = st.number_input("年份", min_value=1900, max_value=2100, value=2024, key="meta_year")
                    category = st.text_input("分類", key="meta_category")
                    
                    if author:
                        metadata_items.append({"key": "author", "string_value": author})
                    if year:
                        metadata_items.append({"key": "year", "numeric_value": year})
                    if category:
                        metadata_items.append({"key": "category", "string_value": category})
        
        # 上傳按鈕
        if st.button("🚀 開始上傳", type="primary", use_container_width=True):
            if not uploaded_files:
                st.warning("請先選擇檔案")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_files = len(uploaded_files)
                success_count = 0
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"正在處理: {uploaded_file.name} ({idx+1}/{total_files})")
                    
                    try:
                        # 建立臨時檔案 (跨平台相容)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            temp_path = tmp_file.name
                        
                        if upload_method == "直接上傳":
                            # 準備設定
                            config = {'display_name': uploaded_file.name}
                            
                            if use_custom_chunking:
                                config['chunking_config'] = {
                                    'white_space_config': {
                                        'max_tokens_per_chunk': max_tokens,
                                        'max_overlap_tokens': overlap_tokens
                                    }
                                }
                            
                            if metadata_items:
                                config['custom_metadata'] = metadata_items
                            
                            # 上傳
                            operation = client.file_search_stores.upload_to_file_search_store(
                                file=temp_path,
                                file_search_store_name=selected_store,
                                config=config
                            )
                        else:
                            # 先上傳到 Files API
                            sample_file = client.files.upload(
                                file=temp_path,
                                config={'name': uploaded_file.name}
                            )
                            
                            # 準備匯入設定
                            import_config = {}
                            if metadata_items:
                                import_config['custom_metadata'] = metadata_items
                            
                            # 匯入到商店
                            operation = client.file_search_stores.import_file(
                                file_search_store_name=selected_store,
                                file_name=sample_file.name,
                                **import_config
                            )
                        
                        # 等待操作完成
                        while not operation.done:
                            time.sleep(2)
                            operation = client.operations.get(operation)
                        
                        # 清理臨時檔案
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                        
                        success_count += 1
                        st.success(f"✅ {uploaded_file.name} 上傳成功")
                        
                    except Exception as e:
                        st.error(f"❌ {uploaded_file.name} 上傳失敗: {str(e)}")
                        # 確保清理臨時檔案
                        try:
                            if 'temp_path' in locals():
                                os.unlink(temp_path)
                        except:
                            pass
                    
                    progress_bar.progress((idx + 1) / total_files)
                
                status_text.text(f"完成! 成功上傳 {success_count}/{total_files} 個檔案")
                st.balloons()

# ===== 標籤頁 3: 統計資訊 =====
with tab3:
    st.header("系統統計資訊")
    
    stores = get_stores()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("商店總數", len(stores))
    
    with col2:
        st.metric("支援格式", "20+ 種")
    
    with col3:
        st.metric("最大檔案", "100 MB")
    
    st.divider()
    
    # 各商店詳細資訊
    if stores:
        st.subheader("商店列表")
        
        for store in stores:
            with st.expander(f"📦 {store['display_name']}"):
                st.markdown(f"**商店 ID:** `{store['name']}`")
                st.markdown(f"**建立時間:** {store['create_time']}")
                
                # 顯示商店資訊
                try:
                    store_info = client.file_search_stores.get(name=store['name'])
                    if hasattr(store_info, 'active_documents_count'):
                        st.metric("活躍文件數", store_info.active_documents_count)
                except Exception as e:
                    st.info("無法取得詳細資訊")
                
                st.markdown("---")
                st.caption("💡 注意: 檔案匯入 FileSearchStore 後會轉為嵌入向量,無法直接列出檔案清單")
    
    st.divider()
    
    # 系統說明
    with st.expander("📖 關於 FileSearchStore"):
        st.markdown("""
        ### FileSearchStore 特性
        
        - ✅ **永久儲存**: 資料會無限期保存,除非手動刪除
        - ✅ **嵌入索引**: 檔案自動轉為向量嵌入並建立索引
        - ✅ **語意搜尋**: 支援自然語言查詢
        - ⚠️ **不可列出**: 已匯入的檔案無法直接列出,只能透過查詢使用
        
        ### 儲存容量限制
        
        | 層級 | 容量 |
        |------|------|
        | 免費版 | 1 GB |
        | 第 1 級 | 10 GB |
        | 第 2 級 | 100 GB |
        | 第 3 級 | 1 TB |
        
        ### 成本說明
        
        - **首次索引**: $0.15 / 百萬 tokens
        - **儲存空間**: 免費
        - **查詢嵌入**: 免費
        """)

# 頁尾
st.markdown("---")
st.caption("💡 提示: 上傳的檔案會永久保存在 FileSearchStore 中,除非手動刪除商店")