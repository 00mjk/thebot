CREATE TABLE cleaned_username (
  guild_id BIGINT NOT NULL REFERENCES guild_config ON DELETE CASCADE,
  member_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, member_id)
);
