UPDATE guild_config
SET auto_clean_normalize = FALSE
WHERE auto_clean_normalize IS NULL;

UPDATE guild_config
SET auto_clean_dehoist = FALSE
WHERE auto_clean_dehoist IS NULL;

ALTER TABLE guild_config
ALTER COLUMN auto_clean_normalize SET NOT NULL,
ALTER COLUMN auto_clean_normalize SET DEFAULT FALSE,
ALTER COLUMN auto_clean_dehoist SET NOT NULL,
ALTER COLUMN auto_clean_dehoist SET DEFAULT FALSE;
