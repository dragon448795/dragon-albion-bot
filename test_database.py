# test_database.py
import sys
import os

# 加入專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("🧪 測試小雲ALBION機械人資料庫模組")
print("=" * 50)

try:
    # 測試匯入 config
    from config import BOT_CONFIG
    print("✅ config.py 載入成功")
    print(f"   機器人名稱: {BOT_CONFIG['name']}")
    print(f"   版本: {BOT_CONFIG['version']}")
    
    # 測試匯入 database
    from utils.database import db
    print("✅ database.py 載入成功")
    print(f"   資料庫路徑: {db.db_path}")
    
    # 測試連線
    print("\n🔗 測試資料庫連線...")
    if db.test_connection():
        print("✅ 資料庫連線成功")
        
        # 取得表格數量
        counts = db.get_table_counts()
        print("\n📊 資料庫表格狀態:")
        print("-" * 30)
        for table, count in counts.items():
            print(f"   {table:20} : {count:3} 筆記錄")
        
        # 測試用戶操作
        print("\n👤 測試用戶操作...")
        user_id = "test_user_" + str(hash(os.getcwd()))[-8:]
        user = db.get_or_create_user(user_id, "測試玩家")
        
        if user:
            print(f"✅ 用戶操作成功")
            print(f"   用戶ID: {user.get('user_id', 'N/A')}")
            print(f"   用戶名稱: {user.get('discord_name', 'N/A')}")
        else:
            print("❌ 用戶操作失敗")
        
        print("\n" + "=" * 50)
        print("🎉 所有基礎測試通過！")
        print("=" * 50)
        
    else:
        print("❌ 資料庫連線失敗")
        print("\n💡 可能的原因:")
        print("   1. SQLite 未安裝 (Windows 已內建)")
        print("   2. 資料夾權限問題")
        print("   3. 檔案路徑問題")
        
except ImportError as e:
    print(f"❌ 匯入失敗: {e}")
    print("\n💡 請檢查:")
    print("   1. 是否有 __init__.py 檔案在 cogs/ 和 utils/ 資料夾內")
    print("   2. 檔案名稱是否正確")
    
except Exception as e:
    print(f"❌ 測試失敗: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n💡 建議步驟:")
    print("   1. 檢查所有檔案是否都存在")
    print("   2. 確認 Python 版本 (需要 3.8+)")
    print("   3. 確認檔案編碼為 UTF-8")