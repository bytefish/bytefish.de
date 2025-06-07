title: notes
date: 2025-06-07 11:18
author: Philipp Wagner
template: page
summary: Notes, Ideas and Links

## Table of contents ##

[TOC]

## 2025-06-07: How it all started... 22 years ago  ##

This page started in 2003 as a way to share my poems with the world. It was a time full of beautiful self-pity, and not knowing what to do with my life… basically the whole range of first-world problems.

Please never use the Wayback Machine!

To the next 20 years to come!🍻

## 2025-06-07: The Microsoft Copilot Distortion Bubble ##

The Microsoft Build 2025 conference was all about AI and how it improves productivity. So it’s interesting to see Microsoft dogfooding Copilot in their `dotnet/aspnetcore` and `dotnet/runtime` repositories:

* [https://github.com/dotnet/runtime/pulls](https://github.com/dotnet/runtime/pulls)

It’s hilarious to see these world class engineers begging their Copilot to “Please do not forget to add the files to the project!” and “Do not make up APIs!”. Yes, they label it an experiment, but I am sure it’s mandated use.

And why label it an experiment? The very same engineers just went on stage and told us, how it improves their workflow! Why am I not witnessing any use of Copilot in other PRs? What am I missing here?

Of course there’s a chance I am getting the whole thing wrong and Microsoft engineers believe in this? Or am I witnessing a cult? Whatever it is, outside the distortion bubble this whole thing looks pretty bad.

## 2025-06-07: Fulltext Search Engine using SQLite and FTS5 Tables ##

I've started a new job in 2024, so my free-time budget for writing blog articles took a cut.

One of the projects I didn't write about is a Full-Text Search Engine using SQLite FTS5 and Blazor WASM:

* [https://github.com/bytefish/SqliteFulltextSearch](https://github.com/bytefish/SqliteFulltextSearch)

## 2025-06-07: Another "Google Zanzibar" Experiment with .NET ##

Relationship-based Access Control is an interesting approach to Authorization, with "Google Zanzibar" as an 
implementation described by Google. It's kind of a nemesis for me, because I have already tried to:

* Build something with OpenFGA, which is a Google Zanzibar implementation (Failed)
* Build a ANTLR4 Parser for the Google Zanzibar Configuration Language (Success, but not useful)
* Implement the Check and Expand API described in the Google Zanzibar paper (Maybe Success)

So of course I am now exploring it again and try to implement the Check API, Expand API and ListObjects API:

* [https://github.com/bytefish/GoogleZanzibarExperiments](https://github.com/bytefish/GoogleZanzibarExperiments)

I don't know yet, if this is going to be successful or where it is going.

# 2025-06-07: Notes, or "Lowering the Bar for Writing" ##

This "notes page" is an idea, to make it easier for me to *write*, without the tedious work of long-form blog articles. Maybe notes on this page are something akin to a small tweet.

At the moment this is a single page with technical and non-technical content being mixed wildly. I am not sure, if it’s a good idea. We will see.

However it lowers the bar for writing and publishing by a lot and I am sure I’ll find a way to turn this into a more coherent piece.

As of now, I really like this format! 🚀 
