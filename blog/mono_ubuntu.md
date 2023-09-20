title: Mono on Ubuntu 14.04
date: 2016-01-15 11:09
tags: csharp, tinycsvparser, mono, linux
category: mono
slug: mono_ubuntu
author: Philipp Wagner
summary: This article explains how to use Mono on Ubuntu 14.04.3.

[MIT License]: https://opensource.org/licenses/MIT
[JTinyCsvParser]: https://codeberg.org/bytefish/JTinyCsvParser
[TinyCsvParser]: https://codeberg.org/bytefish/TinyCsvParser
[Parallel Streams]: https://docs.oracle.com/javase/tutorial/collections/streams/parallelism.html
[Ubuntu]: http://www.ubuntu.com/
[Mono]: http://www.mono-project.com/
[MonoDevelop]: http://www.monodevelop.com/

There is an open source project called [Mono], which provides a .NET-compatible set of tools, a C# compiler and Common Language Runtime (CLR).
This makes it possible to run C# code in Linux. I wanted to see, if [TinyCsvParser] works in Linux and I was pleasantly surprised, that all 
Unit Tests succeeded without touching a single line of code.

Installing the latest stable release [Mono] 4.2 on a fresh Ubuntu installation is easy.

## Adding the project GPG signing key and the package repository ##

Switch into a Terminal of your choice and add the Mono project signing key and the repository to 

```
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
echo "deb http://download.mono-project.com/repo/debian wheezy main" | sudo tee /etc/apt/sources.list.d/mono-xamarin.list
sudo apt-get update
```

## Installing Mono ##

Once the package list has been updated, you can install [Mono] 4.2 by running:

```
sudo apt-get install mono-complete
```

## Installing MonoDevelop ##

The easiest way to build a .NET project with [Mono] is to use the [MonoDevelop] IDE.

```
sudo apt-get install monodevelop
```

## Installing the MonoDevelop NUnit Plugin ##

In order to run the NUnit Unit Tests, you should install the NUnit Plugin for [MonoDevelop]:

```
sudo apt-get install monodevelop-nunit
```

You can show the sidebar with the Unit Tests from the Menu bar with:

```
Menu Bar: View -> Pads -> Unit Tests
```