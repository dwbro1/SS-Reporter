#!/usr/bin/env python
"""
   Copyright 2016 Dale Brown

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: envirophatSensor.py
 Author: Dale Brown
 Date:   December 9, 2016
 Purpose: Checks envirophat sensors and publishes any changes

 TODO: Take advantage of GPIO.add_event_detect(pin, GPIO.RISING, callback=myFunction)
       to register for events instead of polling. Use Dash sensor as an example.
"""

import sys
import time

from envirophat import weather

class envirophatSensor:

    """Represents a sensors connected"""

    def __init__(self, publisher, params):
        """Gets data from sensor"""

        self.temp = weather.temperature()

    def publishState(self):
        """Publishes the current state"""

        self.publish('weather.temperature()', self.destination)
