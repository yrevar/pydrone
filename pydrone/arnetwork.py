"""
This module provides access to the data provided by the ARDrone.
"""


from select import select
from threading import Thread
from multiprocessing import Process
from socket import socket, AF_INET, SOCK_DGRAM
from struct import unpack_from, calcsize, error

from .arvideo import read_picture


ARDRONE_NAVDATA_PORT = 5554
ARDRONE_VIDEO_PORT = 5555

def decode_navdata(packet):
    """\
    Decode a navdata packet.

    @param packet: The packet.
    @type packet: C{int}
    @return: The decoded data.
    @rtype: C{dict}
    """
    offset = 0
    _ =  unpack_from("IIII", packet, offset)
    drone_state = dict()
    drone_state['fly_mask']             = _[1]       & 1 # FLY MASK : (0) ardrone is landed, (1) ardrone is flying
    drone_state['video_mask']           = _[1] >>  1 & 1 # VIDEO MASK : (0) video disable, (1) video enable
    drone_state['vision_mask']          = _[1] >>  2 & 1 # VISION MASK : (0) vision disable, (1) vision enable
    drone_state['control_mask']         = _[1] >>  3 & 1 # CONTROL ALGO (0) euler angles control, (1) angular speed control
    drone_state['altitude_mask']        = _[1] >>  4 & 1 # ALTITUDE CONTROL ALGO : (0) altitude control inactive (1) altitude control active
    drone_state['user_feedback_start']  = _[1] >>  5 & 1 # USER feedback : Start button state
    drone_state['command_mask']         = _[1] >>  6 & 1 # Control command ACK : (0) None, (1) one received
    drone_state['fw_file_mask']         = _[1] >>  7 & 1 # Firmware file is good (1)
    drone_state['fw_ver_mask']          = _[1] >>  8 & 1 # Firmware update is newer (1)
    drone_state['fw_upd_mask']          = _[1] >>  9 & 1 # Firmware update is ongoing (1)
    drone_state['navdata_demo_mask']    = _[1] >> 10 & 1 # Navdata demo : (0) All navdata, (1) only navdata demo
    drone_state['navdata_bootstrap']    = _[1] >> 11 & 1 # Navdata bootstrap : (0) options sent in all or demo mode, (1) no navdata options sent
    drone_state['motors_mask']          = _[1] >> 12 & 1 # Motor status : (0) Ok, (1) Motors problem
    drone_state['com_lost_mask']        = _[1] >> 13 & 1 # Communication lost : (1) com problem, (0) Com is ok
    drone_state['vbat_low']             = _[1] >> 15 & 1 # VBat low : (1) too low, (0) Ok
    drone_state['user_el']              = _[1] >> 16 & 1 # User Emergency Landing : (1) User EL is ON, (0) User EL is OFF
    drone_state['timer_elapsed']        = _[1] >> 17 & 1 # Timer elapsed : (1) elapsed, (0) not elapsed
    drone_state['angles_out_of_range']  = _[1] >> 19 & 1 # Angles : (0) Ok, (1) out of range
    drone_state['ultrasound_mask']      = _[1] >> 21 & 1 # Ultrasonic sensor : (0) Ok, (1) deaf
    drone_state['cutout_mask']          = _[1] >> 22 & 1 # Cutout system detection : (0) Not detected, (1) detected
    drone_state['pic_version_mask']     = _[1] >> 23 & 1 # PIC Version number OK : (0) a bad version number, (1) version number is OK
    drone_state['atcodec_thread_on']    = _[1] >> 24 & 1 # ATCodec thread ON : (0) thread OFF (1) thread ON
    drone_state['navdata_thread_on']    = _[1] >> 25 & 1 # Navdata thread ON : (0) thread OFF (1) thread ON
    drone_state['video_thread_on']      = _[1] >> 26 & 1 # Video thread ON : (0) thread OFF (1) thread ON
    drone_state['acq_thread_on']        = _[1] >> 27 & 1 # Acquisition thread ON : (0) thread OFF (1) thread ON
    drone_state['ctrl_watchdog_mask']   = _[1] >> 28 & 1 # CTRL watchdog : (1) delay in control execution (> 5ms), (0) control is well scheduled
    drone_state['adc_watchdog_mask']    = _[1] >> 29 & 1 # ADC Watchdog : (1) delay in uart2 dsr (> 5ms), (0) uart2 is good
    drone_state['com_watchdog_mask']    = _[1] >> 30 & 1 # Communication Watchdog : (1) com problem, (0) Com is ok
    drone_state['emergency_mask']       = _[1] >> 31 & 1 # Emergency landing : (0) no emergency, (1) emergency
    data = dict()
    data['drone_state'] = drone_state
    data['header'] = _[0]
    data['seq_nr'] = _[2]
    data['vision_flag'] = _[3]
    offset += calcsize("IIII")
    while 1:
        try:
            id_nr, size =  unpack_from("HH", packet, offset)
            offset += calcsize("HH")
        except error:
            break
        values = []
        for i in range(size - calcsize("HH")):
            values.append(unpack_from("c", packet, offset)[0])
            offset += calcsize("c")
        # navdata_tag_t in navdata-common.h
        if id_nr == 0:
            values = unpack_from("IIfffIfffI", "".join(values))
            values = dict(zip(['ctrl_state', 'battery', 'theta', 'phi', 'psi',
                'altitude', 'vx', 'vy', 'vz', 'num_frames'], values))
            # convert the millidegrees into degrees and round to int, as they
            # are not so precise anyways
            for i in 'theta', 'phi', 'psi':
                values[i] = int(values[i] / 1000)
                #values[i] /= 1000
        data[id_nr] = values
    return data

