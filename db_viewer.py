import streamlit as st
import pandas as pd
from db_manager import DatabaseManager
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 頁面配置
st.set_page_config(
    page_title="資料庫管理介面",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化資料庫連線
@st.cache_resource
def init_database():
    db = DatabaseManager()
    if db.connect():
        return db
    else:
        st.error("⚠️ 資料庫連線失敗,請檢查設定")
        st.stop()

db = init_database()

# 標題
st.title("🗄️ 資料庫管理介面")
st.markdown("查詢和管理系統所有資料表")

# 側邊欄 - 導航
with st.sidebar:
    st.header("📋 導航選單")
    
    page = st.radio(
        "選擇頁面",
        [
            "📊 儀表板",
            "👥 使用者管理",
            "💬 會話管理",
            "💭 訊息查詢",
            "🔍 檢索記錄",
            "📖 引用來源",
            "⚠️ 安全警告",
            "⚙️ 會話設定",
            "📈 統計分析",
            "🔧 SQL 查詢"
        ]
    )
    
    st.divider()
    
    # 快速統計
    st.subheader("📈 即時統計")
    stats = db.get_statistics()
    st.metric("總使用者", stats['total_users'])
    st.metric("總會話", stats['total_sessions'])
    st.metric("總訊息", stats['total_messages'])
    st.metric("今日會話", stats['today_sessions'])
    if stats['total_warnings'] > 0:
        st.metric("安全警告", stats['total_warnings'], delta=None, delta_color="off")
    
    st.divider()
    
    # 重新整理
    if st.button("🔄 重新整理", width='stretch'):
        st.cache_data.clear()
        st.rerun()

# ===== 頁面 1: 儀表板 =====
if page == "📊 儀表板":
    st.header("📊 系統儀表板")
    
    # 總覽統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "👥 總使用者數",
            stats['total_users'],
            help="系統中所有註冊使用者"
        )
    
    with col2:
        st.metric(
            "💬 總會話數",
            stats['total_sessions'],
            help="所有建立的對話會話"
        )
    
    with col3:
        st.metric(
            "💭 總訊息數",
            stats['total_messages'],
            help="所有發送的訊息數量"
        )
    
    with col4:
        avg_msg = stats['total_messages'] / stats['total_sessions'] if stats['total_sessions'] > 0 else 0
        st.metric(
            "📊 平均訊息數",
            f"{avg_msg:.1f}",
            help="每個會話的平均訊息數"
        )
    
    st.divider()
    
    # 最近活動
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🕐 最近會話")
        query = """
            SELECT 
                session_id,
                session_name,
                username,
                session_start,
                total_messages,
                is_active
            FROM session_summary
            ORDER BY session_start DESC
            LIMIT 10
        """
        recent_sessions = db.execute_query(query)
        
        if recent_sessions:
            df = pd.DataFrame(recent_sessions)
            df['session_start'] = pd.to_datetime(df['session_start'])
            df['狀態'] = df['is_active'].apply(lambda x: '🟢 活躍' if x else '⚪ 結束')
            
            display_df = df[['session_name', 'username', 'total_messages', '狀態', 'session_start']]
            display_df.columns = ['會話名稱', '使用者', '訊息數', '狀態', '開始時間']
            st.dataframe(display_df, width='stretch', hide_index=True)
        else:
            st.info("尚無會話記錄")
    
    with col2:
        st.subheader("⚠️ 最近警告")
        query = """
            SELECT 
                warning_type,
                warning_message,
                created_at
            FROM security_warnings
            ORDER BY created_at DESC
            LIMIT 10
        """
        recent_warnings = db.execute_query(query)
        
        if recent_warnings:
            df = pd.DataFrame(recent_warnings)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df.columns = ['類型', '訊息', '時間']
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.success("✅ 無安全警告")
    
    st.divider()
    
    # 圖表分析
    st.subheader("📈 趨勢分析")
    
    tab1, tab2, tab3 = st.tabs(["會話趨勢", "使用者活躍度", "訊息分布"])
    
    with tab1:
        # 每日會話數趨勢
        query = """
            SELECT 
                DATE(session_start) as date,
                COUNT(*) as session_count
            FROM sessions
            WHERE session_start >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(session_start)
            ORDER BY date
        """
        trend_data = db.execute_query(query)
        
        if trend_data:
            df = pd.DataFrame(trend_data)
            df['date'] = pd.to_datetime(df['date'])
            
            fig = px.line(
                df, 
                x='date', 
                y='session_count',
                title='每日會話數 (最近30天)',
                labels={'date': '日期', 'session_count': '會話數'}
            )
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("暫無數據")
    
    with tab2:
        # 使用者活躍度
        query = """
            SELECT 
                username,
                total_sessions,
                total_queries
            FROM user_statistics
            ORDER BY total_queries DESC
            LIMIT 10
        """
        user_activity = db.execute_query(query)
        
        if user_activity:
            df = pd.DataFrame(user_activity)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='會話數',
                x=df['username'],
                y=df['total_sessions'],
                marker_color='lightblue'
            ))
            fig.add_trace(go.Bar(
                name='查詢數',
                x=df['username'],
                y=df['total_queries'],
                marker_color='salmon'
            ))
            
            fig.update_layout(
                title='Top 10 活躍使用者',
                xaxis_title='使用者',
                yaxis_title='數量',
                barmode='group'
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("暫無數據")
    
    with tab3:
        # 訊息類型分布
        query = """
            SELECT 
                role,
                COUNT(*) as count
            FROM messages
            GROUP BY role
        """
        msg_dist = db.execute_query(query)
        
        if msg_dist:
            df = pd.DataFrame(msg_dist)
            
            fig = px.pie(
                df,
                values='count',
                names='role',
                title='訊息類型分布',
                hole=0.4
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("暫無數據")

# ===== 頁面 2: 使用者管理 =====
elif page == "👥 使用者管理":
    st.header("👥 使用者管理")
    
    # 查詢選項
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        search_username = st.text_input("🔍 搜尋使用者名稱", "")
    
    with col2:
        sort_by = st.selectbox(
            "排序方式",
            ["最後訪問時間", "總會話數", "總查詢數", "註冊時間"]
        )
    
    with col3:
        limit = st.number_input("顯示數量", 10, 100, 50)
    
    # 查詢使用者
    order_map = {
        "最後訪問時間": "last_visit DESC",
        "總會話數": "total_sessions DESC",
        "總查詢數": "total_queries DESC",
        "註冊時間": "first_visit DESC"
    }
    
    query = f"""
        SELECT * FROM user_statistics
        WHERE username ILIKE %s
        ORDER BY {order_map[sort_by]}
        LIMIT {limit}
    """
    
    users = db.execute_query(query, (f"%{search_username}%",))
    
    if users:
        st.success(f"找到 {len(users)} 位使用者")
        
        df = pd.DataFrame(users)
        df['first_visit'] = pd.to_datetime(df['first_visit']).dt.strftime('%Y-%m-%d %H:%M')
        df['last_visit'] = pd.to_datetime(df['last_visit']).dt.strftime('%Y-%m-%d %H:%M')
        
        # 顯示資料表
        display_df = df[[
            'user_id', 'username', 'ip_address', 
            'total_sessions', 'total_queries', 'active_sessions',
            'total_warnings', 'first_visit', 'last_visit'
        ]]
        
        display_df.columns = [
            'ID', '使用者名稱', 'IP位址',
            '總會話', '總查詢', '活躍會話',
            '警告數', '首次訪問', '最後訪問'
        ]
        
        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(format="%d"),
                "總會話": st.column_config.NumberColumn(format="%d"),
                "總查詢": st.column_config.NumberColumn(format="%d"),
                "活躍會話": st.column_config.NumberColumn(format="%d"),
                "警告數": st.column_config.NumberColumn(format="%d"),
            }
        )
        
        # 使用者詳情
        st.divider()
        st.subheader("📋 使用者詳情")
        
        selected_user_id = st.selectbox(
            "選擇使用者查看詳情",
            df['user_id'].tolist(),
            format_func=lambda x: df[df['user_id']==x]['username'].values[0]
        )
        
        if selected_user_id:
            user_detail = df[df['user_id'] == selected_user_id].iloc[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("使用者ID", user_detail['user_id'])
            with col2:
                st.metric("總會話", user_detail['total_sessions'])
            with col3:
                st.metric("總查詢", user_detail['total_queries'])
            with col4:
                st.metric("警告數", user_detail['total_warnings'])
            
            # 該使用者的會話列表
            st.markdown("**會話列表:**")
            sessions = db.get_user_sessions(selected_user_id)
            
            if sessions:
                sessions_df = pd.DataFrame(sessions)
                sessions_df['session_start'] = pd.to_datetime(sessions_df['session_start']).dt.strftime('%Y-%m-%d %H:%M')
                
                display_sessions = sessions_df[[
                    'session_id', 'session_name', 'total_messages',
                    'warning_count', 'session_start', 'is_active'
                ]]
                display_sessions.columns = [
                    '會話ID', '會話名稱', '訊息數', 
                    '警告數', '開始時間', '是否活躍'
                ]
                
                st.dataframe(display_sessions, width='stretch', hide_index=True)
    else:
        st.info("未找到符合條件的使用者")

# ===== 頁面 3: 會話管理 =====
elif page == "💬 會話管理":
    st.header("💬 會話管理")
    
    # 篩選選項
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_active = st.selectbox(
            "會話狀態",
            ["全部", "活躍", "已結束"]
        )
    
    with col2:
        filter_user = st.text_input("使用者名稱", "")
    
    with col3:
        date_from = st.date_input(
            "開始日期",
            value=datetime.now() - timedelta(days=7)
        )
    
    with col4:
        date_to = st.date_input("結束日期", value=datetime.now())
    
    # 建立查詢
    conditions = []
    params = []
    
    if filter_active == "活躍":
        conditions.append("is_active = TRUE")
    elif filter_active == "已結束":
        conditions.append("is_active = FALSE")
    
    if filter_user:
        conditions.append("username ILIKE %s")
        params.append(f"%{filter_user}%")
    
    conditions.append("DATE(session_start) BETWEEN %s AND %s")
    params.extend([date_from, date_to])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT * FROM session_summary
        WHERE {where_clause}
        ORDER BY session_start DESC
    """
    
    sessions = db.execute_query(query, tuple(params))
    
    if sessions:
        st.success(f"找到 {len(sessions)} 個會話")
        
        df = pd.DataFrame(sessions)
        df['session_start'] = pd.to_datetime(df['session_start']).dt.strftime('%Y-%m-%d %H:%M')
        df['狀態'] = df['is_active'].apply(lambda x: '🟢 活躍' if x else '⚪ 結束')
        
        display_df = df[[
            'session_id', 'session_name', 'username',
            'knowledge_base', 'total_messages', 'warning_count',
            '狀態', 'session_start'
        ]]
        
        display_df.columns = [
            '會話ID', '會話名稱', '使用者',
            '知識庫', '訊息數', '警告數',
            '狀態', '開始時間'
        ]
        
        st.dataframe(display_df, width='stretch', hide_index=True)
        
        # 會話詳情
        st.divider()
        st.subheader("💬 會話詳情")
        
        selected_session = st.selectbox(
            "選擇會話查看詳情",
            df['session_id'].tolist(),
            format_func=lambda x: f"{df[df['session_id']==x]['session_name'].values[0]} (ID: {x})"
        )
        
        if selected_session:
            # 顯示會話訊息
            messages = db.get_session_messages(selected_session)
            
            st.markdown(f"**訊息記錄 ({len(messages)} 則):**")
            
            for msg in messages:
                role_icon = "👤" if msg['role'] == 'user' else "🤖"
                role_color = "blue" if msg['role'] == 'user' else "green"
                
                with st.expander(
                    f"{role_icon} {msg['role'].upper()} - {msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')}"
                ):
                    st.markdown(f":{role_color}[{msg['content']}]")
                    
                    if msg['has_chunks']:
                        st.caption(f"📊 檢索到 {msg['chunk_count']} 個區塊")
                    
                    if msg['tokens_used']:
                        st.caption(f"🎫 使用 {msg['tokens_used']} tokens")
    else:
        st.info("未找到符合條件的會話")

# ===== 頁面 4: 訊息查詢 =====
elif page == "💭 訊息查詢":
    st.header("💭 訊息查詢")
    
    # 搜尋選項
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        search_content = st.text_input("🔍 搜尋訊息內容", "")
    
    with col2:
        filter_role = st.selectbox(
            "訊息類型",
            ["全部", "user", "assistant", "system"]
        )
    
    with col3:
        limit = st.number_input("顯示數量", 10, 500, 100)
    
    # 建立查詢
    conditions = ["content ILIKE %s"]
    params = [f"%{search_content}%"]
    
    if filter_role != "全部":
        conditions.append("role = %s")
        params.append(filter_role)
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT 
            m.*,
            s.session_name,
            u.username
        FROM messages m
        JOIN sessions s ON m.session_id = s.session_id
        JOIN users u ON s.user_id = u.user_id
        WHERE {where_clause}
        ORDER BY m.created_at DESC
        LIMIT {limit}
    """
    
    messages = db.execute_query(query, tuple(params))
    
    if messages:
        st.success(f"找到 {len(messages)} 則訊息")
        
        for msg in messages:
            role_icon = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg['role'], "💭")
            role_color = {"user": "blue", "assistant": "green", "system": "orange"}.get(msg['role'], "gray")
            
            with st.expander(
                f"{role_icon} {msg['username']} - {msg['session_name']} ({msg['created_at'].strftime('%Y-%m-%d %H:%M')})"
            ):
                st.markdown(f":{role_color}[{msg['content']}]")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.caption(f"訊息ID: {msg['message_id']}")
                with col2:
                    st.caption(f"會話ID: {msg['session_id']}")
                with col3:
                    if msg['has_chunks']:
                        st.caption(f"📊 {msg['chunk_count']} 個區塊")
                with col4:
                    if msg['tokens_used']:
                        st.caption(f"🎫 {msg['tokens_used']} tokens")
    else:
        st.info("未找到符合條件的訊息")

