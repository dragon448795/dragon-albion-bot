import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import random
import json
import os  # 新增

class Evaluation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.evaluations = {}
        self.user_data = {}
        self.attendance_records = {}
        
        # ============ 新增：權限系統 ============
        self.permissions_file = "data/evaluation_perms.json"
        self.default_permissions = {
            "allowed_roles": [],
            "allowed_users": [],
            "require_manage_guild": True,
            "admin_only": False
        }
        self.permissions = self.load_permissions()
        print(f"✅ 評核系統已初始化，已載入 {len(self.permissions)} 個伺服器權限設定")
        # ============ 權限系統結束 ============
        
        # 當前半月期計算
        self.current_period = self.get_current_period()
        
        # 評分權重設定
        self.rating_weights = {
            "優秀": 1.2,
            "普通": 1.0,
            "待改進": 0.8,
            "極差": 0.2
        }
        
        # 職業加成
        self.class_bonus = {
            "坦克": 1.0,
            "输出": 1.0,
            "治疗": 1.2,
            "辅助": 1.0
        }
        
        # 評分EMOJI對應
        self.rating_emojis = {
            "⭐": "優秀",
            "🆗": "普通",
            "⚠️": "待改進",
            "❌": "極差"
        }
        
        # 數字EMOJI對應玩家（1-50）
        self.number_emojis = [
            "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
            "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
            "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹",
            "🇺", "🇻", "🇼", "🇽", "🇾", "🇿", "🔴", "🟠", "🟡", "🟢",
            "🔵", "🟣", "🟤", "⚫", "⚪", "🟥", "🟧", "🟨", "🟩", "🟦"
        ]

    # ============ 新增：權限系統方法 ============
    
    def load_permissions(self) -> dict:
        """載入權限設定"""
        try:
            os.makedirs("data", exist_ok=True)
            if os.path.exists(self.permissions_file):
                with open(self.permissions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_permissions(self):
        """保存權限設定"""
        try:
            with open(self.permissions_file, 'w', encoding='utf-8') as f:
                json.dump(self.permissions, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def get_guild_permissions(self, guild_id: int) -> dict:
        """獲取伺服器權限設定"""
        guild_str = str(guild_id)
        if guild_str not in self.permissions:
            self.permissions[guild_str] = self.default_permissions.copy()
            self.save_permissions()
        return self.permissions[guild_str]
    
    def update_guild_permissions(self, guild_id: int, updates: dict):
        """更新伺服器權限設定"""
        guild_str = str(guild_id)
        if guild_str not in self.permissions:
            self.permissions[guild_str] = self.default_permissions.copy()
        self.permissions[guild_str].update(updates)
        self.save_permissions()
    
    def check_permission(self, ctx) -> bool:
        """檢查用戶是否有權限"""
        guild_id = ctx.guild.id
        user = ctx.author
        perms = self.get_guild_permissions(guild_id)
        
        # 如果設定為僅管理員可用
        if perms.get("admin_only", False):
            return user.guild_permissions.administrator
        
        # 伺服器管理員直接通過
        if user.guild_permissions.administrator:
            return True
        
        # 檢查是否需要管理伺服器權限
        if perms.get("require_manage_guild", True):
            if user.guild_permissions.manage_guild:
                return True
        
        # 檢查是否在允許的用戶列表中
        user_id_str = str(user.id)
        if user_id_str in [str(uid) for uid in perms.get("allowed_users", [])]:
            return True
        
        # 檢查是否有允許的角色
        user_role_ids = [str(role.id) for role in user.roles]
        allowed_role_ids = [str(rid) for rid in perms.get("allowed_roles", [])]
        
        for role_id in user_role_ids:
            if role_id in allowed_role_ids:
                return True
        
        return False
    
    def get_permission_error_message(self, ctx) -> str:
        """獲取權限錯誤訊息"""
        guild_id = ctx.guild.id
        perms = self.get_guild_permissions(guild_id)
        
        lines = ["❌ **權限不足**"]
        lines.append("你需要以下條件之一：")
        
        conditions = []
        
        if perms.get("admin_only", False):
            conditions.append("• 伺服器管理員")
        else:
            if perms.get("require_manage_guild", True):
                conditions.append("• 管理伺服器權限")
            
            allowed_roles = perms.get("allowed_roles", [])
            if allowed_roles:
                role_mentions = []
                for role_id in allowed_roles[:5]:
                    role = ctx.guild.get_role(int(role_id))
                    if role:
                        role_mentions.append(role.mention)
                if role_mentions:
                    conditions.append(f"• 擁有身份組：{', '.join(role_mentions)}")
            
            allowed_users = perms.get("allowed_users", [])
            if allowed_users:
                conditions.append(f"• 已被管理員授權（共 {len(allowed_users)} 人）")
        
        if conditions:
            lines.append("\n".join(conditions))
        
        lines.append(f"\n使用 `!評核權限 查看` 了解詳情")
        lines.append(f"使用 `!評核權限 幫助` 查看設定指令")
        
        return "\n".join(lines)
    
    # ============ 新增：權限管理指令 ============
    
    @commands.command(name="評核權限", aliases=["evalperms", "評核權限設定"])
    @commands.has_permissions(administrator=True)
    async def evaluation_permissions(self, ctx, 動作: str = "查看", *, 參數: str = None):
        """評核系統權限管理（僅管理員）"""
        
        guild_id = ctx.guild.id
        
        if 動作 == "查看":
            perms = self.get_guild_permissions(guild_id)
            
            embed = discord.Embed(
                title="📋 評核系統權限設定",
                description=f"伺服器：{ctx.guild.name}",
                color=0x3498db
            )
            
            basic_info = []
            basic_info.append(f"**僅管理員可用:** {'✅' if perms.get('admin_only', False) else '❌'}")
            basic_info.append(f"**需要管理伺服器權限:** {'✅' if perms.get('require_manage_guild', True) else '❌'}")
            
            embed.add_field(name="⚙️ 基本設定", value="\n".join(basic_info), inline=False)
            
            allowed_roles = []
            for role_id in perms.get("allowed_roles", []):
                role = ctx.guild.get_role(int(role_id))
                if role:
                    allowed_roles.append(f"{role.mention} (`{role_id}`)")
            
            embed.add_field(
                name=f"👥 允許的角色 ({len(allowed_roles)})",
                value="\n".join(allowed_roles) if allowed_roles else "無",
                inline=False
            )
            
            allowed_users = []
            for user_id in perms.get("allowed_users", []):
                member = ctx.guild.get_member(int(user_id))
                if member:
                    allowed_users.append(f"{member.mention} (`{user_id}`)")
            
            embed.add_field(
                name=f"👤 允許的用戶 ({len(allowed_users)})",
                value="\n".join(allowed_users) if allowed_users else "無",
                inline=False
            )
            
            has_perm = self.check_permission(ctx)
            embed.add_field(
                name="🔍 你的權限狀態",
                value=f"{'✅ 有權限' if has_perm else '❌ 無權限'}",
                inline=False
            )
            
            embed.set_footer(text="使用 !評核權限 幫助 查看所有指令")
            await ctx.send(embed=embed)
        
        elif 動作 == "幫助":
            embed = discord.Embed(title="📖 評核權限指令幫助", color=0x7289da)
            embed.add_field(name="查看設定", value="`!評核權限 查看`", inline=False)
            embed.add_field(name="角色管理", value="`!評核權限 添加角色 @角色`\n`!評核權限 移除角色 @角色`", inline=False)
            embed.add_field(name="用戶管理", value="`!評核權限 添加用戶 @用戶`\n`!評核權限 移除用戶 @用戶`", inline=False)
            embed.add_field(name="權限設定", value="`!評核權限 管理權限 開啟/關閉`\n`!評核權限 僅管理員 開啟/關閉`\n`!評核權限 重置`", inline=False)
            await ctx.send(embed=embed)
        
        elif 動作 == "添加角色":
            if not ctx.message.role_mentions:
                await ctx.send("❌ 請使用 @ 提及要添加的角色")
                return
            
            role = ctx.message.role_mentions[0]
            perms = self.get_guild_permissions(guild_id)
            role_id_str = str(role.id)
            allowed_roles = [str(r) for r in perms.get("allowed_roles", [])]
            
            if role_id_str in allowed_roles:
                await ctx.send(f"ℹ️ 角色 {role.mention} 已經在允許列表中")
                return
            
            if "allowed_roles" not in perms:
                perms["allowed_roles"] = []
            perms["allowed_roles"].append(int(role.id))
            self.update_guild_permissions(guild_id, perms)
            await ctx.send(f"✅ 已添加角色 {role.mention} 到允許列表")
        
        elif 動作 == "移除角色":
            if not ctx.message.role_mentions:
                await ctx.send("❌ 請使用 @ 提及要移除的角色")
                return
            
            role = ctx.message.role_mentions[0]
            perms = self.get_guild_permissions(guild_id)
            role_id_str = str(role.id)
            allowed_roles = [str(r) for r in perms.get("allowed_roles", [])]
            
            if role_id_str not in allowed_roles:
                await ctx.send(f"ℹ️ 角色 {role.mention} 不在允許列表中")
                return
            
            perms["allowed_roles"] = [r for r in perms.get("allowed_roles", []) if str(r) != role_id_str]
            self.update_guild_permissions(guild_id, perms)
            await ctx.send(f"✅ 已從允許列表中移除角色 {role.mention}")
        
        elif 動作 == "添加用戶":
            if not ctx.message.mentions:
                await ctx.send("❌ 請使用 @ 提及要添加的用戶")
                return
            
            user = ctx.message.mentions[0]
            perms = self.get_guild_permissions(guild_id)
            user_id_str = str(user.id)
            allowed_users = [str(u) for u in perms.get("allowed_users", [])]
            
            if user_id_str in allowed_users:
                await ctx.send(f"ℹ️ 用戶 {user.mention} 已經在允許列表中")
                return
            
            if "allowed_users" not in perms:
                perms["allowed_users"] = []
            perms["allowed_users"].append(int(user.id))
            self.update_guild_permissions(guild_id, perms)
            await ctx.send(f"✅ 已添加用戶 {user.mention} 到允許列表")
        
        elif 動作 == "移除用戶":
            if not ctx.message.mentions:
                await ctx.send("❌ 請使用 @ 提及要移除的用戶")
                return
            
            user = ctx.message.mentions[0]
            perms = self.get_guild_permissions(guild_id)
            user_id_str = str(user.id)
            allowed_users = [str(u) for u in perms.get("allowed_users", [])]
            
            if user_id_str not in allowed_users:
                await ctx.send(f"ℹ️ 用戶 {user.mention} 不在允許列表中")
                return
            
            perms["allowed_users"] = [u for u in perms.get("allowed_users", []) if str(u) != user_id_str]
            self.update_guild_permissions(guild_id, perms)
            await ctx.send(f"✅ 已從允許列表中移除用戶 {user.mention}")
        
        elif 動作 == "管理權限":
            if 參數 not in ["開啟", "關閉"]:
                await ctx.send("❌ 請指定 `開啟` 或 `關閉`")
                return
            
            perms = self.get_guild_permissions(guild_id)
            perms["require_manage_guild"] = (參數 == "開啟")
            self.update_guild_permissions(guild_id, perms)
            await ctx.send(f"✅ 已{'開啟' if 參數 == '開啟' else '關閉'}「需要管理伺服器權限」設定")
        
        elif 動作 == "僅管理員":
            if 參數 not in ["開啟", "關閉"]:
                await ctx.send("❌ 請指定 `開啟` 或 `關閉`")
                return
            
            perms = self.get_guild_permissions(guild_id)
            perms["admin_only"] = (參數 == "開啟")
            self.update_guild_permissions(guild_id, perms)
            await ctx.send(f"✅ 已{'開啟' if 參數 == '開啟' else '關閉'}「僅管理員可用」設定")
        
        elif 動作 == "重置":
            confirm_embed = discord.Embed(
                title="⚠️ 確認重置",
                description="確定要重置評核系統權限設定嗎？\n這將恢復為默認設定。",
                color=0xff9900
            )
            confirm_embed.set_footer(text="輸入 '確認重置' 以確認")
            await ctx.send(embed=confirm_embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content == "確認重置"
            
            try:
                await self.bot.wait_for('message', timeout=30.0, check=check)
                self.permissions[str(guild_id)] = self.default_permissions.copy()
                self.save_permissions()
                await ctx.send("✅ 已重置評核系統權限設定")
            except asyncio.TimeoutError:
                await ctx.send("❌ 重置已取消")
        
        else:
            await ctx.send("❌ 未知的動作，使用 `!評核權限 幫助` 查看可用指令")
    
    # ============ 新增：權限測試指令 ============
    
    @commands.command(name="測試權限")
    async def test_permission(self, ctx):
        """測試你是否擁有評核系統權限"""
        if self.check_permission(ctx):
            embed = discord.Embed(
                title="✅ 權限測試通過",
                description="你有權限使用評核系統！",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ 權限測試失敗",
                description=self.get_permission_error_message(ctx),
                color=0xff0000
            )
        await ctx.send(embed=embed)
    
    # ============ 以下是你原本的程式碼，只修改創建評核活動指令 ============
    
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
        
        # ============ 新增：權限檢查 ============
        if not self.check_permission(ctx):
            error_msg = self.get_permission_error_message(ctx)
            await ctx.send(error_msg)
            return
        # ============ 權限檢查結束 ============
        
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
            "selected_player": None
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
        
        activity["allow_signup"] = False
        activity["status"] = "rating"
        
        await ctx.send(f"⏰ 簽到已結束！現在進入評分階段。")
        await self.show_rating_interface(ctx, activity_id)

    async def show_rating_interface(self, ctx, activity_id):
        """顯示評分界面"""
        
        if activity_id not in self.evaluations:
            return
            
        activity = self.evaluations[activity_id]
        participants_info = await self.get_participants_info(activity_id)
        
        for participant in participants_info:
            if participant["rating"] == "未評分":
                activity["ratings"][participant["id"]] = "普通"
                participant["rating"] = "普通"
                
                weight = self.rating_weights["普通"]
                if participant["class"] in self.class_bonus:
                    weight *= self.class_bonus[participant["class"]]
                activity["weights"][participant["id"]] = weight
                participant["weight"] = weight
        
        embed = discord.Embed(
            title=f"⭐ 評分時間 - {activity['name']}",
            description=f"**活動ID:** `{activity_id}`\n**參與人數：** {len(participants_info)}人\n**抽獎物品：** {activity['prize']}",
            color=discord.Color.gold()
        )
        
        if participants_info:
            participants_text = ""
            for i, participant in enumerate(participants_info[:15]):
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
        
        total_weight = sum(p["weight"] for p in participants_info if isinstance(p["weight"], (int, float)))
        embed.add_field(name="**[總權重]**", value=f"{total_weight:.1f}", inline=True)
        
        rating_msg = await ctx.send(embed=embed)
        activity["rating_msg_id"] = rating_msg.id
        
        max_players = min(len(participants_info), 20)
        for i in range(max_players):
            await rating_msg.add_reaction(self.number_emojis[i])
        
        for emoji in self.rating_emojis.keys():
            await rating_msg.add_reaction(emoji)
        
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
            
            player_class = activity["class_selections"].get(user_id, "未選擇")
            rating = activity["ratings"].get(user_id, "未評分")
            
            weight = 1.0
            if rating in self.rating_weights:
                weight = self.rating_weights[rating]
                if player_class in self.class_bonus:
                    weight *= self.class_bonus[player_class]
            elif rating == "未評分":
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
        
        for activity_id, activity in self.evaluations.items():
            if activity.get("signup_msg_id") == msg_id:
                if not activity.get("allow_signup", True):
                    try:
                        await reaction.remove(user)
                    except:
                        pass
                    return
                
                if emoji == "✅":
                    if datetime.now() > activity["signup_end_time"]:
                        try:
                            await reaction.remove(user)
                        except:
                            pass
                        return
                    
                    activity["attendees"].add(user_id)
                    
                    if user_id not in self.user_data:
                        self.user_data[user_id] = {
                            "name": user.name,
                            "rating_counts": {"優秀": 0, "普通": 0, "待改進": 0, "極差": 0},
                            "activities": [],
                            "attendance_periods": {}
                        }
                    
                    period = activity["period"]
                    if period not in self.user_data[user_id]["attendance_periods"]:
                        self.user_data[user_id]["attendance_periods"][period] = {
                            "total_events": 0,
                            "attended": 0
                        }
                    
                    activity_key = f"{activity['name']}_{activity['start_time'].strftime('%Y%m%d%H%M%S')}"
                    if activity_key not in self.user_data[user_id].get("attended_events", set()):
                        if "attended_events" not in self.user_data[user_id]:
                            self.user_data[user_id]["attended_events"] = set()
                        
                        self.user_data[user_id]["attended_events"].add(activity_key)
                        self.user_data[user_id]["attendance_periods"][period]["total_events"] += 1
                    
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
            
            elif activity.get("rating_msg_id") == msg_id:
                if user_id != str(activity["creator"]):
                    return
                
                participants_info = await self.get_participants_info(activity_id)
                if not participants_info:
                    await channel.send("❌ 沒有參與者可以評分！")
                    return
                
                if emoji in self.number_emojis:
                    player_index = self.number_emojis.index(emoji)
                    if player_index < len(participants_info):
                        selected_player = participants_info[player_index]
                        activity["selected_player"] = selected_player["id"]
                        
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
                
                elif emoji in self.rating_emojis:
                    rating = self.rating_emojis[emoji]
                    
                    if "selected_player" not in activity:
                        await channel.send("❌ 請先選擇玩家（按數字/字母按鈕）！")
                        return
                    
                    player_id = activity["selected_player"]
                    
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
                    
                    old_rating = activity["ratings"].get(player_id, "普通")
                    activity["ratings"][player_id] = rating
                    
                    player_class = activity["class_selections"].get(player_id, "未選擇")
                    weight = self.rating_weights[rating]
                    if player_class in self.class_bonus:
                        weight *= self.class_bonus[player_class]
                    
                    activity["weights"][player_id] = weight
                    
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
                    
                    if rating in self.user_data[player_id]["rating_counts"]:
                        self.user_data[player_id]["rating_counts"][rating] += 1
                    
                    if old_rating != "普通" and old_rating in self.user_data[player_id]["rating_counts"]:
                        self.user_data[player_id]["rating_counts"][old_rating] = max(0, self.user_data[player_id]["rating_counts"][old_rating] - 1)
                    
                    activity_record = {
                        "name": activity["name"],
                        "rating": rating,
                        "class": player_class,
                        "prize": activity["prize"],
                        "date": activity.get("start_time", datetime.now()).strftime("%Y-%m-%d"),
                        "period": activity["period"]
                    }
                    
                    existing_index = -1
                    for i, record in enumerate(self.user_data[player_id]["activities"]):
                        if record["name"] == activity["name"]:
                            existing_index = i
                            break
                    
                    if existing_index >= 0:
                        old_rating_in_record = self.user_data[player_id]["activities"][existing_index]["rating"]
                        if old_rating_in_record != rating:
                            if old_rating_in_record in self.user_data[player_id]["rating_counts"]:
                                self.user_data[player_id]["rating_counts"][old_rating_in_record] = max(0, self.user_data[player_id]["rating_counts"][old_rating_in_record] - 1)
                        
                        self.user_data[player_id]["activities"][existing_index] = activity_record
                    else:
                        self.user_data[player_id]["activities"].append(activity_record)
                    
                    rating_emoji_display = {
                        "優秀": "⭐",
                        "普通": "🆗",
                        "待改進": "⚠️",
                        "極差": "❌"
                    }.get(rating, "❓")
                    
                    await channel.send(f"✅ 已為 **{player_name}** 評級：{rating_emoji_display} **{rating}** (權重: {weight:.1f})")
                    
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
                    
                    await self.refresh_rating_interface(channel, activity_id)
                    
                    if "selected_player" in activity:
                        del activity["selected_player"]
                
                elif emoji == "🎲":
                    await self.execute_lottery(channel, activity_id)
                return

    async def refresh_rating_interface(self, channel, activity_id):
        """刷新評分界面"""
        
        if activity_id not in self.evaluations:
            return
            
        activity = self.evaluations[activity_id]
        participants_info = await self.get_participants_info(activity_id)
        
        embed = discord.Embed(
            title=f"⭐ 評分時間 - {activity['name']}",
            description=f"**活動ID:** `{activity_id}`\n**參與人數：** {len(participants_info)}人\n**抽獎物品：** {activity['prize']}",
            color=discord.Color.gold()
        )
        
        if participants_info:
            participants_text = ""
            for i, participant in enumerate(participants_info[:15]):
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
        
        total_weight = sum(p["weight"] for p in participants_info if isinstance(p["weight"], (int, float)))
        embed.add_field(name="**[總權重]**", value=f"{total_weight:.1f}", inline=True)
        
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
        
        if not activity["weights"]:
            await channel.send("❌ 還沒有任何評分，無法抽獎！")
            return
        
        weighted_players = []
        for player_id, weight in activity["weights"].items():
            entries = max(1, round(weight))
            weighted_players.extend([player_id] * entries)
        
        if not weighted_players:
            await channel.send("❌ 沒有可抽獎的玩家！")
            return
        
        winner_id = random.choice(weighted_players)
        
        try:
            winner = await self.bot.fetch_user(int(winner_id))
            winner_name = winner.mention
        except:
            winner_name = f"用戶{winner_id[:4]}"
        
        rating = activity["ratings"].get(winner_id, "普通")
        rating_emoji = {
            "優秀": "⭐",
            "普通": "🆗",
            "待改進": "⚠️",
            "極差": "❌"
        }.get(rating, "❓")
        
        player_class = activity["class_selections"].get(winner_id, "未選擇")
        weight = activity["weights"].get(winner_id, 1.0)
        
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
        
        try:
            if winner:
                await winner.send(f"🎉 恭喜！你在活動 **'{activity['name']}'** 中抽中了 **{activity['prize']}**！")
        except:
            pass
        
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
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "name": ctx.author.name,
                "rating_counts": {"優秀": 0, "普通": 0, "待改進": 0, "極差": 0},
                "activities": [],
                "attendance_periods": {},
                "attended_events": set()
            }
        
        data = self.user_data[user_id]
        
        embed = discord.Embed(
            title=f"📊 {ctx.author.name} 的評核數據",
            color=discord.Color.green()
        )
        
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
        
        if data["activities"]:
            recent_activities = data["activities"][-5:]
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

    @commands.command(name="所有人的數據", aliases=["所有數據", "全體數據"])
    async def all_stats(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ 需要管理員權限！")
            return
        
        if not self.user_data:
            await ctx.send("📊 目前還沒有任何數據。")
            return
        
        user_stats = []
        current_period = self.get_current_period()
        
        for user_id, data in self.user_data.items():
            attendance_rate, total_events, attended, _ = self.calculate_attendance_rate(user_id, current_period)
            
            excellent = data["rating_counts"]["優秀"]
            good = data["rating_counts"]["普通"]
            needs_improvement = data["rating_counts"]["待改進"]
            poor = data["rating_counts"]["極差"]
            
            user_stats.append({
                "name": data["name"],
                "attendance_rate": attendance_rate,
                "total_events": total_events,
                "attended": attended,
                "excellent": excellent,
                "good": good,
                "needs_improvement": needs_improvement,
                "poor": poor,
                "user_id": user_id
            })
        
        user_stats.sort(key=lambda x: x["attendance_rate"], reverse=True)
        
        items_per_page = 30
        total_pages = (len(user_stats) + items_per_page - 1) // items_per_page
        
        class AllStatsPaginator(discord.ui.View):
            def __init__(self, user_stats, items_per_page, total_pages, current_period):
                super().__init__(timeout=180)
                self.user_stats = user_stats
                self.items_per_page = items_per_page
                self.total_pages = total_pages
                self.current_period = current_period
                self.current_page = 0
            
            async def create_page_embed(self):
                start_idx = self.current_page * self.items_per_page
                end_idx = min(start_idx + self.items_per_page, len(self.user_stats))
                current_page_stats = self.user_stats[start_idx:end_idx]
                
                embed = discord.Embed(
                    title=f"📊 全體數據統計 (第 {self.current_page + 1}/{self.total_pages} 頁)",
                    description=f"**數據週期：** {self.current_period}\n**總人數：** {len(self.user_stats)}人\n**排序：** 出席率（高→低）",
                    color=discord.Color.blue()
                )
                
                columns = 3
                rows_per_column = 10
                
                for col in range(columns):
                    start = col * rows_per_column
                    end = min(start + rows_per_column, len(current_page_stats))
                    
                    if start >= end:
                        continue
                    
                    column_text = ""
                    for i in range(start, end):
                        stat = current_page_stats[i]
                        rank = start_idx + i + 1
                        
                        column_text += (
                            f"**{rank}. {stat['name']}**\n"
                            f"出席: {stat['attended']}/{stat['total_events']} ({stat['attendance_rate']}%)\n"
                            f"評級: ⭐{stat['excellent']} 🆗{stat['good']} ⚠️{stat['needs_improvement']} ❌{stat['poor']}\n"
                        )
                    
                    embed.add_field(
                        name=f"第 {col*10+1}-{col*10+(end-start)} 名",
                        value=column_text,
                        inline=True
                    )
                
                if self.current_page == 0 and self.user_stats:
                    total_players = len(self.user_stats)
                    total_events = sum(stat["total_events"] for stat in self.user_stats)
                    total_attended = sum(stat["attended"] for stat in self.user_stats)
                    avg_attendance = sum(stat["attendance_rate"] for stat in self.user_stats) / total_players if total_players > 0 else 0
                    
                    summary_text = (
                        f"**玩家總數：** {total_players}人\n"
                        f"**總活動數：** {total_events}次\n"
                        f"**總出席次數：** {total_attended}次\n"
                        f"**平均出席率：** {avg_attendance:.1f}%\n"
                        f"**頁面操作：** 使用下方按鈕瀏覽"
                    )
                    
                    embed.add_field(
                        name="📈 統計摘要",
                        value=summary_text,
                        inline=False
                    )
                
                embed.set_footer(text=f"第 {self.current_page + 1}/{self.total_pages} 頁 | 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                return embed
            
            @discord.ui.button(label="◀️ 上一頁", style=discord.ButtonStyle.secondary, disabled=True)
            async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page > 0:
                    self.current_page -= 1
                    await interaction.response.edit_message(embed=await self.create_page_embed(), view=self)
            
            @discord.ui.button(label="▶️ 下一頁", style=discord.ButtonStyle.secondary)
            async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                    await interaction.response.edit_message(embed=await self.create_page_embed(), view=self)
            
            async def update_buttons(self):
                self.previous_page.disabled = self.current_page == 0
                self.next_page.disabled = self.current_page >= self.total_pages - 1
            
            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                await self.update_buttons()
                return True
        
        paginator = AllStatsPaginator(user_stats, items_per_page, total_pages, current_period)
        embed = await paginator.create_page_embed()
        
        paginator.previous_page.disabled = True
        paginator.next_page.disabled = total_pages <= 1
        
        await ctx.send(embed=embed, view=paginator)

async def setup(bot):
    await bot.add_cog(Evaluation(bot))
