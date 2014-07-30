title: android
date: 2013-03-25 10:20
author: Philipp Wagner
template: page_discussion
tags: java, android

# Android #

Here are some solutions for the problems I had in my Android apps. I really hope these snippets help you to save time. Each snippet comes with a short description, so [Google](http://www.google.com) is able to send you to this page. If there is anything unclear, then feel free to comment below. 

## Capturing the Camera Preview with a PreviewCallback ##

I needed to capture the preview image of the Camera, which is quite easy with the [Camera.PreviewCallback](http://developer.android.com/reference/android/hardware/Camera.PreviewCallback.html). But it's not described very well in the documentation or hard to find in existing code, so I post mine. For getting the current image of the preview you need to override the ``onPreviewFrame`` method, then buffer the image and convert it. Since the method is called asynchronously by the framework, we put a lock around the buffer when working with it.

The preview frame of the camera is encoded as [YUV](http://en.wikipedia.org/wiki/YUV). To decode it to a Bitmap you can use the [YuvImage](http://developer.android.com/reference/android/graphics/YuvImage.html) class coming with Android libraries. There might be more efficient implementations, but it suits my needs. 

```java
public class CameraActivity extends Activity
        implements SurfaceHolder.Callback, Camera.PreviewCallback {

    // Holds the current frame, so we can react on a click event:
    private final Lock lock = new ReentrantLock();
    private byte[] mPreviewFrameBuffer;
    
    // Constructor, Overrides for the Activity...
    
    @Override
    public void onPreviewFrame(byte[] bytes, Camera camera) {
        try {
            lock.lock();
            mPreviewFrameBuffer = bytes;
        } finally {
            lock.unlock();
        }
    }
    
    public static Bitmap convertYuvByteArrayToBitmap(byte[] data, Camera camera) {
        Camera.Parameters parameters = camera.getParameters();
        Camera.Size size = parameters.getPreviewSize();
        YuvImage image = new YuvImage(data, parameters.getPreviewFormat(), size.width, size.height, null);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        image.compressToJpeg(new Rect(0, 0, size.width, size.height), 100, out);
        byte[] imageBytes = out.toByteArray();
        return BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);
    }
    
    @Override
    public boolean onTouchEvent(MotionEvent event) {
        int x = (int)event.getX();
        int y = (int)event.getY();
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                break;
            case MotionEvent.ACTION_MOVE:
                break;
            case MotionEvent.ACTION_UP:
            {
                try {
                    lock.lock();
                    // Process the buffered frame! This is safe, because we have locked the access
                    // to the resource we are going to work on. This task should be a background
                    // task, in case it takes too long.

                    Bitmap capturedScreen = convertYuvByteArrayToBitmap(mPreviewFrameBuffer, mCamera);
                        
                    // Now you can work with the Bitmap!

                } finally {
                    lock.unlock();
                 }
            }
            break;
        }
        return false;
    }

    @Override
    public void surfaceCreated(SurfaceHolder surfaceHolder) {
        mCamera = Camera.open();
        try {
            mCamera.setPreviewDisplay(surfaceHolder);
            mCamera.setPreviewCallback(this);
        } catch (Exception e) {
            Log.e(TAG, "Could not preview the image.", e);
        }
    }
    
    @Override
    public void surfaceChanged(SurfaceHolder surfaceHolder, int i, int i2, int i3) {
        // Try to stop the current preview:
        try {
            mCamera.stopPreview();
        } catch (Exception e) {
            // Ignore...
        }
        // Finally start the camera preview again:
        mCamera.setPreviewCallback(this);
        mCamera.startPreview();
    }
}
```

### Extracting a Face from the PreviewImage ###

In my code I wanted to extract a Camera.Face from the preview image. I thought it might be sufficient for basic face recognition tasks, but in 
the end, the images have such a low resolution, that they are not really suited for this task. Still I think the task of extracting an object
from the Camera preview frame might be interesting, so here it goes.

There are functions, which are not necessary for the described task, they are just utility functions. The ``convertYuvByteArrayToBitmap`` method
is described in the parent snippet.

```java
    @Override
    public boolean onTouchEvent(MotionEvent event) {
        int x = (int)event.getX();
        int y = (int)event.getY();
        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                break;
            case MotionEvent.ACTION_MOVE:
                break;
            case MotionEvent.ACTION_UP:
            {
                Face face = mFaceView.touchIntersectsFace(x,y);
                if(face != null) {
                    Toast.makeText(getApplicationContext(), "(" + x + "," + y +")", Toast.LENGTH_LONG).show();
                    try {
                        lock.lock();
                        // Process the buffered frame! This is safe, because we have locked the access
                        // to the resource we are going to work on. This task should be a background
                        // task, in case it takes too long.

                        // Convert the Image from a Yuv ByteArray into a Bitmap:
                        Bitmap b = Util.convertYuvByteArrayToBitmap(mPreviewFrameBuffer, mCamera);

                        // The coordinates of the Camera.Face are given in a range of (-1000,1000),
                        // so let's scale them to the Bitmap coordinate system:
                        Matrix matrix = new Matrix();
                        matrix.postScale(b.getWidth() / 2000f, b.getHeight() / 2000f);
                        matrix.postTranslate(b.getWidth() / 2f, b.getHeight() / 2f);
                        // Now translate the Camera.Face coordinates into the
                        // Bitmap coordinate system:
                        RectF scaledRect = new RectF(face.rect);
                        matrix.mapRect(scaledRect);
                        // And make a Rect again, we need it later. It's the source we want
                        // to crop from:
                        Rect srcRect = new Rect((int) scaledRect.left, (int) scaledRect.top, (int)scaledRect.right, (int) scaledRect.bottom );
                        // This is the destination rectangle, we want it to have the width
                        // and height of the scaled rect:
                        int width = (int) scaledRect.width();
                        int height = (int) scaledRect.height();
                        Rect dstRect = new Rect(0, 0, width, height);
                        // This is the output image, which is going to store the Camera.Face:
                        Bitmap croppedImage = Bitmap.createBitmap(width, height, Bitmap.Config.RGB_565);
                        // And finally crop the image, which is a simple drawBitmap call on the
                        // Canvas:
                        Canvas canvas = new Canvas(croppedImage);
                        canvas.drawBitmap(b, srcRect , dstRect, null);
                        // And write it to the External storage, this is a simple helper method:
                        ImageHelper.saveBitmapAsJpegToExternalStorage(croppedImage, "filename.jpg");
                    } finally {
                        lock.unlock();
                    }
                }
            }
            break;
        }
        return false;
    }
```