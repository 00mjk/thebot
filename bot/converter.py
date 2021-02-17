import discord
from discord.ext import commands
from discord.utils import get

from bot import cmd


class MessageConverter(commands.MessageConverter):
    """Converts to a :class:`discord.Message`.

    Different from `discord.ext.commands.converter.MessageConverter` by not
    leaking messages from other guilds, or channels the member cannot read.
    """

    async def convert(self, ctx: cmd.Context, argument):
        message = await super().convert(ctx, argument)

        perms = message.channel.permissions_for(ctx.author)
        if (
            message.guild == ctx.guild
            and perms.read_messages
            and perms.read_message_history
        ):
            return message

        raise commands.ChannelNotReadable(message.channel)


class PartialEmojiConverter(commands.PartialEmojiConverter):
    """Converts to a :class:`~discord.PartialEmoji`.

    Different from `discord.ext.commands.converter.PartialEmojiConverter` by
    falling back to getting emoji by name from the guild.
    """

    async def convert(self, ctx: cmd.Context, argument):
        try:
            emoji_id = int(argument)

            async with ctx.bot.session as client:
                gif_url = str(
                    discord.Asset(ctx.bot._connection, f"/emojis/{emoji_id}.gif")
                )
                png_url = str(
                    discord.Asset(ctx.bot._connection, f"/emojis/{emoji_id}.png")
                )

                async with client.head(gif_url) as resp:
                    if resp.ok:
                        return discord.PartialEmoji.with_state(
                            ctx.bot._connection,
                            id=int(argument),
                            name="unknown",
                            animated=True,
                        )

                async with client.head(png_url) as resp:
                    if resp.ok:
                        return discord.PartialEmoji.with_state(
                            ctx.bot._connection,
                            id=int(argument),
                            name="unknown",
                            animated=False,
                        )

        except ValueError:
            pass

        try:
            return await super().convert(ctx, argument)
        except commands.PartialEmojiConversionFailure:
            if not ctx.guild:
                raise

            guild_emoji = get(ctx.guild.emojis, name=argument.strip(":"))
            if guild_emoji is None:
                guild_emoji = get(ctx.guild.emojis, id=argument)

            return await super().convert(ctx, str(guild_emoji or argument))
