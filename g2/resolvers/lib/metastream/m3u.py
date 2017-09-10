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


import re

from g2.libraries import log


def video_resolution(fileobj, stop_at_bytes=0):
    m3u = fileobj.read(stop_at_bytes)

    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=853000,RESOLUTION=512x288,CODECS="avc1.77.30, mp4a.40.2",CLOSED-CAPTIONS=NONE
    resolutions = sorted([(int(m.group(1)), int(m.group(2))) for m in re.finditer(r'RESOLUTION=(\d+)x(\d+)', m3u)],
                         cmp=lambda x, y: cmp(x[0]*x[1], y[0]*y[1]))

    return (0, 0) if not resolutions else resolutions[-1]
