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


import threading
import datetime

from contextlib import contextmanager

from g2.libraries import log


Lock = threading.Lock
current_thread = threading.current_thread


class WouldBlockError(Exception):
    pass


class Thread(threading.Thread):
    def __init__(self, target, *args, **kwargs):
        if target is not None:
            threading.Thread.__init__(self, target=target, args=args, kwargs=kwargs)
        self.started = None
        self.stopped = None
        self.exc = None
        self.result = None
        self.die = False
        if not self.is_alive():
            self.daemon = True # Let's not block kodi in case a thread runaway

    def init(self):
        self.__init__(None)

    def run(self):
        try:
            self.started = datetime.datetime.now()
            log.debug('Thread.run: %s: started at %s'%(self.name, self.started))
            if self.__target:
                self.result = self.__target(*self.__args, **self.__kwargs)
            # self.result = self.target(*self.args, **self.kwargs)
        except Exception as ex:
            log.error('Thread.run: %s: %s', self.name, repr(ex), trace=True)
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self.__target, self.__args, self.__kwargs
            self.stopped = datetime.datetime.now()
            log.debug('Thread.run: %s: elapsed for %.6fs%s',
                      self.name, self.elapsed(), '' if not self.die else ' (asked to die)')

    def elapsed(self):
        if not self.started:
            return None
        else:
            elapsed = (self.stopped if self.stopped else datetime.datetime.now()) - self.started
            return elapsed.days*86400 + elapsed.seconds + float(elapsed.microseconds)/1000000


def promote(thread):
    if not isinstance(thread, threading.Thread):
        return False
    if not isinstance(thread, Thread):
        thread.__class__ = Thread
        thread.init()
    return True


@contextmanager
def non_blocking(lock):
    if not lock.acquire(False):
        raise WouldBlockError
    try:
        yield lock
    finally:
        lock.release()
