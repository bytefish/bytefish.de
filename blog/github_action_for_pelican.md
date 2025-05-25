title: Deploying a Pelican Website using GitHub Actions
date: 2025-05-25 10:25
tags: python, website
category: website
slug: github_action_for_pelican
author: Philipp Wagner
summary: Deploying a Pelican Website using GitHub Actions.

This page is built with Pelican, which is a Static Site Generator. And the deployment has always been a very complex copy-and-paste of the `output` folder using WinSCP (hey, I am lazy!).

The provider of this page offers SSH, so why not use a GitHub Action to automate all this for me? Let's write a workflow to deploy, whenever I push to the `master` branch!

So I start by adding Repository Secrets for:

* `HOST`
    * The hostname of the SSH Server.
* `PORT`
    * The port of the SSH Server (usually `22`)
* `USER`
    * The username configured on the SSH Server.
* `SSHKEY`
    * The Private Key for the SSH Handshake.
* `TARGET_PATH`
    * The target path on the server, we are copying the `output` to.

And then I am adding a file `.github/workflows/deploy.yaml` and add:

```yaml
name: deploy

on: 
    push:
        branches:
            - master

jobs:
    build:
        runs-on: ubuntu-latest

        steps:
        - uses: actions/checkout@v1

        - name: Set up Python
          uses: actions/setup-python@v3
          with:
            python-version: 3.x

        - name: Install pelican with markdown
          shell: bash
          run: "pip install invoke pelican[markdown]"

        - name: Build the project
          shell: bash
          run: "pelican . -s ./settings/settings_prod.py"

        - name: Copy output via scp
          uses: appleboy/scp-action@master
          with:
              host: ${{ secrets.HOST }}
              username: ${{ secrets.USER }}
              port: ${{ secrets.PORT }}
              key: ${{ secrets.SSHKEY }}
              source: settings/output/PROD/
              target: ${{ secrets.TARGET_PATH }}
              strip_components: 3
```

## Conclusion ##

Honestly? I should have done this years ago. 🤭