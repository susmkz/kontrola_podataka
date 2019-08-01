# -*- coding: utf-8 -*-
"""
Created on Fri Feb 13 12:01:41 2015

@author: User
"""
import logging
import pandas as pd
from PyQt4 import QtCore, uic

base10, form10 = uic.loadUiType('./app/view/ui_files/dodavanje_referentnih_zero_span.ui')
class DijalogDodajRefZS(base10, form10):
    """
    Dijalog za dodavanje novih referentnih vrijednosti za ZERO i SPAN.

    polja su:

    1. program mjerenja
        --> hardcoded (za sada) opisni string
        --> pokazuju na trenutno aktivni glavni kanal.

    2. Pocetak primjene
        --> QDateTimeEdit
        --> izbor vremena od kojega se primjenjuje

    3. Vrsta
        --> combobox sa izborom ZERO ili SPAN

    4. Vrijednost
        --> QLineEdit
        --> nova referentna vrijednost

    5. Dozvoljeno odstupanje
        --> QLineEdit
        --> tolerancija odstupanja
        --> potencijalno nebitno, jer koliko sam shvatio server automatski racuna
        tu vrijednost???
    """
    def __init__(self, parent=None, opisKanal=None, idKanal=None):
        logging.debug('Inicijalizacija dijaloga za dodavanje ref. vrijednosti, start')
        super(base10, self).__init__(parent)
        self.setupUi(self)
        # set int id kanala
        self.idKanal = idKanal
        #set program mjerenja opis
        self.programSelect.setText(opisKanal)
        #set vrijeme da pokazuje trenutak kaada je dijalog inicijaliziran
        self.vrijemeSelect.setDateTime(QtCore.QDateTime.currentDateTime())
        self.vrijednostSelect.textEdited.connect(self.check_vrijednost)
        logging.debug('Inicijalizacija dijaloga za dodavanje ref. vrijednosti, kraj')

    def check_vrijednost(self, x):
        """
        provjera ispravnosti unosa vrijednosti... samo smisleni brojevi
        """
        self.vrijednostSelect.setStyleSheet('')
        test = self.convert_line_edit_to_float(x)
        if not test:
            self.vrijednostSelect.setStyleSheet('color : red')

    def convert_line_edit_to_float(self, x):
        """
        pretvaranje line edit stringa u float vrijednost

        vrati valjani float ako se string da convertat
        vratni None ako se string ne moze prebaciti u float ili ako nema podataka
        """
        x = str(x)
        if x:
            x = x.replace(',', '.')
            try:
                return float(x)
            except ValueError:
                return None
        else:
            return None

    def vrati_postavke(self):
        """
        mehanizam kojim dijalog vraca postavke
        """
        # QDateTime objekt
        vrijeme = self.vrijemeSelect.dateTime()
        #convert to python datetime
        vrijeme = vrijeme.toPyDateTime()
        #convert u pandas.tslib.Timestamp
        vrijeme = pd.to_datetime(vrijeme)
        #convert u unix timestamp
        vrijeme = self.time_to_int(vrijeme)
        vrsta = self.vrstaSelect.currentText()[0]  #samo prvo slovo stringa.. 'Z' ili 'S'
        vrijednost = self.convert_line_edit_to_float(self.vrijednostSelect.text())  #float
        out = {'vrsta': vrsta,
               'vrijednost': vrijednost,
               'vrijeme': vrijeme,
               'kanal': self.idKanal}
        msg = '"spremljene" postavke dijaloga za referentnu vrijednost. postavke={0}'.format(str(out))
        logging.debug(msg)
        return out

    def time_to_int(self, x):
        """
        Funkcija pretvara vrijeme x (pandas.tslib.Timestamp) u unix timestamp

        testirano sa:
        http://www.onlineconversion.com/unix_time.htm

        bilo koji pandas timestamp definiran rucno preko string reprezentacije ili
        programski (npr.funkcij pandas.tslib.Timestamp.now() ) vraca int koji
        odgovara zadanom vremenu.

        BITNO!
        based on seconds since standard epoch of 1/1/1970
        vrijeme je u GMT
        """
        return x.value / 1000000000
