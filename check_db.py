import sqlite3

def check_tables():
    conn = sqlite3.connect("data/dragon.db")
    cursor = conn.cursor()
    
    print("檢查資料庫表結構...")
    
    # 1. 列出所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("📊 現有的表：")
    for table in tables:
        print(f"  • {table[0]}")
    
    # 2. 檢查 evaluations 表的結構
    print("\n🔍 檢查 evaluations 表結構：")
    try:
        cursor.execute("PRAGMA table_info(evaluations);")
        columns = cursor.fetchall()
        if columns:
            for col in columns:
                print(f"  • {col[1]} ({col[2]})")
        else:
            print("  ❌ evaluations 表不存在或為空")
    except:
        print("  ❌ 無法讀取 evaluations 表")
    
    # 3. 檢查 evaluation_scores 表
    print("\n🔍 檢查 evaluation_scores 表結構：")
    try:
        cursor.execute("PRAGMA table_info(evaluation_scores);")
        columns = cursor.fetchall()
        if columns:
            for col in columns:
                print(f"  • {col[1]} ({col[2]})")
        else:
            print("  ❌ evaluation_scores 表不存在或為空")
    except:
        print("  ❌ 無法讀取 evaluation_scores 表")
    
    conn.close()

if __name__ == "__main__":
    check_tables()