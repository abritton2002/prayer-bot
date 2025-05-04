import discord
from discord.ext import tasks
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import json
from datetime import datetime
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread

# --- Keep Alive Web Server for Render ---
app = Flask('')

@app.route('/')
def home():
    return "PrayerBot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()

# --- Bot Setup ---
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

PRAYER_REQUESTS_CHANNEL_ID = 1367468653531889689
OPEN_REQUESTS_CHANNEL_ID = 1368636489079984150
PRAYER_SUMMARY_CHANNEL_ID = 1368636720429535287
PRAYER_FILE = "prayers.json"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- Helper functions ---
def load_prayers():
    try:
        with open(PRAYER_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_prayers(data):
    with open(PRAYER_FILE, "w") as f:
        json.dump(data, f, indent=2)

@tree.command(name="add_requests", description="Add one or more prayer requests (comma-separated)")
async def add_requests(interaction: discord.Interaction, requests: str):
    prayers = load_prayers()
    entries = [r.strip() for r in requests.split(",") if r.strip()]
    count = 0
    user_prayers = []

    for req in entries:
        prayer = {
            "id": len(prayers) + 1,
            "text": req,
            "status": "open",
            "added_by": {
                "id": interaction.user.id,
                "display_name": interaction.user.display_name,
                "tag": str(interaction.user)
            },
            "date": str(datetime.now().date())
        }
        prayers.append(prayer)
        user_prayers.append(prayer)
        count += 1

    save_prayers(prayers)
    await interaction.response.send_message(f"✅ Added {count} prayer request(s).")

    open_channel = client.get_channel(OPEN_REQUESTS_CHANNEL_ID)
    if open_channel:
        msg = f"🆕 **Prayer Requests from {interaction.user.display_name}:**\n\n"
        for p in user_prayers:
            msg += f"• {p['text']}\n"
        await open_channel.send(msg)

@tree.command(name="refresh_open_requests", description="Post all current open requests grouped by user")
async def refresh_open_requests(interaction: discord.Interaction):
    prayers = load_prayers()
    open_requests_by_user = {}

    for p in prayers:
        if p["status"] == "open":
            user = p["added_by"]["display_name"]
            if user not in open_requests_by_user:
                open_requests_by_user[user] = []
            open_requests_by_user[user].append(p["text"])

    if not open_requests_by_user:
        await interaction.response.send_message("✅ No open prayer requests to refresh.")
        return

    msg = "**🗂️ Current Open Prayer Requests (Grouped by Name):**\n\n"
    for name, requests in open_requests_by_user.items():
        msg += f"**{name}**\n"
        for r in requests:
            msg += f"• {r}\n"
        msg += "\n"

    channel = client.get_channel(OPEN_REQUESTS_CHANNEL_ID)
    if channel:
        await channel.send(msg[:2000])

    await interaction.response.send_message("🔄 Open requests refreshed in #requests-update.")

class PrayerDropdown(discord.ui.Select):
    def __init__(self, user_id, request):
        self.user_id = user_id
        self.request = request
        options = [
            discord.SelectOption(label="Yes 🙌", value="yes"),
            discord.SelectOption(label="No ❌", value="no"),
            discord.SelectOption(label="Kinda 🤷", value="kinda"),
        ]
        display_text = (request['text'][:97] + '...') if len(request['text']) > 100 else request['text']
        super().__init__(placeholder=f"{display_text}", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ You can only update your own requests.", ephemeral=True)
            return

        prayers = load_prayers()
        for p in prayers:
            if p["id"] == self.request["id"]:
                p["status"] = self.values[0]
                save_prayers(prayers)

                update_channel = client.get_channel(OPEN_REQUESTS_CHANNEL_ID)
                if update_channel:
                    await update_channel.send(
                        f"✅ **Request #{p['id']}** updated to '{self.values[0]}' by {interaction.user.display_name}"
                    )

                await interaction.response.send_message(
                    f"✅ Updated: '{p['text']}' marked as '{self.values[0]}'", ephemeral=True)
                return

class PrayerDropdownView(discord.ui.View):
    def __init__(self, user_id, user_requests):
        super().__init__(timeout=None)
        for r in user_requests:
            self.add_item(PrayerDropdown(user_id, r))

async def send_daily_prayer_summary():
    prayers = load_prayers()
    open_prayers = [p for p in prayers if p["status"] == "open"]

    if not open_prayers:
        channel = client.get_channel(PRAYER_SUMMARY_CHANNEL_ID)
        if channel:
            await channel.send("🙌 No open prayer requests this morning.")
        return

    prayers_by_user = {}
    for p in open_prayers:
        uid = p["added_by"]["id"]
        prayers_by_user.setdefault(uid, []).append(p)

    summary_channel = client.get_channel(PRAYER_SUMMARY_CHANNEL_ID)
    if not summary_channel:
        print("❌ Summary channel not found.")
        return

    for user_id, requests in prayers_by_user.items():
        user = await client.fetch_user(user_id)
        view = PrayerDropdownView(user_id, requests)

        block = f"**{user.display_name}**\n"
        for req in requests:
            block += f"• {req['text']}\n"

        await summary_channel.send(block, view=view)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot ready as {client.user}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_prayer_summary, CronTrigger(hour=7, minute=0))
    scheduler.start()
    print("📅 Daily interactive summary scheduled at 7:00 AM.")

client.run(TOKEN)
