#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小雲ALBION機械人 1.0
作者: 小雲團隊
版本: 1.0.0
功能: ALBION戰績評核與抽獎系統
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import sys

# 載入環境變數
load_dotenv()

class XiaoYunBot(commands.Bot):
    """小雲ALBION機械人主類別"""
    
    def __init__(self):
        # 設定機器人意圖
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        
        # 初始化父類別
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,  # 自訂幫助指令
            case_insensitive=True  # 指令不分大小寫
        )
        
        # 從 config 取得設定
        from config import BOT_CONFIG
        self.version = BOT_CONFIG["version"]
        self.author = BOT_CONFIG["author"]
        self.description = BOT_CONFIG["description"]
    
    async def setup_hook(self):
        """載入所有功能模組"""
        print("🔧 正在載入功能模組...")
        
        try:
            # 載入自動抽獎模組（時間到自動開獎）
            try:
                await self.load_extension("cogs.giveaway_auto")
                print("✅ 已載入: 自動抽獎模組")
            except Exception as e:
                print(f"❌ 自動抽獎模組載入失敗: {e}")
                print("⚠️  請確認 cogs/giveaway_auto.py 是否存在")
            
            # 載入評核模組（新版）
            try:
                await self.load_extension("cogs.evaluation")
                print("✅ 已載入: 評核模組")
            except Exception as e:
                print(f"❌ 評核模組載入失敗: {e}")
                print("⚠️  請確認 cogs/evaluation.py 是否存在")
            
            print("✅ 所有模組載入完成！")
            
        except Exception as e:
            print(f"❌ 載入模組失敗: {e}")
            print("⚠️  請確認 cogs 資料夾內的檔案是否存在")
    
    async def on_ready(self):
        """機器人上線時執行"""
        print(f"\n{'='*50}")
        print(f"🤖 小雲ALBION機械人 v{self.version}")
        print(f"🔗 已登入: {self.user}")
        print(f"🆔 ID: {self.user.id}")
        print(f"📊 已連接伺服器: {len(self.guilds)} 個")
        print(f"{'='*50}\n")
        
        # 設定機器人狀態
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="ALBION ONLINE | !幫助 或 !help"
            )
        )
        
        # 檢查模組載入狀態
        print("📋 模組載入狀態檢查:")
        
        # 檢查自動抽獎系統
        giveaway_cog = self.get_cog("GiveawayAuto")
        if giveaway_cog:
            active_count = len(giveaway_cog.active_giveaways) if hasattr(giveaway_cog, 'active_giveaways') else 0
            print(f"✅ 自動抽獎系統: 已載入 ({active_count} 個進行中)")
        else:
            print("❌ 自動抽獎系統: 未載入")
        
        # 檢查評核系統
        evaluation_cog = self.get_cog("Evaluation")
        if evaluation_cog:
            print("✅ 評核系統: 已載入")
        else:
            print("❌ 評核系統: 未載入")
        
        print("🎮 機器人準備就緒！")
        
        # 顯示可用指令
        self.display_available_commands()
    
    def display_available_commands(self):
        """顯示可用指令列表"""
        print("\n📋 核心功能已載入:")
        print("  自動抽獎系統（時間到自動開獎）:")
        print("    !創建自動抽獎 \"獎品\" 人數 分鐘 - 創建抽獎（自動開獎）")
        print("    !手動開獎 抽獎ID - 手動提前開獎")
        print("    !抽獎列表 - 查看進行中的抽獎")
        print("    !抽獎資訊 抽獎ID - 查看詳細資訊")
        
        print("\n  評核系統（完整功能）:")
        print("    !創建評核活動 \"活動名稱\" 分鐘 \"抽獎物品\" - 創建評核活動")
        print("    功能: 簽到、職業選擇、按鈕評分、加權抽獎、數據查詢")
        
        print("\n  數據查詢指令:")
        print("    !我的數據 [活動ID] - 查詢個人數據和出值率")
        print("    !詳細數據 活動ID - 查看活動詳細數據")
        print("    !活動列表 [狀態] - 查看活動列表")
        print("    !導出報表 活動ID [格式] - 導出活動報表")
        
        print("\n  系統指令:")
        print("    !幫助 / !help - 顯示所有指令")
        print("    !機器人狀態 / !status - 查看狀態")
        print("\n🎮 輸入 !幫助 或 !help 查看詳細說明")
    
    async def on_command_error(self, ctx, error):
        """指令錯誤處理"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"❌ 未知指令: `{ctx.invoked_with}`\n輸入 `!幫助` 或 `!help` 查看可用指令")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ 缺少參數！使用方式: `{ctx.command.usage or ctx.command.signature}`")
        else:
            await ctx.send(f"❌ 發生錯誤: {error}")
            print(f"⚠️  指令錯誤: {error}")

# 創建機器人實例
bot = XiaoYunBot()

# 幫助指令（放在這裡，因為我們禁用了預設幫助）
@bot.command(name="幫助", aliases=["help"])
async def help_command(ctx):
    """顯示幫助訊息"""
    embed = discord.Embed(
        title="🤖 小雲ALBION機械人 - 幫助",
        description="ALBION ONLINE 戰績評核與抽獎系統",
        color=0x7289DA
    )
    
    embed.add_field(
        name="🎲 自動抽獎指令",
        value=(
            "中文: `!創建自動抽獎 \"獎品\" 獲獎人數 分鐘`\n\n"
            "📝 範例:\n"
            "• `!創建自動抽獎 \"8.3裝備箱\" 3 60`\n"
            "• `!創建自動抽獎 \"傳奇武器箱\" 1 120`\n\n"
            "💡 特色功能：\n"
            "• ⏰ **時間到自動開獎，無需手動指令**\n"
            "• 🎫 按鈕點擊參與\n"
            "• 📊 自動公告中獎者\n"
            "• 🔄 機器人重啟後自動恢復\n\n"
            "其他抽獎指令:\n"
            "• `!手動開獎 抽獎ID` - 提前開獎\n"
            "• `!抽獎列表` - 查看進行中的抽獎\n"
            "• `!抽獎資訊 抽獎ID` - 查看詳細資訊"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 評核系統指令（完整功能）",
        value=(
            "中文: `!創建評核活動 \"活動名稱\" 分鐘 \"抽獎物品\"`\n\n"
            "📝 範例:\n"
            "• `!創建評核活動 \"深淵團攻略\" 60 \"傳奇武器箱\"`\n"
            "• `!創建評核活動 \"水晶戰場\" 90 \"8.4裝備箱\"`\n\n"
            "💡 特色功能：\n"
            "• ✅ **一鍵簽到**（點擊 ✅ 反應）\n"
            "• 💚🛡️⚔️✨ **選擇職業**（點擊職業反應）\n"
            "• ⏰ **自動計時結束**\n"
            "• 🎯 **按鈕評分**（🌟 👍 📉 ❌ 立即生效）\n"
            "• 📊 **自動計算加權分數**\n"
            "• 🎲 **加權抽獎**（根據分數權重）\n"
            "• 🚀 **一鍵完成並公開**\n"
            "• 📈 **完整數據查詢系統**"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📈 數據查詢指令",
        value=(
            "**個人數據查詢:**\n"
            "• `!我的數據 [活動ID]` - 查詢個人數據和出值率\n"
            "• `!詳細數據 活動ID` - 查看活動詳細數據\n\n"
            "**活動管理:**\n"
            "• `!活動列表 [狀態]` - 查看活動列表\n"
            "  (狀態: all/active/completed)\n"
            "• `!導出報表 活動ID [格式]` - 導出活動報表\n"
            "  (格式: csv/txt)\n\n"
            "📝 範例:\n"
            "• `!我的數據` - 查詢所有活動數據\n"
            "• `!我的數據 eval_xxxxx` - 查詢指定活動數據\n"
            "• `!活動列表 active` - 查看進行中的活動\n"
            "• `!導出報表 eval_xxxxx csv` - 導出CSV報表"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ 系統指令",
        value=(
            "• `!機器人狀態` / `!status` - 查看機器人狀態\n"
            "• `!幫助` / `!help` - 顯示此訊息"
        ),
        inline=False
    )
    
    embed.set_footer(text="🤖 小雲ALBION機械人 v1.0.0 | 自動開獎系統已啟用")
    
    await ctx.send(embed=embed)

# 機器人狀態指令
@bot.command(name="機器人狀態", aliases=["status"])
async def bot_status(ctx):
    """顯示機器人狀態"""
    from datetime import datetime
    
    embed = discord.Embed(
        title="🤖 機器人狀態",
        color=0x43B581  # 綠色表示正常
    )
    
    embed.add_field(name="版本", value="1.0.0", inline=True)
    embed.add_field(name="狀態", value="🟢 正常運行", inline=True)
    embed.add_field(name="上線時間", value=datetime.now().strftime("%Y-%m-%d %H:%M"), inline=True)
    
    # 檢查自動抽獎系統狀態
    giveaway_cog = bot.get_cog("GiveawayAuto")
    if giveaway_cog:
        active_count = len(giveaway_cog.active_giveaways) if hasattr(giveaway_cog, 'active_giveaways') else 0
        giveaway_status = f"✅ 正常運行（{active_count} 個進行中）"
    else:
        giveaway_status = "❌ 未載入"
    
    # 檢查評核系統狀態
    evaluation_cog = bot.get_cog("Evaluation")
    if evaluation_cog:
        evaluation_status = "✅ 正常運行"
    else:
        evaluation_status = "❌ 未載入"
    
    embed.add_field(
        name="已載入模組",
        value=(
            f"• 自動抽獎系統: {giveaway_status}\n"
            f"• 評核系統: {evaluation_status}"
        ),
        inline=False
    )
    
    embed.add_field(
        name="伺服器統計",
        value=(
            f"• 已連接伺服器: {len(bot.guilds)} 個\n"
            f"• 總用戶數: {len(bot.users)} 人\n"
            f"• 延遲: {round(bot.latency * 1000)}ms"
        ),
        inline=False
    )
    
    # 顯示可用指令數量
    commands_count = len(bot.commands)
    embed.add_field(
        name="📋 可用指令",
        value=f"共 {commands_count} 個指令可用",
        inline=False
    )
    
    embed.set_footer(text="小雲ALBION機械人 v1.0.0 | 自動開獎系統")
    
    await ctx.send(embed=embed)

# 運行機器人
def main():
    """主程式入口"""
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ 錯誤: 找不到 DISCORD_TOKEN")
        print("📝 請確認:")
        print("  1. 已建立 .env 檔案")
        print("  2. .env 中有 DISCORD_TOKEN=你的令牌")
        print("  3. 令牌格式正確")
        sys.exit(1)
    
    print("🚀 正在啟動小雲ALBION機械人...")
    print("📁 專案路徑:", os.path.dirname(os.path.abspath(__file__)))
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ 登入失敗！請檢查 DISCORD_TOKEN 是否正確")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")

if __name__ == "__main__":
    main()