title: Colormaps in OpenCV
date: 2011-11-25 12:23
tags: opencv, cpp
category: computer vision
slug: colormaps_in_opencv
author: Philipp Wagner
summary: Using colormaps with OpenCV.

## Introduction ##

Yesterday I needed to visualize some data in [OpenCV](http://opencv.org). It's easy to apply a colormap in [MATLAB](http://www.mathworks.de/index.html), but [OpenCV](http://opencv.org) doesn't 
come with predefined colormaps. So I simply took the interpolation steps from the [GNU Octave](http://www.gnu.org/software/octave/) colormaps and turned them into C++ classes. 

The source code is on:

* [https://codeberg.org/bytefish/colormaps-opencv](https://codeberg.org/bytefish/colormaps-opencv)

## Using the code ##

You only need ``cv::applyColorMap`` to apply a colormap on a given image. The signature of ``cv::applyColorMap`` is:

```cpp
void applyColorMap(InputArray src, OutputArray dst, int colormap)
```

The following code example reads an image (given as a command line argument), applies a Jet colormap on it and shows the result:

```cpp
#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include "colormap.hpp"

using namespace cv;

int main(int argc, const char *argv[]) {
    // Get the path to the image, if it was given
    // if no arguments were given.
    string filename;
    if (argc > 1) {
        filename = string(argv[1]);
    }
	// The following lines show how to apply a colormap on a given image
	// and show it with cv::imshow example with an image. An exception is
	// thrown if the path to the image is invalid.
	if(!filename.empty()) {
        Mat img0 = imread(filename);
        // Throw an exception, if the image can't be read:
        if(img0.empty()) {
            CV_Error(CV_StsBadArg, "Sample image is empty. Please adjust your path, so it points to a valid input image!");
        }
        // Holds the colormap version of the image:
        Mat cm_img0;
        // Apply the colormap:
        applyColorMap(img0, cm_img0, COLORMAP_JET);
        // Show the result:
        imshow("cm_img0", cm_img0);
        waitKey(0);
	}

	return 0;
}
```

The available colormaps are:

```cpp
enum
{
    COLORMAP_AUTUMN = 0,
    COLORMAP_BONE = 1,
    COLORMAP_JET = 2,
    COLORMAP_WINTER = 3,
    COLORMAP_RAINBOW = 4,
    COLORMAP_OCEAN = 5,
    COLORMAP_SUMMER = 6,
    COLORMAP_SPRING = 7,
    COLORMAP_COOL = 8,
    COLORMAP_HSV = 9,
    COLORMAP_PINK = 10,
    COLORMAP_HOT = 11
}
```

And here are the scales corresponding to each of the maps, so you know what they look like:

<table>
  <thead>
    <tr>
      <th>Name</th>
      <th>Scale</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>Autumn</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_autumn.jpg" alt="colorscale_autumn" /></td></tr>
    <tr><td>Bone</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_bone.jpg" alt="colorscale_bone" /></td></tr>
    <tr><td>Cool</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_cool.jpg" alt="colorscale_cool" /></td></tr>
    <tr><td>Hot</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_hot.jpg" alt="colorscale_hot" /></td></tr>
    <tr><td>HSV</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_hsv.jpg" alt="colorscale_hsv" /></td></tr>
    <tr><td>Jet</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_jet.jpg" alt="colorscale_jet" /></td></tr>
    <tr><td>Ocean</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_ocean.jpg" alt="colorscale_ocean" /></td></tr>
    <tr><td>Pink</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_pink.jpg" alt="colorscale_pink" /></td></tr>
    <tr><td>Rainbow</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_rainbow.jpg" alt="colorscale_rainbow" /></td></tr>
    <tr><td>Spring</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_spring.jpg" alt="colorscale_spring" /></td></tr>
    <tr><td>Summer</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_summer.jpg" alt="colorscale_summer" /></td></tr>
    <tr><td>Winter</td><td><img src="/static/images/blog/colormaps_in_opencv/colorscale_winter.jpg" alt="colorscale_winter" /></td></tr>
  </tbody>
</table>

##  Demo ##

The demo coming with the ``cv::applyColorMap`` shows how to use the colormaps and how I've created the scales you have seen:

* [https://codeberg.org/bytefish/colormaps-opencv/src/branch/master/src/main.cpp](https://codeberg.org/bytefish/colormaps-opencv/src/branch/master/src/main.cpp)

If you want to apply a Jet colormap on a given image, then call the demo with:

```sh
./cm_demo /path/to/your/image.ext
```

Or if you just want to generate the color scales, then call the demo with:

```sh
./cm_demo
```

Note: Replace ``./cm_demo`` with ``cm_demo.exe`` if you are running Windows!

###  Building the demo ###

The project comes as a CMake project, so building it is as simple as:

```
philipp@mango:~/some/dir/colormaps-opencv$ mkdir build
philipp@mango:~/some/dir/colormaps-opencv$ cd build
philipp@mango:~/some/dir/colormaps-opencv/build$ cmake ..
philipp@mango:~/some/dir/colormaps-opencv/build$ make
philipp@mango:~/some/dir/colormaps-opencv/build$ ./cm_demo path/to/your/image.ext
```

Or if you use MinGW on Windows:

```
C:\some\dir\colormaps-opencv> mkdir build
C:\some\dir\colormaps-opencv> cd build
C:\some\dir\colormaps-opencv\build> cmake -G "MinGW Makefiles" ..
C:\some\dir\colormaps-opencv\build> mingw32-make
C:\some\dir\colormaps-opencv\build> cm_demo.exe /path/to/your/image.ext
```

Or if you are using Visual Studio, you can generate yourself a solution like this (please adjust to your version):

```
C:\some\dir\colormaps-opencv> mkdir build
C:\some\dir\colormaps-opencv> cd build
C:\some\dir\colormaps-opencv\build> cmake -G "Visual Studio 9 2008" ..
```
