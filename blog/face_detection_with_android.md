title: Face Detection with Android
date: 2014-08-02 12:23
tags: android, java, face detection
category: android, computer vision
slug: face_detection_with_android
author: Philipp Wagner
summary: Face Detection with the Android Camera.

# Face Detection with the Android API #

In this post I want to show you how to work with the [Android Camera API](http://developer.android.com/reference/android/hardware/Camera.html) to implement an app for Face Detection. 
The final app will draw an overlay on the camera image, which will highlight the detected faces. Basically the application only consists of an Activity and a custom view. The functions 
for calculating the correct display orientation have been taken from Androids original Camera App, which is released under terms of the Apache License, Version 2.0.

Here is a screenshot of the final application:

<img src="/static/images/blog/face_detection_with_android/face_detection_with_android_app.jpg" class="mediacenter" alt="face_detection_with_android_app.jpg" />

I am sure you will come up with a lot of cool ideas to extend the app!

You can find a full [Android Studio](https://developer.android.com/sdk/installing/studio.html) project with the source code at:

* [https://github.com/bytefish/facerec/tree/master/android/VideoFaceDetection](https://github.com/bytefish/facerec/tree/master/android/VideoFaceDetection)

## Manifest.xml ##

In order to use the Camera, we need to add the ``uses-permission`` for the Camera to the [App Manifest](http://developer.android.com/guide/topics/manifest/manifest-intro.html). The App Manifest is located in the source folder of your project as ``AndroidManifest.xml``. If you are unsure where to put it, then just have a look at the [AndroidManifest.xml](https://github.com/bytefish/facerec/blob/master/android/VideoFaceDetection/app/src/main/AndroidManifest.xml) of the GitHub project coming with this blog post.

The only ``uses-permission`` you need to add is:

```xml
<uses-permission android:name="android.permission.CAMERA"/>
```

## CameraActivity ##

### Description ###

First of all I would like to point out, that the Android documentation comes with a great guide for working with Camera API:

* [http://developer.android.com/guide/topics/media/camera.html](http://developer.android.com/guide/topics/media/camera.html)

With the help of the guide you will learn how to open the camera, how to draw the preview frames, how to setup the [FaceDetectionListener](http://developer.android.com/reference/android/hardware/Camera.FaceDetectionListener.html) and work with its results.

The ``CameraActivity`` for the sample app is the entry point for our application. It is responsible for controlling the camera, drawing the preview frames and implementing the [FaceDetectionListener](http://developer.android.com/reference/android/hardware/Camera.FaceDetectionListener.html). It also keeps track of the current display orientation, so we can rotate the [FaceDetectionListener](http://developer.android.com/reference/android/hardware/Camera.FaceDetectionListener.html) results according to the current phone orientation.

### Source Code ###

```java
public class CameraActivity extends Activity
        implements SurfaceHolder.Callback {

    public static final String TAG = CameraActivity.class.getSimpleName();

    private Camera mCamera;

    // We need the phone orientation to correctly draw the overlay:
    private int mOrientation;
    private int mOrientationCompensation;
    private OrientationEventListener mOrientationEventListener;

    // Let's keep track of the display rotation and orientation also:
    private int mDisplayRotation;
    private int mDisplayOrientation;

    // Holds the Face Detection result:
    private Camera.Face[] mFaces;

    // The surface view for the camera data
    private SurfaceView mView;

    // Draw rectangles and other fancy stuff:
    private FaceOverlayView mFaceView;

    /**
     * Sets the faces for the overlay view, so it can be updated
     * and the face overlays will be drawn again.
     */
    private FaceDetectionListener faceDetectionListener = new FaceDetectionListener() {
        @Override
        public void onFaceDetection(Face[] faces, Camera camera) {
            Log.d("onFaceDetection", "Number of Faces:" + faces.length);
            // Update the view now!
            mFaceView.setFaces(faces);
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mView = new SurfaceView(this);

        setContentView(mView);
        // Now create the OverlayView:
        mFaceView = new FaceOverlayView(this);
        addContentView(mFaceView, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
        // Create and Start the OrientationListener:
        mOrientationEventListener = new SimpleOrientationEventListener(this);
        mOrientationEventListener.enable();
    }

    @Override
    protected void onPostCreate(Bundle savedInstanceState) {
        super.onPostCreate(savedInstanceState);
        SurfaceHolder holder = mView.getHolder();
        holder.addCallback(this);
    }

    @Override
    protected void onPause() {
        mOrientationEventListener.disable();
        super.onPause();
    }

    @Override
    protected void onResume() {
        mOrientationEventListener.enable();
        super.onResume();
    }

    @Override
    public void surfaceCreated(SurfaceHolder surfaceHolder) {
        mCamera = Camera.open();
        mCamera.setFaceDetectionListener(faceDetectionListener);
        mCamera.startFaceDetection();
        try {
            mCamera.setPreviewDisplay(surfaceHolder);
        } catch (Exception e) {
            Log.e(TAG, "Could not preview the image.", e);
        }
    }


    @Override
    public void surfaceChanged(SurfaceHolder surfaceHolder, int i, int i2, int i3) {
        // We have no surface, return immediately:
        if (surfaceHolder.getSurface() == null) {
            return;
        }
        // Try to stop the current preview:
        try {
            mCamera.stopPreview();
        } catch (Exception e) {
            // Ignore...
        }
        // Get the supported preview sizes:
        Camera.Parameters parameters = mCamera.getParameters();
        List<Camera.Size> previewSizes = parameters.getSupportedPreviewSizes();
        Camera.Size previewSize = previewSizes.get(0);
        // And set them:
        parameters.setPreviewSize(previewSize.width, previewSize.height);
        mCamera.setParameters(parameters);
        // Now set the display orientation for the camera. Can we do this differently?
        mDisplayRotation = Util.getDisplayRotation(CameraActivity.this);
        mDisplayOrientation = Util.getDisplayOrientation(mDisplayRotation, 0);
        mCamera.setDisplayOrientation(mDisplayOrientation);
		
        if (mFaceView != null) {
            mFaceView.setDisplayOrientation(mDisplayOrientation);
        }

        // Finally start the camera preview again:
        mCamera.startPreview();
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder surfaceHolder) {
        mCamera.setPreviewCallback(null);
        mCamera.setFaceDetectionListener(null);
        mCamera.setErrorCallback(null);
        mCamera.release();
        mCamera = null;
    }

    /**
     * We need to react on OrientationEvents to rotate the screen and
     * update the views.
     */
    private class SimpleOrientationEventListener extends OrientationEventListener {

        public SimpleOrientationEventListener(Context context) {
            super(context, SensorManager.SENSOR_DELAY_NORMAL);
        }

        @Override
        public void onOrientationChanged(int orientation) {
            // We keep the last known orientation. So if the user first orient
            // the camera then point the camera to floor or sky, we still have
            // the correct orientation.
            if (orientation == ORIENTATION_UNKNOWN) return;
            mOrientation = Util.roundOrientation(orientation, mOrientation);
            // When the screen is unlocked, display rotation may change. Always
            // calculate the up-to-date orientationCompensation.
            int orientationCompensation = mOrientation
                    + Util.getDisplayRotation(CameraActivity.this);
            if (mOrientationCompensation != orientationCompensation) {
                mOrientationCompensation = orientationCompensation;
                mFaceView.setOrientation(mOrientationCompensation);
            }
        }
    }
}
```

## FaceOverlayView ##

### Description ###

The FaceOverlayView is responsible for drawing the detection results on top of the camera preview. 

The camera returns you coordinates in a range of ``(-1000,1000)``, so we need to map them to the coordinates of the View (see the Android Camera Guide on [metering and focus area](http://developer.android.com/guide/topics/media/camera.html#metering-focus-areas)). And it's important to keep in mind, that what the user sees is not necessarily what the camera sensor sees! So the function ``prepareMatrix(Matrix matrix, boolean mirror, int displayOrientation, int viewWidth, int viewHeight)`` also takes the current display rotation into account, so that the coordinates are normalized, translated to the views origin and rotated by the current display orientation.

### Source Code ###

```java
/**
 * This class is a simple View to display the faces.
 */
public class FaceOverlayView extends View {

    private Paint mPaint;
    private Paint mTextPaint;
    private int mDisplayOrientation;
    private int mOrientation;
    private Face[] mFaces;

    public FaceOverlayView(Context context) {
        super(context);
        initialize();
    }

    private void initialize() {
        // We want a green box around the face:
        mPaint = new Paint();
        mPaint.setAntiAlias(true);
        mPaint.setDither(true);
        mPaint.setColor(Color.GREEN);
        mPaint.setAlpha(128);
        mPaint.setStyle(Paint.Style.FILL_AND_STROKE);

        mTextPaint = new Paint();
        mTextPaint.setAntiAlias(true);
        mTextPaint.setDither(true);
        mTextPaint.setTextSize(20);
        mTextPaint.setColor(Color.GREEN);
        mTextPaint.setStyle(Paint.Style.FILL);
    }

    public void setFaces(Face[] faces) {
        mFaces = faces;
        invalidate();
    }

    public void setOrientation(int orientation) {
        mOrientation = orientation;
    }

    public void setDisplayOrientation(int displayOrientation) {
        mDisplayOrientation = displayOrientation;
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (mFaces != null && mFaces.length > 0) {
            Matrix matrix = new Matrix();
            Util.prepareMatrix(matrix, false, mDisplayOrientation, getWidth(), getHeight());
            canvas.save();
            matrix.postRotate(mOrientation);
            canvas.rotate(-mOrientation);
            RectF rectF = new RectF();
            for (Face face : mFaces) {
                rectF.set(face.rect);
                matrix.mapRect(rectF);
                canvas.drawRect(rectF, mPaint);
                canvas.drawText("Score " + face.score, rectF.right, rectF.top, mTextPaint);
            }
            canvas.restore();
        }
    }
}
```

## Util ##

### Description ###

The Util class is used to calculate the phones current orientation angle and prepare a matrix for normalizing the coordinates.

### Source Code ###

```java
/**
 * This class uses Utility functions written for the Camera module of Android.
 * These snippets have been taken from:
 *
 *      https://android.googlesource.com/platform/packages/apps/Camera/
 *
 *  Android code is released under terms of the Apache 2.0 license. You can obtain the copy in
 *  the assets folder coming with this project.
 *
 *  Copyright (C) 2011 The Android Open Source Project
 *
 */
public class Util {

    // Orientation hysteresis amount used in rounding, in degrees
    private static final int ORIENTATION_HYSTERESIS = 5;

    public static int getDisplayRotation(Activity activity) {
        int rotation = activity.getWindowManager().getDefaultDisplay()
                .getRotation();
        switch (rotation) {
            case Surface.ROTATION_0: return 0;
            case Surface.ROTATION_90: return 90;
            case Surface.ROTATION_180: return 180;
            case Surface.ROTATION_270: return 270;
        }
        return 0;
    }

    public static int getDisplayOrientation(int degrees, int cameraId) {
        // See android.hardware.Camera.setDisplayOrientation for
        // documentation.
        Camera.CameraInfo info = new Camera.CameraInfo();
        Camera.getCameraInfo(cameraId, info);
        int result;
        if (info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT) {
            result = (info.orientation + degrees) % 360;
            result = (360 - result) % 360;  // compensate the mirror
        } else {  // back-facing
            result = (info.orientation - degrees + 360) % 360;
        }
        return result;
    }

    public static void prepareMatrix(Matrix matrix, boolean mirror, int displayOrientation,
                                     int viewWidth, int viewHeight) {
        // Need mirror for front camera.
        matrix.setScale(mirror ? -1 : 1, 1);
        // This is the value for android.hardware.Camera.setDisplayOrientation.
        matrix.postRotate(displayOrientation);
        // Camera driver coordinates range from (-1000, -1000) to (1000, 1000).
        // UI coordinates range from (0, 0) to (width, height).
        matrix.postScale(viewWidth / 2000f, viewHeight / 2000f);
        matrix.postTranslate(viewWidth / 2f, viewHeight / 2f);
    }

    public static int roundOrientation(int orientation, int orientationHistory) {
        boolean changeOrientation = false;
        if (orientationHistory == OrientationEventListener.ORIENTATION_UNKNOWN) {
            changeOrientation = true;
        } else {
            int dist = Math.abs(orientation - orientationHistory);
            dist = Math.min( dist, 360 - dist );
            changeOrientation = ( dist >= 45 + ORIENTATION_HYSTERESIS );
        }
        if (changeOrientation) {
            return ((orientation + 45) / 90 * 90) % 360;
        }
        return orientationHistory;
    }
}
```