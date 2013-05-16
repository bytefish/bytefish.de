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
from datetime import datetime
from pelican import signals
from lxml import etree

import logging
logger = logging.getLogger(__name__)

# This builds a list of dictionaries similar to:
#
# [{'album': 'Viva La Vida Or Death And All His Friends',
#  'artist': 'Coldplay',
#  'bitrate': '192',
#  'date': '733042',
#  'duration': '249',
#  'file-size': '5995610',
#  'first-seen': datetime.fromtimestamp(1299845660),
#  'genre': 'Other',
#  'last-played': datetime.fromtimestamp(1367611263),
#  'last-seen': datetime.fromtimestamp(1368303708),
#  'location': 'file:///home/philipp/Music/coldplay/viva_la_vida_or_death_and_all_his_friends/09-coldplay__strawberry_swing.mp3',
#  'mimetype': 'application/x-id3',
#  'mtime': datetime.fromtimestamp(1299836480),
#  'play-count': 104,
#  'title': 'Strawberry Swing',
#  'track-number': '9'},
#  ...]
def read_database(filename):
  doc = etree.parse(filename)
  items = []
  for node in doc.iter("entry"):
    if node.attrib["type"] == "song":
      item = {}
      for elem in node:
        elem_tag = elem.tag.replace("-", "_")
        if elem.tag in ('play-count', 'duration', 'bitrate', 'track-number'):
          item[elem_tag] = int(elem.text)
        elif elem.tag in ('first-seen', 'last-played', 'last-seen', 'mtime'):
          item[elem_tag] = datetime.fromtimestamp(int(elem.text))
        else:
          item[elem_tag] = elem.text
      items.append(item)
  return items

def add_rhythmbox_db(generator, metadata):
  if 'RHYTHMBOX_DB' in generator.settings.keys():
    generator.context["rhythmbox_db"] = read_database(generator.settings['RHYTHMBOX_DB'])

def register():
  signals.article_generate_context.connect(add_rhythmbox_db)
