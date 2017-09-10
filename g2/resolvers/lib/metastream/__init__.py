# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Based on the original idea/code of boogiekodi@GitHub for his ump plugin
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


import struct

from g2.libraries import log

# Do not read more that 100KB in the stream to look for the resolution
_MAX_BYTE_READ_FOR_RESOLUTION = 100 * 1024


def video(fil):
    first8 = fil.read(8)
    meta = {}
    if len(first8) < 8:
        meta['firstbytes'] = first8
        return meta

    size, atom = struct.unpack('>i4s', first8)
    if atom == 'ftyp':
        from . import mp4 as decoder
        fil.read(size-8)           # Skip to the next mp4 atom
        meta['type'] = 'mp4'

    elif first8[:3] == "FLV":
        from . import flv as decoder
        fil.read(1)                # Skip to the first flv header packet
        meta['type'] = 'flv'

    elif 'EXTM3U' in first8:
        from . import m3u as decoder
        meta['type'] = 'm3u'

    else:
        meta['firstbytes'] = first8
        return meta

    meta['width'], meta['height'] = decoder.video_resolution(fil, stop_at_bytes=_MAX_BYTE_READ_FOR_RESOLUTION)
    if meta['width'] < 0 or meta['height'] < 0:
        meta['type'] += '?'

    return meta
