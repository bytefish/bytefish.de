# -*- coding: utf-8 -*-
import os

# This is a simple configuration for the Pelican (http://getpelican.com) 
# project and it is probably closely tied to the 'minimal' theme I am 
# using.
PLUGIN_PATHS = [ os.path.abspath('./plugins'), ]
PLUGINS = [ 'sitemap', ]
# Most important metadata:
AUTHOR = 'Philipp Wagner'
EMAIL = 'philipp AT bytefish DOT de'
SITENAME = 'https://www.bytefish.de'
OUTPUT_PATH = 'output/PROD/'
# Base URL this page is hosted at:
SITEURL = 'https://www.bytefish.de'
# Timezone is GMT+1:
TIMEZONE = 'Europe/Paris'
# Using a simple date format:
DEFAULT_DATE_FORMAT = ('%d %b %Y')
# We are using the custom minimal2 theme:
THEME = './themes/minimal/'
# Probably add rst here:
MARKUP = ('md',)
# Markdown Configuration:
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight'},
        'markdown.extensions.toc' : {},
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.footnotes': {},
    },
    'output_format': 'html5',
}
# We don't use relative URLs:
RELATIVE_URLS = False
# Edit predefined pathes:
ARCHIVES_SAVE_AS = 'pages.html'
# Generates nice URLs for pages:
PAGE_URL = '{slug}.html'
PAGE_SAVE_AS = '{slug}.html'
# Generate nice URLs for articles:
ARTICLE_EXCLUDES = (('pages',))
ARTICLE_URL = 'blog/{slug}.html'
ARTICLE_SAVE_AS = 'blog/{slug}.html'
# Generate nice URLs for tags:
TAG_URL = 'tag/{name}.html'
TAG_SAVE_AS = 'tag/{name}.html'
TAGS_SAVE_AS = 'tags.html'
# Generate nice URLs for categories:
CATEGORY_URL = 'category/{name}.html'
CATEGORY_SAVE_AS = 'category/{name}.html'
# Setup the RSS/ATOM feeds:
FEED_DOMAIN = SITEURL
FEED_MAX_ITEMS = 10
# We only want RSS/ATOM Feeds for all articles, exclude categories:
FEED_RSS = 'feeds/rss.xml'
FEED_ATOM = 'feeds/atom.xml'
FEED_ALL_ATOM = None
FEED_ALL_RSS = None
TAG_FEED_ATOM = None
TAG_FEED_RSS = None
CATEGORY_FEED_RSS = None
CATEGORY_FEED_ATOM = None
AUTHOR_FEED_RSS = None
AUTHOR_FEED_ATOM  = None
TRANSLATION_FEED_ATOM = None
RSS_FEED_SUMMARY_ONLY = False
# Separate page directory and articles directory:
PAGE_PATHS = [ 'pages' ]
ARTICLE_PATHS = [ 'blog' ]
# Save index as blog.html instead of index.html:
INDEX_SAVE_AS = 'blog.html'
# Navigation menu:
SECTIONS = [
  ('blog', '/blog.html'),
  ('about', '/about.html'),
  ('pages', '/pages.html'),
  ('documents', '/documents.html'),]
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
  'extra/robots.txt' : { 'path' : '../robots.txt' },
  'extra/favicon.ico' : { 'path': '../favicon.ico' },
}
# Folders to copy to <output>/static/...:
STATIC_SAVE_AS = 'static/{path}'
STATIC_PATHS = ['images', 'apps', 'extra/.htaccess', 'extra/robots.txt', 'extra/favicon.ico']
# Codeberg Base Path:
CODEBERG_ISSUE_PATH='https://codeberg.org/bytefish/bytefish.de/issues'
CODEBERG_SOURCE_PATH='https://codeberg.org/bytefish/bytefish.de/src/branch/master/blog'
#Sitemap Settings:
SITEMAP = {
    'format': 'xml',
    'exclude': ['tag/', 'category/', '404.html'],
    'priorities': {
        'articles': 0.5,
        'indexes': 0.5,
        'pages': 0.5
    }
}

# Custom functions available to all templates:
import calendar
import ntpath

def getCodebergPage(source_file):
    filename = getBasename(source_file)
    return '{0}/{1}'.format(CODEBERG_SOURCE_PATH, filename)

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
    'asCodebergPage' : getCodebergPage
}
