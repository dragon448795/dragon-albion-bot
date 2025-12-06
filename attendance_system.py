import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import aiosqlite
from database import Database

class AttendanceSystem:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.active_activities = {}
    
    async def init(self):
        """初始化系統"""
        await self.db.init_db()
    
    async def create_activity(self, activity_name, duration, host, channel, lottery_item=""):
        """創建評核活動"""
        activity_id = f"eval_{int(datetime.now().timestamp())}"
        
        # 創建嵌入訊息
        embed = discord.Embed(
            title=f"🎯 評核活動：{activity_name}",
            color=0x00AE86
        )
        embed.add_field(name="⏰ 持續時間", value=f"{duration}分鐘", inline=True)
        embed.add_field(name="🎁 抽獎物品", value=lottery_item or "無", inline=True)
        embed.add_field(name="👥 主辦人", value=host.mention, inline=True)
        
        embed.description = """
📊 **請按以下 Emoji 參與：**
✅ - **簽到出值率**（按此參加活動）
💚 - **補師**（權重 1.2）
🛡️ - **坦克**（權重 1.0）
⚔️ - **輸出**（權重 1.0）
✨ - **輔助**（權重 1.0）

📝 **活動結束後主辦人將為每位參與者評級：**
🌟 - 杰出 (權重 1.2)
👍 - 普通 (權重 1.0)
📉 - 待改進 (權重 0.8)
❌ - 極差 (權重 0.2)
        """
        
        embed.set_footer(text=f"活動ID：{activity_id} | 系統將於 {duration} 分鐘後自動結束")
        
        # 發送訊息
        message = await channel.send(embed=embed)
        
        # 添加反應
        reactions = ['✅', '💚', '🛡️', '⚔️', '✨']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        # 儲存到數據庫
        await self.db.add_activity(
            activity_id, activity_name, host.id, 
            channel.id, message.id, duration, lottery_item
        )
        
        # 設置定時結束
        self.active_activities[activity_id] = {
            'end_time': datetime.now() + timedelta(minutes=duration),
            'message_id': message.id,
            'channel_id': channel.id
        }
        
        # 啟動定時任務
        asyncio.create_task(self.schedule_activity_end(activity_id, duration))
        
        return activity_id
    
    async def schedule_activity_end(self, activity_id, delay_minutes):
        """定時結束活動"""
        await asyncio.sleep(delay_minutes * 60)
        await self.end_activity(activity_id)
    
    async def end_activity(self, activity_id):
        """結束活動並創建評分面板"""
        # 獲取活動資訊 - 使用 Database 的方法
        async with aiosqlite.connect('attendance.db') as db:
            cursor = await db.execute(
                "SELECT * FROM activities WHERE activity_id = ?",
                (activity_id,)
            )
            activity = await cursor.fetchone()
        
        if not activity:
            return
        
        # 獲取參與者
        async with aiosqlite.connect('attendance.db') as db:
            cursor = await db.execute('''
                SELECT p.user_id, p.role, u.username 
                FROM participations p
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.activity_id = ? AND p.signed_at IS NOT NULL
            ''', (activity_id,))
            participants = await cursor.fetchall()
        
        # 創建評分面板
        await self.create_rating_panel(activity, participants)
    
    async def create_rating_panel(self, activity, participants):
        """創建評分面板"""
        channel = self.bot.get_channel(int(activity[3]))  # channel_id
        
        embed = discord.Embed(
            title="🔒 【評分面板 - 僅主辦人可見】",
            color=0xFF9900
        )
        
        participants_text = ""
        for i, (user_id, role, username) in enumerate(participants, 1):
            role_emoji = self.get_role_emoji(role)
            participants_text += f"""
{i}. <@{user_id}> ({role_emoji} {role or '未選擇'})
   🌟 👍 📉 ❌ | 🔄
   *當前：普通*
"""
        
        embed.description = f"""
**{activity[1]}** - 請為參與者評級（{len(participants)}人參與）

🎯 **快速操作：**
✅ 全部設為普通
🔄 重設所有評級
🚀 完成評分並公開

👥 **參與者列表：**
{participants_text}

📊 **快速指令（在聊天框輸入）：**
`!傑出 @玩家1 @玩家2` - 標記為杰出
`!待改進 @玩家1` - 標記為待改進
`!全部普通` - 將所有未評分者設為普通
        """
        
        message = await channel.send(
            content=f"<@{activity[2]}> 活動已結束，請評分",
            embed=embed
        )
        
        # 添加快速操作反應
        reactions = ['✅', '🔄', '🚀']
        for reaction in reactions:
            await message.add_reaction(reaction)
    
    def get_role_emoji(self, role):
        """獲取職業對應的Emoji"""
        emojis = {
            '補師': '💚',
            '坦克': '🛡️',
            '輸出': '⚔️',
            '輔助': '✨'
        }
        return emojis.get(role, '👤')
    
    async def handle_checkin(self, payload):
        """處理簽到反應"""
        user = self.bot.get_user(payload.user_id)
        if user.bot:
            return
        
        # 查找對應活動
        async with aiosqlite.connect('attendance.db') as db:
            cursor = await db.execute(
                "SELECT activity_id FROM activities WHERE message_id = ?",
                (str(payload.message_id),)
            )
            activity = await cursor.fetchone()
        
        if activity:
            # 檢查是否已簽到
            async with aiosqlite.connect('attendance.db') as db:
                cursor = await db.execute(
                    "SELECT * FROM participations WHERE activity_id = ? AND user_id = ?",
                    (activity[0], str(payload.user_id))
                )
                existing = await cursor.fetchone()
                
                if not existing:
                    await self.db.add_participation(activity[0], str(payload.user_id))
    
    async def handle_role_selection(self, payload):
        """處理職業選擇"""
        emoji_to_role = {
            '💚': '補師',
            '🛡️': '坦克',
            '⚔️': '輸出',
            '✨': '輔助'
        }
        
        if str(payload.emoji) in emoji_to_role:
            # 查找對應活動
            async with aiosqlite.connect('attendance.db') as db:
                cursor = await db.execute(
                    "SELECT activity_id FROM activities WHERE message_id = ?",
                    (str(payload.message_id),)
                )
                activity = await cursor.fetchone()
                
                if activity:
                    # 檢查是否有參與記錄
                    cursor = await db.execute(
                        "SELECT * FROM participations WHERE activity_id = ? AND user_id = ?",
                        (activity[0], str(payload.user_id))
                    )
                    existing = await cursor.fetchone()
                    
                    if existing:
                        # 更新職業
                        await db.execute('''
                            UPDATE participations 
                            SET role = ? 
                            WHERE activity_id = ? AND user_id = ?
                        ''', (emoji_to_role[str(payload.emoji)], activity[0], str(payload.user_id)))
                        await db.commit()
                    else:
                        # 如果沒有參與記錄，先創建一個
                        await self.db.add_participation(activity[0], str(payload.user_id), emoji_to_role[str(payload.emoji)])