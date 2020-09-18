from PIL import Image, ImageDraw, ImageEnhance
from time import time, perf_counter as clock
from math import exp, pi, cos, sin, hypot
from win32.win32gui import SetWindowPos
from collections import OrderedDict
from win32.lib import win32con
from PyQt import QtCore, QtGui
from io import BytesIO as IO
import resources_shuffler
import subprocess
import traceback
import winshell
import win32gui
import win32api
import random
import types
import math
import os
VERSION = '0.1'
TITLE = 'Shuffler v{}'.format(VERSION)
FORMATS = ['bmp', 'gif', 'jpeg', 'jfif', 'jpg', 'png', 'webp']
CACHE = OrderedDict()
CACHE_SIZE = 2
DPI = None
COLOR = {}
COLOR['main_org'] = (18, 119, 235)
COLOR['main'] = COLOR['main_org']
COLOR['red'] = (255, 45, 85)
DARKMODE = False
ICONS = {}
FPS = 60
ALPHA_HL = False
HEIGHT = 3
R_HANDLE = 6
R_HANDLE_PRESS = 8
DEBUG = False
k_hl = 0.3
k_pr = 0.2
float_org = float
SPEED = 1.0
SHADOW = True
AA = True
R = 3
opacity_max = 1.0
ALPHA = 0.3
FAST_BLUR = False
PYQT = hasattr(QtCore, 'PYQT_VERSION_STR')


def float(x):
    if x is None:
        return 0.0
    else:
        return float_org(x)



def nothing():
    pass


def apply_effect_to_pixmap(src, effect, extent=0.0):
    if src.isNull():
        return QtGui.QPixmap()
    if not effect:
        return src
    size = src.size() + QtCore.QSize(extent, extent) * 2
    scene = QtGui.QGraphicsScene()
    item = QtGui.QGraphicsPixmapItem()
    item.setPixmap(src)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    res = QtGui.QPixmap(size)
    color = QtGui.QColor(255, 0, 255) if DEBUG else QtCore.Qt.transparent
    res.fill(color)
    ptr = QtGui.QPainter(res)
    scene.render(ptr, QtCore.QRectF(), QtCore.QRectF(-extent, -extent, size.width(), size.height()))
    return res


class QGraphicsEffect(QtGui.QGraphicsEffect):
    

    def sourcePixmap(self, system, offset, mode):
        if PYQT:
            px, offset_ = super(QGraphicsEffect, self).sourcePixmap(QtCore.Qt.DeviceCoordinates, mode)
            offset.setX(offset_.x())
            offset.setY(offset_.y())
        else:
            px = super(QGraphicsEffect, self).sourcePixmap(QtCore.Qt.DeviceCoordinates, offset, mode)
        return px



