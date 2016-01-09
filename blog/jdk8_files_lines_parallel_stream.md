title: Performance problem with Files.lines for a Parallel Stream (JDK 1.8)
date: 2016-01-09 15:16
tags: java, streams, spliterator
category: java
slug: jdk8_files_lines_parallel_stream
author: Philipp Wagner
summary: The stream of File.lines has a problem when being read in parallel, this post explains why.

[MIT License]: https://opensource.org/licenses/MIT
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser
[Parallel Streams]: https://docs.oracle.com/javase/tutorial/collections/streams/parallelism.html

The ``Files.lines`` method in Java 1.8 yields a very bad performance, when processing the Stream in parallel. I have 
noticed this issue, when benchmarking [JTinyCsvParser] and I also found the cause of the problem. I am writing my finding 
down, in case someone runs into the same problem.

Java 1.8 comes with [Parallel Streams], which provide a nice way for parallel processing in an application. In Java you can basically 
turn every Stream into a Parallel Stream by calling the ``parallel()`` method on the Stream. Internally Java 8 uses something called 
a ``spliterator`` ("splittable Iterator") to estimate the optimal chunk size for your data, in order to decompose the problem into 
sub problems.

The problem with the ``Files.lines`` Stream implementation in JDK 8 is, that it uses the stream from ``BufferedReader.lines``. The 
``spliterator`` of this stream is derived from an iterator and reports no size. This means the size for the chunks cannot be estimated, 
and you have no performance gain when processing the stream in parallel.

There is a (solved) ticket for this Issue in the OpenJDK bugtracker:

* [JDK-8072773: (fs) Files.lines needs a better splitting implementation for stream source](https://bugs.openjdk.java.net/browse/JDK-8072773)

The bug has been solved for Java 1.9, but the fix also works in Java 1.8 for me. You can find the bugfix in the following commit:

* [http://hg.openjdk.java.net/jdk9/jdk9/jdk/rev/4472aa4d4ae9](http://hg.openjdk.java.net/jdk9/jdk9/jdk/rev/4472aa4d4ae9)

Because the OpenJDK code is licensed under terms of the GPL license, I cannot include it in [JTinyCsvParser].