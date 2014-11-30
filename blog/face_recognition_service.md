title: Implementing a Face Recognition Web service
date: 2014-08-16 21:29
tags: python, flask, facerec
category: python, computer vision
slug: face_recognition_webservice
author: Philipp Wagner
summary: Implementing a Face Recognition Web service with Flask.

This article deals with writing a RESTful Web service for Face Recognition. It's something a 
lot of people have asked me for, and it isn't hard to implement with [Python](http://www.python.org).

The [facerec framework](https://github.com/bytefish/facerec) needs to be extended a little and 
then we are going to use it in a small Web service. I am going to explain how to implement the 
API with [Flask](http://flask.pocoo.org/docs/), which is a great project. The Web service doesn't 
have any security measures yet, so please do not use it in production. It doesn't support any rate 
limiting, authentification or any other important aspects of a real web application.

There's a lot of room for improvement and ideas. I would love to hear your feedback and merge pull
requests to the repository. In the next article I will show how to write an Android app to consume 
the API. You can see the current state of the code in [my github repository](https://www.github.com/bytefish/facerec).

The full server implementation used in this article at:

* [https://github.com/bytefish/facerec/tree/master/py/apps/webapp](https://github.com/bytefish/facerec/tree/master/py/apps/webapp)

All code is put under a BSD License, so feel free to use it for your projects.

## facerec ##

### Installing facerec ###

First of all you have to install the facerec framework, which is available at:

* [https://github.com/bytefish/facerec](https://github.com/bytefish/facerec)

The project comes with a ``setup.py`` file, which is located in the ``py`` folder of the project.

To install the Python framework you have to run (may require administrator access):

```
python setup.py install
```
	
### Dependencies ###


[facerec](https://github.com/bytefish/facerec) has dependencies to:

* [PIL](http://www.pythonware.com/products/pil)
* [NumPy](http://www.numpy.org)
* [SciPy](http://www.scipy.org)
* [matplotlib](http://matplotlib.org/)

All of these packages can be obtained with [pip](http://pip.readthedocs.org/en/latest/) or you follow the installation guide of the projects.

My current Windows setup uses PIL 1.1.7, NumPy 1.8.1, SciPy 0.14.0, matplotlib 1.2.0.

### NumericDataSet ###

The current implementation in the facerec framework uses integers as labels for a person. That was a problem
for many people, since mapping between names and integers might not be obvious, or it makes your code unnecessarily 
complex. To solve this problem, I have written a tiny class that does the mapping for us. It's called a 
``NumericDataSet`` and is available in the ``facerec.dataset`` module.

Instead of explaining the API I am pasting the source, because it is a few lines only.

```python
# To abstract the dirty things away, we are going to use a 
# new class, which we call a NumericDataSet. This NumericDataSet
# allows us to add images and turn them into a facerec compatible
# representation.
class NumericDataSet(object):
    def __init__(self):
        self.data = {}
        self.str_to_num_mapping = {}
        self.num_to_str_mapping = {}

    def add(self, identifier, image):
        try:
            self.data[identifier].append(image)
        except:
            self.data[identifier] = [image]
            numerical_identifier = len(self.str_to_num_mapping)
            # Store in mapping tables:
            self.str_to_num_mapping[identifier] = numerical_identifier
            self.num_to_str_mapping[numerical_identifier] = identifier

    def get(self):
        X = []
        y = []
        for name, num in self.str_to_num_mapping.iteritems():
            for image in self.data[name]:
                X.append(image)
                y.append(num)
        return X,y

    def resolve_by_str(self, identifier):
        return self.str_num_mapping[identifier]

    def resolve_by_num(self, numerical_identifier):
        return self.num_to_str_mapping[numerical_identifier]

    def length(self):
        return len(self.data)

    def __repr__(self):
        print "NumericDataSet"
```

With ``add(identifier, image)`` you can add images to the dataset and assign them with an identifier. 
The images have to be NumPy arrays. The ``get()`` method of the ``NumericDataSet`` returns the 
representation used for training a ``PredictableModel`` used in previous examples of the framework. 

### Wrapping the PredictableModel ###

So how can we use the ``NumericDataSet`` with the framework? 

The simplest solution is to write a wrapper for the ``PredictableModel``, 
that nicely abstracts all the stuff away:
 
```python
# This wrapper hides the complexity of dealing with integer labels for
# the training labels. It also supports updating a model, instead of 
# re-training it. 
class PredictableModelWrapper(object):

    def __init__(self, model):
        self.model = model
        self.numeric_dataset = NumericDataSet()
        
    def compute(self):
        X,y = self.numeric_dataset.get()
        self.model.compute(X,y)

    def set_data(self, numeric_dataset):
        self.numeric_dataset = numeric_dataset

    def predict(self, image):
        prediction_result = self.model.predict(image)
        # Only take label right now:
        num_label = prediction_result[0]
        str_label = self.numeric_dataset.resolve_by_num(num_label)
        return str_label

    def update(self, name, image):
        self.numeric_dataset.add(name, image)
        class_label = self.numeric_dataset.resolve_by_str(name)
        extracted_feature = self.feature.extract(image)
        self.classifier.update(extracted_feature, class_label)

    def __repr__(self):
        return "PredictableModelWrapper (Inner Model=%s)" % (str(self.model))
```

This is exactely the same API, that has been used for the other examples. 

### Defining the Features and Classifier ###

Next we'll define a method to generate us a ``PredictableModel``, which is used to classify incoming images. 

You can read about the concepts of the framework in the documentation at [http://bytefish.de/dev/facerec](http://bytefish.de/dev/facerec/), 
so in short: In order to generate predictions, you'll need to define a ``PredictableModel`` which is a combination
of a feature extraction algorithm (PCA, LDA, LBP, ...) and a classifier (Nearest Neighbor, SVM, ...). With a 
``ChainOperator`` you can build your image processing pipeline, and by calling ``compute()`` the model is finally 
computed.

In this example the images are resized to ``128 x 128`` pixels and the [Fisherfaces](http://bytefish.de/blog/fisherfaces) 
are computed. Computing the model can take some time, so the method also stores the model, if a filename was given.

```python
# Now define a method to get a model trained on a NumericDataSet,
# which should also store the model into a file if filename is given.
def get_model(numeric_dataset, model_filename=None):
    feature = ChainOperator(Resize((128,128)), Fisherfaces())
    classifier = NearestNeighbor(dist_metric=EuclideanDistance(), k=1)
    inner_model = PredictableModel(feature=feature, classifier=classifier)
    model = PredictableModelWrapper(inner_model)
    model.set_data(numeric_dataset)
    model.compute()
    if not model_filename is None:
        save_model(model_filename, model)
    return model
```

### Reading the Data ###

We are almost done with the facerec part. What's left is to read in a set of images, 
which may be a dataset given in a really easy CSV format. It's up to you how to read
in the data, this is how I do it for this article.

The CSV file simply defines the name of a person and the folder to read the images from:

```
Angelina Jolie;D:/facerec/data/c1/crop_angelina_jolie
Arnold Schwarzenegger;D:/facerec/data/c1/crop_arnold_schwarzenegger
Brad Pitt;D:/facerec/data/c1/crop_brad_pitt
...
```

And with the following methods we are reading the image data:

```python
# Now a method to read images from a folder. It's pretty simple,
# since we can pass a numeric_dataset into the read_images  method 
# and just add the files as we read them. 
def read_images(path, identifier, numeric_dataset):
    for filename in os.listdir(path):
        try:
            img = Image.open(os.path.join(path, filename))
            img = img.convert("L")
            img = np.asarray(img, dtype=np.uint8)
            numeric_dataset.add(identifier, img)
        except IOError, (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

# read_csv is a tiny little method, that takes a csv file defined
# like this:
#
#   Philipp Wagner;D:/images/philipp
#   Another Name;D:/images/another_name
#   ...
#
def read_from_csv(filename):
    numeric_dataset = NumericDataSet()
    with open(filename, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar='#')
        for row in reader:
            identifier = row[0]
            path = row[1]
            read_images(path, identifier, numeric_dataset)
    return numeric_dataset

# Just some sugar on top...
def get_model_from_csv(filename, out_model_filename):
    numeric_dataset = read_from_csv(filename)
    model = get_model(numeric_dataset, out_model_filename)
    return model

def load_model_file(model_filename):
    load_model(model_filename)
```

## The Web service ##

Now the server part is going to be implemented. The server uses [Flask](http://flask.pocoo.org/docs/) and
should be easy to extend, if you want to add some features. Currently it only supports recognizing an image
given as [Base64](http://en.wikipedia.org/wiki/Base64). One of the features worth adding, would be a method
to download an image and recognize it.

### Error Codes ###

We'll start with an important part: Errors. 

You can't expect input data to be perfect. There are probably images, that can't be read. There are probably errors 
in the facerec code, that crash the application (I am not perfect, and the code obviously lacks any unit tests). 

It's important to not return the Stacktrace of the exception to the Consumer of the API. Why? Because without knowing 
the code in detail it will be totally useless to him. And returning the Stacktrace might leak implementation details, 
which we want to hide.

So if you are building your own RESTful API, you should define a set of errors. The consuming client can react on 
these errors and take the necessary actions, to inform the user about a problem.

The list of error codes in this Web service is:

```python
# This is a list of errors the Webservice returns. You can come up
# with new error codes and plug them into the API.
#
# An example JSON response for an error looks like this:
#
#   { "status" : failed, "message" : "IMAGE_DECODE_ERROR", "code" : 10 }
#
# If there are multiple errors, only the first error is considered.

IMAGE_DECODE_ERROR = 10
IMAGE_RESIZE_ERROR = 11
PREDICTION_ERROR = 12
SERVICE_TEMPORARY_UNAVAILABLE = 20
UNKNOWN_ERROR = 21
INVALID_FORMAT = 30
INVALID_API_KEY = 31
INVALID_API_TOKEN = 32
MISSING_ARGUMENTS = 40

errors = {
    IMAGE_DECODE_ERROR : "IMAGE_DECODE_ERROR",
    IMAGE_RESIZE_ERROR  : "IMAGE_RESIZE_ERROR",
    SERVICE_TEMPORARY_UNAVAILABLE	: "SERVICE_TEMPORARILY_UNAVAILABLE",
    PREDICTION_ERROR : "PREDICTION_ERROR",
    UNKNOWN_ERROR : "UNKNOWN_ERROR",
    INVALID_FORMAT : "INVALID_FORMAT",
    INVALID_API_KEY : "INVALID_API_KEY",
    INVALID_API_TOKEN : "INVALID_API_TOKEN",
    MISSING_ARGUMENTS : "MISSING_ARGUMENTS"
}
```

### Handling Exceptions ###

So how do we return these errors to the consumer?

You don't want to write a try-catch block around each method, at least I don't want to. Instead we can use a decorator, 
which we call a ``ThrowsWebAppException``. It catches the original exception and wraps it in a new ``WebAppException``,
which in turn is thrown at flask. 

This ``WebAppException`` exception is then handled by [Flask's errorhandler](http://flask.pocoo.org/docs/api/#flask.Flask.errorhandler),
which logs the original exception and extracts a meaningful JSON representation from the ``WebAppException``.

The code looks like this:

```python
# The WebAppException might be useful. It enables us to 
# throw exceptions at any place in the application and give the user
# a custom error code.
class WebAppException(Exception):

    def __init__(self, error_code, exception, status_code=None):
        Exception.__init__(self)
        self.status_code = 400
        self.exception = exception
        self.error_code = error_code
        try:
            self.message = errors[self.error_code]
        except:
            self.error_code = UNKNOWN_ERROR
            self.message = errors[self.error_code]
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        rv = dict()
        rv['status'] = 'failed'
        rv['code'] = self.error_code
        rv['message'] = self.message
        return rv

# Wow, a decorator! This enables us to catch Exceptions 
# in a method and raise a new WebAppException with the 
# original Exception included. This is a quick and dirty way
# to minimize error handling code in our server.
class ThrowsWebAppException(object):
   def __init__(self, error_code, status_code=None):
      self.error_code = error_code
      self.status_code = status_code

   def __call__(self, function):
      def returnfunction(*args, **kwargs):
         try:
            return function(*args, **kwargs)
         except Exception as e:
            raise WebAppException(self.error_code, e)
      return returnfunction

# Register an error handler on the WebAppException, so we
# can return the error as JSON back to the User. At the same
# time you should do some logging, so it doesn't pass by 
# silently.
@app.errorhandler(WebAppException)
def handle_exception(error):
    app.logger.exception(error.exception)
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
```

Now imagine there's a problem with the Base64 represented image data. The function
for reading the image might throw an exception, either when decoding the Base64
string or trying to read the image with PIL. 

The trick is to decorate the method with out ``ThrowsWebAppException`` decorator,
which will return the ``IMAGE_DECODE_ERROR`` to the user, instead of returning
the original exception.

```python
# Now finally add the methods needed for our FaceRecognition API!
# Right now there is no rate limiting, no auth tokens and so on.
# 
@ThrowsWebAppException(error_code = IMAGE_DECODE_ERROR)
def read_image(base64_image):
    """ Decodes Base64 image data, reads it with PIL and converts it into grayscale.

    Args:
    
        base64_image [string] A Base64 encoded image (all types PIL supports).
    """
    enc_data = base64.b64decode(base64_image)
    file_like = cStringIO.StringIO(enc_data)
    im = Image.open(file_like)
    im = im.convert("L")
    return im
```

### Logging ###

Tracing errors might be hard, so it's important to log what's going on behind the scenes. Flask uses
the common [Python logging](https://docs.python.org/2/library/logging.html) infrastructure. That means
we can initialize a handler at startup and append all the loggers we want to it, this includes the logger
of the Flask application of course. This example uses a [RotatingFileHandler](https://docs.python.org/2/library/logging.handlers.html#rotatingfilehandler)) 
as a handler and also defines a custom formatter. 

```python
# Setup the logging for the server, so we can log all exceptions
# away. We also want to acquire a logger for the facerec framework,
# so we can be sure, that all logging goes into one place.
LOG_FILENAME = 'serverlog.log'
LOG_BACKUP_COUNT = 5
LOG_FILE_SIZE_BYTES = 50 * 1024 * 1024

def init_logger(app):
    handler = RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_SIZE_BYTES, backupCount=LOG_BACKUP_COUNT)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    loggers = [app.logger, logging.getLogger('facerec')]
    for logger in loggers:
        logger.addHandler(handler)

# Bring the model variable into global scope. This might be
# dangerous in Flask, I am trying to figure out, which is the
# best practice here. 

# Initializes the Flask application, which is going to 
# add the loggers, load the initial facerec model and 
# all of this.
def init_app(app):
    init_logger(app)
```

### Decoding the Image ###

The image sent to the Web service is [Base64](http://en.wikipedia.org/wiki/Base64), that means it 
needs to be decoded to its original representation. We don't want to store the image, so we use 
Pythons very cool [cStringIO](https://docs.python.org/2/library/stringio.html) module to open it 
as a file. 

Since these operations might throw an error, the method is annotated with a ``WebAppException``:

```python
# Now finally add the methods needed for our FaceRecognition API!
# Right now there is no rate limiting, no auth tokens and so on.
# 
@ThrowsWebAppException(error_code = IMAGE_DECODE_ERROR)
def read_image(base64_image):
    """ Decodes Base64 image data, reads it with PIL and converts it into grayscale.

    Args:
    
        base64_image [string] A Base64 encoded image (all types PIL supports).
    """
    enc_data = base64.b64decode(base64_image)
    file_like = cStringIO.StringIO(enc_data)
    im = Image.open(file_like)
    im = im.convert("L")
    return im
```

### Recognize ###

With all the methods defined, getting a prediction becomes easy. First of all we create a new url rule for Flask, which can be done with a [route decorator](http://flask.pocoo.org/docs/api/#flask.Flask.route).
The method parses the request, decodes the Base64 image and creates a prediction with a given facerec model. 


```python
def preprocess_image(image_data):
    image = read_image(image_data)
    return image

# Get the prediction from the global model.
@ThrowsWebAppException(error_code = PREDICTION_ERROR)
def get_prediction(image_data):
    image = preprocess_image(image_data)
    prediction = model.predict(image)
    return prediction

# Now add the API endpoints for recognizing, learning and 
# so on. If you want to use this in any public setup, you
# should add rate limiting, auth tokens and so on.
@app.route('/api/recognize', methods=['GET', 'POST'])
def identify():
    if request.headers['Content-Type'] == 'application/json':
            try:
                image_data = request.json['image']
            except:
                raise WebAppException(error_code=MISSING_ARGUMENTS)
            prediction = get_prediction(image_data)
            response = jsonify(name = prediction) 
            return response
    else:
        raise WebAppException(error_code=INVALID_FORMAT)
```

## Client ##

Now what's left is testing the Web service. Using a browser might work, but it's probably not a handy tool.
My next article is going to show how to consume the service with Android, but for now we'll write a small
Python client. It's really easy with Python and its modules to write the client for testing the service.

### client.py ###

The plan is basically: Use the [base64 module](https://docs.python.org/2/library/base64.html) to encode a file, 
the [json module](https://docs.python.org/2/library/json.html) to encode the JSON Request to the server and finally 
[urllib2](https://docs.python.org/2/library/urllib2.html) to make the POST request.

This results in the ``client.py`` script:

```python
#!/usr/bin/env python

import json
import base64
import urllib2

SERVER_ADDRESS = "http://localhost:8000/api/recognize"

class FaceRecClient(object):

    def __init__(self, url):
        self.url = url
        
    def getBase64(self, filename):
        with open(filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        return encoded_string

    def request(self, api_func, request_data):
        url_func = "%s/api/%s" % (self.url, api_func)
        req = urllib2.Request(url=url_func, data = json.dumps(request_data), headers = {'content-type': 'application/json'})
        res = urllib2.urlopen(req)
        return res.read()

    def recognize(self, filename):
        base64Image = self.getBase64(filename)
        json_data = { "image" : base64Image }
        api_result = self.request("recognize", json_data)
        print json.loads(api_result)
        
if __name__ == '__main__':
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    parser.add_argument("-s", "--server", action="store", dest="host", default=SERVER_ADDRESS, 
        help="Sets the endpoint for the server to call.", required=False)
    parser.add_argument('images', nargs='+', help="Images to call the server with.")
    
    print "=== Usage ==="
    parser.print_help()
    
    # Recognize each image:        
    args = parser.parse_args()
    print "=== Predictions ==="       
    faceRecClient = FaceRecClient(args.host)
    for image in args.images:
        faceRecClient.recognize(image)
```

## Running the Client and Server ##

Now it's time to run the server and client. I don't have a dataset for you to play around with,
so you might want to come up with your own. In these examples I am using the Celebrities dataset,
that I have created years ago.

You might want to read my other articles on preprocessing images: [http://bytefish.de/blog/aligning_face_images](http://bytefish.de/blog/aligning_face_images).

### Starting the Server ###

Fire up a shell and type ``python server.py -h`` to get the help message. It shows the available
parameters and explains them in detail. I've also added a short description at startup to give
the user additional information (and to warn about using it in production). 

```
PS D:\github\facerec\py\apps\webapp> python .\server.py -h
=== Description ===
server.py is a simple facerec webservice. It provides you with a simple RESTful API to recognize faces from a computed m
odel. Please don't use this server in a production environment, as it provides no security and there might be ugly concu
rrency issues with the global state of the model.
=== Usage ===
usage: server.py [-h] [-t DATASET] [-a HOST] [-p PORT] [model_filename]

positional arguments:
  model_filename        Filename of the model to use or store

optional arguments:
  -h, --help            show this help message and exit
  -t DATASET, --train DATASET
                        Calculates a new model from a given CSV file. CSV
                        format: <person>;</path/to/image/folder>.
  -a HOST, --address HOST
                        Sets the endpoint for this server.
  -p PORT, --port PORT  Sets the port for this server.
usage: server.py [-h] [-t DATASET] [-a HOST] [-p PORT] [model_filename]
```

Now imagine we have a data set available given in the format as described above:

```
Angelina Jolie;D:/facerec/data/c1/crop_angelina_jolie
Arnold Schwarzenegger;D:/facerec/data/c1/crop_arnold_schwarzenegger
Brad Pitt;D:/facerec/data/c1/crop_brad_pitt
...
```

If you don't have a model yet, you have to learn one when starting the server and
it will be stored to the model filename given in command line. 

Starting the Server then becomes as easy as typing:

```
python server.py -t D:/facerec/celebrities.csv model.pkl
```

The server will then start:

```
=== Server Log (also in serverlog.log) ===
 * Running on http://0.0.0.0:5000/
```

So initially it runs on ``localhost`` and port ``5000``, but you can define different parameters with the ``-a`` and ``-p`` switch.

### Consuming the API with the Client ###

Again, we have a look at the help message of the script first:

```
PS D:\github\facerec\py\apps\webapp> python client.py -h
=== Usage ===
usage: client.py [-h] [-s HOST] image [image ...]

positional arguments:
  image                 Images to call the server with.

optional arguments:
  -h, --help            show this help message and exit
  -s HOST, --server HOST
                        Sets the endpoint for the server to call.
usage: client.py [-h] [-s HOST] image [image ...]

positional arguments:
  image                 Images to call the server with.

optional arguments:
  -h, --help            show this help message and exit
  -s HOST, --server HOST
                        Sets the endpoint for the server to call.
```

And we can see, that the script can be called with a host address (defaults to ``http://localhost:5000``) 
and a list of images, given as positional arguments.

So to consume the face recognition server, which has been started above, you can call the client script like this:

```
python client.py "D:\facerec\data\c1\crop_angelina_jolie\crop_09.jpg" "D:\facerec\data\c1\crop_arnold_schwarzenegger\crop_01.jpg"
```

And it will call the server and print the predictions it got:

```
=== Predictions ===
{u'name': u'Angelina Jolie'}
{u'name': u'Arnold Schwarzenegger'}
```

## Conclusion ##

And that's it! I hope the big takeaway in this article is, that it's really easy to build a server application with Flask and Python.