
import os
import discord
from discord.ext import commands

# ==============================
# MHN ARCADE V1
# Purple Gaming System 💜
# ==============================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("Slash commands synced successfully!")


@bot.event
async def on_ready():
    print("=" * 40)
    print("MHN ARCADE V1")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Status: ONLINE")
    print("=" * 40)


@bot.tree.command(
    name="ping",
    description="Check MHN ARCADE bot connection"
)
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"💜 MHN ARCADE V1 is online!\n"
        f"🏓 Ping: {latency} ms",
        ephemeral=True
    )


bot.run(TOKEN)
