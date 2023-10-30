title: Face Recognition with Python/GNU Octave/Matlab
date: 2011-10-09 15:10
tags: python, matlab, octave, face recognition
category: computer vision
slug: face_recognition_with_opencv2
author: Philipp Wagner
summary: This post presents you the guide I've wished for, when I was working myself into face recognition. The Eigenfaces and Fisherfaces method are explained in detail and implemented with Python and GNU Octave/MATLAB. The code and document is released under a BSD license, so feel free to use it for your commercial and academic projects.

I've recently pushed some code to perform face recognition with OpenCV2 into [my github repository](https://github.com/bytefish). If you've ever researched on face recognition I am pretty sure you've noticed: there's a [gigantic number of publications](http://scholar.google.de/scholar?q=face+recognition), but source code is almost always kept like a secret. Since I've got some positive feedback on [Machine Learning with OpenCV2](https://www.bytefish.de/pdf/machinelearning.pdf), I thought I write a document on:

* [Face Recognition with OpenCV2 (Python version, pdf)](https://www.bytefish.de/pdf/facerec_python.pdf)
* [Face Recognition with OpenCV2 (GNU Octave/MATLAB version, pdf)](https://www.bytefish.de/pdf/facerec_octave.pdf)

It's the kind of guide I've wished for, when I was working myself into face recognition. The Eigenfaces and Fisherfaces method are explained in detail and implemented with Python and GNU Octave/MATLAB. The code and document is released under a BSD license, so feel free to use it for your commercial and academic projects.

Note: the latest version of the document and code can be obtained from the projects github repository:

* [https://github.com/bytefish/facerecognition_guide](http://www.github.com/bytefish/facerecognition_guide)

## Getting & Working with the Code ##

I've got some mails and comments on how to acquire and use the code in the document. It may not be obvious, so I am going to write a small tutorial (which I'll add to the Guide as soon as I have some time). I should have done so in the first place!

### Getting the Code ###

So the first thing you need to do is to get the code. Since I have git installed on my machine I simply clone the github repository:

```
philipp@mango:~/github$ git clone https://github.com/bytefish/facerecognition_guide.git
```

This will check out the latest Face Recognition Guide from the github repository, with all source code examples included in the document. You'll see something like this as output:

```
Initialized empty Git repository in /home/philipp/github/facerecognition_guide/.git/
remote: Counting objects: 223, done.
remote: Compressing objects: 100% (141/141), done.
remote: Total 223 (delta 82), reused 211 (delta 70)
Receiving objects: 100% (223/223), 8.89 MiB | 283 KiB/s, done.
Resolving deltas: 100% (82/82), done.
```

If you have troubles using [git](http://git-scm.org), then you can also download the entire repository as a zip (or tar.gz) from:

* https://github.com/bytefish/facerecognition_guide/downloads

Once downloaded (or unzipped) the directory has the following content:

```
philipp@mango:~/github/facerecognition_guide$ tree -d -L 1
.
|-- bib
|-- img
|-- section
`-- src
    |-- m
    `-- py
```

Where:

* ``bib`` contains the bibliography.
* ``img`` contains the images.
* ``section`` contains the sections.
* ``src`` contains the source code.
    * ``m`` The code for the GNU Octave/MATLAB version.
    * ``py`` The code for the Python version.

### Getting the Data right ###

Before we start you should prepare your data. For sake of simplicity I have assumed, that the images (*faces*, *persons you want to recognize*) are given in folders. So imagine I have a folder ``images``, with the subfolders ``person1``, ``person2`` and so on:

```
philipp@mango:~/facerec/data/images$ tree -L 2 | head -n 20
.
|-- person1
|   |-- 1.jpg
|   |-- 2.jpg
|   |-- 3.jpg
|   |-- 4.jpg
...
|-- person2
|   |-- 1.jpg
|   |-- 2.jpg
|   |-- 3.jpg
|   |-- 4.jpg

[...]
```

One of the publicly available datasets, that is already coming in such a folder structure is the AT&T Face Database, available at:

* [http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html](http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html)

Once unpacked it is going to look like this (on my filesystem it is unpacked to ``/home/philipp/facerec/data/at/``, your path is different!):

```
philipp@mango:~/facerec/data/at$ tree .
.
|-- README
|-- s1
|   |-- 1.pgm
|   |-- 2.pgm
[...]
|   `-- 10.pgm
|-- s2
|   |-- 1.pgm
|   |-- 2.pgm
[...]
|   `-- 10.pgm
|-- s3
|   |-- 1.pgm
|   |-- 2.pgm
[...]
|   `-- 10.pgm
   
...

40 directories, 401 files
```

### Working with the Code ###

So let's have a look at the Python version first! As you have seen, all the source code is in the ``src`` folder, which you have acquired with the repository (or your downloaded zip!). The Python version has two folders ``scripts`` and ``tinyfacerec``:

```
philipp@mango:~/github/facerecognition_guide$ tree -d -L 3
.
`-- src
    |-- m
    `-- py
        |-- scripts
        `-- tinyfacerec
```

Where:

* ``scripts`` are the scripts to show how to use the tiny library we developed (hence the name *tinyfacerec*). These are the same examples as shown in the guide.
* ``tinyfacerec`` is the face recognition library, that was developed within the document.

Running the Python samples is easy. First of all ``cd`` into ``scripts`` directory:

```sh
philipp@mango:~/github/facerecognition_guide$ cd src/py/scripts/
```

and from there you can start the scripts by running:

```sh
python <scriptname.py> </path/to/your/images>
```

Where:

* ``<scriptname.py>`` is the script you want to run.
* ``</path/to/your/images>`` is the folder, with the images you want learn on.

### Example: Eigenfaces ###

So to learn the Eigenfaces of the AT&T Facedatabase (which I extracted to ``/home/philipp/facerec/data/at``) I would run ``example_eigenfaces.py`` like this (*make sure you adapt the path to the images* for your system):

```
python example_eigenfaces.py /home/philipp/facerec/data/at
```

And the script will generate two plots for you (in the scripts folder!):

<div class="table">
  <table>
    <thead>
      <tr>
        <th>Filename</th>
        <th>Plot</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>python_pca_eigenfaces.png</td>
        <td><a href="/static/images/blog/face_recognition_with_python/python_pca_eigenfaces.png"><img src="/static/images/blog/face_recognition_with_python/thumbs/python_pca_eigenfaces.jpg" alt="Eigenfaces"/></a></td>
      </tr>
      <tr>
        <td>python_pca_reconstruction.png</td>
        <td><a href="/static/images/blog/face_recognition_with_python/python_pca_reconstruction.png"><img src="/static/images/blog/face_recognition_with_python/thumbs/python_pca_reconstruction.jpg" alt="Eigenfaces Reconstruction" /> </a> </td>
      </tr>
    </tbody>
  </table>
</div>

## Credits ##

I can only make such cool examples, because of nice people providing the image data. Credit where credit's due, so I'd like to quote from the official README coming with the AT&T Facedatabase.

### AT&T Face Database ###

The Database of Faces, formerly 'The ORL Database of Faces', contains a set of face images taken between April 1992 and April 1994. The database was used in the context of a face recognition project carried out in collaboration with the Speech, Vision and Robotics Group of the Cambridge University Engineering Department.

There are ten different images of each of 40 distinct subjects. For some subjects, the images were taken at different times, varying the lighting, facial expressions (open / closed eyes, smiling / not smiling) and facial details (glasses / no glasses). All the images were taken against a dark homogeneous background with the subjects in an upright, frontal position (with tolerance for some side movement).

The files are in PGM format. The size of each image is 92x112 pixels, with 256 grey levels per pixel. The images are organised in 40 directories (one for each subject), which have names of the form sX, where X indicates the subject number (between 1 and 40). In each of these directories, there are ten different images of that subject, which have names of the form Y.pgm, where Y is the image number for that subject (between 1 and 10).

A copy of the database can be retrieved from:

* [http://www.cl.cam.ac.uk/research/dtg/attarchive/pub/data/att_faces.zip](http://www.cl.cam.ac.uk/research/dtg/attarchive/pub/data/att_faces.zip)

