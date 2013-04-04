title: Validating Algorithms
date: 2012-09-08 09:02
tags: python, opencv
category: computer vision
slug: validating_algorithms
author: Philipp Wagner

# Validating Algorithms #

This post was originally written for the [[http://answers.opencv.org/questions/|OpenCV QA forum]]. I post it here, because I think it's a great example of how Open Source projects make your life easy.

## introduction ##

Actually validating algorithms is a very interesting topic and it's really not that hard. In this post I'll show how to validate your algorithms (I'll take the FaceRecognizer in this example). As always in my posts I will show it with a full source code example, because I think it's much easier to explain stuff by code.

So whenever people tell me *"my algorithm performs bad"*, I ask them: 

  * What is *bad* actually?
  * Did you rate this by looking at one sample?
  * What was your image data?
  * How do you split between training and test data? 
  * What is your metric?
  * [...]

My hope is, that this post will clear up some confusion and show how easy it is to validate algorithms. Because what I have learned from experimenting with computer vision and machine learning algorithms is:

* Without a proper validation it's all about chasing ghosts. You really, really need figures to talk about. 

All code in this post is put under BSD License, so feel free to use it for your projects.

## validating algorithms ##

One of the most important tasks of any computer vision project is to acquire image data. You need to get the same image data as you expect in production, so you won't have any bad experiences when going live. A very practical example: If you want to recognize faces in the wild, then it isn't useful to validate your algorithms on images taken in a very controlled scenario. Get as much data as possible, because *Data is king*.

Once you have got some data and you have written your algorithm, it comes to evaluating it. There are several strategies for validating, but I think you should start with a simple Cross Validation and go on from there, for informations on Cross Validation see:

* [Wikipedia on Cross-Validation](http://en.wikipedia.org/wiki/Cross-validation_%28statistics%29)

Instead of implementing it all by ourself, we'll make use of [scikit-learn](https://github.com/scikit-learn/) a great Open Source project:

* [https://github.com/scikit-learn](https://github.com/scikit-learn)

It comes with a very good documentation and tutorials for validating algorithms:

* [http://scikit-learn.org/stable/tutorial/statistical_inference/index.html](http://scikit-learn.org/stable/tutorial/statistical_inference/index.html)

So the plan is the following:

1. Write a function to read some image data.
2. Wrap the //cv2.FaceRecognizer// into a scikit-learn estimator.
3. Estimate the performance of our //cv2.FaceRecognizer// with a given validation and metric.
4. Profit!

## Getting the image data right ##

First I'd like to write some words on the image data to be read, because questions on this almost always pop up. For sake of simplicity I have assumed in the example, that the images (the *faces*, *persons you want to recognize*) are given in folders. One folder per person. So imagine I have a folder (a dataset) called ``dataset1``, with the subfolders ``person1``, ``person2`` and so on:

<pre>
philipp@mango:~/facerec/data/dataset1$ tree -L 2 | head -n 20
.
|-- person1
|   |-- 1.jpg
|   |-- 2.jpg
|   |-- 3.jpg
|   |-- 4.jpg
|-- person2
|   |-- 1.jpg
|   |-- 2.jpg
|   |-- 3.jpg
|   |-- 4.jpg

[...]
</pre>

One of the public available datasets, that is already coming in such a folder structure is the AT&T Facedatabase, available at:

* [http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html](http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html)

Once unpacked it is going to look like this (on my filesystem it is unpacked to ``/home/philipp/facerec/data/at/``, your path is different!):

<pre>
philipp@mango:~/facerec/data/at$ tree .
.
|-- README
|-- s1
|   |-- 1.pgm
|   |-- 2.pgm
[...]
|   //-- 10.pgm
|-- s2
|   |-- 1.pgm
|   |-- 2.pgm
[...]
|   //-- 10.pgm
|-- s3
|   |-- 1.pgm
|   |-- 2.pgm
[...]
|   //-- 10.pgm
   
...

40 directories, 401 files
</pre>

## putting it together ##

So first of all we'll define a method ``read_images`` for reading in the image data and labels:

```python
import os
import sys
import cv2
import numpy as np

def read_images(path, sz=None):
    """Reads the images in a given folder, resizes images on the fly if size is given.
    
    Args:
        path: Path to a folder with subfolders representing the subjects (persons).
        sz: A tuple with the size Resizes 
    
    Returns:
        A list [X,y]
        
            X: The images, which is a Python list of numpy arrays.
            y: The corresponding labels (the unique number of the subject, person) in a Python list.
    """
    c = 0
    X,y = [], []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            subject_path = os.path.join(dirname, subdirname)
            for filename in os.listdir(subject_path):
                try:
                    im = cv2.imread(os.path.join(subject_path, filename), cv2.IMREAD_GRAYSCALE)
                    # resize to given size (if given)
                    if (sz is not None):
                        im = cv2.resize(im, sz)
                    X.append(np.asarray(im, dtype=np.uint8))
                    y.append(c)
                except IOError, (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    raise
            c = c+1
    return [X,y]
```
        
Reading in the image data then becomes as easy as calling:

```python
[X,y] = read_images("/path/to/some/folder")
```
    
Because some algorithms (for example Eigenfaces, Fisherfaces) require your images to be of equal size, I added a second parameter //sz//. By passing the tuple ``sz``, all of the images get resized. So the following call will resize all images in ``/path/to/some/folder`` to ``100x100`` pixels, while loading:

```python
[X,y] = read_images("/path/to/some/folder", (100,100))
```
    
All classifiers in scikit-learn are derived from a //BaseEstimator//, which is supposed to have a //fit// and //predict// method. The //fit// method gets a list of samples //X// and corresponding labels //y//, so it's trivial to map to the train method of the //cv2.FaceRecognizer//. The //predict// method also gets a list of samples and corresponding labels, but this time we'll need to return the predictions for each sample:

```python
from sklearn.base import BaseEstimator

class FaceRecognizerModel(BaseEstimator):

    def __init__(self):
        self.model = cv2.createEigenFaceRecognizer()
        
    def fit(self, X, y):
        self.model.train(X,y)
    
    def predict(self, T):
        return [self.model.predict(T[i]) for i in range(0, T.shape[0])]
```

You can then choose between a large range of validation methods and metrics to test the ``cv2.FaceRecognizer`` with. You can find the available cross validation algorithms in [sklearn.cross_validation](https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/cross_validation.py):

* Leave-One-Out cross validation
* K-Folds cross validation
* Stratified K-Folds cross validation
* Leave-One-Label-Out cross-validation
* Random sampling with replacement cross-validation
* [...]

For estimating the recognition rate of the ``cv2.FaceRecognizer`` I suggest using a Stratified Cross Validation. You may ask why anyone needs the other Cross Validation methods. Imagine you want to perform emotion recognition with your algorithm. What happens if your training set has images of the person you test your algorithm with? You will probably find the closest match to the person, but not the emotion. In these cases you should perform a subject-independent cross validation.

Creating a Stratified k-Fold Cross Validation Iterator is very simple with scikit-learn:

```python
from sklearn import cross_validation as cval
# Then we create a 10-fold cross validation iterator:
cv = cval.StratifiedKFold(y, 10)
```

And there's a wide range of metrics we can choose from. For now I only want to know the precision of the model, so we import the callable function ``sklearn.metrics.precision_score``:

```python
from sklearn.metrics import precision_score
```

Now we'll only need to create our estimator and pass the ``estimator``, ``X``, ``y``, ``precision_score`` and ``cv`` to ``sklearn.cross_validation.cross_val_score``, which calculates the cross validation scores for us:

```python
# Now we'll create a classifier, note we wrap it up in the 
# FaceRecognizerModel we have defined in this file. This is 
# done, so we can use it in the awesome scikit-learn library:
estimator = FaceRecognizerModel()
# And getting the precision_scores is then as easy as writing:
precision_scores = cval.cross_val_score(estimator, X, y, score_func=precision_score, cv=cv)
```
    
There's a large amount of metrics available, feel free to choose another one:

* [https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/metrics/metrics.py](https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/metrics/metrics.py)

So let's put all this in a script!

## validation.py ##

```python
# Author: Philipp Wagner <bytefish@gmx.de>
# Released to public domain under terms of the BSD Simplified license.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the organization nor the names of its contributors
#     may be used to endorse or promote products derived from this software
#     without specific prior written permission.
#
#   See <http://www.opensource.org/licenses/bsd-license>

import os
import sys
import cv2
import numpy as np

from sklearn import cross_validation as cval
from sklearn.base import BaseEstimator
from sklearn.metrics import precision_score

def read_images(path, sz=None):
    """Reads the images in a given folder, resizes images on the fly if size is given.
    
    Args:
        path: Path to a folder with subfolders representing the subjects (persons).
        sz: A tuple with the size Resizes 
    
    Returns:
        A list [X,y]
        
            X: The images, which is a Python list of numpy arrays.
            y: The corresponding labels (the unique number of the subject, person) in a Python list.
    """
    c = 0
    X,y = [], []
    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            subject_path = os.path.join(dirname, subdirname)
            for filename in os.listdir(subject_path):
                try:
                    im = cv2.imread(os.path.join(subject_path, filename), cv2.IMREAD_GRAYSCALE)
                    # resize to given size (if given)
                    if (sz is not None):
                        im = cv2.resize(im, sz)
                    X.append(np.asarray(im, dtype=np.uint8))
                    y.append(c)
                except IOError, (errno, strerror):
                    print "I/O error({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    raise
            c = c+1
    return [X,y]

class FaceRecognizerModel(BaseEstimator):

    def __init__(self):
        self.model = cv2.createFisherFaceRecognizer()
        
    def fit(self, X, y):
        self.model.train(X,y)
    
    def predict(self, T):
        return [self.model.predict(T[i]) for i in range(0, T.shape[0])]
        
if __name__ == "__main__":
    # You'll need at least some images to perform the validation on:
    if len(sys.argv) < 2:
        print "USAGE: facerec_demo.py </path/to/images> [</path/to/store/images/at>]"
        sys.exit()
    # Read the images and corresponding labels into X and y.
    [X,y] = read_images(sys.argv[1])
    # Convert labels to 32bit integers. This is a workaround for 64bit machines,
    # because the labels will truncated else. This is fixed in recent OpenCV
    # revisions already, I just leave it here for people on older revisions.
    #
    # Thanks to Leo Dirac for reporting:
    y = np.asarray(y, dtype=np.int32)
    # Then we create a 10-fold cross validation iterator:
    cv = cval.StratifiedKFold(y, 10)
    # Now we'll create a classifier, note we wrap it up in the 
    # FaceRecognizerModel we have defined in this file. This is 
    # done, so we can use it in the awesome scikit-learn library:
    estimator = FaceRecognizerModel()
    # And getting the precision_scores is then as easy as writing:
    precision_scores = cval.cross_val_score(estimator, X, y, score_func=precision_score, cv=cv)
    # Let's print them:
    print precision_scores
```
        
## running the script ##

The above script will print out the precision scores for the Fisherfaces method. You simply need to call the script with the image folder:

<pre>
philipp@mango:~/src/python$ python validation.py /home/philipp/facerec/data/at

Precision Scores:
[ 1.          0.85        0.925       0.9625      1.          0.9625
  0.8875      0.93333333  0.9625      0.925     ]
</pre>

## conclusion ##

The conclusion is, that... Open Source projects make your life really easy! There's much to enhance for the script. You probably want to add some logging, see which fold you are in for example. But it's a start for evaluating any metric you want, just read through the scikit-learn tutorials and adapt it to the above script. I encourage everybody to play around with OpenCV Python and scikit-learn, because interfacing these two great projects is really, really easy as you can see!
