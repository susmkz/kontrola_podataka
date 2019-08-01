# -*- coding: utf-8 -*-
"""
@author: User

U ovom modulu nalaze se pomocne funkcije koje se koriste u drugim dijelovima
aplikacije. Cilj ih je sve staviti na jedno mjesto radi smanjivanja ponavljanja
koda u vise raznih modula.
"""
import logging
import matplotlib
from PyQt4 import QtGui

class AppExcept(Exception):
    """definicjia vlastite exception klase"""
    pass


def load_config_item(cfg, section, option, default, tip):
    """
    funkcija koja ucitava odredjenu opciju iz config objekta u zadani
    target objekt ako opcija postoji. Ako opcija ne postoji, koristi se
    zadani default.

    P.S. Objasnjenje za dosta ruzan komad koda:

    Problem je sto configparser po defaultu cita samo stringove
    i output get metode je string, coercanje u specificni tip se
    moze elegantno srediti sa eval(), ali to stvara sigurnosnu rupu u
    aplikaciji.

    npr.
    poziv funkcije eval("(1,'banana',2.34)") ima output tip tuple sa 3 clana.
    prvi je tipa int, drugi je tipa str, treci je tipa float.

    problem nastaje kada se u eval kao string prosljedi npr. naredba za
    formatiranje hard diska...
    """
    try:
        if tip == str:
            value = cfg.get(section, option)
            msg = 'Config element {0} - {1} postoji, value = {2}'.format(section, option, value)
            logging.debug(msg)
            return value
        elif tip == int:
            value = cfg.getint(section, option)
            msg = 'Config element {0} - {1} postoji, value = {2}'.format(section, option, value)
            logging.debug(msg)
            return value
        elif tip == float:
            value = cfg.getfloat(section, option)
            msg = 'Config element {0} - {1} postoji, value = {2}'.format(section, option, value)
            logging.debug(msg)
            return value
        elif tip == bool:
            value = cfg.getboolean(section, option)
            msg = 'Config element {0} - {1} postoji, value = {2}'.format(section, option, value)
            logging.debug(msg)
            return value
        elif tip == list:
            textValue = cfg.get(section, option)
            value = textValue.split(',')
            msg = 'Config element {0} - {1} postoji, value = {2}'.format(section, option, value)
            logging.debug(msg)
            return value
        elif tip == tuple:
            textValue = cfg.get(section, option)
            value = textValue.split(',')
            value = tuple(value)
            msg = 'Config element {0} - {1} postoji, value = {2}'.format(section, option, value)
            logging.debug(msg)
            return value
    except Exception as err:
        logging.debug(err, exc_info=True)
        msg = 'Config element {0} - {1} nije definiran. Koristi se default, value = {2}'.format(section, option, default)
        logging.debug(msg)
        return default

def normalize_rgb(rgbTuple):
    """
    Adapter za crtanje.
    - matplotlib za boju ima niz vrijednosti izmedju [0-1], a ne izmedju [0-255]
    - ulaz je rgbTuple npr. (0,255,0)
    """
    r, g, b = rgbTuple
    return r/255, g/255, b/255

def make_color(rgb, a):
    """
    za zadani rgb i alpha vrati matplotlib valjani color
    """
    #normalize values na range [0-1]
    boja = normalize_rgb(rgb)
    #convert to hex color code
    hexcolor = matplotlib.colors.rgb2hex(boja)
    #convert to rgba pripremljen za crtanje
    color = matplotlib.colors.colorConverter.to_rgba(hexcolor, alpha=a)
    return color

def default_color_to_qcolor(rgb, a):
    """
    Helper funkcija za transformaciju boje u QColor. Funkcija je u biti adapter.
    RGB (tuple) se sastoji od tri broja u rasponu od 0-255 npr. (255,0,0) je crvena
    a (alpha, transparentnost) je float izmedju 0 i 1. Vece vrijednosti su manje prozirne
    Izlaz je QColor objekt, sa tim postavkama boje.
    input:
        rgb -> (r, g, b) tuple
        a -> float izmedju [0:1]
    output:
        QtGui.QColor objekt
    """
    boja = QtGui.QColor()
    #unpack tuple of rgb color
    r, g, b = rgb
    boja.setRed(r)
    boja.setGreen(g)
    boja.setBlue(b)
    #alpha je izmedju 0-1, input treba biti int 0-255
    a = int(a*255)
    boja.setAlpha(a)
    return boja

def color_to_style_string(tip, target, color):
    """
    Helper funkcija za izradu styleSheet stringa. Funkcija se iskljucivo koristi za
    promjenu pozadinske boje QWidgeta.
    Formatiranje pozadinske boje moguce je izvesti uz pomoc setStyleSheet metode
    na zadanim QObjektima. Ta funkcija uzima kao argument string (slican CSS-u).
    Ova funkcija stvara taj string.

    input:
        tip -> string, tip widgeta koji se mjenja npr. QPushButton
        target -> string, naziv widgeta kojem mjenjamo boju
            npr. 'label1'
        color -> QtGui.QColor (QColor objekt, sadrzi informaciju o boji)
    output:
        string - styleSheet 'css' stil ciljanog elementa
    """
    r = color.red()
    g = color.green()
    b = color.blue()
    a = int(100*color.alpha()/255)
    stil = str(tip) + "#" + target + " {background: rgba(" +"{0},{1},{2},{3}%)".format(r, g, b, a)+"}"
    return stil

def rgba_to_style_string(rgb, a, tip, target):
    """
    kombinacija funkcija color_to_style_string i default_color_to_qcolor
    rgb - tuple boje
    a - alpha vrijednost
    tip - klasa QWidgeta (string)
    target - specificna instanca tipa (string)
    """
    boja = default_color_to_qcolor(rgb, a)
    stil = color_to_style_string(tip, target, boja)
    return stil

def qcolor_to_default_color(color):
    """
    Helper funkcija za transformacije QColor u defaultnu boju, tj. rgb tuple i
    alphu (transparentrnost). Ulazni argument je QColor objekt, POSTOJE 2 izlazna
    argumenta, rgb tuple (3 vrijednosti izmedju 0 i 255) i alpha (float izmedju 0 i 1).
    input:
        color ->QtGui.QColor
    output:
        (r,g,b) tuple, i alpha
    """
    r = color.red()
    g = color.green()
    b = color.blue()
    a = color.alpha()/255
    return (r, g, b), a
