# Server Density
# www.serverdensity.com
#
# Server monitoring agent for Linux, FreeBSD and Mac OS X
#
# Licensed under Simplified BSD License (see LICENSE)

import glob
import platform
import sched
import sys
import time

# Check we're not using an old version of Python. Do this before anything else
# We need 2.4 above because some modules (like subprocess) were only introduced
# in 2.4.
if int(sys.version_info[1]) <= 3:
    print ('You are using an outdated version of Python. Please update to '
           'v2.4 or above (v3 is not supported). For newer OSs, you can '
           'update Python without affecting your system install. See '
           'https://blog.serverdensity.com/updating-python-on-rhelcentos/ If '
           'you are running RHEl 4 / CentOS 4 then you will need to compile '
           'Python manually.')
    sys.exit(1)

# After the version check as this isn't available on older Python versions
# and will error before the message is shown
import subprocess

# Custom modules
from checks import checks
from daemon import Daemon


def cpu_cores():
    if sys.platform == 'linux2':
        grep = subprocess.Popen(['grep', 'model name', '/proc/cpuinfo'], stdout=subprocess.PIPE, close_fds=True)
        wc = subprocess.Popen(['wc', '-l'], stdin=grep.stdout, stdout=subprocess.PIPE, close_fds=True)
        output = wc.communicate()[0]
        return int(output)

    if sys.platform == 'darwin':
        output = subprocess.Popen(
            ['sysctl', 'hw.ncpu'],
            stdout=subprocess.PIPE,
            close_fds=True
        ).communicate()[0].split(': ')[1]
        return int(output)


# Override the generic daemon class to run our checks
class Agent(Daemon):

    def __init__(self, logger, agentConfig, rawConfig, pidFile):
        self.mainLogger = logger
        self.agentConfig = agentConfig
        self.rawConfig = rawConfig
        self.pidfile = pidFile

    def run(self):
        self.mainLogger.debug('Collecting basic system stats')

        # Get some basic system stats to post back for development/testing
        systemStats = {
            'machine': platform.machine(),
            'platform': sys.platform,
            'processor': platform.processor(),
            'pythonV': platform.python_version(),
            'cpuCores': cpu_cores()
        }

        if sys.platform == 'linux2':
            systemStats['nixV'] = platform.dist()

        elif sys.platform == 'darwin':
            systemStats['macV'] = platform.mac_ver()

        elif sys.platform.find('freebsd') != -1:
            version = platform.uname()[2]
            systemStats['fbsdV'] = ('freebsd', version, '')  # no codename for FreeBSD

        self.mainLogger.info('System: ' + str(systemStats))

        # Log tailer
        if self.agentConfig.get('logTailPaths', '') != '':

            from logtail import LogTailer

            logFiles = []

            for path in self.agentConfig['logTailPaths'].split(','):
                files = glob.glob(path)

                for file in files:
                    logFiles.append(file)

            for file in logFiles:
                self.mainLogger.info('Starting log tailer: %s', file)

                logThread = LogTailer(self.agentConfig, self.mainLogger, file)
                logThread.setName(file)
                logThread.start()

        # Checks instance
        self.mainLogger.debug('Creating checks instance')
        c = checks(self.agentConfig, self.rawConfig, self.mainLogger)

        # Schedule the checks
        self.mainLogger.info('checkFreq: %s', self.agentConfig['checkFreq'])
        s = sched.scheduler(time.time, time.sleep)
        c.doChecks(s, True, systemStats)  # start immediately (case 28315)
        s.run()
