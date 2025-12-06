# -*- coding: utf-8 -*-
"""
小雲ALBION機械人設定檔
版本: 1.0.0
"""

import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# ========== 機器人基本設定 ==========
BOT_CONFIG = {
    "name": os.getenv("BOT_NAME", "小雲ALBION機械人"),
    "version": os.getenv("BOT_VERSION", "1.0.0"),
    "author": "小雲團隊",
    "description": "ALBION ONLINE 戰績評核與抽獎系統",
    "color": 0x7289DA,  # Discord 藍色
    "footer_text": "🤖 小雲ALBION機械人 v1.0.0",
    "prefix": os.getenv("BOT_PREFIX", "!"),
}

# ========== 權限設定 ==========
PERMISSIONS = {
    # 可以創建評核活動的角色
    "eval_creator_roles": ["戰隊領袖", "資深指揮官", "HOST", "管理員", "Admin"],
    
    # 可以管理所有活動的角色
    "admin_roles": ["管理員", "創建者", "Admin", "Owner"],
    
    # 公開指令（所有人都可用）
    "public_commands": [
        "幫助", "抽獎類型", "創建抽獎", "我的出值率",
        "導出報表", "活動列表", "機器人狀態"
    ]
}

# ========== 出值率計算設定 ==========
EVALUATION_CONFIG = {
    # 評級權重
    "rating_weights": {
        "優秀": 1.2,   # +20%
        "標準": 1.0,   # 正常
        "待改進": 0.8, # -20%
        "非常差": 0.2  # -80%
    },
    
    # 職業加成
    "role_bonus": {
        "補師": 1.2,   # +20%
        "坦克": 1.05,  # +5%
        "支援": 1.03,  # +3%
        "輸出": 1.0,   # 無加成
        "其他": 1.0    # 無加成
    },
    
    # 預設截止時間（分鐘）
    "default_duration": 90,
    
    # 評級選項
    "rating_options": ["優秀", "標準", "待改進", "非常差"],
    
    # 簽到表情
    "checkin_emoji": "✅"
}

# ========== 抽獎設定 ==========
GIVEAWAY_CONFIG = {
    # 預設截止時間（分鐘）
    "default_duration": 60,
    
    # 最大獲獎人數
    "max_winners": 50,
    
    # 最小獲獎人數
    "min_winners": 1,
    
    # 參與表情
    "participation_emoji": "🎟️",
    
    # 最小參與人數
    "min_participants": 1
}

# ========== 資料庫設定 ==========
DATABASE_CONFIG = {
    "path": os.getenv("DATABASE_PATH", "data/dragon.db"),  # 改用 dragon.db
    "backup_path": "data/backups/",
    
    # 資料保留時間（天）
    "retention_days": {
        "giveaways": 30,      # 抽獎記錄保留30天
        "evaluations": 90,    # 評核記錄保留90天
        "user_data": 365      # 用戶數據保留1年
    }
}

# ========== 系統設定 ==========
SYSTEM_CONFIG = {
    "debug_mode": True,  # 開發模式
    "log_level": "INFO",  # 日誌等級
    "timezone": "Asia/Taipei",  # 時區
}

# ========== 計算工具設定 ==========
CALCULATOR_CONFIG = {
    # 出值率計算公式
    "value_rate_formula": "基礎權重 × 職業加成",
    
    # 權重上限
    "max_weight": 3.0,
    
    # 權重下限
    "min_weight": 0.1,
}

# ========== 訊息格式設定 ==========
MESSAGE_FORMAT = {
    # Embed 顏色
    "colors": {
        "success": 0x43B581,    # 綠色
        "error": 0xF04747,      # 紅色
        "warning": 0xFAA61A,    # 橙色
        "info": 0x7289DA,       # 藍色
        "giveaway": 0xFFD700,   # 金色
        "evaluation": 0x9B59B6  # 紫色
    },
    
    # 表情符號
    "emojis": {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "giveaway": "🎉",
        "evaluation": "📊",
        "healer": "💚",
        "tank": "🛡️",
        "dps": "⚔️",
        "support": "🔄"
    }
}

# ========== 時間設定 ==========
TIME_CONFIG = {
    # 時間格式
    "datetime_format": "%Y-%m-%d %H:%M:%S",
    "date_format": "%Y-%m-%d",
    "time_format": "%H:%M:%S",
    
    # 預設時間（秒）
    "default_giveaway_duration": 3600,      # 1小時
    "default_evaluation_duration": 5400,    # 1.5小時
    "cleanup_interval": 86400,              # 24小時
}

# ========== 檔案路徑設定 ==========
PATH_CONFIG = {
    "database": "data/dragon.db",           # 主要資料庫
    "backup_dir": "data/backups/",          # 備份目錄
    "log_dir": "logs/",                     # 日誌目錄
    "export_dir": "exports/",               # 導出目錄
    "cache_dir": "cache/",                  # 快取目錄
}

# ========== 限制設定 ==========
LIMIT_CONFIG = {
    # 每用戶限制
    "max_giveaways_per_user": 5,        # 每個用戶最多同時5個抽獎
    "max_evaluations_per_user": 3,      # 每個用戶最多同時3個評核
    
    # 時間限制
    "min_giveaway_duration": 60,        # 抽獎最短1分鐘
    "max_giveaway_duration": 43200,     # 抽獎最長30天
    
    # 參與限制
    "max_participants": 1000,           # 單一活動最多1000人
}

# ========== 功能開關設定 ==========
FEATURE_FLAGS = {
    "enable_giveaway": True,            # 啟用抽獎功能
    "enable_evaluation": True,          # 啟用評核功能
    "enable_export": True,              # 啟用導出功能
    "enable_statistics": True,          # 啟用統計功能
    "debug_mode": True,                 # 啟用除錯模式
}

print("✅ 設定檔載入完成: config.py")