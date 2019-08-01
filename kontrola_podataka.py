#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 31 14:06:55 2014

@author: User

VERZIJE EKSTERNIH MODULA
-PyQt4 4.11.3
-pandas 0.22.0
-numpy 1.14.2
-matplotlib 2.2.2
-requests 2.5.3

- standard library python 3.4.3 (sys, configparser...)
"""
import sys
import configparser
import logging
from PyQt4 import QtGui

import app.view.glavniprozor as glavniprozor

def setup_logging(file='applog.log', mode='a', lvl='INFO'):
    """
    pattern of use:
    ovo je top modul, za sve child module koristi se isti logger sve dok
    su u istom procesu (konzoli). U child modulima dovoljno je samo importati
    logging module te bilo gdje pozvati logging.info('msg') (ili neku slicnu
    metodu za dodavanje u log).
    """
    DOZVOLJENI = {'DEBUG': logging.DEBUG,
                  'INFO': logging.INFO,
                  'WARNING': logging.WARNING,
                  'ERROR': logging.ERROR,
                  'CRITICAL': logging.CRITICAL}
    # lvl parametar
    if lvl in DOZVOLJENI:
        lvl = DOZVOLJENI[lvl]
    else:
        lvl = logging.ERROR
    #filemode
    if mode not in ['a', 'w']:
        mode = 'a'
    try:
        logging.basicConfig(handlers=[logging.FileHandler(file, mode, 'utf-8')], level=lvl, format=u'{levelname}:::{asctime}:::{module}:::{funcName}:::{message}', style='{')
        #logging.basicConfig(level=lvl,
        #                    filename=file,
        #                    filemode=mode,
        #                    format='{levelname}:::{asctime}:::{module}:::{funcName}:::{message}',
        #                    style='{')
    except Exception as err:
        print('Error sa loggerom.', err)
        #exit iz programa.
        raise SystemExit('Error prilikom konfiguracije loggera, Application exit.')


def main():
    """
    Pokretac aplikacije.
    """
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
    except Exception as err:
        print('Greska kod ucitavanja config.ini, ', err)
        # kill interpreter
        raise SystemExit('Error prilikom citanja konfig filea, Application exit.')

    # dohvati postevke za logger (section, option, fallback ako log ne postoji)
    filename = config.get('LOG_SETUP', 'file', fallback='applog.log')
    filemode = config.get('LOG_SETUP', 'mode', fallback='a')
    level = config.get('LOG_SETUP', 'lvl', fallback='INFO')
    #setup logging
    setup_logging(file=filename, mode=filemode, lvl=level)

    #instancira QApplication objekt i starta main event loop
    aplikacija = QtGui.QApplication(sys.argv)
    #inicijaliziraj aplikaciju sa config objektom
    glavniProzor = glavniprozor.GlavniProzor(cfg=config)
    #prikaz GUI na ekran
    glavniProzor.show()
    #clean exit iz aplikacije
    sys.exit(aplikacija.exec_())

if __name__ == '__main__':
    main()
