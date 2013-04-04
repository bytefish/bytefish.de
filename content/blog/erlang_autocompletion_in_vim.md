title: Erlang autocompletion in vim
date: 2010-08-11 01:38
tags: vim, erlang
category: programming
slug: erlang_autocompletion_in_vim
author: Philipp Wagner

# Erlang autocompletion in vim #

In case someone is interested, here is my mini how-to for erlang autocompletion in vim. You need to get a dictionary with the Erlang keywords first. Someone has already created it for you: [erlang.dict](http://github.com/cooldaemon/myhome/tree/master/.vim/dict/erlang.dict). Thanks a lot! Save ``erlang.dict`` to the folder ``~/.vim/dict`` (or any folder you wish, just keep it consistent... create if necessary).

Then add to ``~/.vim/after/ftplugin/erlang.vim`` (create if necessary):

```sh
setlocal softtabstop=2
setlocal shiftwidth=2
setlocal tabstop=2
 
setlocal iskeyword+=:
setlocal complete=.,w,b,u,t,i,k
setlocal dictionary=~/.vim/dict/erlang.dict
 
setlocal makeprg=erlc\ %
```

That's it. Now type ``lists:``, press ``<Ctrl> + p`` in edit mode (of an erlang file of course) and you should see the autocompletion.
