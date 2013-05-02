title: Local Phase Quantization
date: 2013-04-28 16:40
tags: python, face recognition
category: computer vision
slug: local_phase_quantization
author: Philipp Wagner

# Local Phase Quantization (LPQ) #

Internet, here I am! Now that [I can work from anywhere I want to](/blog/huawei_e352s), it's finally time to work on new articles again. The first algorithm I'd like to discuss is Local Phase Quantization (LPQ), which has been described in:

* 

LPQ has been added to the [facerec](http://github.com/bytefish/facerec) project, which is my playground for experimenting with new computer vision algorithms. I have also added the GNU Octave/MATLAB implementation provided by []() and []() with only minor modifications, so all credit goes to the original authors. The experiments in this article are based on the [Python](http://www.python.org) implementation, feel free to verify the results with the GNU Octave/MATLAB branch.

## a quick recap ##

In most of my articles on face recognition, I've already discussed the problems you'll encounter when trying to perform face recognition in the wild. The [Eigenfaces algorithm](/blog/eigenfaces) yields a great recognition rate - if we are given images with somewhat similar illumination. The Fisherfaces algorithm was able to compensate large differences in illumination - only if we have images with a fixed position and a light source from different directions. Both methods [need a lot of training data](/static/images/blog/local_binary_patterns/at_database_vs_accuracy_xy.png) to build their models and it's often hard to provide all this in real life. So we had a brief look at [Local Binary Patterns](/blog/local_binary_patterns), a method having its roots in the 2D texture analysis. Local Binary Patterns have the nice property to be computationally very simple and robust against linear grayscale transformations. The downside is, that illumination in real life is a highly non-linear thing. We can also overcome this problem by applying the preprocessing presented by Tan and Triggs in:

* 

In [Python](http://www.python.org) with [NumPy](http://www.scipy.org) the algorithm fits into this 10-liner:

```python
import numpy as np
from scipy import ndimage

def tantriggs(X, alpha = 0.1, tau = 10.0, gamma = 0.2, sigma0 = 1.0, sigma1 = 2.0):
  X = np.array(X, dtype=np.float32)
  X = np.power(X, gamma)
  X = np.asarray(ndimage.gaussian_filter(X, sigma1) - ndimage.gaussian_filter(X, sigma0))
  X = X / np.power(np.mean(np.power(np.abs(X), alpha)), 1.0/alpha)
  X = X / np.power(np.mean(np.power(np.minimum(np.abs(X),tau),alpha)), 1.0/alpha)
  X = tau*np.tanh(X/tau)
  return X
```

Almost all of the datasets I've experiment with had high-quality image data. The [AT&T Facedatabase]() and [Yale Facedatabase A/B]() have been taken in very controlled conditions, even for [my celebrity dataset](/blog/fisherfaces) I have only chosen the higher quality images. In real life you are often confronted with the problem of low quality images and your algorithms have to be able to cope with this problem. Local Phase Quantization is a blur-invariant feature description and I think... this is a great chance for an experiment!

## the algorithm ##

## implementation ##

For implementing LPQ we first need a function to calculate us an Euclidean Distance Matrix:

```python
def euclidean_distmatrix(X):
  pass
```

## experiment ##

As always in my articles you can easily run the experiments all by yourself. 


### dataset ###

The question is: How do the existing face recognition algorithms cope with blur? I guess it's best to use the [AT&T Dataset](...) for a quick experiment, since all of the [existing methods have shown to yield excellent recognition rates on this dataset](/blog/fisherfaces). The figures in the experiment are determined by running a 10-fold cross validation 5 times on a shuffled dataset. This should give us a good estimate of the classifiers true recognition rate.

## getting the image data right ##

I'd like to write some words on the image data to be read, because questions on this **almost always** pop up. For sake of simplicity I have assumed in the experiments, that the images (the *faces*, *persons you want to recognize*) are given in folders. One folder per person. So imagine I have a folder (a dataset) called ``dataset1``, with the subfolders ``person1``, ``person2`` and so on:

<pre>
philipp@mango:~/facerec/data/dataset1$ tree -L 2 | head -n 20
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
...
</pre>

This makes it easy to read in the image data, without the need of a configuration file or overkill things like a database. One of the public available datasets, that is already coming in such a folder structure is the AT&T Facedatabase available at:

* [http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html](http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html)

Once unpacked it is going to look like this (on my filesystem it is unpacked to ``/home/philipp/facerec/data/at/``, your path is different!):

<pre>
philipp@mango:~/facerec/data/at$ tree .
.
|-- README
|-- s1
|   |-- 1.pgm
|   |-- 2.pgm
 ...
|-- s2
|   |-- 1.pgm
|   |-- 2.pgm
 ...
|-- s3
|   |-- 1.pgm
|   |-- 2.pgm
 ...

40 directories, 401 files
</pre>

### reading the image data ###

So now that you know the folder structure, we can define a method ``read_images`` for reading in the image data and associated labels:

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

### preprocessing: gaussian blur ###

We are going to validate the algorithms on both, the original dataset and a blurred version. It's common in image processing to use a Gaussian blur for reducing image noise and detail. Applying a Gaussian blur is trivial with NumPy, since all that needs to be done is a call [ndimage.gaussian_filter(x, sigma)](...), with the image given in ``x``. 

To apply the Gaussian filter on each image, you can use a function like ``preprocess_gaussian``:

```python
def preprocess_gaussian(X, sigma):
  return [ndimage.gaussian_filter(x, sigma) for x in X]
```

Applying a Gaussian blur with ``sigma=2`` on a list of images is then as easy as:

```python
# Read in the AT&T Facedatabase, your path is different:
[X, y] = read_images("/home/philipp/facerec/data/at")
# Apply a Gaussian Blur on each image:
Y = preprocess_gaussian(X, sigma=2)
```

### experimental setup ###

The parameters used in the experiments are taken from the relevant publications and previous experiments. 

<table>
  <tr>
    <th>algorithm</th>
    <th><a href="http://www.github.com/bytefish/facerec">facerec</a> module</th>
    <th>parameters</th>
  </tr>
  <!-- Eigenfaces -->
  <tr>
    <!-- algorithm -->
    <td>
    Eigenfaces
    </td>
    <!-- facerec module -->
    <td>
    </td>
    <!-- parameters -->
    <td>
      <ul>
        <li>
        num_components = 50
        </li>
      </ul>
    </td>
  </tr>
  <!-- Fisherfaces -->
  <tr>
    <!-- algorithm -->
    <td>
    Fisherfaces
    </td>
    <!-- facerec module -->
    <td>
    </td>
    <!-- parameters -->
    <td>
      <ul>
        <li>num_components = 0 (default, means: number of components are determined from data)
      </ul>
    </td>
  </tr>
  <!-- Local Binary Patterns -->
  <tr>
    <!-- algorithm -->
    <td>
    Local Binary Patterns
    </td>
    <!-- facerec module -->
    <td>
    </td>
    <!-- parameters -->
    <td>
      <ul>
        <li>radius = 1 (default)</li>
        <li>neighbors = 8 (default)</li>
      </ul>    
    </td>
  </tr>
  <!-- Local Phase Quantization -->
  <tr>
    <!-- algorithm -->
    <td>
    Local Phase Quantization
    </td>
    <!-- facerec module -->
    <td>
    </td>
    <!-- parameters -->
    <td>
    </td>
  </tr>
</table>

### results ###


