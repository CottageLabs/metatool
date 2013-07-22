import imp, os

MODULE_EXTENSIONS = ('.py') # only interested in .py files, not pyc or pyo

class Plugin(object):
    # subclasses should override these methods with their implementations
    def supports(self, datatype, **validation_options):
        return False
        
    def run(self, issn, **validation_options):
        return None
    
class ValidationResponse(object):
    def __init__(self, provenance=None):
        if provenance is not None:
            self.provenance = provenance
        self._info = []
        self._warn = []
        self._error = []
        
    def info(self, info):
        self._info.append(info)
    
    def warn(self, warn):
        self._warn.append(warn)
        
    def error(self, error):
        self._error.append(error)
        
def load():
    plugin_instances = {}
    modules = get_modules("plugins")
    for modname, modpath in modules:
        mod = imp.load_source(modname, os.path.join(modpath, modname + ".py"))
        members = dir(mod)
        for member in members:
            attr = getattr(mod, member)
            if isinstance(attr, type):
                if issubclass(attr, Plugin):
                    plugin_instances[modname + "." + attr.__name__] = attr()
    return plugin_instances

def get_modules(package_name):
    file, pathname, description = imp.find_module(package_name)
    if file:
        raise ImportError('Not a package: %r', package_name)
        
    # Use a set because some may be both source and compiled.
    return [(os.path.splitext(module)[0], pathname)
        for module in os.listdir(pathname)
        if module.endswith(MODULE_EXTENSIONS) and module != "__init__.py"]
