# Public Libraries
from xml.dom.minidom import Attr
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import sys
from time import sleep
from misc_functions import qtsleep

# Custom modules
from threads.DataGenerator import Generator
from threads.Controller import ControllerThread
from threads.ODriveController import ODriveController
from parametertree import MyParamTree
from settings import SettingsWindow
from plots import SignalPlot

debug_mode = False # Switch to either use NI threads or a random data generator.
fbs_mode = False  # Switch to use either the PyQt5 app starting or the FBS container


class MyWindow(QtGui.QMainWindow):
    """ The main window of the application.

    This class is the parent to all the widgets inside of it. The grid layout of the UI is described here. This class
    also serves as a "middle man" for communication between threads. e.g. data from the readThread is passed here and
    then passed to the plot widget.

    Attributes:
        config: instantiated version of the SettingsWindow class located in settings.py
    """

    def __init__(self):
        super().__init__()  # Inherit everything from the Qt "QMainWindow" class

        # Instantiate class in settings.py which contains the settings UI AND the persistent QSettings values
        self.config = SettingsWindow()
        
        # Style
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=True)

        # Call setup methods below
        self.initUI()
        self.initThreads(self.config)

        self.p1.keyPressed.connect(self.t.on_key)  # Connect keyPresses on signal plot to Param Tree

        # Delay to avoid constantly sending updates to odrive controller
        self.last_update = 0.2

    def initUI(self):
        """
        This method instantiates every widget and arranges them all inside the main window. This is where the
        puzzle pieces are assembled.
        """
        # General window properties
        # self.setWindowTitle('MuControl v1.0.3')
        self.resize(1280, 720)  # Non- maximized size
        self.setWindowState(QtCore.Qt.WindowMaximized)

        # Make menu bar at the top of the window
        mainMenu = self.menuBar()
        # mainMenu.setStyleSheet("""QMenuBar { background-color: #F0F0F0; }""")  # Makes the menu bar grey-ish
        fileMenu = mainMenu.addMenu('File')  # Adds the file button
        helpMenu = mainMenu.addMenu('Help')

        # Settings button
        settingsButton = QtGui.QAction("&Settings", self)
        settingsButton.setShortcut('Ctrl+Alt+S')
        settingsButton.triggered.connect(self.config.show)  # when the settings button is clicked, window is shown
        fileMenu.addAction(settingsButton)  # Adds the settings button to the file menu

        # Exit Button
        exitButton = QtWidgets.QAction('Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)

        # User Guide button in help menu
        userguideButton = QtGui.QAction("Open User Guide", self)
        userguideButton.setShortcut('Ctrl+H')
        userguideButton.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(
            "https://czimm79.github.io/mucontrol-userguide/index.html")))
        helpMenu.addAction(userguideButton)

        # Create an empty box to hold all the following widgets
        self.mainbox = QtGui.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = QtWidgets.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        # Instantiate the plots from plots.py
        self.p1 = SignalPlot(curve_colors=['r'])  # heading
        self.p1.setYRange(0, 360)
        self.p2 = SignalPlot(curve_colors=['g'])  # roboscope
        self.p2.setYRange(0, 30)
        self.p3 = SignalPlot(curve_colors=['b'])  # spinner
        self.p3.setYRange(0, 30)

        # Create control descriptions
        # self.keyboardlbl = QtWidgets.QLabel(
        #     '<h3> Keyboard Controls </h3>\
        #     <span style="font-size: 10pt;">To enable keyboard controls, left click once anywhere on the signal plot. </span> \
        #     <p> <strong> Toggle Output:  </strong> T; <strong> +Voltage Multiplier: </strong> W; <strong> -Voltage Multiplier: </strong> Q </p> \
        #     <p> <strong> +Frequency: </strong> G, <strong> -Frequency: </strong> F; <strong> +Camber: </strong> B; \
        #     <strong> -Camber: </strong> V; ,<strong> Toggle Swarm: </strong> U</p>'
        # )
        self.gamepadlbl = QtWidgets.QLabel(
            '<h3> Gamepad Controls </h3>\
            <span style="font-size: 10pt;">To enable gamepad controls, plug in the controller before starting the program. </span> \
            <p> <strong> Toggle Output:  </strong> Left Thumb Click; <strong> +Voltage Multiplier: </strong> RB; <strong> -Voltage Multiplier: </strong> LB </p> \
            <p> <strong> +Frequency: </strong> Y, <strong> -Frequency: </strong> X; <strong> +Camber: </strong> B; \
            <strong> -Camber: </strong> A; <strong> Toggle Swarm: </strong> START </p>'
        )
        # self.keyboardlbl.setFont(QtGui.QFont("Default", 11))  # Optionally, change font size
        # self.gamepadlbl.setFont(QtGui.QFont("Default", 11))

        # Create plot labels
        self.p1lbl = QtWidgets.QLabel('<b><u>Heading Angle</u></b>')
        self.p2lbl = QtWidgets.QLabel('<b><u>Roboscope Z (cm)</u></b>')
        self.p3lbl = QtWidgets.QLabel('<b><u>Magnet Rotation Frequency</u></b>')

        # Parameter Tree widget
        self.t = MyParamTree(self.config)  # From ParameterTree.py
        self.t.paramChange.connect(self.change)  # Connect the output signal from changes in the param tree to change

        # Add widgets to the layout in their proper positions
        layout.addWidget(self.p1lbl, 0, 0)
        layout.addWidget(self.p2lbl, 0, 1)
        layout.addWidget(self.p3lbl, 0, 2)
        layout.addWidget(self.p1, 1, 0)
        layout.addWidget(self.p2, 1, 1)
        layout.addWidget(self.p3, 1, 2)
        layout.addWidget(self.t, 3, 0, 1, 3)  # row, col, rowspan, colspan
        #layout.addWidget(self.keyboardlbl, 2, 0, 1, 3)
        layout.addWidget(self.gamepadlbl, 2, 0, 1, 3)
        

    def initThreads(self, config):
        """Initialize the readThread and writeThread using configurations.

        Args:
            config: The previously instantiated SettingsWindow class containing the persistent QSettings values

        """

        self.odriveThread = ODriveController()
        self.odriveThread.newheadingpos.connect(self.p1.on_new_data_update_plot)
        self.odriveThread.newrobopos.connect(self.p2.on_new_data_update_plot)
        self.odriveThread.newspinnervel.connect(self.p3.on_new_data_update_plot)
        self.odriveThread.start()
        qtsleep(3)  # wait for odrive to connect

        # Lastly, initialize and connect the controller input listening thread
        self.gamepadThread = ControllerThread()
        self.gamepadThread.newGamepadEvent.connect(self.t.on_gamepad_event)
        self.gamepadThread.start()
        self.gamepadThread.setPriority(QtCore.QThread.LowestPriority)



    def change(self, param, changes):
        """Parses the value change signals coming in from the Parameter Tree.

        When a parameter is changed in the Parameter Tree by the UI, keyboard, or gamepad, the Parameter Tree sends a
        signal to this method. The signal contains the param and changes args. This method uses if statements
        to filter the corresponding value changes and send them to their proper places.

        Args:
            param: Name of the parameter being changed
            changes: an iterable which contains one or more value change signals

        """
        for param, change, data in changes:
            path = self.t.p.childPath(param)
            isengaged = self.t.getTopLevelParamValue("Engage Motors")

            # Logic for sending changes to the odriveThread
            # Top branch parameters
            if path[0] == 'Engage Motors':
                self.toggle_control(data)
            
            elif path[0] == 'Control Mode':
                if data == 'Rolling':
                    self.odriveThread.mode = "Rolling"
                    # Update with current parameter tree vals
                    self.odriveThread.f = self.t.getParamValue("Frequency")
                    self.odriveThread.h = self.t.getParamValue("Heading")

                elif data == 'Pointing':
                    self.odriveThread.mode = "Pointing"
                    print("This functionality doesn't exist yet!")

            elif path[0] == 'Heading Filter Bandwidth':
                self.odriveThread.set_heading_filter_bandwidth(data)

            elif path[0] == 'Constants':
                if path[1] == 'Gain':
                    print("Functionality does not exist yet.")
                    #self.odriveThread.heading_pos_offset = data

            elif path[0] == 'Roboscope Control':
                if path[1] == 'Z':
                    Z_current = self.t.getParamValue("Z", branch="Roboscope Control")
                    self.odriveThread.z = Z_current
                    self.odriveThread.update_roboscope()

            # Dumb Rolling
            elif (path[1] == 'Frequency'):
                self.odriveThread.f = data
                self.odriveThread.update_magnet_rotation_rate()

            elif (path[1] == 'Camber') & (self.odriveThread.mode == "Rolling"):
                print("no camber functionality yet.")

            elif path[1] == 'Heading':
                self.odriveThread.h = data
                now = pg.ptime.time()

                time_elapsed = now - self.last_update
                if time_elapsed < 0.1:  # if a bunch of changes are made fast, skip updating
                    pass
                else:  # Continue along
                    self.last_update = now
                    self.odriveThread.update_heading()

            # Pointing
            elif (path[1] == "X") & (self.odriveThread.mode == "Pointing"):
                self.odriveThread.mdes[0] = data

            elif (path[1] == "Y") & (self.odriveThread.mode == "Pointing"):
                self.odriveThread.mdes[1] = data

            elif (path[1] == "Z") & (self.odriveThread.mode == "Pointing"):
                self.odriveThread.mdes[2] = data



    def toggle_control(self, data):
        """A sub-method that toggles whether the motors are engaged or idle..

        Args:
            data: a boolean, whether the checkbox is checked or not

        """
        if data is True:  # If the box is checked
            self.odriveThread.closed_loop()  # Turn on closed loop control

        elif data is False:  # if box is unchecked
            error_box = QtWidgets.QErrorMessage()
            error_box.setModal(True)  # Cannot do other things in the app while this window is open
            error_box.showMessage("Warning! Motors will free-spin and can DROP after this message is dismissed.")
            error_box.exec_()
            self.odriveThread.idle()  # release motors

    def error_handling(self, error_message):
        """When an error signal is sent to this method, show an error box with the message inside.

        Args:
            error_message: signal from either the writeThread or readThread containing the error message

        """
        error_box = QtWidgets.QErrorMessage()
        error_box.setModal(True)  # Cannot do other things in the app while this window is open
        error_box.showMessage(error_message)
        error_box.exec_()

    def closeEvent(self, evnt):
        """ This method runs when Qt detects the main window closing. Used to gracefully end threads.

        The purpose of this method is to try and gracefully close threads to avoid persisting processes or bugs with
        the National Instruments cards.

        Args:
            evnt: dummy variable, unused

        """
        # Close controller thread
        self.gamepadThread.running = False
        self.gamepadThread.exit()

        # turn magnet off and gracefully lower roboscope
        self.odriveThread.z = 0.2
        self.odriveThread.update_roboscope()
        self.odriveThread.f = 0
        self.odriveThread.update_magnet_rotation_rate()
        sleep(2)
        
        # data retriever
        self.odriveThread.dataretriever.running = False

        self.odriveThread.running = False
        self.odriveThread.idle()
        self.odriveThread.exit()
        print("closed threads.")
        sleep(0.5)

if __name__ == '__main__':

    if not fbs_mode:  # The normal way to start a PyQt app when Python is installed
        app = QtWidgets.QApplication([])  # Initialize application
        w = MyWindow()  # Instantiate my window
        w.show()  # Show it
        exit_code = app.exec_()

    elif fbs_mode:  # When housed in an exe, this boilerplate code from fbs is used instead.
        from fbs_runtime.application_context.PyQt5 import ApplicationContext

        appctxt = ApplicationContext()  # FBS : 1. Instantiate ApplicationContext
        w = MyWindow()  # Instantiate my window
        w.show()  # Show it
        exit_code = appctxt.app.exec_()  # FBS : 2. Invoke appctxt.app.exec_()

    sys.exit(exit_code)
