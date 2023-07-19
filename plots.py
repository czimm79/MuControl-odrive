import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import numpy as np
import pyqtgraph.opengl as gl


class SignalPlot(pg.PlotWidget):
    """
    """
    keyPressed = QtCore.pyqtSignal(object)

    def __init__(self, curve_colors = ['b', 'g', 'r']):
        super().__init__()
        self.line_width = 4
        self.curve_colors = curve_colors
        self.pens = [pg.mkPen(i, width=self.line_width) for i in self.curve_colors]

        self.setFocusPolicy(QtCore.Qt.StrongFocus)  # By default the plot is the keyboard focus
        self.showGrid(y=True)

        # self.disableAutoRange('y')

        # Set up curves
        self.data = np.zeros(100)
        self.curve = self.plot(self.data, pen=self.pens[0], clear=False)


    def keyPressEvent(self, event):
        """ When a key is pressed, pass it up to the PyQt event handling system. """
        super().keyPressEvent(event)
        self.keyPressed.emit(event.key())

    def on_new_data_update_plot(self, incomingData):
        """ Update plot."""

        self.data[:-1] = self.data[1:]  # shift data in the array one sample left
                                          # (see also: np.roll)
        self.data[-1] = incomingData  # update last point
        self.curve.setData(self.data, clear=False)


        # for i in range(0, np.size(incomingData)):  # For each entry in incomingData
        #     # Plot each value
        #     self.plot(incomingData, clear=False, pen=self.pens[i])


class MultiSignalPlot(pg.PlotWidget):
    """
    """
    keyPressed = QtCore.pyqtSignal(object)

    def __init__(self, curve_colors = ['b', 'g', 'r']):
        super().__init__()
        self.line_width = 4
        self.curve_colors = curve_colors
        self.pens = [pg.mkPen(i, width=self.line_width) for i in self.curve_colors]

        self.setFocusPolicy(QtCore.Qt.StrongFocus)  # By default the plot is the keyboard focus
        self.showGrid(y=True)

        # self.disableAutoRange('y')

        # Set up curves
        self.xdata = np.zeros(100)
        self.ydata = np.zeros(100)
        #self.zdata = np.zeros(100)

        self.xcurve = self.plot(self.xdata, pen=self.pens[0], clear=False)
        self.ycurve = self.plot(self.ydata, pen=self.pens[1], clear=False)
        #self.zcurve = self.plot(self.zdata, pen=self.pens[2], clear=False)

    def keyPressEvent(self, event):
        """ When a key is pressed, pass it up to the PyQt event handling system. """
        super().keyPressEvent(event)
        self.keyPressed.emit(event.key())

    def on_new_data_update_plot(self, incomingData):
        """ Update plot."""

        self.xdata[:-1] = self.xdata[1:]  # shift data in the array one sample left
                                          # (see also: np.roll)
        self.ydata[:-1] = self.ydata[1:]

        self.xdata[-1] = incomingData[0]  # update last point
        self.ydata[-1] = incomingData[1]

        self.xcurve.setData(self.xdata, clear=False)
        self.ycurve.setData(self.ydata, clear=False)

        # for i in range(0, np.size(incomingData)):  # For each entry in incomingData
        #     # Plot each value
        #     self.plot(incomingData, clear=False, pen=self.pens[i])

