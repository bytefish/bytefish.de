-- Populate Image Database

INSERT INTO im.image(imageid, hash, description)
    VALUES (1, 'a3b0c44', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (2, 'a9b0c44', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (3, 'e3b0c44', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (4, 'a3c0c74', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (5, 'e301244', 'Some Description');
    
INSERT INTO im.image(imageid, hash, description, createdon)
    VALUES (6, 'e301214', 'Some Description', '2014-03-09T22:00:00.132');

-- Populate Tag Database

INSERT INTO im.tag (tagid, name)
    VALUES (1, 'Cool');

INSERT INTO im.tag (tagid, name)
    VALUES (2, 'Soccer');

INSERT INTO im.tag (tagid, name)
    VALUES (3, 'Car');

-- Assign Images
INSERT INTO im.image_tag (imageid,tagid)
    VALUES (1,1);

INSERT INTO im.image_tag (imageid,tagid)
    VALUES (1,2);

INSERT INTO im.image_tag (imageid, tagid)
    VALUES (2,1);
    
INSERT INTO im.image_tag (imageid, tagid)
    VALUES (2,3);

-- Comments
INSERT INTO im.comment (commentid, imageid, text)
	VALUES(1, 1, 'This is a comment!');

INSERT INTO im.comment (commentid, imageid, text)
	VALUES(2, 1, 'A second comment.');