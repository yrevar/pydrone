"""\
Python library for the ARDrone.

This module was tested with Python 2.7.5 and ARDrone Parrot.

Copyright (c) 2011 Bastian Venthur

The license and distribution terms for this file may be
found in the file LICENSE in this distribution.
"""


from struct import unpack, pack
from multiprocessing import Pipe
from threading import Timer, Lock
from socket import socket, AF_INET, SOCK_DGRAM

from .arnetwork import ARDroneNetworkProcess, IPCThread


ARDRONE_COMMAND_PORT = 5556

class ARDrone(object):
    """\
    ARDrone Class.

    Instantiate this class to control your drone and receive decoded video and
    navdata.
    """
    def __init__(self):
        """\
        Constructor.
        """
        self.seq_nr = 1
        self.timer_t = 0.2
        self.com_watchdog_timer = Timer(self.timer_t, self.commwdg)
        self.lock = Lock()
        self.speed = 0.1

        self.at(at_config, "general:navdata_demo", "TRUE")

        self.video_pipe, video_pipe_other = Pipe()
        self.nav_pipe, nav_pipe_other = Pipe()
        self.com_pipe, com_pipe_other = Pipe()

        self.network_process = ARDroneNetworkProcess(nav_pipe_other, \
            video_pipe_other, com_pipe_other)
        self.network_process.start()
        self.ipc_thread = IPCThread(self)
        self.ipc_thread.start()

        self.image = None

        self.navdata = dict()
        self.time = 0

    def takeoff(self):
        """\
        Make the drone takeoff.
        """
        self.at(at_ftrim)
        self.at(at_config, "control:altitude_max", "20000")
        self.at(at_ref, True)

    def land(self):
        """\
        Make the drone land.
        """
        self.at(at_ref, False)

    def hover(self):
        """\
        Make the drone hover.
        """
        self.at(at_pcmd, False, 0, 0, 0, 0)

    def move_left(self):
        """\
        Make the drone move left.
        """
        self.at(at_pcmd, True, -self.speed, 0, 0, 0)

    def move_right(self):
        """\
        Make the drone move right.
        """
        self.at(at_pcmd, True, self.speed, 0, 0, 0)

    def move_up(self):
        """\
        Make the drone rise upwards.
        """
        self.at(at_pcmd, True, 0, 0, self.speed, 0)

    def move_down(self):
        """\
        Make the drone decent downwards.
        """
        self.at(at_pcmd, True, 0, 0, -self.speed, 0)

    def move_forward(self):
        """\
        Make the drone move forward.
        """
        self.at(at_pcmd, True, 0, -self.speed, 0, 0)

    def move_backward(self):
        """\
        Make the drone move backwards.
        """
        self.at(at_pcmd, True, 0, self.speed, 0, 0)

    def turn_left(self):
        """\
        Make the drone rotate left.
        """
        self.at(at_pcmd, True, 0, 0, 0, -self.speed)

    def turn_right(self):
        """\
        Make the drone rotate right.
        """
        self.at(at_pcmd, True, 0, 0, 0, self.speed)

    def reset(self):
        """\
        Toggle the drone's emergency state.
        """
        self.at(at_ref, False, True)
        self.at(at_ref, False, False)

    def trim(self):
        """\
        Flat trim the drone.
        """
        self.at(at_ftrim)

    def set_speed(self, speed):
        """\
        Set the drone's speed. Valid values are floats from [0..1]

        @param speed: The desired speed.
        @type speed: C{float}
        """
        self.speed = speed

    def at(self, cmd, *args, **kwargs):
        """\
        Wrapper for the low level at commands.

        This method takes care that the sequence number is increased after each
        at command and the watchdog timer is started to make sure the drone
        receives a command at least every second.
        """
        self.lock.acquire()
        self.com_watchdog_timer.cancel()
        cmd(self.seq_nr, *args, **kwargs)
        self.seq_nr += 1
        self.com_watchdog_timer = Timer(self.timer_t, self.commwdg)
        self.com_watchdog_timer.start()
        self.lock.release()

    def commwdg(self):
        """\
        Communication watchdog signal.

        This needs to be send regulary to keep the communication w/ the drone
        alive.
        """
        self.at(at_comwdg)

    def halt(self):
        """\
        Shutdown the drone.

        This method does not land or halt the actual drone, but the
        communication with the drone. You should call it at the end of your
        application to close all sockets, pipes, processes and threads related
        with this object.
        """
        self.lock.acquire()
        self.com_watchdog_timer.cancel()
        self.com_pipe.send('die!')
        self.network_process.terminate()
        self.network_process.join()
        self.ipc_thread.stop()
        self.ipc_thread.join()
        self.lock.release()


# Low level operations.

