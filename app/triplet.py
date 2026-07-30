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

bot = commands.Bot(command_prefix="ttt.", strip_after_prefix=True, intents=intents)

# Remove default built-in help command to prevent registration collision crash
bot.remove_command("help")


async def perform_verification(member: discord.Member) -> bool:
    """Helper function to assign Verified and remove Unverified role."""
    guild = member.guild
    verified_role = discord.utils.get(guild.roles, name="Verified")
    unverified_role = discord.utils.get(guild.roles, name="Unverified")

    try:
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        if verified_role and verified_role not in member.roles:
            await member.add_roles(verified_role)
        return True
    except discord.Forbidden:
        return False


async def setup_verification(guild: discord.Guild):
    """Configures Unverified & Verified roles and restricts Unverified users to ONLY see #verify."""
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

    for channel in guild.channels:
        if channel.name != "verify":
            try:
                await channel.set_permissions(
                    unverified_role,
                    view_channel=False,
                    reason="Hiding channels from Unverified role",
                )
            except discord.Forbidden:
                print(f"Lacking permissions to modify channel {channel.name}")

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
            read_message_history=True,  # Allows unverified role to read message history
            add_reactions=True,
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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to run this command.")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Please mention a member to verify. Usage: `ttt.verify @member`")
        return
    raise error


# =========================================================
# PREFIX COMMANDS (ttt.help, ttt.prefix, ttt.verify)
# =========================================================
@bot.command(name="help")
async def prefix_help(ctx):
    await ctx.send("https://discord.gg/2s8Um6Wgn3")


@bot.command(name="prefix")
async def prefix_prefix(ctx):
    await ctx.send("the prefix is ttt.")


@bot.command(name="verify")
@commands.has_permissions(manage_roles=True)
async def prefix_verify(ctx, member: discord.Member):
    """Prefix command to manually verify a user: ttt.verify @member"""
    success = await perform_verification(member)
    if success:
        await ctx.send(f"✅ Automatically verified {member.mention} and removed the Unverified role.")
    else:
        await ctx.send(f"❌ Failed to verify {member.mention}. Check bot permissions/role hierarchy.")


# =========================================================
# GENERAL SLASH COMMANDS (/help, /prefix, /verify)
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


@bot.tree.command(name="verify", description="Manually verify a member and remove Unverified role")
@app_commands.checks.has_permissions(manage_roles=True)
async def slash_verify(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    success = await perform_verification(member)
    if success:
        await interaction.followup.send(f"✅ Automatically verified {member.mention} and removed the Unverified role.")
    else:
        await interaction.followup.send(f"❌ Failed to verify {member.mention}. Check bot permissions/role hierarchy.")


@slash_verify.error
async def slash_verify_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Manage Roles** permissions to verify members.", ephemeral=True)


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
async def on_guild_channel_create(channel):
    """Automatically hide newly created channels from Unverified users."""
    unverified_role = discord.utils.get(channel.guild.roles, name="Unverified")
    if unverified_role and channel.name != "verify":
        try:
            await channel.set_permissions(
                unverified_role,
                view_channel=False,
                reason="Hiding new channel from Unverified role",
            )
        except discord.Forbidden:
            pass


@bot.event
async def on_raw_reaction_add(payload):
    # Ignore bot reactions
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "verify":
        return

    # Check if the reaction matches the defined verification emoji ID
    is_valid_emoji = False
    if payload.emoji.is_custom_emoji():
        if payload.emoji.id == EMOJI_ID:
            is_valid_emoji = True
    elif EMOJI_ID == 0:  # Fallback if using standard emojis
        is_valid_emoji = True

    # If user reacted with an unauthorized emoji, remove it
    if not is_valid_emoji:
        try:
            msg = await channel.fetch_message(payload.message_id)
            user = guild.get_member(payload.user_id)
            if user:
                await msg.remove_reaction(payload.emoji, user)
        except discord.Forbidden:
            pass
        return

    # User reacted with valid verification emoji -> Verify them
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    await perform_verification(member)


if __name__ == "__main__":
    bot.run(TOKEN)
