from pyqtgraph.Qt import QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
from PyQt5.QtCore import Qt
import numpy as np
from misc_functions import qtsleep

class MyParamTree(ParameterTree):
    """The parameter tree widget that lives in the bottom of the main window.

    This is where the current parameters of the application live. When a parameter here is changed by ANY method
    (UI, gamepad, keyboard), this object sends a signal to the MainWindow to get forward to the salient thread/object.
    The values are initialized from the config parameter passed in when instantiating this object.

    Attributes:
        params: a nested dictionary which contains the visable and edit-able parameters during program run-time
        p: the actual parameter tree object that contains the values

    """
    paramChange = QtCore.pyqtSignal(object, object)  # MyParamTree outputs a signal with param and changes.

    def __init__(self, config):
        super().__init__()
        self.r0 = 33.78  # cm
        self.Zlims = (0.0, 27.0)
        self.rlims = (self.r0-self.Zlims[1], self.r0-self.Zlims[0])
        self.params = [
            {'name': 'Engage Motors', 'type': 'bool', 'value': False, 'tip': "Checked = Closed loop control, Unchecked = idle"},
            {'name': 'Control Mode', 'type': 'list', 'values': ['Rolling', "Pointing"], 'value': 'Rolling'},
            {'name': 'Heading Filter Bandwidth', 'type':'float', 'value': 6.0},
            ComplexParameter(name='Roboscope Control', Zlims=self.Zlims, rlims=self.rlims, r0 = self.r0),
            {'name': 'Rolling', 'type': 'group', 'children': [
                {'name': 'Frequency', 'type': 'float', 'value': 0, 'step': 1, 'siPrefix': True, 'suffix': 'Hz'},
                {'name': 'Heading', 'type': 'float', 'value': 138.5, 'step': 45, 'siPrefix': True, 'suffix': '°'},  # config.defaults['camber']
                {'name': 'Swarm Mode', 'type': 'list', 'values': ['Rolling', 'Corkscrew', 'Flipping', 'Switchback'], 'value': 'Rolling'}
            ]},
            {'name': 'Pointing', 'type': 'group', 'children': [
                {'name': 'X', 'type': 'float', 'value': 1, 'step': 0.1},
                {'name': 'Y', 'type': 'float', 'value': 0, 'step': 0.1},
                {'name': 'Z', 'type': 'float', 'value': 0, 'step': 0.1},
            ]},
            {'name': 'Constants', 'type': 'group', 'children': [
                {'name': 'Gain', 'type': 'float', 'value': 0, 'step': 0.1}
            ]}
        ]

        # Create my parameter object and link it to methods
        self.p = Parameter.create(name='self.params', type='group', children=self.params)
        self.setParameters(self.p, showTop=False)

        self.p.sigTreeStateChanged.connect(self.sendChange)  # When the params change, send to method to emit.

        # Connect keyPresses
        self.setFocusPolicy(Qt.NoFocus)

        self.running_explode = False

    def sendChange(self, param, changes):
        self.paramChange.emit(param, changes)

    # Convenience methods for modifying parameter values.
    def getParamValue(self, child, branch='Rolling'):
        """Get the current value of a parameter."""
        return self.p.param(branch, child).value()

    def getTopLevelParamValue(self, name):
        """Get the current value of a top level parameter"""
        return self.p.param(name).value()

    def setTopLevelParamValue(self, name, value):
        """Set value of a top level parameter"""
        return self.p.param(name).setValue(value)

    def setParamValue(self, child, value, branch='Rolling'):
        """Set the current value of a parameter."""
        return self.p.param(branch, child).setValue(value)

    def stepParamValue(self, child, delta, limits=None, branch='Rolling'):
        """Change a parameter by a delta. Can be negative or positive."""
        if limits is not None:
            param = self.p.param(branch, child)
            curVal = param.value()
            newVal = curVal + delta
            if (newVal < limits[1]) & (newVal > limits[0]):
                return param.setValue(newVal)
            elif newVal >= limits[1]:
                print(f"{newVal} is greater than {limits[1]}")
                return param.setValue(limits[1])
            elif newVal <= limits[0]:
                print(f"{newVal} is less than {limits[0]}")
                return param.setValue(limits[0])
            else:
                print(f"this shouldn't happen, newVal={newVal}, limits={limits}")
        else:
            param = self.p.param(branch, child)
            curVal = param.value()
            newVal = curVal + delta
            return param.setValue(newVal)

    def on_key(self, key):
        """ On a keypress on the plot widget, forward the keypress to the correct function below."""
        qtk = QtCore.Qt
        # Its necessary to have this func map because the key is simply an integer I need to check against
        # the key dictionary in QtCore.Qt.
        func_map ={
            qtk.Key_Left: self.Key_Left,
            qtk.Key_Right: self.Key_Right,
            qtk.Key_Up: self.Key_Up,
            qtk.Key_Down: self.Key_Down,
            qtk.Key_G: self.Key_G,
            qtk.Key_F: self.Key_F,
            qtk.Key_B: self.Key_B,
            qtk.Key_V: self.Key_V,
            qtk.Key_Q: self.Key_Q,
            qtk.Key_W: self.Key_W,
            qtk.Key_T: self.Key_T,
            qtk.Key_U: self.Key_U
        }
        func = func_map.get(key, lambda: 'Not bound yet')
        return func()


    def Key_Left(self):
        self.setParamValue('Heading', 180)

    def Key_Right(self):
        self.setParamValue('Heading', 0)

    def Key_Up(self):
        self.setParamValue('Heading', 90)

    def Key_Down(self):
        self.setParamValue('Heading', 270)

    def Key_G(self):
        self.stepParamValue('Frequency', 1)

    def Key_F(self):
        self.stepParamValue('Frequency', -1)

    def Key_B(self):  # also controller B
        self.setParamValue('Heading', 225)
        self.setParamValue('r', 8.3, branch="Roboscope Control")

    def Key_V(self):  # also controller A
        # capillary
        #self.setParamValue('Heading', 135)
        #self.setParamValue("r", 11.3, branch="Roboscope Control")
        
        #switchback toggle
        self.toggle_switchback()

    def Key_Q(self):
        self.stepParamValue('Z', -1.0, branch="Roboscope Control", limits=self.Zlims)

    def Key_W(self):
        self.stepParamValue('Z', 1.0, branch="Roboscope Control", limits=self.Zlims)

    def Key_T(self):
        """Toggles the toggle value"""
        # TODO Change so getParamValue can access the top level parameters.
        cur = self.p.param("Engage Motors").value()

        set = not cur

        self.p.param("Engage Motors").setValue(set)

    def Key_U(self):  # also start
        #self.setParamValue('Heading', 225)
        self.setParamValue("Z", 0.2, branch="Roboscope Control")

    def explode(self):
        """Explode the wheel by applying an orthogonal camber angle briefly."""
        camber = self.getParamValue("Camber")
        heading = self.getParamValue('Heading')
        ortho = camber - 90
        time = 0.2  # default 0.2

        # Tilt
        self.setParamValue('Camber', ortho)
        if np.abs(ortho) > 91:
            self.setParamValue('Heading', (heading - 180) % 360)

        qtsleep(time)  # sleep using PyQt5


        # Reset
        self.setParamValue('Camber', camber)
        if np.abs(ortho) > 91:
            self.setParamValue('Heading', heading)

    def toggle_explode(self):
        time_between_explodes = 0.5  # default 0.5
        self.running_explode = not self.running_explode
        while self.running_explode:
            self.explode()

            qtsleep(time_between_explodes)  # wait


    def switchback(self, time, driving_heading, wiggle_angle):
        """Switchback swarm execution code.

        Args:
            time (float): time constant between each turn
            driving_heading (int): uphill direction, overall movement direction
            wiggle_angle (int): deviation from centerline, determines angle of switchbacks
        """
        
        # turn left
        new_heading_1 = (driving_heading - wiggle_angle) % 360
        self.setParamValue('Heading', new_heading_1)
        qtsleep(time)  # sleep using PyQt5

        # turn right
        new_heading_2 = (driving_heading + wiggle_angle) % 360
        self.setParamValue('Heading', new_heading_2)
        qtsleep(time)

    def toggle_switchback(self):
        """Toggle the switchback field."""
        time_between_turn = 0.2
        wiggle_angle = 35

        self.running_explode = not self.running_explode
        driving_heading = self.getParamValue('Heading')
        while self.running_explode:
            self.switchback(time_between_turn, driving_heading, wiggle_angle)

            # After running climb at least once, the wheel is currently in `right` formation. To update the driving heading, we'll
            # read what it is now, and subtract the wiggle angle.
            # driving_heading = (self.getParamValue('Heading') - wiggle_angle) % 360

            # If there has been a change to the Heading from the user, update the driving heading.
            if driving_heading != (self.getParamValue('Heading') - wiggle_angle) % 360:
                driving_heading = self.getParamValue('Heading')

        # reset back to original heading
        self.setParamValue('Heading', driving_heading)


    def my_corkscrew(self):
        """My version of the corkscrew motion, described in signal_sandbox notebook."""
        print('running corkscrew')
        z_start = self.getParamValue('Heading')
        camber = self.getParamValue('Camber')
        camber_max = 70
        total_steps = 10  # Must be an even number
        camber_half_steps = (camber_max - camber) / (total_steps // 2)

        total_time = 1.0
        step_time = total_time / total_steps
        alpha = 0.4
        beta = total_time - alpha
        a = 360 / (2 * beta + alpha)

        time = np.linspace(0, total_time, num=total_steps)

        for seconds in time:  
            # Calculate z_phase given current time
            if seconds <= alpha:
                z_phase = a * seconds + z_start
            elif seconds > alpha:
                z_phase = 2 * a * seconds - a * alpha + z_start
            else:
                print('Something went terribly wrong with the corkscrew code.')

            # Calculate camber angle
            if seconds <= total_time / 2: # first half of time steps, bow down camber
                camber += camber_half_steps
            elif seconds > total_time / 2: # second half, rise up
                camber -= camber_half_steps

            print(z_phase)
            print(camber)
            self.setParamValue('Heading', z_phase % 360)  # set Heading
            self.setParamValue('Camber', camber)  # set camber

            # Wait
            qtsleep(step_time)

    def toggle_my_corkscrew(self):
        time_between_explodes = 0.01
        self.running_explode = not self.running_explode
        while self.running_explode:
            self.my_corkscrew()
            
            qtsleep(time_between_explodes)  # wait

        
    def toggle_swarm(self):
        swarm = self.getParamValue('Swarm Mode')

        if swarm == 'Corkscrew':
            self.toggle_my_corkscrew()
        elif swarm == 'Flipping':
            self.toggle_explode()
        elif swarm == 'Switchback':
            self.toggle_switchback()
        elif swarm == 'Rolling':
            return

    def set_heading_offset(self):
        self.setParamValue("Heading Offset", branch="Constants")

    def on_gamepad_event(self, gamepadEvent):
        """
        Parses the incoming gamepad events and forwards it to the appropriate keybind function below.
        For ease and less repetition, some buttons are forwarded to the keyboard functions.
        Args:
            gamepadEvent (list): incoming list from the controller class of format ['button', val]. ex. ['LJOY', 45]
        """
        func_map = {
            'X': self.Key_F,
            'Y': self.Key_G,
            'B': self.Key_B,
            'A': self.Key_V,
            'LEFT_SHOULDER': self.Key_Q,
            'RIGHT_SHOULDER': self.Key_W,
            'LEFT_THUMB': self.Key_T,
            'LJOY': self.Joystick_Left,
            'START': self.Key_U,
            'BACK': self.set_heading_offset
        }
        func = func_map.get(gamepadEvent[0], lambda: 'Not bound yet')
        if gamepadEvent[0] == 'LJOY':
            return func(gamepadEvent[1])
        else:
            return func()

    def Joystick_Left(self, degree):
        degree = (90 - degree) % 360  # convert joystick degrees to a heading that makes sense
        self.setParamValue('Heading', degree)

class ComplexParameter(pTypes.GroupParameter):
    def __init__(self, Zlims, rlims, r0, **opts):
        self.r0 = r0
        opts['type'] = 'bool'
        opts['value'] = True
        pTypes.GroupParameter.__init__(self, **opts)
        
        self.addChild({'name': 'Z', 'type': 'float', 'value': 0.00, 'step': 0.05, 'limits': Zlims})
        self.addChild({'name': 'r', 'type': 'float', 'value': self.r0, 'step': 0.05, 'limits': rlims})
        self.Z = self.param('Z')
        self.r = self.param('r')
        self.Z.sigValueChanged.connect(self.ZChanged)
        self.r.sigValueChanged.connect(self.rChanged)
        
    def ZChanged(self):
        self.r.setValue(self.r0 - self.Z.value(), blockSignal=self.rChanged)

    def rChanged(self):
        self.Z.setValue(self.r0 - self.r.value(), blockSignal=self.ZChanged)