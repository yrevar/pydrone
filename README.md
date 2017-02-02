#PyDrone - Python API for the ARDrone.

##Overview

PyDrone is a set of python libraries originally written by Bastian Venthur.

##Dependencies:

This software was tested with the following setup:

  * [Python] [python] 2.7.5.
  * [Cython] [cython] 0.19.1.
  * [setuptools] [setuptools].
  * [Pygame] [pygame] 1.9.2 (only for the demo).
  
####Note: On OSX Python and PyGame were installed using [Homebrew] [brew] and [PIP] [pip].

##Getting Started:

###Cython Modules

The pydrone modules are not included as pre-built binaries. To use this API generate the C source code
and build it in-place by using the following commands:

	cython pydrone/*.pyx
	python setup.py build_ext --inplace

After building the pydrone libraries proceed to test the API and drone:

	$ python
	>>> from pydrone import libardrone
	>>> drone = libardrone.ARDrone()
	>>> # You might need to call drone.reset() before taking off if the drone is in
	>>> # emergency mode
	>>> drone.takeoff()
	>>> drone.land()
	>>> drone.halt()

The drone's property `image` contains always the latest image from the camera.
The drone's property `navdata` contains always the latest navdata.

##Demo:

There is also a demo application included which shows the video from the drone
and lets you remote-control the drone with the keyboard:

    RETURN      - takeoff
    SPACE       - land
    BACKSPACE   - reset (from emergency)
    a/d         - left/right
    w/s         - forward/back
    1,2,...,0   - speed
    UP/DOWN     - altitude
    LEFT/RIGHT  - turn left/right

##Make it autonomous?

	$ python
	>>> from pydrone import libardrone
	>>> import cv2
	>>> drone_cam_front = cv2.VideoCapture('tcp://192.168.1.1:5555') # initialize video capture
	>>> drone = libardrone.ARDrone()
	>>> while True:
	>>>	got_frame, frame = drone_cam_front.read() # read frame
	>>>	if got_frame:
	>>>		cv2.imshow('frame', frame) # display frame
	>>>		if cv2.waitKey(1) & 0xFF == 27: # stop processing on escape key
	>>>			break
	>>>		# Do something cool here!
	>>>	else:
	>>>		print 'error reading video feed'
	>>> drone_cam_front.release()
	>>> cv2.destroyAllWindows()

##Repository:

The original public repository is located here:

	git://github.com/venthur/python-ardrone.git

##License:

This software is published under the terms of the MIT License:

	http://www.opensource.org/licenses/mit-license.php
	
[python]: http://www.python.org
[pygame]: http://www.pygame.org/news.html
[drone]: http://ardrone2.parrot.com
[brew]: https://github.com/mxcl/homebrew
[pip]: http://www.pip-installer.org/en/latest/
[cython]: http://cython.org
[setuptools]: http://pypi.python.org/pypi/setuptools
