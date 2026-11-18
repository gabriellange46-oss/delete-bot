import os
import re
from difflib import SequenceMatcher
import discord
from discord.ext import commands
from aiohttp import web

# --- Dummy Web Server for Render Free Tier ---
async def health_check(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- Fuzzy Matching Logic ---
def is_fuzzy_match(message_text: str, target_word: str) -> bool:
    """
    Checks every word in a message against target_word:
    1. Length must be within +/- 2 letters of target_word.
    2. At least 50% of the letters must match in order (similarity >= 0.5).
    """
    words_in_msg = re.findall(r"[a-zA-Z0-9]+", message_text.lower())
    target_len = len(target_word)

    for w in words_in_msg:
        # Rule 1: Within 2 letters longer or shorter
        if abs(len(w) - target_len) > 2:
            continue

        # Rule 2: At least half (50%) of the letters match
        similarity = SequenceMatcher(None, w, target_word).ratio()
        if similarity >= 0.50:
            return True

    return False

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    bot.loop.create_task(start_web_server())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="purgeword")
@commands.has_permissions(manage_messages=True)
async def purge_word(ctx, *, target_word: str):
    """Silently deletes messages containing target_word or close misspellings."""
    word = target_word.strip().lower()
    if not word:
        await ctx.message.delete()
        return

    # Delete your command immediately so nobody sees it
    await ctx.message.delete()

    for channel in ctx.guild.text_channels:
        if not channel.permissions_for(ctx.guild.me).read_message_history:
            continue
        if not channel.permissions_for(ctx.guild.me).manage_messages:
            continue

        try:
            async for msg in channel.history(limit=None):
                if is_fuzzy_match(msg.content, word):
                    await msg.delete()
        except (discord.Forbidden, discord.HTTPException):
            continue

@purge_word.error
async def purge_word_error(ctx, error):
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
