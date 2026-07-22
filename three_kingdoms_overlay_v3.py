#!/usr/bin/env python3
"""
汉末三国十三州地图图层生成器 v3

参考图风格：细红线（3px）、紧凑红色小标签、实心小圆点、小字

考据依据:
  《汉书·地理志》《后汉书·郡国志》
  谭其骧《中国历史地图集》第二册
"""

import os
import argparse
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PNG = os.path.join(BASE_DIR, 'china_full_v3.png')
OUTPUT_DIR = os.path.join(BASE_DIR, 'rendered')

LON_MIN, LON_MAX = 75.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0
IMG_W, IMG_H = 15600, 9600

# ── 视觉 ──
BORDER_COLOR = (180, 30, 30, 220)    # 细红线
BORDER_WIDTH = 3

SEAL_RED = (160, 25, 25, 210)
SEAL_DARK_RED = (120, 15, 15, 200)
SEAL_TEXT = (255, 235, 200, 245)
STATE_FONT_SIZE = 80

CITY_FONT_SIZE = 36
CITY_SMALL = 32
DOT_R = 4
DOT_COLOR = (180, 30, 30, 220)

PASS_FONT_SIZE = 34
TRI_SZ = 8
TRI_COLOR = (160, 50, 40, 210)

TITLE_FONT_SIZE = 50
NOTE_FONT_SIZE = 30

TEXT_WHITE = (255, 255, 255, 245)
TEXT_WHITE_OUT = (30, 25, 20, 200)
TEXT_DARK = (40, 30, 25, 235)
TEXT_DARK_OUT = (230, 225, 215, 180)

FONT_PATHS = [
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
]


def get_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def px(lon, lat):
    x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * IMG_W
    y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * IMG_H
    return (x, y)


def pxi(lon, lat):
    x, y = px(lon, lat)
    return (int(round(x)), int(round(y)))


def outline_text(draw, x, y, text, font, fill, out, ox=2, oy=2):
    for dx, dy in [(-ox,0),(ox,0),(0,-oy),(0,oy),
                   (-ox,-oy),(ox,-oy),(-ox,oy),(ox,oy)]:
        draw.text((x+dx, y+dy), text, font=font, fill=out)
    draw.text((x, y), text, font=font, fill=fill)
