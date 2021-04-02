DELETE FROM cleaned_username;

ALTER TABLE cleaned_username
ADD COLUMN nick TEXT NOT NULL;
