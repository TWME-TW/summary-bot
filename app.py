import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import asyncio
 
# 載入環境變數
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))  # 記錄使用紀錄的頻道ID
 
# 設定 Bot 權限
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guild_messages = True
intents.guilds = True
 
bot = commands.Bot(command_prefix='!', intents=intents)
 
# 初始化 OpenAI 客戶端
client = OpenAI(api_key=OPENAI_API_KEY)
 
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f'已同步 {len(synced)} 個指令')
    except Exception as e:
        print(f'同步指令時發生錯誤: {e}')
    print(f'{bot.user} 已上線!')
 
@bot.tree.command(name="summary", description="總結此頻道最近的對話")
@app_commands.checks.has_permissions(read_messages=True)
async def summary(interaction: discord.Interaction):
    # 檢查機器人權限
    if not interaction.channel.permissions_for(interaction.guild.me).read_message_history:
        await interaction.response.send_message("我沒有讀取訊息歷史的權限！", ephemeral=True)
        return
    
    # 先回應，避免 Discord 顯示互動失敗
    await interaction.response.defer(ephemeral=True)
    
    try:
        # 獲取最近的訊息
        messages = []
        async for msg in interaction.channel.history(limit=50):  # 限制獲取50條訊息
            # if not msg.author.bot:  # 排除機器人的訊息
            messages.append(f"{msg.author.name}: {msg.content}")
        
        messages.reverse()  # 將訊息按時間順序排列
        
        if not messages:
            await interaction.followup.send("沒有找到可以總結的訊息。", ephemeral=True)
            return
        
        # 準備 GPT 提示
        prompt = f"""請依照時間與討論的內容總結以下對話內容，使用繁體中文回答：
 
{'\n'.join(messages)}
 
請提供一個簡潔的總結，分段包含主要討論點和重要結論。"""
        
        # 調用 OpenAI API
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是一個專業的對話總結助手，請用繁體中文進行總結。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        summary_text = response.choices[0].message.content
        
        # 發送總結給使用者（只有使用者能看到）
        await interaction.followup.send(f"對話總結：\n\n{summary_text}", ephemeral=True)
        
        # 記錄使用記錄
        try:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel and log_channel.permissions_for(interaction.guild.me).send_messages:
                embed = discord.Embed(
                    title="總結指令使用記錄",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="使用者", value=interaction.user.name, inline=True)
                embed.add_field(name="頻道", value=interaction.channel.name, inline=True)
                embed.add_field(name="訊息數量", value=len(messages), inline=True)
                await log_channel.send(embed=embed)
        except Exception as e:
            print(f"記錄發送失敗: {e}")
            
    except Exception as e:
        error_message = f"總結時發生錯誤: {str(e)}"
        await interaction.followup.send(error_message, ephemeral=True)
        print(error_message)
 
# 錯誤處理
@summary.error
async def summary_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("您沒有足夠的權限使用此指令。", ephemeral=True)
    else:
        await interaction.response.send_message(f"執行指令時發生錯誤: {str(error)}", ephemeral=True)
 
# 運行 Bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)