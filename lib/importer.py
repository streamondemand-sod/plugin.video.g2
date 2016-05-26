# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016 J0rdyZ65

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


#                           === IMPORTANT NOTE ===
# For some reason, declaring an addon required in the g2 addon.xml seems to broke
# the importer in way that the addon itself cannot be directly imported and used.
#
# For example:
#   [plugin.video.g2/addon.xml]
#           <requires>
#               ...
#               <import addon="script.module.metahandler" optional="true" />
#           </requires>
#
# Actually prevents to use metahandler in the g2 code, like:
#   from metahandler import metahandlers
#   metahandlers.MetaDat()...
#
# It chokes on the import statement with an error like:
#   ImportError: No module named TMDB
#
# On the other hand, creating a package for exactly the same module and let it be
# loaded through the packages methods, works fine!
#
# (fixme)[code]: direct import of required addon libraries
#


_log_level = False # xbmc.LOGNOTICE
_handled_paths = {}
_SANDBOX_NAMESPACE_SEP = '@'


def _name_is_sandboxed(fullname):
    return _SANDBOX_NAMESPACE_SEP in fullname


def _name_sandbox(self, fullname):
    if _name_is_sandboxed(fullname) or not self.sandbox:
        return fullname
    else:
        return self.sandbox+_SANDBOX_NAMESPACE_SEP+fullname


def _name_get_sandbox(fullname):
    return None if not _name_is_sandboxed(fullname) else fullname.split(_SANDBOX_NAMESPACE_SEP, 1)[0]


def _name_desandbox(fullname):
    return fullname if not _name_is_sandboxed(fullname) else fullname.split(_SANDBOX_NAMESPACE_SEP, 1)[1]


def log(msg):
    if _log_level: xbmc.log(msg, level=_log_level)


def add_path(path):
    if not os.path.isdir(path): return
    sandbox = os.path.basename(path).replace('.', '_')
    for p in [path, os.path.realpath(path)]:
        if p not in _handled_paths:
            _handled_paths[p] = sandbox
            log('importer.add_path(%s): added path %s with %s as sandbox prefix'%(path, p, sandbox))


def walk_packages(path=None, prefix='', onerror=None):
    log('importer.walk_packages(%s, %s, %s)'%(path, prefix, onerror))

    for package, name, is_pkg in pkgutil.walk_packages(path, prefix, onerror):
        log('importer.walk_packages(%s, ...): yield: %s, %s, %s'%(path, package, _name_desandbox(name), is_pkg))

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
        log('ImpImporterSandbox.__init__(%s, %s)'%(self, path_entry))

        for hp, sandbox in _handled_paths.iteritems():
            if path_entry.startswith(hp):
                pkgutil.ImpImporter.__init__(self, path_entry)

                self.sandbox = sandbox
                log('ImpImporterSandbox.__init__(..., %s): handled: sandbox=%s'%(path_entry, self.sandbox))
                return

        log('ImpImporterSandbox.__init__(..., %s): not handled'%path_entry)
        raise ImportError()

    def find_module(self, fullname, path=None):
        log('ImpImporterSandbox.find_module(%s, %s, %s)'%(self, fullname, path))

        if self.sandbox is None:
            log('ImpImporterSandbox.find_module(): sandbox is None')
            return None

        impl = pkgutil.ImpImporter.find_module(self, fullname, path)
        if not impl:
            log('ImpImporterSandbox.find_module(..., %s, ...): module not found'%fullname)
            return None

        log('ImpImporterSandbox.find_module(..., %s, ...): sandbox=%s, impl.fullname=%s, file=%s, filename=%s, etc=%s'%(fullname, self.sandbox, impl.fullname, impl.file, impl.filename, impl.etc))

        return ImpLoaderSandbox(_name_sandbox(self, impl.fullname), impl.file, impl.filename, impl.etc)

    def iter_modules(self, prefix=''):
        log('ImpImporterSandbox.iter_modules(%s, %s)'%(self, prefix))

        for name, is_pkg in pkgutil.ImpImporter.iter_modules(self, prefix):
            log('ImpImporterSandbox.iter_modules(..., %s): yield: %s, %s'%(prefix, _name_sandbox(self, name), is_pkg))

            yield _name_sandbox(self, name), is_pkg


class ImpLoaderSandbox(pkgutil.ImpLoader):
    def __init__(self, fullname, file, filename, etc):
        log('ImpLoaderSandbox.__init__(%s, %s, %s, %s, %s)'%(self, fullname, file, filename, etc))

        self.sandbox = _name_get_sandbox(fullname)

        pkgutil.ImpLoader.__init__(self, fullname, file, filename, etc)

    def load_module(self, fullname):
        log('ImpLoaderSandbox.load_module(%s, %s)'%(self, fullname))

        sandboxfullname = _name_sandbox(self, fullname)

        # Load all parents modules first
        parents = _name_desandbox(sandboxfullname).split('.')
        for i in range(0, len(parents)-1):
            sandboxparent = _name_sandbox(self, '.'.join(parents[0:i+1]))
            if sandboxparent in sys.modules:
                log('ImpLoaderSandbox.load_module(..., %s): parent module %s found in the cache'%(fullname, sandboxparent))
            else:
                log('ImpLoaderSandbox.load_module(..., %s): loading parent module %s...'%(self, sandboxparent))

                if not pkgutil.ImpLoader.load_module(self, sandboxparent):
                    log('ImpLoaderSandbox.load_module(..., %s): loading parent module %s failed'%(self, sandboxparent))

        # NOTE: This breaks the module reload semantic because of the sys.modules check!
        # NOTE: Hopefully, not many addons are going to use the reload mechanism.
        if sandboxfullname in sys.modules:
            log('ImpLoaderSandbox.load_module(..., %s): module %s found in the cache'%(fullname, sandboxfullname))

            mod = sys.modules[sandboxfullname]
        else:
            log('ImpLoaderSandbox.load_module(..., %s): loading module %s...'%(self, sandboxfullname))

            mod = pkgutil.ImpLoader.load_module(self, sandboxfullname)

        if not mod:
            log('ImpLoaderSandbox.load_module(..., %s): loading module %s failed'%(fullname, sandboxfullname))
        else:
            log('ImpLoaderSandbox.load_module(..., %s): module %s loaded: __name__=%s, __file__=%s, __package__=%s, __path__=%s'%
                (fullname, sandboxfullname, mod.__name__, mod.__file__, mod.__package__, mod.__path__ if hasattr(mod, '__path__') else 'NO ATTRIBUTE'))

        return mod
