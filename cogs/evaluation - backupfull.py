import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import random

class Evaluation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.evaluations = {}
        self.user_data = {}
        self.attendance_records = {}
        
        # 當前半月期計算
        self.current_period = self.get_current_period()
        
        # 評分權重設定
        self.rating_weights = {
            "優秀": 1.2,    # 优秀
            "普通": 1.0,    # 普通（預設值）
            "待改進": 0.8,  # 待改进
            "極差": 0.2     # 极差
        }
        
        # 職業加成
        self.class_bonus = {
            "坦克": 1.0,
            "输出": 1.0,
            "治疗": 1.2,    # 1.2倍加成
            "辅助": 1.0
        }
        
        # 評分EMOJI對應
        self.rating_emojis = {
            "⭐": "優秀",   # 星星 - 優秀
            "🆗": "普通",   # OK - 普通
            "⚠️": "待改進", # 警告 - 待改進
            "❌": "極差"    # 交叉 - 極差
        }
        
        # 數字EMOJI對應玩家（1-50）
        self.number_emojis = [
            "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
            "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
            "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹",
            "🇺", "🇻", "🇼", "🇽", "🇾", "🇿", "🔴", "🟠", "🟡", "🟢",
            "🔵", "🟣", "🟤", "⚫", "⚪", "🟥", "🟧", "🟨", "🟩", "🟦"
        ]

    def get_current_period(self):
        """獲取當前半月期"""
        now = datetime.now()
        year_month = now.strftime("%Y-%m")
        day = now.day
        
        if day <= 15:
            return f"{year_month}-上半"
        else:
            return f"{year_month}-下半"

    @commands.command(name="創建評核活動")
    async def create_evaluation(self, ctx, name: str, minutes: int, *, prize: str):
        """創建評核活動"""
        
        if name in self.evaluations:
            await ctx.send(f"❌ 已存在同名活動：{name}")
            return
            
        end_time = datetime.now() + timedelta(minutes=minutes)
        activity_id = f"eva_{int(datetime.now().timestamp())}_{ctx.channel.id}"
        current_period = self.get_current_period()
        
        # 儲存活動資料
        self.evaluations[activity_id] = {
            "name": name,
            "creator": ctx.author.id,
            "prize": prize,
            "start_time": datetime.now(),
            "end_time": end_time,
            "duration_minutes": minutes,
            "signup_end_time": None,
            "attendees": set(),
            "class_selections": {},
            "ratings": {},
            "weights": {},
            "status": "signup",
            "rating_msg_id": None,
            "rating_select_msg_id": None,
            "signup_msg_id": None,
            "class_msg_id": None,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "period": current_period,
            "allow_signup": True,
            "selected_player": None  # 當前選擇的玩家
        }
        
        # 簽到訊息
        embed1 = discord.Embed(
            title=f"📋 評核活動：{name}",
            description=f"**活動ID:** `{activity_id}`\n**獎品：** {prize}\n**簽到時間：** {minutes}分鐘",
            color=discord.Color.blue()
        )
        embed1.add_field(
            name="📝 簽到階段",
            value=f"請在活動開始後 {minutes} 分鐘內按 ✅ 簽到\n超過時間簽到將不計算出席率",
            inline=False
        )
        embed1.set_footer(text=f"半月期: {current_period}")
        
        signup_msg = await ctx.send(embed=embed1)
        self.evaluations[activity_id]["signup_msg_id"] = signup_msg.id
        self.evaluations[activity_id]["signup_end_time"] = datetime.now() + timedelta(minutes=minutes)
        
        await signup_msg.add_reaction("✅")
        await signup_msg.add_reaction("❌")
        
        # 職業選擇訊息
        embed2 = discord.Embed(
            title=f"🎮 職業選擇：{name}",
            description="請選擇你的職業：",
            color=discord.Color.green()
        )
        embed2.add_field(name="🛡️", value="坦克", inline=True)
        embed2.add_field(name="⚔️", value="输出", inline=True)
        embed2.add_field(name="💚", value="治疗", inline=True)
        embed2.add_field(name="💛", value="辅助", inline=True)
        
        class_msg = await ctx.send(embed=embed2)
        self.evaluations[activity_id]["class_msg_id"] = class_msg.id
        
        await class_msg.add_reaction("🛡️")
        await class_msg.add_reaction("⚔️")
        await class_msg.add_reaction("💚")
        await class_msg.add_reaction("💛")
        
        await ctx.send(f"✅ 評核活動 '{name}' 已創建！\n簽到將在 {minutes} 分鐘後截止，隨後進入評分階段。")
        
        # 設置簽到截止定時器
        await asyncio.sleep(minutes * 60)
        await self.end_signup_and_show_rating(ctx, activity_id)

    async def end_signup_and_show_rating(self, ctx, activity_id):
        """結束簽到並顯示評分界面"""
        
        if activity_id not in self.evaluations:
            return
            
        activity = self.evaluations[activity_id]
        
        # 關閉簽到
        activity["allow_signup"] = False
        activity["status"] = "rating"
        
        # 發送簽到結束通知
        await ctx.send(f"⏰ 簽到已結束！現在進入評分階段。")
        
        # 顯示評分界面
        await self.show_rating_interface(ctx, activity_id)

    async def show_rating_interface(self, ctx, activity_id):
        """顯示評分界面"""
        
        if activity_id not in self.evaluations:
            return
            
        activity = self.evaluations[activity_id]
        
        # 獲取參與者資訊
        participants_info = await self.get_participants_info(activity_id)
        
        # 設定預設評分為"普通"
        for participant in participants_info:
            if participant["rating"] == "未評分":
                activity["ratings"][participant["id"]] = "普通"
                participant["rating"] = "普通"
                
                # 計算預設權重
                weight = self.rating_weights["普通"]
                if participant["class"] in self.class_bonus:
                    weight *= self.class_bonus[participant["class"]]
                activity["weights"][participant["id"]] = weight
                participant["weight"] = weight
        
        # 創建評分界面
        embed = discord.Embed(
            title=f"⭐ 評分時間 - {activity['name']}",
            description=f"**活動ID:** `{activity_id}`\n**參與人數：** {len(participants_info)}人\n**抽獎物品：** {activity['prize']}",
            color=discord.Color.gold()
        )
        
        # 參與者列表（只顯示前15人，其餘點擊按鈕查看）
        if participants_info:
            participants_text = ""
            for i, participant in enumerate(participants_info[:15]):  # 只顯示前15人
                class_emoji = {
                    "坦克": "🛡️",
                    "输出": "⚔️",
                    "治疗": "💚",
                    "辅助": "💛",
                    "未選擇": "❓"
                }.get(participant["class"], "❓")
                
                rating_emoji = {
                    "優秀": "⭐",
                    "普通": "🆗",
                    "待改進": "⚠️",
                    "極差": "❌"
                }.get(participant["rating"], "❓")
                
                weight_display = f"{participant['weight']:.1f}"
                player_emoji = self.number_emojis[i] if i < len(self.number_emojis) else f"{i+1}."
                
                participants_text += f"{player_emoji} {class_emoji} **{participant['name']}** - {participant['class']} | {rating_emoji} {participant['rating']} (權重: {weight_display})\n"
            
            if len(participants_info) > 15:
                participants_text += f"\n... 還有 {len(participants_info) - 15} 位參與者，請使用下方按鈕選擇"
            
            embed.add_field(name="**📋 參與者列表**", value=participants_text, inline=False)
        else:
            embed.add_field(name="**📋 參與者列表**", value="暫無參與者", inline=False)
        
        # 操作指南
        guide = (
            f"**🎮 EMOJI評分系統：**\n\n"
            f"**1. 選擇玩家：**\n"
            f"   按玩家對應的數字/字母按鈕選擇要評分的玩家\n\n"
            f"**2. 選擇評級：**\n"
            f"   ⭐ = 優秀 (權重 1.2)\n"
            f"   🆗 = 普通 (權重 1.0) ← 預設值\n"
            f"   ⚠️ = 待改進 (權重 0.8)\n"
            f"   ❌ = 極差 (權重 0.2)\n\n"
            f"**3. 完成抽獎：**\n"
            f"   全部評分完成後按 🎲 開始抽獎"
        )
        
        embed.add_field(name="**📝 操作說明**", value=guide, inline=False)
        
        # 總權重計算
        total_weight = sum(p["weight"] for p in participants_info if isinstance(p["weight"], (int, float)))
        embed.add_field(name="**[總權重]**", value=f"{total_weight:.1f}", inline=True)
        
        # 發送評分界面
        rating_msg = await ctx.send(embed=embed)
        activity["rating_msg_id"] = rating_msg.id
        
        # 添加玩家選擇按鈕（最多20個）
        max_players = min(len(participants_info), 20)
        for i in range(max_players):
            await rating_msg.add_reaction(self.number_emojis[i])
        
        # 添加評分按鈕
        for emoji in self.rating_emojis.keys():
            await rating_msg.add_reaction(emoji)
        
        # 添加抽獎按鈕
        await rating_msg.add_reaction("🎲")
        
        await ctx.send(f"💡 **提示：** 所有未評分玩家已預設為「普通」。請先按玩家按鈕，再按評級按鈕。")

    async def get_participants_info(self, activity_id):
        """獲取參與者資訊"""
        
        if activity_id not in self.evaluations:
            return []
        
        activity = self.evaluations[activity_id]
        participants_info = []
        
        for user_id in activity["attendees"]:
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.name
            except:
                username = f"用戶{user_id[:4]}"
            
            # 獲取職業選擇
            player_class = activity["class_selections"].get(user_id, "未選擇")
            
            # 獲取評分（如果已評）
            rating = activity["ratings"].get(user_id, "未評分")
            
            # 計算權重
            weight = 1.0
            if rating in self.rating_weights:
                weight = self.rating_weights[rating]
                # 應用職業加成
                if player_class in self.class_bonus:
                    weight *= self.class_bonus[player_class]
            elif rating == "未評分":
                # 預設為普通
                weight = self.rating_weights["普通"]
                if player_class in self.class_bonus:
                    weight *= self.class_bonus[player_class]
            
            participants_info.append({
                "id": user_id,
                "name": username,
                "class": player_class,
                "rating": rating,
                "weight": weight,
                "index": len(participants_info) + 1
            })
        
        return participants_info

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
            
        msg_id = reaction.message.id
        emoji = str(reaction.emoji)
        user_id = str(user.id)
        channel = reaction.message.channel
        
        # 查找對應的活動
        for activity_id, activity in self.evaluations.items():
            # 處理簽到（僅在允許簽到時段內）
            if activity.get("signup_msg_id") == msg_id:
                if not activity.get("allow_signup", True):
                    # 超過簽到時間，移除反應
                    try:
                        await reaction.remove(user)
                    except:
                        pass
                    return
                
                if emoji == "✅":
                    # 檢查是否在簽到時間內
                    if datetime.now() > activity["signup_end_time"]:
                        try:
                            await reaction.remove(user)
                        except:
                            pass
                        return
                    
                    activity["attendees"].add(user_id)
                    
                    # 初始化用戶數據
                    if user_id not in self.user_data:
                        self.user_data[user_id] = {
                            "name": user.name,
                            "rating_counts": {"優秀": 0, "普通": 0, "待改進": 0, "極差": 0},
                            "activities": [],
                            "attendance_periods": {}
                        }
                    
                    # 記錄出席（半月期）
                    period = activity["period"]
                    if period not in self.user_data[user_id]["attendance_periods"]:
                        self.user_data[user_id]["attendance_periods"][period] = {
                            "total_events": 0,
                            "attended": 0
                        }
                    
                    # 增加該期總活動數（如果這是第一次參加此活動）
                    activity_key = f"{activity['name']}_{activity['start_time'].strftime('%Y%m%d%H%M%S')}"
                    if activity_key not in self.user_data[user_id].get("attended_events", set()):
                        if "attended_events" not in self.user_data[user_id]:
                            self.user_data[user_id]["attended_events"] = set()
                        
                        self.user_data[user_id]["attended_events"].add(activity_key)
                        self.user_data[user_id]["attendance_periods"][period]["total_events"] += 1
                    
                    # 增加出席次數
                    self.user_data[user_id]["attendance_periods"][period]["attended"] += 1
                    
                    try:
                        user_obj = await self.bot.fetch_user(int(user_id))
                        await user_obj.send(f"✅ 你已成功簽到活動：{activity['name']}\n簽到時間：{datetime.now().strftime('%H:%M:%S')}")
                    except:
                        pass
                        
                elif emoji == "❌":
                    if user_id in activity["attendees"]:
                        activity["attendees"].discard(user_id)
                return
            
            # 處理職業選擇
            elif activity.get("class_msg_id") == msg_id:
                if user_id in activity["attendees"]:
                    if emoji == "🛡️":
                        activity["class_selections"][user_id] = "坦克"
                    elif emoji == "⚔️":
                        activity["class_selections"][user_id] = "输出"
                    elif emoji == "💚":
                        activity["class_selections"][user_id] = "治疗"
                    elif emoji == "💛":
                        activity["class_selections"][user_id] = "辅助"
                    
                    try:
                        user_obj = await self.bot.fetch_user(int(user_id))
                        class_name = activity["class_selections"][user_id]
                        await user_obj.send(f"🎮 你在 {activity['name']} 選擇了：{class_name}")
                    except:
                        pass
                return
            
            # 處理評分界面按鈕
            elif activity.get("rating_msg_id") == msg_id:
                if user_id != str(activity["creator"]):
                    return  # 只有HOST可以操作
                
                # 獲取參與者列表
                participants_info = await self.get_participants_info(activity_id)
                if not participants_info:
                    await channel.send("❌ 沒有參與者可以評分！")
                    return
                
                # 處理玩家選擇按鈕
                if emoji in self.number_emojis:
                    player_index = self.number_emojis.index(emoji)
                    if player_index < len(participants_info):
                        selected_player = participants_info[player_index]
                        activity["selected_player"] = selected_player["id"]
                        
                        # 發送選擇確認
                        rating_emoji = {
                            "優秀": "⭐",
                            "普通": "🆗",
                            "待改進": "⚠️",
                            "極差": "❌"
                        }.get(selected_player["rating"], "❓")
                        
                        await channel.send(
                            f"🎯 **已選擇玩家：** {selected_player['name']}\n"
                            f"   職業：{selected_player['class']}\n"
                            f"   當前評級：{rating_emoji} {selected_player['rating']}\n"
                            f"   當前權重：{selected_player['weight']:.1f}\n\n"
                            f"**請選擇評級：** ⭐ 🆗 ⚠️ ❌"
                        )
                    else:
                        await channel.send("❌ 無效的玩家選擇！")
                
                # 處理評級按鈕
                elif emoji in self.rating_emojis:
                    rating = self.rating_emojis[emoji]
                    
                    # 檢查是否有選擇玩家
                    if "selected_player" not in activity:
                        await channel.send("❌ 請先選擇玩家（按數字/字母按鈕）！")
                        return
                    
                    player_id = activity["selected_player"]
                    
                    # 找到玩家資訊
                    player_info = None
                    player_name = ""
                    for participant in participants_info:
                        if participant["id"] == player_id:
                            player_info = participant
                            player_name = participant["name"]
                            break
                    
                    if not player_info:
                        await channel.send("❌ 找不到玩家資訊！")
                        return
                    
                    # 獲取舊評分
                    old_rating = activity["ratings"].get(player_id, "普通")
                    
                    # 記錄新評分
                    activity["ratings"][player_id] = rating
                    
                    # 計算權重
                    player_class = activity["class_selections"].get(player_id, "未選擇")
                    weight = self.rating_weights[rating]
                    if player_class in self.class_bonus:
                        weight *= self.class_bonus[player_class]
                    
                    activity["weights"][player_id] = weight
                    
                    # 更新用戶數據
                    if player_id not in self.user_data:
                        try:
                            player_user = await self.bot.fetch_user(int(player_id))
                            username = player_user.name
                        except:
                            username = player_name
                        
                        self.user_data[player_id] = {
                            "name": username,
                            "rating_counts": {"優秀": 0, "普通": 0, "待改進": 0, "極差": 0},
                            "activities": [],
                            "attendance_periods": {}
                        }
                    
                    # 更新評分次數統計
                    if rating in self.user_data[player_id]["rating_counts"]:
                        self.user_data[player_id]["rating_counts"][rating] += 1
                    
                    # 減少舊評分次數（如果不是普通）
                    if old_rating != "普通" and old_rating in self.user_data[player_id]["rating_counts"]:
                        self.user_data[player_id]["rating_counts"][old_rating] = max(0, self.user_data[player_id]["rating_counts"][old_rating] - 1)
                    
                    # 記錄活動
                    activity_record = {
                        "name": activity["name"],
                        "rating": rating,
                        "class": player_class,
                        "prize": activity["prize"],
                        "date": activity.get("start_time", datetime.now()).strftime("%Y-%m-%d"),
                        "period": activity["period"]
                    }
                    
                    # 檢查是否已記錄此活動
                    existing_index = -1
                    for i, record in enumerate(self.user_data[player_id]["activities"]):
                        if record["name"] == activity["name"]:
                            existing_index = i
                            break
                    
                    if existing_index >= 0:
                        # 更新現有記錄
                        old_rating_in_record = self.user_data[player_id]["activities"][existing_index]["rating"]
                        if old_rating_in_record != rating:
                            # 減少舊評分次數
                            if old_rating_in_record in self.user_data[player_id]["rating_counts"]:
                                self.user_data[player_id]["rating_counts"][old_rating_in_record] = max(0, self.user_data[player_id]["rating_counts"][old_rating_in_record] - 1)
                        
                        self.user_data[player_id]["activities"][existing_index] = activity_record
                    else:
                        # 新增記錄
                        self.user_data[player_id]["activities"].append(activity_record)
                    
                    # 顯示評級EMOJI
                    rating_emoji_display = {
                        "優秀": "⭐",
                        "普通": "🆗",
                        "待改進": "⚠️",
                        "極差": "❌"
                    }.get(rating, "❓")
                    
                    await channel.send(f"✅ 已為 **{player_name}** 評級：{rating_emoji_display} **{rating}** (權重: {weight:.1f})")
                    
                    # 通知玩家
                    try:
                        player_user = await self.bot.fetch_user(int(player_id))
                        rating_emoji_msg = {
                            "優秀": "⭐ 優秀",
                            "普通": "🆗 普通",
                            "待改進": "⚠️ 待改進",
                            "極差": "❌ 極差"
                        }.get(rating, rating)
                        
                        await player_user.send(f"⭐ 你在活動 **'{activity['name']}'** 中獲得 {rating_emoji_msg} 評級！\n權重: {weight:.1f}")
                    except:
                        pass
                    
                    # 刷新評分界面
                    await self.refresh_rating_interface(channel, activity_id)
                    
                    # 清除選擇的玩家
                    if "selected_player" in activity:
                        del activity["selected_player"]
                
                # 處理抽獎按鈕
                elif emoji == "🎲":
                    await self.execute_lottery(channel, activity_id)
                return

    async def refresh_rating_interface(self, channel, activity_id):
        """刷新評分界面"""
        
        if activity_id not in self.evaluations:
            return
            
        activity = self.evaluations[activity_id]
        
        # 獲取參與者資訊
        participants_info = await self.get_participants_info(activity_id)
        
        # 創建新的評分界面
        embed = discord.Embed(
            title=f"⭐ 評分時間 - {activity['name']}",
            description=f"**活動ID:** `{activity_id}`\n**參與人數：** {len(participants_info)}人\n**抽獎物品：** {activity['prize']}",
            color=discord.Color.gold()
        )
        
        # 參與者列表
        if participants_info:
            participants_text = ""
            for i, participant in enumerate(participants_info[:15]):  # 只顯示前15人
                class_emoji = {
                    "坦克": "🛡️",
                    "输出": "⚔️",
                    "治疗": "💚",
                    "辅助": "💛",
                    "未選擇": "❓"
                }.get(participant["class"], "❓")
                
                rating_emoji = {
                    "優秀": "⭐",
                    "普通": "🆗",
                    "待改進": "⚠️",
                    "極差": "❌"
                }.get(participant["rating"], "❓")
                
                weight_display = f"{participant['weight']:.1f}"
                player_emoji = self.number_emojis[i] if i < len(self.number_emojis) else f"{i+1}."
                
                participants_text += f"{player_emoji} {class_emoji} **{participant['name']}** - {participant['class']} | {rating_emoji} {participant['rating']} (權重: {weight_display})\n"
            
            if len(participants_info) > 15:
                participants_text += f"\n... 還有 {len(participants_info) - 15} 位參與者，請使用下方按鈕選擇"
            
            embed.add_field(name="**📋 參與者列表**", value=participants_text, inline=False)
        else:
            embed.add_field(name="**📋 參與者列表**", value="暫無參與者", inline=False)
        
        # 操作指南
        guide = (
            f"**🎮 EMOJI評分系統：**\n\n"
            f"**1. 選擇玩家：**\n"
            f"   按玩家對應的數字/字母按鈕\n\n"
            f"**2. 選擇評級：**\n"
            f"   ⭐ = 優秀 (權重 1.2)\n"
            f"   🆗 = 普通 (權重 1.0)\n"
            f"   ⚠️ = 待改進 (權重 0.8)\n"
            f"   ❌ = 極差 (權重 0.2)\n\n"
            f"**3. 完成抽獎：**\n"
            f"   按 🎲 開始抽獎"
        )
        
        embed.add_field(name="**📝 操作說明**", value=guide, inline=False)
        
        # 總權重計算
        total_weight = sum(p["weight"] for p in participants_info if isinstance(p["weight"], (int, float)))
        embed.add_field(name="**[總權重]**", value=f"{total_weight:.1f}", inline=True)
        
        # 編輯原始訊息
        try:
            rating_msg = await channel.fetch_message(activity["rating_msg_id"])
            await rating_msg.edit(embed=embed)
        except:
            pass

    async def execute_lottery(self, channel, activity_id):
        """執行抽獎"""
        
        if activity_id not in self.evaluations:
            await channel.send(f"❌ 找不到活動：{activity_id}")
            return
            
        activity = self.evaluations[activity_id]
        
        # 檢查是否有評分
        if not activity["weights"]:
            await channel.send("❌ 還沒有任何評分，無法抽獎！")
            return
        
        # 準備抽獎名單（根據權重）
        weighted_players = []
        for player_id, weight in activity["weights"].items():
            # 權重四捨五入取整數，作為抽獎次數
            entries = max(1, round(weight))
            weighted_players.extend([player_id] * entries)
        
        if not weighted_players:
            await channel.send("❌ 沒有可抽獎的玩家！")
            return
        
        # 抽獎
        winner_id = random.choice(weighted_players)
        
        try:
            winner = await self.bot.fetch_user(int(winner_id))
            winner_name = winner.mention
        except:
            winner_name = f"用戶{winner_id[:4]}"
        
        # 獲取中獎者資料
        rating = activity["ratings"].get(winner_id, "普通")
        rating_emoji = {
            "優秀": "⭐",
            "普通": "🆗",
            "待改進": "⚠️",
            "極差": "❌"
        }.get(rating, "❓")
        
        player_class = activity["class_selections"].get(winner_id, "未選擇")
        weight = activity["weights"].get(winner_id, 1.0)
        
        # 發送中獎訊息
        embed = discord.Embed(
            title="🎉 抽獎結果",
            description=f"**活動：** {activity['name']}\n**獎品：** {activity['prize']}",
            color=discord.Color.gold()
        )
        embed.add_field(name="🏆 中獎者", value=winner_name, inline=False)
        embed.add_field(name="評級", value=f"{rating_emoji} {rating}", inline=True)
        embed.add_field(name="職業", value=player_class, inline=True)
        embed.add_field(name="權重", value=f"{weight:.1f}", inline=True)
        
        await channel.send(embed=embed)
        
        # 通知中獎者
        try:
            if winner:
                await winner.send(f"🎉 恭喜！你在活動 **'{activity['name']}'** 中抽中了 **{activity['prize']}**！")
        except:
            pass
        
        # 標記活動完成
        activity["status"] = "completed"

    def calculate_attendance_rate(self, user_id, period=None):
        """計算指定半月期的出席率"""
        
        if user_id not in self.user_data:
            return 0.0, 0, 0, {}
        
        data = self.user_data[user_id]
        
        if not period:
            period = self.get_current_period()
        
        if period not in data["attendance_periods"]:
            return 0.0, 0, 0, {}
        
        period_data = data["attendance_periods"][period]
        total_events = period_data["total_events"]
        attended = period_data["attended"]
        
        if total_events > 0:
            rate = (attended / total_events) * 100
        else:
            rate = 0.0
        
        return round(rate, 1), total_events, attended, period_data

    @commands.command(name="我的數據")
    async def my_stats(self, ctx):
        user_id = str(ctx.author.id)
        current_period = self.get_current_period()
        
        # 確保用戶數據存在
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "name": ctx.author.name,
                "rating_counts": {"優秀": 0, "普通": 0, "待改進": 0, "極差": 0},
                "activities": [],
                "attendance_periods": {},
                "attended_events": set()
            }
        
        data = self.user_data[user_id]
        
        # 創建數據嵌入
        embed = discord.Embed(
            title=f"📊 {ctx.author.name} 的評核數據",
            color=discord.Color.green()
        )
        
        # 顯示當前半月期出席率
        attendance_rate, total_events, attended, period_data = self.calculate_attendance_rate(user_id, current_period)
        
        attendance_info = (
            f"**當前半月期：** {current_period}\n"
            f"**總活動數：** {total_events} 次\n"
            f"**實際出席：** {attended} 次\n"
            f"**出席率：** {attendance_rate}%\n\n"
            f"**計算公式：** (實際出席次數 ÷ 總活動數) × 100%\n"
            f"**註：** 僅計算活動時間內簽到，過時簽到不計入"
        )
        
        embed.add_field(
            name="📅 半月期出席率",
            value=attendance_info,
            inline=False
        )
        
        # 顯示評級次數統計（使用EMOJI）
        rating_counts = data["rating_counts"]
        total_ratings = sum(rating_counts.values())
        
        ratings_info = f"**總評級次數：** {total_ratings} 次\n\n"
        
        rating_emojis_display = {
            "優秀": "⭐ 優秀",
            "普通": "🆗 普通",
            "待改進": "⚠️ 待改進",
            "極差": "❌ 極差"
        }
        
        for rating, count in rating_counts.items():
            if total_ratings > 0:
                percentage = (count / total_ratings) * 100
                emoji_display = rating_emojis_display.get(rating, rating)
                ratings_info += f"**{emoji_display}：** {count}次 ({percentage:.1f}%)\n"
            else:
                emoji_display = rating_emojis_display.get(rating, rating)
                ratings_info += f"**{emoji_display}：** {count}次\n"
        
        embed.add_field(
            name="⭐ 評級統計",
            value=ratings_info,
            inline=False
        )
        
        # 顯示最近活動記錄
        if data["activities"]:
            recent_activities = data["activities"][-5:]  # 最近5個活動
            activities_text = ""
            for activity in recent_activities:
                rating_emoji = {
                    "優秀": "⭐",
                    "普通": "🆗",
                    "待改進": "⚠️",
                    "極差": "❌"
                }.get(activity["rating"], "❓")
                
                activities_text += f"• {activity['name']} - {rating_emoji} {activity['rating']} ({activity['date']})\n"
            
            embed.add_field(
                name="📝 最近活動記錄",
                value=activities_text,
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="所有人的數據")
    async def all_stats(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ 需要管理員權限！")
            return
        
        if not self.user_data:
            await ctx.send("📊 目前還沒有任何數據。")
            return
        
        embed = discord.Embed(
            title="📊 所有人評核數據",
            color=discord.Color.gold()
        )
        
        # 收集所有用戶數據
        user_stats = []
        current_period = self.get_current_period()
        
        for user_id, data in self.user_data.items():
            # 計算當前半月期出席率
            attendance_rate, total_events, attended, _ = self.calculate_attendance_rate(user_id, current_period)
            
            # 計算總評分次數
            total_ratings = sum(data["rating_counts"].values())
            
            user_stats.append({
                "name": data["name"],
                "attendance_rate": attendance_rate,
                "total_events": total_events,
                "attended": attended,
                "total_ratings": total_ratings,
                "excellent": data["rating_counts"]["優秀"],
                "good": data["rating_counts"]["普通"],
                "needs_improvement": data["rating_counts"]["待改進"],
                "poor": data["rating_counts"]["極差"]
            })
        
        # 按照出席率排序
        user_stats.sort(key=lambda x: x["attendance_rate"], reverse=True)
        
        # 顯示前10名
        top_10 = user_stats[:10]
        if top_10:
            stats_text = ""
            for i, stat in enumerate(top_10, 1):
                stats_text += (
                    f"**{i}. {stat['name']}**\n"
                    f"出席率: {stat['attendance_rate']}% ({stat['attended']}/{stat['total_events']})\n"
                    f"評級: ⭐{stat['excellent']} 🆗{stat['good']} ⚠️{stat['needs_improvement']} ❌{stat['poor']}\n\n"
                )
            
            embed.add_field(
                name="🏆 前10名玩家",
                value=stats_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🏆 前10名玩家",
                value="暫無數據",
                inline=False
            )
        
        # 顯示統計摘要
        if user_stats:
            avg_attendance = sum(stat["attendance_rate"] for stat in user_stats) / len(user_stats)
            total_players = len(user_stats)
            total_attended = sum(stat["attended"] for stat in user_stats)
            total_events_sum = sum(stat["total_events"] for stat in user_stats)
            
            summary = (
                f"**玩家總數：** {total_players}人\n"
                f"**總活動數：** {total_events_sum}次\n"
                f"**總出席次數：** {total_attended}次\n"
                f"**平均出席率：** {avg_attendance:.1f}%\n"
                f"**數據週期：** {current_period}"
            )
            
            embed.add_field(
                name="📈 統計摘要",
                value=summary,
                inline=False
            )
        
        await ctx.send(embed=embed)

# 添加 setup 函式（這是載入 Cog 的入口點）
async def setup(bot):
    await bot.add_cog(Evaluation(bot))