import sqlite3
import os

def force_init():
    # 確保 data 資料夾存在
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # 連接到資料庫
    conn = sqlite3.connect("data/dragon.db")
    cursor = conn.cursor()
    
    print("🗑️ 刪除舊表...")
    
    # 刪除所有相關表
    tables = ["evaluations", "evaluation_scores", "player_ratings", "giveaways", "users"]
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"  ✅ 刪除 {table} 表")
        except:
            print(f"  ⚠️ 無法刪除 {table} 表")
    
    print("\n📊 創建新表...")
    
    # 創建 evaluations 表（使用正確的欄位名稱）
    cursor.execute('''
        CREATE TABLE evaluations (
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
    print("  ✅ 創建 evaluations 表")
    
    # 創建 evaluation_scores 表
    cursor.execute('''
        CREATE TABLE evaluation_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            evaluation_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            class_type TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            UNIQUE(user_id, evaluation_id)
        )
    ''')
    print("  ✅ 創建 evaluation_scores 表")
    
    # 創建 player_ratings 表
    cursor.execute('''
        CREATE TABLE player_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            evaluation_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            rated_at TEXT NOT NULL
        )
    ''')
    print("  ✅ 創建 player_ratings 表")
    
    # 創建 giveaways 表
    cursor.execute('''
        CREATE TABLE giveaways (
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
    print("  ✅ 創建 giveaways 表")
    
    # 創建 users 表
    cursor.execute('''
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✅ 創建 users 表")
    
    conn.commit()
    
    print("\n🔍 驗證表結構...")
    
    # 檢查 evaluations 表的欄位
    cursor.execute("PRAGMA table_info(evaluations);")
    columns = cursor.fetchall()
    print("  evaluations 表欄位：")
    for col in columns:
        print(f"    • {col[1]} ({col[2]})")
    
    conn.close()
    
    print("\n✅ 強制初始化完成！")

if __name__ == "__main__":
    force_init()