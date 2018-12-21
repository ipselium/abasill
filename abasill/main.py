#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright © 2016-2018 Cyril Desjouy <ipselium@free.fr>
#
# This file is part of abasill
#
# abasill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# abasill is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with abasill. If not, see <http://www.gnu.org/licenses/>.
#
#
# Creation Date : ven. 09 nov. 2018 15:22:09 CET
"""
-----------
DOCSTRING

@author: Cyril Desjouy
"""

import kivy
kivy.require('1.9.0')

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, AliasProperty, \
                            ListProperty, BooleanProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.garden.graph import LinePlot, MeshLinePlot, BarPlot
from kivy.clock import Clock
import threading
import time
import numpy as np
import re

try:
    import alsaaudio, audioop
    MIC = 1
except ModuleNotFoundError:
    MIC = 0


class MicrophoneLevel(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.busy = threading.Event()
        self.available = threading.Event()

    def run(self):
        """
        https://stackoverflow.com/questions/1936828/how-get-sound-input-from-microphone-in-python-and-process-it-on-the-fly
        """

        global levels

        # Open the device in nonblocking capture mode. The last argument could
        # just as well have been zero for blocking mode. Then we could have
        # left out the sleep call in the bottom of the loop
        if MIC:
            inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK)

            # Set attributes: Mono, 8000 Hz, 16 bit little endian samples
            inp.setchannels(1)
            inp.setrate(8000)
            inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

            # The period size controls the internal number of frames per period.
            # The significance of this parameter is documented in the ALSA api.
            # For our purposes, it is suficcient to know that reads from the device
            # will return this many frames. Each frame being 2 bytes long.
            # This means that the reads below will return either 320 bytes of data
            # or 0 bytes of data. The latter is possible because we are in nonblocking
            # mode.
        #    inp.setperiodsize(160)
            inp.setperiodsize(320)

            while True:

                self.available.wait()   # Block until flag is True

                # Read data from device
                l, data = inp.read()
                if l:
                    # Return the maximum of the absolute value of all samples in a
                    # fragment.
                    mx = audioop.rms(data, 2)
                    levels.append(mx)

                if len(levels) > 100:
                    levels = []


    def pause(self):
        self.available.clear()  # Reset flag to False

    def resume(self):
        self.available.set()    # Set flag to True


class FloatInput(TextInput):

    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


class BasePanel(Screen):

    c = 340.
    frequency = 340

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__time = 0
        self.dt = 1/100

    @property
    def time(self):
        self.__time += self.dt
        return self.__time

    def start(self, *args):
        self.ids.graph.add_plot(self.plot)
        self.clock = Clock.schedule_interval(self.get_value, 1/20)

    def stop(self):
        Clock.unschedule(self.clock)

    def switch_preset(self):
        pass


