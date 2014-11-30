# -*- coding: utf-8 -*-

# This is a simple configuration for the Pelican (http://getpelican.com) 
# project and it is probably closely tied to the 'minimal' theme I am 
# using.
# Most important metadata:
AUTHOR = 'Philipp Wagner'
EMAIL = 'bytefish AT gmx DOT de'
SITENAME = 'http://bytefish.de'
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
# Turn language guessing off!
MD_EXTENSIONS = ['codehilite(css_class=highlight, guess_lang=False)','extra']
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
TAG_FEED_RSS = None
CATEGORY_FEED_RSS = None
FEED_ATOM = 'feeds/atom.xml'
FEED_ALL_ATOM = None
TAG_FEED_ATOM = None
CATEGORY_FEED_ATOM = None
# Separate page directory and articles directory:
PAGE_DIR = ('pages')
ARTICLE_DIR = ('blog')
# A list of files to copy from the source to the destination
FILES_TO_COPY = (
  ('extra/.htaccess', '.htaccess'),
  ('extra/robots.txt', 'robots.txt'),
  ('extra/philipp_wagner.asc.gz', 'static/philipp_wagner.asc.gz'),
  )
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
# Set this to your Disqus account:
DISQUS_SITENAME = 'bytefish'
# Set some default category:
DEFAULT_CATEGORY = 'uncategorized'
# Folders to copy to <output>/static/...:
STATIC_PATHS = ['images' ]

# Custom functions available to all templates:
import calendar

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
    'sortDictByKey': sortDictByKey   
}
