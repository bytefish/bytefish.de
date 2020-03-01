# -*- coding: utf-8 -*-

from emojiextension import EmojiExtension

# This is a simple configuration for the Pelican (http://getpelican.com) 
# project and it is probably closely tied to the 'minimal' theme I am 
# using.
PLUGIN_PATHS = [ 'plugins' ]
# Most important metadata:
AUTHOR = 'Philipp Wagner'
EMAIL = 'philipp AT bytefish DOT de'
SITENAME = 'https://bytefish.de'
OUTPUT_PATH = 'output/DEV/'
# Base URL this page is hosted at:
SITEURL = 'http://localhost:8000'
# Timezone is GMT+1:
TIMEZONE = 'Europe/Paris'
# Using a simple date format:
DEFAULT_DATE_FORMAT = ('%d %b %Y')
# We are using the custom minimal theme:
THEME = './themes/minimal/'
# Probably add rst here:
MARKUP = ('md',)
# Markdown Configuration:
MARKDOWN = {
    'extensions' : [EmojiExtension.create_from_json('./resources/emojis.json')],
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight'},
        'markdown.extensions.toc' : {},
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
    },
    'output_format': 'html5',
}
# We don't use relative URLs:
RELATIVE_URLS = False
# Edit predefined pathes:
ARCHIVES_SAVE_AS = 'pages/index.html'
# Generates nice URLs for pages:
PAGE_URL = '{slug}'
PAGE_SAVE_AS = '{slug}/index.html'
# Generate nice URLs for articles:
ARTICLE_EXCLUDES = (('pages',))
ARTICLE_URL = 'blog/{slug}'
ARTICLE_SAVE_AS = 'blog/{slug}/index.html'
# Generate nice URLs for tags:
TAG_URL = 'tag/{name}/'
TAG_SAVE_AS = 'tag/{name}/index.html'
TAGS_SAVE_AS = 'tags/index.html'
# Generate nice URLs for categories:
CATEGORY_URL = 'category/{name}/'
CATEGORY_SAVE_AS = 'category/{name}/index.html'
# Setup the RSS/ATOM feeds:
FEED_DOMAIN = SITEURL
FEED_MAX_ITEMS = 10
# We only want RSS/ATOM Feeds for all articles, exclude categories:
FEED_RSS = 'feeds/rss.xml'
TAG_FEED_RSS = 'feeds/{slug}.rss.xml'
CATEGORY_FEED_RSS = None
FEED_ATOM = 'feeds/atom.xml'
FEED_ALL_ATOM = None
TAG_FEED_ATOM = None
CATEGORY_FEED_ATOM = None
# Separate page directory and articles directory:
PAGE_PATHS = [ 'pages' ]
ARTICLE_PATHS = [ 'blog' ]
# Save index as blog/index.html instead of index.html:
INDEX_SAVE_AS = 'blog/index.html'
# Navigation menu:
SECTIONS = [
  ('blog', '/blog'),
  ('about', '/about'),
  ('pages', '/pages'),
  ('documents', '/documents'),]
# Links to display in the footer:
LINKS = [
  ('bsd', 'http://www.opensource.org/licenses/BSD-3-Clause'),
  ('xhtml', 'http://validator.w3.org/check/referer'),
  ('css3', 'http://jigsaw.w3.org/css-validator/check/referer?profile=css'),
  ('pelican', 'https://github.com/getpelican'),]
# Set some default category:
DEFAULT_CATEGORY = 'uncategorized'
# A list of files to copy from the source to the destination
EXTRA_PATH_METADATA = {
  'extra/.htaccess' : { 'path' : '../.htaccess'},
  'extra/robots.txt' : { 'path' : '../robots.txt' }
}
# Folders to copy to <output>/static/...:
STATIC_SAVE_AS = 'static/{path}'
STATIC_PATHS = ['images', 'apps', 'extra/.htaccess', 'extra/robots.txt']

# Github Base Path:
GITHUB_ISSUE_PATH='https://github.com/bytefish/bytefish.de/issues'
GITHUB_SOURCE_PATH='https://github.com/bytefish/bytefish.de/blob/master/blog'

# Custom functions available to all templates:
import calendar
import ntpath

def getGitHubPage(source_file):
    filename = getBasename(source_file)
    return '{0}/{1}'.format(GITHUB_SOURCE_PATH, filename)

def getBasename(path):
    return ntpath.basename(path)

def month_name(month_number):
    return calendar.month_name[month_number]

# Probably replace those with simpler methods:
from operator import itemgetter, methodcaller

def sortTupleByIndex(items, index=0, reverse=True):
  return sorted(items, key=lambda tup: len(tup[index]), reverse=reverse)

def sortDictByKey(items, key, reverse=True, default=None):
  if default is None:
    return sorted(items, key=itemgetter(key), reverse=reverse) 
  return sorted(items, key=methodcaller('get', key, default), reverse=reverse) 

JINJA_FILTERS = {
    'month_name' : month_name,
    'sortTupleByIndex': sortTupleByIndex,
    'sortDictByKey': sortDictByKey,
    'basename' : getBasename,
    'asGitHubPage' : getGitHubPage
}
