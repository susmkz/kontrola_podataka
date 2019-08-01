# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 10:58:46 2015

@author: User
"""
import numpy as np
import pandas as pd
import logging
import requests
import json
import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth
from PyQt4 import QtGui, QtCore


class WebZahtjev(object):
    """
    Klasa zaduzena za komunikaciju sa REST servisom

    INSTANCIRAN U:
    - modul kontroler.py prilikom inicijalizacije objekta Kontroler
    - referenca na taj objekt se prosljedjuje svima koji komuniciraju sa REST-om

    KORISTI SE U:
    -datareader.RESTReader (source)
    -datareader.RESTWriter (source)
    """
    def __init__(self, base, resursi, auth):
        """
        inicijalizira se sa:
        - base url REST servisa
        - mapom sa relativnim putevima (od baznog url-a) do specificnih servisa
        - tuple (user, password) potreban za autorizaciju
        """
        self._base = base
        self._resursi = resursi
        self.user, self.pswd = auth

    def get_zerospan_referentne_liste(self, programMjerenjaId, tip):
        """Metoda dohvaca listu referentnih vrijednosti za neki program mjerenja
        i tip.Input je programMjerenjaId (integer), tip (string, 'zero' ili 'span').
        """
        try:
            msg = 'get_zero_ref_listu pozvan sa argumentom, args={0}'.format(str(programMjerenjaId))
            logging.debug(msg)
            url = self._base + self._resursi['zerospan']+'/referentne_vrijednosti/'+str(programMjerenjaId)+'/'+str(tip)
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=15.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            msg = "get_zero_ref_listu procesiran, response code={0}, request url={1}".format(r.status_code, r.url)
            logging.debug(msg)
            msg = "output get_zero_ref_listu:\n{0}".format(str(r.text))
            logging.debug(msg)
            return r.text
        #TODO! fix exception default return
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}\nkoristim default = ''".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return ''
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nkoristim default = ''".format(str(e2), url)
            logging.error(msg, exc_info=True)
            return ''
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nkoristim default = ''".format(str(e3), url)
            logging.error(msg, exc_info=True)
            return ''

    def get_broj_u_satu(self, programMjerenjaId):
        """
        Metoda dohvaca minimalni broj podataka u satu za neki programMjerenjaID.
        Output je integer ili u slucaju pogreske default vrijednost od 45
        """
        try:
            msg = 'get_broj_u_satu pozvan sa argumentom, args={0}'.format(str(programMjerenjaId))
            logging.debug(msg)
            url = self._base + self._resursi['programMjerenja']+'/podaci/'+str(programMjerenjaId)
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=15.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            msg = "get_broj_u_satu procesiran, response code={0}, request url={1}".format(r.status_code, r.url)
            logging.debug(msg)
            msg = "output get_broj_u_satu:\n{0}".format(str(r.text))
            logging.debug(msg)
            out = json.loads(r.text)
            return int(out['brojUSatu'])
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}\nkoristim default = 60".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return 60
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nkoristim default = 60".format(str(e2), url)
            logging.error(msg, exc_info=True)
            return 60
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nkoristim default = 60".format(str(e3), url)
            logging.error(msg, exc_info=True)
            return 60

    def get_satne_podatke(self, mapa):
        """
        Metoda dohvaca satno agregirane podatke sa REST servisa.
        - ulazni parametar mapa je dictionary sa poljima:
        {
            'datumOd': string, format mora biti "YYYY-MM-DDThh:mm:ss"
            'datumDo': string, format mora biti "YYYY-MM-DDThh:mm:ss"
            'kanal': int, id programa mjerenja
            'valjani': boolean, Da li se prikazuju samo valjani
            'validacija': int, nivo validacije
        }

        Metoda vraca json string ili prazan string ako dodje do greske u radu.
        """
        try:
            msg = 'get_satne_podatke pozvan sa argumentima, args={0}'.format(str(mapa))
            logging.debug(msg)
            url = self._base + self._resursi['satniPodaci']+'/'
            res = "/".join([str(mapa['kanal']), str(mapa['datumOd']), str(mapa['datumDo'])])
            url = url+res
            head = {"accept":"application/json"}
            payload = {"samo_valjani":mapa['valjani'],
                       "nivo_validacije":mapa['validacija']}
            r = requests.get(url,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd),
                             params=payload)
            assert r.ok == True, 'Bad request'
            msg = "get_satni_podaci procesiran, response code={0}, request url={1}".format(r.status_code, r.url)
            logging.debug(msg)
            msg = 'output get_satne_podatke:\n{0}'.format(str(r.text))
            logging.debug(msg)
            return r.text
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return ''
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\ndodatni parametri zahtjeva={2}".format(str(e2), url, str(payload))
            logging.error(msg, exc_info=True)
            return ''
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\ndodatni parametri zahtjeva={2}".format(str(e3), url, str(payload))
            logging.error(msg, exc_info=True)
            return ''

    def get_statusMap(self):
        """
        Metoda dohvaca podatke o statusima sa REST servisa
        vraca mapu (dictionary):
        {broj bita [int] : opisni string [str]}
        U slucaju pogreske prilikom rada vraca praznu mapu
        """
        try:
            url = self._base + self._resursi['statusMap']
            logging.debug('get_statusMap pozvan')
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=39.1,
                             headers = head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            jsonStr = r.text
            x = json.loads(jsonStr)
            rezultat = {}
            for i in range(len(x)):
                rezultat[x[i]['i']] = x[i]['s']
            msg = 'get_statusMap procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            msg = 'output status map dictionary:\n{0}'.format(str(rezultat))
            logging.debug(msg)
            return rezultat
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return {}
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}".format(str(e2), url)
            logging.error(msg, exc_info=True)
            return {}
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}".format(str(e3), url)
            logging.error(msg, exc_info=True)
            return {}

    def parse_xml(self, x):
        """
        Pomocna funkcija za internu upotrebu, NE POZIVAJ IZVAN MODULA.
        Parsira xml sa programima mjerenja preuzetih sa rest servisa,
        input: string
        output: (nested) dictionary sa bitnim podacima. Primarni kljuc je program
        mjerenja id, sekundarni kljucevi su opisni (npr. 'komponentaNaziv')
        """
        rezultat = {}
        root = ET.fromstring(x)
        for programMjerenja in root:
            i = int(programMjerenja.find('id').text)
            postajaId = int(programMjerenja.find('.postajaId/id').text)
            postajaNaziv = programMjerenja.find('.postajaId/nazivPostaje').text
            komponentaId = programMjerenja.find('.komponentaId/id').text
            komponentaNaziv = programMjerenja.find('.komponentaId/naziv').text
            komponentaMjernaJedinica = programMjerenja.find('.komponentaId/mjerneJediniceId/oznaka').text
            komponentaFormula = programMjerenja.find('.komponentaId/formula').text
            usporednoMjerenje = programMjerenja.find('usporednoMjerenje').text
            #dodavanje mjerenja u dictionary
            rezultat[i] = {
                'postajaId':postajaId,
                'postajaNaziv':postajaNaziv,
                'komponentaId':komponentaId,
                'komponentaNaziv':komponentaNaziv,
                'komponentaMjernaJedinica':komponentaMjernaJedinica,
                'komponentaFormula':komponentaFormula,
                'usporednoMjerenje':usporednoMjerenje,
                'povezaniKanali':[i]} #TODO! dodan je povezan kanal...
        return rezultat

    def get_programe_mjerenja(self):
        """
        Metoda salje zahtjev za svim programima mjerenja prema REST servisu.
        Uz pomoc funkcije parse_xml, prepakirava dobivene podatke u mapu
        'zanimljivih' podataka. Vraca (nested) dictionary programa mjerenja ili
        prazan dictionary u slucaju pogreske prilikom rada.

        -bitno za test login funkcionalnosti... bogatiji report
        """
        try:
            url = self._base + self._resursi['programMjerenja']
            head = {"accept":"application/xml"}
            payload = {"id":"findAll", "name":"GET"}
            logging.debug('get_programe_mjerenja pozvan')
            r = requests.get(url,
                             params=payload,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            rezultat = self.parse_xml(r.text)
            msg = 'get_programe_mjerenja procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            msg = 'output dictionary programa mjerenja:\n{0}'.format(str(rezultat))
            logging.debug(msg)
            return rezultat
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            #TODO! prikaz warning popup prozora kod loseg odgovora (sve osim 200)
            QtGui.QApplication.restoreOverrideCursor()
            msg = "Neuspjesan login.\n\ncode={0} , {1}\n\nurl={2}".format(r.status_code, r.reason, r.url)
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'login error', msg)
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            return {}
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nparametri={2}".format(str(e2), url, str(payload))
            logging.error(msg, exc_info=True)
            #TODO! prikaz warning popup prozora kod greske sa requests library-om
            QtGui.QApplication.restoreOverrideCursor()
            msg = "Neuspjesan login.\n\n{0}\n\nrequest url={1}\n\nparametri={2}".format(str(e2), url, str(payload))
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'login error', msg)
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            return {}
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nparametri={2}".format(str(e3), url, str(payload))
            logging.error(msg, exc_info=True)
            #TODO! prikaz warning popup prozora kod greske sa requests library-om
            QtGui.QApplication.restoreOverrideCursor()
            msg = "Neuspjesan login.\n\n{0}\n\nrequest url={1}\n\nparametri={2}".format(str(e3), url, str(payload))
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'login error', msg)
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            return {}

    def get_sirovi(self, programMjerenja, datum, brojdana):
        """
        Za zadani program mjerenja (int) i datum (string, formata YYYY-MM-DD)
        dohvati sirove (minutne) podatke sa REST servisa.
        Output funkcije je json string ili prazan string ako je doslo do pogreske
        prilikom rada.
        """
        try:
            url = self._base + self._resursi['siroviPodaci']+'/'+str(programMjerenja)+'/'+datum
            payload = {"id":"getPodaci", "name":"GET", "broj_dana":brojdana}
            head = {"accept":"application/json"}
            msg = 'get_sirovi pozvan sa argumentima, id={0}, datum={1}, brojdana={2}'.format(str(programMjerenja), str(datum), str(brojdana))
            logging.debug(msg)
            assert brojdana >= 1, 'Broj dana mora biti veci ili jednak 1.'
            r = requests.get(url,
                             params=payload,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            msg = 'get_sirovi procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            msg = 'get_sirovi output frame:\n{0}'.format(str(r.text))
            logging.debug(msg)
            return r.text
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return ''
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nparametri={2}".format(str(e2), url, str(payload))
            logging.error(msg, exc_info=True)
            return ''
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nparametri={2}".format(str(e3), url, str(payload))
            logging.error(msg, exc_info=True)
            return ''

    def test_unutar_granica(self, programMjerenja, datum, brojdana, minValue, maxValue):
        """Helper funkcija, za zadani program mjerenja provjeri da li su sve vrijednosti
        unutar zadanih granica. Vrati False u slučaju nedostatka podataka, ili ako je granica
        prekoracena, True ako su svi podaci unutar granice [minValue, maxValue]."""
        #TODO! za provjeru temperature kontejnera
        jstr = self.get_sirovi(programMjerenja, datum, brojdana)
        if jstr:
            df = pd.read_json(jstr, orient='records', convert_dates=['vrijeme'])
            if not (len(df)):
                return False #empty dataframe
            konc = np.array(df['vrijednost'])
            #min max vrijednosti
            minV = np.nanmin(konc)
            maxV = np.nanmax(konc)
            if np.isnan(minValue):
                return False #case all nan values
            if (minV < minValue) or (maxV > maxValue):
                return False #case some values out of bounds
            else:
                return True #case all values inside bounds
        else:
            return False #case prazan string, some error happened

    def upload_json_minutnih(self, program=None, jstring=None, date=None):
        """
        Spremanje minutnih podataka na REST servis.
        ulazni parametrni su:
        -program : program mjerenja id
        -jstring : json string minutnih podataka koji se treba uploadati
        -date : datum

        Funkcija vraca True ako su podaci uspjesno predani REST servisu.
        Funkcija vraca False ako podaci nisu uspjesno predani REST servisu.
        """
        try:
            url = self._base + self._resursi['siroviPodaci']+'/'+str(program)+'/'+str(date)
            payload = {"id":"putPodaci", "name":"PUT"}
            headers = {'Content-type': 'application/json'}
            msg = 'upload_json_minutnih pozvan sa argumentima: id={0}, datum={1}:\n{2}'.format(str(program), str(date), str(jstring))
            logging.debug(msg)
            if not isinstance(jstring, str):
                raise ValueError('Ulazni parametar nije tipa string.')
            if len(jstring) == 0:
                raise ValueError('Ulazni json string je prazan')
            r = requests.put(url,
                             params=payload,
                             data=jstring,
                             headers=headers,
                             timeout=39.1,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            msg = 'upload_json_minutnih procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            return True
        except ValueError as e0:
            msg = "Value error - {0}".format(str(e0))
            logging.error(msg, exc_info=True)
            return False
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return False
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nparametri={2}\nheaderi={3}".format(str(e2), url, str(payload), str(headers))
            logging.error(msg, exc_info=True)
            return False
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nparametri={2}\nheaderi={3}".format(str(e3), url, str(payload), str(headers))
            logging.error(msg, exc_info=True)
            return False

    def get_zero_span(self, programMjerenja, datum, kolicina):
        """
        Dohvati zero-span vrijednosti
        ulazni parametri su:
        -programMjerenja : integer, id programa mjerenja
        -datum : string formata 'YYYY-MM-DD'
        -kolicina : integer, broj dana koji treba dohvatiti

        Funkcija vraca json string sa trazenim podacima ili prazan string ako je
        doslo do problema prilikom rada.
        """
        try:
            url = self._base + self._resursi['zerospan']+'/'+str(programMjerenja)+'/'+datum
            payload = {"id":"getZeroSpanLista", "name":"GET", "broj_dana":int(kolicina)}
            msg = 'get_zero_span pozvan sa parametrima: id={0}, datum={1}, brojdana={2}'.format(str(programMjerenja), str(datum), str(kolicina))
            head = {"accept":"application/json"}
            logging.debug(msg)
            r = requests.get(url,
                             params=payload,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request/response'
            msg = 'get_zero_span procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            msg = 'get_zero_span output:\n{0}'.format(str(r.text))
            logging.debug(msg)
            return r.text
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return ''
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nparametri={2}".format(str(e2), url, str(payload))
            logging.error(msg, exc_info=True)
            return ''
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nparametri={2}".format(str(e3), url, str(payload))
            logging.error(msg, exc_info=True)
            return ''

    def upload_ref_vrijednost_zs(self, jS, kanal):
        """
        Funkcija sluzi za upload nove referentne vrijednosti zero ili span
        na REST.
        ulazni parametri:
        - kanal : integer,  id programa mjerenja
        - jS : string, json string sa podacima o novoj referentnog vrijednosti

        Funkcija vraca True ako je nova vrijednost uspjesno predana REST servisu.
        Funkcija vraca False ako nova vrijednost nije uspjesno predana REST servisu.
        """
        try:
            url = self._base + self._resursi['zerospan']+'/'+str(kanal)
            payload = {"id":"putZeroSpanReferentnuVrijednost", "name":"PUT"}
            headers = {'Content-type': 'application/json'}
            msg = 'upload_ref_vrijednost_zs parametri: id={0}:\n{1}'.format(str(kanal), str(jS))
            logging.debug(msg)
            if not isinstance(jS, str):
                raise ValueError('Ulazni json string je krivo zadan.')
            if len(jS) == 0:
                raise ValueError('Ulazni json string je prazan')
            r = requests.put(url,
                             params=payload,
                             data=jS,
                             headers=headers,
                             timeout=9.1,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request'
            msg = 'upload_ref_vrijednost_zs procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            return True
        except ValueError as e0:
            msg = "Value error - {0}".format(str(e0))
            logging.error(msg, exc_info=True)
            return False
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return False
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nparametri={2}\nheaderi={3}".format(str(e2), url, str(payload), str(headers))
            logging.error(msg, exc_info=True)
            return False
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nparametri={2}\nheaderi={3}".format(str(e3), url, str(payload), str(headers))
            logging.error(msg, exc_info=True)
            return False

    def dohvati_status_info_za_podatak(self, podatakId, statusString):
        """
        Metoda dohvaca status info za minutni podatak uz pomoc njegovog id (int)
        i opisa statusa (string)
        """
        try:
            path = self._base + self._resursi['siroviPodaci'] + '/' + 'opis_statusa'
            url = "/".join([path, str(podatakId), str(statusString)])
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request/response'
            return r.text
        except AssertionError as e1:
            msg = 'Assertion error - {0}\nstatus code={1}\nrequest url={2}'.format(str(e1), str(r.status_code), str(url))
            logging.error(msg, exc_info=True)
            return '{}'
        except requests.exceptions.RequestException as e2:
            msg = 'Request exception - {0}\nrequest url={1}'.format(str(e2), str(url))
            logging.error(msg, exc_info=True)
            return '{}'
        except Exception as e3:
            msg = 'General exception - {0}\nrequest url={1}'.format(str(e3), str(url))
            logging.error(msg, exc_info=True)
            return '{}'

    def dohvati_zadnju_osobu_koja_je_mjenjala_podatak(self, podatakId):
        """
        Metoda dohvaca zadnju osobu koja je mjenjala podatak
        """
        try:
            path = self._base + self._resursi['siroviPodaci'] + '/' + 'opis_statusa'
            url = "/".join([path, str(podatakId), 'KONTROLA'])
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request/response'
            return r.text
            opisi = json.loads(r.text)
            return opisi
        except AssertionError as e1:
            msg = 'Assertion error - {0}\nstatus code={1}\nrequest url={2}'.format(str(e1), str(r.status_code), str(url))
            logging.error(msg, exc_info=True)
            return {}
        except requests.exceptions.RequestException as e2:
            msg = 'Request exception - {0}\nrequest url={1}'.format(str(e2), str(url))
            logging.error(msg, exc_info=True)
            return {}
        except Exception as e3:
            msg = 'General exception - {0}\nrequest url={1}'.format(str(e3), str(url))
            logging.error(msg, exc_info=True)
            return {}

    def dohvati_sve_komentare_za_id(self, programMjerenjaId):
        """
        Metoda dohvaca sve komentare za zadani program mjerenja (integer)

        output je json string ili "[]" u slucaju nedostatka podataka ili greske
        """
        #TODO!
        try:
            path = self._base + self._resursi['komentari']
            url = "/".join([path, str(programMjerenjaId)])
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request/response'
            return r.text
        except AssertionError as e1:
            msg = 'Assertion error - {0}\nstatus code={1}\nrequest url={2}'.format(str(e1), str(r.status_code), str(url))
            logging.error(msg, exc_info=True)
            return '[]'
        except requests.exceptions.RequestException as e2:
            msg = 'Request exception - {0}\nrequest url={1}'.format(str(e2), str(url))
            logging.error(msg, exc_info=True)
            return '[]'
        except Exception as e3:
            msg = 'General exception - {0}\nrequest url={1}'.format(str(e3), str(url))
            logging.error(msg, exc_info=True)
            return '[]'

    def dohvati_komentare_za_id_start_kraj(self, programMjerenjaId, pocetak, kraj):
        """
        Metoda dohvaca kmentare za program mjerenja unutar vremenskog raspona
        [pocetak, kraj]

        ulazni parametri:
        programMjerenjaId - int
        pocetak - string tipa YYYY-MM-DDTHH:MM:SS
        kraj - string tipa YYYY-MM-DDTHH:MM:SS

        output je json string ili "[]" u slucaju nedostatka podataka ili greske
        """
        #TODO!
        try:
            #convet timestamps to propperly formatted strings
            start = str(pocetak).replace(" ", "T")
            end = str(kraj).replace(" ", "T")
            path = self._base +  self._resursi['komentari']
            url = "/".join([path, str(programMjerenjaId), start, end])
            head = {"accept":"application/json"}
            r = requests.get(url,
                             timeout=39.1,
                             headers=head,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request/response'
            return r.text
        except AssertionError as e1:
            msg = 'Assertion error - {0}\nstatus code={1}\nrequest url={2}'.format(str(e1), str(r.status_code), str(url))
            print(msg)
            logging.error(msg, exc_info=True)
            return '[]'
        except requests.exceptions.RequestException as e2:
            msg = 'Request exception - {0}\nrequest url={1}'.format(str(e2), str(url))
            logging.error(msg, exc_info=True)
            print(msg)
            return '[]'
        except Exception as e3:
            msg = 'General exception - {0}\nrequest url={1}'.format(str(e3), str(url))
            logging.error(msg, exc_info=True)
            print(msg)
            return '[]'

    def put_komentar_na_rest(self, jString):
        """
        Metoda uploada ispravno formatirani json string komentar na REST
        """
        #TODO!
        try:
            path = self._base + self._resursi['komentari']
            url = path
            head = {'Content-type': 'application/json'}
            payload = {"id":"putXml", "name":"PUT"}
            r = requests.put(url,
                             params=payload,
                             data=jString,
                             headers=head,
                             timeout=15.1,
                             auth=HTTPBasicAuth(self.user, self.pswd))
            assert r.ok == True, 'Bad request/response'
            msg = 'put_komentar_na_rest procesiran, response code={0}, request url={1}'.format(r.status_code, r.url)
            logging.debug(msg)
            return True
        except ValueError as e0:
            msg = "Value error - {0}".format(str(e0))
            logging.error(msg, exc_info=True)
            return False
        except AssertionError as e1:
            msg = "Assertion error - {0}\nresponse code={1}\nrequest url={2}".format(str(e1), r.status_code, r.url)
            logging.error(msg, exc_info=True)
            return False
        except requests.exceptions.RequestException as e2:
            msg = "Request exception - {0}\nrequest url={1}\nparametri={2}\nheaderi={3}".format(str(e2), url, str(payload), str(head))
            logging.error(msg, exc_info=True)
            return False
        except Exception as e3:
            msg = "General exception - {0}\nrequest url={1}\nparametri={2}\nheaderi={3}".format(str(e3), url, str(payload), str(head))
            logging.error(msg, exc_info=True)
            return False

