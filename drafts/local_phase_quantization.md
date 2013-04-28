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

In most of my articles on face recognition, I've already discussed the problems you'll encounter when trying to perform face recognition in the wild. The [/blog/eigenfaces](Eigenfaces algorithm) yields a great recognition rate - if we are given images with somewhat similar illumination. The Fisherfaces algorithm was able to compensate large differences in illumination - only if we have images with a fixed position and a light source from different directions. Both methods [/static/images/blog/local_binary_patterns/at_database_vs_accuracy_xy.png](need a lot of training data) to build their models and it's often hard to provide all this in real life. So we had a brief look at [/blog/local_binary_patterns](Local Binary Patterns), a method having its roots in the 2D texture analysis. Local Binary Patterns have the nice property to be computationally very simple and robust against linear grayscale transformations. The downside is, that illumination in real life is a highly non-linear thing. We can also overcome this problem by applying the preprocessing presented by Tan and Triggs in:

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

Almost all of the datasets I've experiment with had high-quality image data. The AT&T Facedatabase and Yale Facedatabase A/B have been taken in very controlled conditions, even for my celebrity dataset I have only chosen quality images. In real life you are often confronted with the problem of lower-quality images and your algorithms have to be able to cope with this problem. Local Phase Quantization is a blur-invariant feature description and I think... this is a great chance for an experiment!

## the algorithm ##

## implementation ##

For implementing LPQ we first need a function to calculate us an Euclidean Distance Matrix:

```python
def euclidean_distmatrix(X):
  pass
```

## experiment ##

As always in my articles you can easily run the experiments all by yourself. I am also adding the complete script to the end of the page, just in case GitHub ever goes down.


### dataset ###

The question is: How do the existing face recognition algorithms cope with blur? I guess it's best to use the [AT&T Dataset](...) for a quick experiment, since all of the [/blog/fisherfaces](existing methods have shown to yield excellent recognition rates on this dataset). The figures in the experiment are determined by running a 10-fold cross validation 5 times on a shuffled dataset. This should give us a good estimate of the classifiers true recognition rate.

### reading the image data ###


### preprocessing: gaussian blur ###

It's common in image processing to use a Gaussian blur for reducing image noise and detail. I won't implement the good old Gaussian function all by myself, since applying it is trivial with NumPy is so simple. All that needs to be done is a call [ndimage.gaussian_filter(X, sigma)](...) on the image given in ``X``. 


```python
def preprocess_gaussian(X, sigma):
  return [ndimage.gaussian_filter(xi, sigma) for xi in X]
```

Then applying a Gaussian blur with ``sigma=2`` on a list of images is easy with:

```python
# Read in the AT&T Facedatabase, your path is different:
[X, y] = read_images("/home/philipp/facerec/data/at")
# Apply a Gaussian Blur on each image:
Y = preprocess_gaussian(X, sigma=2)
```

### putting it into a script ###

So let's put everything we have discussed so far into a tiny little script. 

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
