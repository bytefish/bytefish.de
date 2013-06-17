# -*- coding: utf-8 -*-
"""
 Simple plugin to parse Rhythmbox XML Music Database.

 Software License Agreement (BSD License)

 Copyright (c) 2013, Philipp Wagner
 All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions
 are met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.
  * Neither the name of the author nor the names of its
    contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.
 
"""
from lxml import etree
from datetime import datetime
from collections import defaultdict
import sqlite3

import logging
logger = logging.getLogger(__name__)

# Builds a list of dictionaries similar to:
#
# [{'album': 'Viva La Vida Or Death And All His Friends',
#  'artist': 'Coldplay',
#  'bitrate': '192',
#  'date': '733042',
#  'duration': '249',
#  'file_size': '5995610',
#  'first_seen': datetime.fromtimestamp(1299845660),
#  'genre': 'Other',
#  'last_played': datetime.fromtimestamp(1367611263),
#  'last_seen': datetime.fromtimestamp(1368303708),
#  'location': 'file:///home/philipp/Music/coldplay/viva_la_vida_or_death_and_all_his_friends/09-coldplay__strawberry_swing.mp3',
#  'mimetype': 'application/x-id3',
#  'mtime': datetime.fromtimestamp(1299836480),
#  'play_count': 104,
#  'title': 'Strawberry Swing',
#  'track_number': '9'},
#  ...]
def read_database(filename):
  doc = etree.parse(filename)
  items = []
  for node in doc.iter("entry"):
    if node.attrib["type"] == "song":
      item = {}
      for elem in node:
        elem_tag = elem.tag.replace("-", "_") # Jinja2 has problems with "-" as key
        if elem.tag in ('play-count', 'duration', 'bitrate', 'track-number'):
          item[elem_tag] = int(elem.text)
        elif elem.tag in ('first-seen', 'last-played', 'last-seen', 'mtime'):
          item[elem_tag] = datetime.fromtimestamp(int(elem.text))
        else:
          item[elem_tag] = elem.text
      items.append(item)
  return items

# I'll just throw the data into one fat table. Don't be afraid of duplicates, 
# we are going to read the Music DB into memory anyway:
CREATE_TABLE_STATEMENT = """
  CREATE TABLE rhythmdb
    (artist VARCHAR(256),
     album VARCHAR(256),
     title VARCHAR(256),
     track_number INTEGER,
     genre VARCHAR(256),
     bitrate INTEGER,
     date DATETIME,
     duration INTEGER,
     file_size INTEGER,
     first_seen DATETIME,
     last_played DATETIME,
     last_seen DATETIME,
     location VARCHAR(256),
     mimetype VARCHAR(256),
     mtime DATETIME,
     play_count INTEGER)
  """

INSERT_STATEMENT = "insert into rhythmdb (artist, album, title, track_number, genre, bitrate, date, duration, file_size, first_seen, last_played, last_seen, location, mimetype, mtime, play_count) values (:artist, :album, :title, :track_number, :genre, :bitrate, :date, :duration, :file_size, :first_seen, :last_played, :last_seen, :location, :mimetype, :mtime, :play_count)"

# Builds a dictionary with the keys for each row 
# returned by sqlite3:
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
 
if __name__ == "__main__":
  items = read_database("/home/philipp/.local/share/rhythmbox/rhythmdb.xml")
  
  connection = sqlite3.connect(":memory:")
  connection.isolation_level = None
  connection.row_factory = dict_factory
  
  cursor = connection.cursor()
  cursor.execute(CREATE_TABLE_STATEMENT)
  
  for item in items:
    cursor.execute(INSERT_STATEMENT, defaultdict(lambda: None, item))
  
  # Top 10 artists:
  cursor.execute("select artist, sum(play_count) AS play_count from rhythmdb group by artist order by 2 desc LIMIT 10")
  print cursor.fetchall()

  connection.close()