# ===== 頁面 5: 檢索記錄 =====
elif page == "🔍 檢索記錄":
    st.header("🔍 檢索記錄")
    
    # 統計
    query = "SELECT COUNT(*) as total FROM retrieval_chunks"
    result = db.execute_query(query)
    total_chunks = result[0]['total'] if result else 0
    
    st.metric("總檢索區塊數", total_chunks)
    
    st.divider()
    
    # 查詢選項
    col1, col2 = st.columns([3, 2])
    
    with col1:
        search_source = st.text_input("🔍 搜尋來源文件", "")
    
    with col2:
        limit = st.number_input("顯示數量", 10, 200, 50)
    
    query = f"""
        SELECT 
            rc.*,
            m.role,
            m.content as query_content,
            s.session_name,
            u.username
        FROM retrieval_chunks rc
        JOIN messages m ON rc.message_id = m.message_id
        JOIN sessions s ON m.session_id = s.session_id
        JOIN users u ON s.user_id = u.user_id
        WHERE rc.source_document ILIKE %s
        ORDER BY rc.created_at DESC
        LIMIT {limit}
    """
    
    chunks = db.execute_query(query, (f"%{search_source}%",))
    
    if chunks:
        st.success(f"找到 {len(chunks)} 個檢索區塊")
        
        for chunk in chunks:
            with st.expander(
                f"📄 {chunk['source_document']} - {chunk['username']} ({chunk['created_at'].strftime('%Y-%m-%d %H:%M')})"
            ):
                st.markdown(f"**原始查詢:** {chunk['query_content'][:100]}...")
                st.markdown("**檢索內容:**")
                st.text_area(
                    "chunk_text",
                    value=chunk['chunk_text'],
                    height=150,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"chunk_{chunk['chunk_id']}"
                )
                st.caption(f"區塊順序: {chunk['chunk_order']}")
    else:
        st.info("未找到檢索記錄")

