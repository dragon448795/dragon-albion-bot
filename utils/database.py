# -*- coding: utf-8 -*-
"""
資料庫管理模組
使用 SQLite 儲存數據
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
from pathlib import Path

from config import DATABASE_CONFIG

class DatabaseManager:
    """資料庫管理類別"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 使用 config 中的設定
        self.db_path = DATABASE_CONFIG["path"]
        self.backup_path = DATABASE_CONFIG["backup_path"]
        
        self._ensure_directories()
        self._init_database()
        self._initialized = True
        
        print(f"✅ 資料庫初始化完成: {self.db_path}")
    
    def _ensure_directories(self):
        """確保必要的目錄存在"""
        # 建立資料目錄
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        backups_dir = Path("data/backups")
        backups_dir.mkdir(exist_ok=True)
        
        print(f"📁 資料目錄已建立: {data_dir.absolute()}")
    
    def _init_database(self):
        """初始化資料庫表格"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 啟用外鍵約束
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # 用戶資料表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    discord_name TEXT,
                    albion_name TEXT,
                    preferred_role TEXT DEFAULT '其他',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 評核活動表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS evaluations (
                    eval_id TEXT PRIMARY KEY,
                    message_id TEXT UNIQUE,
                    channel_id TEXT,
                    guild_id TEXT,
                    name TEXT NOT NULL,
                    creator_id TEXT NOT NULL,
                    duration INTEGER DEFAULT 90,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP,
                    participants TEXT DEFAULT '{}',
                    ratings TEXT DEFAULT '{}',
                    results TEXT DEFAULT '{}'
                )
            ''')
            
            # 抽獎活動表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    giveaway_id TEXT PRIMARY KEY,
                    message_id TEXT UNIQUE,
                    channel_id TEXT,
                    guild_id TEXT,
                    prize TEXT NOT NULL,
                    creator_id TEXT NOT NULL,
                    winner_count INTEGER DEFAULT 1,
                    duration INTEGER DEFAULT 60,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP,
                    participants TEXT DEFAULT '{}',
                    winners TEXT DEFAULT '[]',
                    weighted BOOLEAN DEFAULT 0,
                    source_eval_id TEXT
                )
            ''')
            
            # 出值率記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    eval_id TEXT NOT NULL,
                    rating TEXT,
                    role TEXT,
                    base_weight REAL,
                    role_bonus REAL,
                    final_value_rate REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 系統記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            print("✅ 資料庫表格建立完成")
    
    def get_connection(self):
        """取得資料庫連線"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 允許以字典方式存取
        return conn
    
    # === 用戶管理方法 ===
    
    def get_or_create_user(self, user_id: str, discord_name: str) -> Dict:
        """取得或創建用戶資料"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 檢查用戶是否存在
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if user:
                # 更新最後活動時間
                cursor.execute(
                    'UPDATE users SET last_active = ?, discord_name = ? WHERE user_id = ?',
                    (datetime.now().isoformat(), discord_name, user_id)
                )
                conn.commit()
                conn.close()
                return dict(user)
            else:
                # 創建新用戶
                cursor.execute('''
                    INSERT INTO users (user_id, discord_name, created_at, last_active)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, discord_name, 
                     datetime.now().isoformat(), 
                     datetime.now().isoformat()))
                
                conn.commit()
                
                # 取得新創建的用戶
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                new_user = cursor.fetchone()
                conn.close()
                
                return dict(new_user) if new_user else {}
                
        except Exception as e:
            print(f"❌ 用戶操作失敗: {e}")
            if 'conn' in locals():
                conn.close()
            return {}
    
    def update_user_role(self, user_id: str, role: str) -> bool:
        """更新用戶偏好職業"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE users SET preferred_role = ? WHERE user_id = ?',
                (role, user_id)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 更新用戶職業失敗: {e}")
            return False
    
    # === 抽獎活動方法 ===
    
    def create_giveaway(self, giveaway_data: Dict) -> bool:
        """創建抽獎活動"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO giveaways 
                (giveaway_id, message_id, channel_id, guild_id, prize, 
                 creator_id, winner_count, duration, status, ends_at, weighted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                giveaway_data['giveaway_id'],
                giveaway_data['message_id'],
                giveaway_data['channel_id'],
                giveaway_data['guild_id'],
                giveaway_data['prize'],
                giveaway_data['creator_id'],
                giveaway_data['winner_count'],
                giveaway_data['duration'],
                'active',
                giveaway_data['ends_at'],
                giveaway_data.get('weighted', False)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 創建抽獎失敗: {e}")
            return False
    
    def get_giveaway(self, giveaway_id: str) -> Optional[Dict]:
        """取得抽獎資料"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM giveaways WHERE giveaway_id = ?', (giveaway_id,))
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"❌ 取得抽獎失敗: {e}")
            return None
    
    def get_giveaway_by_message_id(self, message_id: str) -> Optional[Dict]:
        """根據訊息ID取得抽獎資料"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM giveaways WHERE message_id = ?', (message_id,))
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"❌ 根據訊息ID取得抽獎失敗: {e}")
            return None
    
    def update_giveaway_status(self, giveaway_id: str, status: str, winners: List[str] = None) -> bool:
        """更新抽獎狀態"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if winners:
                cursor.execute('''
                    UPDATE giveaways 
                    SET status = ?, winners = ?
                    WHERE giveaway_id = ?
                ''', (status, json.dumps(winners), giveaway_id))
            else:
                cursor.execute('''
                    UPDATE giveaways 
                    SET status = ?
                    WHERE giveaway_id = ?
                ''', (status, giveaway_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 更新抽獎狀態失敗: {e}")
            return False
    
    def get_active_giveaways(self, guild_id: str) -> List[Dict]:
        """取得進行中的抽獎活動"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM giveaways 
                WHERE guild_id = ? AND status = 'active'
                ORDER BY ends_at ASC
            ''', (guild_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"❌ 取得進行中抽獎失敗: {e}")
            return []
    
    # === 評核活動方法 ===
    
    def create_evaluation(self, eval_data: Dict) -> bool:
        """創建評核活動"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO evaluations 
                (eval_id, message_id, channel_id, guild_id, name, creator_id, 
                 duration, status, ends_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                eval_data['eval_id'],
                eval_data['message_id'],
                eval_data['channel_id'],
                eval_data['guild_id'],
                eval_data['name'],
                eval_data['creator_id'],
                eval_data['duration'],
                'active',
                eval_data['ends_at']
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 創建評核活動失敗: {e}")
            return False
    
    def get_evaluation(self, eval_id: str) -> Optional[Dict]:
        """取得評核活動資料"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM evaluations WHERE eval_id = ?', (eval_id,))
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"❌ 取得評核活動失敗: {e}")
            return None
    
    # === 出值率記錄方法 ===
    
    def save_performance_record(self, record_data: Dict) -> bool:
        """儲存出值率記錄"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_records 
                (user_id, eval_id, rating, role, base_weight, 
                 role_bonus, final_value_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_data['user_id'],
                record_data['eval_id'],
                record_data['rating'],
                record_data['role'],
                record_data['base_weight'],
                record_data['role_bonus'],
                record_data['final_value_rate']
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 儲存出值率記錄失敗: {e}")
            return False
    
    def get_user_performance(self, user_id: str, limit: int = 10) -> List[Dict]:
        """取得用戶的出值率記錄"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT pr.*, e.name as eval_name, e.created_at as eval_date
                FROM performance_records pr
                JOIN evaluations e ON pr.eval_id = e.eval_id
                WHERE pr.user_id = ?
                ORDER BY pr.recorded_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            records = []
            for row in cursor.fetchall():
                records.append(dict(row))
            
            conn.close()
            return records
            
        except Exception as e:
            print(f"❌ 取得用戶出值率失敗: {e}")
            return []
    
    # === 系統方法 ===
    
    def test_connection(self) -> bool:
        """測試資料庫連線"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 執行簡單查詢
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            conn.close()
            return True if result else False
            
        except Exception as e:
            print(f"❌ 資料庫連線測試失敗: {e}")
            return False
    
    def get_table_counts(self) -> Dict[str, int]:
        """取得各表格的記錄數量"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            tables = ['users', 'evaluations', 'giveaways', 'performance_records']
            counts = {}
            
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                result = cursor.fetchone()
                counts[table] = result['count'] if result else 0
            
            conn.close()
            return counts
            
        except Exception as e:
            print(f"❌ 取得表格數量失敗: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30):
        """清理舊數據"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 清理舊的評核活動
            cursor.execute('''
                DELETE FROM evaluations 
                WHERE created_at < ? AND status = 'ended'
            ''', (cutoff_date,))
            
            # 清理舊的抽獎活動
            cursor.execute('''
                DELETE FROM giveaways 
                WHERE created_at < ? AND status = 'ended'
            ''', (cutoff_date,))
            
            deleted_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            print(f"✅ 已清理 {deleted_rows} 筆舊數據（{days}天前）")
            return deleted_rows
            
        except Exception as e:
            print(f"❌ 清理數據失敗: {e}")
            return 0
    
    def backup_database(self) -> bool:
        """備份資料庫"""
        try:
            backup_file = f"{self.backup_path}dragon_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            # 複製資料庫檔案
            import shutil
            shutil.copy2(self.db_path, backup_file)
            
            print(f"✅ 資料庫已備份至: {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ 資料庫備份失敗: {e}")
            return False

# 建立全域資料庫實例
db = DatabaseManager()

# 測試用
if __name__ == "__main__":
    print("🧪 測試資料庫模組...")
    print(f"📁 資料庫路徑: {db.db_path}")
    
    if db.test_connection():
        print("✅ 資料庫連線正常")
        
        counts = db.get_table_counts()
        print("📊 表格記錄數量:")
        for table, count in counts.items():
            print(f"  {table}: {count} 筆")
        
        # 測試用戶操作
        test_user = db.get_or_create_user("test_user_123", "測試用戶")
        print(f"👤 測試用戶: {test_user.get('discord_name', 'N/A')}")
        
    else:
        print("❌ 資料庫連線失敗")