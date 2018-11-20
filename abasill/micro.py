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
# Creation Date : lun. 19 nov. 2018 17:36:41 CET
# Last Modified : mar. 20 nov. 2018 11:40:20 CET
"""
-----------
DOCSTRING

@author: Cyril Desjouy
"""

import alsaaudio
import audioop
import threading


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

