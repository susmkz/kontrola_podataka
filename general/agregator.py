# -*- coding: utf-8 -*-
"""
implementacija satnog agregatora minutnih podataka
"""
import pandas as pd
import numpy as np
import logging


class Agregator(object):
    """
    Agregator minutnih podataka. Minutni podaci se agregiraju u satne.

    P.S. komentar za flag podataka
    -validirani i dobar flag --> flag = 1000
    -nevalidirani i dobar --> flag = 1
    -validirani i los flag --> flag = -1000
    -nevalidirani i los flag --> flag = -1
    -validirani i prekratak niz valjanih --> flag = -1000
    -nevalidirani i prekratak niz valjanih --> flag = -1
    """
    def __init__(self):
        """U buducnosti dozvoliti iniicjalizaciju nekih parametara?"""
        self.webrequest = None

    def set_webrequest(self, x):
        """setter interfacea prema REST servisu. Potrebno je prosljediti webRequest instancu."""
        #XXX! validan web zahtjev za dohvacanje broja podataka u satu
        self.webrequest = x

    def test_validacije(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Test da li su svi unutar intervala validirani.
        Validairani minutni podatci imaju flag 1000 ili -1000
        """
        if len(x) == 0:
            return np.NaN
        total = True
        for ind in x:
            if abs(ind) != 1000:
                #postoji barem jedan minutni podatak koji nije validiran
                total = False
                break
        if total:
            #svi minutni su validirani
            return 1000
        else:
            #barem jedan minutni nije validiran
            return 1

    def my_mean(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija racuna mean.
        """
        if len(x) == 0:
            return np.NaN
        return np.mean(x)

    def my_std(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija racuna standardnu devijaciju.
        """
        if len(x) == 0:
            return np.NaN
        return np.std(x)

    def my_min(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca najmanju vrijednost.
        """
        if len(x) == 0:
            return np.NaN
        return np.min(x)

    def my_max(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca najvecu vrijednost.
        """
        if len(x) == 0:
            return np.NaN
        return np.max(x)

    def h_q05(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca 5 percentil podataka.
        """
        if len(x) == 0:
            return np.NaN
        return np.percentile(x, 5)

    def h_q50(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca 50 percentil podataka, medijan.
        """
        if len(x) == 0:
            return np.NaN
        return np.percentile(x, 50)

    def h_q95(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca 95 percentil podataka.
        """
        if len(x) == 0:
            return np.NaN
        return np.percentile(x, 95)

    def h_binary_or(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca vrijednosti binary OR svih podataka u listi.
        """
        if len(x) == 0:
            return np.NaN
        result = 0
        for i in x:
            try:
                result |= int(i)
            except ValueError:
                #logging.debug('Agregator exception prilikom agregiranja statusa.', exc_info=True)
                pass
        return result

    def h_size(self, x):
        """
        Pomocna funkcija agregatora. Ulaz je numpy array ili lista. Izlaz je broj.
        Funkcija vraca broj podataka u listi.
        """
        if len(x) == 0:
            return np.NaN
        return len(x)

    def agregiraj(self, frejm, pId):
        """
        Glavna funkcija za agregiranje minutnih podataka.
        input
        frejm --> pandas dataframe
            -mora imati stupce : koncentracija, status, flag
            -mora imati vremenski indeks (datetime index)
        pId --> integer program mjerenja ID
        output --> pandas dataframe
            -ima stupce :
                broj podataka, status, flag, acg, std,
                min, max, q05, median, q95, count
            -ima vremenski indeks (satni)(datetime index)
            -ako nema podataka vraca np.NaN vrijednosti za satne intervale.
        """
        logging.debug('Agregator - pocetak agregiranja.')
        #postupak u slucaju da agregatoru netko prosljedi prazan slice
        if len(frejm) == 0:
            #vrati dobro formatirani prazan dataframe
            df = pd.DataFrame(columns=['broj podataka',
                                       'status',
                                       'flag',
                                       'avg',
                                       'std',
                                       'min',
                                       'max',
                                       'q05',
                                       'median',
                                       'q95',
                                       'count'])
            df = df.set_index(df['flag'].astype('datetime64[ns]'))
            #vrati dobro formatirani prazan agregirani frejm
            logging.debug('Agregator - kraj agregiranja. Ulazni parametar je prazan frejm, vracam prazan agregirani frejm.')
            return df
        #sastavljanje izlaznog frejma agregiranih podataka
        agregirani = pd.DataFrame()
        #agregacija statusa prije odbacivanja losih / nepostojecih podataka
        tempDf = frejm.copy()
        dfStatus = tempDf[u'status']
        temp = dfStatus.resample('H', closed='right', label='right').apply(self.h_binary_or)
        agregirani[u'status'] = temp
        #izbaci sve indekse gdje je koncentracija np.NaN (nema podataka)
        df = frejm[np.isnan(frejm[u'koncentracija']) == False]
        tempDf = df.copy()
        #uzmi samo pandas series stupac 'koncentracija'
        dfKonc = tempDf[u'koncentracija']
        #resample series --> prebroji koliko ima podataka
        temp = dfKonc.resample('H', closed='right', label='right').apply(self.h_size)
        agregirani[u'broj podataka'] = temp
        #test validiranosti
        tempDf = df.copy()
        dfFlag = tempDf[u'flag']
        temp = dfFlag.resample('H', closed='right', label='right').apply(self.test_validacije)
        agregirani[u'flag'] = temp
        #upis pomocnih funkcija sa kojima cemo agregirati u mapu
        helperFunc = {u'avg':self.my_mean,
                      u'std':self.my_std,
                      u'min':self.my_min,
                      u'max':self.my_max,
                      u'q05':self.h_q05,
                      u'median':self.h_q50,
                      u'q95':self.h_q95,
                      u'count':self.h_size}
        #kopiraj frame, i filtriraj samo gdje je flag veci ili jednak od 0
        tempDf = df.copy()
        tempDf = tempDf[tempDf[u'flag'] >= 0]
        tempDf = tempDf[u'koncentracija']
        #loop preko helper funkcija za agregiranje.
        for col in helperFunc:
            #copy filtriranu seriju koncentracija (bez nan vrijednosti sa flagom >= 0)
            temp = tempDf.copy()
            #satno agregiraj sa ciljanom funkcijom
            temp = temp.resample('H', closed='right', label='right').apply(helperFunc[col])
            #rename series to match name
            temp.name = col
            #dodaj seriju u izlazni frejm
            agregirani[col] = temp
        #iz frejma agregiranih treba maknuti sve gdje je 'broj podataka' np.Nan
        agregirani = agregirani[np.isnan(agregirani[u'broj podataka']) == False]
        #provjera za broj valjanih podataka (flag > 0). Mora biti barem 75% podataka
        #valjanih u svakom satu, inace se sat automatski flagira lose.
        try:
            #pokusaj dohvacanja ukupnog broja podataka u satu, fallback default je 60
            brojusatu = self.webrequest.get_broj_u_satu(str(pId))
        except Exception as err:
            logging.error(str(err), exc_info=True)
            brojusatu = 60
        brojvaljanih = brojusatu * 0.75 #75% round down
        for i in agregirani.index:
            if np.isnan(agregirani.loc[i, u'count']) or agregirani.loc[i, u'count'] < brojvaljanih:
                if agregirani.loc[i, u'flag'] == 1000:
                    agregirani.loc[i, u'flag'] = -1000
                else:
                    agregirani.loc[i, u'flag'] = -1
        #Problem prilikom agregiranja. ako sve indekse unutar jednog sata prebacimo
        #da su losi, funkcije koje racunaju srednje vrijednosti isl. ne reazlikuju
        #taj slucaj od nepostojecih podataka te uvijek vrate np.NaN (not a number).
        #Potrebno je postaviti te intervale na neku vrijednost (recimo 0) da bi se
        #prikazali na grafu.
        for i in agregirani.index:
            if np.isnan(agregirani.loc[i, u'avg']) and agregirani.loc[i, u'broj podataka'] > 0:
                #ako je average np.nan i ako je broj podataka u intevalu veci od 0 (ima podataka)
                #postavi vrijenosti na 0 da se mogu prikazati
                agregirani.loc[i, u'avg'] = 0
                agregirani.loc[i, u'min'] = 0
                agregirani.loc[i, u'max'] = 0
                agregirani.loc[i, u'q05'] = 0
                agregirani.loc[i, u'q95'] = 0
                agregirani.loc[i, u'count'] = 0
                agregirani.loc[i, u'median'] = 0
                agregirani.loc[i, u'std'] = 0
        logging.debug('Agregator - kraj agregiranja.')
        #return agregirani frejm
        return agregirani
