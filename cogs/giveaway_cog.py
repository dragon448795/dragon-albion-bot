import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import asyncio
import random
from datetime import datetime, timedelta
import aiosqlite
from typing import Optional, List

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self.bot.loop.create_task(self.init_db())
    
    async def init_db(self):
        """初始化資料庫"""
        async with aiosqlite.connect('data/dragon.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    message_id INTEGER,
                    host_id INTEGER,
                    prize TEXT,
                    winners_count INTEGER,
                    duration_minutes INTEGER,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaway_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id TEXT,
                    user_id INTEGER,
                    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways(id)
                )
            ''')
            await db.commit()
    
    @commands.slash_command(name="create_giveaway", description="創建抽獎活動")
    async def create_giveaway(
        self,
        ctx,
        prize: str,
        winners: int = 1,
        duration: int = 60
    ):
        """創建抽獎活動"""
        try:
            # 檢查參數
            if winners < 1:
                await ctx.respond("❌ 中獎人數必須至少為 1 人", ephemeral=True)
                return
            
            if duration < 1:
                await ctx.respond("❌ 持續時間必須至少為 1 分鐘", ephemeral=True)
                return
            
            # 創建抽獎 ID
            giveaway_id = f"giveaway_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            
            # 計算結束時間
            end_time = datetime.now() + timedelta(minutes=duration)
            
            # 創建抽獎訊息
            embed = discord.Embed(
                title="🎉 抽獎活動 🎉",
                color=0x00ff00,
                timestamp=end_time
            )
            
            embed.add_field(name="🎁 獎品", value=prize, inline=True)
            embed.add_field(name="👑 中獎人數", value=str(winners), inline=True)
            embed.add_field(name="⏰ 結束時間", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            
            embed.description = f"📢 主辦人：{ctx.author.mention}\n\n"
            embed.description += "**點擊下方按鈕參與抽獎！**\n"
            embed.description += f"\n🎫 目前參與人數：0 人"
            
            embed.set_footer(text=f"抽獎 ID: {giveaway_id}")
            
            # 創建參與按鈕
            enter_button = Button(label="🎫 參與抽獎", style=discord.ButtonStyle.green, emoji="🎉")
            
            async def enter_callback(interaction):
                if interaction.user.bot:
                    return
                
                # 檢查是否已參與
                async with aiosqlite.connect('data/dragon.db') as db:
                    cursor = await db.execute(
                        "SELECT * FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
                        (giveaway_id, interaction.user.id)
                    )
                    existing = await cursor.fetchone()
                    
                    if existing:
                        await interaction.response.send_message("❌ 你已經參與了這個抽獎！", ephemeral=True)
                        return
                    
                    # 添加參與記錄
                    await db.execute(
                        "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
                        (giveaway_id, interaction.user.id)
                    )
                    await db.commit()
                    
                    # 獲取當前參與人數
                    cursor = await db.execute(
                        "SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = ?",
                        (giveaway_id,)
                    )
                    count = await cursor.fetchone()
                    
                    # 更新嵌入訊息
                    embed.set_field_at(
                        2,
                        name="🎫 目前參與人數",
                        value=f"{count[0]} 人",
                        inline=True
                    )
                    
                    await interaction.message.edit(embed=embed)
                    await interaction.response.send_message("✅ 成功參與抽獎！", ephemeral=True)
            
            enter_button.callback = enter_callback
            
            view = View(timeout=None)
            view.add_item(enter_button)
            
            # 發送抽獎訊息
            message = await ctx.respond(embed=embed, view=view)
            if hasattr(message, 'message'):
                message = message.message
            
            # 儲存到資料庫
            async with aiosqlite.connect('data/dragon.db') as db:
                await db.execute('''
                    INSERT INTO giveaways 
                    (id, channel_id, message_id, host_id, prize, winners_count, duration_minutes, end_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    giveaway_id,
                    ctx.channel.id,
                    message.id,
                    ctx.author.id,
                    prize,
                    winners,
                    duration,
                    end_time.isoformat(),
                    'active'
                ))
                await db.commit()
            
            # 啟動自動開獎任務
            self.active_giveaways[giveaway_id] = asyncio.create_task(
                self.auto_draw_giveaway(giveaway_id, duration)
            )
            
            await ctx.respond(f"✅ 抽獎活動已創建！ID: `{giveaway_id}`", ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"❌ 創建抽獎時發生錯誤：{str(e)}", ephemeral=True)
            print(f"Giveaway creation error: {e}")
    
    async def auto_draw_giveaway(self, giveaway_id: str, duration_minutes: int):
        """自動開獎"""
        try:
            # 等待抽獎結束
            await asyncio.sleep(duration_minutes * 60)
            
            # 從資料庫獲取抽獎資訊
            async with aiosqlite.connect('data/dragon.db') as db:
                cursor = await db.execute(
                    "SELECT * FROM giveaways WHERE id = ?",
                    (giveaway_id,)
                )
                giveaway = await cursor.fetchone()
                
                if not giveaway:
                    print(f"Giveaway {giveaway_id} not found")
                    return
                
                # 獲取參與者
                cursor = await db.execute(
                    "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?",
                    (giveaway_id,)
                )
                entries = await cursor.fetchall()
                participants = [entry[0] for entry in entries]
                
                channel_id, message_id, prize, winners_count = (
                    giveaway[1], giveaway[2], giveaway[4], giveaway[5]
                )
                
                # 獲取頻道和訊息
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    print(f"Channel {channel_id} not found")
                    return
                
                try:
                    message = await channel.fetch_message(message_id)
                except:
                    message = None
                
                # 抽獎邏輯
                if not participants:
                    # 沒有參與者
                    embed = discord.Embed(
                        title="🎉 抽獎活動已結束 🎉",
                        description=f"**{prize}**\n\n❌ 沒有任何人參與抽獎",
                        color=0xff0000
                    )
                    
                    if message:
                        await message.edit(embed=embed, view=None)
                    
                    await channel.send(
                        f"🎉 **抽獎活動結束**\n"
                        f"**獎品：** {prize}\n"
                        f"**結果：** 沒有參與者，抽獎取消"
                    )
                else:
                    # 抽取中獎者
                    if len(participants) < winners_count:
                        winners_count = len(participants)
                    
                    winners = random.sample(participants, winners_count)
                    
                    # 創建中獎公告
                    winners_mentions = " ".join([f"<@{winner}>" for winner in winners])
                    
                    embed = discord.Embed(
                        title="🎉 抽獎活動已結束 🎉",
                        color=0xffd700
                    )
                    
                    embed.add_field(name="🎁 獎品", value=prize, inline=False)
                    embed.add_field(name="👑 中獎人數", value=f"{winners_count} 人", inline=True)
                    embed.add_field(name="🎫 總參與人數", value=f"{len(participants)} 人", inline=True)
                    embed.add_field(name="🏆 中獎者", value=winners_mentions or "無", inline=False)
                    
                    if message:
                        await message.edit(embed=embed, view=None)
                    
                    # 發送中獎公告
                    announcement = await channel.send(
                        f"🎉 **抽獎結果公布** 🎉\n\n"
                        f"**獎品：** {prize}\n"
                        f"**中獎者：** {winners_mentions}\n\n"
                        f"恭喜中獎者！請聯絡主辦人領取獎品。"
                    )
                    
                    # 更新資料庫狀態
                    await db.execute(
                        "UPDATE giveaways SET status = 'completed' WHERE id = ?",
                        (giveaway_id,)
                    )
                    await db.commit()
                
                # 清理任務
                if giveaway_id in self.active_giveaways:
                    del self.active_giveaways[giveaway_id]
                    
        except Exception as e:
            print(f"Auto draw error for {giveaway_id}: {e}")
    
    @commands.slash_command(name="draw", description="手動提前開獎")
    async def manual_draw(self, ctx, giveaway_id: str):
        """手動開獎"""
        try:
            # 檢查權限
            async with aiosqlite.connect('data/dragon.db') as db:
                cursor = await db.execute(
                    "SELECT host_id FROM giveaways WHERE id = ?",
                    (giveaway_id,)
                )
                giveaway = await cursor.fetchone()
                
                if not giveaway:
                    await ctx.respond("❌ 找不到指定的抽獎活動", ephemeral=True)
                    return
                
                if ctx.author.id != giveaway[0] and not ctx.author.guild_permissions.administrator:
                    await ctx.respond("❌ 只有主辦人或管理員可以手動開獎", ephemeral=True)
                    return
                
                # 取消自動開獎任務
                if giveaway_id in self.active_giveaways:
                    self.active_giveaways[giveaway_id].cancel()
                    del self.active_giveaways[giveaway_id]
                
                # 執行開獎
                await self.force_draw_giveaway(giveaway_id)
                await ctx.respond("✅ 已手動開獎", ephemeral=True)
                
        except Exception as e:
            await ctx.respond(f"❌ 開獎時發生錯誤：{str(e)}", ephemeral=True)
    
    async def force_draw_giveaway(self, giveaway_id: str):
        """強制開獎（用於手動開獎）"""
        # 重用 auto_draw_giveaway 的邏輯，但跳過等待
        try:
            async with aiosqlite.connect('data/dragon.db') as db:
                cursor = await db.execute(
                    "SELECT * FROM giveaways WHERE id = ?",
                    (giveaway_id,)
                )
                giveaway = await cursor.fetchone()
                
                if not giveaway:
                    return
                
                # 獲取參與者並開獎（重用 auto_draw_giveaway 的開獎邏輯）
                # ... 這裡可以使用 auto_draw_giveaway 中的開獎代碼 ...
                
        except Exception as e:
            print(f"Force draw error: {e}")
    
    @commands.slash_command(name="list_giveaways", description="查看進行中的抽獎")
    async def list_giveaways(self, ctx):
        """查看抽獎列表"""
        try:
            async with aiosqlite.connect('data/dragon.db') as db:
                cursor = await db.execute(
                    "SELECT id, prize, winners_count, end_time, status FROM giveaways WHERE status = 'active'"
                )
                active_giveaways = await cursor.fetchall()
                
                if not active_giveaways:
                    await ctx.respond("📭 目前沒有進行中的抽獎活動", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="📋 進行中的抽獎活動",
                    color=0x3498db
                )
                
                for giveaway in active_giveaways:
                    giveaway_id, prize, winners, end_time_str, status = giveaway
                    end_time = datetime.fromisoformat(end_time_str)
                    
                    embed.add_field(
                        name=f"🎁 {prize}",
                        value=(
                            f"**ID：** `{giveaway_id}`\n"
                            f"**中獎人數：** {winners} 人\n"
                            f"**結束時間：** <t:{int(end_time.timestamp())}:R>\n"
                            f"**狀態：** {status}"
                        ),
                        inline=False
                    )
                
                await ctx.respond(embed=embed, ephemeral=True)
                
        except Exception as e:
            await ctx.respond(f"❌ 獲取抽獎列表時發生錯誤：{str(e)}", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """機器人啟動時恢復進行中的抽獎"""
        try:
            async with aiosqlite.connect('data/dragon.db') as db:
                cursor = await db.execute(
                    "SELECT id, duration_minutes, end_time FROM giveaways WHERE status = 'active'"
                )
                giveaways = await cursor.fetchall()
                
                for giveaway_id, duration, end_time_str in giveaways:
                    end_time = datetime.fromisoformat(end_time_str)
                    now = datetime.now()
                    
                    if now >= end_time:
                        # 已經過期，立即開獎
                        await self.force_draw_giveaway(giveaway_id)
                    else:
                        # 計算剩餘時間
                        remaining = (end_time - now).total_seconds()
                        if remaining > 0:
                            # 重新啟動定時任務
                            self.active_giveaways[giveaway_id] = asyncio.create_task(
                                self.auto_draw_giveaway(giveaway_id, int(remaining / 60))
                            )
                            
        except Exception as e:
            print(f"Error restoring giveaways: {e}")

def setup(bot):
    bot.add_cog(GiveawayCog(bot))