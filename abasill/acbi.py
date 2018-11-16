#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright © 2016-2018 Cyril Desjouy <ipselium@free.fr>
#
# This file is part of {name}
#
# {name} is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# {name} is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with {name}. If not, see <http://www.gnu.org/licenses/>.
#
#
# Creation Date : ven. 09 nov. 2018 15:22:09 CET
# Last Modified : ven. 16 nov. 2018 17:47:26 CET
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
from kivy.garden.graph import LinePlot, MeshLinePlot
from kivy.clock import Clock
from threading import Thread
import alsaaudio, audioop
import queue
import numpy as np
import re

def get_microphone_level_alsa():
    """
    https://stackoverflow.com/questions/1936828/how-get-sound-input-from-microphone-in-python-and-process-it-on-the-fly
    """

    global levels

    # Open the device in nonblocking capture mode. The last argument could
    # just as well have been zero for blocking mode. Then we could have
    # left out the sleep call in the bottom of the loop
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
        # Read data from device
        l, data = inp.read()
        if l:
            # Return the maximum of the absolute value of all samples in a fragment.
            mx = audioop.rms(data, 2)
            levels.append(mx)

        if len(levels) > 100:
            levels = []


class FloatInput(TextInput):

    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


class MicrophonePanel(Screen):
    """
    Microphone Panel
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=2)

    def start(self):
        self.ids.graph.add_plot(self.plot)
        Clock.schedule_interval(self.get_value, 1/24)
    def stop(self):
        Clock.unschedule(self.get_value)

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
        self.__even = range(2, self.N, 2)
        self.__odd = range(3, self.N, 2)
        self.__all = range(2, self.N)

        _ = Clock.schedule_once(self.start)

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
        Clock.schedule_interval(self.get_value, 1/10)

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

    def switch_presets(self):
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


class OlaPanel(Screen):
    """
    Ola Panel
    """

    c = 340.
    frequency = 340
    A = NumericProperty(0)
    B = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=20)
        self.__time = 0
        self.dt = 2*np.pi/350000
        self.space = np.linspace(0, 1, 1000)

        _ = Clock.schedule_once(self.start)

    @property
    def time(self):
        self.__time += self.dt
        return self.__time

    def start(self, *args):
        self.ids.graph.add_plot(self.plot)
        Clock.schedule_interval(self.get_value, 1/100)

    def get_value(self, *args):
        k = 2*np.pi*self.frequency/self.c
        omega = 2*np.pi*self.frequency
        s = (self.A*np.exp(1j*k*self.space)
                + self.B*np.exp(-1j*k*self.space))*np.exp(1j*omega*self.time)
        self.plot.points = [(self.space[i], j) for i, j in enumerate(s.real)]

    @staticmethod
    def Ola(Nsupporters, d, T, tau):
        """
            Return
                x : Les bonshommes
                y : Leur déplacement
                v : Leur vitesse
        """
        Nt = 1000
        t = np.linspace(0, 10, Nt)
        x = np.arange(0, d*Nsupporters, d) + 1

        y = np.zeros((Nsupporters, Nt))
        v = np.empty_like(y)
        for ii in range(Nsupporters):
            y[ii, :] = np.sin(2*np.pi*(t-ii*tau)/T)
            v[ii, :] = 2*np.pi*np.cos(2*np.pi*(t-ii*tau)/T)/T
        return t, x, y, v


class SinePanel(Screen):
    """
    Sine Panel
    """

    f1 = NumericProperty(10)
    f2 = NumericProperty(10)
    A1 = NumericProperty(0.5)
    A2 = NumericProperty(0.5)
    t1 = NumericProperty(0)
    t2 = NumericProperty(0)
    presets = ["Operations with sine functions", 'Battement', 'Porteuse']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot1 = LinePlot(color=[1., 0.65, 0., 1], line_width=1)
        self.plot2 = LinePlot(color=[1., 1., 0., 1], line_width=1)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=3)

        _ = Clock.schedule_once(self.start)

    def start(self, *args):
        self.ids.graph.add_plot(self.plot1)
        self.ids.graph.add_plot(self.plot2)
        self.ids.graph.add_plot(self.plot)
        Clock.schedule_interval(self.get_value, 1/10)

    def get_value(self, *args):
        t = np.linspace(0, 1, 1000)
        s1 = self.A1*np.sin(2*np.pi*self.f1*t + self.t1)
        s2 = self.A2*np.sin(2*np.pi*self.f2*t + self.t2)
        stot = eval('s1 {} s2'.format(self.ids.operator.text))
        self.plot.points = [(i, j) for i, j in enumerate(stot)]
        if self.ids.disp1.active:
            self.plot1.points = [(i, j) for i, j in enumerate(s1)]
        else:
            self.plot1.points = []
        if self.ids.disp2.active:
            self.plot2.points = [(i, j) for i, j in enumerate(s2)]
        else:
            self.plot2.points = []

    def switch_preset(self):
        pass

class InterferencePanel(Screen):
    """
    InterferencePanel Panel
    """
    c = 340.
    frequency = 340
    A = NumericProperty(0)
    B = NumericProperty(0)
    dispB = BooleanProperty(False)
    presets = ListProperty(['Interferences',
        'Progressive wave (+)', 'Progressive Wave (-)', 'Stationnary Wave'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plot1 = LinePlot(color=[1., 0.65, 0., 1], line_width=1)
        self.plot2 = LinePlot(color=[1., 1., 0., 1], line_width=1)
        self.plot = LinePlot(color=[0., 0.29, 0.49, 1], line_width=3)
        self.__time = 0
        self.dt = 2*np.pi/350000
        self.space = np.linspace(0, 1, 1000)

        _ = Clock.schedule_once(self.start)

    @property
    def time(self):
        self.__time += self.dt
        return self.__time

    def start(self, *args):
        self.ids.graph.add_plot(self.plot1)
        self.ids.graph.add_plot(self.plot2)
        self.ids.graph.add_plot(self.plot)
        Clock.schedule_interval(self.get_value, 1/50)

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


class MediaPanel(Screen):
    frequency = 340
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
        self.dt = 2*np.pi/350000
        self.omega = 2*np.pi*self.frequency
        self.x1 = np.linspace(-2, 0, 1000)
        self.x2 = np.linspace(0, 2, 1000)
        self.xtot = np.concatenate([self.x1, self.x2])

        _ = Clock.schedule_once(self.start)

    @property
    def time(self):
        self.__time += self.dt
        return self.__time

    def start(self, *args):
        self.ids.graph.add_plot(self.plot)
        self.ids.graph.add_plot(self.sep)
        self.sep.points = [(0, j) for j in self.xtot]

        Clock.schedule_interval(self.get_value, 1/100)

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
    get_level_thread = Thread(target = get_microphone_level_alsa)
    get_level_thread.daemon = True
    get_level_thread.start()

    # Run App
    AcousticBasicIllustration().run()
