import sqlite3
import aiosqlite
from datetime import datetime

class Database:
    def __init__(self, db_path='attendance.db'):
        self.db_path = db_path
    
    async def init_db(self):
        """初始化數據庫表格"""
        async with aiosqlite.connect(self.db_path) as db:
            # 用戶表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    default_rating TEXT DEFAULT '普通',
                    total_participations INTEGER DEFAULT 0,
                    attendances INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 活動表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id TEXT PRIMARY KEY,
                    activity_name TEXT,
                    host_id TEXT,
                    channel_id TEXT,
                    message_id TEXT,
                    duration INTEGER,
                    lottery_item TEXT,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ended_at DATETIME
                )
            ''')
            
            # 參與記錄表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS participations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id TEXT,
                    user_id TEXT,
                    role TEXT,
                    rating TEXT DEFAULT '普通',
                    weight REAL,
                    attended INTEGER DEFAULT 0,
                    signed_at DATETIME,
                    FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 評分記錄表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id TEXT,
                    user_id TEXT,
                    rating TEXT,
                    rated_by TEXT,
                    rated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()
        print("✅ 數據庫初始化完成")
    
    async def add_activity(self, activity_id, activity_name, host_id, channel_id, message_id, duration, lottery_item):
        """添加新活動"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO activities 
                (activity_id, activity_name, host_id, channel_id, message_id, duration, lottery_item, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
            ''', (activity_id, activity_name, host_id, channel_id, message_id, duration, lottery_item))
            await db.commit()
    
    async def add_participation(self, activity_id, user_id, role=None):
        """添加參與記錄"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO participations (activity_id, user_id, role, signed_at, attended)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
            ''', (activity_id, user_id, role))
            
            # 更新用戶統計
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, total_participations, attendances)
                VALUES (?,
                    COALESCE((SELECT total_participations FROM users WHERE user_id = ?), 0) + 1,
                    COALESCE((SELECT attendances FROM users WHERE user_id = ?), 0) + 1)
            ''', (user_id, user_id, user_id))
            await db.commit()
    
    async def get_user_stats(self, user_id, days=14):
        """獲取用戶統計"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(attended) as attended,
                    ROUND((SUM(attended) * 100.0 / COUNT(*)), 1) as rate
                FROM participations p
                WHERE p.user_id = ? 
                    AND DATE(p.signed_at) >= DATE('now', ?)
            ''', (user_id, f'-{days} days'))
            
            result = await cursor.fetchone()
            return {
                'total': result[0] or 0,
                'attended': result[1] or 0,
                'rate': result[2] or 0
            }