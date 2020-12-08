# The bot

General purpose utility do it all bot.

Invite using <https://discord.com/api/oauth2/authorize?client_id=715557048187617280&permissions=51200&scope=bot>.

## Installing

Requires Python 3.8

```sh
python3.8 -m venv venv  # Create virtual environment
source venv/bin/activate  # Activate virtual environment
pip install -Ur requirements.txt  # Install dependencies
```

This project requires a postgres database, migrations are done with `agnostic`.

Create a role and a database.

```sql
CREATE ROLE thebot WITH LOGIN PASSWORD 'secure-password';
CREATE DATABASE thebot;
GRANT ALL ON DATABASE thebot TO thebot;
```

Bootstrap agnostic and migrate to the lastest database version.

```sh
agnostic -t postgres -u thebot -d thebot bootstrap --no-load-existing
agnostic -t postgres -u thebot -d thebot migrate
```

## Running

Make sure that the virtual environment is active.

Load configuration using environment variables, or using a `.env` file.

Relevant environment variables are:

- `DISCORD_TOKEN`: Discord bot token
- `DATABASE_DSN`: Database credentials in the form of the [libpq connection URI format](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)

Once configured, the bot can be started using the following command:

```sh
python main.py
```
