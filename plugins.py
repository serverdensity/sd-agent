#!/usr/bin/env python

"""
Classes for plugin download, installation, and registration.

"""


import ConfigParser
import os
import platform
import urllib, urllib2
from optparse import OptionParser
from zipfile import ZipFile


python_version = platform.python_version_tuple()

if int(python_version[1]) >= 6:
    import json
else:
    import minjson


class App(object):
    """
    Class for collecting arguments and options for the plugin
    download and installation process.

    """
    def __init__(self):
        usage = 'usage: %prog [options] key'
        self.parser = OptionParser(usage=usage)
        self.parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                               default=False, help='run in verbose mode')
        self.parser.add_option('-r', '--remove', action='store_true', dest='remove',
                               default=False, help='remove plugin')

    def run(self):
        """
        Entry point to the plugin helper application.

        """
        (options, args) = self.parser.parse_args()
        if len(args) != 1:
            self.parser.error('incorrect number of arguments')
        downloader = PluginDownloader(key=args[0], verbose=options.verbose)
        downloader.start()

class PluginMetadata(object):
    def __init__(self, downloader=None):
        self.downloader = downloader

    def get(self):
        raise Exception, 'sub-classes to provide implementation.'

    def json(self):
        metadata = self.get()
        if self.downloader.verbose:
            print metadata
        if json:
            return json.loads(metadata)
        else:
            return minjson.safeRead(metadata)

class FilePluginMetadata(PluginMetadata):
    """
    File-based metadata provider, for testing purposes.

    """
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'tests/plugin.json')
        if self.downloader.verbose:
            print 'reading plugin data from %s' % path
        f = open(path, 'r')
        data = f.read()
        f.close()
        return data

class WebPluginMetadata(PluginMetadata):
    """
    Web-based metadata provider.

    """
    def __init__(self, downloader=None, agent_key=None):
        super(WebPluginMetadata, self).__init__(downloader=downloader)
        self.agent_key = agent_key

    def get(self):
        url = 'http://plugins.serverdensity.com/install/'
        data = {
            'installId': self.downloader.key,
            'agentKey': self.agent_key
        }
        if self.downloader.verbose:
            print 'sending %s to %s' % (data, url)
        request = urllib2.urlopen(url, urllib.urlencode(data))
        response = request.read()
        return response

class PluginDownloader(object):
    """
    Class for downloading a plugin.

    """
    def __init__(self, key=None, verbose=True):
        self.key = key
        self.verbose = verbose

    def __prepare_plugin_directory(self):
        if not os.path.exists(self.config.plugin_path):
            if self.verbose:
                print '%s does not exist, creating' % self.config.plugin_path
            os.mkdir(self.config.plugin_path)
            if self.verbose:
                print '%s created' % self.config.plugin_path
        elif self.verbose:
            print '%s exists' % self.config.plugin_path

    def __download(self):
        self.url = 'http://plugins.serverdensity.com/download/%s/%s/' % (self.key, self.config.agent_key)
        if self.verbose:
            print 'downloading for agent %s: %s' % (self.config.agent_key, self.url)
        request = urllib2.urlopen(self.url)
        data = request.read()
        path = os.path.join(self.config.plugin_path, '%s.zip' % self.key)
        f = open(path, 'w')
        f.write(data)
        f.close()
        z = ZipFile(path, 'r')
        z.extractall(os.path.dirname(path))
        z.close()
        os.remove(path)

    def start(self):
        self.config = AgentConfig(downloader=self)
        metadata = WebPluginMetadata(self, agent_key=self.config.agent_key).json()
        if self.verbose:
            print 'retrieved metadata.'
        assert 'configKeys' in metadata or 'status' in metadata, 'metadata is not valid.'
        if 'status' in metadata and metadata['status'] == 'error':
            raise Exception, metadata['msg']
        self.__prepare_plugin_directory()
        self.__download()
        self.config.prompt(metadata['configKeys'])
        print 'plugin installed; please restart your agent'

class AgentConfig(object):
    """
    Class for writing new config options to sd-agent config.

    """
    def __init__(self, downloader=None):
        self.downloader = downloader
        self.path = self.__get_config_path()
        assert self.path, 'no config path found.'
        self.config = self.__parse()
        if self.config.get('Main', 'plugin_directory'):
            self.plugin_path = self.config.get('Main', 'plugin_directory')
        self.agent_key = self.config.get('Main', 'agent_key')
        assert self.agent_key, 'no agent key.'

    def __get_config_path(self):
        paths = (
            '/etc/sd-agent/config.cfg',
            os.path.join(os.path.dirname(__file__), 'config.cfg')
        )
        for path in paths:
            if os.path.exists(path):
                if self.downloader.verbose:
                    print 'found config at %s' % path
                return path

    def __parse(self):
        if os.access(self.path, os.R_OK) == False:
            if self.downloader.verbose:
                print 'cannot access config'
            raise Exception, 'cannot access config'
        if self.downloader.verbose:
            print 'found config, parsing'
        config = ConfigParser.ConfigParser()
        config.read(self.path)
        if self.downloader.verbose:
            print 'parsed config'
        return config

    def __write(self, values):
        for key in values.keys():   
            self.config.set('Main', key, values[key])
        try:
            f = open(self.path, 'w')
            self.config.write(f)
            f.close()
        except Exception, ex:
            print ex
            sys.exit(1)

    def prompt(self, options):
        values = {}
        for option in options:
            values[option] = raw_input('value for %s: ' % option)
        self.__write(values)

if __name__ == '__main__':
    try:
        app = App()
        app.run()
    except Exception, ex:
        print 'error: %s' % ex