# ===== 頁面 6: 引用來源 =====
elif page == "📖 引用來源":
    st.header("📖 引用來源")
    
    # 統計
    query = "SELECT COUNT(*) as total FROM citations"
    result = db.execute_query(query)
    total_citations = result[0]['total'] if result else 0
    
    query = "SELECT COUNT(DISTINCT document_name) as total FROM citations"
    result = db.execute_query(query)
    unique_docs = result[0]['total'] if result else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("總引用次數", total_citations)
    with col2:
        st.metric("被引用文件數", unique_docs)
    
    st.divider()
    
    # 最常被引用的文件
    st.subheader("📊 最常被引用的文件")
    
    query = """
        SELECT 
            document_name,
            COUNT(*) as citation_count
        FROM citations
        GROUP BY document_name
        ORDER BY citation_count DESC
        LIMIT 20
    """
    
    top_citations = db.execute_query(query)
    
    if top_citations:
        df = pd.DataFrame(top_citations)
        
        fig = px.bar(
            df,
            x='citation_count',
            y='document_name',
            orientation='h',
            title='Top 20 最常引用文件',
            labels={'document_name': '文件名稱', 'citation_count': '引用次數'}
        )
        st.plotly_chart(fig, width='stretch')
        
        # 詳細列表
        st.subheader("📋 引用詳細記錄")
        
        query = """
            SELECT 
                c.*,
                m.content as message_content,
                s.session_name,
                u.username
            FROM citations c
            JOIN messages m ON c.message_id = m.message_id
            JOIN sessions s ON m.session_id = s.session_id
            JOIN users u ON s.user_id = u.user_id
            ORDER BY c.created_at DESC
            LIMIT 100
        """
        
        citations = db.execute_query(query)
        
        if citations:
            df = pd.DataFrame(citations)
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            display_df = df[[
                'document_name', 'chunk_reference', 'username',
                'session_name', 'citation_order', 'created_at'
            ]]
            
            display_df.columns = [
                '文件名稱', '區塊參照', '使用者',
                '會話名稱', '順序', '時間'
            ]
            
            st.dataframe(display_df, width='stretch', hide_index=True)
    else:
        st.info("暫無引用記錄")

