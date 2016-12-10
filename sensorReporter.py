#!/usr/bin/python

"""
   Copyright 2016 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script:  sensorReporter.py
 Author:  Rich Koshak
 Date:    February 10, 2016
 Purpose: Uses the REST API or MQTT to report updates to the configured sensors, activates actuators based on MQTT messages
"""

import logging
import logging.handlers
import ConfigParser
import signal
import sys
import time
import traceback
from threading import *
from signalProc import *
import importlib
import RPi.GPIO as GPIO

# Globals
GPIO.setwarnings(False)
logger = logging.getLogger('sensorReporter')

config = ConfigParser.ConfigParser(allow_no_value=True)
sensors = []
actuators = []
connections = {}

#------------------------------------------------------------------------------
# Main event loops
def on_message(client, userdata, msg):
    """Called when a message is received from a connection, send the current sensor state.
       We don't care what the message is."""
    
    try:
        logger.info("Received a request for current state, publishing")
        if msg is not None:
            print(msg.topic)
            logger.info("Topic: " + msg.topic + " Message: " + str(msg.payload))
        logger.info("getting states")
        for s in sensors:
            if s.poll > 0:
                s.checkState()
                s.publishState()
    except:
        logger.info("Unexpected error:", sys.exec_info()[0])

def main():
    """Polls the sensor pins and publishes any changes"""

    if len(sys.argv) < 2:
        print "No config file specified on the command line!"
        sys.exit(1)

    loadConfig(sys.argv[1])
    for s in sensors:
        s.lastPoll = time.time()

    logger.info("Kicking off polling threads...")
    while True:

        # Kick off a poll of the sensor in a separate process
        for s in sensors:
            if s.poll > 0 and (time.time() - s.lastPoll) > s.poll:
                s.lastPoll = time.time()
                Thread(target=check, args=(s,)).start()
        
        time.sleep(0.5) # give the processor a chance if REST is being slow

#------------------------------------------------------------------------------
# Signal Processing

# The decorators below causes the creation of a SignalHandler attached to this function for each of the
# signals we care about using the handles function above. The resultant SignalHandler is registered with
# the signal.signal so cleanup_and_exit is called when they are received.
@handles(signal.SIGTERM)
@handles(signal.SIGHUP)
@handles(signal.SIGINT)
def cleanup_and_exit():
    """ Signal handler to ensure we disconnect cleanly in the event of a SIGTERM or SIGINT. """

    logger.warn("Terminating the program")
    try:
        for key in connections:
            try:
                connections[key].disconnect()
            except AttributeError:
                pass
	for s in sensors:
            try:
                s.quit = true
            except AttributeError:
                pass
    except:
        pass
    sys.exit(0)

# This decorator registers the function with the SignalHandler blocks_on so the SignalHandler knows
# when the function is running
@cleanup_and_exit.blocks_on
def check(s):
    """Gets the current state of the passed in sensor and publishes it"""
    s.checkState()

#------------------------------------------------------------------------------
# Initialization
def configLogger(file, size, num, syslog):
    """Configure a rotating log"""
    logger.setLevel(logging.DEBUG)
    if syslog != "YES":
      print "Configuring logger: file = " + file + " size = " + str(size) + " num = " + str(num)
      fh = logging.handlers.RotatingFileHandler(file, mode='a', maxBytes=size, backupCount=num)
      fh.setLevel(logging.INFO)
      formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
      fh.setFormatter(formatter)
      logger.addHandler(fh)
    elif syslog == "YES":
      print "Configuring syslogging"
      sh = logging.handlers.SysLogHandler('/dev/log', facility=logging.handlers.SysLogHandler.LOG_SYSLOG)
      sh.encodePriority(sh.LOG_SYSLOG, sh.LOG_INFO)
      slFormatter = logging.Formatter('[sensorReporter] %(levelname)s - %(message)s')
      sh.setFormatter(slFormatter)
      logger.addHandler(sh)
    logger.info("---------------Started")

def createDevice(config, section):
    """Configure a sensor or actuator"""

    try:
      module_name, class_name = config.get(section, "Class").rsplit(".", 1)
      MyDevice = getattr(importlib.import_module(module_name), class_name)

      params = lambda key: config.get(section, key)
      connName = params("Connection")
      d = MyDevice(connections[connName], logger, params)
      if config.getfloat(section, "Poll") == -1:
        Thread(target=d.checkState).start() # don't need to use cleanup-on-exit for non-polling sensors

      return d
    except ImportError:
      logger.err("%s.%s is not supported on this platform" % module_name, class_name)

def createConnection(config, section):

    try:
      name = config.get(section, "Name")
      logger.info("Creating connection %s" % (name))
      module_name, class_name = config.get(section, "Class").rsplit(".", 1)
      MyConn = getattr(importlib.import_module(module_name), class_name)
      params = lambda key: config.get(section, key)
      connections[name] = MyConn(on_message, logger, params)
    except ImportError:
      logger.err("%s.%s is not supported on this platform" % module_name, class_name)


def loadConfig(configFile):
    """Read in the config file, set up the logger, and populate the sensors"""
    print "Loading " + configFile
    config.read(configFile)

    configLogger(config.get("Logging", "File"), 
                 config.getint("Logging", "MaxSize"), 
                 config.getint("Logging", "NumFiles"),
                 config.get("Logging", "Syslog"))

    # create connections first
    logger.info("Creating connetions...")
    for section in config.sections():
        if section.startswith("Connection"):
            createConnection(config, section)

    logger.info("Populating the sensor/actuator list...")
    for section in config.sections():
        if section.startswith("Sensor"):
            sensors.append(createDevice(config, section))
        elif section.startswith("Actuator"):
            actuators.append(createDevice(config, section))

    return sensors

if __name__ == "__main__":
    main()
