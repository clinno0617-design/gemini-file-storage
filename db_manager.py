import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import socket
import getpass

class DatabaseManager:
    """PostgreSQL 資料庫管理類別"""
    
    def __init__(self):
        """初始化資料庫連線"""
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'legal_query_system'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '123456')
        }
        self.conn = None
        
    def connect(self):
        """建立資料庫連線"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            return True
        except Exception as e:
            print(f"資料庫連線失敗: {str(e)}")
            return False
    
    def close(self):
        """關閉資料庫連線"""
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """執行 SQL 查詢"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                else:
                    self.conn.commit()
                    return cursor.rowcount
        except Exception as e:
            self.conn.rollback()
            print(f"查詢執行失敗: {str(e)}")
            return None
    
    # ===== 使用者管理 =====
    
    def get_system_info(self) -> Dict[str, str]:
        """取得系統資訊"""
        try:
            hostname = socket.gethostname()
            username = getpass.getuser()
            ip_address = socket.gethostbyname(hostname)
        except:
            hostname = "unknown"
            username = "anonymous"
            ip_address = "127.0.0.1"
        
        return {
            'username': username,
            'hostname': hostname,
            'ip_address': ip_address
        }
    
    def get_or_create_user(self, username: str = None, ip_address: str = None) -> Optional[int]:
        """取得或建立使用者"""
        if not username or not ip_address:
            sys_info = self.get_system_info()
            username = username or sys_info['username']
            ip_address = ip_address or sys_info['ip_address']
        
        # 檢查使用者是否存在
        query = """
            SELECT user_id FROM users 
            WHERE username = %s AND ip_address = %s::inet
        """
        result = self.execute_query(query, (username, ip_address))
        
        if result:
            # 更新最後訪問時間
            update_query = """
                UPDATE users 
                SET last_visit = CURRENT_TIMESTAMP 
                WHERE user_id = %s
            """
            self.execute_query(update_query, (result[0]['user_id'],), fetch=False)
            return result[0]['user_id']
        else:
            # 建立新使用者
            insert_query = """
                INSERT INTO users (username, ip_address) 
                VALUES (%s, %s::inet) 
                RETURNING user_id
            """
            result = self.execute_query(insert_query, (username, ip_address))
            if result:
                return result[0]['user_id']
        
        return None
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """取得使用者資訊"""
        query = "SELECT * FROM user_statistics WHERE user_id = %s"
        result = self.execute_query(query, (user_id,))
        return dict(result[0]) if result else None
    
    # ===== 會話管理 =====
    
    def create_session(self, user_id: int, session_name: str = "新會話", 
                      knowledge_base: str = None) -> Optional[int]:
        """建立新會話"""
        query = """
            INSERT INTO sessions (user_id, session_name, knowledge_base) 
            VALUES (%s, %s, %s) 
            RETURNING session_id
        """
        result = self.execute_query(query, (user_id, session_name, knowledge_base))
        return result[0]['session_id'] if result else None
    
    def get_user_sessions(self, user_id: int, active_only: bool = False) -> List[Dict]:
        """取得使用者的所有會話"""
        query = """
            SELECT * FROM session_summary 
            WHERE user_id = %s
        """
        if active_only:
            query += " AND is_active = TRUE"
        query += " ORDER BY session_start DESC"
        
        # 修正: 需要加入 user_id 欄位
        query = """
            SELECT s.*, u.user_id FROM session_summary s
            JOIN sessions sess ON s.session_id = sess.session_id
            JOIN users u ON sess.user_id = u.user_id
            WHERE u.user_id = %s
        """
        if active_only:
            query += " AND s.is_active = TRUE"
        query += " ORDER BY s.session_start DESC"
        
        result = self.execute_query(query, (user_id,))
        return [dict(row) for row in result] if result else []
    
    def get_session_detail(self, session_id: int) -> Optional[Dict]:
        """取得會話詳細資訊"""
        query = "SELECT * FROM session_summary WHERE session_id = %s"
        result = self.execute_query(query, (session_id,))
        return dict(result[0]) if result else None
    
    def update_session_name(self, session_id: int, new_name: str) -> bool:
        """更新會話名稱"""
        query = "UPDATE sessions SET session_name = %s WHERE session_id = %s"
        result = self.execute_query(query, (new_name, session_id), fetch=False)
        return result is not None and result > 0
    
    def end_session(self, session_id: int) -> bool:
        """結束會話"""
        query = """
            UPDATE sessions 
            SET is_active = FALSE, session_end = CURRENT_TIMESTAMP 
            WHERE session_id = %s
        """
        result = self.execute_query(query, (session_id,), fetch=False)
        return result is not None and result > 0
    
    def delete_session(self, session_id: int) -> bool:
        """刪除會話"""
        query = "DELETE FROM sessions WHERE session_id = %s"
        result = self.execute_query(query, (session_id,), fetch=False)
        return result is not None and result > 0
    
    # ===== 訊息管理 =====
    
    def add_message(self, session_id: int, role: str, content: str, 
                   tokens_used: int = None, has_chunks: bool = False,
                   chunk_count: int = 0) -> Optional[int]:
        """新增訊息"""
        query = """
            INSERT INTO messages 
            (session_id, role, content, tokens_used, has_chunks, chunk_count) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            RETURNING message_id
        """
        result = self.execute_query(
            query, 
            (session_id, role, content, tokens_used, has_chunks, chunk_count)
        )
        return result[0]['message_id'] if result else None
    
    def get_session_messages(self, session_id: int) -> List[Dict]:
        """取得會話的所有訊息"""
        query = """
            SELECT * FROM messages 
            WHERE session_id = %s 
            ORDER BY created_at ASC
        """
        result = self.execute_query(query, (session_id,))
        return [dict(row) for row in result] if result else []
    
    # ===== 檢索區塊管理 =====
    
    def add_retrieval_chunk(self, message_id: int, source_document: str,
                           chunk_text: str, chunk_order: int) -> bool:
        """新增檢索區塊"""
        query = """
            INSERT INTO retrieval_chunks 
            (message_id, source_document, chunk_text, chunk_order) 
            VALUES (%s, %s, %s, %s)
        """
        result = self.execute_query(
            query, 
            (message_id, source_document, chunk_text, chunk_order),
            fetch=False
        )
        return result is not None
    
    def get_message_chunks(self, message_id: int) -> List[Dict]:
        """取得訊息的檢索區塊"""
        query = """
            SELECT * FROM retrieval_chunks 
            WHERE message_id = %s 
            ORDER BY chunk_order ASC
        """
        result = self.execute_query(query, (message_id,))
        return [dict(row) for row in result] if result else []
    
    # ===== 引用來源管理 =====
    
    def add_citation(self, message_id: int, document_name: str,
                    chunk_reference: str, citation_order: int) -> bool:
        """新增引用來源"""
        query = """
            INSERT INTO citations 
            (message_id, document_name, chunk_reference, citation_order) 
            VALUES (%s, %s, %s, %s)
        """
        result = self.execute_query(
            query, 
            (message_id, document_name, chunk_reference, citation_order),
            fetch=False
        )
        return result is not None
    
    def get_message_citations(self, message_id: int) -> List[Dict]:
        """取得訊息的引用來源"""
        query = """
            SELECT * FROM citations 
            WHERE message_id = %s 
            ORDER BY citation_order ASC
        """
        result = self.execute_query(query, (message_id,))
        return [dict(row) for row in result] if result else []
    
    # ===== 安全警告管理 =====
    
    def add_security_warning(self, session_id: int, warning_type: str,
                            warning_message: str, query_text: str,
                            message_id: int = None) -> bool:
        """新增安全警告"""
        query = """
            INSERT INTO security_warnings 
            (session_id, message_id, warning_type, warning_message, query_text) 
            VALUES (%s, %s, %s, %s, %s)
        """
        result = self.execute_query(
            query, 
            (session_id, message_id, warning_type, warning_message, query_text),
            fetch=False
        )
        return result is not None
    
    def get_session_warnings(self, session_id: int) -> List[Dict]:
        """取得會話的安全警告"""
        query = """
            SELECT * FROM security_warnings 
            WHERE session_id = %s 
            ORDER BY created_at DESC
        """
        result = self.execute_query(query, (session_id,))
        return [dict(row) for row in result] if result else []
    
    # ===== 會話設定管理 =====
    
    def save_session_settings(self, session_id: int, model_name: str,
                             system_prompt: str, use_metadata_filter: bool = False,
                             metadata_filter: str = None, 
                             security_enabled: bool = True) -> bool:
        """儲存會話設定"""
        query = """
            INSERT INTO session_settings 
            (session_id, model_name, system_prompt, use_metadata_filter, 
             metadata_filter, security_enabled) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        result = self.execute_query(
            query, 
            (session_id, model_name, system_prompt, use_metadata_filter,
             metadata_filter, security_enabled),
            fetch=False
        )
        return result is not None
    
    def get_session_settings(self, session_id: int) -> Optional[Dict]:
        """取得會話設定"""
        query = """
            SELECT * FROM session_settings 
            WHERE session_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        result = self.execute_query(query, (session_id,))
        return dict(result[0]) if result else None
    
    # ===== 統計查詢 =====
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得系統統計資訊"""
        stats = {}
        
        # 總使用者數
        query = "SELECT COUNT(*) as total FROM users"
        result = self.execute_query(query)
        stats['total_users'] = result[0]['total'] if result else 0
        
        # 總會話數
        query = "SELECT COUNT(*) as total FROM sessions"
        result = self.execute_query(query)
        stats['total_sessions'] = result[0]['total'] if result else 0
        
        # 總訊息數
        query = "SELECT COUNT(*) as total FROM messages"
        result = self.execute_query(query)
        stats['total_messages'] = result[0]['total'] if result else 0
        
        # 今日活躍會話
        query = """
            SELECT COUNT(*) as total FROM sessions 
            WHERE DATE(session_start) = CURRENT_DATE
        """
        result = self.execute_query(query)
        stats['today_sessions'] = result[0]['total'] if result else 0
        
        # 安全警告數
        query = "SELECT COUNT(*) as total FROM security_warnings"
        result = self.execute_query(query)
        stats['total_warnings'] = result[0]['total'] if result else 0
        
        return stats