# ===== 頁面 7: 安全警告 =====
elif page == "⚠️ 安全警告":
    st.header("⚠️ 安全警告")
    
    # 統計
    query = "SELECT COUNT(*) as total FROM security_warnings"
    result = db.execute_query(query)
    total_warnings = result[0]['total'] if result else 0
    
    query = """
        SELECT 
            warning_type,
            COUNT(*) as count
        FROM security_warnings
        GROUP BY warning_type
        ORDER BY count DESC
    """
    warning_types = db.execute_query(query)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("總警告數", total_warnings)
        
        if warning_types:
            st.markdown("**警告類型分布:**")
            for wt in warning_types[:5]:
                st.caption(f"{wt['warning_type']}: {wt['count']}")
    
    with col2:
        if warning_types:
            df = pd.DataFrame(warning_types)
            fig = px.pie(
                df,
                values='count',
                names='warning_type',
                title='警告類型分布'
            )
            st.plotly_chart(fig, width='stretch')
    
    st.divider()
    
    # 最近警告
    st.subheader("🕐 最近警告記錄")
    
    query = """
        SELECT 
            sw.*,
            s.session_name,
            u.username
        FROM security_warnings sw
        JOIN sessions s ON sw.session_id = s.session_id
        JOIN users u ON s.user_id = u.user_id
        ORDER BY sw.created_at DESC
        LIMIT 100
    """
    
    warnings = db.execute_query(query)
    
    if warnings:
        for warning in warnings:
            severity_color = "red" if "越獄" in warning['warning_type'] else "orange"
            
            with st.expander(
                f"⚠️ {warning['warning_type']} - {warning['username']} ({warning['created_at'].strftime('%Y-%m-%d %H:%M')})",
                expanded=False
            ):
                st.markdown(f":{severity_color}[{warning['warning_message']}]")
                st.markdown(f"**原始查詢:** {warning['query_text']}")
                st.caption(f"會話: {warning['session_name']}")
    else:
        st.success("✅ 沒有安全警告記錄")

