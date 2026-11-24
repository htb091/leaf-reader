#!/usr/bin/env python3
"""Generate original LeafReader RGB app icons with Python's standard library."""
import json
import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1] / 'Assets.xcassets'
DEST = ROOT / 'AppIcon.appiconset'


def bezier(points, steps=48):
    a, b, c, d = points
    result = []
    for i in range(steps + 1):
        t = i / steps
        result.append(tuple((1-t)**3*a[k] + 3*(1-t)**2*t*b[k] + 3*(1-t)*t*t*c[k] + t**3*d[k] for k in (0, 1)))
    return result


def icon(size):
    factor = 3 if size < 200 else 1
    width = size * factor
    scale = width / 1024
    pixels = bytearray(width * width * 3)
    for y in range(width):
        t = y / max(1, width - 1)
        color = bytes((round(35 - 16*t), round(88 - 33*t), round(79 - 28*t)))
        pixels[y*width*3:(y+1)*width*3] = color * width

    def polygon(points, color):
        points = [(x*scale, y*scale) for x, y in points]
        for y in range(max(0, int(min(p[1] for p in points))), min(width, math.ceil(max(p[1] for p in points)))):
            scan = y + 0.5
            cuts = []
            for i, (x1, y1) in enumerate(points):
                x2, y2 = points[(i+1) % len(points)]
                if (y1 <= scan < y2) or (y2 <= scan < y1):
                    cuts.append(x1 + (scan-y1) * (x2-x1) / (y2-y1))
            cuts.sort()
            for i in range(0, len(cuts)-1, 2):
                left = max(0, math.ceil(cuts[i]-0.5))
                right = min(width, math.ceil(cuts[i+1]-0.5))
                if right > left:
                    offset = (y*width + left) * 3
                    pixels[offset:offset+(right-left)*3] = bytes(color) * (right-left)

    def line(start, end, thickness, color):
        dx, dy = end[0]-start[0], end[1]-start[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy/length*thickness/2, dx/length*thickness/2
        polygon([(start[0]+nx, start[1]+ny), (end[0]+nx, end[1]+ny),
                 (end[0]-nx, end[1]-ny), (start[0]-nx, start[1]-ny)], color)

    # Open book: a quiet two-page silhouette with a warm fold.
    polygon([(222,492),(421,522),(512,576),(603,522),(802,492),
             (802,760),(601,792),(512,842),(423,792),(222,760)], (13, 43, 40))
    polygon([(236,470),(425,505),(512,557),(512,815),(422,765),(236,735)], (248, 245, 224))
    polygon([(512,557),(599,505),(788,470),(788,735),(602,765),(512,815)], (229, 235, 208))
    line((512,566),(512,798),10,(180,197,164))
    for y in (587,642,697):
        line((286,y),(424,y+28),9,(195,207,176))
        line((600,y+28),(738,y),9,(176,195,161))
    # Original leaf built from two cubic curves, not an external asset.
    leaf = bezier([(454,487),(411,314),(548,177),(756,197)])
    leaf += bezier([(756,197),(772,386),(632,499),(454,487)])[1:]
    polygon(leaf, (155, 205, 155))
    vein = bezier([(465,475),(535,410),(624,313),(727,222)], 24)
    for a, b in zip(vein, vein[1:]):
        line(a,b,11,(226,237,194))
    line((547,395),(524,316),8,(226,237,194))
    line((609,331),(693,325),8,(226,237,194))

    if factor > 1:
        reduced = bytearray(size*size*3)
        for y in range(size):
            for x in range(size):
                for c in range(3):
                    reduced[(y*size+x)*3+c] = sum(pixels[((y*factor+dy)*width+x*factor+dx)*3+c]
                                                  for dy in range(factor) for dx in range(factor)) // (factor*factor)
        pixels = reduced
    rows = b''.join(b'\x00' + pixels[y*size*3:(y+1)*size*3] for y in range(size))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',size,size,8,2,0,0,0))
            + chunk(b'IDAT',zlib.compress(rows,9)) + chunk(b'IEND',b''))


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    images = []
    specifications = [('iphone','20',2),('iphone','20',3),('iphone','29',2),('iphone','29',3),
                      ('iphone','40',2),('iphone','40',3),('iphone','60',2),('iphone','60',3),
                      ('ipad','20',1),('ipad','20',2),('ipad','29',1),('ipad','29',2),
                      ('ipad','40',1),('ipad','40',2),('ipad','76',1),('ipad','76',2),
                      ('ipad','83.5',2),('ios-marketing','1024',1)]
    sizes = set()
    for idiom, points, scale in specifications:
        size = round(float(points)*scale)
        sizes.add(size)
        images.append({'idiom':idiom,'size':f'{points}x{points}','scale':f'{scale}x','filename':f'AppIcon-{size}.png'})
    for size in sorted(sizes):
        (DEST / f'AppIcon-{size}.png').write_bytes(icon(size))
    info = {'author':'LeafReader','version':1}
    (ROOT / 'Contents.json').write_text(json.dumps({'info':info},indent=2)+'\n')
    (DEST / 'Contents.json').write_text(json.dumps({'images':images,'info':info},indent=2)+'\n')
    print(f'Generated {len(sizes)} original RGB PNG icons for {len(images)} slots')


if __name__ == '__main__':
    main()
