title: Fisherfaces in OpenCV
date: 2011-11-12 15:11
tags: c++, opencv,face recognition
category: computer vision
slug: fisherfaces_in_opencv
author: Philipp Wagner
summary: Fisherface implementation in OpenCV and how to build the code.

# Fisherfaces in OpenCV #

This project is a C++ implementation of the Fisherfaces method as described in: 

* P. Belhumeur, J. Hespanha, and D. Kriegman, *"Eigenfaces vs. Fisherfaces: Recognition Using Class Specific Linear Projection"*, IEEE Transactions on Pattern Analysis and Machine Intelligence, 19(7):711--720, 1997.

It was written in preparation of [libfacerec](https://github.com/bytefish/libfacerec) and its contribution to OpenCV. The project has no other dependencies except a recent OpenCV2. 

All code is put under a [BSD license](http://www.opensource.org/licenses/bsd-license), so feel free to use it for your projects:

* [https://github.com/bytefish/opencv/blob/master/lda](https://github.com/bytefish/opencv/blob/master/lda)

## Building the Project ##

This project does not need any external libraries except [OpenCV](http://opencv.willowgarage.com), so compiling the project is as easy as writing (assuming you are in this folder):

<pre>
philipp@mango:~/some/dir/lda$ mkdir build
philipp@mango:~/some/dir/lda$ cd build
philipp@mango:~/some/dir/lda/build$ cmake ..
philipp@mango:~/some/dir/lda/build$ make
philipp@mango:~/some/dir/lda/build$ ./lda filename.ext
</pre>

And if you are in Windows using [MinGW](http://www.mingw.org) it may look like this:

<pre>
C:\some\dir\lda> mkdir build
C:\some\dir\lda> cd build
C:\some\dir\lda\build> cmake -G "MinGW Makefiles" ..
C:\some\dir\lda\build> mingw32-make
C:\some\dir\lda\build> lda.exe filename.ext
</pre>

You probably have to set the ``OpenCV_DIR`` variable if it hasn't been added by your installation, see [Line 5 in the CMakeLists.txt](https://github.com/bytefish/opencv/blob/master/lda/CMakeLists.txt#L5) on how to do this. 

## Using the Project ##

The project comes with an example, please have a look at the [main.cpp](https://github.com/bytefish/opencv/blob/master/lda/src/main.cpp) on how to use the classes. You need some data to make the examples work, sorry but I really can't include those face databases in my repository. I have thoroughly commented the code and reworked it lately, to make its usage simpler. So if anything regarding the classes is unclear, please read the comments.

In the example I use a CSV file to read in the data, it's the easiest solution I can think of right now. However, if you know a simpler solution please ping me about it. Basically all the CSV file needs to contain are lines composed of a ``filename`` followed by a ``;`` (semicolon) followed by the ``label`` (as an *integer number*), making up a file like this: 

<pre>
/dataset/subject1/image0.jpg;0
/dataset/subject1/image1.ext;0
/dataset/subject2/image0.ext;1
/dataset/subject2/image1.ext;1
</pre>

Think of the ``label`` as the subject (the person) this image belongs to, so same subjects (persons) should have the same ``label``. An example CSV file for the [AT&T Facedatabase](http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html) is [given here](https://github.com/bytefish/opencv/blob/master/eigenfaces/at.txt), which looks like this (assuming I've extracted the database to ``/home/philipp/facerec/data/at/``, file is without ``...`` of course):

<pre>
/home/philipp/facerec/data/at/s1/1.pgm;0
/home/philipp/facerec/data/at/s1/2.pgm;0
...
/home/philipp/facerec/data/at/s2/1.pgm;1
/home/philipp/facerec/data/at/s2/2.pgm;1
...
/home/philipp/facerec/data/at/s40/1.pgm;39
/home/philipp/facerec/data/at/s40/2.pgm;39
</pre>

Once you have a CSV file with *valid* ``filenames`` and ``labels``, you can run the demo by simply starting the demo with the path to the CSV file as parameter:

<pre>
./lda /path/to/your/csvfile.ext
</pre>

Or if you are in Windows:

<pre>
lda.exe /path/to/your/csvfile.ext
</pre>
