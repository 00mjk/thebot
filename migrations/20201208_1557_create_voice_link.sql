CREATE TABLE voice_link (
  guild_id BIGINT NOT NULL REFERENCES guild_config ON DELETE CASCADE,
  text_channel_id BIGINT NOT NULL,
  voice_channel_id BIGINT NOT NULL,
  PRIMARY KEY (text_channel_id, voice_channel_id)
);