def at_ref(seq, takeoff, emergency=False):
    """\
    Basic behaviour of the drone: take-off/landing, emergency, stop/reset.

    @param seq: Sequence number.
    @type seq: C{int}
    @param takeoff: True: Takeoff / False: Land.
    @type takeoff: C{bool}
    @param emergency: True: Turn of the engines.
    @type emergency: C{bool}
    """
    p = 0b10001010101000000000000000000
    if takeoff:
        p += 0b1000000000
    if emergency:
        p += 0b0100000000
    at("REF", seq, [p])

def at_pcmd(seq, progressive, lr, fb, vv, va):
    """\
    Makes the drone move (translate/rotate). The float values are a percentage of
    the maximum speed.

    @param seq: Sequence number.
    @type seq: C{int}
    @param progressive: True: enable progressive commands, False: disable (i.e.
        enable hovering mode).
    @type progressive: C{bool}
    @param lr: left-right tilt: [-1..1] negative: left, positive: right.
    @type lr: C{float}
    @param rb: front-back tilt: [-1..1] negative: forwards, positive: backwards.
    @type rb: C{float}
    @param vv: vertical speed: [-1..1] negative: go down, positive: rise.
    @type vv: C{float}
    @param va: angular speed: [-1..1] negative: spin left, positive: spin right.
    @type va: C{float}
    """
    p = 1 if progressive else 0
    at("PCMD", seq, [p, float(lr), float(fb), float(vv), float(va)])

def at_ftrim(seq):
    """\
    Tell the drone it's lying horizontally.

    @param seq: Sequence number.
    @type seq: C{int}
    """
    at("FTRIM", seq, [])

def at_zap(seq, stream):
    """\
    Selects which video stream to send on the video UDP port.

    @param seq: Sequence number.
    @type seq: C{int}
    @param stream: Video stream to broadcast.
    @type stream: C{int}
    """
    # FIXME: improve parameters to select the modes directly
    at("ZAP", seq, [stream])

def at_config(seq, option, value):
    """\
    Set configuration parameters of the drone.

    @param seq: Sequence number.
    @type seq: C{int}
    @param option: Option.
    @type option: C{str}
    @param value: Value.
    @type value: C{str}
    """
    at("CONFIG", seq, [str(option), str(value)])

def at_comwdg(seq):
    """\
    Reset communication watchdog.

    @param seq: Sequence number.
    @type seq: C{int}
    """
    # FIXME: no sequence number
    at("COMWDG", seq, [])

def at_aflight(seq, flag):
    """\
    Makes the drone fly autonomously.

    @param seq: Sequence number.
    @type seq: C{int}
    @param flag: 1: start flight, 0: stop flight.
    @type flag: C{int}
    """
    at("AFLIGHT", seq, [flag])

def at_pwm(seq, m1, m2, m3, m4):
    """\
    Sends control values directly to the engines, overriding control loops.

    @param seq: Sequence number.
    @type seq: C{int}
    @param m1: -- front left command.
    @param m2: -- fright right command.
    @param m3: -- back right command.
    @param m4: -- back left command.
    """
    # FIXME: what type do mx have?
    raise NotImplementedError

def at_led(seq, anim, f, d):
    """\
    Control the drones LED.

    @param seq: Sequence number.
    @type seq: C{int}
    @param anim: Animation to play.
    @type anim: C{int}
    @param f: Frequence in HZ of the animation.
    @param d: Total duration in seconds of the animation.
    @type d: C{int}
    """
    raise NotImplementedError

def at_anim(seq, anim, d):
    """\
    Makes the drone execute a predefined movement (animation).

    @param seq: Sequence number.
    @type seq: C{int}
    @param anim: Animation to play.
    @type anim: C{int}
    @param d: Total duration in seconds of the animation.
    @type d: C{int}
    """
    at("ANIM", seq, [anim, d])

def at(command, seq, params):
    """\
    Send a command to the drone.

    @param command: The command.
    @type command: C{str}
    @param seq: Sequence number.
    @type seq: C{int}
    @param params: A list of elements which can be either int, float or string.
    @type params: C{list}
    """
    param_str = ''
    for p in params:
        if type(p) == int:
            param_str += ",%d" % p
        elif type(p) == float:
            param_str += ",%d" % f2i(p)
        elif type(p) == str:
            param_str += ',"'+p+'"'
    msg = "AT*%s=%i%s\r" % (command, seq, param_str)
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.sendto(msg, ("192.168.1.1", ARDRONE_COMMAND_PORT))

def f2i(f):
    """\
    Interpret IEEE-754 floating-point value as signed integer.

    @param f: Floating point value.
    @type f: C{float}
    @return: The integer value.
    @rtype: C{int}
    """
    return unpack('i', pack('f', f))[0]
