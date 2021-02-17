import discord
from bot import cmd
from bot.utils import get_command_signature, wrap_in_code
from discord.ext import commands
from discord.utils import get

# format: written, nominative, accusative, pronominal possessive, predicative possessive, reflexive
pronoun_list = [
    ("any pronoun", "*any*", "*any*", "*any*", "*any*", "*any*"),
    ("no pronouns", "[name]", "[name]", "[name]'s", "[name]'s", "[name]"),
    ("they/them", "they", "them", "their", "theirs", "themselves"),
    ("she/her", "she", "her", "her", "hers", "herself"),
    ("he/him", "he", "him", "his", "his", "himself"),
    ("e/em", "e", "em", "eir", "eirs", "emself"),
    ("ey/em", "ey", "em", "eir", "eirs", "emself"),
    ("fae/faer", "fae", "faer", "faer", "faers", "faerself"),
    ("it/its", "it", "it", "its", "its", "itself"),
    ("ne/nem", "ne", "nem", "nir", "nirs", "nemself"),
    ("ne/ner", "ne", "ner", "nis", "nis", "nemself"),
    ("one/one", "one", "one", "ones", "one's", "oneself"),
    ("per/per", "per", "per", "per", "pers", "perself"),
    ("sie/hir", "sie", "hir", "hir", "hirs", "hirself"),
    ("thon/thon", "thon", "thon", "thons", "thon's", "thonself"),
    ("ve/ver", "ve", "ver", "vis", "vis", "verself"),
    ("xe/hir", "xe", "hir", "hir", "hirs", "hirself"),
    ("xe/xir", "xe", "xir", "xir", "xirs", "xirself"),
    ("xe/xyr", "xe", "xyr", "xyr", "xyrs", "xyrself"),
    ("xe/xem", "xe", "xem", "xyr", "xyrs", "xemself"),
    ("ze/hir", "ze", "hir", "hir", "hirs", "hirself"),
    ("zie/zir", "zie", "zir", "zir", "zirs", "zirself"),
    ("zie/zim", "zie", "zim", "zir", "zirs", "zirself"),
]


