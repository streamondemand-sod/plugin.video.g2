# -*- coding: utf-8 -*-

"""
    Genesi2 Add-on
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


import xbmc

from g2.libraries import log
from g2.libraries import platform
from g2 import notifiers

from .lib import ui


_log_debug = True


class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        _check_changes('setting')


_MONITOR_OBJECTS = {}
_PLAYER = xbmc.Player()
_MONITOR = Monitor()


def monitor(monitorid, kind, callback, *args, **kwargs):
    if kind not in ['setting', 'property', 'player']:
        log.error('{m}.{f}(%s): monitor object %s not implemented!', monitorid, kind)
        return

    if not callable(callback):
        log.error('{m}.{f}(%s): callback %s is not callable!', monitorid, callback)
        return

    _MONITOR_OBJECTS[monitorid] = {
        'id': monitorid,
        'kind': kind,
        'value': _get_objectvalue(monitorid, kind),
        'callback': callback,
        'args': args,
        'kwargs': kwargs,
        'thread': None,
        'thread_status': None,
    }

    log.debug('{m}.{f}(%s): %s', monitorid, _MONITOR_OBJECTS[monitorid])


def _get_objectvalue(monitorid, kind):
    if kind == 'setting':
        return platform.freshsetting(monitorid)
    elif kind == 'property':
        return platform.property(monitorid)
    elif kind == 'player':
        return _player_state(monitorid)


def _check_changes(kind):
    for moid, mobj in {mi: mo for mi, mo in _MONITOR_OBJECTS.iteritems()
                        if mo['kind'] == kind and mo['value'] != _get_objectvalue(mi, kind)}.iteritems():
        new_value = _get_objectvalue(moid, kind)
        log.debug('service[{t}]: monitored object %s %s changed: %s -> %s',
                  moid, mobj['kind'], mobj['value'], new_value)
        mobj['value'] = new_value
        if mobj['thread']:
            # For service threads to be stopped, the new value should evaluate False
            if not new_value or new_value == 'false':
                _service_thread_shutdown(moid)
        else:
            if moid in mobj['kwargs']:
                mobj['kwargs'][moid] = new_value
            thd = mobj['callback'](*mobj['args'], **mobj['kwargs'])
            # For service threads to be started, the new value should evaluate True
            if thd and new_value:
                _service_thread_start(moid, thd)


_THREADS = {}


def _service_thread_start(monitorid, thread):
    log.notice('service[{t}]: %s thread starting...', monitorid)
    _MONITOR_OBJECTS[monitorid]['thread'] = thread
    _MONITOR_OBJECTS[monitorid]['thread_status'] = None
    _THREADS[monitorid] = thread
    thread.name = monitorid
    log.debug('service[{t}]: %s thread: %s', monitorid, thread)
    thread.start()


def _service_thread_status(monitorid):
    status = _THREADS[monitorid].result
    if status == _MONITOR_OBJECTS[monitorid]['thread_status']:
        return None
    else:
        _MONITOR_OBJECTS[monitorid]['thread_status'] = status
        return status


def _service_thread_shutdown(monitorid):
    if not _THREADS[monitorid].die:
        log.notice('service[{t}]: %s thread shutting down...', monitorid)
    _THREADS[monitorid].die = True


def _service_thread_cleanup(monitorid):
    log.notice('service[{t}]: %s thread terminated after %.3f secs', monitorid, _THREADS[monitorid].elapsed())
    _MONITOR_OBJECTS[monitorid]['thread'] = None
    del _THREADS[monitorid]
    if _MONITOR_OBJECTS[monitorid]['kind'] == 'setting':
        platform.setSetting(monitorid, 'false')
    elif _MONITOR_OBJECTS[monitorid]['kind'] == 'property':
        platform.property(monitorid, False)


def _player_state(monitorid):
    if monitorid == 'playing':
        return None if not _PLAYER.isPlaying() else \
               'audio' if _PLAYER.isPlayingAudio() else \
               'video' if _PLAYER.isPlayingVideo() else None

    return None


def thread(name=None, **dummy_kwargs):
    log.notice('service thread[%s] started ({t})', name)

    try:
        for mobj in _MONITOR_OBJECTS.itervalues():
            log.notice('service[%s]: monitored %s %s', name, mobj['id'], mobj['kind'])

        while not ui.abortRequested() and platform.property('service', name=name):
            _check_changes('property')
            _check_changes('player')

            notices = []
            for thd in list(_THREADS.values()):
                if thd.is_alive():
                    notice = _service_thread_status(thd.name)
                else:
                    notice = _service_thread_status(thd.name)
                    _service_thread_cleanup(thd.name)
                if notice:
                    notices.append(notice)

            if notices:
                notifiers.notices(notices, playing=_player_state('playing'))

            ui.sleep(1000)

        for secs in range(5):
            alive_threads = [t for t in _THREADS.values() if t.is_alive()]
            if not alive_threads:
                break
            for thd in alive_threads:
                _service_thread_shutdown(thd.name)
            ui.sleep(1000)
    except Exception as ex:
        log.error('service[%s]: %s', name, ex)

    log.notice('service thread[%s] stopped ({t})', name)

    platform.property('service', '', name=name)
