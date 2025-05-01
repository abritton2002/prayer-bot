import discord
from discord.ext import commands, tasks
import json
from datetime import datetime

TOKEN = "MTM2NzQ3NjEyMzkxNDczNTY4Nw.GLnze6.S58hgVqqWBiSreuo9inpqc4FDQsVCqVEac_Axs"
CHANNEL_ID = 1367468653531889689  # Replace with your Discord channel ID (an integer)

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())
PRAYER_FILE = "prayers.json"

def load_prayers():
    try:
        with open(PRAYER_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_prayers(data):
    with open(PRAYER_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    print(f"✅ Bot ready: {bot.user}")
    daily_reminder.start()

@bot.command()
async def add_request(ctx, *, request):
    prayers = load_prayers()
    prayers.append({
        "id": len(prayers)+1,
        "text": request,
        "status": "open",
        "added_by": ctx.author.name,
        "date": str(datetime.now().date())
    })
    save_prayers(prayers)
    await ctx.send(f"🆕 Prayer added: {request}")

@bot.command()
async def mark_answered(ctx, request_id: int, status: str):
    prayers = load_prayers()
    for p in prayers:
        if p["id"] == request_id:
            p["status"] = status
            save_prayers(prayers)
            await ctx.send(f"✅ Request #{request_id} marked as {status}.")
            return
    await ctx.send("❌ Request not found.")

@bot.command()
async def list_requests(ctx):
    prayers = load_prayers()
    if not prayers:
        await ctx.send("🙅 No prayer requests yet.")
        return
    msg = "\n".join([f"{p['id']}. {p['text']} - [{p['status']}]" for p in prayers])
    await ctx.send(msg)

@tasks.loop(hours=24)
async def daily_reminder():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🛐 Daily prayer reminder! Don’t forget to lift up your requests.")

bot.run(TOKEN)
