-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns an image by id.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_image(image_id int) RETURNS json AS 
$BODY$
DECLARE
  found_image im.image;
  image_tags json;
  image_comments json;
BEGIN
  -- Load the image data:
  SELECT * INTO found_image 
  FROM im.image i 
  WHERE i.imageid = image_id;  
  
  -- Get assigned tags:
  SELECT CASE WHEN COUNT(x) = 0 THEN '[]' ELSE json_agg(x) END INTO image_tags 
  FROM (SELECT t.* 
        FROM im.image i
        INNER JOIN im.image_tag it ON i.imageid = it.imageid
        INNER JOIN im.tag t ON it.tagid = t.tagid
        WHERE i.imageid = image_id) x;

  -- Get assigned comments:
  SELECT CASE WHEN COUNT(y) = 0 THEN '[]' ELSE json_agg(y) END INTO image_comments 
  FROM (SELECT * 
        FROM im.comment c 
        WHERE c.imageid = image_id) y;

  -- Build the JSON Response:
  RETURN (SELECT json_build_object(
    'imageid', found_image.imageid,
    'hash', found_image.hash,
    'description', found_image.description,
    'created_on', found_image.createdon, 
    'comments', image_comments,
    'tags', image_tags));

END
$BODY$
LANGUAGE 'plpgsql';

-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns an image by hash value.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_image_by_hash(hashval varchar) RETURNS json AS 
$BODY$
BEGIN

    RETURN (SELECT im.get_image(i.imageid) 
            FROM image i
            WHERE i.hash = hashval);

END
$BODY$
LANGUAGE 'plpgsql';

-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns the (distinct) set of images matching the given tags.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_image_by_tag(VARIADIC tags varchar[]) RETURNS SETOF json AS 
$BODY$
BEGIN

    RETURN QUERY
    SELECT im.get_image(x.imageid)
    FROM (SELECT DISTINCT i.imageid as imageid
          FROM im.image i
            INNER JOIN im.image_tag it on i.imageid = it.imageid
            INNER JOIN im.tag t on t.tagid = it.tagid
          WHERE t.name = ANY(tags)) x;

END
$BODY$
LANGUAGE 'plpgsql';

-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns the images in added between now() and now() - interval.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_latest(timespan interval) RETURNS SETOF json AS 
$BODY$
BEGIN
    
    RETURN QUERY
    SELECT im.get_image(i.imageid)
    FROM im.image i
    WHERE i.createdon > (NOW() - timespan);
    
END
$BODY$
LANGUAGE 'plpgsql';