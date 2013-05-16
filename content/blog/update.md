title: Website Update
date: 2013-03-13 20:10
tags: website
category: infrastructure
slug: website_update
author: Philipp Wagner

# Website Update #

[http://bytefish.de](http://bytefish.de) has been built on [DokuWiki](http://www.dokuwiki.org) for years and I absolutely loved it. But I don't have the time to keep the installation in sync with latest security fixes and more recently some of the plugins began to act strange. It's finally time to make a change, so these pages are now built by [Pelican](http://getpelican.com), which is a static website generator. [Disqus](http://disqus.com/) is used for the comments, but I can't import comments from the old system - I am sorry.

Most of my private work is open source, so are the sources and content of this page:

* [https://github.com/bytefish/bytefish.de](https://github.com/bytefish/bytefish.de)

The theme is fit to my needs and contains some hardcoded stuff, so it is probably not useful for you without putting some work into. Most of the existing blog posts and wiki pages have been converted and should be available under the same URLs. I have omitted a few articles, that are not relevant anymore and I had to change some URLs in the wiki pages. Therefore some of the wiki pages have been turned into articles, early drafts will be added to [/pages](/pages) in the future. You can get a list of tags for the articles at [/tags](/tags), see I am not a huge fan of tag clouds so I have simply ordered the list by the number of articles. 

I'll probably extend some functionality, but right now I am quite happy. If you find something is missing in here, please do not hesitate to send me a mail!


## useful notes ##

### embedding disqus ###

I am using [Disqus](http://disqus.com/) for comments, which is a really useful service and easy to embed. There are some [concerns raised about privacy](http://en.wikipedia.org/wiki/Disqus#Criticism_and_privacy_concerns), but I've noticed people are less afraid to comment here, compared to my old comment solution. If you are integrating [Disqus](http://disqus.com/), make sure you are setting the [JavaScript configuration variables](http://help.disqus.com/customer/portal/articles/472098-javascript-configuration-variables):

* [http://help.disqus.com/customer/portal/articles/472098-javascript-configuration-variables](http://help.disqus.com/customer/portal/articles/472098-javascript-configuration-variables)

I suggest to use at least ``disqus_shortname`` (required), ``disqus_url`` (optional) and ``disqus_title`` (optional). As an example, the JavaScript for the page you are currently reading looks like this:

```html
<script type="text/javascript">
    /* * * CONFIGURATION VARIABLES: EDIT BEFORE PASTING INTO YOUR WEBPAGE * * */
    var disqus_shortname = 'bytefish'; // required: this is your shortname as registered on disqus.com
    var disqus_url = 'http://bytefish.de/blog/website_update'; // optional: this is a common URL, so disqus knows which comments to show
    var disqus_title = 'Website Update'; // optional: this is a title of the discussion thread, should sound better than the URL
    /* * * DON'T EDIT BELOW THIS LINE * * */
    (function() {
        var dsq = document.createElement('script'); dsq.type = 'text/javascript'; dsq.async = true;
        dsq.src = '//' + disqus_shortname + '.disqus.com/embed.js';
        (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
    })();
</script>
```

### using jinja2 filters ###

Pelican uses [Jinja2](http://jinja.pocoo.org/docs/) as its templating system, which comes with a lot of useful filter functions. However, you'll sometimes want to add your own filter, to treat the input data slightly different. On my page I wanted to sort the tags descending by the number of articles. So I simply added the following at the end of my Pelican configuration:

```python
# Custom functions available to all templates:
from operator import itemgetter

def sort_tags_by_length(tags):
  return sorted(tags, key=lambda tup: len(tup[1]), reverse=True)
  
   
JINJA_FILTERS = {
    'sort_tags_by_length': sort_tags_by_length,
}
```

And now it's easy to use the ``sort_tags_by_length`` filter in a [Jinja2](http://jinja.pocoo.org/docs/) template:

```html
{% block content %}
  {% if tags %}
  <h1>Available Tags and Articles</h1>
    <ul>
    {% for (tag, articles) in tags | sort_tags_by_length %}
      <li><span class="date">{{ tag }}</span> &raquo; <a href="{{ SITEURL }}/tag/{{ tag }}">{{ articles | count }} Article(s)</a></li>
    {% endfor %}
  {% endif %}
{% endblock %}
```

## website statistics ##

After about a month of the website migration, one can see a dramatic improvement in loading times with [Google Webmaster Tools](https://www.google.com/webmasters/):

<a href="/static/images/blog/website_update/crawl_stats.png"><img src="/static/images/blog/website_update/thumbs/crawl_stats.png" alt="Website statistics after a good month." class="mediacenter" /></a>
