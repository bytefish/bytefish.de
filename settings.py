# -*- coding: utf-8 -*-

AUTHOR = 'Philipp Wagner'
EMAIL = 'bytefish AT gmx DOT de'
SITENAME = 'http://bytefish.de'

SITEURL_PUBLIC = 'http://bytefish.de'
SITEURL_LOCAL = 'http://localhost:8080'

TIMEZONE = 'Europe/Berlin'
DEFAULT_LANG = 'en'
LOCALE = ''

THEME = './themes/minimal/'
MARKUP = 'md'

# Edit predefined pathes:
ARCHIVES_SAVE_AS = 'archives/index.html'

# Generates nice URLs for pages:
PAGE_URL = '{slug}'
PAGE_SAVE_AS = '{slug}/index.html'

# Generate nice URLs for articles:
ARTICLE_URL = 'blog/{slug}'
ARTICLE_SAVE_AS = 'blog/{slug}/index.html'

# Setup the RSS/ATOM feeds:
FEED_RSS = 'feeds/rss.xml'
TAG_FEED_RSS = None
CATEGORY_FEED_RSS = None

FEED_ATOM = 'feeds/atom.xml'
FEED_ALL_ATOM = None
TAG_FEED_ATOM = None
CATEGORY_FEED_ATOM = None

PATH = 'content'
PAGE_DIR = ('pages')

# Save index as blog/index.html:
INDEX_SAVE_AS = 'blog/index.html'

# Navigation menu:
SECTIONS = [
  ('home', '/index.html'),
  ('blog', '/blog'),
  ('documents', '/documents'),
  ('archive', '/archives'),
  ('wiki', '/wiki'),
  ('rss', '/feeds/rss.xml'),
  ('+', 'https://plus.google.com/102725420896943303368?rel=author'),]

# Links to display in the footer:
LINKS = [
  ('bsd', 'http://www.opensource.org/licenses/BSD-3-Clause'),
  ('xhtml', 'http://validator.w3.org/check/referer'),
  ('css3', 'http://jigsaw.w3.org/css-validator/check/referer?profile=css'),
  ('pelican', 'http://www.getpelican.com'),]

# Set this to your Disqus account:
DISQUS_SITENAME = 'bytefish'

# Set some default category:
DEFAULT_CATEGORY = 'Uncategorized'
