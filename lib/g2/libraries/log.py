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
import sys
import inspect
import traceback
import threading

import xbmc
import xbmcaddon


_debug_attribute = '_log_debug'
_trace_attribute = '_log_trace_on_error'

_ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
try:
    _THREAD_ID = int(sys.argv[1])
except Exception:
    _THREAD_ID = -1

_LEVEL_NAME = {
    xbmc.LOGDEBUG: 'debug',
    xbmc.LOGINFO: 'info',
    xbmc.LOGNOTICE: 'notice',
    xbmc.LOGERROR: 'error',
}


def debug(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGDEBUG, *args, **kwargs)


def info(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGINFO, *args, **kwargs)


def notice(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGNOTICE, *args, **kwargs)


def error(msg, *args, **kwargs):
    return _log(msg, xbmc.LOGERROR, *args, **kwargs)


def _log(msg, level, *args, **kwargs):
    try:
        level_info = ''
        if level in [xbmc.LOGDEBUG, xbmc.LOGINFO]:
            newlevel = _check_for_debug(level)
            if newlevel != level:
                level_info = 'DEBUG: ' if level == xbmc.LOGDEBUG else '[INFO]'
                level = newlevel
        if '{m}' in msg or '{f}' in msg or '{t}' in msg:
            ids = _fetch_ids()
            for i in ['m', 'f', 't']:
                msg = msg.replace('{%s}'%i, ids[i])
        if len(args):
            msg = msg % args
        if isinstance(msg, unicode):
            msg = '%s (utf-8)'%msg.encode('utf-8')
        xbmc.log('%s[%s%s] %s'%(level_info, _ADDON_ID, ('' if _THREAD_ID < 0 else ':%d'%_THREAD_ID), msg), level)
    except Exception:
        try:
            xbmc.log('log.%s("%s", %s, %s): %s'%(_LEVEL_NAME.get(level), msg, args, kwargs, traceback.format_exc()),
                     xbmc.LOGNOTICE)
        except Exception:
            pass
    try:
        if kwargs.get('trace') or (level >= xbmc.LOGERROR and _check_for_debug(xbmc.LOGDEBUG, _trace_attribute) != xbmc.LOGDEBUG):
            stacktrace = traceback.format_exc()
            if stacktrace and not stacktrace.startswith('None'):
                xbmc.log('[%s%s] %s'%(_ADDON_ID, ('' if _THREAD_ID < 0 else ':%d'%_THREAD_ID), stacktrace), level)
    except Exception:
        pass
    return msg


def _check_for_debug(level, attribute=_debug_attribute):
    stack = inspect.stack()
    return level if len(stack) <= 3 or not stack[3][0].f_globals.get(attribute) else xbmc.LOGNOTICE


def _fetch_ids():
    ids = {}
    stack = None
    try:
        stack = inspect.stack()
        if len(stack) <= 3:
            raise Exception()
        module = stack[3][1]
        ids.update({
            'm': os.path.basename(os.path.dirname(module)) if module.endswith('__init__.py') else
                 os.path.splitext(os.path.basename(module))[0],
            'f': stack[3][3],
        })
    except Exception:
        ids.update({
            'm': '',
            'f': '',
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
