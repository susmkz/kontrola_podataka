#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  5 14:20:39 2014

@author: User
"""
import logging
import ctypes
from PyQt4 import QtCore, QtGui, uic
import app.view.rest_izbornik as rest_izbornik
import app.view.grafovi_panel as grafovi_panel
import app.general.app_dto as app_dto
import app.control.kontroler as kontroler
import app.view.auth_login as auth_login
import app.view.glavni_dijalog as glavni_dijalog
from app.view.pregled_komentara import PregledKomentara


base, form = uic.loadUiType('./app/view/ui_files/display.ui')
class GlavniProzor(base, form):
    """
    Glavni prozor aplikacije
    """
    def __init__(self, cfg=None, parent=None):
        logging.debug('inicijalizacija GlavniProzor, start.')
        super(base, self).__init__(parent)
        self.setupUi(self)
        self.config = cfg
        #set up inicijalizaciju
        self.setup_main_window()
        logging.debug('inicijalizacija GlavniProzor, kraj.')

    def setup_main_window(self):
        """
        setup glavnog prozora koristeci podatke iz self.config
        """
        #inicijalizacija konfiguracijskog objekta
        self.konfiguracija = app_dto.KonfigAplikacije(self.config)
        logging.debug('postavljen konfig objekt')
        #inicijalizacija panela sa grafovima koncentracije
        self.koncPanel = grafovi_panel.KoncPanel(konfig=self.konfiguracija, parent=self)
        self.koncPanelLayout.addWidget(self.koncPanel)
        logging.debug('postavljen panel sa grafovima koncentracije')
        #inicijalizacija panela sa zero/span grafovima
        self.zsPanel = grafovi_panel.ZeroSpanPanel(self.konfiguracija)
        self.zsPanelLayout.addWidget(self.zsPanel)
        logging.debug('postavljen panel sa zero i span grafovima')
        #inicijalizacija panela za pregled agregiranih (visednevni)
        self.visednevniPanel = grafovi_panel.RestPregledSatnih(self.konfiguracija)
        self.visednevniLayout.addWidget(self.visednevniPanel)
        logging.debug('postavljen panel za visednevni prikaz agregiranih podataka sa rest-a')
        #inicijalizacija panela za komentare
        self.komentariPanel = PregledKomentara()
        self.komentariLayout.addWidget(self.komentariPanel)
        #inicijalizacija i postavljanje kontrolnog widgeta (tree view/kalendar...)
        self.restIzbornik = rest_izbornik.RestIzbornik()
        self.dockWidget.setWidget(self.restIzbornik)
        logging.debug('postavljen restIzbornik')
        #setup icons
        self.setup_ikone()
        logging.debug('setup ikona zavrsen')
        #definiranje signala gui elemenata
        self.setup_signals()
        logging.debug('setup signala zavrsen')
        #na kraju inicijalizacije stavi inicijalizaciju kontorlora u event loop
        QtCore.QTimer.singleShot(0, self.setup_kontroler)

    def promjeniTabRef(self, x):
        """
        promjena tab, koji je od panela trenutno prikazan na ekranu.
        """
        msg = 'request promjene aktivnog taba. novi tab={0}'.format(str(x))
        logging.info(msg)
        self.emit(QtCore.SIGNAL('promjena_aktivnog_taba(PyQt_PyObject)'), x)

    def setup_ikone(self):
        """
        Postavljanje ikona za definirane QAkcije (toolbar/menubar...)
        """
        self.action_exit.setIcon(QtGui.QIcon('./app/view/icons/close19.png'))
        self.action_log_in.setIcon(QtGui.QIcon('./app/view/icons/enter3.png'))
        self.action_log_out.setIcon(QtGui.QIcon('./app/view/icons/door9.png'))
        self.action_reconnect.setIcon(QtGui.QIcon('./app/view/icons/cogwheel9.png'))
        self.action_stil_grafova.setIcon(QtGui.QIcon('./app/view/icons/bars7.png'))

    def setup_signals(self):
        """
        Metoda difinira signale koje emitiraju dijelovi sucelja prema kontrolnom
        elementu.
        """
        self.tabWidget.currentChanged.connect(self.promjeniTabRef)
        self.action_exit.triggered.connect(self.close)
        self.action_log_in.triggered.connect(self.request_log_in)
        self.action_log_out.triggered.connect(self.request_log_out)
        self.action_reconnect.triggered.connect(self.request_reconnect)
        self.action_stil_grafova.triggered.connect(self.promjeni_stil_grafova)
        self.action_info_aplikacija.triggered.connect(self.informacije)

    def informacije(self):
        tekst="Aplikacija za kontrolu podataka\nVerzija: 1.0\nAutor: DHMZ\n"
        ctypes.windll.user32.MessageBoxW(0, tekst, "O Aplikaciji", 0)

    def closeEvent(self, event):
        """
        Overloadani signal za gasenje aplikacije. Dodatna potvrda za izlaz.
        """
        saveState = self.exit_check()
        if not saveState:
            reply = QtGui.QMessageBox.question(
                self,
                'Potvrdi izlaz:',
                'Da li ste sigurni da hocete ugasiti aplikaciju?\nNeki podaci nisu spremljeni na REST servis.',
                QtGui.QMessageBox.Yes,
                QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                #pregazi konfig za trenutnim vrijednostima
                self.konfiguracija.overwrite_konfig_file()
                event.accept()
            else:
                event.ignore()
        else:
            #izlaz iz aplikacije bez dodatnog pitanja.
            #pregazi konfig za trenutnim vrijednostima
            self.konfiguracija.overwrite_konfig_file()
            event.accept()

    def exit_check(self):
        """
        Funkcija sluzi za provjeru spremljenog rada prije izlaska iz aplikacije.

        provjerava za svaki ucitani glavni kanal, datume ucitanih i datume
        uspjesno spremljenih na REST.

        Funkcija vraca boolean ovisno o jednakosti skupova datuma.

        poziva ga glavniprozor.py - u overloadanoj metodi za izlaz iz aplikacije
        """
        out = True #default je sve u redu
        for kanal in self.kontrola.setGlavnihKanala:
            if kanal in self.kontrola.kalendarStatus:
                if set(self.kontrola.kalendarStatus[kanal]['ok']) == set(self.kontrola.kalendarStatus[kanal]['bad']):
                    out = out and True
                else:
                    out = out and False
        #return rezultat (upozori da neki podaci NISU spremljeni na REST)
        return out

    def promjeni_stil_grafova(self):
        opis = self.kontrola.mapaMjerenjeIdToOpis
        drvo = self.kontrola.modelProgramaMjerenja
        if opis is not None and drvo is not None:
            logging.info('Pozvan dijalog za promjenu stila grafova')
            dijalog = glavni_dijalog.GlavniIzbor(
                defaulti=self.konfiguracija,
                opiskanala=opis,
                stablo=drvo,
                parent=self)
            #connect apply gumb
            self.connect(dijalog,
                         QtCore.SIGNAL('apply_promjene_izgleda'),
                         self.naredi_promjenu_izgleda_grafova)
            if dijalog.exec_():
                logging.debug('Dialog za stil closed, accepted')
                self.naredi_promjenu_izgleda_grafova()
            else:
                logging.debug('Dialog za stil closed')
                self.naredi_promjenu_izgleda_grafova()
            #disconnect apply gumb
            self.disconnect(dijalog,
                            QtCore.SIGNAL('apply_promjene_izgleda'),
                            self.naredi_promjenu_izgleda_grafova)
        else:
            QtGui.QMessageBox.information(self, 'Problem:', 'Nije moguce pokrenuti dijalog.\nProvjeri da li su programi mjerenja uspjesno ucitani.')
            logging.debug('Nije moguce inicijalizirati dijalog za stil grafova, nedostaje model mjerenja')

    def naredi_promjenu_izgleda_grafova(self):
        """
        emitiraj zahtjev prema kontorlolu za update izgleda grafova
        """
        self.emit(QtCore.SIGNAL('apply_promjena_izgleda_grafova'))

    def request_log_in(self):
        """
        - prikazi dijalog za unos korisnickog imena i lozinke
        - enable/disable odredjene akcije
        - emitiraj signal sa tuple objektom (korisnicko ime, sifra)
        """
        dijalog = auth_login.DijalogLoginAuth()
        if dijalog.exec_():
            info = dijalog.vrati_postavke()
            msg = 'User logged in. User = {0}'.format(info[0])
            logging.info(msg)
            #disable log in action, enable log out action
            self.action_log_in.setEnabled(False)
            self.action_log_out.setEnabled(True)
            self.emit(QtCore.SIGNAL('user_log_in(PyQt_PyObject)'), info)

    def request_log_out(self):
        """
        - prikazi dijalog za potvrdu log outa
        - enable/diable odredjene akcije
        - emitiraj signal za log out
        """
        dijalog = QtGui.QMessageBox.question(self,
                                             'Log out:',
                                             'Potvrdi log out.',
                                             QtGui.QMessageBox.Yes,
                                             QtGui.QMessageBox.No)
        if dijalog == QtGui.QMessageBox.Yes:
            logging.info('User logged out.')
            self.action_log_in.setEnabled(True)
            self.action_log_out.setEnabled(False)
            self.emit(QtCore.SIGNAL('user_log_out'))

    def request_reconnect(self):
        """
        metoda emitira request za reconnect proceduru
        """
        self.emit(QtCore.SIGNAL('reconnect_to_REST'))

    def setup_kontroler(self):
        """
        Metoda inicijalizira kontroler dio aplikacije.
        """
        self.kontrola = kontroler.Kontroler(parent=None, gui=self)
