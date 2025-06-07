title: notes
date: 2025-06-07 11:18
author: Philipp Wagner
template: page
summary: Notes, Ideas and Links

## Table of contents ##

[TOC]

## 2025-07-06: Fulltext Search Engine using SQLite and FTS5 Tables ##

I've started a new job in 2024, so my free-time budget for writing blog articles took a cut.

One of the projects I didn't write about is a Full-Text Search Engine using SQLite FTS5 and Blazor WASM:

* [https://github.com/bytefish/SqliteFulltextSearch](https://github.com/bytefish/SqliteFulltextSearch)

## 2025-07-06: Another "Google Zanzibar" Experiment with .NET ##

Relationship-based Access Control is an interesting approach to Authorization, with "Google Zanzibar" as an 
implementation described by Google. It's kind of a nemesis for me, because I have already tried to:

* Build something with OpenFGA, which is a Google Zanzibar implementation (Failed)
* Build a ANTLR4 Parser for the Google Zanzibar Configuration Language (Success, but not useful)
* Implement the Check and Expand API described in the Google Zanzibar paper (Maybe Success)

So of course I am now exploring it again and try to implement the Check API, Expand API and ListObjects API:

* [https://github.com/bytefish/GoogleZanzibarExperiments](https://github.com/bytefish/GoogleZanzibarExperiments)

I don't know yet, if this is going to be successful or where it is going.
