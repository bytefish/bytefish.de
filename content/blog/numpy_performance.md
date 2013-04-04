title: NumPy Performance
date: 2011/10/09 15:10
tags: python, numpy
category: programming
slug: numpy_performance
author: Philipp Wagner

# NumPy Performance #

It's always important to perform calculations as fast as you can. That's why performance intensive code is often ported to C or even down to Assembler. Here's an example for performance computing in [NumPy](http://www.scipy.org). In my code I wanted to compute the [Local Binary Patterns](http://www.scholarpedia.org/article/Local_Binary_Patterns) of 165 images each sized ``100x130`` pixels. So the first naive version I came up with looked like this:

```python
def rlbp_slow(X):
	X = np.asarray(X)
	ysize, xsize = X.shape
	result = np.zeros((ysize-2,xsize-2), dtype=np.uint8)
	for y in range(1, ysize-1):
		for x in range(1, xsize-1):
				center = X[y,x]
				code = 0
				code |= (X[y-1,x-1] >= center) << 7
				code |= (X[y-1,x] >= center) << 6
				code |= (X[y-1,x+1] >= center) << 5
				code |= (X[y,x+1] >= center) << 4
				code |= (X[y+1,x+1] >= center) << 3
				code |= (X[y+1,x] >= center) << 2
				code |= (X[y+1,x-1] >= center) << 1
				code |= (X[y,x-1] >= center) << 0
				result[y-1,x-1] = code
	return result
```

