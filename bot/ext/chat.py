import re
import unicodedata

import discord
from bot import cmd, converter
from bot.utils import wrap_in_code
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
            await ctx.send(
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
        await ctx.send(
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
            await ctx.send(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Slow mode cannot be longer than 21600 seconds.",
                )
            )
            return
        if seconds < 0:
            await ctx.send(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Warping back in time is impossible.",
                )
            )
            return

        await ctx.channel.edit(slowmode_delay=seconds)

        if seconds > 0:
            second_plural = "second" if seconds == 1 else "seconds"
            await ctx.send(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Slow mode in this channel is now set to {seconds} {second_plural}.",
                )
            )
        else:
            await ctx.send(
                embed=discord.Embed(
                    title="Slowmode",
                    description=f"Slow mode in this channel is now disabled.",
                )
            )

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
                if member.bot:
                    continue

                normalized = unicodedata.normalize("NFKC", member.display_name)
                new_nick = ""
                for char in normalized:
                    if not new_nick and ord(char) < ord("0"):
                        continue
                    if unicodedata.combining(char) == 0:
                        new_nick += char

                if not new_nick:
                    new_nick = "dehoisted"

                if member.display_name != new_nick:
                    nicknames_changed += 1
                    await member.edit(nick=new_nick)

        plural_nickname = "nickname" if nicknames_changed == 1 else "nicknames"
        await ctx.send(
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
                if member.bot:
                    continue

                new_nick = ""
                for char in member.display_name:
                    if not new_nick and ord(char) < ord("0"):
                        continue
                    new_nick += char

                if not new_nick:
                    new_nick = "dehoisted"

                if member.display_name != new_nick:
                    nicknames_changed += 1
                    await member.edit(nick=new_nick)

        plural_nickname = "nickname" if nicknames_changed == 1 else "nicknames"
        await ctx.send(
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
                if member.bot:
                    continue

                normalized = unicodedata.normalize("NFKC", member.display_name)
                new_nick = ""
                for char in normalized:
                    if unicodedata.combining(char) == 0:
                        new_nick += char

                if not new_nick:
                    new_nick = "bad name"

                if member.display_name != new_nick:
                    nicknames_changed += 1
                    await member.edit(nick=new_nick)

        plural_nickname = "nickname" if nicknames_changed == 1 else "nicknames"
        await ctx.send(
            embed=discord.Embed(
                title="Nickname",
                description=f"Successfully normalized {nicknames_changed} {plural_nickname}.",
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
            author = message.author
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
            embed.set_footer(text=f"Sent in #{message.channel.name}")

            if len(linked_message.attachments) > 0:
                attachment = linked_message.attachments[0]
                if not attachment.height or attachment.is_spoiler():
                    embed.add_field(
                        name="File",
                        value=f"[{escape_markdown(attachment.filename)}]({attachment.url})",
                    )
                else:
                    embed.set_image(url=linked_message.attachments[0].url)

            await message.reply(embed=embed)

        if len(linked_messages) > 3:
            message_plural = "message" if len(linked_messages) == 4 else "messages"
            await message.reply(
                f"Aborted embedding {len(linked_messages) - 3} more {message_plural}."
            )


def setup(bot: commands.Bot):
    voice = Chat(bot)
    bot.add_cog(voice)
