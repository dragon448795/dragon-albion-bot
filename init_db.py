import sqlite3
import os

def init_database():
    # 確保 data 資料夾存在
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # 連接到資料庫
    conn = sqlite3.connect("data/dragon.db")
    cursor = conn.cursor()
    
    print("正在初始化資料庫表...")
    
    # 1. 創建評核活動表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            evaluation_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            name TEXT NOT NULL,
            ends_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ 創建 evaluations 表")
    
    # 2. 創建出值率記錄表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            evaluation_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            class_type TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            UNIQUE(user_id, evaluation_id)
        )
    ''')
    print("✅ 創建 evaluation_scores 表")
    
    # 3. 創建玩家評分表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            evaluation_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            rated_at TEXT NOT NULL
        )
    ''')
    print("✅ 創建 player_ratings 表")
    
    # 4. 創建抽獎表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            giveaway_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            prize TEXT NOT NULL,
            creator_id TEXT NOT NULL,
            winner_count INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            ends_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            winners TEXT,
            weighted BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ 創建 giveaways 表")
    
    # 5. 創建用戶表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ 創建 users 表")
    
    conn.commit()
    conn.close()
    print("✅ 資料庫初始化完成！")

if __name__ == "__main__":
    init_database()