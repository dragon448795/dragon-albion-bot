#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動抽獎系統 - 簡化版，不使用 aiosqlite
"""

import discord
from discord.ext import commands
import asyncio
import random
import json
import os
from datetime import datetime, timedelta

class GiveawayAuto(commands.Cog):
    """自動抽獎系統（簡化版）"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self.giveaway_tasks = {}
        self.data_file = "giveaways.json"
        self.bot.loop.create_task(self.load_giveaways())
    
    async def load_giveaways(self):
        """從 JSON 載入抽獎數據"""
        await self.bot.wait_until_ready()
        
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_giveaways = data
                    
                    # 恢復進行中的抽獎
                    for giveaway_id, giveaway in self.active_giveaways.items():
                        if giveaway.get("status") == "active":
                            end_time = datetime.fromisoformat(giveaway["end_time"])
                            now = datetime.now()
                            
                            if now >= end_time:
                                await self.draw_giveaway(giveaway_id)
                            else:
                                remaining_seconds = (end_time - now).total_seconds()
                                self.giveaway_tasks[giveaway_id] = asyncio.create_task(
                                    self.schedule_giveaway_end(giveaway_id, remaining_seconds)
                                )
            
            print(f"✅ 抽獎系統已載入 {len(self.active_giveaways)} 個抽獎活動")
            
        except Exception as e:
            print(f"❌ 載入抽獎數據失敗: {e}")
            self.active_giveaways = {}
    
    def save_giveaways(self):
        """保存抽獎數據"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_giveaways, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存抽獎數據失敗: {e}")
    
    @commands.command(name="創建自動抽獎", aliases=["create_auto_giveaway"])
    async def create_auto_giveaway(self, ctx, 獎品: str, 獲獎人數: int = 1, 持續時間: int = 60):
        """創建自動抽獎活動"""
        try:
            # 參數驗證
            if 獲獎人數 < 1:
                await ctx.send("❌ 獲獎人數必須至少為 1 人")
                return
            
            if 持續時間 < 1:
                await ctx.send("❌ 持續時間必須至少為 1 分鐘")
                return
            
            # 生成抽獎ID
            giveaway_id = f"giveaway_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            
            # 計算結束時間
            end_time = datetime.now() + timedelta(minutes=持續時間)
            
            # 創建抽獎訊息
            embed = discord.Embed(
                title="🎉 自動抽獎活動 🎉",
                description="**時間到自動開獎！**",
                color=0x00ff00,
                timestamp=end_time
            )
            
            embed.add_field(name="🎁 獎品", value=獎品, inline=True)
            embed.add_field(name="👑 中獎人數", value=str(獲獎人數), inline=True)
            embed.add_field(name="⏰ 結束時間", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            embed.add_field(name="🎫 參與人數", value="0 人", inline=True)
            
            embed.add_field(
                name="📝 參與方式",
                value="點擊下方 🎫 按鈕參與",
                inline=False
            )
            
            embed.set_footer(text=f"抽獎ID: {giveaway_id} | 主辦人: {ctx.author}")
            
            # 儲存抽獎資訊
            self.active_giveaways[giveaway_id] = {
                "channel_id": ctx.channel.id,
                "host_id": ctx.author.id,
                "prize": 獎品,
                "winners": 獲獎人數,
                "duration": 持續時間,
                "end_time": end_time.isoformat(),
                "status": "active",
                "participants": [],
                "button_id": f"giveaway_{giveaway_id}"
            }
            
            self.save_giveaways()
            
            # 創建按鈕
            class GiveawayButton(discord.ui.View):
                def __init__(self, cog, gid):
                    super().__init__(timeout=None)
                    self.cog = cog
                    self.giveaway_id = gid
                
                @discord.ui.button(label="🎫 參與抽獎", style=discord.ButtonStyle.green, custom_id=f"giveaway_{giveaway_id}")
                async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.bot:
                        return
                    
                    giveaway = self.cog.active_giveaways.get(self.giveaway_id)
                    if not giveaway or giveaway["status"] != "active":
                        await interaction.response.send_message("❌ 此抽獎已結束", ephemeral=True)
                        return
                    
                    # 檢查是否已參與
                    user_id = str(interaction.user.id)
                    if user_id in giveaway["participants"]:
                        await interaction.response.send_message("❌ 你已經參與了！", ephemeral=True)
                        return
                    
                    # 添加參與者
                    giveaway["participants"].append(user_id)
                    self.cog.save_giveaways()
                    
                    # 更新訊息
                    embed = interaction.message.embeds[0]
                    embed.set_field_at(
                        3,
                        name="🎫 參與人數",
                        value=f"{len(giveaway['participants'])} 人",
                        inline=True
                    )
                    
                    try:
                        await interaction.message.edit(embed=embed)
                    except:
                        pass
                    
                    await interaction.response.send_message(
                        f"✅ 成功參與！獎品: {giveaway['prize']}",
                        ephemeral=True
                    )
            
            # 發送訊息
            view = GiveawayButton(self, giveaway_id)
            message = await ctx.send(embed=embed, view=view)
            
            # 更新訊息ID
            self.active_giveaways[giveaway_id]["message_id"] = message.id
            self.save_giveaways()
            
            # 啟動定時任務
            self.giveaway_tasks[giveaway_id] = asyncio.create_task(
                self.schedule_giveaway_end(giveaway_id, 持續時間 * 60)
            )
            
            # 確認訊息
            confirm_embed = discord.Embed(
                title="✅ 抽獎已創建",
                color=0x00ff00
            )
            confirm_embed.add_field(name="獎品", value=獎品, inline=True)
            confirm_embed.add_field(name="中獎人數", value=str(獲獎人數), inline=True)
            confirm_embed.add_field(name="持續時間", value=f"{持續時間} 分鐘", inline=True)
            await ctx.send(embed=confirm_embed)
            
        except Exception as e:
            await ctx.send(f"❌ 錯誤: {str(e)}")
            print(f"抽獎創建錯誤: {e}")
    
    async def schedule_giveaway_end(self, giveaway_id: str, delay_seconds: float):
        """定時結束抽獎"""
        await asyncio.sleep(delay_seconds)
        await self.draw_giveaway(giveaway_id)
    
    async def draw_giveaway(self, giveaway_id: str):
        """執行開獎"""
        giveaway = self.active_giveaways.get(giveaway_id)
        if not giveaway or giveaway["status"] != "active":
            return
        
        try:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                return
            
            participants = giveaway["participants"]
            winners_count = giveaway["winners"]
            
            if not participants:
                # 無人參與
                embed = discord.Embed(
                    title="🎉 抽獎結束",
                    description=f"**{giveaway['prize']}**",
                    color=0xff0000
                )
                embed.add_field(name="結果", value="❌ 無人參與", inline=False)
                await channel.send(embed=embed)
            else:
                # 抽獎
                if len(participants) < winners_count:
                    winners_count = len(participants)
                
                winners = random.sample(participants, winners_count)
                
                embed = discord.Embed(
                    title="🎉 抽獎結束！",
                    description="**自動開獎完成**",
                    color=0xffd700
                )
                embed.add_field(name="獎品", value=giveaway['prize'], inline=False)
                embed.add_field(name="中獎人數", value=f"{winners_count} 人", inline=True)
                embed.add_field(name="總參與人數", value=f"{len(participants)} 人", inline=True)
                
                winners_text = "\n".join([f"🎉 <@{user_id}>" for user_id in winners])
                if winners_text:
                    embed.add_field(name="🏆 中獎者", value=winners_text, inline=False)
                
                await channel.send(embed=embed)
                
                # 標記中獎者
                if winners:
                    await channel.send(f"🎉 恭喜 {' '.join([f'<@{w}>' for w in winners])}")
            
            # 更新狀態
            giveaway["status"] = "completed"
            self.save_giveaways()
            
            # 清理任務
            if giveaway_id in self.giveaway_tasks:
                del self.giveaway_tasks[giveaway_id]
            
            print(f"✅ 抽獎 {giveaway_id} 已開獎")
            
        except Exception as e:
            print(f"開獎錯誤 {giveaway_id}: {e}")
    
    @commands.command(name="抽獎列表", aliases=["list_giveaways"])
    async def list_giveaways(self, ctx):
        """查看進行中的抽獎"""
        active = {k: v for k, v in self.active_giveaways.items() if v.get("status") == "active"}
        
        if not active:
            await ctx.send("📭 目前沒有進行中的抽獎")
            return
        
        embed = discord.Embed(title="📋 進行中的抽獎", color=0x3498db)
        
        for gid, g in active.items():
            end_time = datetime.fromisoformat(g["end_time"])
            embed.add_field(
                name=f"🎁 {g['prize']}",
                value=f"ID: `{gid}`\n參與: {len(g['participants'])}人\n結束: <t:{int(end_time.timestamp())}:R>",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """載入此Cog"""
    await bot.add_cog(GiveawayAuto(bot))
