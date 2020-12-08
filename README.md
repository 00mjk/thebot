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

## Running

Make sure that the virtual environment is active.

Enter environment variables in a file named `.env`. Namely `DISCORD_TOKEN`, and `DATABASE_DSN`.

```sh
python main.py
```
