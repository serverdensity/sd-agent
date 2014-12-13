"""
    Server Density
    www.serverdensity.com
    ----
    Server monitoring agent for Linux, FreeBSD and Mac OS X

    Licensed under Simplified BSD License (see LICENSE)
"""

import httplib  # Used only for handling httplib.HTTPException
import datetime
import os
import platform
import socket
import string
import threading
import time
import urllib
import urllib2

pythonVersion = platform.python_version_tuple()
python24 = platform.python_version().startswith('2.4')

# Build the request headers
headers = {
    'User-Agent': 'Server Density Agent',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/html, */*',
}

if int(pythonVersion[1]) >= 6:  # Don't bother checking major version since we only support v2 anyway
    import json
else:
    import minjson


class LogTailer(threading.Thread):

    def __init__(self, agentConfig, mainLogger, filename):
        self.agentConfig = agentConfig
        self.mainLogger = mainLogger
        self.filename = filename

        threading.Thread.__init__(self)

    # http://www.dabeaz.com/generators/follow.py
    def follow(self, thefile):
        try:
            thefile.seek(0, 2)

            while True:

                line = thefile.readline()
                if not line:
                    time.sleep(0.1)

                    # Check to see if the file is still the one we opened
                    # This can change if the log gets rotated, for example
                    fstat = os.fstat(thefile.fileno())
                    stat = os.stat(self.filename)

                    if fstat.st_ino != stat.st_ino:
                        self.mainLogger.warn('LogTailer (%s) - log file changed, reopening', self.filename)

                        thefile.close()

                        thefile = open(self.filename, "r")

                    continue

                yield line

        except Exception:
            import traceback
            self.mainLogger.error(
                'LogTailer (%s) - follow() failed = %s',
                self.filename,
                traceback.format_exc()
            )
            return

    def run(self):

        try:
            filename = open(self.filename, "r")
            loglines = self.follow(filename)

        except Exception:
            import traceback
            self.mainLogger.error(
                'LogTailer (%s) - Unable to open log file = %s',
                self.filename,
                traceback.format_exc()
            )
            return

        for line in loglines:
            payload = {
                "itemId": self.agentConfig['agentKey'],
                "logs":
                [{
                    "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                    "message": line,
                    "filename": self.filename
                }]
            }

            try:
                if int(pythonVersion[1]) >= 6:
                    payloadJSON = json.dumps(payload)
                else:
                    payloadJSON = minjson.write(payload)

            except Exception:
                import traceback
                self.mainLogger.error(
                    'LogTailer (%s) - Failed encoding payload to json. Exception = %s',
                    self.filename,
                    traceback.format_exc()
                )
                return

            sdUrl = string.replace(self.agentConfig['sdUrl'], 'https://', '')
            sdUrl = string.replace(sdUrl, '.serverdensity.io', '')

            payload = {'payload': payloadJSON, 'sdUrl': sdUrl}
            self.doPostBack(payload)

    def doPostBack(self, postBackData, retry=False):

        self.mainLogger.debug('LogTailer (%s) - doPostBack: start', self.filename)

        try:

            try:
                self.mainLogger.debug(
                    'LogTailer (%s) - doPostBack: attempting postback for %s',
                    self.filename,
                    postBackData['sdUrl']
                )

                # Build the request handler
                request = urllib2.Request(
                    'https://logs.serverdensity.io/collector',
                    urllib.urlencode(postBackData),
                    headers
                )

                # Do the request, log any errors
                response = urllib2.urlopen(request)

                self.mainLogger.info(
                    'LogTailer (%s) - Postback response: %s',
                    self.filename,
                    response.read()
                )

            except urllib2.HTTPError, e:
                self.mainLogger.error('LogTailer (%s) - doPostBack: HTTPError = %s', self.filename, e)

                return

            except urllib2.URLError, e:
                self.mainLogger.error('LogTailer (%s) - doPostBack: URLError = %s', self.filename, e)

                # attempt a lookup, in case of DNS fail
                # https://github.com/serverdensity/sd-agent/issues/47
                if not retry:

                    timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(5)

                    self.mainLogger.info(
                        'LogTailer (%s) - doPostBack: Retrying postback with DNS lookup iteration',
                        self.filename
                    )
                    try:
                        [socket.gethostbyname(self.agentConfig['sdUrl']) for x in xrange(0, 2)]
                    except Exception:
                        # this can raise, if the dns lookup doesn't work
                        pass
                    socket.setdefaulttimeout(timeout)

                    self.mainLogger.info(
                        "LogTailer (%s) - doPostBack: Executing retry",
                        self.filename
                    )
                    return self.doPostBack(postBackData, retry=True)
                else:
                    # if we get here, the retry has failed, so we need to reschedule
                    self.mainLogger.info(
                        "LogTailer (%s) - doPostBack: Retry failed, rescheduling",
                        self.filename
                    )

                    return

            except httplib.HTTPException, e:  # Added for case #26701
                self.mainLogger.error(
                    'LogTailer (%s) - doPostBack: HTTPException = %s',
                    self.filename,
                    e
                )
                return

            except Exception:
                import traceback
                self.mainLogger.error(
                    'LogTailer (%s) - doPostBack: Exception = %s',
                    self.filename,
                    traceback.format_exc()
                )
                return

        finally:
            if int(pythonVersion[1]) >= 6:
                try:
                    if 'response' in locals():
                        response.close()
                except Exception:
                    import traceback
                    self.mainLogger.error(
                        'LogTailer (%s) - doPostBack: Exception = %s',
                        self.filename,
                        traceback.format_exc()
                    )
                    return

            self.mainLogger.debug('LogTailer (%s) - doPostBack: completed', self.filename)
