import typing

import discord
from bot import cmd
from bot.utils import get_command_signature, wrap_in_code
from discord.ext import commands


class Meta(cmd.Cog):
    """Commands related to the bot itself"""

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    async def prefix(
        self,
        ctx: cmd.Context,
        *,
        new_prefix: typing.Optional[str],
    ):
        """Manages server prefix for the bot"""

        if new_prefix:
            await commands.has_guild_permissions(manage_guild=True).predicate(ctx)

            await self.bot.pool.execute(
                """
                UPDATE guild_config
                SET prefix = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                new_prefix,
            )

            await ctx.send(
                embed=discord.Embed(
                    title="Prefix",
                    description=f"Prefix has been set to {wrap_in_code(new_prefix)}.",
                )
            )
            return

        prefix = await self.bot.pool.fetchval(
            """
            SELECT prefix FROM guild_config
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        embed = discord.Embed(
            title="Prefix",
            description=f"The current server prefix is {wrap_in_code(prefix)}."
            f"\nUse {get_command_signature(ctx, self.prefix)} to set it.",
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["invite"])
    @commands.cooldown(3, 8, commands.BucketType.channel)
    async def about(self, ctx: cmd.Context):
        """Gives information about this bot"""

        app_info = await self.bot.application_info()

        embed = discord.Embed(title="About", description=self.bot.description)
        embed.add_field(
            name="Invite Link",
            value=f"https://discord.com/api/oauth2/authorize?client_id={app_info.id}&permissions=51200&scope=bot",
            inline=False,
        )
        embed.add_field(
            name="Bot Owner",
            value=f"[{app_info.owner}](https://discord.com/users/{app_info.owner.id})",
            inline=False,
        )

        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    meta = Meta(bot)
    bot.add_cog(meta)
