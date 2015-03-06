import warnings

warnings.filterwarnings('ignore', '.*already imported.*')

try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    # don't prevent use of if pkg_resources isn't installed
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)

try:
    import modulefinder
except ImportError:
    pass
else:
    for p in __path__:
        modulefinder.AddPackagePath(__name__, p)
