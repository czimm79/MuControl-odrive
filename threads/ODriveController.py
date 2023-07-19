import numpy as np
from pyqtgraph.Qt import QtCore
from misc_functions import qtsleep, unit_vector
import odrive
from odrive.enums import *
import fibre.libfibre
from time import sleep

class DataRetriever(QtCore.QThread):
    """ Sub-thread of ODriveController that reads the current position of the axes.
    """
    newDataSUB = QtCore.pyqtSignal(object)

    def __init__(self, ows):
        super().__init__()
        self.running = False

        self.ows = ows

    def read_pos(self, axis):
        return axis.encoder.pos_estimate

    def read_vel(self, axis):
        return axis.encoder.vel_estimate

    def run(self):
        """ This method runs when the thread is started."""
        self.running = True
        while self.running:
            ow3pos = self.read_pos(self.ows[2])  # heading
            ow2pos = self.read_pos(self.ows[1])  # roboscope
            ow1vel = self.read_vel(self.ows[0])  # spinner
            self.newDataSUB.emit([ow3pos, ow2pos, ow1vel])
            qtsleep(0.1)
            

class ODriveController(QtCore.QThread):
    """Thread for sending and recieving commands to the ODrive.

    """
    newheadingpos = QtCore.pyqtSignal(object)  # Designates that this class will have an output signal
    newrobopos = QtCore.pyqtSignal(object)
    newspinnervel = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.running = False

        self.mode = "Rolling"

        # Gear Ratios
        self.magnet_gr = 3/10 # 4/15 for old 3d printed pulley
        self.heading_gr = 3/19
        self.roboscope_cmperturn = 7.10

        # Heading Gear Position Offset
        self.initial_heading = 138.5

        # Current velocity and position
        self.f = 0.0
        self.h = 138.5

        # Roboscope distance
        self.z = 0.0  # distance the roboscope has moved
        


    def run(self):
        """ This method runs when the thread is started."""

        # Find a connected ODrive (this will block until you connect one)
        print("Finding ODrives...")
        drv1 = odrive.find_any(serial_number="208739A04D4D")
        drv2 = odrive.find_any(serial_number="207539694D4D")


        self.ow3 = drv1.axis0  # heading
        self.ow1 = drv1.axis1  # spinner
        self.ow2 = drv2.axis0  # roboscope
        
        self.ows = [self.ow1, self.ow2, self.ow3]
        print("found ows")

        self.ow1.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
        self.ow3.controller.config.control_mode = CONTROL_MODE_POSITION_CONTROL
        self.ow2.controller.config.control_mode = CONTROL_MODE_POSITION_CONTROL

        # apply filter for roboscope position control
        self.ow2.controller.config.input_filter_bandwidth = 4.0
        self.ow2.controller.config.input_mode = INPUT_MODE_POS_FILTER

        # apply filter for heading position control
        self.ow3.controller.config.vel_limit = 15
        self.ow3.controller.config.input_filter_bandwidth = 6.0
        self.ow3.controller.config.input_mode = INPUT_MODE_POS_FILTER

        #self.ow3.controller.config.input_mode = INPUT_MODE_PASSTHROUGH

        self.update_heading()
        self.update_magnet_rotation_rate()

        self.initial_robopos = self.ow2.encoder.pos_estimate
        self.robopos = self.initial_robopos

        # open a reading thread
        self.dataretriever = DataRetriever(self.ows)
        self.dataretriever.newDataSUB.connect(self.pass_data_up)
        self.dataretriever.start()

    def set_heading_filter_bandwidth(self, b):
        self.ow3.controller.config.input_filter_bandwidth = b

    def closed_loop(self):
        """Set motors to closed loop control."""
        for ow in self.ows:
            ow.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL

    def idle(self):
        """Release motors."""
        for ow in self.ows:
            ow.requested_state = AXIS_STATE_IDLE

    def update_magnet_rotation_rate(self):
        """Send velocity command to a the motor spinning the magnet given local variable f (Hz). Convert according to the gear ratio."""
        self.ow1.controller.input_vel = self.f / self.magnet_gr

    def update_heading(self):
        """Send position command to a heading gear."""
        # + self.heading_pos_offset 138.5 + requested_heading * self.heading_gr * 360 
        self.ow3.controller.input_pos = (self.initial_heading - self.h) / (self.heading_gr * 360)

    def update_roboscope(self):
        self.ow2.controller.input_pos = (self.z / self.roboscope_cmperturn) + self.initial_robopos

    def pass_data_up(self, incomingData):
        """ Decompose odrive axis readings from subthread DataRetriever into heading degree, roboscope distance, and spinner hz.
        """
        # Heading
        # 0 is 138.5
        #self.newheadingpos.emit(360 - (360-self.initial_heading + incomingData[0] * self.heading_gr * 360))
        self.newheadingpos.emit(self.initial_heading - incomingData[0] * self.heading_gr * 360)

        # Roboscope
        self.newrobopos.emit((incomingData[1] - self.initial_robopos) * self.roboscope_cmperturn)
        #print((incomingData[1] - self.initial_robopos) * self.roboscope_cmperturn)

        # Magnet (spinner)
        self.newspinnervel.emit(incomingData[2] * self.magnet_gr)

