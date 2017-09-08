# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016-2017 J0rdyZ65

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import pkgutil

import xbmc


_LOG_DEBUG = False
"""Set to True to enable this module logging"""

_LOG_MODULES = ['script.module.urlresolver', 'plugin.video.streamondemand']
"""List of sandboxed modules (e.g. addons) for which to activate the debug logging.
If [], the debug logging, if enabled, is active for all modules.
"""

_HANDLED_PATHS = {}
_SANDBOX_NAMESPACE_SEP = '@'


def _normalize_sandbox_name(name):
    return name.replace('.', '_')


for i in range(len(_LOG_MODULES)):
    _LOG_MODULES[i] = _normalize_sandbox_name(_LOG_MODULES[i])


def _log(sandbox, msg):
    if _LOG_DEBUG and (not _LOG_MODULES or sandbox in _LOG_MODULES):
        xbmc.log('[%s%s] %s'%(sys.argv[0], '' if len(sys.argv) <= 1 else ':'+sys.argv[1], msg))


def _name_is_sandboxed(fullname):
    return _SANDBOX_NAMESPACE_SEP in fullname


def _name_sandbox(sandbox, fullname):
    if _name_is_sandboxed(fullname) or not sandbox:
        return fullname
    else:
        return sandbox+_SANDBOX_NAMESPACE_SEP+fullname


def _name_get_sandbox(fullname):
    return None if not _name_is_sandboxed(fullname) else fullname.split(_SANDBOX_NAMESPACE_SEP, 1)[0]


def _name_desandbox(fullname):
    return fullname if not _name_is_sandboxed(fullname) else fullname.split(_SANDBOX_NAMESPACE_SEP, 1)[1]


def add_path(path):
    if not os.path.isdir(path):
        return
    sandbox = _normalize_sandbox_name(os.path.basename(path))
    for path in [path, os.path.realpath(path)]:
        if path not in _HANDLED_PATHS:
            _HANDLED_PATHS[path] = sandbox
            _log(sandbox, 'importer: imports under path %s handled as %s'%(path, sandbox))


def walk_packages(path=None, prefix='', onerror=None):
    for package, name, is_pkg in pkgutil.walk_packages(path, prefix, onerror):
        yield package, _name_desandbox(name), is_pkg


class ImpImporterSandbox(pkgutil.ImpImporter):
    """
        The ImpImporterSandbox class enhance the standard import mechanism
        by creating a separate module namespace for each addon.
        This allow the coexistence in the same python thread of different addons
        using the same module namespace regardless of the import model used.

        Usage:
            import sys
            import importer
            importer.add_path(addon_root_directory)
            ...
            sys.path_hooks.append(importer.ImpImporterSandbox)

        NOTE1: specify a path for each addon that requires a separate namespace.
        NOTE2: the ImpImporterSandbox doesn't respect the module reload semantic.
    """
    def __init__(self, path_entry):
        self.sandbox = None
        for hpath, sandbox in _HANDLED_PATHS.iteritems():
            if path_entry.startswith(hpath):
                pkgutil.ImpImporter.__init__(self, path_entry)

                self.sandbox = sandbox
                self._log('ImpImporterSandbox(%s, %s): handled: sandbox=%s'%(self, path_entry, self.sandbox))
                return

        self._log('ImpImporterSandbox(%s, %s): not handled'%(self, path_entry))
        raise ImportError()

    def find_module(self, fullname, path=None):
        self._log('find_module(%s, %s, %s)'%(self, fullname, path))

        if self.sandbox is None:
            self._log('find_module(): sandbox is None')
            return None

        impl = pkgutil.ImpImporter.find_module(self, fullname, path)
        if not impl:
            self._log('find_module(..., %s, ...): module not found'%fullname)
            return None

        self._log('find_module(..., %s, ...): sandbox=%s, impl.fullname=%s, file=%s, filename=%s, etc=%s'%
                  (fullname, self.sandbox, impl.fullname, impl.file, impl.filename, impl.etc))

        return ImpLoaderSandbox(_name_sandbox(self.sandbox, impl.fullname), impl.file, impl.filename, impl.etc)

    def iter_modules(self, prefix=''):
        self._log('iter_modules(%s, %s)'%(self, prefix))

        for name, is_pkg in pkgutil.ImpImporter.iter_modules(self, prefix):
            self._log('iter_modules(..., %s): yield: %s, %s'%(prefix, _name_sandbox(self.sandbox, name), is_pkg))

            yield _name_sandbox(self.sandbox, name), is_pkg

    def _log(self, msg):
        _log(self.sandbox, msg)


class ImpLoaderSandbox(pkgutil.ImpLoader):
    def __init__(self, fullname, fil, filename, etc):
        self.sandbox = _name_get_sandbox(fullname)

        self._log('ImpLoaderSandbox(%s, %s, %s, %s, %s)'%(self, fullname, fil, filename, etc))

        pkgutil.ImpLoader.__init__(self, fullname, fil, filename, etc)

    def load_module(self, fullname):
        self._log('load_module(%s, %s)'%(self, fullname))

        sandboxfullname = _name_sandbox(self.sandbox, fullname)

        #
        # NOTE: Kodi, before running an addon, seems to load the top level packages found in the
        #   required section of the addon itself (e.g. for the dependency script.module.requests,
        #   Kodi loads the "requests" package found in "addons/script.module.requests/lib/" directory).
        #   This is done before the importer machinery is hooked up by the addon, so the required
        #   top level packages are inserted in sys.modules not sandboxed (e.g. as "requests" not as
        #   "script_module_requests@requests"). This is not a problem from a conflict point of
        #   view as these packages should not conflict at all and, if they are, the module that imports it
        #   can change the import statement. However, subsequently, this importer module fails to find them.
        #   The check below is performed to verify this scenario and eventually patch the sys.modules.
        #
        cleanfullname = _name_desandbox(sandboxfullname)
        grandparent = cleanfullname.split('.')[0]
        if grandparent != cleanfullname:
            sandboxgrandparent = _name_sandbox(self.sandbox, grandparent)
            if sandboxgrandparent in sys.modules:
                self._log('load_module(..., %s): sandboxed grand parent module %s found in the cache: %s'%
                          (fullname, sandboxgrandparent, sys.modules[sandboxgrandparent]))
            elif grandparent in sys.modules:
                self._log('load_module(..., %s): grand parent module %s found in the cache: %s'%
                          (fullname, grandparent, sys.modules[grandparent]))
                # The top level module is already loaded in sys.modules not sandboxed
                sys.modules[sandboxgrandparent] = sys.modules[grandparent]

        #
        # NOTE: This breaks the module reload semantic because of the sys.modules check!
        #   Hopefully, not many addons are going to use the reload mechanism.
        #
        if sandboxfullname in sys.modules:
            mod = sys.modules[sandboxfullname]

            self._log('load_module(..., %s): module %s found in the cache: %s'%(fullname, sandboxfullname, mod))
        else:
            self._log('load_module(..., %s): loading module %s...'%(self, sandboxfullname))

            mod = pkgutil.ImpLoader.load_module(self, sandboxfullname)

        if not mod:
            self._log('load_module(..., %s): loading module %s failed'%(fullname, sandboxfullname))
        else:
            self._log('load_module(..., %s): %s loaded: __name__=%s, __file__=%s, __package__=%s, __path__=%s'%
                      (fullname, sandboxfullname, mod.__name__, mod.__file__, mod.__package__,
                       mod.__path__ if hasattr(mod, '__path__') else 'NO ATTRIBUTE'))

        return mod

    def _log(self, msg):
        _log(self.sandbox, msg)
