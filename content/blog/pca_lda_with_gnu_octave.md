title: Principal Component Analysis and Linear Discriminant Analysis with GNU Octave
date: 2011-10-01 00:46
tags: octave, r
category: statistics
slug: pca_lda_with_gnu_octave
author: Philipp Wagner

# Principal Component Analysis and Linear Discriminant Analysis with GNU Octave #

This page will show you how to do a Principal Component and Linear Discriminant Analysis with [GNU Octave](http://www.gnu.org/software/octave), a high-level language and environment for numerical computing.

## Experiment 1 ##

### Data ###

Start GNU Octave from command line with:

<pre>
$ octave
</pre>

and create some data in ``X`` with corresponding classes in ``c``:

```matlab
X = [2 3;3 4;4 5;5 6;5 7;2 1;3 2;4 2;4 3;6 4;7 6];
c = [  1;  1;  1;  1;  1;  2;  2;  2;  2;  2;  2]; 
```

Find the indices of each class {1,2}:

```matlab
c1 = X(find(c==1),:)
c2 = X(find(c==2),:)
```

And then plot the data:

```matlab
figure;

p1 = plot(c1(:,1), c1(:,2), "ro", "markersize",10, "linewidth", 3); hold on;
p2 = plot(c2(:,1), c2(:,2), "go", "markersize",10, "linewidth", 3)

xlim([0 8])
ylim([0 8])
```

We can see that both classes can clearly be separated in one dimension:

<img src="/static/images/blog/pca_lda_with_gnu_octave/data.png" width="400" class="mediacenter" />

So how does a Principal Component Analysis perform on this dataset?

### Principal Component Analysis ###

The Principal Component Analysis (PCA) was independently proposed by [Karl Pearson](http://en.wikipedia.org/wiki/Karl_Pearson) (1901) and [Harold Hotelling](http://en.wikipedia.org/wiki/Harold_Hotelling) (1933) to turn a set of possibly correlated variables into a smaller set of uncorrelated variables. The idea is that a high-dimensional dataset is often described by correlated variables and therefore only a few meaningful dimensions account for most of the information. The PCA method finds those directions in the original dataset that account for the greatest variance in data, also called the principal components.

A good start is to read [A tutorial on Principal Components Analysis](http://www.cs.otago.ac.nz/cosc453/student_tutorials/principal_components.pdf) or [Wikipedia on PCA](http://en.wikipedia.org/wiki/Principal_component_analysis).

#### Finding the Principal Components ####

The math in the recommended documents can be reduced to these four lines of code:

```matlab
mu = mean(X)
Xm = bsxfun(@minus, X, mu)
C = cov(Xm)
[V,D] = eig(C)
```

That's it! Note that the Eigenvectors in GNU Octave are sorted ascending, so the last column is the first principal component. Strange to work with? So better sort the eigenvectors in a descending order:

```matlab
% sort eigenvectors desc
[D, i] = sort(diag(D), 'descend');
V = V(:,i);
```

Because all variables in this example are measured on the same scale we don't need to apply any standardization. Plotting both eigenvectors:

```matlab
scale = 5
pc1 = line([mu(1) - scale * V(1,1) mu(1) + scale * V(1,1)], [mu(2) - scale * V(2,1) mu(2) + scale * V(2,1)]);
pc2 = line([mu(1) - scale * V(1,2) mu(1) + scale * V(1,2)], [mu(2) - scale * V(2,2) mu(2) + scale * V(2,2)]);

set(pc1, 'color', [1 0 0], "linestyle", "--")
set(pc2, 'color', [0 1 0], "linestyle", "--")
```

yields a new coordinate system with the mean as origin and the orthogonal principal components as axes:

<img src="/static/images/blog/pca_lda_with_gnu_octave/principal.png" width="400" class="mediacenter" />

According to the PCA we can safely discard the second component, because the first principal component is responsible for 85% of the total variance.

<pre>
octave> cumsum(D) / sum(D)
ans =

   0.85471
   1.00000
</pre>

But what will happen if we project the data on the first principal component (red)? Do you already see the problem?

#### projection and reconstruction ####

To understand why the PCA fails in some situations, project the data onto the first principal component: 

```matlab
% project on pc1
z = Xm*V(:,1)
% and reconstruct it
p = z*V(:,1)'
p = bsxfun(@plus, p, mu)
```

and visualize it:

```matlab
% delete old plots
delete(p1);delete(p2);

y1 = p(find(c==1),:)
y2 = p(find(c==2),:)

p1 = plot(y1(:,1),y1(:,2),"ro", "markersize", 10, "linewidth", 3);
p2 = plot(y2(:,1), y2(:,2),"go", "markersize", 10, "linewidth", 3); 
```

... et voilà. The data isn't [linearly separable](http://en.wikipedia.org/wiki/Linear_separability) anymore in this lower-dimensional representation. What does this mean? The classes are smeared together and classification becomes tough:

<img src="/static/images/blog/pca_lda_with_gnu_octave/pc1.png" width="400" class="mediacenter" />

... while a projection on the second principal component yields a much better representation for classification:

<img src="/static/images/blog/pca_lda_with_gnu_octave/pc2.png" width="400" class="mediacenter" />

See that even a simple Nearest Neighbor classifier would perform awesome here? So we learn that the directions of maximum variance may be useless for classification tasks. The second principal component had a smaller variance, but provided a much better discrimination between the two classes. 

### Linear Discriminant Analysis ###

What we aim for is a projection, that maintains the maximum discriminative power of a given dataset, so a method should make use of class labels (if they are known a priori).  The Linear Discriminant Analysis, invented by [R. A. Fisher](http://en.wikipedia.org/wiki/Ronald_Fisher) (1936), does so by maximizing the between-class scatter, while minimizing the within-class scatter at the same time.

I took the equations from [Ricardo Gutierrez-Osuna's](http://research.cs.tamu.edu/prism/rgo.htm): [Lecture notes on Linear Discriminant Analysis](http://research.cs.tamu.edu/prism/lectures/pr/pr_l10.pdf) and [Wikipedia on LDA](http://en.wikipedia.org/wiki/Linear_discriminant_analysis).

We'll use the same data as for the PCA example. Again create the data in //X// with corresponding classes in //c//:

```matlab
X = [2 3;3 4;4 5;5 6;5 7;2 1;3 2;4 2;4 3;6 4;7 6];
c = [  1;  1;  1;  1;  1;  2;  2;  2;  2;  2;  2]; 
```

Again find the indices of each class {1,2}:

```matlab
c1 = X(find(c==1),:)
c2 = X(find(c==2),:)
```

And then plot the data:

```matlab
figure;

p1 = plot(c1(:,1), c1(:,2), "ro", "markersize",10, "linewidth", 3); hold on;
p2 = plot(c2(:,1), c2(:,2), "go", "markersize",10, "linewidth", 3)

xlim([0 8])
ylim([0 8])
```

So how does a Linear Discriminant Analysis perform on this dataset?

#### Finding the projection matrix ####

Finding the between and within-classes scatter matrices is easy for our two classes example:

```matlab
classes = max(c)
mu_total = mean(X)
mu = [ mean(c1); mean(c2) ]
Sw = (X - mu(c,:))'*(X - mu(c,:))
Sb = (ones(classes,1) * mu_total - mu)' * (ones(classes,1) * mu_total - mu)
```

The General Eigenvalue problem is now solved by simply doing:

```matlab
[V, D] = eig(Sw\Sb)
```

And that's it. Now let's see what separations the LDA method has found! Don't forget to first sort the Eigenvectors in a descending order:

```matlab
% sort eigenvectors desc
[D, i] = sort(diag(D), 'descend');
V = V(:,i);
```

and then plot them:

```matlab
scale = 5
pc1 = line([mu_total(1) - scale * V(1,1) mu_total(1) + scale * V(1,1)], [mu_total(2) - scale * V(2,1) mu_total(2) + scale * V(2,1)]);

set(pc1, 'color', [1 0 0], "linestyle", "--")
```

Let's look at the component found by the LDA:

<img src="/static/images/blog/pca_lda_with_gnu_octave/lda_components.png" width="400" class="mediacenter" />

Yeah! Perfect separation on the first component, that was what we were looking for!

#### projection and reconstruction ####

First shift the data to the new center:

```matlab
Xm = bsxfun(@minus, X, mu_total)
```

then calculate the projection and reconstruction:

```matlab
z = Xm*V(:,1)
% and reconstruct it
p = z*V(:,1)'
p = bsxfun(@plus, p, mu_total)
```

and now plotting it:

```matlab
% delete old plots
delete(p1);delete(p2);

y1 = p(find(c==1),:)
y2 = p(find(c==2),:)

p1 = plot(y1(:,1),y1(:,2),"ro", "markersize", 10, "linewidth", 3);
p2 = plot(y2(:,1), y2(:,2),"go", "markersize", 10, "linewidth", 3);
```

yields this beautiful plot:

<img src="/static/images/blog/pca_lda_with_gnu_octave/lda_pc1.png" width="400" class="mediacenter" />

## Experiment 2: Wine Dataset ##

The first experiment was somewhat constructed. Let's get our hands now on some real data from the [UCI Machine Learning Repository](http://archive.ics.uci.edu/ml/index.html)! I decided to test both methods on the [Wine Dataset](http://archive.ics.uci.edu/ml/datasets/Wine), an admittedly easy dataset. It consists of 178 samples with 13 constituents drawn from three types of wine.

### Functions ###

First of all we will turn the methods from the first experiment into functions to make them a bit more usable:

```matlab
function Z = zscore(X)
  Z = bsxfun(@rdivide, bsxfun(@minus, X, mean(X)), std(X));
end

function [D, W_pca] = pca(X) 
  mu = mean(X);
  Xm = bsxfun(@minus, X ,mu);
  C = cov(Xm);
  [W_pca,D] = eig(C);
  [D, i] = sort(diag(D), 'descend');
  W_pca = W_pca(:,i);
end

function [D, W_lda] = lda(X,y) 
  dimension = columns(X);
  labels = unique(y);
  C = length(labels);
  Sw = zeros(dimension,dimension);
  Sb = zeros(dimension,dimension);
  mu = mean(X);

  for i = 1:C
    Xi = X(find(y == labels(i)),:);
    n = rows(Xi);
    mu_i = mean(Xi);
    XMi = bsxfun(@minus, Xi, mu_i);
    Sw = Sw + (XMi' * XMi );
    MiM =  mu_i - mu;
    Sb = Sb + n * MiM' * MiM; 
  endfor
  
  [W_lda, D] = eig(Sw\Sb);
  [D, i] = sort(diag(D), 'descend');
  W_lda = W_lda(:,i);
end

function X_proj = project(X, W)
  X_proj = X*W;
end

function X = reconstruct(X_proj, W)
  X = X_proj * W';
end
```

### Loading the Wine Dataset ###

Loading the Wine Dataset is easy in GNU Octave with the //dlmread// function. I am sure there is something equivalent in MATLAB: 

```matlab
% http://archive.ics.uci.edu/ml/datasets/Wine
data = dlmread("wine.data",",");
y = data(:,1);
X = data(:,2:end);
</code>
Everything's ok?
<code>
> size(X)
ans =

   178    13

> size(y)
ans =

   178     1

> length(unique(y))
ans = 3
```

Everything was loaded correctly! 178 instances with 13 attributes from 3 classes.

### Principal Components without normalization ###

With the functions it's easy to perform a PCA:

```matlab
[DPca, Wpca] = pca(X);
Xm = bsxfun(@minus, X, mean(X));
Xproj = project(Xm, Wpca(:,1:2));
</code>
According to the eigenvalues, the first component already accounts for 99% of the total variance.
<code>
> cumsum(DPca) / sum(DPca)
ans =

   0.99809
   0.99983
   0.99992
   0.99997
   0.99998
   0.99999
   1.00000
   1.00000
   1.00000
   1.00000
   1.00000
   1.00000
   1.00000
```

But the plot

```matlab
wine1 = Xproj(find(y==1),:);
wine2 = Xproj(find(y==2),:);
wine3 = Xproj(find(y==3),:);

figure;
plot(wine1(:,1), wine1(:,2),"ro", "markersize", 10, "linewidth", 3); hold on;
plot(wine2(:,1), wine2(:,2),"go", "markersize", 10, "linewidth", 3);
plot(wine3(:,1), wine3(:,2),"bo", "markersize", 10, "linewidth", 3);
title("PCA (original data)")
```

shows that the clusters are not clearly separated

<img src="/static/images/blog/pca_lda_with_gnu_octave/pca_wine_original_data.png" width="400" class="mediacenter" />

### Linear Discriminant Analysis without normalization ###

If we apply Fisher's Discriminant Analysis on the Wine Dataset:

```matlab
[D, W_lda] = lda(X,y);
Xproj = project(Xm, W_lda(:,1:2));
```

and project it on the first two components, the classes are way better separated:

<img src="/static/images/blog/pca_lda_with_gnu_octave/lda_wine_original_data.png" width="400" class="mediacenter" />

### When normalization matters ###

The PCA performs bad. Why is that? Because the features are all on a different scale. A common trick is to scale the input to zero mean and unit variance, also called [[http://en.wikipedia.org/wiki/Standard_score|z-scores]]. If the normalization is applied on the data:

```matlab
Xm = zscore(X);
```

then the first principal component is responsible for only 36% of the total variance. We have to take 8 components to rise above 90% variance.

<pre>
> cumsum(DPca) / sum(DPca)
ans =

   0.36199
   0.55406
   0.66530
   0.73599
   0.80162
   0.85098
   0.89337
   0.92018
   0.94240
   0.96170
   0.97907
   0.99205
   1.00000
</pre>

On normalized data the clusters are better separated by the PCA:

<img src="/static/images/blog/pca_lda_with_gnu_octave/pca_wine_normalized_data.png" width="400" class="mediacenter" />

While the projection found by Fisher's Discriminant Analysis only changes in scale:

<img src="/static/images/blog/pca_lda_with_gnu_octave/lda_wine_normalized_data.png" width="400" class="mediacenter" />

## Relationship between a PCA and SVD ##

Something I didn't mention is the close relation between a [Singular Value Decomposition](http://en.wikipedia.org/wiki/Singular_value_decomposition) (SVD) and a Principle Component Analysis. A nice tutorial for the SVD is given [here](http://web.ics.purdue.edu/~park283/wp-content/uploads/2010/10/Singular_Value_Decomposition_Tutorial.pdf) and a real-life example with Ruby is given [here](http://www.igvita.com/2007/01/15/svd-recommendation-system-in-ruby/).

So let's decompose the data matrix:

```matlab
[U, S, V] = svd(Xm);
Xproj = project(Xm,V(:,1:2));
DSvd = diag(S).^2;
```

and you can compare yourself. The diagonal elements squared are the eigenvalues found by the PCA. We need to normalize both vectors first:

```matlab
function N = normalize(I, l, h)
    % set default values
    if(nargin < 3)
     l=0;
     h=1;
    endif 
    minI = min(I(:));
    maxI = max(I(:));
    %% normalize between [0...1]
    N = I - minI;
    N = N ./ (maxI - minI);
    %% scale between [l...h]
    N = N .* (h-l);
    N = N + l;
end
```

and then we can compare both:

<pre>
octave> all((normalize(DPca) - normalize(DSvd)) < eps)
ans = 1
</pre>

Where ``1`` is for ``true``.

## Appendix ##

### R ###

If you don't like GNU Octave for some reasons, you can also use [R](http://www.r-project.org) for the above examples. Please note that there is already the sophisticated function [princomp](http://stat.ethz.ch/R-manual/R-patched/library/stats/html/princomp.html) in R, so you shouldn't really do it by yourself. Anyway, here is the first example translated to R. Please note I am by no means an R expert:

```r
repmat <- function(data, nrows, ncols, byrow=T) {
  ncols <- length(data) * ncols
  rep <- matrix(rep(data, nrows), nrow=nrows, ncol=ncols, byrow=byrow)
  return(rep)
}

data <- c(2,3,3,4,4,5,5,6,5,7,2,1,3,2,4,2,4,3,6,4,7,6)
y <- c(1,1,1,1,1,2,2,2,2,2,2);
X <- matrix(data, ncol=2, byrow=T)
mean <- colMeans(X)
Xm <- X - repmat(mean, nrow(X), 1)
C <- cov(Xm)
eig <- eigen(C)

z <- Xm%*%eig$vectors[,1]
p <- z%*%eig$vectors[,1]
p <- p + repmat(mean, nrow(p), 1)

plot(p[y==1,], col="red", xlim=c(0,8), ylim=c(0,8))
points(p[y==2,], col="green")

title(main="PCA projection", xlab="X", ylab="Y")
```
