title: Dynamic Time Warping
date: 2010-08-04 00:55 
tags: c++
category: programming
slug: dynamic_time_warping
author: Philipp Wagner

# Dynamic Time Warping #

I've read about [Dynamic Time Warping](http://en.wikipedia.org/wiki/Dynamic_time_warping) yesterday and here is how I would do it in C++. [DTW](http://en.wikipedia.org/wiki/Dynamic_time_warping) is a distance measure for sequences that may vary in time or speed, like:

* Gestures ([/wiki/android](/wiki/android))
* Motion Patterns
* Sound signals in Speech or Music Recognition

A good introduction is given in:

* http://www.ailab.si/qr09/papers/Strle.pdf

## dtw.h ##

```cpp
#include <vector>

#ifndef DTW_H
#define DTW_H

namespace DTW {
	double dtw(const std::vector<double>& t1, const std::vector<double>& t2);
}

#endif
```

## dtw.cpp ##

```cpp
#include <vector>
#include <utility>
#include <cmath>
#include "dtw.h"

namespace DTW {
	
	double dist(double x, double y) {
		return sqrt(pow((x - y), 2));
	}
	
	double dtw(const std::vector<double>& t1, const std::vector<double>& t2) {
		int m = t1.size();
		int n = t2.size();

		// create cost matrix
		double cost[m][n];

		cost[0][0] = dist(t1[0], t2[0]);

		// calculate first row
		for(int i = 1; i < m; i++)
			cost[i][0] = cost[i-1][0] + dist(t1[i], t2[0]);
		// calculate first column
		for(int j = 1; j < n; j++)
			cost[0][j] = cost[0][j-1] + dist(t1[0], t2[j]);
		// fill matrix
		for(int i = 1; i < m; i++)
			for(int j = 1; j < n; j++)
				cost[i][j] = std::min(cost[i-1][j], std::min(cost[i][j-1], cost[i-1][j-1])) 
					+ dist(t1[i],t2[j]);
	
		return cost[m-1][n-1];
	}
}
```

## usage ##

```cpp
#include <vector>
#include <iostream>
#include "dtw.h"

using namespace std;

int main() {
    vector<double> t1;
    vector<double> t2;
    /* some data */
    t1.push_back(0.0);
    /* ... */
    t2.push_back(3.0);    
    /* ... */

    cout<< "dist_dtw=" << DTW::dtw(t1, t2) << endl;
}
```

## notes ##

You can obtain the sourcecode from my github page at:

* [http://github.com/bytefish/timeseries](http://github.com/bytefish/timeseries)

To find the minimum warp path between two sequences, you can use a greedy strategy from ``cost[m][n]`` to ``cost[0][0]`` by picking the minimum of the three adjacenct values. I leave this for your personal excercise. Some papers I have read divide the distance by the length of the warp path. This gives you the average distance between two points of the sequence, I doubt that this is useful in all cases, so I have left it out.