class MicrophonePanel(Screen):
    """
    Microphone Panel
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=2)

    def start(self):
        self.ids.graph.add_plot(self.plot)
        self.clock = Clock.schedule_interval(self.get_value, 1/24)

    def stop(self):
        Clock.unschedule(self.clock)

    def get_value(self, dt):
        self.plot.points = [(i, j/100) for i, j in enumerate(levels)]


class SeriesPanel(Screen):
    """
    Series Panel
    """

    presets = ['Series', 'Square', 'Triangle', 'Sawtooth']
    N = NumericProperty(1)
    parity = ListProperty(['All', 'Even', 'Odd'])
    f_i = StringProperty('1/i')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=3)
        self.t = np.linspace(0, 2, 1000)
        self.range = []
        self.__even = range(3, self.N, 2)
        self.__odd = range(2, self.N, 2)
        self.__all = range(2, self.N)

    @property
    def even(self):
        return range(2, self.N, 2)

    @property
    def odd(self):
        return range(3, self.N, 2)

    @property
    def all(self):
        return range(2, self.N)

    def start(self, *args):
        self.ids.graph.add_plot(self.plot)
        self.clock = Clock.schedule_interval(self.get_value, 1/20)

    def stop(self):
        Clock.unschedule(self.clock)

    def get_value(self, *args):
        s = np.sin(2*np.pi*self.t)
        if self.f_i in ['Bad expression', 'Bad values']:
            self.plot.points = []
        else:
            self.amp = lambda i: eval(self.f_i)
            for i in self.range:
                if type(self.amp(i)) != float:
                    self.f_i = 'Bad values'
                    return
                s += self.amp(i)*np.sin(2*np.pi*self.t*i)
            self.plot.points = [(self.t[i], j) for i, j in enumerate(s)]

    def check_f_i(self):
        if any(char not in 'i+-*/()' for char in self.f_i):
            self.f_i = 'Bad expression'

    def switch_parity(self):
        if self.ids.parity.text == self.parity[0]:
            self.range = self.all
        elif self.ids.parity.text == self.parity[1]:
            self.range = self.even
        elif self.ids.parity.text == self.parity[2]:
            self.range = self.odd

    def switch_preset(self):
        if self.ids.preset.text == self.presets[1]:
            self.f_i = '1/i'
            self.N = 100
            self.range = self.odd
            self.ids.parity.text = self.parity[2]

        elif self.ids.preset.text == self.presets[2]:
            self.f_i = '(-1)**((i-1)/2)/i**2'
            self.N = 100
            self.range = self.odd
            self.ids.parity.text = self.parity[2]

        elif self.ids.preset.text == self.presets[3]:
            self.f_i = '1/i'
            self.N = 100
            self.range = self.even
            self.ids.parity.text = self.parity[0]

        else:
            self.f_i = '1/i'
            self.N = 1
            self.range = []
            self.ids.parity.text = self.parity[0]


class OlaPanel(BasePanel):
    """
    Ola Panel
    """

    T = NumericProperty(0.6)
    tau = NumericProperty(0.06)
    vsup = NumericProperty(0)
    cwave = NumericProperty(0)
    presets = ["La Ola", 'Fast Motion', 'Slow Motion']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = BarPlot(color=[0., 0.29, 0.49, 1], bar_width=5)
        self.Ns = 50

    def get_value(self, *args):
        self.cwave = 1/self.tau
        self.vsup = 1/self.T
        s = self.Ola(self.time, self.Ns, self.T, self.tau)
        self.plot.points = [(i, j) for i, j in enumerate(s)]

    @staticmethod
    def Ola(t, Ns, T, tau):
        """
        """
        y = np.zeros(Ns)
        for i in range(Ns):
            y[i] = np.sin(2*np.pi*(t-i*tau)/T) + 1
        return y

    def switch_preset(self):
        if self.ids.preset.text == self.presets[0]:
            self.T = 0.6
            self.tau = 0.06

        elif self.ids.preset.text == self.presets[1]:
            self.T = 0.5
            self.tau = 0.01

        elif self.ids.preset.text == self.presets[2]:
            self.T = 1
            self.tau = 0.01


class SinePanel(BasePanel):
    """
    Sine Panel : Basic Operations with sinus function
    """

    f1 = NumericProperty(10)
    f2 = NumericProperty(10)
    A1 = NumericProperty(0.5)
    A2 = NumericProperty(0.5)
    t1 = NumericProperty(0)
    t2 = NumericProperty(0)
    operators = ListProperty(['+', '-', '*'])
    presets = ["Operations with sine functions", 'Acoustic Beat']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot1 = LinePlot(color=[1., 0.65, 0., 1], line_width=1)
        self.plot2 = LinePlot(color=[1., 1., 0., 1], line_width=1)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=3)

    def start(self, *args):
        self.ids.graph.add_plot(self.plot1)
        self.ids.graph.add_plot(self.plot2)
        self.ids.graph.add_plot(self.plot)
        self.clock = Clock.schedule_interval(self.get_value, 1/50)

    def get_value(self, *args):
        t = np.linspace(0, 1, 1000)
        s1 = self.A1*np.sin(2*np.pi*self.f1*t + self.t1)
        s2 = self.A2*np.sin(2*np.pi*self.f2*t + self.t2)
        stot = eval('s1 {} s2'.format(self.ids.operator.text))
        self.plot.points = [(t[i], j) for i, j in enumerate(stot)]
        if self.ids.disp1.active:
            self.plot1.points = [(t[i], j) for i, j in enumerate(s1)]
        else:
            self.plot1.points = []
        if self.ids.disp2.active:
            self.plot2.points = [(t[i], j) for i, j in enumerate(s2)]
        else:
            self.plot2.points = []

    def switch_preset(self):
        if self.ids.preset.text == self.presets[0]:
            self.f1 = 1
            self.f2 = 1
            self.A1 = 1
            self.A2 = 1
            self.t1 = 0
            self.t2 = 0
            self.ids.operator.text = self.operators[0]

        elif self.ids.preset.text == self.presets[1]:
            self.f1 = 20
            self.f2 = 22
            self.A1 = 1
            self.A2 = 1
            self.t1 = 0
            self.t2 = 0
            self.ids.operator.text = self.operators[0]


class InterferencePanel(BasePanel):
    """
    InterferencePanel Panel
    """
    A = NumericProperty(0.2)
    B = NumericProperty(0.4)
    dispB = BooleanProperty(False)
    presets = ListProperty(['Interferences',
        'Progressive wave (+)', 'Progressive Wave (-)', 'Stationnary Wave'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot1 = LinePlot(color=[1., 0.65, 0., 1], line_width=1)
        self.plot2 = LinePlot(color=[1., 1., 0., 1], line_width=1)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=3)
        self.__time = 0
        self.dt = 1/50000
        self.space = np.linspace(0, 1, 1000)

    def start(self, *args):
        self.ids.graph.add_plot(self.plot1)
        self.ids.graph.add_plot(self.plot2)
        self.ids.graph.add_plot(self.plot)
        self.clock = Clock.schedule_interval(self.get_value, 1/50)

    def get_value(self, *args):
        k = 2*np.pi*self.frequency/self.c
        omega = 2*np.pi*self.frequency
        s1 = self.A*np.exp(1j*k*self.space)*np.exp(1j*omega*self.time)
        s2 = self.B*np.exp(-1j*k*self.space)*np.exp(1j*omega*self.time)
        s = s1 + s2
        self.plot.points = [(self.space[i], j) for i, j in enumerate(s.real)]
        if self.ids.dispA.active:
            self.plot1.points = [(self.space[i], j) for i, j in enumerate(s1.real)]
        else:
            self.plot1.points = []
        if self.ids.dispB.active:
            self.plot2.points = [(self.space[i], j) for i, j in enumerate(s2.real)]
        else:
            self.plot2.points = []

    def switch_preset(self):
        if self.ids.preset.text == self.presets[1]:
            self.A = 1
            self.B = 0
        elif self.ids.preset.text == self.presets[2]:
            self.A = 0
            self.B = 1
        elif self.ids.preset.text == self.presets[3]:
            self.A = 1
            self.B = 1
        else:
            self.A = 0.2
            self.B = 0.4


class SectionPanel(BasePanel):
    """
    SectionPanel : Section change Animations
    """

    Smin = 1
    Smax = 100
    S1 = NumericProperty(1)
    S2 = NumericProperty(1)
    Rp = NumericProperty(0)
    Tp = NumericProperty(1)
    presets = ListProperty(['Section Change', 'Large -> Small', 'Small -> Large'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=2)
        self.sep = LinePlot(color=[1, 0, 0, 1], line_width=4)
        self.__time = 0
        self.dt = 1/50000
        self.omega = 2*np.pi*self.frequency
        self.x1 = np.linspace(-2, 0, 1000)
        self.x2 = np.linspace(0, 2, 1000)
        self.xtot = np.concatenate([self.x1, self.x2])

    def start(self, *args):
        self.ids.graph.add_plot(self.plot)
        self.ids.graph.add_plot(self.sep)
        self.sep.points = [(0, j) for j in self.xtot]
        self.clock = Clock.schedule_interval(self.get_value, 1/50)

    def get_value(self, *args):
        A = 1
        self.Rp = (self.S1 - self.S2)/(self.S1 + self.S2)
        self.Tp = 2*self.S1/(self.S1 + self.S2)
        k = self.omega/self.c
        p1 = A*(np.exp(-1j*k*self.x1)
                + self.Rp*np.exp(1j*k*self.x1))*np.exp(1j*self.omega*self.time)
        p2 = A*self.Tp*np.exp(-1j*k*self.x2)*np.exp(1j*self.omega*self.time)
        ptot = np.concatenate([p1, p2])
        self.plot.points = [(self.xtot[i], j) for i, j in enumerate(ptot.real)]

    def switch_preset(self):
        if self.ids.preset.text == self.presets[1]:
            self.S1 = 30
            self.S2 = 10
        elif self.ids.preset.text == self.presets[2]:
            self.S1 = 10
            self.S2 = 30
        else:
            self.S1 = 1
            self.S2 = 1


class MediaPanel(BasePanel):
    """
    MediaPanel : Interface between two media
    """

    rho_min = 0.7
    rho_max = 1500
    c_min = 290
    c_max = 5000
    rho1 = NumericProperty(1.2)
    rho2 = NumericProperty(1.2)
    c1 = NumericProperty(340)
    c2 = NumericProperty(340)
    Rp = NumericProperty(0)
    Tp = NumericProperty(1)
    presets = ListProperty(['Two Media', 'Water -> Air', 'Air -> Water'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=2)
        self.sep = LinePlot(color=[1, 0, 0, 1], line_width=4)
        self.__time = 0
        self.dt = 1/50000
        self.omega = 2*np.pi*self.frequency
        self.x1 = np.linspace(-2, 0, 1000)
        self.x2 = np.linspace(0, 2, 1000)
        self.xtot = np.concatenate([self.x1, self.x2])

    def start(self, *args):
        self.ids.graph.add_plot(self.plot)
        self.ids.graph.add_plot(self.sep)
        self.sep.points = [(0, j) for j in self.xtot]
        self.clock = Clock.schedule_interval(self.get_value, 1/50)

    def get_value(self, *args):
        A = 1
        Zc1 = self.c1*self.rho1
        Zc2 = self.c2*self.rho2
        self.Rp = (Zc2 - Zc1)/(Zc1 + Zc2)
        self.Tp = 2*Zc2/(Zc1 + Zc2)
        k1 = self.omega/self.c1
        k2 = self.omega/self.c2
        p1 = A*(np.exp(-1j*k1*self.x1)
                + self.Rp*np.exp(1j*k1*self.x1))*np.exp(1j*self.omega*self.time)
        p2 = A*self.Tp*np.exp(-1j*k2*self.x2)*np.exp(1j*self.omega*self.time)
        ptot = np.concatenate([p1, p2])
        self.plot.points = [(self.xtot[i], j) for i, j in enumerate(ptot.real)]

    def switch_preset(self):
        if self.ids.preset.text == self.presets[1]:
            self.rho1 = 1000
            self.rho2 = 1.2
            self.c1 = 1500
            self.c2 = 340
        elif self.ids.preset.text == self.presets[2]:
            self.rho1 = 1.2
            self.rho2 = 1000
            self.c1 = 340
            self.c2 = 1500
        else:
            self.rho1 = 1.2
            self.rho2 = 1.2
            self.c1 = 340
            self.c2 = 340


class Home(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _ = Clock.schedule_once(self.anim)

    def anim(self, *args):
        self.ids.blabel.animate()
        self.ids.tlabel.animate()


class Screens(ScreenManager):
    pass


class AcousticBasicIllustration(App):

    title_bcolor = [0., 0.29, 0.49, 1]
    title_fsize = 36
    title_font = 'Domestic_Manners'   # 'Junkyard', 'TSCu_Comic', 'DroidSansMono', 'Balker'
    txt_font = 'Domestic_Manners'
    txt_fsize = 30
    btn_font = 'Domestic_Manners'
    btn_fsize = 30
    btn_bg = list(np.array(title_bcolor)/0.35)
    transition_time = 0.5

    def __init__(self, get_level, **kwargs):
        super().__init__(**kwargs)
        self.get_level = get_level
        self.get_level.pause()

    def build(self):
        return Builder.load_file('acbi.kv')

    def close_menu(self):
        box = BoxLayout(orientation = 'vertical', padding = (10))
        box.add_widget(Label(text = "Are you sure you want to quit?",
                            font_name=self.txt_font,
                            font_size=self.txt_fsize))
        popup = Popup(title='Acoustic Basics', title_size=self.title_fsize,
                        title_font=self.title_font,
                        title_align='center', content=box,
                        size_hint=(None, None), size=(470, 400),
                        auto_dismiss=True)
        box.add_widget(Button(text = "YES, CLOSE THE APP!",  on_release=self.stop))
        box.add_widget(Button(text = "NO, I WANT TO GO BACK", on_release=popup.dismiss))
        popup.open()


if __name__ == "__main__":

    # Get microphone in a thread
    levels = []  # store levels of microphone
    get_level = MicrophoneLevel()
    get_level.daemon = True
    get_level.start()

    # Run App
    AcousticBasicIllustration(get_level).run()
