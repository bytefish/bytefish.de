title: OpenCV Code Snippets
date: 2011-10-28 17:13
tags: opencv, cpp
category: computer vision
slug: opencv/code_snippets
author: Philipp Wagner

# OpenCV Code Snippets #

## Datatypes ##

The OpenCV matrices ``CvMat`` and ``cv::Mat`` have their own type system:

<table>
  <tr><th>OpenCV</th><th>Datatype</th></tr> 
  <tr><td>CV_8S</td><td>char</td></tr>
  <tr><td>CV_8U</td><td>unsigned char</td></tr>
  <tr><td>CV_16S</td><td>short</td></tr>
  <tr><td>CV_16U</td><td>unsigned short</td></tr>
  <tr><td>CV_32S</td><td>int</td></tr>
  <tr><td>CV_32F</td><td>float</td></tr>
  <tr><td>CV_64F</td><td>double</td></tr>
</table>

It's kind of awkward to remember all the types and even worse, there's no type-checking at compile time. So the recent OpenCV2 introduced the templated matrix ``cv::Mat_<_Tp>``. Now imagine we are writing a highly simple function, where we want to print a matrix. 

With a ``cv::Mat_`` we can use the advantadges of templates:

```cpp
#include <cv.h>
#include <iostream>

using namespace cv;
using namespace std;

template <typename _Tp>
void printMat(const cv::Mat_<_Tp>& mat) {
	typedef typename DataType<_Tp>::work_type _wTp;
	for(int i = 0; i < mat.rows; i++)
		for(int j=0; j < mat.cols; j++)
			cout << (_wTp) mat(i,j) << " ";
	cout << endl;
}

void printMat(const cv::Mat& mat) {
	for(int i = 0; i < mat.rows; i++)
		for(int j=0; j < mat.cols; j++)
			cout << (int) mat.at<unsigned char>(i,j) << " ";
	cout << endl;
}

int main(int argc, const char *argv[]) {

	unsigned char a[] = {0,1,2,3,4,5,6,7,8};
	Mat_<unsigned char> d0 = cv::Mat_<unsigned char>(9,1,a).clone();
	Mat d1 = cv::Mat(9,1,CV_8UC1,a).clone();
	cout << "d0: ";
	printMat(d0);
	cout << "d1: ";
	printMat(d1);
}
```

If you run the the program you'll get:

<pre>
d0: 0 1 2 3 4 5 6 7 8 
d1: 0 1 2 3 4 5 6 7 8 
</pre>

But what happens if I now choose integers instead?

```cpp
int main(int argc, const char *argv[]) {

	int a[] = {255,256,257,258,259,260,261,262,263};
	Mat_<int> d0 = cv::Mat_<int>(9,1,a).clone();
	Mat d1 = cv::Mat(9,1,CV_32SC1,a).clone();
	cout << "d0: ";
	printMat(d0);
	cout << "d1: ";
	printMat(d1);
}
```

If I now run the function, you'll see where it fails... The element access to the ``cv::Mat`` with ``unsigned char`` will truncate the result:

<pre>
d0: 255 256 257 258 259 260 261 262 263 
d1: 255 0 1 2 3 4 5 6 7 
</pre>

So the first function stays unchanged, because of using templates, while ``printMat(const cv::Mat& mat)`` has to be changed to:

```cpp
void printMat(const cv::Mat& mat) {
	for(int i = 0; i < mat.rows; i++)
		for(int j=0; j < mat.cols; j++)
			cout << mat.at<int>(i,j) << " ";
	cout << endl;
}
```

For old code I write my methods in such a way:

```cpp
template <typename _Tp>
void histogram(const cv::Mat& input, cv::Mat& hist, int N) {
  hist = cv::Mat::zeros(1, N, CV_32SC1);
  for(int i = 0; i < input.rows; i++) {
    for(int j = 0; j < input.cols; j++) {
      int bin = input.at<_Tp>(i,j);
      hist.at<int>(0,bin) += 1;
    }
  }
}

void histogram(const cv::Mat& input, cv::Mat& hist, int N) {
  if(input.type() != CV_8SC1 && input.type() && CV_8UC1 && input.type() != CV_16SC1
			&& input.type() != CV_16UC1	&& input.type() != CV_32SC1)
  {
    CV_Error(CV_StsUnsupportedFormat, "Only Integer data is supported.");
    lf::logging::error("wrong type for histogram.");
  }

  switch(input.type()) {
    case CV_8SC1: histogram<char>(input, hist, N); break;
    case CV_8UC1: histogram<unsigned char>(input, hist, N); break;
    case CV_16SC1: histogram<short>(input, hist, N); break;
    case CV_16UC1: histogram<unsigned short>(input, hist, N); break;
    case CV_32SC1: histogram<int>(input, hist, N); break;
  }
}
```

## General Matrix Multiplication ##

In Octave:

```octave
octave:1> A = [1 2;3 4]
A =

   1   2
   3   4

octave:2> B = [5 6;7 8]
B =

   5   6
   7   8

octave:3> C = [9 10;11 12]
C =

    9   10
   11   12

octave:4> A*B
ans =

   19   22
   43   50

octave:5> A'*B
ans =

   26   30
   38   44

octave:6> A'*B'
ans =

   23   31
   34   46

octave:7> alpha=2
alpha =  2
octave:8> A*B+alpha*C
ans =

   37   42
   65   74
```

In OpenCV2 this translates to:

```cpp
#include <cv.h>
#include <iostream>

int main(int argc, const char *argv[]) {

	float a[] = {1.0, 2.0, 3.0, 4.0};
	float b[] = {5.0, 6.0, 7.0, 8.0};
	float c[] = {9.0, 10.0, 11.0, 12.0};

	cv::Mat A = cv::Mat(2,2,CV_32FC1,a).clone();
	cv::Mat B = cv::Mat(2,2,CV_32FC1, b).clone();
	cv::Mat C = cv::Mat(2,2,CV_32FC1, c).clone();;
	cv::Mat D; // result
	// D = A*B
	cv::gemm(A, B, 1.0, cv::Mat(), 0.0, D);
	std::cout << D << std::endl;
	// D = A^T*B
	cv::gemm(A, B, 1.0, cv::Mat(), 0.0, D, CV_GEMM_A_T);
	std::cout << D << std::endl;
	// D = A^T * B^T
	cv::gemm(A, B, 1.0, cv::Mat(), 0.0, D, CV_GEMM_A_T + CV_GEMM_B_T);
	std::cout << D << std::endl;
	// D = A*B+alpha*C
	float alpha = 2.0;
	cv::gemm(A, B, 1.0, C, alpha, D);
	std::cout << D << std::endl;

	return 0;
}
```
