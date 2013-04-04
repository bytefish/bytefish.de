title: Gender Classification
date: 2011-08-17 21:29
tags: face recognition, matlab, octave
category: computer vision
slug: gender_classification
author: Philipp Wagner

# gender classification #

My last post was very long and I promise to keep this one short. In this post I want to do gender classification on a set of face images and find out which are the specific features faces differ in.

## Dataset ##

I have used the celebrity dataset from my last post and downloaded images for [Emma Watson](http://en.wikipedia.org/wiki/Emma_Watson), [Naomi Watts](http://en.wikipedia.org/wiki/Naomi_Watts) and [Jennifer Lopez](http://en.wikipedia.org/wiki/Jennifer_lopez). So the database has 8 male and 5 female subjects, each with 10 images. All images were chosen to have a frontal face perspective and have been cropped to a size of ``140x140`` pixels, just like [this set of images](/static/images/blog/fisherfaces/clooney_set.png). You can easily find some images yourself using [Google Images](http://images.google.com), then locate the eye positions and use a tool like [crop_face.py](http://www.bytefish.de/blog/aligning_face_images) to geometrically normalize it.

## Experiments ##

Get the code from github by either cloning the repository:

```sh
$ git clone git@github.com:bytefish/facerec.git
```

or downloading the latest version as a [tar](https://github.com/bytefish/facerec/tarball/master) or [zip](https://github.com/bytefish/facerec/zipball/master) archive.

Then startup Octave and make the functions available:

<pre>
$ cd facerec/m
$ octave
octave> addpath(genpath("."));
octave> fun_fisherface = @(X,y) fisherfaces(X,y); % no parameters needed
octave> fun_predict = @(model,Xtest) fisherfaces_predict(model,Xtest,1); % 1-NN
</pre>

### subject-dependent cross-validation ###

A Leave-One-Out Cross validation shows that the Fisherfaces method can very accurately predict, wether a given face is male or female:

<pre>
octave> [X y width height names] = read_images("/home/philipp/facerec/data/gender/");
octave> cv0 = LeaveOneOutCV(X,y,fun_fisherface,fun_predict,1)
   129     1     0     0
</pre>

There are 129 correct predictions and only 1 false prediction, which is a recognition rate of 99%.

### subject-independent cross-validation ###

The results we got were very promising, but they are probably misleading. Have a look at the way a leave-one-out and k-fold cross-validation splits a Dataset ``D`` with 3 classes each with 3 observations:

<pre>
    o0 o1 o2        o0 o1 o2        o0 o1 o2  
c0 | A  B  B |  c0 | B  A  B |  c0 | B  B  A |
c1 | A  B  B |  c1 | B  A  B |  c1 | B  B  A |
c2 | A  B  B |  c2 | B  A  B |  c2 | B  B  A |
</pre>

Allthough the folds are not overlapping (training data is *never used* for testing) the training set contains images of persons we want to know the gender from. So the prediction may depend on the subject and the method finds the closest match to a persons image, but not the gender. What we aim for is a *split by class*:

<pre>
    o0 o1 o2        o0 o1 o2        o0 o1 o2  
c0 | A  A  A |  c0 | B  B  B |  c0 | B  B  B |
c1 | B  B  B |  c1 | A  A  A |  c1 | B  B  B |
c2 | B  B  B |  c2 | B  B  B |  c2 | A  A  A |
</pre>

With this strategy the cross-validation becomes *subject-independent*, because images of a subject are never used for learning the model. We restructure our folder hierarchy, so that it now reads: ``<group>/<subject>/<image>``:

<pre>
philipp@mango:~/facerec/data/gender$ tree .
.
|-- female
|   |-- crop_angelina_jolie
|   |   |-- crop_angelina_jolie_01.jpg
|   |   |-- crop_angelina_jolie_02.jpg
|   |   |-- crop_angelina_jolie_03.jpg
[...]
`-- male
    |-- crop_arnold_schwarzenegger
    |   |-- crop_arnold_schwarzenegger_01.jpg
    |   |-- crop_arnold_schwarzenegger_02.jpg
    |   |-- crop_arnold_schwarzenegger_03.jpg
[...]

15 directories, 130 files
</pre>

The function for reading the dataset needs to return both, the group and the subject of each observation. The cross-validation then predicts on the groups and leaves one subject out in each iteration. [read_images.m](https://github.com/bytefish/facerec/blob/master/m/util/read_images.m) can be easily extended to [read_groups.m](https://github.com/bytefish/facerec/blob/master/m/util/read_groups.m) and a simple [subject-independent cross-validation](https://github.com/bytefish/facerec/blob/master/m/validation/LeaveOneClassOutCV.m) is quickly written.

On a subject-independent cross-validation the Fisherfaces method is able to predict 128 out of 130 gender correctly, which is a recognition rate of 98%:

<pre>
octave> [X y g group_names subject_names width height] = read_groups("/home/philipp/facerec/data/gender/");
octave> cv0 = LeaveOneClassOutCV(X,y,g,fun_fisherface,fun_predict,1)
cv0 =

   128     2     0     0
</pre>

### Fisherface and Conclusion ###

Let's have a look at the features identified by the Discriminant Analysis. Since it's a binary classification, there's only one Fisherface. We'll plot it with:

```matlab
fisherface = fisherfaces(X,g);
fig = figure('visible','off');
imagesc(cvtGray(fisherface.W,width,height));
% remove offsets, set to pixels and scale accordingly
set(gca,'units','normalized','Position',[0 0 1 1]);
set(gcf,'units','pixels','position',[0 0 width height]);
print("-dpng",sprintf("-S%d,%d",width,height),"fisherface.png");
```

and the Fisherface reveals:

![Fisherface found for Gender Classification](/static/images/blog/gender_classification/fisherface.png)

Great surprise: it's the eyes and eyebrows the genders differ in... probably there's also a bit of mouth. We can conclude, that given a preprocessed face the Fisherfaces method can very accurately predict the gender of a given face. The recognition rate for a subject-independent cross-validation was 98.5%, which is only slightly below the 99.2% for a subject-dependent validation. 

Of course, the experimental results should be validated on larger datasets.