You already see the problem... The ``for`` loop over the pixels will be unbelievably slow in [Python](http://www.python.org), but hey I am optimistic. A Dual Core at 2.3 GHz, just throw some more cycles at it -- I don't mind the milliseconds! How long could it take?

```python
# [...]
	from time import time
	t0 = time()
	for i in range(0,X.shape[1]):
		rlbp_slow(X[:,i].reshape(self.height, self.width))
	self.logger.debug("time to compute patterns took=%.6f seconds" % (time()-t0))
# [...]
```

Forever. 185 seconds. 3 minutes. Lightyears away from realtime:

<pre>
2011-09-30 14:12:39,811 - facerec.models.LBP - DEBUG - time to compute patterns took=185.088027 seconds
</pre>

Yes... Realtime really get's hard with this. This code is executed in Python and due to checking array bounds (and so on) for each call it get's unbelievably slow; I should really port this to C. But if you think another second about it you will probably recognize that you can perform this calculation by only using ``X``: Take the inner matrix of X as the center values and compare it with the equally sized matrix at a (-1,-1) offset. Multiply the result with ``2^7`` and you are done for the first neighbor. Now take the matrix at a (-1,0) offset, multiply with ``2^6`` and add it... You see where this leads to. 

Is this useful in NumPy? Yes it is, because [now the computations are performed in C](http://www.scipy.org/PerformancePython). 

Let's see what it looks like:

```python
def rlbp_fast(X):
	X = (1<<7) * (X[0:-2,0:-2] >= X[1:-1,1:-1]) \
		+ (1<<6) * (X[0:-2,1:-1] >= X[1:-1,1:-1]) \
		+ (1<<5) * (X[0:-2,2:] >= X[1:-1,1:-1]) \
		+ (1<<4) * (X[1:-1,2:] >= X[1:-1,1:-1]) \
		+ (1<<3) * (X[2:,2:] >= X[1:-1,1:-1]) \
		+ (1<<2) * (X[2:,1:-1] >= X[1:-1,1:-1]) \
		+ (1<<1) * (X[2:,:-2] >= X[1:-1,1:-1]) \
		+ (1<<0) * (X[1:-1,:-2] >= X[1:-1,1:-1])
	return X
```

This code yields the same result and needs //0.27// seconds to complete:

<pre>
2011-09-30 14:29:40,337 - facerec.models.LBP - DEBUG - time to compute patterns took=0.269666 seconds
</pre>

By vectorizing the code we can use the [[http://www.scholarpedia.org/article/Local_Binary_Patterns|Local Binary Patterns]] without going to C and stay with our familiar NumPy syntax.

We can still do faster with the tools NumPy and SciPy have. **Beware!** Things get a little bit tough to debug from here on. By using [scipy.weave](http://docs.scipy.org/doc/scipy/reference/tutorial/weave.html) you can either use [weave.blitz](http://docs.scipy.org/doc/scipy/reference/tutorial/weave.html) or [weave.inline](http://docs.scipy.org/doc/scipy/reference/tutorial/weave.html) to weave C/C++ code into your program. Our code is rather easy for [blitz](http://www.oonumerics.org/blitz), because it only has to translate our NumPy ranges into ``blitz::Range`` objects:

```python
from scipy import weave

def rlbp_fast_blitz(X):
	X = np.asarray(X) # blitz otherwise doesn't know the type
	Y = np.zeros(((X.shape[0]-2), (X.shape[1]-2)), dtype=np.uint8) # and we don't want to override X
	arg_dict={'X':X, 'Y':Y} # variables C++ has to know about
	expr = "Y = (1<<7) * (X[0:-2,0:-2] >= X[1:-1,1:-1])	\
		+ (1<<6) * (X[0:-2,1:-1] >= X[1:-1,1:-1])	\
		+ (1<<5) * (X[0:-2,2:] >= X[1:-1,1:-1])	\
		+ (1<<4) * (X[1:-1,2:] >= X[1:-1,1:-1]) \
		+ (1<<3) * (X[2:,2:] >= X[1:-1,1:-1]) \
		+ (1<<2) * (X[2:,1:-1] >= X[1:-1,1:-1])	\
		+ (1<<1) * (X[2:,:-2] >= X[1:-1,1:-1]) \
		+ (1<<0) * (X[1:-1,:-2] >= X[1:-1,1:-1])"
	weave.blitz(expr, arg_dict, check_size=0)
	return Y
```

When you run the program for the first time it gets translated and compiled. The generated C++ code looks familiar (I am not pasting the whole thing here):

```cpp
// ...
Y=(1<<7)*(X(blitz::Range(0,NX(0)-2-1),blitz::Range(0,NX(1)-2-1))>=X(blitz::Range(1,NX(0)-1-1),blitz::Range(1,NX(1)-1-1)))+(1<<6)*[...]
// ...
```

Translating and compiling takes some time, so the first call now takes 4.2 seconds to execute:

<pre>
2011-09-30 14:49:17,483 - facerec.models.LBP - DEBUG - time to compute patterns took=4.170938 seconds
</pre>

But the second call only takes **0.05** seconds to finish:

<pre>
2011-09-30 14:50:19,677 - facerec.models.LBP - DEBUG - time to compute patterns took=0.052150 seconds
</pre>

Sometimes the blitz syntax is not expressive enough, so you want to fall back to standard C/C++. You can write inline C++ with the [weave.inline](http://docs.scipy.org/doc/scipy/reference/tutorial/weave.html) module. The code is first embedded into a C++ file (with all the macros) and is then compiled. 

Let's see how my very naive attempt performs in C++:

```python
def rlbp_fast_inline(X):
	X = np.asarray(X)
	Y = np.zeros(((X.shape[0]-2), (X.shape[1]-2)), dtype=np.uint8) # allocate some space
	expr = """
	int i,j;
	for(i=1;i<NX[0]-1;i++) {
		for(j=1;j<NX[1]-1;j++) {
			int center = X2(i,j);
			int code = 0;
			code |= (X2(i-1,j-1) >= center) << 7;
			code |= (X2(i-1,j) >= center) << 6;
			code |= (X2(i-1,j+1) >= center) << 5;
			code |= (X2(i,j+1) >= center) << 4;
			code |= (X2(i+1,j+1) >= center) << 3;
			code |= (X2(i+1,j) >= center) << 2;
			code |= (X2(i+1,j-1) >= center) << 1;
			code |= (X2(i,j-1) >= center) << 0;
			Y2(i-1,j-1) = code;
		}
	}
	"""
	weave.inline(expr, ['X', 'Y'])
	return Y
```

I'll explain this code a bit. Don't think you've missed something! The ``NX``, ``X2``, ``Y2`` variables are macros created by scipy.weave to make your life easier. ``NX`` has the information about the shape of ``X``; ``X2`` is a macro that allows 2-dimensional indexing.

Now in C++ my naive attempt only takes //0.07// seconds:

<pre>
2011-09-30 15:28:17,026 - facerec.models.LBP - DEBUG - time to compute patterns took=0.069170 seconds
</pre>

This is just a little slower compared to the code generated by the [weave.blitz](http://docs.scipy.org/doc/scipy/reference/tutorial/weave.html) module. 

Finally make sure that all functions calculate the same (you should come up with something more sophisticated):

```python
import numpy as np

X = np.asarray(np.random.rand(100,100)*255, dtype=np.uint8)
ts = np.sum(rlbp_slow(X)) \
	== np.sum(rlbp_fast(X)) \
	== np.sum(rlbp_fast_blitz(X)) \
	== np.sum(rlbp_fast_inline(X))

if ts:
	print "Test succeeded."
else:
	print "Test failed."
```

Do all functions calculate the same?

<pre>
philipp@mango:~/github$ python rlbp.py
Test succeeded.
</pre>

They do. Hooray!

## Conclusion ##

So you saw that we could speed up our code from 185 seconds to **0.05** seconds. That's one of the reasons why C, C++ and Fortran aren't dead, because they are blazingly fast at some tasks. It's great that NumPy allows to inline C++ code that easy. For more complex tasks you should research for tools like [Cython](http://cython.org), because it's probably easier (and better supported) to interface with external C/C++ code from Python -- at least the documentation suggests it.
