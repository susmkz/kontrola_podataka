# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 14:45:37 2015

@author: User
"""
import logging
import datetime
import numpy as np
import pandas as pd
from PyQt4 import QtCore


class DataModel(QtCore.QObject):
    """
    Subklasan QtCore.QObject radi emita u metodi self.change_flag()

    Data model aplikacije
    Podaci se spremaju u mapu pandas datafrejmova (self.data)
    {programMjerenjaId:DataFrame,...}

    programMjerenjaId je integer koji odgovara id broju programa mjerenja u bazi.
    """

    def __init__(self, reader=None, writer=None, agregator=None, parent=None):
        """
        Da bi objekt funkcionirao kako treba, potrebno mu je prosljediti reference
        na objekte readera, writera i agregatora. Postoje metode setteri za
        te objekte tako da se objekt moze inicijalizirati i bez njih, ali se onda
        reader, writer i agregator moraju naknadno postaviti sa setterom.
        """
        QtCore.QObject.__init__(self, parent)
        self.data = {}
        self.citac = None
        self.pisac = None
        self.agregator = None
        self.dataDirty = False

        if reader != None:
            self.set_reader(reader)
        if writer != None:
            self.set_writer(writer)
        if agregator != None:
            self.set_agregator(agregator)

    def set_reader(self, reader):
        """
        Setter objekta citaca u model.

        Zbog kompatibilnosti citac mora definirati metode:

        read(key = None, date = None)
            -uzima 2 keyword argumenta
                key --> kanal
                date --> datum string formata 'YYYY-MM-DD'
            -MORA vratiti tuple (kljuc, frejm)
                - kljuc --> kljuc pod kojim se podatak zapisuje u dokument
                - frejm --> dobro formatirani dataframe (za detalje o stupcima
                vidi data_reader.py, metodu adaptiraj_ulazni_json())
        """
        self.citac = reader
        msg = 'reader {0} postavljen u dokument'.format(repr(reader))
        logging.info(msg)

    def set_writer(self, writer):
        """
        Setter objekta writera u model.
        Zbog kompatibilnosti writer mora definirati metode:

        write_minutni(key = None, date = None, frejm = None)
            -argumenti:
                key --> integer, program mjerenja id u bazi
                date --> string, datum formata 'YYYY-MM-DD'
                frejm --> slajs minutnog frejma
            -izlaz:
                -vraca True ako je uspjesno spremljen na REST
                -vraca False ako nije uspjesno spremljen na REST
        """
        self.pisac = writer
        msg = 'writer {0} postavljen u dokument'.format(repr(writer))
        logging.info(msg)

    def set_agregator(self, agreg):
        """
        Setter objekta agregatora u model.

        Zbog kompatibilnosti agregator mora definirati metode:

        agregiraj(frejm):
            -argumenti:
                frejm --> pandas DataFrame (slajs kojeg treba agregirati)
            -izlaz:
                -satno agregirani DataFrame sa stupcima
        """
        self.agregator = agreg
        msg = 'agregator {0} postavljen u dokument'.format(repr(agreg))
        logging.info(msg)

    def set_dirty(self, x):
        """
        Setter membera koji prati da li je doslo do promjene flaga u podacima.
        x je boolean, False ako nije doslo do promjene, True ako je doslo do
        promjene
        """
        self.dataDirty = x
        msg = 'set_dirty, dirty={0}'.format(str(x))
        logging.debug(msg)

    def is_dirty(self):
        """
        Funkcija vraca boolean. True ako je doslo do promjene flaga na trenutnim
        podacima. False u suprotnom slucaju.
        """
        return bool(self.dataDirty)

    def citaj(self, key=None, date=None, ndana=1):
        """
        Metoda dokumenta zaduzena za citanje sa REST servisa. Operativni dio
        citanja delegiraDelegira citacu (self.citac).

        -key je kljuc pod kojim ce se spremiti podaci u mapu self.data
        -date je datum formata 'YYYY-MM-DD' koji se treba ucitati

        Vraca True ako je podatak ucitan i spremljen u self.data, a False ako nije.
        """
        try:
            assert isinstance(key, int), 'Assert fail, ulazni kljuc nije tipa integer'
            kljuc, df = self.citac.read(key=key, date=date, ndana=ndana)
            self.dataframe_structure_test(df)
            df['status'] = df['status'].astype(np.int64)
            df['id'] = df['id'].astype(np.int64)
            if len(df):
                serija = df['nivoValidacije'].map(self.pronadji_kontorlirane)
                df.loc[:, 'flag'] = df.loc[:, 'flag'] * serija
                self.set_frame(key=kljuc, frame=df)
                self.set_dirty(False)
                return True
            else:
                tekst = " ".join(['Podaci za', str(key), str(date), 'nisu ucitani. Prazan frejm'])
                logging.info(tekst)
                self.set_dirty(False)
                return False
        except (AttributeError, TypeError):
            tekst = 'Frejm nije spremljen u model. Neispravan reader.'
            logging.error(tekst, exc_info=True)
            self.set_dirty(False)
            return False
        except AssertionError:
            tekst = 'Frejm nije spremljen u model. Neispravan frejm.'
            logging.error(tekst, exc_info=True)
            self.set_dirty(False)
            return False

    def dataframe_structure_test(self, frame):
        """provjera da li je dataframe dobre strukture"""
        assert type(frame) == pd.core.frame.DataFrame, 'Assert fail, ulaz nije DataFrame objekt'
        assert type(frame.index) == pd.core.indexes.datetimes.DatetimeIndex, 'Assert fail, DataFrame nema vremenski indeks'
        stupci = list(frame.columns)
        assert 'koncentracija' in stupci, 'Assert fail, nedostaje stupac "koncentracija"'
        assert 'status' in stupci, 'Assert fail, nedostaje stupac "status"'
        assert 'flag' in stupci, 'Assert fail, nedostaje stupac "flag"'
        assert 'id' in stupci, 'Assert fail, nedostaje stupac "id"'
        assert 'statusString' in stupci, 'Assert fail, nedostaje stupac "statusString"'
        assert 'nivoValidacije' in stupci, 'Assert fail, nedostaje stupac "nivoValidacije"'

    def pronadji_kontorlirane(self, x):
        """
        Adapter funkcija koja sluzi za ucinkovito trazenje vec validiranih podataka.
        Funkcija vraca multiplikator za vrijednost flag (za taj indeks).
        """
        if x == 0:
            return 1
        elif x == 1:
            return 1000

    def set_frame(self, key=None, frame=None):
        """
        Funkcija postavlja frame u mapu self.data pod kljucem key.
        key --> integer, program mjerenja id
        frame --> ucitani pandas DataFrame
        """
        #recast 'statusString to str type
        frame['statusString'] = frame['statusString'].astype(str)
        frame.sort_index(inplace=True)
        self.data[key] = frame

    def persist_minutne_podatke(self, key=None, date=None):
        """
        Funkcija je zaduzena za spremanje minutnih podataka. Operativni dio
        spremanja na REST delegira writeru (self.pisac).

        -key je kljuc pod kojim su spremljeni podaci u mapu self.data
        -date je datum formata 'YYYY-MM-DD' koji se treba spremiti

        P.S. iako u self.data moze biti zapisano vise dana, spremaj jedan po jedan.

        funckija vraca True ako je slajs frema spremljen, a False ako slice nije
        spremljen na REST
        """
        t = pd.to_datetime(date)
        tmin = t + datetime.timedelta(minutes=1)
        tmax = t + datetime.timedelta(days=1)
        msg = 'dokument, naredba za spremanje slajsa podataka za:\nkanal={0}\ndatum={1}\ntmin{2}\ntmax{3}'.format(str(key), str(date), str(tmin), str(tmax))
        logging.info(msg)
        frejm = self.get_frame(key=key, tmin=tmin, tmax=tmax)
        if len(frejm):
            uspjeh = self.pisac.write_minutni(key=key, date=date, frejm=frejm)
            if uspjeh:
                self.set_dirty(False)
                msg = 'podaci za kanal={0} i datum={1} su uspjesno spremljeni na REST'.format(str(key), str(date))
                logging.info(msg)
                return True
            else:
                return False
        else:
            #podaci nisu spremljeni na rest servis
            msg = 'podaci za kanal={0} i datum={1} nisu spremljeni na REST. Prazan frejm.'.format(str(key), str(date))
            logging.info(msg)
            return False

    def get_frame(self, key=None, tmin=None, tmax=None):
        """
        Funkcija dohvaca trazeni slice frejma.
        key --> integer, program mjerenja id
        tmin --> pandas timestamp (pd.tslib.Timestamp)
             --> indeks od kojega se uzima slajs, rub je ukljucen
        tmax --> pandas timestamp (pd.tslib.Timestamp)
             --> indeks do kojega se uzima slajs, rub je ukljucen

        Funkcija vraca trazeni slajs, ili defaultni prazan DataFrame objekt u
        slucaju pogreske prilikom rada.
        P.S. ako u trazenom vremenskom slajsu nema podataka, vraca se prazan
        frame.
        """
        try:
            msg = 'get_frame zahtjev. key={0}, tmin={1}, tmax={2}'.format(str(key), str(tmin), str(tmax))
            logging.debug(msg)
            assert key is not None, 'Assert fail, key = None'
            assert key in self.data, 'Assert fail, key ne postoji u mapi self.data'
            assert isinstance(tmin, pd.Timestamp), 'Assert fail, krivi tip tmin'
            assert isinstance(tmax, pd.Timestamp), 'Assert fail, krivi tip tmax'
            if tmin > tmax:
                tmin, tmax = tmax, tmin
            df = self.data[key].copy()
            df = df[df.index >= tmin]
            df = df[df.index <= tmax]
            msg = 'get_frame procesiran. key={0}, tmin={1}, tmax={2}'.format(str(key), str(tmin), str(tmax))
            logging.debug(msg)
            msg = 'trazeni slajs:\n{0}'.format(str(df))
            logging.debug(msg)
            return df
        except (LookupError, TypeError, AssertionError):
            msg = 'Problem prilikom dohvacanja slajsa frejma. key={0}, tmin={1}, tmax={2}'.format(str(key), str(tmin), str(tmax))
            logging.error(msg, exc_info=True)
            defaultColumns = ['koncentracija',
                              'status',
                              'flag',
                              'id',
                              'statusString',
                              'nivoValidacije']
            df = pd.DataFrame(columns=defaultColumns)
            df = df.set_index(df['id'].astype('datetime64[ns]'))
            return df

    def dohvati_minutne_frejmove(self, lista=None, tmin=None, tmax=None):
        """
        Funkcija vraca mapu minutnih slajsova.
        Ulazni parametari:
        -lista --> lista integera (programi mjerenja id)
        -tmin --> donja granica vremenskog intervala (ukljucena)
        -tmax --> gornja granica vremenskog intervala (ukljucena)
        """
        out = {}
        for kljuc in lista:
            if kljuc in self.data:
                out[kljuc] = self.get_frame(key=kljuc, tmin=tmin, tmax=tmax)
        return out

    def dohvati_agregirane_frejmove(self, lista=None, tmin=None, tmax=None):
        """
        Funkcija vraca mapu satno agregiranih slajsova.
        Ulazni parametari:
        -lista --> lista integera (programi mjerenja id)
        -tmin --> donja granica vremenskog intervala (ukljucena)
        -tmax --> gornja granica vremenskog intervala (ukljucena)
        """
        out = {}
        for kljuc in lista:
            if kljuc in self.data:
                out[kljuc] = self.get_agregirani_frame(key=kljuc, tmin=tmin, tmax=tmax)
        return out

    def get_agregirani_frame(self, key=None, tmin=None, tmax=None):
        """
        Metoda dohvaca trazeni slajs, agregira ga te vraca satno agregirani frejm
        """
        frejm = self.get_frame(key=key, tmin=tmin, tmax=tmax)
        try:
            agregiraniFrejm = self.agregator.agregiraj(frejm, key)
            msg = 'agregirani frejm:\n{0}'.format(str(agregiraniFrejm))
            logging.debug(msg)
            return agregiraniFrejm
        except (AttributeError, TypeError):
            msg = 'Agregator Error, agregator nije postavljen ili nema odgovarajucu metodu "agregiraj"'
            logging.error(msg)
            defaultColumns = ['broj podataka',
                              'status',
                              'flag',
                              'avg',
                              'std',
                              'min',
                              'max',
                              'q05',
                              'median',
                              'q95',
                              'count']
            df = pd.DataFrame(columns=defaultColumns)
            df = df.set_index(df['flag'].astype('datetime64[ns]'))
            return df


    def change_flag(self, key=None, tmin=None, tmax=None, flag=0):
        """
        Promjena flaga za program mjerenja u zadanom vremenskom intervalu
        """
        try:
            if tmin > tmax:
                tmin, tmax = tmax, tmin
            if key in self.data:
                self.data[key].loc[tmin:tmax, u'flag'] = flag
                self.notify_about_change()
                self.set_dirty(True)
                msg = 'Flag uspjesno promjenjen na flag={0}.\nid={1}\nvrijeme1={2}\nvrijeme2={3}'.format(str(flag), str(key), str(tmin), str(tmax))
                logging.info(msg)
        except (KeyError, LookupError, TypeError):
            msg = 'Flag nije uspjesno promjenjen.\nid={0}\nvrijeme1={1}\nvrijeme2={2}'.format(str(key), str(tmin), str(tmax))
            logging.error(msg, exc_info=True)

    def notify_about_change(self):
        """
        Funkcija emitira specificni signal da je doslo do promjene u flaga.
        """
        logging.debug('promjena flaga, emit promjene statusa')
        self.emit(QtCore.SIGNAL('model_flag_changed'))

    def provjeri_validiranost_dana(self, kanal, datum):
        """
        Provjera da li su u slajsu frejma (za kanal i datum) validirani svi
        podaci.
        kanal --> integer
        datum --> QDate objekt

        Funkcija vraca boolean ovisno da li su svi podaci unutar datuma validirani.
        """
        msg = 'provjera validiranosti za kanal={0} i datum={1}'.format(str(kanal), str(datum))
        logging.debug(msg)
        dan = pd.to_datetime(datum.toPyDate())
        maxi = dan+datetime.timedelta(days=1)
        mini = dan+datetime.timedelta(minutes=1)
        if kanal not in self.data:
            logging.debug('Kanal nije ucitan u self.data, vrati False')
            return False
        slajs = self.get_frame(key=kanal, tmin=mini, tmax=maxi)
        if len(slajs) == 0:
            logging.debug('U trazenom slajsu nema podataka (prazan frame), vrati False')
            return False
        testValidacije = slajs['flag'].map(self.test_stupnja_validacije)
        lenSvih = len(testValidacije)
        lenDobrih = len(testValidacije[testValidacije == True])
        if lenSvih == lenDobrih:
            logging.debug('U trazenom slajsu svi su validirani, vrati True')
            return True
        else:
            logging.debug('U trazenom slajsu neki nisu validirani, vrati False')
            return False

    def test_stupnja_validacije(self, x):
        """
        Pomocna funkcija, provjerava da li je vrijednost 1000 ili -1000. Bitno za
        provjeru validacije stupca flag (da li su svi podaci validirani).
        """
        if abs(x) == 1000:
            return True
        else:
            return False
