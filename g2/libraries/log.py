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
import re
import ast
import sys
import errno
import inspect
import traceback
import threading

import xbmc
import xbmcaddon


_ADDON = xbmcaddon.Addon()
_ADDON_ID = _ADDON.getAddonInfo('id')
_ADDON_VERSION = _ADDON.getAddonInfo('version')
try:
    _THREAD_ID = int(sys.argv[1])
except Exception:
    _THREAD_ID = -1
_CONFIG_PATH = xbmc.translatePath(os.path.join(_ADDON.getAddonInfo('profile'), '.logconfig.py'))


_SPECIAL_TAGS = [
    'p',    # package name
    'm',    # module name
    'f',    # function name
    't',    # thread object address
    'cf',   # calling module.function
    'v',    # addon version
]

_CONFIG = {}


def debug(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGDEBUG, *args, **kwargs)


def info(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGINFO, *args, **kwargs)


def notice(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGNOTICE, *args, **kwargs)


def error(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGERROR, *args, **kwargs)


def perfactive():
    ids = _fetch_ids(1)
    # Log performance related stats for...
    config = (_CONFIG.get(ids['m']+'.'+ids['f']) or
              _CONFIG.get(ids['cf']+'.'+ids['m']+'.'+ids['f']))
    try:
        return 'P' in config
    except Exception:
        return False


def debugactive(ids=None, calling_context=True):
    if ids is None:
        ids = {}
    ids.update(_fetch_ids(1 if calling_context else 3))
    # Debug...
    return (_CONFIG.get(ids['p']) or                    # the entire package
            _CONFIG.get(ids['p']+'.'+ids['m']) or       # a specific package.module
            _CONFIG.get(ids['m']+'.'+ids['f']) or       # a specific module.function
            _CONFIG.get(ids['cf']+'.'+ids['f']))        # a specific function when called by a specific module.function


def _log(msg, level, *args, **kwargs):
    debug = kwargs.get('debug')
    trace = kwargs.get('trace')
    try:
        ids = {}
        orig_level = ''
        if level in [xbmc.LOGDEBUG, xbmc.LOGINFO]:
            if debug or debugactive(ids, calling_context=False):
                orig_level = 'DEBUG' if level == xbmc.LOGDEBUG else 'INFO'
                level = xbmc.LOGNOTICE

        if any('{%s}'%tag in msg for tag in _SPECIAL_TAGS):
            if not ids:
                ids = _fetch_ids()
            for tag in _SPECIAL_TAGS:
                msg = msg.replace('{%s}'%tag, ids[tag] or '---')

        if len(args):
            msg = msg % args
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8') + ' (utf-8)'

        xbmc.log('%s[%s%s] %s'%(orig_level, _ADDON_ID, ('' if _THREAD_ID < 0 else ':%d'%_THREAD_ID), msg), level)
    except Exception:
        try:
            xbmc.log('log.%s("...", %s, %s): %s'%(orig_level.lower(), args, kwargs, traceback.format_exc()),
                     xbmc.LOGNOTICE)
            trace = True
        except Exception:
            pass

    if trace:
        try:
            stacktrace = traceback.format_exc()
            if stacktrace and not stacktrace.startswith('None'):
                xbmc.log('[%s%s] %s'%(_ADDON_ID, ('' if _THREAD_ID < 0 else ':%d'%_THREAD_ID), stacktrace), level)
        except Exception:
            pass

    return msg


def _fetch_ids(ids_level=2):
    def module_name(path):
        return os.path.basename(os.path.dirname(path)) if path.endswith('__init__.py') else \
               os.path.splitext(os.path.basename(path))[0]

    ids = {
        'v': _ADDON_VERSION,
    }
    stack = None
    try:
        ids_level += 1
        stack = inspect.stack(0)
        if len(stack) <= ids_level:
            raise Exception()
        module = stack[ids_level][1]
        function = stack[ids_level][3]
        ids.update({
            'p': os.path.basename(os.path.dirname(module)),
            'm': module_name(module),
            'f': function,
        })
        if len(stack) > ids_level+1:
            calling_module = stack[ids_level+1][1]
            calling_function = stack[ids_level+1][3]
            ids.update({
                'cf': '%s.%s'%(module_name(calling_module), calling_function),
            })
    except Exception:
        ids.update({
            'p': '',
            'm': '',
            'f': '',
            'cf': '',
        })
    finally:
        del stack

    try:
        ids.update({
            't': hex(int(re.search(r'\s+started\s+-?([\d]+)', str(threading.current_thread())).group(1))),
        })
    except Exception:
        ids.update({
            't': '',
        })

    return ids


try:
    with open(_CONFIG_PATH) as fil:
        _CONFIG = ast.literal_eval(fil.read().strip())
    if type(_CONFIG) != dict:
        raise Exception('the log configuration file should contain a single python dictionary')
except IOError as ex:
    if ex.errno != errno.ENOENT:
        error('{m}.{f}: %s: %s', _CONFIG_PATH, repr(ex))
except Exception as ex:
    error('{m}.{f}: %s: %s', _CONFIG_PATH, repr(ex))

notice('logging config: %s', _CONFIG)
