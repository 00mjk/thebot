import re

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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        conv = converter.MessageConverter()
        ctx = await self.bot.get_context(message, cls=cmd.Context)
        linked_messages = []
        for word in message.content.split():
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
            embed = discord.Embed(
                description=linked_message.content,
                timestamp=linked_message.created_at,
                colour=linked_message.author.colour.value or None,
            )
            embed.set_author(
                name=str(linked_message.author),
                icon_url=str(linked_message.author.avatar_url),
            )
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
