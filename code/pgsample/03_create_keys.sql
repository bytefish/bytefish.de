DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'image_tag_imageid_fkey') THEN
	ALTER TABLE im.image_tag
		ADD CONSTRAINT image_tag_imageid_fkey
		FOREIGN KEY (ImageID) REFERENCES im.Image(ImageID);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'image_tag_tagid_fkey') THEN
	ALTER TABLE im.image_tag
		ADD CONSTRAINT image_tag_tagid_fkey
		FOREIGN KEY (TagID) REFERENCES im.Tag(TagID);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'comment_imageid_fkey') THEN
	ALTER TABLE im.comment
		ADD CONSTRAINT comment_imageid_fkey
		FOREIGN KEY (ImageID) REFERENCES im.Image(ImageID);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_tag_name') THEN
	ALTER TABLE im.tag
		ADD CONSTRAINT uk_tag_name
		UNIQUE (Name);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_image_hash') THEN
	ALTER TABLE im.Image
		ADD CONSTRAINT uk_image_hash
		UNIQUE (Hash);
END IF;

END;
$$;