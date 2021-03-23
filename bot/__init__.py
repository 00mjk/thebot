import re
from os import environ

import aiohttp
import asyncpg
import cachetools
import discord
from discord.ext import commands

from bot import cmd
from bot.utils import wrap_in_code

initial_extensions = (
    "jishaku",
    "bot.ext.errors",
    "bot.ext.meta",
    "bot.ext.help",
    "bot.ext.roles",
    "bot.ext.voice",
    "bot.ext.emoji",
    "bot.ext.chat",
)


class Bot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix_list,
            description="General purpose utility do it all bot",
            help_command=None,
            activity=discord.Game(name=";help"),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                users=False,
                replied_user=True,
            ),
            intents=discord.Intents(
                guilds=True,
                messages=True,
                emojis=True,
                reactions=True,
                voice_states=True,
                members=True,
            ),
            member_cache_flags=discord.MemberCacheFlags.none(),
            max_messages=None,
        )

        self.add_check(self.global_check)

        for extension in initial_extensions:
            self.load_extension(extension)

    async def start(self, *args, **kwargs):
        self.session = aiohttp.ClientSession()
        self.pool = await asyncpg.create_pool(dsn=environ.get("DATABASE_DSN"))
        await super().start(*args, **kwargs)

    async def close(self):
        await self.session.close()
        await self.pool.close()
        await super().close()

    prefix_cache = cachetools.TTLCache(maxsize=float("inf"), ttl=900)

    async def get_prefix_for_message(self, message):
        if not message.guild:
            return ";"

        try:
            return self.prefix_cache[message.guild.id]
        except KeyError:
            prefix = await self.pool.fetchval(
                """
                SELECT prefix FROM guild_config
                WHERE guild_id = $1
                """,
                message.guild.id,
            )
            self.prefix_cache[message.guild.id] = prefix
            return prefix

    async def get_prefix_list(self, bot, message):
        prefix = await self.get_prefix_for_message(message)

        return (
            f"<@!{bot.user.id}> ",
            f"<@{bot.user.id}> ",
            f"{prefix} ",
            prefix,
        )

    async def global_check(self, ctx):
        await commands.bot_has_permissions(
            send_messages=True,
            embed_links=True,
            attach_files=True,
        ).predicate(ctx)

        return True

    async def on_ready(self):
        print(f"Ready as {self.user} ({self.user.id})")

    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild and message.guild.id not in self.prefix_cache:
            await self.pool.execute(
                """
                INSERT INTO guild_config (guild_id) VALUES ($1)
                ON CONFLICT DO NOTHING
                """,
                message.guild.id,
            )

        ctx = await self.get_context(message, cls=cmd.Context)

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            prefix = await self.get_prefix_for_message(message)

            await message.channel.send(
                embed=discord.Embed(
                    title="Prefix",
                    description=f"My prefix is {wrap_in_code(prefix)}.",
                )
            )

        await self.invoke(ctx)

    async def on_error(self, event, *args, **kwargs):
        errors = self.get_cog("Errors")
        if errors:
            await errors.on_error(event, *args, **kwargs)
