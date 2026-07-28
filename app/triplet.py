import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

EMOJI_ID = int(os.getenv("EMOJI_ID", "0"))
IMAGE_URL = os.getenv("IMAGE_URL", "YOUR_IMAGE_URL_HERE")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="ttt.", intents=intents)


async def setup_verification(guild: discord.Guild):
    """Configures Unverified & Verified role permissions directly without touching existing channels."""
    existing_channel = discord.utils.get(guild.text_channels, name="verify")
    if existing_channel:
        try:
            await existing_channel.delete(reason="Re-setting up verify channel")
        except discord.Forbidden:
            pass

    verified_role = discord.utils.get(guild.roles, name="Verified")
    if not verified_role:
        verified_role = await guild.create_role(
            name="Verified",
            permissions=discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                add_reactions=True,
                use_external_emojis=True,
                attach_files=True,
                connect=True,
                speak=True,
            ),
            reason="Created for Triplet verification system",
        )

    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    if not unverified_role:
        unverified_role = await guild.create_role(
            name="Unverified",
            permissions=discord.Permissions(
                view_channel=False,
                send_messages=False,
            ),
            reason="Created for Triplet verification system",
        )
    else:
        try:
            await unverified_role.edit(
                permissions=discord.Permissions(view_channel=False, send_messages=False)
            )
        except discord.Forbidden:
            pass

    for member in guild.members:
        if not member.bot and verified_role not in member.roles:
            try:
                await member.add_roles(unverified_role)
            except discord.Forbidden as e:
                print(f"Failed to give Unverified role to {member}: {e}")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        unverified_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=False,
        ),
        verified_role: discord.PermissionOverwrite(view_channel=False),
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


async def teardown_verification(guild: discord.Guild):
    """Deletes #verify channel and cleans up Unverified / Verified roles."""
    verify_channel = discord.utils.get(guild.text_channels, name="verify")
    if verify_channel:
        try:
            await verify_channel.delete(reason="Verification disabled")
        except discord.Forbidden:
            pass

    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    if unverified_role:
        try:
            await unverified_role.delete()
        except discord.Forbidden:
            pass

    verified_role = discord.utils.get(guild.roles, name="Verified")
    if verified_role:
        try:
            await verified_role.delete()
        except discord.Forbidden:
            pass


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)


@bot.event
async def on_guild_join(guild):
    await setup_verification(guild)


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if bot.user in message.mentions and len(message.content.strip().split()) == 1:
        await message.channel.send("The prefix is ttt.")

    await bot.process_commands(message)


# =========================================================
# GENERAL SLASH COMMANDS (/help & /prefix)
# =========================================================
@bot.tree.command(name="help", description="get help and support server link")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message("https://discord.gg/2s8Um6Wgn3")


@bot.tree.command(name="prefix", description="check the bot prefix")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def slash_prefix(interaction: discord.Interaction):
    await interaction.response.send_message("the prefix is ttt.")


# =========================================================
# SLASH COMMAND GROUP: /verification enable | disable
# =========================================================
class VerificationGroup(app_commands.Group):
    pass

verification_group = VerificationGroup(name="verification", description="Manage server verification system")


@verification_group.command(name="enable", description="Enable verification and create #verify channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def enable_verification(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await setup_verification(interaction.guild)
    await interaction.followup.send("✅ Verification system enabled! `#verify` channel created.", ephemeral=True)


@verification_group.command(name="disable", description="Disable verification and remove created roles/channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def disable_verification(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await teardown_verification(interaction.guild)
    await interaction.followup.send("✅ Verification system disabled.", ephemeral=True)


@enable_verification.error
@disable_verification.error
async def verification_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Manage Server** or **Administrator** permissions to use this command.", ephemeral=True)


bot.tree.add_command(verification_group)


@bot.event
async def on_member_join(member):
    if not member.bot:
        unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
        if unverified_role:
            try:
                await member.add_roles(unverified_role)
            except discord.Forbidden as e:
                print(f"Could not give Unverified role to {member}: {e}")


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "verify":
        return

    if payload.emoji.id != EMOJI_ID:
        try:
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
        except discord.Forbidden:
            pass
        return

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
    except discord.Forbidden as e:
        print(f"Failed to switch roles for {member}: {e}")


if __name__ == "__main__":
    bot.run(TOKEN)
