#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 17 15:18:10 2014

@author: User
"""
import logging
import datetime
import pandas as pd
import numpy as np

################################################################################
################################################################################
class FileReader(object):
    """
    implementacija csv readera
    #TODO! za rad sa csv fileovima ignore or rework
    """
    def __init__(self):
        self.frejmovi = {}

    def valjan_conversion(self, x):
        if x:
            return 1
        else:
            return -1

    def nan_conversion(self, x):
        if x > -99:
            return x
        else:
            return np.NaN

    def read(self, key=None, date=None, ndana=1):
        """
        Metoda za ucitavanje minutnih podataka:
        ulazni parametri:
        - key : integer, program mjerenja id
        - date : string, trazeni datum formata 'YYYY-MM-DD'
        - ndana : integer

        Funkcija vraca tuple. Prvi element je program mjerenja id (key), a drugi
        element je pandas DataFrame (df). Ako dodje do pogreske prilikom citanja
        vraca se prazan dataframe.
        """
        msg = 'csv read, key={0}, date={1}, ndana={2}'.format(str(key), str(date), str(ndana))
        logging.info(msg)
        df = self.frejmovi[key]
        tmax = pd.to_datetime(date)
        tmin = tmax - datetime.timedelta(days=ndana)
        df = df[df.index >= tmin]
        df = df[df.index <= tmax]
        return key, df

    def clear_all_keys(self):
        self.frejmovi = {}

    def ucitaj_csv_file_u_memoriju(self, filename, key):
        #TODO! podesiti za stupce..
        df = pd.read_csv(filename,
                         sep=',',
                         parse_dates=True)
        assert 'vrijeme' in df.columns, 'ERROR - Nedostaje stupac: "vrijeme"'
        assert 'id' in df.columns, 'ERROR - Nedostaje stupac: "id"'
        assert 'vrijednost' in df.columns, 'ERROR - Nedostaje stupac: "vrijednost'
        assert 'statusString' in df.columns, 'ERROR - Nedostaje stupac: "statusString"'
        assert 'valjan' in df.columns, 'ERROR - Nedostaje stupac: "valjan"'
        assert 'statusInt' in df.columns, 'ERROR - Nedostaje stupac: "statusInt"'
        assert 'nivoValidacije' in df.columns, 'Error - Nedostaje stupac: "nivoValidacije"'

        df = df.set_index(df['vrijeme'])
        renameMap = {'vrijednost':'koncentracija',
                     'valjan':'flag',
                     'statusInt':'status'}
        df.rename(columns=renameMap, inplace=True)
        df['koncentracija'] = df['koncentracija'].map(self.nan_conversion)
        df['flag'] = df['flag'].map(self.valjan_conversion)
        df.drop('vrijeme', inplace=True, axis=1) #drop column vrijeme
        #add to dict of frejms
        if key in self.frejmovi:
            self.frejmovi[key] = self.frejmovi[key].append(df)
        else:
            self.frejmovi[key] = df


################################################################################
################################################################################


class RESTReader(object):
    """
    implementacija REST json citaca
    """
    def __init__(self, source=None):
        """
        RESTReader se instancira uz pomoc instance WebZahtjev.
        RestReader je adapter/wrapper oko instance WebZahtjeva koji je zaduzen
        za citanje minutnih podataka sa REST servisa.
        """
        self.source = source

    def valjan_conversion(self, x):
        """
        Adapter funkcija. Pretvara ulazni boolean x u integer. Output je 1 ako
        je x True, -1 ako je x False. Funkcija se koristi prilikom prilagodbe
        stupca 'flag'.
        """
        if x:
            return 1
        else:
            return -1

    def nan_conversion(self, x):
        """
        Adapter funkcija. Funkcija primarno sluzi da se na ucinkovit nacin
        zamjene besmisleno male vrijednosti koncentracije u NaN.
        """
        if x > -99:
            return x
        else:
            return np.NaN

    def adaptiraj_ulazni_json(self, x):
        """
        Funkcija je zaduzena da konvertira ulazni json string (x) u pandas
        DataFrame objekt.

        output je pandas dataframe (prazan frame ako nema podataka)
        """
        try:
            df = pd.read_json(x, orient='records', convert_dates=['vrijeme'])
            assert 'vrijeme' in df.columns, 'ERROR - Nedostaje stupac: "vrijeme"'
            assert 'id' in df.columns, 'ERROR - Nedostaje stupac: "id"'
            assert 'vrijednost' in df.columns, 'ERROR - Nedostaje stupac: "vrijednost'
            assert 'statusString' in df.columns, 'ERROR - Nedostaje stupac: "statusString"'
            assert 'valjan' in df.columns, 'ERROR - Nedostaje stupac: "valjan"'
            assert 'statusInt' in df.columns, 'ERROR - Nedostaje stupac: "statusInt"'
            assert 'nivoValidacije' in df.columns, 'Error - Nedostaje stupac: "nivoValidacije"'

            df = df.set_index(df['vrijeme'])
            renameMap = {'vrijednost':'koncentracija',
                         'valjan':'flag',
                         'statusInt':'status'}
            df.rename(columns=renameMap, inplace=True)
            df['koncentracija'] = df['koncentracija'].map(self.nan_conversion)
            df['flag'] = df['flag'].map(self.valjan_conversion)
            df.drop('vrijeme', inplace=True, axis=1) #drop column vrijeme
            return df
        except (ValueError, TypeError, AssertionError):
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            expectedColumns = ['koncentracija',
                               'status',
                               'flag',
                               'id',
                               'statusString',
                               'nivoValidacije']
            df = pd.DataFrame(columns=expectedColumns)
            df = df.set_index(df['id'].astype('datetime64[ns]'))
            return df

    def read(self, key=None, date=None, ndana=1):
        """
        Metoda za ucitavanje minutnih podataka sa rest servisa.
        ulazni parametri:
        - key : integer, program mjerenja id
        - date : string, trazeni datum formata 'YYYY-MM-DD'
        - ndana : integer

        Funkcija delegira dohvacanje json stringa sa REST serivsa i naknadno
        konvertira json string sa podacima u dobro formatirani pandas data frame.

        Funkcija vraca tuple. Prvi element je program mjerenja id (key), a drugi
        element je pandas DataFrame (df). Ako dodje do pogreske prilikom citanja
        sa rest servisa ili prilikom parsanja jsona, vraca se prazan dataframe.
        """
        msg = 'read, key={0}, date={1}, ndana={2}'.format(str(key), str(date), str(ndana))
        logging.info(msg)
        jsonString = self.source.get_sirovi(key, date, ndana)
        df = self.adaptiraj_ulazni_json(jsonString)
        return key, df


class RESTWriter(object):
    """
    implementacija REST writer objekta
    """
    def __init__(self, source=None):
        """
        RESTWriter se instancira uz pomoc instance WebZahtjev.
        RestWriter je adapter/wrapper oko instance WebZahtjeva koji je zaduzen
        za spremanje/upload minutnih podataka na REST servis.
        """
        self.source = source

    def write_minutni(self, key=None, date=None, frejm=None):
        """
        Metoda za upload minutnih podataka na rest servis.
        ulazni parametri:
        - key : integer, program mjerenja id
        - date : string, datum formata 'YYYY-MM-DD'
        - frejm : slajs pandas dataframea.

        Funkcija adaptira slajs pandas DataFrame-a i priprema ga za upload na
        REST (provjera trazenih stupaca, izbacivanje viska podataka...).
        Upload je delegiran instanci WebZahtjev-a.

        Ovisno o uspjehu operacije spremanja na REST funkcija vraca True ili False.
        """
        msg = 'write_minutni, key={0}, date={1}, broj podataka={2}'.format(str(key), str(date), str(len(frejm)))
        logging.info(msg)
        if key == None:
            msg = 'write_minutni problem : program mjerenja nije zadan. key={0}'.format(str(key))
            logging.error(msg)
            return False
        if 'id' not in frejm.columns:
            msg = 'write_minutni problem : U frejmu nedostaje stupac "id". stupci frejma = {0}'.format(str(frejm.columns))
            logging.error(msg)
            return False
        if 'flag' not in frejm.columns:
            msg = 'write_minutni problem : U frejmu nedostaje stupac "flag". stupci frejma = {0}'.format(str(frejm.columns))
            logging.error(msg)
            return False
        frejm.rename(columns={'flag':'valjan'}, inplace=True)
        frejm['valjan'] = frejm['valjan'].map(self.int_to_boolean)
        for stupac in frejm.columns:
            if stupac not in ['id', 'valjan']:
                frejm.drop(stupac, inplace=True, axis=1)
        frejm['id'] = frejm['id'].astype(np.int64)
        jstring = frejm.to_json(orient='records')
        uspjeh = self.source.upload_json_minutnih(jstring=jstring, program=key, date=date)
        return uspjeh

    def int_to_boolean(self, x):
        """
        Pomocna adapter funkcija. Koristi se za prilagodbu vrijednosti stupca
        'flag' u boolean vrijednosti.
        """
        if x >= 0:
            return True
        else:
            return False