# ===== 頁面 8: 會話設定 =====
elif page == "⚙️ 會話設定":
    st.header("⚙️ 會話設定")
    
    query = """
        SELECT 
            ss.*,
            s.session_name,
            u.username
        FROM session_settings ss
        JOIN sessions s ON ss.session_id = s.session_id
        JOIN users u ON s.user_id = u.user_id
        ORDER BY ss.created_at DESC
        LIMIT 50
    """
    
    settings = db.execute_query(query)
    
    if settings:
        st.success(f"找到 {len(settings)} 個會話設定記錄")
        
        for setting in settings:
            with st.expander(
                f"⚙️ {setting['session_name']} - {setting['username']} ({setting['created_at'].strftime('%Y-%m-%d %H:%M')})"
            ):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**模型:** {setting['model_name']}")
                    st.markdown(f"**中繼資料篩選:** {'是' if setting['use_metadata_filter'] else '否'}")
                
                with col2:
                    if setting['metadata_filter']:
                        st.markdown(f"**篩選條件:** {setting['metadata_filter']}")
                    st.markdown(f"**安全防護:** {'啟用' if setting['security_enabled'] else '停用'}")
                
                with col3:
                    st.caption(f"設定ID: {setting['setting_id']}")
                
                st.markdown("**系統提示詞:**")
                st.code(setting['system_prompt'][:500] + "..." if len(setting['system_prompt']) > 500 else setting['system_prompt'])
    else:
        st.info("暫無會話設定記錄")

