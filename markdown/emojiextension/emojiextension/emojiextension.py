from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern

from pkg_resources import resource_stream, resource_listdir

import json
import io
import os
import codecs

EMOJI_RE = r'(::)(.*?)::'

class EmojiExtension(Extension):

    def __init__(self, **kwargs):
        super(EmojiExtension, self).__init__(**kwargs)
        
        
    def extendMarkdown(self, md, md_globals):
        filename = os.path.join(os.path.dirname(__file__), 'emojis.json')
        emoji_list = json.loads(resource_stream('emojiextension.resources', 'emojis.json').read().decode('utf-8'))
        emojis = dict((emoji['key'], emoji['value']) for emoji in emoji_list)
        md.inlinePatterns.add('emoji', EmojiInlineProcessor(EMOJI_RE, emojis) ,'<not_strong')

        
class EmojiInlineProcessor(Pattern):
    
    def __init__(self, pattern, emojis):
        super(EmojiInlineProcessor, self).__init__(pattern)
        
        self.emojis = emojis
        
    def handleMatch(self, m):
    
        emoji_key = m.group(3)
        
        if self._is_null_or_whitespace(emoji_key):
            return ''
                
        return self.emojis.get(emoji_key, '')
    
    def _is_null_or_whitespace(self, s):
        return not s or not s.strip()

def makeExtension(**kwargs):  # pragma: no cover
    return FencedCodeExtension(**kwargs)