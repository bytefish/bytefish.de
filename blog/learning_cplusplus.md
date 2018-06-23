title: Sharing my C++ Adventures
date: 2018-06-23 11:02
tags: c++
category: c++
slug: learning_cplusplus
author: Philipp Wagner
summary: This article described my journey with C++ .

Whenever I hit a compiler message I can't make sense of I have to laugh out loud. I really do.

When I started programming I knew some Java, Delphi and Visual Basic. But trustful sources told me, that you have 
to know C++ for being *a real programmer*! And without any hesitation I bought magazines showing how to build 
all kind of great applications with C++.

I was used to the simplicity of Java, Delphi and Visual Basic. Want a TCP Server? I just fire up a ``ServerSocket`` and 
Java does all the rest for me! Want a User Interface? Let's create some amazing looking AWT UIs, I am the king of the 
``BorderLayout``! You want to build a Windows application quickly?  I just drop in some OCX components from the Toolbox 
into my ``Form1.vb``!

Sun Microsystems had a great Java documentation and tutorials for almost everything, that I wanted to do. I could copy 
and paste the code and know what? It simply worked.

## Meeting C++ ##

And then I tried to learn C++. What to build first? Of course a GUI! But maybe let's learn how to print stuff to the 
Command Line first. So I clicked through the Wizard. And oh! So many project templates for later joy: 

<a href="/static/images/blog/learning_cplusplus/projects.jpg">
    <img src="/static/images/blog/learning_cplusplus/projects.jpg">
</a>

But Philipp, hold on! Let's not get too excited for now. Let us build this "Win32 Console Application" first and get a feel 
for this mysterious and amazing language:

<a href="/static/images/blog/learning_cplusplus/console.jpg">
    <img src="/static/images/blog/learning_cplusplus/console.jpg">
</a>

And uh. What is this ``stdafx.h``? The C++ literature here does not mention it. What does this ``return 0`` do? Can I also 
``return 1``? What is this ``\n``? Well. I am young. I don't care. I will understand it later. Let's execute it. And... 

> Fatal error C1083: Cannot open precompiled header file: ‘Debug\project.pch’: No such file or directory

What on earth is a PCH file? What did I wrong? I just clicked Execute and now I get all kind of error messages. 

Help!

Eventually some Lycos Search result pointed me to a page, that explained how to enable "Precompiled Headers" for my 
Console application. I didn't really understand it, but OK. After trying to build UIs with Microsoft Foundation Classes 
(MFC) for a good month and failing to write a simple TCP Listener... my frustration level was reached. 

I gave up. 

Maybe I am not a real programmer.

## Fast-forward ##

Some years ago I thought I can finally program C++. I contributed to the OpenCV project! I was creating all kinds of CMake 
files for helping me with all the complicated Build-related stuff. ``#ifndef`` directives in my header files? Linking other 
libraries? A piece of cake! I (thought I) knew the Language. I (thought I) knew how to use templates.

And then I applied for my first job and got into a large C++ project.

And nothing I saw looked like the C++ I thought I knew. When I tried to build simple "Hello World" applications with the 
internal libraries I was greeted with books of Compiler errors. What on earth does this Macro do? You can do that with 
templates? Shared Pointers? Auto Pointers? Argument Dependent Lookup? Oh dear. I think my Hello World applications could 
have participated in the [The Grand C++ Error Explosion Competition].

The Post-Traumatic Stress Disorder of my youthful C++ learning attempts kicked in, this time mixed with an unhealthy amount 
of [Imposter Syndrome]. They hired me as a C++ programmer! And there is a JIRA Board with tickets assigned to me! Tickets I 
should estimate! People said it is a dead simple task and I even fail to compile a Hello World?

These days I know the most important thing in programming: Ask for help early on and communicate problems openly. 
No one is perfect. No one knows everything. And by no means I am judging the code. I still regard my colleague as 
one of the best programmers I ever met. And there is often a good reason for company-internal C++ libraries: C++ Code 
should often work on multiple Operating Systems and the C++ Standard Library only has a limited amount of features.

But back then I got more and more frustrated about everything. So frustrated, that I... gave up. 

Maybe I am not a real programmer.

## Aftermath ##

Eventually the company didn't give me up. I got into a C\# project and the language brought back some fun. I learnt more about 
Unit Testing. People showed me how to apply all kinds of Design Patterns, that unrolled my Spaghetti Code into something more 
human. Using LINQ was an eye-opener to functional programming. Reactive Extensions. Win Forms. WPF. There is so much to learn! 
``Func``, ``Action``, real Generics. ``ADO.NET`` for connecting to databases!

And most importantly: The Compiler errors often made some sense and pointed me into the right direction.

So whenever the .NET compiler (or Java) throws an error message at me, that I can't make sense of... it reminds me of my totally 
helpless, frustrated self sitting in front of a C++ compiler and trying to make sense of the error message explosion (and how 
I am unable to write a simple Hello World Console application with C++).

And I have to laugh out loud.

## Conclusion ##

From time to time I look at modern C++ code and how sexy C++14 looks like, with all its functional features. But as a result of 
my life-long C++ adventure I didn't touch a C++ IDE for years. And I decided to always put C++ as the last language on my CV. Even 
when the list of programming languages should be sorted in an ascending lexicographic order.

I think I still don't know C++, but I hope it doesn't make me less a programmer.


[The Grand C++ Error Explosion Competition]: https://tgceec.tumblr.com/
[Imposter Syndrome]: https://en.wikipedia.org/wiki/Impostor_syndrome