# ===== 頁面 9: 統計分析 =====
elif page == "📈 統計分析":
    st.header("📈 統計分析")
    
    # 時間範圍選擇
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input(
            "開始日期",
            value=datetime.now() - timedelta(days=30)
        )
    with col2:
        date_to = st.date_input("結束日期", value=datetime.now())
    
    st.divider()
    
    # 分析報表
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 使用趨勢",
        "👥 使用者分析", 
        "⏱️ 時段分析",
        "📋 綜合報表"
    ])
    
    with tab1:
        st.subheader("使用趨勢分析")
        
        # 每日統計
        query = """
            SELECT 
                DATE(session_start) as date,
                COUNT(DISTINCT session_id) as sessions,
                COUNT(DISTINCT s.user_id) as users,
                SUM(total_messages) as messages
            FROM sessions s
            WHERE DATE(session_start) BETWEEN %s AND %s
            GROUP BY DATE(session_start)
            ORDER BY date
        """
        
        trend = db.execute_query(query, (date_from, date_to))
        
        if trend:
            df = pd.DataFrame(trend)
            df['date'] = pd.to_datetime(df['date'])
            
            # 多線圖
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['sessions'],
                name='會話數',
                mode='lines+markers'
            ))
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['users'],
                name='使用者數',
                mode='lines+markers'
            ))
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['messages'],
                name='訊息數',
                mode='lines+markers',
                yaxis='y2'
            ))
            
            fig.update_layout(
                title='每日使用趨勢',
                xaxis_title='日期',
                yaxis_title='會話數/使用者數',
                yaxis2=dict(
                    title='訊息數',
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, width='stretch')
            
            # 數據表
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("所選時間範圍內無數據")
    
    with tab2:
        st.subheader("使用者行為分析")
        
        # 使用者活躍度分布
        query = """
            SELECT 
                CASE 
                    WHEN total_queries < 10 THEN '1-9次'
                    WHEN total_queries < 50 THEN '10-49次'
                    WHEN total_queries < 100 THEN '50-99次'
                    ELSE '100+次'
                END as query_range,
                COUNT(*) as user_count
            FROM users
            GROUP BY 
                CASE 
                    WHEN total_queries < 10 THEN '1-9次'
                    WHEN total_queries < 50 THEN '10-49次'
                    WHEN total_queries < 100 THEN '50-99次'
                    ELSE '100+次'
                END
            ORDER BY 
                CASE 
                    WHEN CASE 
                        WHEN total_queries < 10 THEN '1-9次'
                        WHEN total_queries < 50 THEN '10-49次'
                        WHEN total_queries < 100 THEN '50-99次'
                        ELSE '100+次'
                    END = '1-9次' THEN 1
                    WHEN CASE 
                        WHEN total_queries < 10 THEN '1-9次'
                        WHEN total_queries < 50 THEN '10-49次'
                        WHEN total_queries < 100 THEN '50-99次'
                        ELSE '100+次'
                    END = '10-49次' THEN 2
                    WHEN CASE 
                        WHEN total_queries < 10 THEN '1-9次'
                        WHEN total_queries < 50 THEN '10-49次'
                        WHEN total_queries < 100 THEN '50-99次'
                        ELSE '100+次'
                    END = '50-99次' THEN 3
                    ELSE 4
                END
        """
        
        user_dist = db.execute_query(query)
        
        if user_dist:
            df = pd.DataFrame(user_dist)
            
            fig = px.bar(
                df,
                x='query_range',
                y='user_count',
                title='使用者查詢次數分布',
                labels={'query_range': '查詢次數範圍', 'user_count': '使用者數'}
            )
            st.plotly_chart(fig, width='stretch')
        
        # Top 使用者
        st.markdown("**Top 20 活躍使用者:**")
        
        query = """
            SELECT 
                username,
                total_sessions,
                total_queries,
                total_warnings,
                last_visit
            FROM user_statistics
            ORDER BY total_queries DESC
            LIMIT 20
        """
        
        top_users = db.execute_query(query)
        
        if top_users:
            df = pd.DataFrame(top_users)
            df['last_visit'] = pd.to_datetime(df['last_visit']).dt.strftime('%Y-%m-%d %H:%M')
            df.columns = ['使用者', '總會話', '總查詢', '警告數', '最後訪問']
            st.dataframe(df, width='stretch', hide_index=True)
    
    with tab3:
        st.subheader("時段分析")
        
        # 每小時分布
        query = """
            SELECT 
                EXTRACT(HOUR FROM session_start) as hour,
                COUNT(*) as session_count
            FROM sessions
            WHERE DATE(session_start) BETWEEN %s AND %s
            GROUP BY EXTRACT(HOUR FROM session_start)
            ORDER BY hour
        """
        
        hourly = db.execute_query(query, (date_from, date_to))
        
        if hourly:
            df = pd.DataFrame(hourly)
            df['hour'] = df['hour'].astype(int)
            
            fig = px.bar(
                df,
                x='hour',
                y='session_count',
                title='每小時會話分布',
                labels={'hour': '時段', 'session_count': '會話數'}
            )
            st.plotly_chart(fig, width='stretch')
        
        # 星期分布
        query = """
            SELECT 
                TO_CHAR(session_start, 'Day') as day_name,
                EXTRACT(DOW FROM session_start) as day_num,
                COUNT(*) as session_count
            FROM sessions
            WHERE DATE(session_start) BETWEEN %s AND %s
            GROUP BY TO_CHAR(session_start, 'Day'), EXTRACT(DOW FROM session_start)
            ORDER BY day_num
        """
        
        weekly = db.execute_query(query, (date_from, date_to))
        
        if weekly:
            df = pd.DataFrame(weekly)
            
            fig = px.bar(
                df,
                x='day_name',
                y='session_count',
                title='星期分布',
                labels={'day_name': '星期', 'session_count': '會話數'}
            )
            st.plotly_chart(fig, width='stretch')
    
    with tab4:
        st.subheader("綜合統計報表")
        
        # 綜合統計
        col1, col2, col3, col4 = st.columns(4)
        
        # 總會話數
        query = """
            SELECT COUNT(*) as total 
            FROM sessions 
            WHERE DATE(session_start) BETWEEN %s AND %s
        """
        result = db.execute_query(query, (date_from, date_to))
        with col1:
            st.metric("總會話", result[0]['total'] if result else 0)
        
        # 總訊息數
        query = """
            SELECT COUNT(*) as total 
            FROM messages m
            JOIN sessions s ON m.session_id = s.session_id
            WHERE DATE(s.session_start) BETWEEN %s AND %s
        """
        result = db.execute_query(query, (date_from, date_to))
        with col2:
            st.metric("總訊息", result[0]['total'] if result else 0)
        
        # 活躍使用者
        query = """
            SELECT COUNT(DISTINCT s.user_id) as total
            FROM sessions s
            WHERE DATE(s.session_start) BETWEEN %s AND %s
        """
        result = db.execute_query(query, (date_from, date_to))
        with col3:
            st.metric("活躍使用者", result[0]['total'] if result else 0)
        
        # 安全警告
        query = """
            SELECT COUNT(*) as total
            FROM security_warnings sw
            WHERE DATE(sw.created_at) BETWEEN %s AND %s
        """
        result = db.execute_query(query, (date_from, date_to))
        with col4:
            st.metric("安全警告", result[0]['total'] if result else 0)
        
        st.divider()
        
        # 詳細統計表
        st.markdown("**詳細統計:**")
        
        query = """
            SELECT 
                COUNT(DISTINCT s.session_id) as total_sessions,
                COUNT(DISTINCT s.user_id) as unique_users,
                COUNT(DISTINCT m.message_id) as total_messages,
                COUNT(DISTINCT CASE WHEN m.role = 'user' THEN m.message_id END) as user_messages,
                COUNT(DISTINCT CASE WHEN m.role = 'assistant' THEN m.message_id END) as ai_messages,
                COUNT(DISTINCT rc.chunk_id) as total_chunks,
                COUNT(DISTINCT c.citation_id) as total_citations,
                COUNT(DISTINCT sw.warning_id) as total_warnings,
                AVG(s.total_messages) as avg_messages_per_session
            FROM sessions s
            LEFT JOIN messages m ON s.session_id = m.session_id
            LEFT JOIN retrieval_chunks rc ON m.message_id = rc.message_id
            LEFT JOIN citations c ON m.message_id = c.message_id
            LEFT JOIN security_warnings sw ON s.session_id = sw.session_id
            WHERE DATE(s.session_start) BETWEEN %s AND %s
        """
        
        stats = db.execute_query(query, (date_from, date_to))
        
        if stats:
            stat = stats[0]
            
            data = {
                "指標": [
                    "總會話數",
                    "獨立使用者數",
                    "總訊息數",
                    "使用者訊息",
                    "AI 回覆",
                    "檢索區塊",
                    "引用次數",
                    "安全警告",
                    "平均訊息/會話"
                ],
                "數值": [
                    int(stat['total_sessions']) if stat['total_sessions'] else 0,
                    int(stat['unique_users']) if stat['unique_users'] else 0,
                    int(stat['total_messages']) if stat['total_messages'] else 0,
                    int(stat['user_messages']) if stat['user_messages'] else 0,
                    int(stat['ai_messages']) if stat['ai_messages'] else 0,
                    int(stat['total_chunks']) if stat['total_chunks'] else 0,
                    int(stat['total_citations']) if stat['total_citations'] else 0,
                    int(stat['total_warnings']) if stat['total_warnings'] else 0,
                    round(float(stat['avg_messages_per_session']), 2) if stat['avg_messages_per_session'] else 0.0
                ]
            }
            
            df = pd.DataFrame(data)
            st.dataframe(df, width='stretch', hide_index=True)

# ===== 頁面 10: SQL 查詢 =====
elif page == "🔧 SQL 查詢":
    st.header("🔧 自訂 SQL 查詢")
    
    st.warning("⚠️ 注意: 此功能僅供管理員使用,請謹慎執行 SQL 查詢")
    
    # 預設查詢範例
    st.subheader("📋 查詢範例")
    
    examples = {
        "查看所有資料表": """
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
        """,
        "查看所有視圖": """
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public';
        """,
        "查看資料表欄位": """
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
        """,
        "最近 24 小時活動": """
SELECT 
    u.username,
    s.session_name,
    COUNT(m.message_id) as message_count,
    MAX(m.created_at) as last_message
FROM users u
JOIN sessions s ON u.user_id = s.user_id
JOIN messages m ON s.session_id = m.session_id
WHERE m.created_at >= NOW() - INTERVAL '24 hours'
GROUP BY u.username, s.session_name
ORDER BY last_message DESC;
        """,
        "檢索效能統計": """
SELECT 
    s.session_name,
    COUNT(rc.chunk_id) as total_chunks,
    AVG(LENGTH(rc.chunk_text)) as avg_chunk_length
FROM sessions s
JOIN messages m ON s.session_id = m.session_id
JOIN retrieval_chunks rc ON m.message_id = rc.message_id
GROUP BY s.session_name
ORDER BY total_chunks DESC
LIMIT 10;
        """
    }
    
    example_choice = st.selectbox("選擇範例查詢", list(examples.keys()))
    
    # SQL 輸入
    sql_query = st.text_area(
        "SQL 查詢語句",
        value=examples[example_choice],
        height=200,
        help="輸入 SELECT 查詢語句"
    )
    
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        execute_btn = st.button("▶️ 執行查詢", type="primary")
    
    with col2:
        clear_btn = st.button("🗑️ 清空")
        if clear_btn:
            st.rerun()
    
    # 執行查詢
    if execute_btn and sql_query.strip():
        # 安全檢查 - 只允許 SELECT 查詢
        if not sql_query.strip().upper().startswith('SELECT'):
            st.error("❌ 僅允許執行 SELECT 查詢")
        else:
            try:
                with st.spinner("執行中..."):
                    result = db.execute_query(sql_query)
                
                if result:
                    st.success(f"✅ 查詢成功! 返回 {len(result)} 筆記錄")
                    
                    # 顯示結果
                    df = pd.DataFrame(result)
                    
                    # 下載按鈕
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 下載 CSV",
                        data=csv,
                        file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # 顯示資料表
                    st.dataframe(df, width='stretch')
                    
                    # 顯示資料型態資訊
                    with st.expander("📊 資料型態資訊"):
                        st.write(df.dtypes)
                else:
                    st.info("查詢無返回結果")
                    
            except Exception as e:
                st.error(f"❌ 查詢執行失敗: {str(e)}")
                st.code(sql_query, language="sql")

# 頁尾
st.divider()
st.caption(f"🕐 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 資料庫管理介面 v1.0")