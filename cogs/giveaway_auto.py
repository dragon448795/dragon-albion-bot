#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動抽獎系統 - 時間到自動開獎，無需手動指令
兼容 discord.py 1.x 版本
"""

import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime, timedelta
import aiosqlite
import os
from typing import Dict, List, Optional

class GiveawayAuto(commands.Cog):
    """自動抽獎系統"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways: Dict[str, asyncio.Task] = {}
        self.bot.loop.create_task(self.init_db())
        self.bot.loop.create_task(self.restore_giveaways())
    
    async def init_db(self):
        """初始化資料庫"""
        # 確保 data 資料夾存在
        os.makedirs("data", exist_ok=True)
        
        async with aiosqlite.connect("data/giveaways.db") as db:
            # 抽獎活動表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    message_id INTEGER,
                    host_id INTEGER,
                    prize TEXT,
                    winners INTEGER,
                    duration INTEGER,
                    end_time TIMESTAMP,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 參與記錄表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id TEXT,
                    user_id INTEGER,
                    user_name TEXT,
                    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE
                )
            ''')
            
            await db.commit()
    
    async def restore_giveaways(self):
        """恢復進行中的抽獎活動"""
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)  # 等待其他系統初始化
        
        try:
            async with aiosqlite.connect("data/giveaways.db") as db:
                cursor = await db.execute(
                    "SELECT id, end_time FROM giveaways WHERE status = 'active'"
                )
                active = await cursor.fetchall()
                
                for giveaway_id, end_time_str in active:
                    end_time = datetime.fromisoformat(end_time_str)
                    now = datetime.now()
                    
                    if now >= end_time:
                        # 已經過期，立即開獎
                        await self.draw_giveaway(giveaway_id)
                    else:
                        # 計算剩餘時間（分鐘）
                        remaining_seconds = (end_time - now).total_seconds()
                        if remaining_seconds > 0:
                            # 重新啟動定時任務
                            self.active_giveaways[giveaway_id] = asyncio.create_task(
                                self.schedule_giveaway_end(giveaway_id, remaining_seconds)
                            )
                            print(f"✅ 已恢復抽獎活動: {giveaway_id} (剩餘 {remaining_seconds/60:.1f} 分鐘)")
        
        except Exception as e:
            print(f"❌ 恢復抽獎活動失敗: {e}")
    
    @commands.command(name="創建自動抽獎", aliases=["create_auto_giveaway"])
    async def create_auto_giveaway(self, ctx, 獎品: str, 獲獎人數: int = 1, 持續時間: int = 60):
        """創建自動抽獎活動（時間到自動開獎）
        
        參數:
          獎品: 抽獎獎品名稱
          獲獎人數: 中獎者數量 (預設: 1)
          持續時間: 抽獎持續時間（分鐘）(預設: 60)
        """
        try:
            # 參數驗證
            if 獲獎人數 < 1:
                await ctx.send("❌ 獲獎人數必須至少為 1 人")
                return
            
            if 持續時間 < 1:
                await ctx.send("❌ 持續時間必須至少為 1 分鐘")
                return
            elif 持續時間 > 10080:  # 7天
                await ctx.send("❌ 持續時間不能超過 7 天 (10080 分鐘)")
                return
            
            # 生成抽獎ID
            giveaway_id = f"giveaway_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            
            # 計算結束時間
            end_time = datetime.now() + timedelta(minutes=持續時間)
            
            # 創建抽獎訊息
            embed = discord.Embed(
                title="🎉 自動抽獎活動 🎉",
                description="**時間到自動開獎，無需手動指令！**",
                color=0x00ff00,
                timestamp=end_time
            )
            
            embed.add_field(name="🎁 獎品", value=獎品, inline=True)
            embed.add_field(name="👑 中獎人數", value=str(獲獎人數), inline=True)
            embed.add_field(name="⏰ 結束時間", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            embed.add_field(name="🎫 目前參與人數", value="0 人", inline=True)
            
            embed.add_field(
                name="📝 參與方式",
                value="點擊下方 🎫 按鈕參與抽獎",
                inline=False
            )
            
            embed.add_field(
                name="💡 注意事項",
                value=(
                    "• 每個用戶只能參與一次\n"
                    f"• 結束時間: <t:{int(end_time.timestamp())}:F>\n"
                    "• 時間到自動開獎並公告"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"抽獎ID: {giveaway_id} | 主辦人: {ctx.author}")
            
            # 創建參與按鈕
            class GiveawayButton(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)
                
                @discord.ui.button(label="🎫 參與抽獎", style=discord.ButtonStyle.green, custom_id=f"giveaway_{giveaway_id}")
                async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    # 防止機器人參與
                    if interaction.user.bot:
                        return
                    
                    # 檢查是否已參與
                    async with aiosqlite.connect("data/giveaways.db") as db:
                        cursor = await db.execute(
                            "SELECT id FROM entries WHERE giveaway_id = ? AND user_id = ?",
                            (giveaway_id, interaction.user.id)
                        )
                        existing = await cursor.fetchone()
                        
                        if existing:
                            await interaction.response.send_message(
                                "❌ 你已經參與了這個抽獎！", 
                                ephemeral=True
                            )
                            return
                        
                        # 添加參與記錄
                        await db.execute(
                            "INSERT INTO entries (giveaway_id, user_id, user_name) VALUES (?, ?, ?)",
                            (giveaway_id, interaction.user.id, str(interaction.user))
                        )
                        await db.commit()
                        
                        # 獲取當前參與人數
                        cursor = await db.execute(
                            "SELECT COUNT(*) FROM entries WHERE giveaway_id = ?",
                            (giveaway_id,)
                        )
                        count = await cursor.fetchone()
                        
                        # 更新原始訊息
                        embed.set_field_at(
                            3,
                            name="🎫 目前參與人數",
                            value=f"{count[0]} 人",
                            inline=True
                        )
                        
                        try:
                            await interaction.message.edit(embed=embed)
                        except:
                            pass
                        
                        await interaction.response.send_message(
                            f"✅ 成功參與抽獎！\n"
                            f"**獎品:** {獎品}\n"
                            f"**中獎人數:** {獲獎人數}人\n"
                            f"**結束時間:** <t:{int(end_time.timestamp())}:R>",
                            ephemeral=True
                        )
            
            # 發送抽獎訊息
            view = GiveawayButton()
            message = await ctx.send(embed=embed, view=view)
            
            # 儲存到資料庫
            async with aiosqlite.connect("data/giveaways.db") as db:
                await db.execute('''
                    INSERT INTO giveaways 
                    (id, channel_id, message_id, host_id, prize, winners, duration, end_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    giveaway_id,
                    ctx.channel.id,
                    message.id,
                    ctx.author.id,
                    獎品,
                    獲獎人數,
                    持續時間,
                    end_time.isoformat(),
                    'active'
                ))
                await db.commit()
            
            # 啟動自動開獎任務
            self.active_giveaways[giveaway_id] = asyncio.create_task(
                self.schedule_giveaway_end(giveaway_id, 持續時間 * 60)
            )
            
            # 發送確認訊息
            confirm_embed = discord.Embed(
                title="✅ 抽獎活動已創建",
                color=0x00ff00
            )
            
            confirm_embed.add_field(name="🎁 獎品", value=獎品, inline=True)
            confirm_embed.add_field(name="👑 中獎人數", value=str(獲獎人數), inline=True)
            confirm_embed.add_field(name="⏰ 持續時間", value=f"{持續時間} 分鐘", inline=True)
            confirm_embed.add_field(name="🆔 抽獎ID", value=f"`{giveaway_id}`", inline=False)
            confirm_embed.add_field(name="📅 結束時間", value=f"<t:{int(end_time.timestamp())}:F>", inline=False)
            
            confirm_embed.set_footer(text="時間到自動開獎，無需手動指令！")
            
            await ctx.send(embed=confirm_embed)
            
        except Exception as e:
            await ctx.send(f"❌ 創建抽獎時發生錯誤：{str(e)}")
            print(f"抽獎創建錯誤: {e}")
    
    async def schedule_giveaway_end(self, giveaway_id: str, delay_seconds: float):
        """定時結束抽獎"""
        try:
            # 等待抽獎結束
            await asyncio.sleep(delay_seconds)
            
            # 執行開獎
            await self.draw_giveaway(giveaway_id)
            
        except asyncio.CancelledError:
            print(f"抽獎 {giveaway_id} 已取消")
        except Exception as e:
            print(f"抽獎結束錯誤 {giveaway_id}: {e}")
    
    async def draw_giveaway(self, giveaway_id: str):
        """執行開獎"""
        try:
            # 從資料庫獲取抽獎資訊
            async with aiosqlite.connect("data/giveaways.db") as db:
                cursor = await db.execute(
                    "SELECT * FROM giveaways WHERE id = ?",
                    (giveaway_id,)
                )
                giveaway = await cursor.fetchone()
                
                if not giveaway:
                    print(f"抽獎 {giveaway_id} 不存在")
                    return
                
                _, channel_id, message_id, host_id, prize, winners, _, end_time, status, _ = giveaway
                
                if status != 'active':
                    print(f"抽獎 {giveaway_id} 狀態不是 active: {status}")
                    return
                
                # 獲取參與者
                cursor = await db.execute(
                    "SELECT user_id, user_name FROM entries WHERE giveaway_id = ?",
                    (giveaway_id,)
                )
                entries = await cursor.fetchall()
                participants = [{"id": e[0], "name": e[1]} for e in entries]
                
                # 獲取頻道
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    print(f"頻道 {channel_id} 不存在")
                    return
                
                # 抽獎邏輯
                if not participants:
                    # 沒有參與者
                    embed = discord.Embed(
                        title="🎉 抽獎活動結束 🎉",
                        description=f"**獎品:** {prize}",
                        color=0xff0000
                    )
                    
                    embed.add_field(
                        name="📊 結果",
                        value="❌ 沒有任何人參與抽獎，活動取消",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"抽獎ID: {giveaway_id}")
                    
                    await channel.send(embed=embed)
                    
                else:
                    # 抽取中獎者
                    if len(participants) < winners:
                        winners = len(participants)
                    
                    selected_winners = random.sample(participants, winners)
                    
                    # 創建中獎公告
                    winners_text = "\n".join([f"🎉 <@{w['id']}> ({w['name']})" for w in selected_winners])
                    
                    embed = discord.Embed(
                        title="🎉 抽獎活動結束 🎉",
                        description="**時間到自動開獎完成！**",
                        color=0xffd700  # 金色
                    )
                    
                    embed.add_field(name="🎁 獎品", value=prize, inline=False)
                    embed.add_field(name="👑 中獎人數", value=f"{winners} 人", inline=True)
                    embed.add_field(name="🎫 總參與人數", value=f"{len(participants)} 人", inline=True)
                    embed.add_field(name="🏆 中獎者名單", value=winners_text or "無", inline=False)
                    
                    embed.add_field(
                        name="📢 公告",
                        value=f"恭喜中獎者！請聯絡 <@{host_id}> 領取獎品。",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"抽獎ID: {giveaway_id} | 自動開獎系統")
                    
                    # 發送中獎公告
                    announcement = await channel.send(embed=embed)
                    
                    # 標記中獎者
                    winners_mentions = " ".join([f"<@{w['id']}>" for w in selected_winners])
                    if winners_mentions:
                        await channel.send(f"🎉 **恭喜中獎者！** {winners_mentions}")
                
                # 更新資料庫狀態
                await db.execute(
                    "UPDATE giveaways SET status = 'completed' WHERE id = ?",
                    (giveaway_id,)
                )
                await db.commit()
                
                # 清理任務
                if giveaway_id in self.active_giveaways:
                    del self.active_giveaways[giveaway_id]
                
                print(f"✅ 抽獎 {giveaway_id} 已自動開獎完成")
                
        except Exception as e:
            print(f"開獎錯誤 {giveaway_id}: {e}")
    
    @commands.command(name="手動開獎", aliases=["manual_draw"])
    async def manual_draw(self, ctx, 抽獎ID: str):
        """手動提前開獎（僅限主辦人或管理員）"""
        try:
            # 從資料庫獲取抽獎資訊
            async with aiosqlite.connect("data/giveaways.db") as db:
                cursor = await db.execute(
                    "SELECT host_id, status FROM giveaways WHERE id = ?",
                    (抽獎ID,)
                )
                giveaway = await cursor.fetchone()
                
                if not giveaway:
                    await ctx.send("❌ 找不到指定的抽獎活動")
                    return
                
                host_id, status = giveaway
                
                # 權限檢查
                if ctx.author.id != host_id and not ctx.author.guild_permissions.administrator:
                    await ctx.send("❌ 只有主辦人或管理員可以手動開獎")
                    return
                
                if status != 'active':
                    await ctx.send(f"❌ 此抽獎狀態為 {status}，無法開獎")
                    return
                
                # 取消自動任務（如果存在）
                if 抽獎ID in self.active_giveaways:
                    self.active_giveaways[抽獎ID].cancel()
                    del self.active_giveaways[抽獎ID]
                
                # 執行開獎
                await self.draw_giveaway(抽獎ID)
                await ctx.send("✅ 已手動開獎完成")
                
        except Exception as e:
            await ctx.send(f"❌ 手動開獎時發生錯誤：{str(e)}")
    
    @commands.command(name="抽獎列表", aliases=["list_giveaways"])
    async def list_giveaways(self, ctx):
        """查看進行中的抽獎活動"""
        try:
            async with aiosqlite.connect("data/giveaways.db") as db:
                cursor = await db.execute('''
                    SELECT id, prize, winners, end_time, status 
                    FROM giveaways 
                    WHERE status = 'active'
                    ORDER BY end_time ASC
                ''')
                giveaways = await cursor.fetchall()
                
                if not giveaways:
                    await ctx.send("📭 目前沒有進行中的抽獎活動")
                    return
                
                embed = discord.Embed(
                    title="📋 進行中的抽獎活動",
                    color=0x3498db
                )
                
                for giveaway in giveaways:
                    giveaway_id, prize, winners, end_time_str, status = giveaway
                    end_time = datetime.fromisoformat(end_time_str)
                    
                    # 獲取參與人數
                    cursor2 = await db.execute(
                        "SELECT COUNT(*) FROM entries WHERE giveaway_id = ?",
                        (giveaway_id,)
                    )
                    count = await cursor2.fetchone()
                    participants = count[0] if count else 0
                    
                    embed.add_field(
                        name=f"🎁 {prize}",
                        value=(
                            f"**ID:** `{giveaway_id}`\n"
                            f"**中獎人數:** {winners} 人\n"
                            f"**參與人數:** {participants} 人\n"
                            f"**結束時間:** <t:{int(end_time.timestamp())}:R>\n"
                            f"**狀態:** {status}"
                        ),
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ 獲取抽獎列表時發生錯誤：{str(e)}")
    
    @commands.command(name="抽獎資訊", aliases=["giveaway_info"])
    async def giveaway_info(self, ctx, 抽獎ID: str):
        """查看抽獎詳細資訊"""
        try:
            async with aiosqlite.connect("data/giveaways.db") as db:
                cursor = await db.execute(
                    "SELECT * FROM giveaways WHERE id = ?",
                    (抽獎ID,)
                )
                giveaway = await cursor.fetchone()
                
                if not giveaway:
                    await ctx.send("❌ 找不到指定的抽獎活動")
                    return
                
                giveaway_id, channel_id, message_id, host_id, prize, winners, duration, end_time_str, status, created_at = giveaway
                
                end_time = datetime.fromisoformat(end_time_str)
                
                # 獲取參與者
                cursor = await db.execute(
                    "SELECT user_name FROM entries WHERE giveaway_id = ? ORDER BY entered_at",
                    (抽獎ID,)
                )
                entries = await cursor.fetchall()
                participants = [e[0] for e in entries]
                
                embed = discord.Embed(
                    title=f"📊 抽獎資訊 - {prize}",
                    color=0x9b59b6
                )
                
                embed.add_field(name="🆔 抽獎ID", value=f"`{giveaway_id}`", inline=True)
                embed.add_field(name="👑 中獎人數", value=str(winners), inline=True)
                embed.add_field(name="🎫 參與人數", value=str(len(participants)), inline=True)
                embed.add_field(name="⏰ 持續時間", value=f"{duration} 分鐘", inline=True)
                embed.add_field(name="📅 創建時間", value=f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:R>", inline=True)
                embed.add_field(name="⏱️ 結束時間", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
                embed.add_field(name="📊 狀態", value=status, inline=True)
                
                if participants:
                    # 只顯示前20個參與者
                    participants_display = "\n".join(participants[:20])
                    if len(participants) > 20:
                        participants_display += f"\n... 還有 {len(participants) - 20} 人"
                    
                    embed.add_field(
                        name="👥 參與者列表",
                        value=participants_display,
                        inline=False
                    )
                
                embed.set_footer(text=f"主辦人ID: {host_id}")
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ 獲取抽獎資訊時發生錯誤：{str(e)}")

async def setup(bot):
    """載入此Cog"""
    await bot.add_cog(GiveawayAuto(bot))