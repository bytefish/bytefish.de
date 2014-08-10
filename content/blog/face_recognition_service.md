title: Face Recognition with Android and Python0
date: 2014-08-02 12:23
tags: android, java, face detection
category: android, computer vision
slug: face_detection_with_android
author: Philipp Wagner
summary: Face Detection with the Android Camera.

# A Face Recognition Webservice #

This article deals with writing a RESTful Webservice for Face Recognition. I want to show you
how to extend the [facerec framework](https://github.com/bytefish/facerec) and use it for a small
Web service. The service uses [Flask](http://flask.pocoo.org/docs/), which is a great project.

The Web service doesn't have any security measures yet, so please do not use it in production. It 
doesn't support rate limiting, authentification and all important aspects of a real web application.

You can find the full server implementation used in this article at:

* [https://github.com/bytefish/facerec/tree/master/py/apps/webapp](https://github.com/bytefish/facerec/tree/master/py/apps/webapp)

All code is put under a BSD License, so feel free to use it for your projects.

## cURL ##

[cURL](http://curl.haxx.se/) is a command-line tool for transferring data over various protocols. We are interested in 
executing HTTP commands, in order to make face recognition requests. 

## server.py ##

### Error Codes ###

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

### Logging ###

Tracing errors might be hard, so it's important to log what's going on behind the scenes. Flask uses
the common [Python logging](https://docs.python.org/2/library/logging.html) infrastructure, so we can 
initialize a handler (this example uses a [RotatingFileHandler](https://docs.python.org/2/library/logging.handlers.html#rotatingfilehandler)), 
a formatter and add the handler to Flask's logger. 

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

### Handling Exceptions ###

A crucial aspect of Web service design is how to handle errors. The user of the API should never see 
an exception with stacktrace thrown back at him. The exception could leak implementation details and 
the user probably wouldn't understand the real cause of the exception.

Now you don't want to write a try-catch block around each method, because you would repeat yourself a 
thousand times. Instead we can use a decorator, which catches the original exception and wraps it in a new 
``WebAppException``. 

This exception is then handled by [Flask's errorhandler](http://flask.pocoo.org/docs/api/#flask.Flask.errorhandler),
which logs the original exception and returns a meaningful JSON representation of the ``WebAppException`` to the user.

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

Now imagine we want to throw , if we can't  ``ThrowsWebAppException``

```python
# Get the prediction from the global model.
@ThrowsWebAppException(error_code = PREDICTION_ERROR)
def get_prediction(image_data):
    image = preprocess_image(image_data)
    prediction = model.predict(image)
    return prediction
```

## Decoding the Image ##

The image sent to the Web service is Base64, that means it needs to be decoded to 
its original representation. We don't want to store the image, so we use Pythons very
cool [cStringIO](https://docs.python.org/2/library/stringio.html) module to open it as an image. 

Since these operations might throw an error, the method is annotated with a ``WebAppException``.

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