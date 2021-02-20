UPDATE guild_config
SET selfrole = '{}'
WHERE selfrole IS NULL;

UPDATE guild_config
SET selfrole_pronoun = FALSE
WHERE selfrole_pronoun IS NULL;

UPDATE guild_config
SET embed_messages = FALSE
WHERE embed_messages IS NULL;

ALTER TABLE guild_config
ALTER COLUMN selfrole SET NOT NULL,
ALTER COLUMN selfrole SET DEFAULT '{}',
ALTER COLUMN selfrole_pronoun SET NOT NULL,
ALTER COLUMN selfrole_pronoun SET DEFAULT FALSE,
ALTER COLUMN embed_messages SET NOT NULL,
ALTER COLUMN embed_messages SET DEFAULT FALSE;