def pronouns_enabled():
    async def extended_check(ctx):
        await commands.guild_only().predicate(ctx)

        enabled = await ctx.bot.pool.fetchval(
            """
            SELECT selfrole_pronoun FROM guild_config
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not enabled:
            raise commands.DisabledCommand()

        return True

    return commands.check(extended_check)


class Roles(cmd.Cog):
    """Role related commands"""

    @commands.group(invoke_without_command=True)
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_roles=True)
    async def selfrole(self, ctx: cmd.Context):
        """Manages selfroles setup for this server"""

        await ctx.send_help("selfrole")

    @selfrole.command(name="add")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_roles=True)
    async def selfrole_add(self, ctx: cmd.Context, *, role: discord.Role):
        """Adds a role to the list of self-assignable roles"""

        in_db = await ctx.bot.pool.fetchval(
            """
            SELECT $1 = ANY(selfrole) FROM guild_config
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id,
        )

        if in_db:
            await ctx.send(
                embed=discord.Embed(
                    title="Selfroles",
                    description=f"{role.mention} already was self-assignable.",
                )
            )
            return

        await ctx.bot.pool.execute(
            """
            UPDATE guild_config
            SET selfrole = array_append(selfrole, $1)
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id,
        )
        await ctx.send(
            embed=discord.Embed(
                title="Selfroles",
                description=f"{role.mention} is now self-assignable.",
            )
        )

    @selfrole.command(name="remove")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_roles=True)
    async def selfrole_remove(self, ctx: cmd.Context, *, role: discord.Role):
        """Removes a role to the list of self-assignable roles"""

        in_db = await ctx.bot.pool.fetchval(
            """
            SELECT $1 = ANY(selfrole) FROM guild_config
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id,
        )

        if not in_db:
            await ctx.send(
                embed=discord.Embed(
                    title="Selfroles",
                    description=f"{role.mention} already was not self-assignable.",
                )
            )
            return

        await ctx.bot.pool.execute(
            """
            UPDATE guild_config
            SET selfrole = array_remove(selfrole, $1)
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id,
        )
        await ctx.send(
            embed=discord.Embed(
                title="Selfroles",
                description=f"{role.mention} is now no longer self-assignable.",
            )
        )

    @selfrole.command(name="pronoun")
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_roles=True)
    async def selfrole_pronoun(self, ctx: cmd.Context, enable: bool = None):
        """Gets or sets if pronoun selfroles are enabled"""

        if enable is None:
            enabled = await ctx.bot.pool.fetchval(
                """
                SELECT selfrole_pronoun FROM guild_config
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            enabled_str = "enabled" if enabled else "disabled"
            await ctx.send(
                embed=discord.Embed(
                    title="Pronoun selfrole",
                    description=f"Self assignable pronoun roles are currently {enabled_str}."
                    f"\nUse {get_command_signature(ctx, self.selfrole_pronoun)} to change this.",
                )
            )
            return

        await ctx.bot.pool.execute(
            """
            UPDATE guild_config
            SET selfrole_pronoun = $1
            WHERE guild_id = $2
            """,
            enable,
            ctx.guild.id,
        )

        enabled_str = "enabled" if enable else "disabled"
        await ctx.send(
            embed=discord.Embed(
                title="Pronoun selfrole",
                description=f"Self assignable pronoun roles are now {enabled_str}.",
            )
        )

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @commands.has_guild_permissions(manage_roles=True)
    async def selfroles(self, ctx: cmd.Context):
        """Lists all self-assignable roles"""

        role_ids = await ctx.bot.pool.fetchval(
            """
            SELECT selfrole FROM guild_config
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        role_ids_in_db = len(role_ids)

        role_ids = {rid for rid in role_ids if ctx.guild.get_role(rid)}

        if len(role_ids) != role_ids_in_db:
            await ctx.bot.pool.execute(
                """
                UPDATE guild_config
                SET selfrole = $1
                WHERE guild_id = $2
                """,
                list(role_ids),
                ctx.guild.id,
            )

        await ctx.send(
            embed=discord.Embed(
                title="Selfroles",
                description="These are the roles you can assign to yourself:\n"
                + ", ".join(map(lambda id: f"<@&{id}>", role_ids))
                + ".",
            )
        )

    @commands.command(aliases=["iam"])
    @commands.cooldown(3, 8, commands.BucketType.member)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def assign(self, ctx: cmd.Context, *, role: discord.Role):
        """Toggles a self-assignable role on you"""

        in_db = await ctx.bot.pool.fetchval(
            """
            SELECT $1 = ANY(selfrole) FROM guild_config
            WHERE guild_id = $2
            """,
            role.id,
            ctx.guild.id,
        )

        if not in_db:
            await ctx.send(
                embed=discord.Embed(
                    title="Selfroles",
                    description=f"{role.mention} is not self-assignable.",
                )
            )
            return

        if role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.send(
                embed=discord.Embed(
                    title="Selfroles",
                    description=f"You have been assigned {role.mention}.",
                )
            )
        else:
            await ctx.author.remove_roles(role)
            await ctx.send(
                embed=discord.Embed(
                    title="Selfroles",
                    description=f"You have been unassigned {role.mention}.",
                )
            )

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.member)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @pronouns_enabled()
    async def pronoun(self, ctx: cmd.Context, *, pronoun: str):
        """Assigns or unassigns a pronoun role"""

        selected_pronoun = None

        for entry in pronoun_list:
            written_form = entry[0]
            if pronoun == written_form or pronoun == written_form.split("/")[0]:
                selected_pronoun = written_form
                break

        if not selected_pronoun:
            await ctx.send(
                embed=discord.Embed(
                    title="Pronoun selfrole",
                    description=f"Could not find pronoun for {wrap_in_code(pronoun)}. "
                    f"Use {get_command_signature(ctx, self.pronounlist)} to see all available pronouns.",
                )
            )
            return

        role = get(
            ctx.guild.roles,
            name=selected_pronoun,
            permissions=discord.Permissions.none(),
        )

        if not role:
            role = await ctx.guild.create_role(name=selected_pronoun)

        if role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.send(
                embed=discord.Embed(
                    title="Pronoun selfrole",
                    description=f"Assigned pronoun role {written_form}.",
                )
            )
        else:
            await ctx.author.remove_roles(role)
            await ctx.send(
                embed=discord.Embed(
                    title="Pronoun selfrole",
                    description=f"Unassigned pronoun role {written_form}.",
                )
            )

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @pronouns_enabled()
    async def pronounlist(self, ctx: cmd.Context):
        """Lists all pronouns available for self assignment"""

        await ctx.send(
            embed=discord.Embed(
                title="Pronoun list",
                description=f"List of pronouns known to me are:\n"
                + ", ".join(map(lambda pronoun: pronoun[0], pronoun_list))
                + ".",
            )
        )

    @commands.command()
    @commands.cooldown(3, 8, commands.BucketType.channel)
    @pronouns_enabled()
    async def pronouninfo(self, ctx: cmd.Context, *, pronoun: str):
        """Gives examples on how to use a pronoun"""

        selected_pronoun = None

        for entry in pronoun_list:
            written_form = entry[0]
            if pronoun == written_form or pronoun == written_form.split("/")[0]:
                selected_pronoun = entry
                break

        if not selected_pronoun:
            await ctx.send(
                embed=discord.Embed(
                    title="Pronoun info",
                    description=f"Could not find pronoun for {wrap_in_code(pronoun)}. "
                    f"Use {get_command_signature(ctx, self.pronounlist)} to see all available pronouns.",
                )
            )
            return

        (
            written_form,
            nominative,
            accusative,
            pronominal_possessive,
            predicative_possessive,
            reflexive,
        ) = entry

        embed = discord.Embed(
            title=written_form,
            description=f"Nominative: {nominative}"
            f"\nAccusative: {accusative}"
            f"\nPronominal possessive: {pronominal_possessive}"
            f"\nPredicative possessive: {predicative_possessive}"
            f"\nReflexive: {reflexive}",
        )
        embed.add_field(
            name="Examples",
            value=f"{nominative.capitalize()} went to the park yesterday.\n"
            f"I saw {accusative} when walking home from the store,\n"
            f"as {nominative} were eating {pronominal_possessive} lunch.\n"
            f"I was hungry, so I asked if I could take a small bite of {predicative_possessive}.\n"
            f"Sadly, {nominative} wouldn't have enough left for {reflexive}.",
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    async def sync(self, ctx: cmd.Context):
        """Syncs integrations like Twitch subscribers and YouTube members"""

        integrations = await ctx.guild.integrations()
        for integration in integrations:
            await integration.sync()

        await ctx.send(
            embed=discord.Embed(
                title="Sync",
                description="Synced all integrations:\n"
                + "\n".join(map(lambda i: f"{i.type}: {i.name}", integrations)),
            )
        )


def setup(bot: commands.Bot):
    voice = Roles(bot)
    bot.add_cog(voice)
