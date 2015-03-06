# Server Density
# www.serverdensity.com
#
# Server monitoring agent for Linux, FreeBSD and Mac OS X
#
# Licensed under Simplified BSD License (see LICENSE)

import ConfigParser
import locale
import logging
import os
import re
import sys
from glob import glob

# Custom modules
import serverdensity
from agent import Agent
from updater import Updater


class Command(object):

    agentConfig = {
        'logging': logging.INFO,
        'checkFreq': 60,
        'version': '1.13.4'
    }

    def __init__(self):

        self.configPath = None
        self._logger = None

    def parse_config(self):
        """Parse sd-agent configuration file."""

        # General config

        self.rawConfig = {}
        config = None
        # Config handling
        try:
            path = os.path.realpath(serverdensity.__file__)
            path = os.path.dirname(path)
            path = os.path.join(path, '..')
            path = os.path.abspath(path)

            config = ConfigParser.ConfigParser()

            if os.path.exists('/etc/sd-agent/conf.d/'):
                self.configPath = '/etc/sd-agent/conf.d/'
            elif os.path.exists('/etc/sd-agent/config.cfg'):
                self.configPath = '/etc/sd-agent/config.cfg'
            else:
                self.configPath = path + '/config.cfg'

            if not os.access(self.configPath, os.R_OK):
                print 'Unable to read the config file at ' + self.configPath
                print 'Agent will now quit'
                sys.exit(1)

            if os.path.isdir(self.configPath):
                for configFile in glob(os.path.join(self.configPath, "*.cfg")):
                    config.read(configFile)
            else:
                config.read(self.configPath)

            # Core config
            self.agentConfig['sdUrl'] = config.get('Main', 'sd_url')

            if self.agentConfig['sdUrl'].endswith('/'):
                self.agentConfig['sdUrl'] = self.agentConfig['sdUrl'][:-1]

            self.agentConfig['agentKey'] = config.get('Main', 'agent_key')

            # Tmp path
            if os.path.exists('/var/log/sd-agent/'):
                self.agentConfig['tmpDirectory'] = '/var/log/sd-agent/'
            else:
                # default which may be overriden in the config later
                self.agentConfig['tmpDirectory'] = '/tmp/'

            self.agentConfig['pidfileDirectory'] = self.agentConfig['tmpDirectory']

            # Plugin config
            if config.has_option('Main', 'plugin_directory'):
                self.agentConfig['pluginDirectory'] = config.get(
                    'Main', 'plugin_directory')

            # Optional config
            # Also do not need to be present in the config file (case 28326).
            if config.has_option('Main', 'apache_status_url'):
                self.agentConfig['apacheStatusUrl'] = config.get(
                    'Main', 'apache_status_url')

            if config.has_option('Main', 'apache_status_user'):
                self.agentConfig['apacheStatusUser'] = config.get(
                    'Main', 'apache_status_user')

            if config.has_option('Main', 'apache_status_pass'):
                self.agentConfig['apacheStatusPass'] = config.get(
                    'Main', 'apache_status_pass')

            if config.has_option('Main', 'logging_level'):
                # Maps log levels from the configuration file to Python log levels
                loggingLevelMapping = {
                    'debug': logging.DEBUG,
                    'info': logging.INFO,
                    'error': logging.ERROR,
                    'warn': logging.WARN,
                    'warning': logging.WARNING,
                    'critical': logging.CRITICAL,
                    'fatal': logging.FATAL,
                }

                customLogging = config.get('Main', 'logging_level')

                try:
                    self.agentConfig['logging'] = loggingLevelMapping[customLogging.lower()]

                except KeyError, ex:
                    self.agentConfig['logging'] = logging.INFO

            if config.has_option('Main', 'mongodb_server'):
                self.agentConfig['MongoDBServer'] = config.get('Main', 'mongodb_server')

            if config.has_option('Main', 'mongodb_keyfile'):
                self.agentConfig['MongoDBKeyfile'] = config.get('Main', 'mongodb_keyfile')

            if config.has_option('Main', 'mongodb_certfile'):
                self.agentConfig['MongoDBCertfile'] = config.get('Main', 'mongodb_certfile')

            if config.has_option('Main', 'mongodb_dbstats'):
                self.agentConfig['MongoDBDBStats'] = config.get('Main', 'mongodb_dbstats')

            if config.has_option('Main', 'mongodb_replset'):
                self.agentConfig['MongoDBReplSet'] = config.get('Main', 'mongodb_replset')

            if config.has_option('Main', 'mysql_server'):
                self.agentConfig['MySQLServer'] = config.get('Main', 'mysql_server')

            if config.has_option('Main', 'mysql_user'):
                self.agentConfig['MySQLUser'] = config.get('Main', 'mysql_user')

            if config.has_option('Main', 'mysql_pass'):
                self.agentConfig['MySQLPass'] = config.get('Main', 'mysql_pass')

            if config.has_option('Main', 'mysql_port'):
                self.agentConfig['MySQLPort'] = config.get('Main', 'mysql_port')

            if config.has_option('Main', 'mysql_socket'):
                self.agentConfig['MySQLSocket'] = config.get('Main', 'mysql_socket')

            if config.has_option('Main', 'mysql_norepl'):
                self.agentConfig['MySQLNoRepl'] = config.get('Main', 'mysql_norepl')

            if config.has_option('Main', 'nginx_status_url'):
                self.agentConfig['nginxStatusUrl'] = config.get('Main', 'nginx_status_url')

            if config.has_option('Main', 'tmp_directory'):
                self.agentConfig['tmpDirectory'] = config.get('Main', 'tmp_directory')

            if config.has_option('Main', 'pidfile_directory'):
                self.agentConfig['pidfileDirectory'] = config.get('Main', 'pidfile_directory')

            if config.has_option('Main', 'rabbitmq_status_url'):
                self.agentConfig['rabbitMQStatusUrl'] = config.get('Main', 'rabbitmq_status_url')

            if config.has_option('Main', 'rabbitmq_user'):
                self.agentConfig['rabbitMQUser'] = config.get('Main', 'rabbitmq_user')

            if config.has_option('Main', 'rabbitmq_pass'):
                self.agentConfig['rabbitMQPass'] = config.get('Main', 'rabbitmq_pass')

            if config.has_option('Main', 'logtail_paths'):
                self.agentConfig['logTailPaths'] = config.get('Main', 'logtail_paths')

            if config.has_option('Main', 'proxy_url'):
                self.agentConfig['proxyUrl'] = config.get('Main', 'proxy_url')

        except ConfigParser.NoSectionError, e:
            print 'Config file not found or incorrectly formatted'
            print 'Agent will now quit'
            sys.exit(1)

        except ConfigParser.ParsingError, e:
            print 'Config file not found or incorrectly formatted'
            print 'Agent will now quit'
            sys.exit(1)

        except ConfigParser.NoOptionError, e:
            print 'There are some items missing from your config file, but nothing fatal'

        # Check to make sure the default config values have been changed (only core config values)
        if (re.match('http(s)?(\:\/\/)example\.serverdensity\.(com|io)',
                     self.agentConfig['sdUrl']) is not None
                or self.agentConfig['agentKey'] == 'keyHere'):
            print 'You have not modified config.cfg for your server'
            print 'Agent will now quit'
            sys.exit(1)

        # Check to make sure sd_url is in correct
        if (re.match('http(s)?(\:\/\/)[a-zA-Z0-9_\-]+\.serverdensity\.(com|io)',
                     self.agentConfig['sdUrl']) is None):
            print 'Your sd_url is incorrect. It needs to be in the form https://example.serverdensity.com or https://example.serverdensity.io'
            print 'Agent will now quit'
            sys.exit(1)

        # Check apache_status_url is not empty (case 27073)
        if 'apacheStatusUrl' in self.agentConfig and self.agentConfig['apacheStatusUrl'] is None:
            print ('You must provide a config value for apache_status_url. If you do not wish to use Apache monitoring, '
                   'leave it as its default value - http://www.example.com/server-status/?auto')
            print 'Agent will now quit'
            sys.exit(1)

        if 'nginxStatusUrl' in self.agentConfig and self.agentConfig['nginxStatusUrl'] is None:
            print 'You must provide a config value for nginx_status_url. If you do not wish to use Nginx monitoring, leave it as its default value - http://www.example.com/nginx_status'
            print 'Agent will now quit'
            sys.exit(1)

        if (
                'MySQLServer' in self.agentConfig and
                self.agentConfig['MySQLServer'] != '' and
                'MySQLUser' in self.agentConfig and
                self.agentConfig['MySQLUser'] != '' and
                'MySQLPass' in self.agentConfig
        ):
            try:
                import MySQLdb
            except ImportError:
                print (
                    'You have configured MySQL for monitoring, but the MySQLdb module is not installed. For more info, see: '
                    'http://www.serverdensity.com/docs/agent/mysqlstatus/\nAgent will now quit'
                )
                sys.exit(1)

        if 'MongoDBServer' in self.agentConfig and self.agentConfig['MongoDBServer'] != '':
            try:
                import pymongo
            except ImportError:
                print (
                    'You have configured MongoDB for monitoring, but the pymongo module is not installed. For more info, see: '
                    'http://www.serverdensity.com/docs/agent/mongodbstatus/\nAgent will now quit'
                )
                sys.exit(1)

        for section in config.sections():
            self.rawConfig[section] = {}

            for option in config.options(section):
                self.rawConfig[section][option] = config.get(section, option)

    def get_logger(self):
        """Return logger object for the agent."""

        if self._logger is None:
            logFile = os.path.join(
                self.agentConfig['tmpDirectory'], 'sd-agent.log')

            if not os.access(self.agentConfig['tmpDirectory'], os.W_OK):
                print 'Unable to write the log file at ' + logFile
                print 'Agent will now quit'
                sys.exit(1)

            handler = logging.handlers.RotatingFileHandler(
                logFile, maxBytes=10485760, backupCount=5)  # 10MB files
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            handler.setFormatter(formatter)

            self._logger = logging.getLogger('main')
            self._logger.setLevel(self.agentConfig['logging'])
            self._logger.addHandler(handler)

        return self._logger

    def run(self):

        # Setup locale to use always 'C' locale. This would prevent that the
        # commands executed by the agent produce localized output and thus,
        # break the parsers.
        locale.setlocale(locale.LC_ALL, 'C')
        os.putenv('LC_ALL', 'C')

        self.parse_config()

        mainLogger = self.get_logger()

        mainLogger.info('--')
        mainLogger.info('sd-agent %s started', self.agentConfig['version'])
        mainLogger.info('--')

        mainLogger.info('Reading config from: %s', self.configPath)
        mainLogger.info('sd_url: %s', self.agentConfig['sdUrl'])
        mainLogger.info('agent_key: %s', self.agentConfig['agentKey'])

        argLen = len(sys.argv)

        pidFile = None
        if argLen == 3 or argLen == 4:  # needs to accept case when --clean is passed
            if sys.argv[2] == 'init':
                # This path added for newer Linux packages which run under
                # a separate sd-agent user account.
                if os.path.exists('/var/run/sd-agent/'):
                    pidFile = '/var/run/sd-agent/sd-agent.pid'
                else:
                    pidFile = '/var/run/sd-agent.pid'

        else:
            pidFile = os.path.join(
                self.agentConfig['pidfileDirectory'], 'sd-agent.pid')

        if not os.access(self.agentConfig['pidfileDirectory'], os.W_OK):
            print 'Unable to write the PID file at ' + pidFile
            print 'Agent will now quit'
            sys.exit(1)

        mainLogger.info('PID: %s', pidFile)

        if argLen == 4 and sys.argv[3] == '--clean':
            mainLogger.info('--clean')
            try:
                os.remove(pidFile)
            except OSError:
                # Did not find pid file
                pass

        # Daemon instance from agent class
        daemon = Agent(mainLogger, self.agentConfig, self.rawConfig, pidFile)

        # Control options
        if argLen == 2 or argLen == 3 or argLen == 4:
            if 'start' == sys.argv[1]:
                mainLogger.info('Action: start')
                daemon.start()

            elif 'stop' == sys.argv[1]:
                mainLogger.info('Action: stop')
                daemon.stop()

            elif 'restart' == sys.argv[1]:
                mainLogger.info('Action: restart')
                daemon.restart()

            elif 'foreground' == sys.argv[1]:
                mainLogger.info('Action: foreground')
                daemon.run()

            elif 'status' == sys.argv[1]:
                mainLogger.info('Action: status')

                try:
                    pf = open(pidFile, 'r')
                    pid = int(pf.read().strip())
                    pf.close()
                except IOError:
                    pid = None
                except SystemExit:
                    pid = None

                if pid:
                    print 'sd-agent is running as pid %s.' % pid
                else:
                    print 'sd-agent is not running.'

            elif 'update' == sys.argv[1]:
                mainLogger.info('Action: update')

                updater = Updater(mainLogger, self.agentConfig)
                updater.update()

            else:
                print 'Unknown command'
                sys.exit(1)

            sys.exit(0)

        else:
            print 'usage: %s start|stop|restart|status|update' % sys.argv[0]
            sys.exit(1)
