title: Dynamic Time Warping
date: 2010-08-04 00:55 
tags: cpp
category: programming
slug: dynamic_time_warping
author: Philipp Wagner
summary: Source code for calculating the Dynamic Time Warping distance in C++.

I've read about [Dynamic Time Warping](http://en.wikipedia.org/wiki/Dynamic_time_warping) yesterday and here is how I would do it in C++. 

## TimeSeriesUtils.hpp ##

```cpp
#ifndef TSUTIL_H
#define TSUTIL_H

#include <vector>
#include <cstdint>

namespace TimeSeriesUtils {
	
	double CalculateEuclideanDistance(double x, double y);

	double CalculateDynamicTimeWarpedDistance(std::vector<double> t0, std::vector<double> t1);
	
	int CalculateLongestCommonSubsequence(std::vector<double> t0, std::vector<double> t1);
	
	int CalculateTimeWarpedLongestCommonSubsequence(std::vector<double> t0, std::vector<double> t1);

}

#endif

```

## TimeSeriesUtils.cpp ##

```cpp
#include <vector>
#include <algorithm>
#include "../include/TimeSeriesUtils.hpp"

namespace TimeSeriesUtils {

	double CalculateEuclideanDistance(double x, double y) {
		return std::sqrt(std::pow((x - y), 2));
	}	

	double CalculateDynamicTimeWarpedDistance(std::vector<double> t0, std::vector<double> t1) {
		
		size_t m = t0.size();
		size_t n = t1.size();

		// Allocate the Matrix to work on:
		std::vector<std::vector<double>> cost(m, std::vector<double>(n));

		cost[0][0] = CalculateEuclideanDistance(t0[0], t1[0]);

		// Calculate the first row:
		for (int i = 1; i < m; i++) {
			cost[i][0] = cost[i - 1][0] + CalculateEuclideanDistance(t0[i], t1[0]);
		}

		// Calculate the first column:
		for (int j = 1; j < n; j++) {
			cost[0][j] = cost[0][j - 1] + CalculateEuclideanDistance(t0[0], t1[j]);
		}

		// Fill the matrix:
		for (int i = 1; i < m; i++) {
			for (int j = 1; j < n; j++) {
				cost[i][j] = std::min(cost[i - 1][j], std::min(cost[i][j - 1], cost[i - 1][j - 1])) 
					+ CalculateEuclideanDistance(t0[i], t1[j]);
			}
		}
	
		return cost[m-1][n-1];
	}

	int CalculateLongestCommonSubsequence(std::vector<double> t0, std::vector<double> t1) {
	
		size_t m = t0.size() + 1;
		size_t n = t1.size() + 1;

		// Allocate the Matrix to work on:
		std::vector<std::vector<int>> cost(m, std::vector<int>(n));

		cost[0][0] = 0;

		// Calculate the first row:
		for (int i = 1; i < m; i++) {
			cost[i][0] = 0;
		}

		// Calculate the first column:
		for (int j = 1; j < n; j++) {
			cost[0][j] = 0;
		}


		for(int i = 1; i < m; i++) {
			for(int j = 1; j < n; j++) {
				 if(std::abs(t0[i-1] - t1[j-1]) <= 1e-10) {
					cost[i][j] = 1 + cost[i-1][j-1];
				} else {
					cost[i][j] = std::max(cost[i][j-1], cost[i-1][j]);
				}
			}
		}
	
		return cost[m-1][n-1];
	}
	
	int CalculateTimeWarpedLongestCommonSubsequence(std::vector<double> t0, std::vector<double> t1) {
	
		size_t m = t0.size() + 1;
		size_t n = t1.size() + 1;

		// Allocate the Matrix to work on:
		std::vector<std::vector<int>> cost(m, std::vector<int>(n));

		cost[0][0] = 0;

		// Calculate the first row:
		for (int i = 1; i < m; i++) {
			cost[i][0] = 0;
		}

		// Calculate the first column:
		for (int j = 1; j < n; j++) {
			cost[0][j] = 0;
		}


		for(int i = 1; i < m; i++) {
			for(int j = 1; j < n; j++) {
				 if(std::abs(t0[i-1] - t1[j-1]) <= 1e-10) {
					cost[i][j] = 1 + std::max(cost[i][j-1], std::max(cost[i-1][j],  cost[i-1][j-1]));
				} else {
					cost[i][j] = std::max(cost[i][j-1], cost[i-1][j]);
				}
			}
		}
		
		return cost[m-1][n-1];
	}
}
```

## usage ##

```cpp
#include "../include/TimeSeriesUtils.hpp"
#include <vector>
#include <cstdint>
#include <catch.hpp>

namespace {

	TEST_CASE("DynamicTimeWarpedDistanceTest")
	{
		std::vector<double> timeSeries0;
		std::vector<double> timeSeries1;

		timeSeries0.push_back(4);
		timeSeries0.push_back(4);
		timeSeries0.push_back(5);
		timeSeries0.push_back(5);
		timeSeries0.push_back(6);
		timeSeries0.push_back(6);
		timeSeries0.push_back(7);
		timeSeries0.push_back(7);

		timeSeries1.push_back(23);
		timeSeries1.push_back(4);
		timeSeries1.push_back(5);
		timeSeries1.push_back(6);
		timeSeries1.push_back(7);

		double result = TimeSeriesUtils::CalculateDynamicTimeWarpedDistance(timeSeries0, timeSeries1);

		REQUIRE(result == Approx(19).epsilon(0.01));
	}

	TEST_CASE("LongestCommonSubsequenceTest")
	{
		std::vector<double> timeSeries0;
		std::vector<double> timeSeries1;

		timeSeries0.push_back(4);
		timeSeries0.push_back(4);
		timeSeries0.push_back(5);
		timeSeries0.push_back(5);
		timeSeries0.push_back(6);
		timeSeries0.push_back(6);
		timeSeries0.push_back(7);
		timeSeries0.push_back(7);

		timeSeries1.push_back(4);
		timeSeries1.push_back(5);
		timeSeries1.push_back(6);
		timeSeries1.push_back(7);

		int result = TimeSeriesUtils::CalculateLongestCommonSubsequence(timeSeries0, timeSeries1);

		REQUIRE(result == 4);
	}
}
```