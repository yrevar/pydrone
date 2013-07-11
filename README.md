#PyDrone - Python API for the ARDrone UAV.

##Overview

PyDrone is a set of python libraries originally written by Bastian Venthur.

##Getting Started:

	$ python
	>>> import libardrone
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

##Repository:

The original public repository is located here:

	git://github.com/venthur/python-ardrone.git


##Requirements:

This software was tested with the following setup:

  * Python 2.7.5
  * Pygame 1.9.2 (only for the demo)
  * Unmodified ARDrone Parrot


##License:

This software is published under the terms of the MIT License:

	http://www.opensource.org/licenses/mit-license.php
