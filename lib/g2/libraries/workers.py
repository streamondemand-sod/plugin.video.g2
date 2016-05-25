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


import threading
import datetime

from contextlib import contextmanager

from g2.libraries import log


Lock = threading.Lock
current_thread = threading.current_thread


class Thread(threading.Thread):
    def __init__(self, target, *args, **kwargs):
        threading.Thread.__init__(self)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.started = None
        self.stopped = None
        self.exc = None
        self.result = None
        self.die = False
        self.daemon = True # Let's not block kodi in case a thread runaway

    def run(self):
        try:
            self.started = datetime.datetime.now()
            log.debug('Thread.run(%s): started at %s'%(self.name, self.started))
            self.result = self.target(*self.args, **self.kwargs)
        except:
            import traceback
            log.notice('Thread.run(%s): %s'%(self.name, traceback.format_exc()))
        finally:
            self.stopped = datetime.datetime.now()
            log.debug('Thread.run(%s): elapsed for %.6fs%s'%(self.name, self.elapsed(), '' if not self.die else ' (asked to die)'))

    def elapsed(self):
        if not self.started:
            return None
        else:
            elapsed = (self.stopped if self.stopped else datetime.datetime.now()) - self.started
            return elapsed.days*86400 + elapsed.seconds + float(elapsed.microseconds)/1000000


@contextmanager
def non_blocking(lock):
    if not lock.acquire(False):
        raise WouldBlockError
    try:
        yield lock
    finally:
        lock.release()