class Shadow(QGraphicsEffect):
    _radius = 3.0
    _color = None
    _opacity = 1.0
    _drawMain = True

    def __init__(self, parent=None, dpi=None, fast_blur=None):
        super(Shadow ,self).__init__(parent)
        if dpi is None:
            self.dpi = dpi()
        else:
            self.dpi = dpi
        self.fast_blur = fast_blur

    def offset(self):
        fast_blur = FAST_BLUR if self.fast_blur is None else self.fast_blur
        return math.ceil(self._radius * self.dpi / 96 * (2.2 if fast_blur else 2.0))

    def setRadius(self, r):
        self._radius = r
        self.updateBoundingRect()

    def setColor(self, color):
        self._color = color

    def setOpacity(self, opacity):
        self._opacity = opacity

    def color(self):
        c = self._color
        if c == 'HL':
            c = COLOR['main']
        return c

    def setDrawMain(self, flag):
        self._drawMain = flag

    def draw(self, painter):
        #print('blurEffect.Shadow.draw', clock())
        mode = QGraphicsEffect.PadToEffectiveBoundingRect
        offset = QtCore.QPoint()
        px = self.sourcePixmap(QtCore.Qt.DeviceCoordinates, offset, mode)
        if px.isNull():
            return
        dpi = self.dpi
        restore_transform = painter.worldTransform()
        painter.setWorldTransform(QtGui.QTransform())
        painter.save()
        painter.translate(offset + QtCore.QPoint(self.offset(), self.offset()))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self._radius * dpi / 96.0 * 1.35
        alpha = self._opacity * 0.16 * 1.05
        if r < 2:
            alpha *= r * 0.5
            r = 2
        rem = r % 1
        draw_shadow(painter, px, self.offset(), r // 1, alpha * (1 - rem), r // 1 * 0.15, self.color(), self.fast_blur)
        if rem:
            draw_shadow(painter, px, self.offset(), r // 1 + 1, alpha * rem, (r // 1 + 1) * 0.15, self.color(), self.fast_blur)
        r = self._radius * dpi / 96.0
        alpha = self._opacity * 0.24 * 1.1
        if r < 2:
            alpha *= r * 0.5
            r = 2
        rem = r % 1
        draw_shadow(painter, px, self.offset(), r // 1, alpha * (1 - rem), r // 1 * 0.39, self.color(), self.fast_blur)
        if rem:
            draw_shadow(painter, px, self.offset(), r // 1 + 1, alpha * rem, (r // 1 + 1) * 0.39, self.color(), self.fast_blur)
        painter.restore()
        if self._drawMain:
            painter.drawPixmap(offset, px, QtCore.QRect())
        painter.setWorldTransform(restore_transform)

    def boundingRectFor(self, rect):
        b = self.offset()
        return rect.adjusted(-b, -b, b, b)

    
def click_through(widget):
    try:
        widget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents) # python3
        hwnd = int(widget.winId())
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
    except Exception as e:
        print('falied to click_through', e)


def draw_shadow(painter, px, offset, r, alpha, shift=0.0, color=(0, 0, 0), fast_blur=None, trans=True):
    eff = QtGui.QGraphicsBlurEffect()
    if fast_blur is None:
        fast_blur = FAST_BLUR
    if fast_blur:
        eff.setBlurHints(QtGui.QGraphicsBlurEffect.BlurHints(1))
    eff.setBlurRadius(r)
    pixmap_blur = apply_effect_to_pixmap(px, eff, offset)
    if color is not None:
        painter_blur = QtGui.QPainter(pixmap_blur)
        painter_blur.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        color = QtGui.QColor(*color)
        painter_blur.fillRect(pixmap_blur.rect(), color)
        painter_blur.end()
    painter.setOpacity(alpha)
    painter.save()
    if not trans:
        offset = 0
    painter.translate(-offset * 2, -offset * 2 + shift)
    painter.drawPixmap(QtCore.QPointF(0, 0), pixmap_blur)
    painter.restore()
    painter.setOpacity(1.0)


def shadow(widget, r=3, color=(0, 0, 0), opacity=1.0, fast_blur=None):
    eff = Shadow(widget, fast_blur=fast_blur)
    eff.setRadius(r)
    eff.setColor(color)
    eff.setOpacity(opacity)
    widget.setGraphicsEffect(eff)

    
def isVisible(widget):
    try:
        return widget.isVisible()
    except Exception as e:
        return False


def update():
    t = clock()
    for parent, toasts in Toast.instances.items():
        for toast in toasts:
            try:
                toast.update(t)
            except Exception as e:
                print(print_error())
                toast.delete()


def boundingText(text_raw, font, max_width, max_line, ellipsis=u' \u2026'):
    metrics = QtGui.QFontMetricsF(font)
    text = u''
    i = 0
    n_line = 1
    text_line = u''
    w_max = 0
    rect = QtCore.QRectF()
    while i < len(text_raw):
        c = text_raw[i]
        if c == '\n':
            if n_line >= max_line:
                break
            text += u'\n'
            text_line = u''
            n_line += 1
            i += 1
            continue
        pred = compatstr(metrics.elidedText(text_line + text_raw[i:].split('\n')[0], QtCore.Qt.ElideRight, max_width)).replace(u'\u2026', '')[len(text_line):]
        if len(pred) > 1:
            text += pred
            text_line += pred
            i += len(pred)
            rect = metrics.boundingRect(text_line)
            w_max = max(w_max, rect.width())
            continue
        rect = metrics.boundingRect(text_line + c)
        if rect.width() <= max_width:
            text += c
            text_line += c
            i += 1
            w_max = max(w_max, rect.width())
        elif not text_line or n_line >= max_line:
            for i in range(len(text_line))[::-1]:
                text_ = text_line[:i] + ellipsis
                if metrics.boundingRect(text_).width() <= max_width:
                    break

            text = text[:len(text) + i - len(text_line)] + ellipsis
            break
        else:
            text += u'\n'
            text_line = u''
            n_line += 1
            continue

    rect = QtCore.QRect(0, 0, w_max, metrics.lineSpacing() * n_line)
    return (
     text, rect)


class Toast(QtGui.QWidget):
    instances = {}
    icon_cache = {}
    _soundName = {'info': 'SystemAsterisk', 
       'alert': 'SystemHand'}
    timer = None
    n_max = 16
    ellipsis = u' ...'
    virgin = True
    _posF = QtCore.QPointF(-1000, -1000)

    def __init__(self, parent, text, delay=3.0, icon='check', align='center', color='default', color_text='auto', color_icon='auto', shadow=SHADOW, sound='', max_width=256, max_line=4, clickable=False):
        if not icon and not text:
            return
        self.isReady = False
        self.parent = (parent, align)
        self.text = text
        self.delay = delay
        self.icon = icon
        self.align = align
        self.color = (24, 24, 24) if isinstance(color, str) and color.lower().strip() == 'default' else color
        self.color_text = color_text
        self.color_icon = color_icon
        self.shadow = shadow if not clickable else False
        self.sound = sound
        self.max_width = max_width
        self.max_line = max_line
        self.clickable = clickable
        self.t0 = None
        self.t = None
        if self.parent not in Toast.instances:
            Toast.instances[self.parent] = [
             self]
        else:
            toasts = Toast.instances[self.parent]
            if Toast.n_max:
                while len(toasts) >= Toast.n_max:
                    toasts[0].delete()

            toasts.append(self)
        if Toast.timer is None:
            Toast.timer = QtCore.QTimer()
            Toast.timer.timeout.connect(update)
            Toast.timer.start(1000 / FPS)

    def mousePressEvent(self, event):
        self.delete()

    def ready(self):
        if self.isReady:
            return
        self.isReady = True
        if self.parent[0].isVisible():
            parent = QtGui.QApplication.activeWindow()
        else:
            parent = None
        if parent is None:
            parent = self.parent[0]
        super(Toast, self).__init__(parent)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.DPI = DPI = float(dpi())
        self.offset = (0, 1 * DPI / 96) if self.shadow else (0, 0)
        self.r = R * self.DPI / 96
        self.r_blur = 6*1.5 if self.shadow else 0
        self.margin_tri = 6 * DPI // 96
        self.margin = max(self.r_blur * 3 * DPI // 96 + max(abs(self.offset[0]), abs(self.offset[1])), self.margin_tri)
        self.max_width = self.max_width * DPI // 96
        if isinstance(self.color, str) and self.color.lower() == 'random':
            self.color = [ randrange(256) for i in range(3) ]
            index = randrange(3)
        if isinstance(self.color_icon, str) and self.color_icon.lower() == 'random':
            self.color_icon = [ randrange(256) for i in range(3) ]
            index = randrange(3)
        L = (self.color[0] * 0.2126 + self.color[1] * 0.7152 + self.color[2] * 0.0722) / 255
        if L < 0.5:
            color_auto = [
             255, 255, 255]
        else:
            color_auto = [
             0, 0, 0]
        if isinstance(self.color_icon, str) and self.color_icon.lower().strip() == 'auto':
            self.color_icon = color_auto
        if isinstance(self.color_text, str) and self.color_text.lower().strip() == 'auto':
            self.color_text = color_auto
        if self.icon:
            self.icon_size = 20 * self.DPI // 96
            pixmap = getIcon(self.icon).pixmap
            pixmap = pixmap.scaled(self.icon_size, self.icon_size, QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
            if self.color_icon is not None:
                icon = (
                 self.icon, tuple(self.color_icon))
                if icon in self.icon_cache:
                    pixmap = self.icon_cache[icon]
                else:
                    img = convert(pixmap, 'img', alpha=True)
                    img = fill(img, self.color_icon)
                    pixmap = convert(img, 'pixmap', alpha=True)
                    self.icon_cache[icon] = pixmap
            self.icon = pixmap
        else:
            self.icon_size = 0
        self.move(-100000, -100000)
        self.adjustSize()
        self.hide()
        dx_init = 32 * DPI // 96
        dy_init = 32 * DPI // 96
        self.dx0 = 0
        self.dy0 = 0
        self.dx = 0
        self.dy = 0
        spacing = 5 * DPI // 96
        if self.align == 'center':
            self.dy0 = 0
            self.dy = self.dy0 + dy_init
        elif self.align == 'top':
            self.dy0 = self.margin - self.margin_tri - spacing
            self.dy = self.dy0 + dy_init
        elif self.align == 'bottom':
            self.dy0 = self.margin_tri - self.margin + spacing
            self.dy = self.dy0 - dy_init
        elif self.align == 'left':
            self.dx0 = self.margin - self.margin_tri - spacing
            self.dx = self.dx0 + dx_init
        elif self.align == 'right':
            self.dx0 = self.margin_tri - self.margin + spacing
            self.dx = self.dx0 - dx_init
        self.rotation = 0
        if self.clickable:
            self.setCursor(QtCore.Qt.PointingHandCursor)
        flag = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint
        self.setWindowFlags(flag)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor(*self.color))
        self.setPalette(p)
        if not self.clickable:
            click_through(self)

    @property
    def zoom(self):
        p = .95
        return p + (1-p)*(1-cos(pi*self._opacity))/2

    def resizeEvent(self, event=None):
        instances = dict(Toast.instances)
        parent = self.parent
        DPI = self.DPI
        margin = self.margin
        margin_tri = self.margin_tri
        try:
            index = instances[parent].index(self)
        except ValueError:
            print('deleted')
            return

        dx = self.dx0
        dy = self.dy0
        prev_toast = self
        for i in range(index + 1, len(instances[parent])):
            toast = instances[parent][i]
            if isVisible(toast):
                if self.align == 'center':
                    dy -= ((toast.height() + prev_toast.height()) / 2 - prev_toast.margin - toast.margin + margin_tri + 1 * self.DPI // 96) * toast.zoom
                elif self.align == 'top':
                    dy -= (toast.height() - 2 * toast.margin + margin_tri + 1 * self.DPI // 96) * toast.zoom
                elif self.align == 'bottom':
                    dy += (toast.height() - 2 * toast.margin + margin_tri + 1 * self.DPI // 96) * toast.zoom
                elif self.align == 'left':
                    dx -= (toast.width() - 2 * toast.margin + margin_tri + 1 * self.DPI // 96) * toast.zoom
                elif self.align == 'right':
                    dx += (toast.width() - 2 * toast.margin + margin_tri + 1 * self.DPI // 96) * toast.zoom
                prev_toast = toast

        if self.align in ['center', 'top']:
            dy += (self.height() - self.margin * 2 - margin_tri + 1 * self.DPI // 96) * (1 - self.zoom)
        elif self.align in ['bottom']:
            dy -= (self.height() - self.margin * 2 - margin_tri + 1 * self.DPI // 96) * (1 - self.zoom)
        elif self.align in ['left']:
            dx += (self.width() - self.margin * 2 - margin_tri + 1 * self.DPI // 96) * (1 - self.zoom)
        elif self.align in ['right']:
            dx -= (self.width() - self.margin * 2 - margin_tri + 1 * self.DPI // 96) * (1 - self.zoom)
        else:
            raise NotImplementedError('Align {}'.format(self.align))

        p = 0.0008 ** (self.dt * SPEED)
        self.dx = self.dx * p + dx * (1 - p)
        self.dy = self.dy * p + dy * (1 - p)
        w, h = self.width(), self.height()
        pos = parent[0].mapToGlobal(QtCore.QPoint(0, 0))
        if self.align == 'left':
            x = pos.x() - w + self.dx
            y = pos.y() + parent[0].height() // 2 - h // 2
        elif self.align == 'right':
            x = pos.x() + parent[0].width() + self.dx
            y = pos.y() + parent[0].height() // 2 - h // 2
        else:
            x = pos.x() + parent[0].width() // 2 - w // 2
        if self.align == 'center':
            y = pos.y() + parent[0].height() // 2 - h // 2 + self.dy
        elif self.align == 'top':
            y = pos.y() - h + self.dy
        elif self.align == 'bottom':
            y = pos.y() + parent[0].height() + self.dy
        posF_prev = self._posF
        if not AA:
            x = int(x)
            y = int(y)
        self._posF = QtCore.QPointF(x, y)
        dp = posF_prev - self._posF
        if hypot(dp.x(), dp.y()) > .001:
            self._posF_prev = posF_prev
            self.move(int(x), int(y))
            self.repaint()

    def opacity(self, p):
        mid = 0.9
        if p < mid:
            opacity = min((1 - exp(-p / 0.1)) / (1 - exp(-1)), 1)
        elif self.clickable:
            opacity = 1
        else:
            opacity = 1 / (1 - mid) * (1 - p)
        self._opacity = opacity * 0.9 * opacity_max
        return self._opacity

    def update(self, t):
        self.ready()
        if self.parent[0].isVisible():
            if self.t0 is None:
                self.t = self.t0 = t
            self.dt = t - self.t
            self.t = t
            p = min((t - self.t0) / (self.delay / SPEED), 1)
            opacity = self.opacity(p)
            self.setWindowOpacity(opacity)
            self.resizeEvent()
            if not self.isVisible():
                if self.sound and self.virgin:
                    sound = self._soundName[self.sound]
                    winsound.PlaySound(sound, winsound.SND_ALIAS | winsound.SND_ASYNC)
                self.virgin = False
                self.show()
                self.adjustSize()
                self.resizeEvent()
            if not self.clickable and p >= 1:
                self.delete()
        else:
            self.t0 = None
            self.hide()
        return

    def delete(self):
        try:
            Toast.instances[self.parent].remove(self)
            if self.isReady:
                self.hide()
                self.deleteLater()
        except Exception as e:
            print(e)

    def adjustSize(self):
        margin = self.margin
        self.border = 7 * self.DPI // 96
        self.space = 5 * self.DPI // 96
        text, rect = boundingText(self.text, self.font(), self.max_width, self.max_line, self.ellipsis)
        if text:
            space = self.space + 2 * self.DPI // 96
        else:
            space = 0
        self.text = text
        self.rect = rect
        self.resize(rect.width() + margin * 2 + self.border * 2 + self.icon_size + space, max(rect.height() + margin * 2 + self.border * 2, self.r * 3))

    _pixmap = None

    def pixmap(self):
        size = self.size()
        if self._pixmap is not None and size == self._pixmap.size():
            return self._pixmap
        else:
            pixmap = QtGui.QPixmap(size.width(), size.height())
            pixmap.fill(QtCore.Qt.transparent)
            self.paint(QtGui.QPainter(pixmap))
            eff = Shadow(dpi=dpi())
            eff.setRadius(self.r_blur)
            eff.setColor((0, 0, 0))
            pixmap = apply_effect_to_pixmap(pixmap, eff)
            self._pixmap = pixmap
            return pixmap

    def paintEvent(self, event=None):
        pixmap = self.pixmap()
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing | QtGui.QPainter.HighQualityAntialiasing | QtGui.QPainter.NonCosmeticDefaultPen)
        w, h = self.width(), self.height()
        wp, hp = pixmap.width(), pixmap.height()
        rx, ry = self._posF.x() % 1, self._posF.y() % 1
        zoom = self.zoom
        painter.drawPixmap(QtCore.QRectF(rx+w/2*(1-zoom), ry+h/2*(1-zoom), w*zoom, h*zoom), pixmap, QtCore.QRectF(0, 0, w, h - 1e-08))

    def paint(self, painter):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect
        w, h = self.width(), self.height()
        margin = self.margin
        if self.rotation:
            painter.translate(w // 2, h // 2)
            painter.rotate(self.rotation)
            painter.translate(-w // 2, -h // 2)
        self.draw(painter, self.palette().color(QtGui.QPalette.Background))
        painter.setPen(QtGui.QColor(*self.color_text))
        painter.setFont(self.font())
        pos = QtCore.QPoint(margin + self.icon_size + self.space - rect.left() + self.border, margin - rect.top() + self.border)
        w_more = 16 * self.DPI // 96
        rect = QtCore.QRect(margin + self.border + self.icon_size + self.space - w_more, h // 2 - rect.height() // 2, rect.width() + w_more * 2, rect.height())
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text)
        if self.icon:
            painter.drawPixmap(QtCore.QPointF(margin + self.border, h // 2 - self.icon_size // 2), self.icon)

    def draw(self, painter, color, triangle=True):
        margin = self.margin
        margin_tri = self.margin_tri
        r = self.r
        w, h = self.width(), self.height()
        painter.setPen(QtCore.Qt.NoPen)
        if DEBUG:
            painter.setBrush(QtGui.QColor(255, 0, 255))
            painter.drawRect(0, 0, w, h)
        painter.setBrush(color)
        painter.drawRoundedRect(margin, margin, w - margin * 2, h - margin * 2, r, r)
        if triangle:
            color = self.palette().color(QtGui.QPalette.Background)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)
            r = margin_tri
            ratio = 1.4
            w_t = r / 1.7320508075688772 * ratio
            margin_more = margin + 1
            w_t = w_t * margin_more // margin
            path = None
            if self.align == 'top':
                path = QtGui.QPainterPath()
                path.moveTo(w // 2, h - (margin - r))
                path.lineTo(w // 2 - w_t, h - margin_more)
                path.lineTo(w // 2 + w_t, h - margin_more)
                path.lineTo(w // 2, h - (margin - r))
            elif self.align == 'bottom':
                path = QtGui.QPainterPath()
                path.moveTo(w // 2, margin - r)
                path.lineTo(w // 2 - w_t, margin_more)
                path.lineTo(w // 2 + w_t, margin_more)
                path.lineTo(w // 2, margin - r)
            elif self.align == 'left':
                path = QtGui.QPainterPath()
                path.moveTo(w - (margin - r), h // 2)
                path.lineTo(w - margin_more, h // 2 - w_t)
                path.lineTo(w - margin_more, h // 2 + w_t)
                path.lineTo(w - (margin - r), h // 2)
            elif self.align == 'right':
                path = QtGui.QPainterPath()
                path.moveTo(margin - r, h // 2)
                path.lineTo(margin_more, h // 2 - w_t)
                path.lineTo(margin_more, h // 2 + w_t)
                path.lineTo(margin - r, h // 2)
            if path is not None:
                painter.fillPath(path, painter.brush())
        return

    
class LazyTimer(object):

    def __init__(self, parent, timeout, immortal=False):
        self.parent = parent
        self.timeout = timeout
        self.timer = None
        self.immortal = immortal
        if immortal:
            self.timer = QtCore.QTimer(parent)
            self.timer.timeout.connect(timeout)

    def isActive(self):
        try:
            return self.timer.isActive()
        except:
            return False

    def setInterval(self, delay):
        self.delay = delay
        if self.timer is not None:
            self.timer.setInterval(delay)

    def start(self, delay=None, emit=False):
        if self.timer is not None:
            if not self.isActive():
                self.timer.start()
            return
        self.timer = QtCore.QTimer(self.parent)
        self.timer.timeout.connect(self.timeout)
        if delay is None:
            delay = self.delay
        self.timer.setInterval(delay)
        if not self.isActive():
            self.timer.start(delay)
        if emit:
            self.timer.timeout.emit()

    def stop(self):
        if self.timer is not None:
            self.timer.stop()

    def deleteLater(self):
        if self.timer is not None:
            if self.immortal:
                self.timer.stop()
            else:
                timer = self.timer
                self.timer = None
                timer.stop()
                timer.deleteLater()



QSlider = QtGui.QSlider

class MySlider(QSlider):

    def __init__(self, *args, **kwargs):
        super(MySlider, self).__init__(*args, **kwargs)
        self.COLOR_BASE = (220, 220, 220)
        self.dpi = dpi()
        self.SPACING = 5 * self.dpi / 96
        self.SHIFT = int(1 * self.dpi / 96)
        self.clicks = []
        self.isIn = False
        self.isPress = False
        self.isMoved = False
        self.pos0 = QtCore.QPoint(0, 0)
        self.h_anim = 0
        self.pr_anim = 0
        self.t0_anim = None
        self.timer = LazyTimer(None, self.timeout)
        self.timer.setInterval(1000 / FPS)
        self.timeout()
        self.setMouseTracking(True)
        self.setMinimumHeight(max(HEIGHT, R_HANDLE * 2, R_HANDLE_PRESS * 2) * self.dpi / 96 + 2)

    def timeout(self):
        try:
            h0 = self.h_anim
            h_new = int(self.isIn)
            pr0 = self.pr_anim
            pr_new = int(self.isPress)
            t0 = self.t0_anim
            if t0 is None:
                t0 = clock()
            self.t0_anim = t = clock()
            dt = t - t0
            _k_hl = k_hl ** (10 * dt * SPEED)
            _k_pr = k_pr ** (10 * dt * SPEED)
            if abs(h0 - h_new) < 0.001:
                self.h_anim = h_new
            else:
                self.h_anim = h0 * _k_hl + h_new * (1 - _k_hl)
            if abs(pr0 - pr_new) < 0.001:
                self.pr_anim = pr_new
            else:
                self.pr_anim = pr0 * _k_pr + pr_new * (1 - _k_pr)
            if h0 != h_new or pr0 != pr_new or self.clicks:
                self.repaint()
            else:
                self.t0_anim = None
                self.timer.deleteLater()
        except Exception as e:
            print(e)
            self.timer.deleteLater()

        return

    @property
    def COLOR_ON(self):
        return COLOR['main']

    @property
    def R_HANDLE(self):
        return R_HANDLE * self.dpi / 96

    @property
    def R_HANDLE_PRESS(self):
        return R_HANDLE_PRESS * self.dpi / 96

    @property
    def R_HANDLE_MAX(self):
        return max(R_HANDLE, R_HANDLE_PRESS) * self.dpi / 96

    def _update(self):
        self.timeout()
        self.timer.start()

    def enterEvent(self, event):
        self.isIn = True
        self._update()

    def leaveEvent(self, event):
        self.isIn = False
        self._update()

    def mousePressEvent(self, event):
        if event.button() == 1:
            self.isPress = True
            self.mouseMoveEvent(event)
            self._update()

    def mouseMoveEvent(self, event):
        if self.isPress:
            r_handle = self.R_HANDLE
            x = event.pos().x()
            w = self.width() - 1
            p = float(x - r_handle) / (w - r_handle * 2)
            min_ = self.minimum()
            max_ = self.maximum()
            value = min_ + (max_ - min_) * p
            value = min(max(min_, int(value + 0.5)), max_)
            self.setValue(value)

    def mouseReleaseEvent(self, event):
        self.isPress = False
        self._update()

    def setValue(self, value):
        self._setValue(value)

    def _setValue(self, value, repaint=True):
        QSlider.setValue(self, value)
        if ALPHA_HL and self.minimum() < value < self.maximum() or self.minimum() == 0 and self.maximum() == 0:
            if not self.timer.isActive():
                self.timer.start(1000 / FPS, emit=True)
        elif repaint:
            self.repaint()

    def setMaximum(self, value):
        QSlider.setMaximum(self, value)
        self._setValue(self.value(), repaint=False)

    def setRange(self, min, max):
        QSlider.setRange(self, min, max)
        self.setValue(self.value())

    @property
    def COLOR_HL(self):
        return QtGui.QColor(*self.COLOR_ON).lighter(110).getRgb()

    @property
    def COLOR_PRESS(self):
        return QtGui.QColor(*self.COLOR_ON).darker(130).getRgb()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        h_ = self.h_anim
        pr = self.pr_anim
        h = min(self.height(), HEIGHT * self.dpi / 96)
        h -= h % 2
        r = h * 0.5
        r_handle = self.R_HANDLE * (1 - pr) + self.R_HANDLE_PRESS * pr
        if DEBUG:
            brush = QtGui.QBrush(QtGui.QColor(255, 0, 255), style=QtCore.Qt.SolidPattern)
            painter.fillRect(self.rect(), brush)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.isEnabled():
            color = QtGui.QColor(*self.COLOR_BASE)
        else:
            color = QtGui.QColor(*COLOR['disable'])
        brush = QtGui.QBrush(color, style=QtCore.Qt.SolidPattern)
        path = QtGui.QPainterPath()
        rect = QtCore.QRectF(self.R_HANDLE_MAX, self.height() / 2 - h / 2, self.width() - self.R_HANDLE_MAX * 2, h)
        path.addRoundedRect(rect, r, r)
        painter.setClipPath(path)
        painter.fillRect(QtCore.QRectF(0, 0, self.width(), self.height()), brush)
        w = (self.width() - self.R_HANDLE_MAX * 2) * (self.value() - self.minimum()) / max(self.maximum() - self.minimum(), 1)
        brush = None
        if self.isEnabled():
            color = mix(self.COLOR_ON, self.COLOR_HL, h_)
            color = mix(color, self.COLOR_PRESS, pr)
            color_handle = QtGui.QColor(*color)
            color = QtGui.QColor(*self.COLOR_ON)
        else:
            color = QtGui.QColor(*COLOR['disable'])
            color_handle = color
        if brush is None:
            brush = QtGui.QBrush(color, style=QtCore.Qt.SolidPattern)
        rx = 200 * r / max(w, 1)
        ry = 200 * r / max(h, 1)
        painter.fillRect(QtCore.QRectF(0, 0, self.R_HANDLE_MAX + w, self.height()), brush)
        x = self.R_HANDLE_MAX + w
        y = self.height() / 2
        brush = QtGui.QBrush(color_handle, style=QtCore.Qt.SolidPattern)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(x - r_handle, y - r_handle, 2 * r_handle, 2 * r_handle), r_handle, r_handle)
        painter.setClipPath(path)
        painter.fillRect(QtCore.QRectF(0, 0, self.width(), self.height()), brush)
        return

QtGui.QSlider = MySlider


class ExtendedQAction(QtGui.QWidgetAction):
    instances = []

    def __init__(self, label, action, parent=None, *args, **kw):
        super(ExtendedQAction, self).__init__(parent, *args, **kw)
        self.instances.append(self)
        self.myWidget = myWidget = QtGui.QWidget()
        myWidget.setObjectName('_')
        layout = QtGui.QHBoxLayout()
        dpi_ = dpi()
        layout.setContentsMargins(35 * dpi_ / 96, 2 * dpi_ / 96, 13 * dpi_ / 96, 2 * dpi_ / 96)
        myWidget.setLayout(layout)
        self.label = label = QtGui.QLabel(label)
        self.slider = slider = QtGui.QSlider()
        layout.addWidget(label)
        layout.addWidget(slider)
        self.updatePalette()
        myWidget.mouseReleaseEvent = nothing
        slider.valueChanged.connect(action)
        self.setDefaultWidget(myWidget)
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setTickPosition(QtGui.QSlider.TicksBothSides)
        slider.setTickInterval(25)
        slider.setPageStep(25)

    def updatePalette(self):
        color = QtGui.QColor(*COLOR['main'])
        color.setAlpha(64)
        color = color.getRgb()
        self.myWidget.setStyleSheet(('QWidget:hover#_ { background:rgb{color};} QWidget#_ { padding: 4px; margin:0px}').replace('{color}', str(color)))



class MyMessageBox(QtGui.QMessageBox):

    def __init__(self, parent, width = None):
        super(MyMessageBox, self).__init__(parent)
        self._width = width
        #self.setSizeGripEnabled(True)

    def event(self, e):
        result = super(MyMessageBox, self).event(e)
        if self._width is not None:
            dpi_ = dpi()
            self.setMinimumWidth(self._width * dpi_ / 96)
            self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        return result

    
def getIcon(name, force=False, color=None, size=None):
    name_org = name
    if color:
        name += ('_{}').format(color)
    if size is not None:
        size = int(size)
        name += ('_{}').format(size)
    icon = ICONS.get(name)
    if icon is None or force:
        if name_org in ICONS:
            pixmap = ICONS[name_org].pixmap
        else:
            if not name_org.startswith(':'):
                filename = u':/icons/{}'.format(name_org)
            else:
                filename = name_org
            pixmap = QtGui.QPixmap(filename)
            
        if pixmap.isNull():
            icon = QtGui.QIcon()
            icon.pixmap = pixmap
            return icon
            
        if size is not None:
            pixmap = pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
        if color:
            try:
                img = convert(pixmap, 'img', alpha=True)
                img = fill(img, color)
                pixmap = convert(img, 'pixmap', alpha=True)
            except Exception as e:
                print(e)

        icon = QtGui.QIcon(pixmap)
        icon.pixmap = pixmap
        ICONS[name] = icon
    return icon


def fill(img, color):
    color = tuple(color)
    if len(color) == 4:
        a = color[(-1)]
        color = color[:3]
    else:
        a = 255
    dst = Image.new(img.mode, img.size, color + (0, ))
    draw = ImageDraw.Draw(dst, 'RGBA')
    draw.bitmap([0, 0], img, fill=color)
    if a < 255:
        alpha = dst.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(a / 255.0)
        dst.putalpha(alpha)
    return dst


def print_error(e):
    return traceback.format_exc()


def QPixmap(fileName, alpha=False, size=None):
    tmp_files = []
    try:
        return QPixmap_(fileName, alpha, size)
    except Exception as e:
        print('QPixmap error', print_error(e))
        return QtGui.QPixmap()


def QPixmap_(fileName, alpha=False, size=None, oversize=True):
    if callable(fileName):
        fileName = fileName()
    if isinstance(fileName, QtGui.QPixmap):
        if size is not None and size[0] != fileName.width() and size[1] != fileName.height():
            fileName = fileName.scaled(size[0], size[1], QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
        return fileName
    
    fileName = compatstr(fileName)

    img = Image.open(fileName)
    if img.palette is not None:
        img = img.convert('RGBA')
    if size is not None:
        img.draft(None, size)#
        w0, h0 = img.size
        w, h = size
        if float(w0) / h0 > float(w) / h:
            size = (
             w, float(w) * h0 / w0)
        else:
            size = (
             float(h) * w0 / h0, h)
        size = (
         int(math.ceil(size[0])), int(math.ceil(size[1])))
        if oversize or size[0] * size[1] < w0 * h0:
            if size[0] * size[1] > w0 * h0:
                img = img.resize(size, resample=Image.NEAREST)
            else:
                img = img.resize(size, resample=Image.ANTIALIAS)
    pixmap = convert(img, 'pixmap', alpha)
    img.close()
    del img
    return pixmap


class Loader(QtCore.QObject):
    instance = None

    def __init__(self, parent=None):
        super(Loader, self).__init__(parent)

    @classmethod
    def init(cls):
        cls.instance = cls()

    def loadFromData(self, data, format=None, size=None, alpha=None, swap=False):
        format = QtGui.QImage.Format_ARGB32 if alpha else QtGui.QImage.Format_RGB888
        qimg = QtGui.QImage(data, size[0], size[1], format)
        if swap:
            qimg = qimg.rgbSwapped()
        try:
            pixmap = QtGui.QPixmap.fromImage(qimg)
        except Exception as e:
            print(e)
            pixmap = QtGui.QPixmap()
        return pixmap


def convert(src, to, alpha=False):
    if isinstance(src, Image.Image) and to == 'pixmap':
        alpha = True
        if alpha:
            src = src.convert('RGBA')
            data = src.tobytes('raw', 'RGBA')
        else:
            src = src.convert('RGB')
            data = src.tobytes('raw', 'RGB')
        pixmap = Loader.instance.loadFromData(data, size=src.size, alpha=alpha, swap=True)
        return pixmap
    if isinstance(src, QtGui.QPixmap) and to == 'img':
        format = 'PNG' if alpha else 'BMP'
        bytes = QtCore.QByteArray()
        buffer = QtCore.QBuffer(bytes)
        buffer.open(QtCore.QIODevice.WriteOnly)
        src.save(buffer, format)
        data = bytes.data()
        f = IO(data)
        #f.seek(0)
        img = Image.open(f)
        return img
    raise NotImplementedError(u'The conversion from {} to <{}> is not supported'.format(type(src), to))


def mix(color, color2, p, power=True):
    if len(color) == 3:
        color = color + (255, )
    if len(color2) == 3:
        color2 = color2 + (255, )
    color_mix = []
    for c, c2 in zip(color, color2):
        if power:
            c_res = ((c / 255.0) ** 2 * (1 - p) + (c2 / 255.0) ** 2 * p) ** 0.5 * 255
        else:
            c_res = (c / 255.0 * (1 - p) + c2 / 255.0 * p) * 255
        color_mix.append(c_res)

    return tuple(color_mix)



def apply(app, dpi=None):
    if dpi is None:
        dpi = app.desktop().logicalDpiX()
    ss = '''
QMenuBar {
    background-color: palette(base);
}
QMenuBar::item {
    background-color: palette(base);
}
QMenuBar::item:selected {
    background-color: @@@;
}
QMenuBar::item:pressed {
    background-color: palette(highlight);
    color: white;
}
QMenu {
    background-color: palette(base);
    border-style: solid;
    border-width: 1px;
    border-color: @BORDERCOLOR;/*palette(highlight);*/
    padding: {0}px 0px;
}

QMenu::item {
    background-color: transparent;
    padding: 0px {3}px 0px {2}px; /* top, right, bottom, left */
    min-height: {1}px;
}

QMenu::item:selected {
    background-color: @@@;
}

QMenu::icon{
    margin: 0px 0px 0px {3}px;
}

QMenu::separator {
    background-color: @SEPERATOR;
    height: 1px;
    margin: {4}px 1px {4}px 1px;
}

QMenu::indicator {
    width: {7}px;
    height: {7}px;
    margin: 0px 0px 0px {6}px;
    padding: 0px 0px 0px -{8}px;
}

QMenu::indicator:exclusive:checked {
    image: url(:/icons/radiobox);
}

QMenu::indicator:exclusive {
    image: url(:/icons/radiobox_blank);
}

QMenu::indicator:checked {
    image: url(:/icons/checkbox);
}

QMenu::indicator {
    image: url(:/icons/checkbox_blank);
}

QMenu::right-arrow {
    width: {7}px;
    height: {7}px;
    image: url(:/icons/next);
}

QPushButton,QToolButton,QComboBox,QDateTimeEdit{color:black}
QPushButton:disabled,QToolButton:disabled,QComboBox:disabled,QDateTimeEdit:disabled{color:gray}

QTabWidget::pane{
    border: 1px solid @BORDERCOLOR;
    margin-top: -1px;
}
QTabBar::tab{
    background-color:palette(base);
    padding: {4} {9} {4} {9};
    border: 1px solid @BORDERCOLOR;
    margin: 0px 0px 0px -1px;
}
QTabBar::tab:first, QTabBar::tab:only-one{
    margin-left: 0px;
}
QTabBar::tab:selected{background-color:palette(highlight);color:white;}
QTabBar::tab:hover:!selected{background-color:@@@;}
QTabWidget>QWidget>QWidget{background-color:palette(base);}

QHeaderView:enabled{color:black}
QHeaderView:disabled{color:gray}

QLineEdit {
    border: 1px solid @BORDERCOLOR2;
}
QLineEdit:focus {
    border: 1px solid palette(highlight);
}
QLineEdit:hover:!focus {
    border-color: $$$;
}

QDoubleSpinBox {
    border: 1px solid @BORDERCOLOR2;
}
QDoubleSpinBox:focus {
    border: 1px solid palette(highlight);
}
QDoubleSpinBox:hover:!focus {
    border-color: $$$;
}
QDoubleSpinBox::up-button {
    width: 0px;
}QDoubleSpinBox::down-button {
    width: 0px;
}
'''.replace('{0}', str(3 * dpi // 96))\
.replace('{1}', str(23 * dpi // 96))\
.replace('{2}', str(15 * dpi // 96))\
.replace('{3}', str(13 * dpi / 96))\
.replace('{4}', str(5 * dpi // 96))\
.replace('{5}', str(20 * dpi // 96))\
.replace('{6}', str(9 * dpi // 96))\
.replace('{7}', str(16 * dpi // 96))\
.replace('{8}', str(5 * dpi // 96))\
.replace('{9}', str(10 * dpi // 96))
    color = QtGui.QColor(*COLOR['main'])
    color.setAlpha(64)
    color = color.getRgb()

    border_color = (76,77,80) if DARKMODE else (163,163,163)
    color_hl_half = mix(border_color, app.palette().highlight().color().getRgb()[:3], .5, False)
    
    ss = ss.replace('@BORDERCOLOR2', 'rgb{}'.format(border_color))
    ss = ss.replace('@BORDERCOLOR', 'rgb(60,64,67)' if DARKMODE else 'rgb(186,186,186)')
    ss = ss.replace('@SEPERATOR', 'rgb(60,64,67)' if DARKMODE else 'rgb(233,233,233)')
    ss = ss.replace('@@@', 'rgba{}'.format(color))
    ss = ss.replace('$$$', 'rgb{}'.format(color_hl_half))
    
    if DARKMODE:
        ss = ss.replace(':/icons/', ':/icons/dark_')
        ss = ss.replace(':/icons/dark_next', ':/icons/next_white')
    app.setStyleSheet(ss)

    
def compatstr(s):
    if isinstance(s, bool):
        s = str(s)
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        return s.decode('utf8')
    return s.toUtf8().decode('utf8')


def draggable(window, target=None):
    if target is None:
        target = window
    try:
        window.menuClicked = False
        def mousePressEvent(self, event):
            type(self).mousePressEvent(self, event)
            #print(event.spontaneous())
            parentWindow = self
            while parentWindow is not None:
                if isinstance(parentWindow, QtGui.QDockWidget):
                    break
                parentWindow = parentWindow.parent()
            if target.isMaximized() or target.isFullScreen() or self.menuClicked or (parentWindow is not None and parentWindow.isFloating()):
                self.menuClicked = False
                return
            if event.button() == 1:
                self.pos0 = event.pos()
                self.push = True

        def mouseMoveEvent(self, event):
            type(self).mouseMoveEvent(self, event)
            #print(self.push)
            try:
                if not self.push:
                    return
                pos = event.pos()
                dpos = pos - self.pos0
                pos = target.pos() + dpos
                target.move(pos)
            except Exception as e:
                print(e)

        def mouseReleaseEvent(self, event):
            #print('release')
            self.push = False
            self.menuClicked = False
            type(self).mouseReleaseEvent(self, event)

        window.push = False
        window.mousePressEvent = types.MethodType(mousePressEvent, window)
        window.mouseMoveEvent = types.MethodType(mouseMoveEvent, window)
        window.mouseReleaseEvent = types.MethodType(mouseReleaseEvent, window)
        if isinstance(window, QtGui.QMenuBar):
            for menu in window.findChildren(QtGui.QMenu):
                #print(menu)
                def aboutToShow():
                    #print('aboutToShow')
                    window.menuClicked = True
                menu.aboutToShow.connect(aboutToShow)
    except Exception as e:
        print(e)

        
def cleanCache():
    while len(CACHE) > CACHE_SIZE:
        CACHE.popitem(False)


def request(filename):
    filename = os.path.realpath(filename)
    pixmap = CACHE.get(filename, None)
    if pixmap:
        return pixmap
    size = QtGui.QApplication.desktop().size()
    size = size.width(), size.height()
    pixmap = QPixmap(filename, True, size=size)
    #print('read pixmap:', filename)
    CACHE[filename] = pixmap
    cleanCache()
    return pixmap


def dpi():
    global DPI
    if DPI is None:
        DPI = QtGui.QApplication.desktop().logicalDpiX()
    return DPI


class Lock(object):
    _lock = False

    def lock(self):
        if self._lock:
            raise Exception('locked')
        self._lock = True

    def unlock(self):
        self._lock = False

    def __enter__(self):
        self.lock()
    
    def __exit__(self, type, value, traceback):
        self.unlock()


class Overlay(QtGui.QWidget):

    def __init__(self, parent):
        self._parent = parent
        super(Overlay, self).__init__(parent)
        self.dpi = dpi()
        self.move(0,0)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        
        if self._parent._slideshow:
            rt = self._parent._rt_pause if self._parent._pause_slideshow else self._parent._t_slideshow + self._parent._delay_slideshow - time()
            rt = max(1, rt)
            text = '{:02} : {:02}'.format(int(rt//60), int(math.ceil(rt%60)))
            aa = 4
            bb = 2
            margin = 16 * self.dpi / 96
            font = self.font()
            font.setPointSizeF((w*h)**.5*.05*aa)
            m = QtGui.QFontMetricsF(font)
            rect = m.boundingRect(text)
            pixmap = QtGui.QPixmap(math.ceil(rect.width()+margin*2*aa), math.ceil(rect.height()+margin*2*aa))
            pixmap.fill(QtCore.Qt.transparent)
            painter_text = QtGui.QPainter(pixmap)
            painter_text.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
            painter_text.setPen(QtGui.QPen(QtGui.QColor('white')))
            painter_text.setFont(font)
            rect_src = QtCore.QRectF(0,0,pixmap.width(),pixmap.height())
            painter_text.drawText(rect_src, QtCore.Qt.AlignCenter, text)
            painter_text.end()
            pixmap = pixmap.scaled(math.ceil(pixmap.width()/aa*bb), math.ceil(pixmap.height()/aa*bb), QtCore.Qt.KeepAspectRatio, transformMode=QtCore.Qt.SmoothTransformation)
            rect = QtCore.QRectF(0,0,w,rect.height()/aa)
            painter.fillRect(rect, QtGui.QColor(0,0,0,64))
            rect_src = QtCore.QRectF(0,0,pixmap.width(), pixmap.height())
            rect_dst = QtCore.QRectF(rect.width()/2-pixmap.width()/2/bb, rect.height()/2-pixmap.height()/2/bb, pixmap.width()/bb, pixmap.height()/bb)
            painter.drawPixmap(rect_dst, pixmap, rect_src)


def shortName(long_name):
    if long_name.startswith('\\\\?\\'):
        long_name = long_name.replace('\\\\?\\', '', 1)
    return win32api.GetShortPathName(long_name)
        

class MainWidget(QtGui.QMainWindow):
    _currentFolder = None
    _filenames = []
    _index = 0
    _flipH = False
    _flipV = False
    _wheelStep = 100
    _wheelDelta = 0
    _subfolder = True
    _slideshow = False
    _delay_slideshow = 10
    _pause_slideshow = False
    _scale = 1.0
    _rotate = 0.0
    _aa = True
    _top = False

    def __init__(self, parent=None):
        super(MainWidget, self).__init__(parent)
        self.lock_filenames = Lock()
        self._overlay = Overlay(self)
        self._timer_slideshow = QtCore.QTimer()
        self._timer_slideshow.setInterval(100)
        self._timer_slideshow.timeout.connect(self._timeout_slideshow)
        dpi()#
        draggable(self)
        self.setAcceptDrops(True)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self).activated.connect(self.prev)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Up), self).activated.connect(self.prev)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_PageUp), self).activated.connect(self.prev)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self).activated.connect(self.next)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Down), self).activated.connect(self.next)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_PageDown), self).activated.connect(self.next)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self).activated.connect(self.next)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Home), self).activated.connect(self.first)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_End), self).activated.connect(self.last)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_M), self).activated.connect(self.flipH)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_F), self).activated.connect(self.flipV)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_O), self).activated.connect(self.openCurrentImage)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_Return), self).activated.connect(self.openCurrentImageLocation)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete), self).activated.connect(lambda: self.deleteCurrentImage(False))
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ShiftModifier | QtCore.Qt.Key_Delete), self).activated.connect(lambda: self.deleteCurrentImage(True))
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_O), self).activated.connect(self.selectCurrentFolder)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_F1), self).activated.connect(self.about)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Return), self).activated.connect(self.changeWindowState)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_P), self).activated.connect(self.togglePauseSlideshow)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Plus), self).activated.connect(self.scaleUp)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Minus), self).activated.connect(self.scaleDown)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Asterisk), self).activated.connect(self.scaleReset)
        QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_A), self).activated.connect(self.toggleTop)
        self.first()

    def toggleTop(self):
        self.setTop(not self._top)

    def setTop(self, flag):
        self._top = flag
        SetWindowPos(self.winId(), win32con.HWND_TOPMOST if flag else win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        Toast(self, 'Always on top ' + ('ON' if flag else 'OFF'), icon='top' if flag else 'top_off')

    def dragEnterEvent(self, event):
        print('dragEnter')
        folders = []
        files = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = compatstr(url.toLocalFile())
                if os.path.isdir(path):
                    folders.append(path)
                else:
                    files.append(path)
        if folders or files:
            event.accept()

    def dropEvent(self, event):
        folders = []
        files = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = compatstr(url.toLocalFile())
                if os.path.isdir(path):
                    folders.append(path)
                else:
                    files.append(path)
        if folders or files:
            self.setCurrentFolders(folders, files)

    def scaleUp(self):
        scale = min(self._scale * 1.2, 1.2**20)
        if abs(scale - 1) < .001:
            scale = 1.0
        self._scale = scale
        self.update()

    def scaleDown(self):
        scale = max(self._scale / 1.2, 1/1.2**20)
        if abs(scale - 1) < .001:
            scale = 1.0
        self._scale = scale
        self.update()

    def scaleReset(self):
        self._scale = 1.0
        self.update()

    def update(self):
        self.updateTitle()
        super(MainWidget, self).update()

    def updateTitle(self):
        text = '{}    [{} / {}]'.format(TITLE, self.index()+1, len(self.filenames()))
        if self._pause_slideshow:
            text += '    [PAUSED]'
        if self._scale != 1.0:
            text += '    {:.01f}%'.format(int(self._scale*1000+.5)/10)
        self.setWindowTitle(text)

    def togglePauseSlideshow(self):
        if not self._slideshow:
            return
        if self._pause_slideshow:
            self.resumeSlideshow()
        else:
            self.pauseSlideshow()

    def _timeout_slideshow(self):
        t = time()
        rt = self._t_slideshow + self._delay_slideshow - t
        if rt < 0 :
            self._t_slideshow = t
            self.next()
        self._overlay.update()

    def startSlideshow(self):
        delay, ok = QtGui.QInputDialog.getDouble(self, 'Slideshow', 'Interval (sec):', self._delay_slideshow)
        if not ok:
            return
        if delay <= 0:
            msg = MyMessageBox(self)
            msg.setIcon(QtGui.QMessageBox.Warning)
            msg.setWindowTitle(u'Error')
            msg.setText('Invalid interval')
            msg.exec_()
            return self.startSlideshow()
        self._delay_slideshow = delay
        self._t_slideshow = time()
        self._slideshow = True
        self._timer_slideshow.start()
        self.update()

    def stopSlideshow(self):
        self._slideshow = False
        self._pause_slideshow = False
        self._timer_slideshow.stop()
        self.update()

    def pauseSlideshow(self):
        self._rt_pause = self._t_slideshow + self._delay_slideshow - time()
        self._pause_slideshow = True
        self._timer_slideshow.stop()
        self.update()

    def resumeSlideshow(self):
        self._t_slideshow = self._rt_pause - self._delay_slideshow + time()
        self._pause_slideshow = False
        self._timer_slideshow.start()
        self.update()

    def changeWindowState(self):
        if self.isMaximized():
            self.setWindowState(QtCore.Qt.WindowNoState)
        else:
            self.setWindowState(QtCore.Qt.WindowMaximized)

    def mouseDoubleClickEvent(self, event):
        self.changeWindowState()
            
    def filenames(self):
        return self._filenames

    def setFilenames(self, filenames):
        self._filenames = filenames

    def filename(self, lock=True):
        if lock:
            self.lock_filenames.lock()
        try:
            if not self.filenames():
                raise Exception('Empty filenames')
            return self.filenames()[self.index()]
        finally:
            if lock:
                self.lock_filenames.unlock()
        
    def wheelEvent(self, event):
        self._wheelDelta += event.angleDelta().y()
        self._processWheelDelta()

    def _processWheelDelta(self):
        #print('_processWheelDelta', self._wheelDelta)
        step = self._wheelStep * dpi() / 96
        if abs(self._wheelDelta) < step:
            return
        if self._wheelDelta > 0:
            self.prev()
            self._wheelDelta -= step
        else:
            self.next()
            self._wheelDelta += step
        #self._processWheelDelta()
        self._wheelDelta = 0

    def deleteCurrentImage(self, shift=False):
        try:
            with self.lock_filenames:
                winshell.delete_file(self.filename(False), allow_undo=not shift, no_confirm=True, silent=True)
                self.filenames().pop(self.index())
            self.setIndex(self.index())
        except Exception as e:
            e_msg = print_error(e)
            msg = MyMessageBox(self)
            msg.setIcon(QtGui.QMessageBox.Critical)
            msg.setWindowTitle(u'Error')
            msg.setText(e_msg)
            msg.exec_()

    def next(self):
        with self.lock_filenames:
            if self.filenames():
                self.setIndex((self.index()+1)%len(self.filenames()), lock=False)
            else:
                print('Empty filenames')

    def prev(self):
        with self.lock_filenames:
            if self.filenames():
                self.setIndex((self.index()-1)%len(self.filenames()), lock=False)
            else:
                print('Empty filenames')

    def first(self):
        with self.lock_filenames:
            self.setIndex(0, lock=False)

    def last(self):
        with self.lock_filenames:
            self.setIndex(len(self.filenames())-1, lock=False)

    def flipH(self):
        self._flipH = not self._flipH
        self.update()

    def flipV(self):
        self._flipV = not self._flipV
        self.update()

    def index(self):
        index = max(0, min(self._index, len(self.filenames())-1))
        self._index = index
        return index

    def setIndex(self, index, lock=True):
        if lock:
            self.lock_filenames.lock()
        try:
            index = max(0, min(index, len(self.filenames())-1))
            self._index = index
            self.update()
            if self._slideshow:
                self._t_slideshow = time()
                if self._pause_slideshow:
                    self._rt_pause = self._delay_slideshow
        finally:
            if lock:
                self.lock_filenames.unlock()

    def currentFolder(self):
        return self._currentFolder

    def setCurrentFolders(self, folders, files=[]):
        subfolder = self._subfolder
        imgs = []
        for folder in folders:
            for path, dir, files_ in os.walk(folder):
                imgs += [os.path.join(path, filename) for filename in files_ if (os.path.splitext(filename)[1][1:].lower() in FORMATS)]
                if not subfolder:
                    break
        imgs += files
        random.shuffle(imgs)
        self.setFilenames(imgs)
        self.first()

    def selectCurrentFolder(self):
        folder = QtGui.QFileDialog.getExistingDirectory(self, 'Select folder')
        if not folder:
            return
        folder = compatstr(folder)
        self.setCurrentFolders([folder])

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)

        action = QtGui.QAction(menu)
        action.setText('Select folder')
        action.triggered.connect(self.selectCurrentFolder)
        action.setIcon(getIcon('folder'))
        action.setShortcut('Ctrl+O')
        menu.addAction(action)
        
        menu.addSeparator()

        action = QtGui.QAction(menu)
        action.setText('Open current image')
        action.triggered.connect(self.openCurrentImage)
        action.setIcon(getIcon('view'))
        menu.addAction(action)

        action = QtGui.QAction(menu)
        action.setText('Open current image location')
        action.triggered.connect(self.openCurrentImageLocation)
        menu.addAction(action)

        menu.addSeparator()
        
        action = QtGui.QAction(menu)
        action.setText('Delete current image')
        action.triggered.connect(lambda: self.deleteCurrentImage(False))
        action.setIcon(getIcon('delete'))
        action.setShortcut('Del')
        menu.addAction(action)
        
        action = QtGui.QAction(menu)
        action.setText('Delete current image Permanently')
        action.triggered.connect(lambda: self.deleteCurrentImage(True))
        action.setIcon(getIcon('delete', color=COLOR['red']))
        action.setShortcut('Shift+Del')
        menu.addAction(action)

        menu.addSeparator()
        
        action = QtGui.QAction(menu)
        action.setText('Search subfolder')
        def foo():
            self._subfolder = not self._subfolder
        action.triggered.connect(foo)
        action.setCheckable(True)
        action.setChecked(self._subfolder)
        menu.addAction(action)
        
        action = QtGui.QAction(menu)
        action.setText('Flip horizontally')
        def foo():
            self._flipH = not self._flipH
            self.update()
        action.triggered.connect(foo)
        action.setCheckable(True)
        action.setChecked(self._flipH)
        action.setShortcut('Ctrl+M')
        menu.addAction(action)
        
        action = QtGui.QAction(menu)
        action.setText('Flip vertically')
        def foo():
            self._flipV = not self._flipV
            self.update()
        action.triggered.connect(foo)
        action.setCheckable(True)
        action.setChecked(self._flipV)
        action.setShortcut('Ctrl+F')
        menu.addAction(action)
        
        action = QtGui.QAction(menu)
        action.setText('Anti-aliasing')
        def foo():
            self._aa = not self._aa
            self.update()
        action.triggered.connect(foo)
        action.setCheckable(True)
        action.setChecked(self._aa)
        menu.addAction(action)
        
        action = QtGui.QAction(menu)
        action.setText('Always on top')
        def foo():
            self.toggleTop()
        action.triggered.connect(foo)
        action.setCheckable(True)
        action.setChecked(self._top)
        action.setShortcut('Ctrl+A')
        menu.addAction(action)

        menu.addSeparator()

        def foo(value):
            self._rotate = value
            self.update()
        action = ExtendedQAction('Rotate', foo, menu)
        action.slider.setRange(0, 360)
        action.slider.setValue(self._rotate)
        action.slider.setPageStep(45)
        menu.addAction(action)

        menu.addSeparator()

        if self._slideshow:
            action = QtGui.QAction(menu)
            action.setText('Resume slideshow' if self._pause_slideshow else 'Pause slideshow')
            action.triggered.connect(self.resumeSlideshow if self._pause_slideshow else self.pauseSlideshow)
            action.setIcon(getIcon('renew' if self._pause_slideshow else 'pause', color=None if self._pause_slideshow else COLOR['red']))
            action.setShortcut('P')
            menu.addAction(action)

        action = QtGui.QAction(menu)
        action.setText('Stop slideshow' if self._slideshow else 'Start slideshow')
        action.triggered.connect(self.stopSlideshow if self._slideshow else self.startSlideshow)
        action.setIcon(getIcon('close' if self._slideshow else 'play', color=COLOR['red'] if self._slideshow else None))
        menu.addAction(action)

        menu.addSeparator()

        action = QtGui.QAction(menu)
        action.setText('About')
        action.triggered.connect(self.about)
        action.setIcon(getIcon('info'))
        action.setShortcut('F1')
        menu.addAction(action)

        menu.addSeparator()

        action = QtGui.QAction(menu)
        action.setText('Quit')
        action.triggered.connect(self.close)
        action.setIcon(getIcon('exit'))
        action.setShortcut('Alt+F4')
        menu.addAction(action)

        menu.exec_(event.globalPos())

    def about(self):
        msg = MyMessageBox(self, width=320)
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setWindowTitle(u'About')
        msg.setText('<b>{}</b>'.format(TITLE))
        msg.setInformativeText('Developed by Kurt Bestor\n')
        msg.exec_()

    def openCurrentImage(self):
        try:
            os.startfile(self.filename())
        except Exception as e:
            print(e)

    def openCurrentImageLocation(self):
        try:
            filename = self.filename().replace('/', '\\')
            filename = shortName(filename)
            subprocess.Popen('explorer /select,"{}"'.format(filename))
        except Exception as e:
            print(e)

    def closeEvent(self, event):
        os._exit(0)#

    def resizeEvent(self, event):
        self._overlay.resize(event.size())
        super(MainWidget, self).resizeEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        if not self._aa:
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)
        w, h = self.width(), self.height()

        painter.fillRect(self.rect(), QtGui.QColor(32,32,32))

        if w <= 0 or h <= 0:
            return

        try:
            pixmap = request(self.filename())
        except Exception as e:
            print(e)
            pixmap = QtGui.QPixmap()

        if pixmap.isNull():
            return

        if h/w < pixmap.height()/pixmap.width():
            w_dst, h_dst = h*pixmap.width()/pixmap.height(), h
        else:
            w_dst, h_dst = w, w*pixmap.height()/pixmap.width()

        w_dst *= self._scale
        h_dst *= self._scale

        if w_dst <=0 or h_dst <= 0:
            return
        
        painter.save()
        painter.translate(w/2, h/2)
        rect_dst = QtCore.QRectF(-w_dst/2, -h_dst/2, w_dst, h_dst)
        painter.scale(-1 if self._flipH else 1, -1 if self._flipV else 1)
        painter.rotate(self._rotate)
        if w_dst < pixmap.width() / 2:
            w_pixmap = int(w_dst*2+.5)
            pixmap = pixmap.scaledToWidth(w_pixmap, mode=QtCore.Qt.SmoothTransformation)
        rect_src = QtCore.QRectF(0, 0, pixmap.width(), pixmap.height() - 1e-08)
        painter.drawPixmap(rect_dst, pixmap, rect_src)
        painter.restore()



if __name__ == '__main__':
    app = QtGui.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QtGui.QIcon(':/icons/main'))
    Loader.init()
    apply(app)

    win = MainWidget()
    win.resize(640, 640)
    win.show()

    app.exec_()
