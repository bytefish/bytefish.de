title: Longest Common Subsequence
date: 2010-08-09 17:37
tags: cpp
category: programming
slug: longest_common_subsequence
author: Philipp Wagner
summary: Longest Common Subsequence implementation in C++.

[Longest Common Subsequence (LCSS)](http://en.wikipedia.org/wiki/Longest_common_subsequence_problem) is another non-euclidean similarity measure for two timeseries, which may be useful on data with gaps. The 
[Time-Warped Longest Common Subsequence Algorithm For Music Retrieval](http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.101.6392) is included, because the implementation may be useful for others.

## tsutil.h ##

```cpp
#include <vector>

#ifndef TSUTIL_H
#define TSUTIL_H

namespace TimeSeries {
	double dtw(const std::vector<double>& t1, const std::vector<double>& t2);
	int lcs(const std::vector<double>& t1, const std::vector<double>& t2);
	int twlcs(const std::vector<double>& t1, const std::vector<double>& t2);
}

#endif
```

## tsutil.cpp ##

```cpp
#include <vector>
#include <utility>
#include <cmath>
#include "tsutil.h"

namespace TimeSeries {
	
	double dist(double x, double y) {
		return sqrt(pow((x - y), 2));
	}
	
	double dtw(const std::vector<double>& t1, const std::vector<double>& t2) {
		// ... see below.
	}

	int lcs(const std::vector<double>& t1, const std::vector<double>& t2) {
	
		int m = t1.size() + 1;
		int n = t2.size() + 1;

		// create cost matrix
		int cost[m][n];

		cost[0][0] = 0;

		// first row
		for(int i = 1; i < m; i++)
			cost[i][0] = 0;
		// first column
		for(int j = 1; j < n; j++)
			cost[0][j] = 0;


		for(int i = 1; i < m; i++) {
			for(int j = 1; j < n; j++) {
				 if(std::abs(t1[i-1] - t2[j-1]) <= 1e-10) {
					cost[i][j] = 1 + cost[i-1][j-1];
				} else {
					cost[i][j] = std::max(cost[i][j-1], cost[i-1][j]);
				}
			}
		}
	
		return cost[m-1][n-1];
	}
	
	int twlcs(const std::vector<double>& t1, const std::vector<double>& t2) {
	
		int m = t1.size() + 1;
		int n = t2.size() + 1;

		// create cost matrix
		int cost[m][n];

		cost[0][0] = 0;

		// first row
		for(int i = 1; i < m; i++)
			cost[i][0] = 0;
		// first column
		for(int j = 1; j < n; j++)
			cost[0][j] = 0;


		for(int i = 1; i < m; i++) {
			for(int j = 1; j < n; j++) {
				 if(std::abs(t1[i-1] - t2[j-1]) <= 1e-10) {
					cost[i][j] = 1 + std::max(cost[i][j-1],
						        std::max(cost[i-1][j], 
								cost[i-1][j-1]));
				} else {
					cost[i][j] = std::max(cost[i][j-1], 
							cost[i-1][j]);
				}
			}
		}
		
		return cost[m-1][n-1];
	}
	
}
```

## usage ##

```cpp
#include <vector>
#include <iostream>
#include "tsutil.h"

using namespace std;

int main() {

	vector<double> t1;
	vector<double> t2;

	/* some data */
	t1.push_back(4);
	/* ... */
	t2.push_back(7);
	/* ... */
	
	cout <<"lcs="<<TimeSeries::lcs(t1,t2) << endl; 
	cout <<"twlcs="<<TimeSeries::twlcs(t1,t2) << endl; 
}
```

## notes ##

You can obtain the sourcecode from my github page at:

* [http://github.com/bytefish/timeseries](http://github.com/bytefish/timeseries)