class ARDroneNetworkProcess(Process):
    """\
    ARDrone Network Process.

    This process collects data from the video and navdata port, converts the
    data and sends it to the IPCThread.
    """

    def __init__(self, nav_pipe, video_pipe, com_pipe):
        """\
        Constructor.

        @param nav_pipe: Nav pipe.
        @type nav_pipe: L{multiprocessing.Pipe}
        @param video_pipe: Video pipe.
        @type video_pipe: L{multiprocessing.Pipe}
        @param com_pipe: Com pipe.
        @type com_pipe: L{multiprocessing.Pipe}
        """
        Process.__init__(self)
        self.nav_pipe = nav_pipe
        self.video_pipe = video_pipe
        self.com_pipe = com_pipe

    def run(self):
        """\
        Start the ARDroneNetworkProcess activity.
        """
        video_socket = socket(AF_INET, SOCK_DGRAM)
        video_socket.setblocking(0)
        video_socket.bind(('', ARDRONE_VIDEO_PORT))
        video_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', ARDRONE_VIDEO_PORT))

        nav_socket = socket(AF_INET, SOCK_DGRAM)
        nav_socket.setblocking(0)
        nav_socket.bind(('', ARDRONE_NAVDATA_PORT))
        nav_socket.sendto("\x01\x00\x00\x00", ('192.168.1.1', ARDRONE_NAVDATA_PORT))

        stopping = False
        while not stopping:
            inputready, outputready, exceptready = select([nav_socket,
                video_socket, self.com_pipe], [], [])
            for i in inputready:
                if i == video_socket:
                    while 1:
                        try:
                            data = video_socket.recv(65535)
                        except IOError:
                            # we consumed every packet from the socket and
                            # continue with the last one
                            break
                    w, h, image, t = read_picture(data)
                    self.video_pipe.send(image)
                elif i == nav_socket:
                    while 1:
                        try:
                            data = nav_socket.recv(65535)
                        except IOError:
                            # we consumed every packet from the socket and
                            # continue with the last one
                            break
                    navdata = decode_navdata(data)
                    self.nav_pipe.send(navdata)
                elif i == self.com_pipe:
                    _ = self.com_pipe.recv()
                    stopping = True
                    break
        video_socket.close()
        nav_socket.close()


class IPCThread(Thread):
    """\
    Inter Process Communication Thread.

    This thread collects the data from the ARDroneNetworkProcess and forwards
    it to the ARDreone.
    """

    def __init__(self, drone):
        """\
        Constructor.

        @param drone: The drone being controlled.
        @type drone: L{pydrone.libardrone.ARDrone}
        """
        Thread.__init__(self)
        self.drone = drone
        self.stopping = False

    def run(self):
        """\
        Start the IPCThread activity.
        """
        while not self.stopping:
            inputready, outputready, exceptready = select(
                [self.drone.video_pipe, self.drone.nav_pipe], [], [], 1)
            for i in inputready:
                if i == self.drone.video_pipe:
                    while self.drone.video_pipe.poll():
                        image = self.drone.video_pipe.recv()
                    self.drone.image = image
                elif i == self.drone.nav_pipe:
                    while self.drone.nav_pipe.poll():
                        navdata = self.drone.nav_pipe.recv()
                    self.drone.navdata = navdata

    def stop(self):
        """\
        Stop the IPCThread activity.
        """
        self.stopping = True

