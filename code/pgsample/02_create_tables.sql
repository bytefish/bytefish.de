DO $$
BEGIN

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'image'
) THEN

CREATE TABLE im.Image
(
	ImageID SERIAL PRIMARY KEY,
	Hash VARCHAR(64) NOT NULL,
	Description VARCHAR(2000) NULL,
	CreatedOn TIMESTAMP WITHOUT TIME ZONE DEFAULT(NOW() AT TIME ZONE 'utc')
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'tag'
) THEN

CREATE TABLE im.Tag
(
	TagID SERIAL PRIMARY KEY,
	Name VARCHAR(255) NOT NULL
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'image_tag'
) THEN

CREATE TABLE im.Image_Tag
(
	ImageID INTEGER NOT NULL,
	TagID INTEGER NOT NULL,
	PRIMARY KEY (ImageID, TagID)  
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'comment'
) THEN

CREATE TABLE im.Comment
(
	CommentID SERIAL PRIMARY KEY,
	ImageID INTEGER NOT NULL,
	Text VARCHAR(2000) NOT NULL,
	CreatedOn TIMESTAMP WITHOUT TIME ZONE DEFAULT(NOW() AT TIME ZONE 'utc')
);

END IF;

END;
$$;