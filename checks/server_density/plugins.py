import configparser
import os
import platform
import sys
import traceback
from glob import glob

# project
from checks import Check
from config import get_config_path

pythonVersion = platform.python_version_tuple()
python24 = platform.python_version().startswith('2.4')


class Plugins(Check):
    """Collects metrics from SDv1 Plugins."""

    def __init__(self, logger):
        Check.__init__(self, logger)

        self.plugins = None
        self.raw_config = self._get_raw_config()

    def _get_raw_config(self):
        raw_config = {}

        try:

            config = configparser.ConfigParser()

            config_path = os.path.dirname(get_config_path())
            if os.path.exists(os.path.join(config_path, 'plugins.d')):
                config_path = os.path.join(config_path, 'plugins.d')
            else:
                config_path = os.path.join(config_path, 'plugins.cfg')

            if not os.access(config_path, os.R_OK):
                self.logger.error(
                    'Unable to read the config file at ' + config_path)
                self.logger.error(
                    'Using no config...')
                return raw_config

            if os.path.isdir(config_path):
                for config_file in glob(os.path.join(config_path, "*.cfg")):
                    config.read(config_file)
            else:
                config.read(config_path)

            for section in config.sections():
                raw_config[section] = {}
                for option in config.options(section):
                    raw_config[section][option] = config.get(section, option)

        except configparser.ParsingError:
            self.logger.error(
                "v1 Plugins config file not found or incorrectly formatted.")

        return raw_config

    def check(self, agentConfig):

        self.logger.debug('getPlugins: start')

        plugin_directory = agentConfig.get('plugin_directory', None)
        if plugin_directory:

            self.logger.info(
                'getPlugins: plugin_directory %s', plugin_directory)

            if not os.access(plugin_directory, os.R_OK):
                self.logger.warning(
                    'getPlugins: Plugin path %s is set but not readable by ' +
                    'agent. Skipping plugins.', plugin_directory)
                return False
        else:
            self.logger.debug('getPlugins: plugin_directory not set')

            return False

        # Have we already imported the plugins?
        # Only load the plugins once
        if self.plugins is None:
            self.logger.debug(
                'getPlugins: initial load from %s', plugin_directory)

            sys.path.append(plugin_directory)

            self.plugins = []
            plugins = []

            # Loop through all the plugin files
            for root, dirs, files in os.walk(plugin_directory):
                for name in files:
                    self.logger.debug('getPlugins: considering: %s', name)

                    name = name.split('.', 1)

                    # Only pull in .py files (ignores others, inc .pyc files)
                    try:
                        if name[1] == 'py':

                            self.logger.debug(
                                'getPlugins: ' + name[0] + '.' + name[1] +
                                ' is a plugin')

                            plugins.append(name[0])
                    except IndexError:
                        continue

            # Loop through all the found plugins, import them then create new
            # objects
            for plugin_name in plugins:
                self.logger.debug('getPlugins: loading %s', plugin_name)

                plugin_path = os.path.join(
                    plugin_directory, '%s.py' % plugin_name)

                if not os.access(plugin_path, os.R_OK):
                    self.logger.error(
                        'getPlugins: Unable to read %s so skipping this '
                        'plugin.', plugin_path)
                    continue

                try:
                    # Import the plugin, but only from the plugin directory
                    # (ensures no conflicts with other module names elsewhere
                    # in the sys.path
                    import imp
                    imported_plugin = imp.load_source(plugin_name, plugin_path)

                    self.logger.debug('getPlugins: imported %s', plugin_name)

                    # Find out the class name and then instantiate it
                    plugin_class = getattr(imported_plugin, plugin_name, None)
                    if plugin_class is None:
                        self.logger.info(
                            'getPlugins: Unable to locate class %s in %s, '
                            'skipping', plugin_name, plugin_path)
                        continue

                    try:
                        plugin_obj = plugin_class(
                            agentConfig, self.logger, self.raw_config)
                    except TypeError:

                        try:
                            plugin_obj = plugin_class(
                                agentConfig, self.logger)
                        except TypeError:
                            # Support older plugins.
                            plugin_obj = plugin_class()

                    self.logger.debug('getPlugins: instantiated %s', plugin_name)

                    # Store in class var so we can execute it again on the
                    # next cycle
                    self.plugins.append(plugin_obj)

                except Exception:
                    self.logger.error(
                        'getPlugins (%s): exception = %s', plugin_name,
                        traceback.format_exc())

        # Now execute the objects previously created
        if self.plugins is not None:
            self.logger.debug('getPlugins: executing plugins')

            # Execute the plugins
            output = {}

            for plugin in self.plugins:
                self.logger.info(
                    'getPlugins: executing  %s', plugin.__class__.__name__)

                try:
                    value = plugin.run()
                    if value:
                        output[plugin.__class__.__name__] = value
                        self.logger.debug(
                            'getPlugins: %s output: %s',
                            plugin.__class__.__name__,
                            output[plugin.__class__.__name__])
                        self.logger.info(
                            'getPlugins: executed %s',
                            plugin.__class__.__name__)
                    else:
                        self.logger.info(
                            'getPlugins: executed %s but returned no data',
                            plugin.__class__.__name__)
                except Exception:
                    self.logger.error(
                        'getPlugins: exception = %s', traceback.format_exc())

            self.logger.debug('getPlugins: returning')
            # Each plugin should output a dictionary so we can convert it to
            # JSON later
            return output

        else:
            self.logger.debug('getPlugins: no plugins, returning false')

            return False
