import httplib
import os.path
import platform
import shutil
import sys
import traceback
import urllib
import urllib2

try:
    from hashlib import md5
except ImportError:  # Python < 2.5
    from md5 import new as md5


class Updater(object):

    def __init__(self, logger, agentConfig):
        self.logger = logger
        self.agentConfig = agentConfig

    def get_update_info(self):
        "Return latest update info available"

        # Get the latest version info
        try:
            self.logger.debug('Update: checking for update')

            request = urllib2.urlopen(
                'http://www.serverdensity.com/agentupdate/')
            response = request.read()

        except urllib2.HTTPError, e:
            print 'Unable to get latest version info - HTTPError = ' + str(e)
            sys.exit(1)

        except urllib2.URLError, e:
            print 'Unable to get latest version info - URLError = ' + str(e)
            sys.exit(1)

        except httplib.HTTPException, e:
            print 'Unable to get latest version info - HTTPException'
            sys.exit(1)

        except Exception:
            print 'Unable to get latest version info - Exception = ' + traceback.format_exc()
            sys.exit(1)

        self.logger.debug('Update: importing json/minjson')

        # We need to return the data using JSON. As of Python 2.6+, there is a core JSON
        # module. We have a 2.4/2.5 compatible lib included with the agent but if we're
        # on 2.6 or above, we should use the core module which will be faster
        pythonVersion = platform.python_version_tuple()

        # Decode the JSON
        if int(pythonVersion[1]) >= 6:  # Don't bother checking major version since we only support v2 anyway
            import json

            self.logger.debug('Update: decoding JSON (json)')

            try:
                updateInfo = json.loads(response)
            except Exception, e:
                print 'Unable to get latest version info. Try again later.'
                sys.exit(1)

        else:
            import minjson

            self.logger.debug('Update: decoding JSON (minjson)')

            try:
                updateInfo = minjson.safeRead(response)
            except Exception, e:
                print 'Unable to get latest version info. Try again later.'
                sys.exit(1)

    def _download_file(self, agentFile, recursed=False):
        self.logger.debug('Update: downloading ' + agentFile['name'])
        print 'Downloading ' + agentFile['name']

        downloadedFile = urllib.urlretrieve(
            'http://www.serverdensity.com/downloads/sd-agent/' + agentFile['name']
        )

        # Do md5 check to make sure the file downloaded properly
        checksum = md5()
        f = open(downloadedFile[0], 'rb')

        # Although the files are small, we can't guarantee the available memory nor that there
        # won't be large files in the future, so read the file in small parts (1kb at time)
        while True:
            part = f.read(1024)

            if not part:
                # end of file
                break

            checksum.update(part)

        f.close()

        # Do we have a match?
        if checksum.hexdigest() == agentFile['md5']:
            return downloadedFile[0]

        else:
            # Try once more
            if not recursed:
                self._download_file(agentFile, True)

            else:
                print agentFile['name'] + (
                    ' did not match its checksum - it is corrupted. This may be caused '
                    'by network issues so please try again in a moment.'
                )
                sys.exit(1)

    def update(self):

        if os.path.abspath(__file__) == '/usr/bin/sd-agent/agent.py':
            print 'Please use the Linux package manager that was used to install the agent to update it.'
            print 'e.g. yum install sd-agent or apt-get install sd-agent'
            sys.exit(1)

        print 'Checking if there is a new version'
        update_info = self.get_update_info()

        if update_info['version'] != self.agentConfig['version']:
            print 'A new version is available.'

            # Loop through the new files and call the download function
            for agentFile in update_info['files']:
                agentFile['tempFile'] = self._download_file(agentFile)

            # If we got to here then everything worked out fine. However, all the files are still in temporary
            # locations so we need to move them. This is to stop an update breaking a working agent if the update
            # fails halfway through
            for agentFile in update_info['files']:
                self.logger.debug('Update: updating ' + agentFile['name'])
                print 'Updating ' + agentFile['name']
                installation_path = os.path.dirname(os.path.abspath(__file__))
                self.logger.debug(
                    'Update: installation path: ' + installation_path)

                try:
                    if os.path.exists(agentFile['name']):
                        os.remove(os.path.join(installation_path, agentFile['name']))

                    # Use of shutil prevents [Errno 18] Invalid
                    # cross-device link (case 26878)
                    shutil.move(agentFile['tempFile'], os.path.join(installation_path, agentFile['name']))

                except OSError:
                    print (
                        'An OS level error occurred. You will need to manually re-install the agent by downloading '
                        'the latest version from http://www.serverdensity.com/downloads/sd-agent.tar.gz. You can '
                        'copy your config.cfg to the new install'
                    )
                    sys.exit(1)

            self.logger.debug('Update: done')

            print 'Update completed. Please restart the agent (python agent.py restart).'

        else:
            print 'The agent is already up to date'
