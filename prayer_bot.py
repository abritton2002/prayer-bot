import discord
from discord.ext import tasks
from discord import app_commands
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = 1367468653531889689  # Replace with your Discord channel ID (an integer)
PRAYER_FILE = "prayers.json"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_prayers():
    try:
        with open(PRAYER_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_prayers(data):
    with open(PRAYER_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot ready as {client.user}")
    daily_reminder.start()

@tree.command(name="add_requests", description="Add multiple prayer requests (separate with commas)")
async def add_requests(interaction: discord.Interaction, requests: str):
    prayers = load_prayers()
    new_requests = [r.strip() for r in requests.split(",") if r.strip()]
    count = 0
    for req in new_requests:
        prayers.append({
            "id": len(prayers)+1,
            "text": req,
            "status": "open",
            "added_by": {
                "id": interaction.user.id,
                "display_name": interaction.user.display_name,
                "tag": str(interaction.user)
            },
            "date": str(datetime.now().date())
        })
        count += 1
    save_prayers(prayers)
    await interaction.response.send_message(f"✅ Added {count} prayer request(s).")


@tree.command(name="mark_answered", description="Mark a request as answered")
async def mark_answered(interaction: discord.Interaction, request_id: int, status: str):
    prayers = load_prayers()
    for p in prayers:
        if p["id"] == request_id:
            p["status"] = status
            save_prayers(prayers)
            await interaction.response.send_message(f"✅ Request #{request_id} marked as {status}.")
            return
    await interaction.response.send_message("❌ Request not found.")

@tree.command(name="list_requests", description="List all prayer requests")
async def list_requests(interaction: discord.Interaction):
    prayers = load_prayers()
    if not prayers:
        await interaction.response.send_message("🙅 No prayer requests yet.")
        return
    msg = "\n".join([
        f"{p['id']}. {p['text']} - [{p['status']}] (added by {p['added_by']['display_name']})"
        for p in prayers
    ])
    await interaction.response.send_message(msg)

@tasks.loop(hours=24)
async def daily_reminder():
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🛐 Daily prayer reminder! Don’t forget to lift up your requests.")

client.run(TOKEN)
