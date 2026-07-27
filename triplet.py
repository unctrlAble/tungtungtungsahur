import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Target custom emoji ID and optional custom banner image URL
EMOJI_ID = 0 # Upload your emoji
IMAGE_URL = "https://italian-brainrot.org/images/characters/tung-tung-tung-sahur.webp"  # Replace with direct image URL if desired

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} commands")
    except Exception as e:
        print(e)


@bot.event
async def on_guild_join(guild):
    # 1. Clean up any leftover #verify channel if re-invited
    existing_channel = discord.utils.get(guild.text_channels, name="verify")
    if existing_channel:
        try:
            await existing_channel.delete(reason="Cleaning up old verify channel")
        except discord.Forbidden:
            pass

    # 2. Setup roles
    verified_role = discord.utils.get(guild.roles, name="Verified") or await guild.create_role(
        name="Verified", permissions=discord.Permissions(mention_everyone=True)
    )
    unverified_role = discord.utils.get(guild.roles, name="Unverified") or await guild.create_role(
        name="Unverified"
    )

    # Assign Unverified role to existing non-bot members without Verified
    for member in guild.members:
        if not member.bot and verified_role not in member.roles:
            try:
                await member.add_roles(unverified_role)
            except discord.Forbidden:
                pass

    # 3. Lock pre-existing channels so unverified members cannot see them
    for ch in guild.channels:
        try:
            await ch.set_permissions(guild.default_role, view_channel=False)
            await ch.set_permissions(verified_role, view_channel=True)
        except discord.Forbidden:
            pass

    # 4. Create the #verify channel
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=False,  # Prevents users from adding new/different emojis
        ),
        verified_role: discord.PermissionOverwrite(
            view_channel=False  # Hides #verify once they get verified
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, add_reactions=True
        ),
    }

    channel = await guild.create_text_channel("verify", overwrites=overwrites)

    embed = discord.Embed(title="React to verified", color=discord.Color.gold())
    if IMAGE_URL and IMAGE_URL != "YOUR_IMAGE_URL_HERE":
        embed.set_image(url=IMAGE_URL)

    msg = await channel.send(embed=embed)

    try:
        await msg.add_reaction(f"<:tung_tung_sahur:{EMOJI_ID}>")
    except discord.HTTPException:
        await msg.add_reaction(discord.PartialEmoji(name="tung_tung_sahur", id=EMOJI_ID))


@bot.event
async def on_member_join(member):
    if not member.bot:
        unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
        if unverified_role:
            try:
                await member.add_roles(unverified_role)
            except discord.Forbidden:
                pass


@bot.event
async def on_raw_reaction_add(payload):
    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "verify":
        return

    # Automatically remove any reaction that isn't the verification emoji
    if payload.emoji.id != EMOJI_ID:
        try:
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
        except discord.Forbidden:
            pass
        return

    # Process role assignment for valid reaction
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    verified_role = discord.utils.get(guild.roles, name="Verified")
    unverified_role = discord.utils.get(guild.roles, name="Unverified")

    try:
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        if verified_role:
            await member.add_roles(verified_role)
    except discord.Forbidden:
        pass


if __name__ == "__main__":
    bot.run(TOKEN)
