title: Android Snippets
date: 2010-02-08 13:31
author: Philipp Wagner
tags: java, android
category: android
slug: android

# Android #

This is an old wiki page turned into an article, so the redirects function correctly. There are trivial snippets here, but they may be helpful for someone.

## Bearing and Distance between two given GPS Coordinates ##

Instead of rolling out your own implementation, you better go with [Location.distanceBetween](http://developer.android.com/reference/android/location/Location.html#distanceBetween%28double,%20double,%20double,%20double,%20float[]%29). It gives you the results on the WGS84 ellipsoid.

Example:

```java
// ...
float[] results = new float[3];
Location.distanceBetween(36.12, -86.67, 33.94, -118.40,results);

float distance = results[0];
float initialBearing = results[1];
float finalBearing = results[2];

// ...
```

## Http Basic Auth ##

Here is how to do a HTTP Basic Authentification:

```java
// ...
DefaultHttpClient client = new DefaultHttpClient();
client.getCredentialsProvider().setCredentials(
		new AuthScope(null, -1),
		new UsernamePasswordCredentials("username", "password"));
// ...
```

If you need to trust SSL certificates read: 

* [http://blog.antoine.li/index.php/2010/10/android-trusting-ssl-certificates](http://blog.antoine.li/index.php/2010/10/android-trusting-ssl-certificates)

## orientation ##

If you don't want orientation changes, put this in your onCreate Method:

```java
// ...

@Override
public void onCreate(Bundle savedInstanceState) {
  super.onCreate(savedInstanceState);
  setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
}

//...
```

## reading accelerometer values ##

Reading Accelerometer values is done by using the [SensorManager](http://developer.android.com/reference/android/hardware/SensorManager.html). To smooth values simply apply a [low-pass filter](http://en.wikipedia.org/wiki/Low-pass_filter#Algorithmic_implementation):

```java
import java.text.DecimalFormat;
import android.app.Activity;
import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.widget.LinearLayout;
import android.widget.LinearLayout.LayoutParams;
import android.widget.TextView;

public class AcceleratorDemo extends Activity implements SensorEventListener {
	
	private SensorManager sensorMgr = null; 
	private TextView txtView = null;
	private Sensor mSensor;
	
	private float[] rolling = new float[3];
	private float mFilteringFactor = 0.8f;
	
	DecimalFormat formatter =  new DecimalFormat("00.00");

    /** Called when the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        this.sensorMgr = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        LinearLayout l = new LinearLayout(this);
        txtView = new TextView(this);
        l.addView(txtView, new LinearLayout.LayoutParams(LayoutParams.FILL_PARENT, LayoutParams.WRAP_CONTENT));        
   
        setContentView(l);
    }

    @Override
    protected void onResume() {
    	super.onResume();
    	mSensor = sensorMgr.getDefaultSensor(SensorManager.SENSOR_ACCELEROMETER);
    	sensorMgr.registerListener(this, mSensor , SensorManager.SENSOR_DELAY_FASTEST);
    }
    
    @Override
    protected void onDestroy() {
    	super.onDestroy();
    	sensorMgr.unregisterListener(this,mSensor);
    }
   
	public void onAccuracyChanged(Sensor sensor, int accuracy) {}

	public void onSensorChanged(SensorEvent event) {
		float[] values = event.values;
		
		float x = values[SensorManager.DATA_X];
		float y = values[SensorManager.DATA_Y];
		float z = values[SensorManager.DATA_Z];
	   
		// smooth data (low-pass filter)
		rolling[0] = (x * mFilteringFactor) + (rolling[0] * (1.0f - mFilteringFactor));
	    rolling[1] = (y * mFilteringFactor) + (rolling[1] * (1.0f - mFilteringFactor));
	    rolling[2] = (z * mFilteringFactor) + (rolling[2] * (1.0f - mFilteringFactor));

		txtView.setText(formatter.format(rolling[0])+ "," + formatter.format(rolling[1]) + "," + formatter.format(rolling[2]));
	}    
}
```

## Simple Gesture Recognition ##

<img src="/static/images/wiki/mousegesture.png" width="300" />

Here is a super simple application for recognizing mouse gestures. Based on DTW it should give a good accuracy. Complexity is O(n²), so it's not really suited for large training sets. You might want to look at the [$1-Recognizer](http://depts.washington.edu/aimgroup/proj/dollar/) for a faster algorithm.

```java
import java.util.ArrayList;
import java.util.List;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;
import android.view.MotionEvent;
import android.view.View;
import android.view.View.OnTouchListener;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class GestureApp extends Activity implements OnTouchListener {

	private DrawView drawView;
	private TextView lblGesture;
	private CheckBox checkMode;

	List<float[]> points = new ArrayList<float[]>();
	List<Template> templates = new ArrayList<Template>();

	private class Template {
		String name;
		List<float[]> points;

		public Template(String name, List<float[]> points) {
			this.name = name;
			this.points = new ArrayList<float[]>(points);
		}
	};

	@Override
	public void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);

		LinearLayout root = new LinearLayout(this);
		root.setOrientation(LinearLayout.VERTICAL);
		root.setBackgroundColor(Color.BLACK);

		drawView = new DrawView(this);
		drawView.setLayoutParams(new LinearLayout.LayoutParams(
				LinearLayout.LayoutParams.WRAP_CONTENT,
				LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f));

		drawView.setBackgroundColor(Color.BLACK);
		drawView.setOnTouchListener(this);

		lblGesture = new TextView(this);
		lblGesture.setText("Gesture?");
		lblGesture.setPadding(10, 0, 0, 0);
		lblGesture.setTextSize(30.0f);
		lblGesture.setBackgroundColor(Color.BLACK);
		lblGesture.setLayoutParams(new LinearLayout.LayoutParams(
				LinearLayout.LayoutParams.FILL_PARENT,
				LinearLayout.LayoutParams.WRAP_CONTENT, 0.0f));

		checkMode = new CheckBox(this);
		checkMode.setText("Training");
		checkMode.setChecked(true);
		checkMode.setLayoutParams(new LinearLayout.LayoutParams(
				LinearLayout.LayoutParams.FILL_PARENT,
				LinearLayout.LayoutParams.WRAP_CONTENT, 0.0f));

		root.addView(checkMode);
		root.addView(drawView);
		root.addView(lblGesture);

		setContentView(root);
		drawView.requestFocus();
	}

	@Override
	public boolean onTouch(View arg0, MotionEvent ev) {

		switch (ev.getAction()) {
		case MotionEvent.ACTION_UP:
			scale(points);
			if (checkMode.isChecked()) {
				store();
			} else {
				classify();
			}

			break;
		case MotionEvent.ACTION_DOWN:
			points.clear();
			break;
		default:
			points.add(new float[] { ev.getX(), ev.getY() });
			break;
		}
		// redraw view
		drawView.invalidate();
		return true;
	}

	private class DrawView extends View {

		Paint borderPaint = new Paint();
		Paint innerPaint = new Paint();
		Paint paint = new Paint();

		public DrawView(Context context) {
			super(context);
			setFocusable(true);
			setFocusableInTouchMode(true);

			borderPaint.setColor(Color.RED);
			borderPaint.setStrokeWidth(3.0f);
			borderPaint.setAntiAlias(true);

			innerPaint.setColor(Color.BLACK);
			innerPaint.setAntiAlias(true);

			paint.setColor(Color.WHITE);
			paint.setStrokeWidth(2.0f);
			paint.setAntiAlias(true);
		}

		@Override
		public void onDraw(Canvas canvas) {
			canvas.drawRect(1, 1, getMeasuredWidth(), getMeasuredHeight(),
					borderPaint);
			canvas.drawRect(5, 5, getMeasuredWidth() - 4,
					getMeasuredHeight() - 4, innerPaint);

			for (int i = 0; i < points.size() - 1; i++) {
				float[] p1 = points.get(i);
				float[] p2 = points.get(i + 1);
				canvas.drawLine(p1[0], p1[1], p2[0], p2[1], paint);
			}
		}
	}

	public void store() {
		final AlertDialog.Builder alert = new AlertDialog.Builder(this);
		alert.setTitle("Name of the Mousegesture:");
		final EditText input = new EditText(this);
		alert.setView(input);
		alert.setPositiveButton("Ok", new DialogInterface.OnClickListener() {
			public void onClick(DialogInterface dialog, int whichButton) {
				String value = input.getText().toString().trim();
				templates.add(new Template(value, points));
			}
		});

		alert.setNegativeButton("Cancel",
				new DialogInterface.OnClickListener() {
					public void onClick(DialogInterface dialog, int whichButton) {
						dialog.cancel();
					}
				});

		alert.show();
	}

	public void classify() {

		float minDist = Float.MAX_VALUE;
		String minTemplate = "none";

		for (Template template : this.templates) {
			float dist = dtw(points, template.points);
			if (dist < minDist) {
				minDist = dist;
				minTemplate = template.name;
			}
		}
		
		lblGesture.setText(minTemplate);
	}

	public static float dist(float[] x, float[] y) {
		float dx = x[0] - y[0];
		float dy = x[1] - y[1];
		return (float) Math.sqrt(dx * dx + dy * dy);
	}

	public static float dtw(List<float[]> t1, List<float[]> t2) {
		int m = t1.size();
		int n = t2.size();
		if(m < 2 || n < 2)
			return Float.MAX_VALUE;
		float[][] cost = new float[m][n];
		cost[0][0] = dist(t1.get(0), t2.get(0));
		for (int i = 1; i < m; i++)
			cost[i][0] = cost[i - 1][0] + dist(t1.get(i), t2.get(0));
		for (int j = 1; j < n; j++)
			cost[0][j] = cost[0][j - 1] + dist(t1.get(0), t2.get(j));
		for (int i = 1; i < m; i++)
			for (int j = 1; j < n; j++)
				cost[i][j] = Math.min(cost[i - 1][j],
						Math.min(cost[i][j - 1], cost[i - 1][j - 1]))
						+ dist(t1.get(i), t2.get(j));
		return cost[m - 1][n - 1];
	}
	
	public static void scale(List<float[]> points) {
		float[] minmaxX = new float[]{Float.MAX_VALUE, Float.MIN_VALUE};
		float[] minmaxY = new float[]{Float.MAX_VALUE, Float.MIN_VALUE};

		for(float[] point : points) {
			if(point[0] < minmaxX[0])
				minmaxX[0] = point[0];
			if(point[0] > minmaxX[1])
				minmaxX[1] = point[0];
			if(point[1] < minmaxY[0])
				minmaxY[0] = point[1];
			if(point[1] > minmaxY[1])
				minmaxY[1] = point[1];
		}
		
		for (int i = 0; i < points.size(); i++) {
			points.get(i)[0] = (points.get(i)[0] - minmaxX[0]) / (minmaxX[1] - minmaxX[0]);
			points.get(i)[1] = (points.get(i)[1] - minmaxY[0]) / (minmaxY[1] - minmaxY[0]);
		}
	}			
}
```
