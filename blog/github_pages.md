title: Creating and Updating GitHub Pages
date: 2016-08-13 20:30
tags: github, git
category: git
slug: github_pages
author: Philipp Wagner
summary: This article shows how to create and update GitHub pages.

This is a quick example on how I have created GitHub pages for the [JTinyCsvParser] documentation.

## Create and Push the initial gh-pages branch ##

First create a new branch, which is a subtree of the master repository. From the root directory I create 
subtree, which points to the html pages:

```
git subtree split --prefix JTinyCsvParser/documentation/build/html --branch gh-pages
```

Then checkout the branch:

```
git checkout gh-pages
```

And push it to GitHub:

```
git push -u origin gh-pages
```

## Workflow ##

Now whenever you commit and push something to the master branch you can apply this simple workflow to update the ``gh-pages`` branch:

```
git checkout gh-pages
git merge -X theirs -X subtree=JTinyCsvParser/documentation/build/html
git push -u origin gh-pages
```

[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser