import re
import unicodedata

import cachetools
import discord
from bot import cmd, converter
from bot.utils import wrap_in_code
from discord import gateway
from discord.ext import commands
from discord.utils import escape_markdown, get


class Chat(cmd.Cog):
    """Chat related commands"""

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_messages=True)
    async def embedmessage(self, ctx: cmd.Context, enable: bool = None):
        """Toggles whether or not I should embed message links"""

        if enable is None:
            enabled = await ctx.bot.pool.fetchval(
                """
                SELECT embed_messages FROM guild_config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            enabled_str = "will" if enabled else "will not"
            await ctx.reply(
                embed=discord.Embed(
                    title="Embed messages",
                    description=f"Message links sent in chat {enabled_str} embed.",
                )
            )
            return

        await ctx.bot.pool.execute(
            """
            UPDATE guild_config
            SET embed_messages = $1
            WHERE guild_id = $2
            """,
            enable,
            ctx.guild.id,
        )

        enabled_str = "will now" if enable else "will no longer"
        await ctx.reply(
            embed=discord.Embed(
                title="Embed messages",
                description=f"Message links sent in chat {enabled_str} embed.",
            )
        )

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: cmd.Context, seconds: int):
        """Edits slowmode to a precise number of seconds"""

        if seconds > 21600:
            await ctx.reply(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Slow mode cannot be longer than 21600 seconds.",
                )
            )
            return
        if seconds < 0:
            await ctx.reply(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Warping back in time is impossible.",
                )
            )
            return

        await ctx.channel.edit(slowmode_delay=seconds)

        if seconds > 0:
            second_plural = "second" if seconds == 1 else "seconds"
            await ctx.reply(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Slow mode in this channel is now set to {seconds} {second_plural}.",
                )
            )
        else:
            await ctx.reply(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Slow mode in this channel is now disabled.",
                )
            )

    def clean_display_name(
        self, text: str, *, normalize: bool = True, dehoist: bool = True
    ):
        if normalize:
            text = unicodedata.normalize("NFKC", text)

        ret = ""

        for char in text:
            if dehoist and not ret and ord(char) < ord("0"):
                continue

            if not normalize or unicodedata.combining(char) == 0:
                ret += char

        return ret

    @commands.group(invoke_without_command=True)
    @commands.cooldown(3, 8, commands.BucketType.channel)
    async def nick(self, ctx: cmd.Context):
        """Commands used to clean up member nicknames"""

        await ctx.send_help("nick")

    @nick.command(name="clean")
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_nicknames=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    async def nick_clean(self, ctx: cmd.Context):
        """Cleans up nicknames for members in the server"""

        nicknames_changed = 0

        async with ctx.typing():
            async for member in ctx.guild.fetch_members(limit=None):
                if (
                    member.bot
                    or member == ctx.guild.owner
                    or member.top_role >= ctx.guild.me.top_role
                ):
                    continue

                new_nick = self.clean_display_name(member.display_name)
                if member.display_name != new_nick:
                    nicknames_changed += 1
                    await member.edit(nick=new_nick or "{cleaned}")

        plural_nickname = "nickname" if nicknames_changed == 1 else "nicknames"
        await ctx.reply(
            embed=discord.Embed(
                title="Nickname",
                description=f"Successfully cleaned up {nicknames_changed} {plural_nickname}.",
            )
        )

    @nick.command(name="dehoist")
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_nicknames=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    async def nick_dehoist(self, ctx: cmd.Context):
        """Dehoists nicknames for members in the server"""

        nicknames_changed = 0

        async with ctx.typing():
            async for member in ctx.guild.fetch_members(limit=None):
                if (
                    member.bot
                    or member == ctx.guild.owner
                    or member.top_role >= ctx.guild.me.top_role
                ):
                    continue

                new_nick = self.clean_display_name(member.display_name, normalize=False)
                if member.display_name != new_nick:
                    nicknames_changed += 1
                    await member.edit(nick=new_nick or "{cleaned}")

        plural_nickname = "nickname" if nicknames_changed == 1 else "nicknames"
        await ctx.reply(
            embed=discord.Embed(
                title="Nickname",
                description=f"Successfully dehoisted {nicknames_changed} {plural_nickname}.",
            )
        )

    @nick.command(name="normalize", aliases=["normalise"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_nicknames=True)
    @commands.bot_has_guild_permissions(manage_nicknames=True)
    async def nick_normalize(self, ctx: cmd.Context):
        """Normalize nicknames for members in the server"""

        nicknames_changed = 0

        async with ctx.typing():
            async for member in ctx.guild.fetch_members(limit=None):
                if (
                    member.bot
                    or member == ctx.guild.owner
                    or member.top_role >= ctx.guild.me.top_role
                ):
                    continue

                new_nick = self.clean_display_name(member.display_name, dehoist=False)
                if member.display_name != new_nick:
                    nicknames_changed += 1
                    await member.edit(nick=new_nick or "{cleaned}")

        plural_nickname = "nickname" if nicknames_changed == 1 else "nicknames"
        await ctx.reply(
            embed=discord.Embed(
                title="Nickname",
                description=f"Successfully normalized {nicknames_changed} {plural_nickname}.",
            )
        )

    @nick.command(name="autodehoist")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_messages=True)
    async def nick_autodehoist(self, ctx: cmd.Context, enable: bool = None):
        """Toggles whether or not I should embed message links"""

        if enable is None:
            enabled = await ctx.bot.pool.fetchval(
                """
                SELECT auto_clean_dehoist FROM guild_config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            enabled_str = "are" if enabled else "are not"
            await ctx.reply(
                embed=discord.Embed(
                    title="Auto dehoist",
                    description=f"Nicknames {enabled_str} dehoisted automatically.",
                )
            )
            return

        await ctx.bot.pool.execute(
            """
            UPDATE guild_config
            SET auto_clean_dehoist = $1
            WHERE guild_id = $2
            """,
            enable,
            ctx.guild.id,
        )

        try:
            _, normalize = self.auto_clean_cache[ctx.guild.id]
            self.auto_clean_cache[ctx.guild.id] = enable, normalize
        except KeyError:
            pass

        enabled_str = "will now" if enable else "will no longer"
        await ctx.reply(
            embed=discord.Embed(
                title="Auto dehoist",
                description=f"Nicknames {enabled_str} be dehoisted automatically.",
            )
        )

    @nick.command(name="autonormalize", aliases=["autonormalise"])
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_messages=True)
    async def nick_autonormalize(self, ctx: cmd.Context, enable: bool = None):
        """Toggles whether or not I should embed message links"""

        if enable is None:
            enabled = await ctx.bot.pool.fetchval(
                """
                SELECT auto_clean_normalize FROM guild_config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            enabled_str = "are" if enabled else "are not"
            await ctx.reply(
                embed=discord.Embed(
                    title="Auto normalize",
                    description=f"Nicknames {enabled_str} normalized automatically.",
                )
            )
            return

        await ctx.bot.pool.execute(
            """
            UPDATE guild_config
            SET auto_clean_normalize = $1
            WHERE guild_id = $2
            """,
            enable,
            ctx.guild.id,
        )

        try:
            dehoist, _ = self.auto_clean_cache[ctx.guild.id]
            self.auto_clean_cache[ctx.guild.id] = dehoist, enable
        except KeyError:
            pass

        enabled_str = "will now" if enable else "will no longer"
        await ctx.reply(
            embed=discord.Embed(
                title="Auto normalize",
                description=f"Nicknames {enabled_str} be normalized automatically.",
            )
        )

    message_link_re = re.compile(
        r"https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/\d+/\d+/\d+"
    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        conv = converter.MessageConverter()
        ctx = await self.bot.get_context(message, cls=cmd.Context)
        linked_messages = []
        for word in message.content.split():
            if self.message_link_re.fullmatch(word):
                try:
                    linked_messages.append(await conv.convert(ctx, word))
                except:
                    pass
        if len(linked_messages) == 0:
            return

        embed_messages = await self.bot.pool.fetchval(
            """
            SELECT embed_messages FROM guild_config
            WHERE guild_id = $1
            """,
            message.guild.id,
        )

        if not embed_messages:
            return

        for linked_message in linked_messages[:3]:
            author = linked_message.author
            try:
                author = await message.guild.fetch_member(linked_message.author.id)
            except discord.NotFound:
                pass

            embed = discord.Embed(
                description=linked_message.content,
                timestamp=linked_message.created_at,
                colour=author.colour.value or discord.Embed.Empty,
            )
            embed.set_author(name=str(author), icon_url=str(author.avatar_url))
            embed.set_footer(text=f"Sent in #{linked_message.channel.name}")

            if len(linked_message.attachments) > 0:
                attachment = linked_message.attachments[0]
                if not attachment.height or attachment.is_spoiler():
                    embed.add_field(
                        name="File",
                        value=f"[{escape_markdown(attachment.filename)}]({attachment.url})",
                    )
                else:
                    embed.set_image(url=linked_message.attachments[0].url)

            await message.reply(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if len(linked_messages) > 3:
            message_plural = "message" if len(linked_messages) == 4 else "messages"
            await message.reply(
                f"Aborted embedding {len(linked_messages) - 3} more {message_plural}.",
                allowed_mentions=discord.AllowedMentions.none(),
            )

    auto_clean_cache = cachetools.TTLCache(maxsize=float("inf"), ttl=900)

    async def get_auto_clean_status(self, guild: discord.Guild):
        try:
            return self.auto_clean_cache[guild.id]
        except KeyError:
            row = await self.bot.pool.fetchrow(
                """
                SELECT auto_clean_dehoist, auto_clean_normalize FROM guild_config
                WHERE guild_id = $1
                """,
                guild.id,
            )
            if not row:
                return False, False

            dehoist = row["auto_clean_dehoist"]
            normalize = row["auto_clean_normalize"]
            self.auto_clean_cache[guild.id] = dehoist, normalize

            return await self.get_auto_clean_status(guild)

    cleaned_usernames_cache = cachetools.TTLCache(maxsize=float("inf"), ttl=900)

    async def get_cleaned_usernames(self, guild: discord.Guild):
        try:
            return self.cleaned_usernames_cache[guild.id]
        except KeyError:
            nicks = await self.bot.pool.fetch(
                """
                SELECT member_id, nick FROM cleaned_username
                WHERE guild_id = $1
                """,
                guild.id,
            )
            self.cleaned_usernames_cache[guild.id] = {
                row["member_id"]: row["nick"] for row in nicks
            }
            return await self.get_cleaned_usernames(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or not member.guild.me.guild_permissions.manage_nicknames:
            return

        dehoist, normalize = await self.get_auto_clean_status(member.guild)
        if not dehoist and not normalize:
            return

        # OAuth2 apps can add members with a nick
        mark_as_managed = not member.nick

        new_nick = self.clean_display_name(
            member.display_name, normalize=normalize, dehoist=dehoist
        )
        if not new_nick:
            new_nick = "{cleaned}"
        if member.display_name != new_nick:
            await member.edit(nick=new_nick)

            if mark_as_managed:
                nicks = await self.get_cleaned_usernames(member.guild)
                nicks[member.id] = new_nick
                await self.bot.pool.execute(
                    """
                    INSERT INTO cleaned_username (guild_id, member_id, nick)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    member.guild.id,
                    member.id,
                    new_nick,
                )

    @commands.Cog.listener()
    async def on_socket_response(self, event: dict):
        if event["op"] != gateway.DiscordWebSocket.DISPATCH:
            return

        data = event["d"]

        if event["t"] == "GUILD_MEMBER_UPDATE":
            guild = self.bot.get_guild(int(data["guild_id"]))
            user_id = int(data["user"]["id"])

            if guild.owner_id == user_id or data["user"].get("bot", False):
                return
            if not guild.me.guild_permissions.manage_nicknames:
                return

            target_top_role = max(
                (guild.get_role(int(role_id)) for role_id in data["roles"]),
                default=guild.default_role,
            )
            if target_top_role >= guild.me.top_role:
                return

            dehoist, normalize = await self.get_auto_clean_status(guild)
            if not dehoist and not normalize:
                return

            nicks = await self.get_cleaned_usernames(guild)
            member = await guild.fetch_member(user_id)

            display_name = (
                member.name
                if member.nick == nicks.get(member.id)
                else member.display_name
            )
            is_username = member.name == display_name

            new_nick = self.clean_display_name(
                display_name, normalize=normalize, dehoist=dehoist
            )
            if not new_nick:
                new_nick = "{cleaned}"

            if not is_username or new_nick == display_name and user_id in nicks:
                nicks.pop(user_id, None)
                await self.bot.pool.execute(
                    """
                    DELETE FROM cleaned_username
                    WHERE guild_id = $1 AND member_id = $2
                    """,
                    guild.id,
                    user_id,
                )
            elif is_username and nicks.get(user_id) != new_nick:
                nicks[user_id] = new_nick
                await self.bot.pool.execute(
                    """
                    INSERT INTO cleaned_username (guild_id, member_id, nick)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, member_id) DO UPDATE
                    SET nick = $3
                    """,
                    guild.id,
                    user_id,
                    new_nick,
                )

            if new_nick != member.display_name:
                await member.edit(nick=new_nick)

        if event["t"] == "GUILD_MEMBER_REMOVE":
            guild = self.bot.get_guild(int(data["guild_id"]))
            user_id = int(data["user"]["id"])

            nicks = await self.get_cleaned_usernames(guild)

            if user_id in nicks:
                nicks.pop(user_id, None)
                await self.bot.pool.execute(
                    """
                    DELETE FROM cleaned_username
                    WHERE guild_id = $1 AND member_id = $2
                    """,
                    guild.id,
                    user_id,
                )


def setup(bot: commands.Bot):
    voice = Chat(bot)
    bot.add_cog(voice)
