title: Website Update
date: 2013-03-13 20:10
tags: website
category: infrastructure
slug: website_update
author: Philipp Wagner
summary: This page has been converted to Pelican, a static website generator. This post discusses my reasons for moving away from DokuWiki and some of the things I've learnt along the way.

It's finally time to make a change, so these pages are now built by [Pelican](http://getpelican.com), which is a static website generator and [Disqus](http://disqus.com/) is used for the comments.

Most of my private work is open source, so are the sources and content of this page:

* [https://github.com/bytefish/bytefish.de](https://github.com/bytefish/bytefish.de)

The theme should also enhance the readability on mobile devices. It is fit to my needs, so please have a look at the settings before using it.

Most of the existing blog posts and wiki pages have been converted and should be available under the same URLs. I have omitted a few articles, that are not relevant anymore 
and I had to change some URLs in the wiki pages. Therefore some of the wiki pages have been turned into articles, early drafts will be added to [/pages](/pages) in the future. 

If you find something is missing in here, please do not hesitate to send me a mail!

## Notes ##

### Embedding Disqus ###

I am using [Disqus](http://disqus.com/) for comments, which is a really useful service and easy to embed. There are some [concerns raised about privacy](http://en.wikipedia.org/wiki/Disqus#Criticism_and_privacy_concerns), but I've noticed people are less afraid to comment here, compared to my old comment solution. If you are integrating [Disqus](http://disqus.com/), make sure you are setting the [JavaScript configuration variables](http://help.disqus.com/customer/portal/articles/472098-javascript-configuration-variables):

* [http://help.disqus.com/customer/portal/articles/472098-javascript-configuration-variables](http://help.disqus.com/customer/portal/articles/472098-javascript-configuration-variables)

I suggest to use at least ``disqus_shortname`` (required), ``disqus_url`` (optional) and ``disqus_title`` (optional). As an example, the JavaScript for the page you are currently reading looks like this:

```html
<script type="text/javascript">
    /* * * CONFIGURATION VARIABLES: EDIT BEFORE PASTING INTO YOUR WEBPAGE * * */
    var disqus_shortname = 'bytefish'; // required: this is your shortname as registered on disqus.com
    var disqus_url = 'https://bytefish.de/blog/website_update'; // optional: this is a common URL, so disqus knows which comments to show
    var disqus_title = 'Website Update'; // optional: this is a title of the discussion thread, should sound better than the URL
    /* * * DON'T EDIT BELOW THIS LINE * * */
    (function() {
        var dsq = document.createElement('script'); dsq.type = 'text/javascript'; dsq.async = true;
        dsq.src = '//' + disqus_shortname + '.disqus.com/embed.js';
        (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
    })();
</script>
```

## Website Statistics ##

A month after the website migration, one can see a dramatic improvement in loading times with [Google Webmaster Tools](https://www.google.com/webmasters/):

<a href="/static/images/blog/website_update/crawl_stats.png"><img src="/static/images/blog/website_update/thumbs/crawl_stats.png" alt="Website statistics after a good month." class="mediacenter" /></a>

### Using gzip ###

I have added gzip compression to my ``.htaccess``, in order to save a few extra bytes:

```
## Set GZIP compression for faster load time and 
## reduce amount of bandwidth consumed by clients:
SetOutputFilter DEFLATE
AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/x-javascript application/x-httpd-php
BrowserMatch ^Mozilla/4 gzip-only-text/html
BrowserMatch ^Mozilla/4\.0[678] no-gzip
BrowserMatch \bMSIE !no-gzip !gzip-only-text/html
BrowserMatch \bMSI[E] !no-gzip !gzip-only-text/html
SetEnvIfNoCase Request_URI \.(?:gif|jpe?g|png)$ no-gzip
Header append Vary User-Agent env=!dont-vary
```