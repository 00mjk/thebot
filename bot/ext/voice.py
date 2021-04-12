import itertools
import typing

import discord
from bot import cmd, menus
from bot.utils import patch_overwrites, wrap_in_code
from discord.ext import commands
from discord.utils import get


class Voice(cmd.Cog):
    """Voice chat helpers"""

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @commands.has_permissions(manage_roles=True)
    async def voicelinks(self, ctx: cmd.Context):
        """Lists existing links between voice and text channels"""

        links = await self.bot.pool.fetch(
            """
            SELECT text_channel_id, voice_channel_id FROM voice_link
            WHERE guild_id = $1
            ORDER BY voice_channel_id
            """,
            ctx.guild.id,
        )

        grouped_links = itertools.groupby(
            links, key=lambda link: link["voice_channel_id"]
        )

        paginator = menus.FieldPaginator(
            self.bot, base_embed=discord.Embed(title="Voice links")
        )

        for voice_channel_id, links in grouped_links:
            voice_channel = get(ctx.guild.channels, id=voice_channel_id)

            paginator.add_field(
                name=str(voice_channel),
                value="\n".join(f"<#{link['text_channel_id']}>" for link in links),
            )

        await paginator.send(ctx)

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @commands.has_permissions(manage_roles=True)
    async def voicelink(
        self,
        ctx: cmd.Context,
        text_channel: discord.TextChannel,
        *,
        voice_channel: discord.VoiceChannel,
    ):
        """Creates a new link between a voice and a text channel"""

        await self.bot.pool.execute(
            """
            INSERT INTO voice_link (guild_id, text_channel_id, voice_channel_id) VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            ctx.guild.id,
            text_channel.id,
            voice_channel.id,
        )

        text_perms = text_channel.permissions_for(ctx.guild.me)
        if not text_perms.view_channel or not text_perms.manage_roles:
            await ctx.reply(
                embed=discord.Embed(
                    title="Missing permissions",
                    description=f"I cannot manage roles in {text_channel.mention}.",
                )
            )
            return

        await patch_overwrites(
            text_channel,
            ctx.guild.me,
            read_messages=True,
        )
        await patch_overwrites(
            text_channel,
            ctx.guild.default_role,
            read_messages=False,
        )

        await ctx.reply(
            embed=discord.Embed(
                title="Voice link created",
                description=f"Members who connect to {wrap_in_code(voice_channel.name)} will now get access to {text_channel.mention}.",
            )
        )

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @commands.has_permissions(manage_roles=True)
    async def voiceunlink(
        self,
        ctx: cmd.Context,
        *,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel],
    ):
        """Removes all link for a voice or text channel"""

        await self.bot.pool.execute(
            """
            DELETE FROM voice_link
            WHERE text_channel_id = $1 OR voice_channel_id = $1
            """,
            channel.id,
        )

        message = f"{channel.mention} is no longer associated with any voice channels."
        if isinstance(channel, discord.VoiceChannel):
            message = f"Members who connect to {wrap_in_code(channel.name)} will no longer get access to extra channels."

        await ctx.reply(
            embed=discord.Embed(title="Voice link deleted", description=message)
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        if before.channel == after.channel:
            return

        before_text_channel_ids = await self.bot.pool.fetch(
            """
            SELECT text_channel_id FROM voice_link
            WHERE voice_channel_id = $1
            """,
            before.channel.id if before.channel else 0,
        )
        before_text_channels = {
            get(member.guild.channels, id=channel_id)
            for (channel_id,) in before_text_channel_ids
        }

        after_text_channel_ids = await self.bot.pool.fetch(
            """
            SELECT text_channel_id FROM voice_link
            WHERE voice_channel_id = $1
            """,
            after.channel.id if after.channel else 0,
        )
        after_text_channels = {
            get(member.guild.channels, id=channel_id)
            for (channel_id,) in after_text_channel_ids
        }

        for channel in before_text_channels - after_text_channels:
            await patch_overwrites(channel, member, read_messages=None)

        for channel in after_text_channels - before_text_channels:
            await patch_overwrites(channel, member, read_messages=True)


def setup(bot: commands.Bot):
    voice = Voice(bot)
    bot.add_cog(voice)
