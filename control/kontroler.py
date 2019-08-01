# -*- coding: utf-8 -*-
"""
Created on Thu Jan 22 09:52:37 2015

@author: User
"""
from PyQt4 import QtCore, QtGui
import datetime
import pandas as pd
import json
import logging
import copy
from functools import partial

import app.general.networking_funkcije as networking_funkcije  # web zahtjev, interface prema REST servisu
import app.model.dokument_model as dokument_model  # interni model za zapisivanje podataka u dict pandas datafrejmova
import app.model.data_reader as data_reader  # REST reader/writer
import app.general.agregator as agregator  # agregator
import app.model.model_drva as model_drva  # pomocne klase za definiranje tree modela programa mjerenja
import app.view.dodaj_ref_zs as dodaj_ref_zs  # dijalog za dodavanje referentnih zero i span vrijednosti


class Kontroler(QtCore.QObject):
    """
    Kontrolni dio aplikacije.
    Tu se nalazi glavna logika programa i povezivanje dijela akcija iz gui
    djela sa modelom.
    """
    def __init__(self, parent=None, gui=None):
        logging.debug('Inicijalizacija kontrolora, start')
        QtCore.QObject.__init__(self, parent)
        self.satniAgregator = agregator.Agregator() #incijalizacija agregatora
        self.dokument = dokument_model.DataModel() #inicijalizacija dokumenta
        self.dokument.set_agregator(self.satniAgregator) #postavljanje agregatora u model
        self.gui = gui #gui element - instanca displaya
        ###definiranje pomocnih membera###
        self.aktivniTab = self.gui.tabWidget.currentIndex()  #koji je tab trenutno aktivan? bitno za crtanje
        self.pickedDate = None  #zadnje izabrani datum, string 'yyyy-mm-dd'
        self.gKanal = None  #trenutno aktivni glavni kanal, integer
        self.zadnjiPovezaniKanal = None
        self.sat = None  #zadnje izabrani sat na satnom grafu, bitno za crtanje minutnog
        self.pocetnoVrijeme = None  #donji rub vremenskog slajsa izabranog dana
        self.zavrsnoVrijeme = None  #gornji rub vremenskog slajsa izabranog dana
        self.modelProgramaMjerenja = None  #tree model programa mjerenja
        self.statusMap = None #status mapa {bit position : opis statusa}
        self.mapaMjerenjeIdToOpis = None  #dict podataka o kanalu, kljuc je ID mjerenja
        self.appAuth = ("", "")  #korisnicko ime i lozinka za REST servis
        self.setGlavnihKanala = set()  #set glavnih kanala, prati koji su glavni kanali bili aktivni
        self.kalendarStatus = {}  #dict koji prati za svaki kanalId da li su podaci ucitani i/ili spremljeni
        self.brojDana = 30  #max broj dana za zero span graf
        self.drawStatus = [False, False]  #status grafa prema panelu [koncPanel, zsPanel]. True ako je graf nacrtan.
        self.zeroFrejm = None  #member sa trenutnim Zero frejmom
        self.spanFrejm = None  #member sa trenutnim Span frejmom
        self.sviBitniKanali = []  #lista potrebnih programMjerenjaId (kanala) za crtanje. Refresh za svaki izbor kanala i datuma.
        self.frejmovi = {}  #mapa aktualnih frejmova (programMjerenjaId:slajs)
        self.agregiraniFrejmovi = {}  #mapa aktualnih agregiranih frejmova (programMjerenjaId:slajs)
        self.brojDanaSatni = 1 #member prati koliko dana se prikazuje za satno agregirani graf
        self.brojSatiMinutni = 1 #member prati koliko sati se prikazuje na minutno agregiranom grafu
        self.frejmKomentara = pd.DataFrame(columns=['Kanal', 'Od', 'Do', 'Komentar']) #frejm komentara
        self.criticalTemperatureWarningMap = {} #mapa sa podacima o kritičnosti temperature (da li je temp kontejnera za taj kanal izvan opsega [15-30])
        #setup radio selection (ako ih treba vise...traba ih definitati u ui fileu i dodati na popise)
        self.koncRadioButtons = [
            self.gui.koncPanel.koncRadioButton1,
            self.gui.koncPanel.koncRadioButton2,
            self.gui.koncPanel.koncRadioButton3,
            self.gui.koncPanel.koncRadioButton4]
        self.zsRadioButtons = [
            self.gui.zsPanel.zsRadioButton1,
            self.gui.zsPanel.zsRadioButton2,
            self.gui.zsPanel.zsRadioButton3,
            self.gui.zsPanel.zsRadioButton4]
        self.vdRadioButtons = [
            self.gui.visednevniPanel.vdRadioButton1,
            self.gui.visednevniPanel.vdRadioButton2,
            self.gui.visednevniPanel.vdRadioButton3,
            self.gui.visednevniPanel.vdRadioButton4]
        #inicijalno skrivanje upozorenja za prekoracenje temperature
        self.gui.koncPanel.change_criticalTemperatureWarningLabel(False)
        ###povezivanje akcija sa funkcijama###
        self.setup_veze()
        self.setup_radio_buttons([])
        logging.debug('Inicijalizacija kontrolora, kraj')

    def setup_veze(self):
        """
        Povezivanje emitiranih signala iz raznih dijelova aplikacije sa
        funkcijama koje definiraju tok programa.
        """
        ###ERROR I DRUGE PORUKE###
        self.connect(self.gui.restIzbornik,
                     QtCore.SIGNAL('prikazi_error_msg(PyQt_PyObject)'),
                     self.prikazi_error_msg)
        ###LOG IN REQUEST###
        self.connect(self.gui,
                     QtCore.SIGNAL('user_log_in(PyQt_PyObject)'),
                     self.user_log_in)
        ###LOG OUT REQUEST###
        self.connect(self.gui,
                     QtCore.SIGNAL('user_log_out'),
                     self.user_log_out)
        ###PROMJENA TABA U DISPLAYU###
        self.connect(self.gui,
                     QtCore.SIGNAL('promjena_aktivnog_taba(PyQt_PyObject)'),
                     self.promjena_aktivnog_taba)
        ###RECONNECT REQUEST###
        self.connect(self.gui,
                     QtCore.SIGNAL('reconnect_to_REST'),
                     self.reconnect_to_REST)
        ###GUMBI ZA PREBACIVANJE DANA NAPRIJED/NAZAD###
        self.connect(self.gui.koncPanel,
                     QtCore.SIGNAL('promjeni_datum(PyQt_PyObject)'),
                     self.promjeni_datum)
        ###PRIPREMA PODATAKA ZA CRTANJE (koncentracije)###
        self.connect(self.gui.restIzbornik,
                     QtCore.SIGNAL('priredi_podatke(PyQt_PyObject)'),
                     self.priredi_podatke)
        self.connect(self.gui.restIzbornik,
                     QtCore.SIGNAL('priredi_podatke(PyQt_PyObject)'),
                     self.gui.visednevniPanel.set_gKanal)
        ###MANUAL SAVE NA REST###
        self.connect(self.gui.koncPanel,
                     QtCore.SIGNAL('upload_minutne_na_REST_gumb'),
                     self.upload_minutne_na_REST_gumb)
        ###PROMJENA BROJA DANA U ZERO/SPAN PANELU###
        self.connect(self.gui.zsPanel,
                     QtCore.SIGNAL('update_zs_broj_dana(PyQt_PyObject)'),
                     self.update_zs_broj_dana)
        ###CRTANJE SATNOG GRAFA I INTERAKCIJA###
        #pick vremena sa satnog grafa - crtanje minutnog grafa za taj interval
        self.connect(self.gui.koncPanel.satniGraf,
                     QtCore.SIGNAL('crtaj_minutni_graf(PyQt_PyObject)'),
                     self.crtaj_minutni_graf)
        #promjena flaga na satnom grafu
        self.connect(self.gui.koncPanel.satniGraf,
                     QtCore.SIGNAL('promjeni_flag(PyQt_PyObject)'),
                     self.promjeni_flag)
        ###POVRATNA INFORMACIJA DOKUMENTA DA JE DOSLO DO PROMJENE FLAGA###
        self.connect(self.dokument,
                     QtCore.SIGNAL('model_flag_changed'),
                     self.crtaj_satni_graf)
        ###CRTANJE MINUTNOG GRAFA I INTERAKCIJA###
        #promjena flaga na minutnog grafu
        self.connect(self.gui.koncPanel.minutniGraf,
                     QtCore.SIGNAL('promjeni_flag(PyQt_PyObject)'),
                     self.promjeni_flag)
        ###CRTANJE ZERO/SPAN GRAFA I INTERAKCIJA###
        #setter podataka za tocku na zero grafu
        self.connect(self.gui.zsPanel.zeroGraf,
                     QtCore.SIGNAL('prikazi_info_zero(PyQt_PyObject)'),
                     self.gui.zsPanel.prikazi_info_zero)
        #pick tocke na zero grafu - nadji najblizu tocku na span grafu
        self.connect(self.gui.zsPanel.zeroGraf,
                     QtCore.SIGNAL('pick_nearest(PyQt_PyObject)'),
                     self.gui.zsPanel.spanGraf.pick_nearest)
        #setter podataka za tocku na span grafu
        self.connect(self.gui.zsPanel.spanGraf,
                     QtCore.SIGNAL('prikazi_info_span(PyQt_PyObject)'),
                     self.gui.zsPanel.prikazi_info_span)
        #pick tocke na span grafu - nadji najblizu tocku na zero grafu
        self.connect(self.gui.zsPanel.spanGraf,
                     QtCore.SIGNAL('pick_nearest(PyQt_PyObject)'),
                     self.gui.zsPanel.zeroGraf.pick_nearest)
        ###CRTANJE SATNO AGREGIRANIH PODATAKA SA RESTA###
        self.connect(self.gui.visednevniPanel,
                     QtCore.SIGNAL('nacrtaj_rest_satne(PyQt_PyObject)'),
                     self.nacrtaj_rest_satne)
        ###DODAVANJE NOVE ZERO ILI SPAN REFERENTNE VRIJEDNOSTI###
        self.connect(self.gui.zsPanel,
                     QtCore.SIGNAL('dodaj_novu_referentnu_vrijednost'),
                     self.dodaj_novu_referentnu_vrijednost)
        ###PROMJENA IZGLEDA GRAFA###
        self.connect(self.gui,
                     QtCore.SIGNAL('apply_promjena_izgleda_grafova'),
                     self.apply_promjena_izgleda_grafova)
        ###GUMB NA KONCENTRACIJSKOM PANELU ZA PONISTAVANJE IZMJENA###
        self.connect(self.gui.koncPanel,
                     QtCore.SIGNAL('ponisti_izmjene'),
                     self.ponisti_izmjene)
        ###UPDATE LABELA NA KONCENTRACIJSKOM PANELU###
        self.connect(self.gui.koncPanel.satniGraf,
                     QtCore.SIGNAL('set_labele_satne_tocke(PyQt_PyObject)'),
                     self.gui.koncPanel.set_labele_satne_tocke)
        self.connect(self.gui.koncPanel.minutniGraf,
                     QtCore.SIGNAL('set_labele_minutne_tocke(PyQt_PyObject)'),
                     self.gui.koncPanel.set_labele_minutne_tocke)
        ###UPDATE LABELA ZA SATNU REST TOCKU###
        self.connect(self.gui.visednevniPanel.satniRest,
                     QtCore.SIGNAL('set_labele_rest_satne_tocke(PyQt_PyObject)'),
                     self.gui.visednevniPanel.prikazi_info_satni_rest)
        ###PROMJENA MAX BORJA DANA ZA SATNI GRAF###
        self.connect(self.gui.koncPanel,
                     QtCore.SIGNAL('promjeni_max_broj_dana_satnog(PyQt_PyObject)'),
                     self.promjeni_max_broj_dana_satnog)
        ###PROMJENA MAX BROJA SATI ZA MINUTNI GRAF###
        self.connect(self.gui.koncPanel,
                     QtCore.SIGNAL('promjeni_max_broj_sati_minutnog(PyQt_PyObject)'),
                     self.promjeni_max_broj_sati_minutnog)
        ###MINUTNI STATUS BIT INFO###
        self.connect(self.gui.koncPanel,
                     QtCore.SIGNAL('get_minutni_fault_info(PyQt_PyObject)'),
                     self.prikazi_info_statusa_podatka)
        ###refresh ZERO / SPAN panela###
        self.connect(self.gui.zsPanel,
                     QtCore.SIGNAL('refresh_zs_panela'),
                     self.refresh_zero_span_panela)
        ###DODAVANJE KOMENTARA###
        self.connect(self.gui.koncPanel.satniGraf,
                     QtCore.SIGNAL('dodaj_novi_komentar(PyQt_PyObject)'),
                     self.dodaj_novi_komentar)
        self.connect(self.gui.koncPanel.minutniGraf,
                     QtCore.SIGNAL('dodaj_novi_komentar(PyQt_PyObject)'),
                     self.dodaj_novi_komentar)
        ### update komentara za postaju (svi kanali, klik na postaju a ne na neki uredjaj) ####
        self.connect(self.gui.restIzbornik,
                     QtCore.SIGNAL('prikazi_komentare_za_stanicu(PyQt_PyObject)'),
                     self.get_sve_komentare_postaje)
        ### TODO! zero span - span selection linear fit###
        #connect reset_graf signal - refresh cijeli panel
        self.connect(self.gui.zsPanel.zeroGraf,
                     QtCore.SIGNAL('reset_zs_graf'),
                     self.refresh_zero_span_panela)
        self.connect(self.gui.zsPanel.spanGraf,
                     QtCore.SIGNAL('reset_zs_graf'),
                     self.refresh_zero_span_panela)
        #TODO! connect zero mora crtati span i obrnuto
        self.connect(self.gui.zsPanel.zeroGraf,
                     QtCore.SIGNAL('plot_linear_fit_line(PyQt_PyObject)'),
                     self.gui.zsPanel.spanGraf.plot_linear_fit_pravac)
        self.connect(self.gui.zsPanel.spanGraf,
                     QtCore.SIGNAL('plot_linear_fit_line(PyQt_PyObject)'),
                     self.gui.zsPanel.zeroGraf.plot_linear_fit_pravac)
        #TODO! zero span intercept update
        self.connect(self.gui.zsPanel.zeroGraf,
                     QtCore.SIGNAL('update_ocekivani_fail(PyQt_PyObject)'),
                     self.update_prekoracenje_zero)
        self.connect(self.gui.zsPanel.spanGraf,
                     QtCore.SIGNAL('update_ocekivani_fail(PyQt_PyObject)'),
                     self.update_prekoracenje_span)
        ###concentration radio buttons###
        for i in range(len(self.koncRadioButtons)):
            button = self.koncRadioButtons[i]
            zsbutton = self.zsRadioButtons[i]
            vdbutton = self.vdRadioButtons[i]
            button.clicked.connect(partial(self.toggle_konc_radio, ind=i))
            zsbutton.clicked.connect(partial(self.toggle_konc_radio, ind=i))
            vdbutton.clicked.connect(partial(self.toggle_konc_radio, ind=i))

    def update_prekoracenje_span(self, x):
        """update label sa vremenom ocekivanog prekoracenja span vrijednosti"""
        #TODO! display panel sa prekoracenjima
        self.gui.zsPanel.groupBoxPrekoracenje.setVisible(True)
        self.gui.zsPanel.labelPrekoracenjeSpan.setText(str(x))

    def update_prekoracenje_zero(self, x):
        """update label sa vremenom ocekivanog prekoracenja zero vrijednosti"""
        #TODO! display panel sa prekoracenjima
        self.gui.zsPanel.groupBoxPrekoracenje.setVisible(True)
        self.gui.zsPanel.labelPrekoracenjeZero.setText(str(x))

    def get_sve_komentare_postaje(self, postaja):
        """
        metoda dohvaca sve komentare sa postaje

        postaja - string naziv postaje
        """
        outFrejm = pd.DataFrame(columns=['Kanal', 'Od', 'Do', 'Komentar'])
        kanaliNaPostaji = set(self.pronadji_sve_kanale_na_postaji(postaja))
        for i in kanaliNaPostaji:
            jString = self.webZahtjev.dohvati_sve_komentare_za_id(i)

            frejm = pd.read_json(jString, convert_dates=['kraj', 'pocetak'])

            if len(frejm):
                frejm.rename(columns={'kraj': 'Do', 'pocetak': 'Od', 'tekst':'Komentar', 'programMjerenjaId':'Kanal'}, inplace=True)
                frejm.drop('id', axis=1, inplace=True)

                #merge result with outFrejm
                outFrejm = outFrejm.append(frejm, ignore_index=True)

        self.gui.komentariPanel.set_frejm_u_model(outFrejm)
        if len(outFrejm):
            #set new frejm to model komentara
            self.gui.komentariPanel.set_frejm_u_model(outFrejm)
            #update visual hint
            self.gui.tabWidget.tabBar().setTabTextColor(3, QtCore.Qt.green)
            self.gui.tabWidget.tabBar().setTabIcon(3, QtGui.QIcon('./app/view/icons/hazard5.png'))
        else:
            self.gui.komentariPanel.set_frejm_u_model(outFrejm)
            #update visual hint
            self.gui.tabWidget.tabBar().setTabTextColor(3, QtCore.Qt.black)
            self.gui.tabWidget.tabBar().setTabIcon(3, QtGui.QIcon())

    def get_bitne_komentare(self, programMjerenjaId, pocetak, kraj):
        """
        metoda dohvaca sve komentare za zadani programMjerenjaId i neki vremenski
        raspon.

        programMjerenjaId - integer, glavni kanal
        pocetak - pandas timestamp
        kraj - pandas timestamp

        output je dobro formatirani pandas datafrejm sa podacima
        """
        # prosiri granice vremena za 7 dana... malo sira slika
        start = pocetak - datetime.timedelta(days=7)
        end = kraj + datetime.timedelta(days=7)
        jString = self.webZahtjev.dohvati_komentare_za_id_start_kraj(programMjerenjaId, start, end)
        frejm = pd.read_json(jString, convert_dates=['kraj', 'pocetak'])
        if len(frejm):
            #adapt frejm -- stupci [Od, Do, Kanal, Komentar]
            frejm.rename(columns={'kraj': 'Do', 'pocetak': 'Od', 'tekst':'Komentar', 'programMjerenjaId':'Kanal'}, inplace=True)
            frejm.drop('id', axis=1, inplace=True)
            #set new frejm to model komentara
            self.gui.komentariPanel.set_frejm_u_model(frejm) #TODO! bugs possible
            #update visual hint
            self.gui.tabWidget.tabBar().setTabTextColor(3, QtCore.Qt.green)
            self.gui.tabWidget.tabBar().setTabIcon(3, QtGui.QIcon('./app/view/icons/hazard5.png'))
        else:
            #sklepaj prazan frejm i postavi ga u model
            frejm = pd.DataFrame(columns=['Kanal', 'Od', 'Do', 'Komentar'])
            self.gui.komentariPanel.set_frejm_u_model(frejm)
            #update visual hint
            self.gui.tabWidget.tabBar().setTabTextColor(3, QtCore.Qt.black)
            self.gui.tabWidget.tabBar().setTabIcon(3, QtGui.QIcon())

    def pronadji_sve_kanale_na_postaji(self, postaja):
        """metoda vraca listu svih kanala na postaji (lista integera)"""
        output = []
        #search by string naziv ili id postaje
        if isinstance(postaja, str):
            searchKey = 'postajaNaziv'
        else:
            searchKey = 'postajaId'
        for key in self.mapaMjerenjeIdToOpis:
            if self.mapaMjerenjeIdToOpis[key][searchKey] == postaja:
                output.append(key)
        return output

    def dodaj_novi_komentar(self, mapa):
        """
        Dodavanje novog komentara u frejm sa komentarima.
        mapa ima kljuceve ['od', 'do', 'kanal', 'tekst', 'spremiSvima']
        "od", "do" su pandas timestampovi
        "kanal" je int
        "tekst" je string
        "spremiSvima" je boolean
        """
        #promjeni cursor u wait cursor
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        #format values
        od = mapa['od'].value / 1000000
        do = mapa['do'].value / 1000000
        tekst = str(mapa['tekst'])
        kanal = int(mapa['kanal'])
        spremiSvimaNaPostaji = bool(mapa['dodajSvima'])

        if spremiSvimaNaPostaji:
            #nadji sve kanale na postaji
            postaja = self.mapaMjerenjeIdToOpis[kanal]['postajaId']
            popisKanala = self.pronadji_sve_kanale_na_postaji(postaja)
        else:
            #samo povezani kanali
            popisKanala = self.mapaMjerenjeIdToOpis[kanal]['povezaniKanali']

        for kanalId in popisKanala:
            data = {"pocetak":od, "kraj":do, "programMjerenjaId":kanalId, "tekst":tekst}
            jString = json.dumps(data)
            #push komentar na REST
            check = self.webZahtjev.put_komentar_na_rest(jString)
            #report fail
            if not check:
                msg = "Komentar nije uspjesno spremljen \n{0}".format(str(jString))
                QtGui.QMessageBox.information(self.gui, 'Pogreska prilikom spremanja komentara', msg)

        #update komentare
        #XXX!
        try:
            self.get_bitne_komentare(self.gKanal, self.pocetnoVrijeme, self.zavrsnoVrijeme)
        except Exception as err:
            #expected fail.. ako vrijeme i/ili kanal nije izabran
            msg = 'ocekivani problem sa updateom komentara kanal:{0}, pocetak:{1}, kraj:{2}'.format(str(self.gKanal), str(self.pocetnoVrijeme), str(self.zavrsnoVrijeme))
            logging.info(msg)
            logging.info(str(err), exc_info=True)

        #promjeni cursor u normalni cursor
        QtGui.QApplication.restoreOverrideCursor()



    def toggle_konc_radio(self, ind=0):
        """
        ponovno crtanje grafa i update labela...
        """
        try:
            logging.debug('toggle radio gumba na poziciji ind={0}'.format(str(ind)))
            kanal = self.mapaMjerenjeIdToOpis[self.gKanal]['povezaniKanali'][ind]
            self.gKanal = kanal
            self.zadnjiPovezaniKanal = kanal
            self.drawStatus = [False, False]
            argMap = {'opis': self.mapaMjerenjeIdToOpis[self.gKanal],
                      'datum': self.pickedDate,
                      'mjerenjeId': self.gKanal}
            msg = 'Promjena labela na panelima, argumenti={0}'.format(str(argMap))
            logging.debug(msg)
            self.gui.koncPanel.change_glavniLabel(argMap)
            self.gui.zsPanel.change_glavniLabel(argMap)
            self.gui.visednevniPanel.change_glavniLabel(argMap)
            #mirror click na drugoj radio skupini
            if not self.koncRadioButtons[ind].isChecked():
                self.koncRadioButtons[ind].blockSignals(True)
                self.koncRadioButtons[ind].setChecked(True)
                self.koncRadioButtons[ind].blockSignals(False)
            if not self.zsRadioButtons[ind].isChecked():
                self.zsRadioButtons[ind].blockSignals(True)
                self.zsRadioButtons[ind].setChecked(True)
                self.zsRadioButtons[ind].blockSignals(False)
            if not self.vdRadioButtons[ind].isChecked():
                self.vdRadioButtons[ind].blockSignals(True)
                self.vdRadioButtons[ind].setChecked(True)
                self.vdRadioButtons[ind].blockSignals(False)
            self.promjena_aktivnog_taba(self.aktivniTab)
        except Exception as err:
            logging.error(str(err), exc_info=True)

    def refresh_zero_span_panela(self):
        self.crtaj_zero_span()
        #TODO! hide panel sa prekoracenjima
        self.gui.zsPanel.groupBoxPrekoracenje.setVisible(False)
        if hasattr(self, 'webZahtjev'):
            referentni = self.get_tablice_zero_span_referentnih_vrijednosti()
            self.gui.zsPanel.update_zero_span_referentne_vrijednosti(referentni)
        self.drawStatus[1] = True

    def prikazi_info_statusa_podatka(self, arg):
        """
        display informacijskog dijaloga sa opisom statusa minutnog podatka
        """
        podatak = arg['id']
        status = arg['statusString']
        response = self.webZahtjev.dohvati_status_info_za_podatak(podatak, status)
        opisi = json.loads(response)
        title = 'Opis statusa minutnog podatka'
        if len(opisi.keys()) == 0:
            output = "Opis ne postoji."
            QtGui.QMessageBox.information(self.gui, title, output)
        else:
            tekst = [" ".join([str(key) ,str(opisi[key])]) for key in opisi]
            output = "\n".join(tekst)
            QtGui.QMessageBox.information(self.gui, title, output)

    def prikazi_error_msg(self, poruka):
        """
        Prikaz informacijskog dijaloga nakon neke greske
        """
        #vrati izgled cursora nazad na "normalni" (bitno zbog exceptiona)
        QtGui.QApplication.restoreOverrideCursor()
        #prikazi information dialog sa pogreskom
        QtGui.QMessageBox.information(self.gui, 'Pogreska prilikom rada', str(poruka))

    def user_log_in(self, x):
        """
        - postavi podatke u self.appAuth
        - reinitialize connection objekt i sve objekte koji ovise o njemu.
        """
        logging.info('Request user_log_in, start')
        self.appAuth = x
        # spoji se na rest
        self.reconnect_to_REST()
        logging.info('Request user_log_in, kraj')

    def provjeri_temperature_kontejnera_u_zadnjih_24_sata(self):
        """
        Ideja je proći kroz sve moguće kanale, pronaći sve koji imaju formulu "Tkont",
        ucitati podatke od "sada"-24 sata do "sada" te provjeriti da li postoje vrijednosti
        iznad 30 i ispod 15. U slučaju da ima, cijela postaja mora imati warning za
        prekoračenje.
        """
        outmapa = {} #link Tkont : ostali kanali na postaji
        pomocni = {} #link postajaId : programMjerenja
        #pass 1 .. postavimo sve ključeve gdje je komponenta temperatura kontejnera
        for programMjerenja in self.mapaMjerenjeIdToOpis:
            if self.mapaMjerenjeIdToOpis[programMjerenja]['komponentaFormula'] == 'Tkont':
                outmapa[programMjerenja] = []
                pomocni[self.mapaMjerenjeIdToOpis[programMjerenja]['postajaNaziv']] = programMjerenja
        #pass 2 ... dodavanje svih ostalih na istoj postaji...
        for programMjerenja in self.mapaMjerenjeIdToOpis:
            if programMjerenja not in outmapa.keys():
                postaja = self.mapaMjerenjeIdToOpis[programMjerenja]['postajaNaziv']
                kljuc = pomocni.get(postaja, None)
                if kljuc:
                    outmapa[kljuc].append(programMjerenja)
        #pass 3 ... ucitavanje svih temperatura kontejnera
        self.criticalTemperatureWarningMap = {}
        #key pojedinog kanala : False(prikazi warning), True(sve je ok, sakrij warning)
        datum = str(datetime.datetime.now().date())
        for key, values in outmapa.items():
            #test za zadnja 2 dana unutar raspona [15-30]
            check = self.webZahtjev.test_unutar_granica(key, datum, 2, 15.0, 30.0)
            self.criticalTemperatureWarningMap[key] = check
            for k in values:
                self.criticalTemperatureWarningMap[k] = check

    def reconnect_to_REST(self):
        """
        inicijalizacija objekata vezanih za interakciju sa REST servisom
        -webZahtjev()
        -dataReader()
        -dataWriter()
        """
        logging.debug('reconnect_to_REST, start')
        # promjeni cursor u wait cursor
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        #inicijalizacija objekata
        self.initialize_web_and_rest_interface(True)
        #konstruiraj tree model programa mjerenja
        self.konstruiraj_tree_model()
        #postavi tree model u ciljani tree view widget na display
        if self.modelProgramaMjerenja == None or self.statusMap == None:
            logging.info('LogIn problem, self.modelProgramaMjerenja ili self.statusMap su None')
            self.gui.action_log_in.setEnabled(True)
            logging.info('action_log_in enabled')
            self.gui.action_log_out.setEnabled(False)
            logging.info('action_log_out disabled')
            msg = 'Krivi REST url, login ili password.\n Spajanje sa REST servisom nije moguce'
            self.prikazi_error_msg(msg)
        else:
            self.gui.restIzbornik.treeView.setModel(self.modelProgramaMjerenja)
            self.gui.restIzbornik.model = self.modelProgramaMjerenja
            logging.debug('Tree model programa mjerenja uspjesno postavljen u rest izbornik')
            self.gui.action_log_in.setEnabled(False)
            logging.info('action_log_in disabled')
            self.gui.action_log_out.setEnabled(True)
            logging.info('action_log_out enabled')
        #vrati izgled cursora nazad na normalni

        #TODO! testing za probleme sa temperaturom kontejnera
        self.provjeri_temperature_kontejnera_u_zadnjih_24_sata()

        QtGui.QApplication.restoreOverrideCursor()
        logging.debug('reconnect_to_REST, kraj')

    def initialize_web_and_rest_interface(self, tip):
        """
        Inicijalizacija web zahtjeva i REST reader/writer objekata koji ovise o
        njemu.
        Takodjer dohvati i mapu status codea  i postavi je u minutni i satni kanvas
        Tip je boolean vrijednost... True za log in, False za log out
        """
        logging.debug('inicijalizacija rest interface, start')
        # dohvati podatke o rest servisu
        baseurl = str(self.gui.konfiguracija.REST.RESTBaseUrl)
        resursi = {'siroviPodaci': str(self.gui.konfiguracija.REST.RESTSiroviPodaci),
                   'programMjerenja': str(self.gui.konfiguracija.REST.RESTProgramMjerenja),
                   'zerospan': str(self.gui.konfiguracija.REST.RESTZeroSpan),
                   'satniPodaci': str(self.gui.konfiguracija.REST.RESTSatniPodaci),
                   'statusMap': str(self.gui.konfiguracija.REST.RESTStatusMap),
                   'komentari':str(self.gui.konfiguracija.REST.RESTkomentari)}
        msg = 'base url={0}\nresursi={1}'.format(baseurl, str(resursi))
        logging.debug(msg)
        # inicijalizacija webZahtjeva
        self.webZahtjev = networking_funkcije.WebZahtjev(baseurl, resursi, self.appAuth)
        self.satniAgregator.set_webrequest(self.webZahtjev)
        logging.debug('webZahtjev inicijaliziran')
        #inicijalizacija REST readera
        self.restReader = data_reader.RESTReader(source=self.webZahtjev)
        logging.debug('rest reader inicijaliziran')
        #postavljanje readera u model
        self.dokument.set_reader(self.restReader)
        logging.debug('rest reader postavljen u dokument')
        #inicijalizacija REST writera agregiranih podataka
        self.restWriter = data_reader.RESTWriter(source=self.webZahtjev)
        logging.debug('rest writer agregiranih podataka inicijaliziran')
        #postavljanje writera u model
        self.dokument.set_writer(self.restWriter)
        logging.debug('rest writer postavljen u dokument')
        if tip:
            #login slucaj, funkcija pozvana sa True
            statusMapa = self.webZahtjev.get_statusMap()
            if statusMapa != {}:
                self.statusMap = statusMapa
                self.gui.koncPanel.satniGraf.set_statusMap(statusMapa)
                self.gui.koncPanel.minutniGraf.set_statusMap(statusMapa)
                self.gui.visednevniPanel.satniRest.set_statusMap(statusMapa)
                logging.info('status mapa postavljena za satni, minutni i satniRest graf')
            else:
                self.statusMap = None
                logging.info('Pristup mapi sa satatusima nije moguc. Tretiraj kao neuspjesni login.')
                msg = 'Pristup mapi sa statusima nije moguc.'
                self.prikazi_error_msg(msg)
        else:
            #logout slucaj, funkcija pozvana sa False
            logging.debug('Logout, prazan dictionary postavljen u self.statusMap')
            self.statusMap = None
            self.gui.action_log_in.setEnabled(True)
            logging.info('action_log_in enabled')
            self.gui.action_log_out.setEnabled(False)
            logging.info('action_log_out disabled')
        logging.debug('Inicijalizacija rest interface, kraj')

    def konstruiraj_tree_model(self):
        """
        Povuci sa REST servisa sve programe mjerenja
        Pokusaj sastaviti model, tree strukturu programa mjerenja
        """
        logging.debug('Konstuiraj_tree_model, start.')
        mapa = self.webZahtjev.get_programe_mjerenja()
        self.mapaMjerenjeIdToOpis = mapa
        #clear sve pomocne grafove (popis kanala nije nuzno isti pa se moraju rekonstuirati defaultni pomocni grafovi)
        self.gui.konfiguracija.reset_pomocne(self.mapaMjerenjeIdToOpis)
        #clear sve povezane grafove
        self.gui.konfiguracija.reset_povezane(self.mapaMjerenjeIdToOpis)

        #sredjivanje povezanih kanala (NOx grupa i PM grupa)
        for kanal in self.mapaMjerenjeIdToOpis:
            pomocni = self.nadji_default_pomocne_za_kanal(kanal)
            for i in pomocni:
                self.mapaMjerenjeIdToOpis[kanal]['povezaniKanali'].append(i)
                #dodavanje povezanih grafova u konfig... za sada random line
                if i != kanal:
                    naziv = self.mapaMjerenjeIdToOpis[i]['komponentaFormula']
                    self.gui.konfiguracija.dodaj_random_povezani(kanal, i, naziv)
            #sortiraj povezane kanale, predak je bitan zbog radio buttona
            lista = self.mapaMjerenjeIdToOpis[kanal]['povezaniKanali']
            lista = sorted(lista)
            self.mapaMjerenjeIdToOpis[kanal]['povezaniKanali'] = lista

        #root objekt za tree strukturu.
        tree = model_drva.TreeItem(['stanice', None, None, None], parent=None)
        #za svaku individualnu stanicu napravi TreeItem objekt, reference objekta spremi u dict
        stanice = []
        for i in sorted(list(mapa.keys())):
            stanica = mapa[i]['postajaNaziv']
            if stanica not in stanice:
                stanice.append(stanica)
        stanice = sorted(stanice)
        postaje = [model_drva.TreeItem([name, None, None, None], parent=tree) for name in stanice]
        strPostaje = [str(i) for i in postaje]
        skipMeList = [] #popis kanala koje treba preskociti za tree model
        for i in self.mapaMjerenjeIdToOpis:
            if i in skipMeList:
                continue
            else:
                #konstrukcija tree modela
                listaPovezanihKanala = self.mapaMjerenjeIdToOpis[i]['povezaniKanali']
                if len(listaPovezanihKanala) > 1:
                    #update kanala koje treba preskociti u konstrukciji tree modela
                    for k in listaPovezanihKanala:
                        skipMeList.append(k)
                    formula = self.mapaMjerenjeIdToOpis[i]['komponentaFormula']
                    tmpLista = [self.mapaMjerenjeIdToOpis[x]['komponentaFormula'] for x in listaPovezanihKanala]
                    #grupacija PM i NOx
                    if formula in ['NO', 'NO2', 'NOx']:
                        komponenta = 'Dusikovi oksidi'
                        indeks = listaPovezanihKanala[tmpLista.index('NO')]
                    elif formula in ['PM1', 'PM2.5', 'PM10']:
                        komponenta = 'PM'
                        try:
                            indeks = listaPovezanihKanala[tmpLista.index('PM1')]
                        except Exception:
                            indeks = i
                else:
                    indeks = i
                    komponenta = self.mapaMjerenjeIdToOpis[indeks]['komponentaNaziv']

                stanica = self.mapaMjerenjeIdToOpis[indeks]['postajaNaziv']  #parent = stanice[stanica]
                formula = self.mapaMjerenjeIdToOpis[indeks]['komponentaFormula']
                mjernaJedinica = self.mapaMjerenjeIdToOpis[indeks]['komponentaMjernaJedinica']
                opis = " ".join([formula, '[', mjernaJedinica, ']'])
                usporedno = self.mapaMjerenjeIdToOpis[indeks]['usporednoMjerenje']

                data = [komponenta, usporedno, indeks, opis]
                redniBrojPostaje = strPostaje.index(stanica)
                #kreacija TreeItem objekta
                model_drva.TreeItem(data, parent=postaje[redniBrojPostaje])
        #napravi model
        self.modelProgramaMjerenja = model_drva.ModelDrva(tree)
        logging.debug('konstuiraj_tree_model, kraj.')

    def nadji_default_pomocne_za_kanal(self, kanal):
        """
        Za zadani kanal, ako je formula kanala unutar nekog od setova,
        vrati sve druge kanale na istoj postaji koji takodjer pripadaju istom
        setu.

        npr. ako je izabrani kanal Desinic NO, funkcija vraca id mjerenja za
        NO2 i NOx sa Desinica (ako postoje)
        """
        msg = 'nadji_default_pomocne_za_kanal id={0}, start'.format(str(kanal))
        logging.debug(msg)
        setovi = [('NOx', 'NO', 'NO2'), ('PM10', 'PM1', 'PM2.5')]
        output = set()
        postaja = self.mapaMjerenjeIdToOpis[kanal]['postajaId']
        formula = self.mapaMjerenjeIdToOpis[kanal]['komponentaFormula']
        usporednoMjerenje = self.mapaMjerenjeIdToOpis[kanal]['usporednoMjerenje']
        ciljaniSet = None
        for kombinacija in setovi:
            if formula in kombinacija:
                ciljaniSet = kombinacija
                break
        if ciljaniSet == None:
            msg = 'Trenutni kanal ne pripada niti jednoj skupini, output set={0}'.format(str(output))
            logging.debug(msg)
            return output
        for programMjerenja in self.mapaMjerenjeIdToOpis:
            if self.mapaMjerenjeIdToOpis[programMjerenja]['postajaId'] == postaja and programMjerenja != kanal:
                if self.mapaMjerenjeIdToOpis[programMjerenja]['komponentaFormula'] in ciljaniSet:
                    if self.mapaMjerenjeIdToOpis[programMjerenja]['usporednoMjerenje'] == usporednoMjerenje: #usporedno mjerenje se mora poklapati...
                        output.add(programMjerenja)
        msg = 'output set srodnih kanala set={0}'.format(str(output))
        logging.debug(msg)
        msg = 'nadji_default_pomocne_za_kanal id={0}, kraj'.format(str(kanal))
        logging.debug(msg)
        return output

    def user_log_out(self):
        """
        - clear self.appAuth
        - reinitialize connection objekt i sve objekte koji ovise o njemu.
        - mankuti tree view
        - clear grafove
        """
        logging.info('Request user_log_out, start')
        #clear auth information
        self.appAuth = ("", "")
        #reset webZahtjev, dokumnet....
        self.initialize_web_and_rest_interface(False)
        #reset tree view model... prikazi nista.
        tree = model_drva.TreeItem(['stanice', None, None, None], parent=None)
        self.modelProgramaMjerenja = model_drva.ModelDrva(tree)
        #set model to views
        self.gui.restIzbornik.treeView.setModel(self.modelProgramaMjerenja)
        self.gui.restIzbornik.model = self.modelProgramaMjerenja
        logging.debug('Tree model programa mjerenja, cleared')
        #clear kalendar u restIzbornik
        dummy = {'ok':[], 'bad':[]}
        self.gui.restIzbornik.calendarWidget.refresh_dates(dummy)
        logging.debug('Boje kalendara cleared')
        #clear glavni kanal i datum, clear sve grafove
        self.gKanal = None
        self.zadnjiPovezaniKanal = None
        self.pickedDate = None
        logging.debug('Glavni kanal i trenutno izabrani datum, cleared')
        self.gui.koncPanel.satniGraf.clear_graf()
        self.gui.koncPanel.minutniGraf.clear_graf()
        self.gui.zsPanel.zeroGraf.clear_graf()
        self.gui.zsPanel.spanGraf.clear_graf()
        self.gui.visednevniPanel.satniRest.clear_graf()
        logging.debug('Grafovi cleared')
        #clear tablice
        clmap = {}
        self.gui.koncPanel.satnoAgregiraniModel.set_data(clmap)
        self.gui.koncPanel.satnoAgregiraniView.update()
        self.gui.koncPanel.minutniModel.set_data(clmap)
        self.gui.koncPanel.minutniView.update()
        self.gui.visednevniPanel.restAgregiraniModel.set_data(clmap)
        self.gui.visednevniPanel.restAgregiraniView.update()
        self.gui.zsPanel.zerospanRefTableModel.clear_frejm()
        #clear radio buttons
        self.setup_radio_buttons([])
        #clear tab sa tabovima
        self.gui.komentariPanel.clear_tab_komentara()
        logging.info('Request user_log_out, kraj.')

    def priredi_podatke(self, mapa):
        """
        Metoda analizira zahtjev za crtanjem preuzet u obliku mape
        {'programMjerenjaId':int, 'datumString':'YYYY-MM-DD'}

        Metoda delegira operativne dijelove drugim metodama radi povecanja
        citljivosti.

        red akcija:
        1. prompt za save (upload na REST) aktivnih podataka (trenutno nacrtanih)
        2. reinicijalizacija membera bitnih za crtanje
            -postavlja se novi glavni kanal i izabrani datum....
        3. ucitavanje podataka sa REST-a
        4. promjena labela na dijelovima GUI-a
            -naslovi grafova isl.
        5. pokretanje naredbi za crtanjem
        """
        msg = 'Metoda priredi_podatke, start. Ulazni parametar mapa={0}'.format(str(mapa))
        logging.info(msg)
        #naredba za prompr savea MORA biti prva u nizu prije nego se postave
        #novi memberi za kanal i izabrani datum.
        self.upload_minutne_na_REST_prompt()
        #prebaci u wait cursor
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        # reinicijalizacija membera (self.gKanal, self.pocetnoVrijeme....)
        self.pripremi_membere_prije_ucitavanja_zahtjeva(mapa)
        #ucitavanje podataka ako prije nisu ucitani (ako nisu u cacheu zahtjeva)
        self.ucitaj_podatke_ako_nisu_prije_ucitani()
        #update komentara za kanal i vremensko razdoblje
        #XXX! broken line...
        try:
            self.get_bitne_komentare(self.gKanal, self.pocetnoVrijeme, self.zavrsnoVrijeme)
        except Exception as err:
            #expected fail.. ako vrijeme i/ili kanal nije izabran
            msg = 'ocekivani problem sa updateom komentara kanal:{0}, pocetak:{1}, kraj:{2}'.format(str(self.gKanal), str(self.pocetnoVrijeme), str(self.zavrsnoVrijeme))
            logging.info(msg)
            logging.info(str(err), exc_info=True)
        #restore cursor u normalni
        QtGui.QApplication.restoreOverrideCursor()
        #pokusaj izabrati prethodno aktivni kanal, ili prvi moguci u slucaju pogreske
        lista = self.mapaMjerenjeIdToOpis[self.gKanal]['povezaniKanali']
        formule = [self.mapaMjerenjeIdToOpis[x]['komponentaFormula'] for x in lista]
        try:
            loc = lista.index(self.zadnjiPovezaniKanal)
            self.koncRadioButtons[loc].setChecked(True)
            self.zsRadioButtons[loc].setChecked(True)
            self.vdRadioButtons[loc].setChecked(True)
            self.koncRadioButtons[loc].clicked.emit(True)
        except Exception:
            if 'NO' in formule:
                loc = formule.index('NO')
            elif 'PM1' in formule:
                loc = formule.index('PM1')
            else:
                loc = 0 #izbor prvog
            self.koncRadioButtons[loc].setChecked(True)
            self.zsRadioButtons[loc].setChecked(True)
            self.vdRadioButtons[loc].setChecked(True)
            self.koncRadioButtons[loc].clicked.emit(True)

        #XXX! dio za provjeru warninga opsega temperature
        #TODO! self.outmapa2... indikator za flagging
        #u mapi sa podacima za warning, False znaci da warning postoji, True znaci da je sve OK
        #gui display radi obrnuto.. zato imamo "not" da okrene stvari na gui pogled
        showWarning = self.criticalTemperatureWarningMap.get(self.gKanal, False)
        self.gui.koncPanel.change_criticalTemperatureWarningLabel(not showWarning)

        logging.info('Metoda priredi_podatke, kraj.')

    def ponisti_izmjene(self):
        """
        Funkcija ponovno ucitava podatke sa REST servisa i poziva na ponovno crtanje
        trenutno aktivnog kanala za trenutno izabrani datum.

        P.S. funkcija je skoro identicna metodi self.pripremi_podatke i radi na
        istom principu, ali NE pokrece save podataka kao prvi korak.
        """
        logging.info('Metoda ponisti_izmjene, start.')
        #test da li podatak postoji...
        if self.gKanal is not None and self.pickedDate is not None:
            mapa = {'programMjerenjaId': self.gKanal,
                    'datumString': self.pickedDate}

            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.pripremi_membere_prije_ucitavanja_zahtjeva(mapa)
            self.ucitaj_podatke_ako_nisu_prije_ucitani()
            QtGui.QApplication.restoreOverrideCursor()
            argMap = {'opis': self.mapaMjerenjeIdToOpis[self.gKanal],
                      'datum': self.pickedDate,
                      'mjerenjeId': self.gKanal}
            msg = 'Promjena labela na panelima, argumenti={0}'.format(str(argMap))
            logging.debug(msg)
            self.gui.koncPanel.change_glavniLabel(argMap)
            self.gui.zsPanel.change_glavniLabel(argMap)
            self.gui.visednevniPanel.change_glavniLabel(argMap)
            self.promjena_aktivnog_taba(self.aktivniTab)
        logging.info('Metoda ponisti_izmjene, kraj.')

    def upload_minutne_na_REST_prompt(self):
        """
        automatska metoda za spremanje minutnih podataka na REST.
        - pita za potvrdu spremanja na REST samo ako postoje podaci koji nisu validirani

        -u slucaju povezanih kanala, testira se samo glavni kanal...
        """
        logging.info('Metoda upload_minutne_na_REST_prompt, start')
        #check da ne radi probleme sa datumima u buducnosti ili sa nepostojecim datumima
        datum = QtCore.QDate().fromString(self.pickedDate, 'yyyy-MM-dd')
        danas = QtCore.QDate.currentDate()
        logging.debug('upload_minutne_na_rest, provjera stanja membera')
        msg = 'trenutno stanje bitnih membera. self.gKanal={0}, self.pickedDate={1}'.format(str(self.gKanal), str(self.pickedDate))
        logging.debug(msg)
        #izabrani datum i kanal moraju biti razliciti od None te datum ne smije biti u buducnosti
        if (self.gKanal != None) and (self.pickedDate != None) and (datum < danas):
            #ako kljuc ne postoji u ucitanim podacima samo izadji (nema podataka)
            if self.gKanal not in self.dokument.data:
                msg = 'U dokumentu (mapa dokument.data) ne postoji kljuc, key={0}. Return None'.format(str(self.gKanal))
                logging.debug(msg)
                return None
            frejm = self.dokument.data[self.gKanal]
            msg = 'Frejm podataka koji treba spremiti:\n{0}'.format(str(frejm))
            logging.debug(msg)
            lenSvih = len(frejm)
            msg = 'broj podataka : {0}'.format(str(lenSvih))
            logging.debug(msg)
            validirani = frejm[abs(frejm['flag']) == 1000]
            lenValidiranih = len(validirani)
            msg = 'broj validiranih : {0}'.format(str(lenValidiranih))
            logging.debug(msg)
            msg = 'stanje dokumenta (dirty, da li je korisnik mjenjao flag) : {0}'.format(str(self.dokument.is_dirty()))
            logging.debug(msg)
            if lenSvih != lenValidiranih or self.dokument.is_dirty():
                # prompt izbora za spremanje filea, question
                logging.debug('Dokuemnt je dirty ili postoje podaci koji nisu validirani. Prikazi prompt za save.')
                msg = "spremi trenutno aktivne podatke?"
                odgovor = QtGui.QMessageBox.question(self.gui,
                                                     "Potvrdi upload na REST servis",
                                                     msg,
                                                     QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                if odgovor == QtGui.QMessageBox.Yes:
                    logging.debug('dijalog je prihvacen, kreni spremati podatke na REST')
                    self.upload_minutnih_na_REST_common()
        logging.info('Metoda upload_minutne_na_REST_prompt, kraj')

    def upload_minutnih_na_REST_common(self):
        """
        Implementacija spremanja minutnih podataka na REST.

        sprema se dan po dan, i za sve kanalie u listi povezanih kanala.
        """
        #promjeni cursor u wait cursor
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        #adapter za podatke
        datumi = self.napravi_listu_dana(self.pickedDate, self.brojDanaSatni)
        #convert from qdate to string representation
        datumi = [i.toString('yyyy-MM-dd') for i in datumi]
        spremljeni = []
        nisuSpremljeni = []
        #hook za povezane kanale...
        kanali = self.mapaMjerenjeIdToOpis[self.gKanal]['povezaniKanali']
        for datum in datumi:
            for kanal in kanali:
                uspjeh = self.dokument.persist_minutne_podatke(key=kanal, date=datum)
                if uspjeh:
                    #podaci su spremljeni.. updejtaj kalendar za datum da je spremljen
                    self.update_kalendarStatus(kanal, datum, 'spremljeni')
                    self.promjena_boje_kalendara()
                    spremljeni.append((kanal, datum))
                else:
                    #podaci nisu spremljeni
                    nisuSpremljeni.append((kanal, datum))
        if len(nisuSpremljeni) != 0:
            #report uspjesnost spremanja
            naslov = 'Spremanje minutnih podataka na REST za kanal {}'.format(str(kanali))
            failStrLista = [str(i) for i in nisuSpremljeni]
            msgNeuspjeh = ", ".join(failStrLista)
            poruka = "\n".join(['Neuspjesno spremljeni datumi:', msgNeuspjeh])
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.information(self.gui, naslov, poruka)
        # vrati izgled cursora nazad na normalni
        QtGui.QApplication.restoreOverrideCursor()

    def upload_minutne_na_REST_gumb(self):
        """spremanje trenutnih opdataka na REST"""
        if self.pickedDate is None or self.gKanal is None:
            return None
        datum = QtCore.QDate().fromString(self.pickedDate, 'yyyy-MM-dd')
        danas = QtCore.QDate.currentDate()
        if datum > danas:
            return None
        if self.gKanal not in self.dokument.data:
            msg = 'U dokumentu (mapa dokument.data) ne postoji kljuc, key={0}. Return None'.format(str(self.gKanal))
            logging.debug(msg)
            return None
        datumi = self.napravi_listu_dana(self.pickedDate, self.brojDanaSatni)
        datumi = [i.toString('yyyy-MM-dd') for i in datumi]
        frejm = self.dokument.data[self.gKanal]
        msg = 'Frejm podataka koji treba spremiti:\n{0}'.format(str(frejm))
        logging.debug(msg)
        lenSvih = len(frejm)
        msg = 'broj podataka : {0}'.format(str(lenSvih))
        logging.debug(msg)
        validirani = frejm[abs(frejm['flag']) == 1000]
        lenValidiranih = len(validirani)
        msg = 'broj validiranih : {0}'.format(str(lenValidiranih))
        logging.debug(msg)
        msg = 'stanje dokumenta (dirty, da li je korisnik mjenjao flag) : {0}'.format(str(self.dokument.is_dirty()))
        logging.debug(msg)
        if lenSvih != lenValidiranih or self.dokument.is_dirty():
            msg = 'Potvrdi spremanje podataka na rest za datume:\n{0}'.format(str(datumi))
            odgovor = QtGui.QMessageBox.question(self.gui,
                                                 "Upload na REST",
                                                 msg,
                                                 QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if odgovor == QtGui.QMessageBox.Yes:
                logging.debug('dijalog je prihvacen, kreni spremati podatke na REST')
                self.upload_minutnih_na_REST_common()
                #nesretno nazvana funkcija... poziva na ponovno povlacenje istog
                #seta podataka sa resta i ponovno crtanje.
                self.ponisti_izmjene()

    def setup_radio_buttons(self, lista):
        """
        postavljanje radio gumbi u aplikaciji.
        Ulazni parametar je lista id programa mjerenja povezanih kanala.
        """
        self.gui.koncPanel.groupBoxRadio.setVisible(True)
        self.gui.zsPanel.groupBoxRadio.setVisible(True)
        self.gui.visednevniPanel.groupBoxRadio.setVisible(True)

        #block all signals, hide everything, uncheck everything
        for i in self.koncRadioButtons:
            i.blockSignals(True)
            i.setVisible(False)
            i.setChecked(False)
        for i in self.zsRadioButtons:
            i.blockSignals(True)
            i.setVisible(False)
            i.setChecked(False)
        for i in self.vdRadioButtons:
            i.blockSignals(True)
            i.setVisible(False)
            i.setChecked(False)

        #set visible needed ammount of elements, set their names
        for i in range(len(lista)):
            tekst = self.mapaMjerenjeIdToOpis[lista[i]]['komponentaFormula']
            self.koncRadioButtons[i].setVisible(True)
            self.koncRadioButtons[i].setText(tekst)
            self.zsRadioButtons[i].setVisible(True)
            self.zsRadioButtons[i].setText(tekst)
            self.vdRadioButtons[i].setVisible(True)
            self.vdRadioButtons[i].setText(tekst)

        #unblock all signals
        for i in self.koncRadioButtons:
            i.blockSignals(False)
        for i in self.zsRadioButtons:
            i.blockSignals(False)
        for i in self.vdRadioButtons:
            i.blockSignals(False)

        if len(lista) == 1:
            #hide groupboxove
            self.gui.koncPanel.groupBoxRadio.setVisible(False)
            self.gui.zsPanel.groupBoxRadio.setVisible(False)
            self.gui.visednevniPanel.groupBoxRadio.setVisible(False)

    def pripremi_membere_prije_ucitavanja_zahtjeva(self, mapa):
        """
        Funkcija analizira zahtjev preuzet u obliku mape
        {'programMjerenjaId':int, 'datumString':'YYYY-MM-DD'}
        i reinicijalizira odredjene membere kontorlora.
        """
        msg = 'pripremi_membere_prije_ucitavanja_zahtjeva, start.\nmapa={0}'.format(str(mapa))
        logging.info(msg)
        # reset status crtanja
        self.drawStatus = [False, False]
        noviglavnikanal = int(mapa['programMjerenjaId'])
        lista = self.mapaMjerenjeIdToOpis[noviglavnikanal]['povezaniKanali']
        self.gKanal = noviglavnikanal
        self.setup_radio_buttons(lista)
        msg = 'postavljen glavni kanal, id={0}'.format(str(self.gKanal))
        logging.info(msg)
        datum = mapa['datumString']  # datum je string formata YYYY-MM-DD
        self.pickedDate = datum  # postavi izabrani datum
        msg = 'postavljen izabrani datum, datum={0}'.format(str(self.pickedDate))
        logging.info(msg)
        # pretvaranje datuma u 2 timestampa od 00:01:00 do 00:00:00 iduceg dana
        tsdatum = pd.to_datetime(datum)
        self.zavrsnoVrijeme = tsdatum + datetime.timedelta(days=1)
        self.pocetnoVrijeme = tsdatum + datetime.timedelta(minutes=1) - datetime.timedelta(days=self.brojDanaSatni-1) #offset dana unazad
        #za svaki slucaj, pobrinimo se da su varijable pandas.tslib.Timestamp
        self.zavrsnoVrijeme = pd.to_datetime(self.zavrsnoVrijeme)
        self.pocetnoVrijeme = pd.to_datetime(self.pocetnoVrijeme)
        msg = 'Postavljeno pocetno i zavrsno vrijeme. pocetnoVrijeme={0} , zavrsnoVrijeme={1}'.format(str(self.pocetnoVrijeme), str(self.zavrsnoVrijeme))
        logging.info(msg)

    def ucitaj_podatke_ako_nisu_prije_ucitani(self):
        """
        Metoda usporedjuje argumente zahtjeva sa 'cacheom' vec odradjenih zahtjeva.
        Ako zahtjev nije prije odradjen, ucitava se u dokument.
        """
        logging.info('start ucitavanja podataka')
        self.sviBitniKanali = copy.deepcopy(self.mapaMjerenjeIdToOpis[self.gKanal]['povezaniKanali'])
        #pronadji sve ostale kanale potrebne za crtanje
        for key in self.gui.konfiguracija.dictPomocnih[self.gKanal]:
            self.sviBitniKanali.append(key)
        msg = 'popis svih bitnih kanala, lista={0}'.format(str(self.sviBitniKanali))
        logging.debug(msg)
        msg = 'pocetak ucitavanja kanala za datum={0} i brojdana={1}'.format(str(self.pickedDate), str(self.brojDanaSatni))
        logging.debug(msg)
        #popis datuma - lista QDate objekata
        datumi = self.napravi_listu_dana(self.pickedDate, self.brojDanaSatni)
        #kreni ucitavati po potrebi
        for kanal in self.sviBitniKanali:
            uspjeh = self.dokument.citaj(key=kanal, date=self.pickedDate, ndana=self.brojDanaSatni)
            if uspjeh:
                #update kalendarStatus
                for datum in datumi:
                    adapter = datum.toString('yyyy-MM-dd') #convert QDate to string
                    self.update_kalendarStatus(kanal, adapter, 'ucitani')
                    #test za validiranost podataka...
                    if self.dokument.provjeri_validiranost_dana(kanal, datum):
                        self.update_kalendarStatus(kanal, adapter, 'spremljeni')
                #dodaj glavni kanal u setGlavnihKanala
                self.setGlavnihKanala = self.setGlavnihKanala.union([self.gKanal])
                self.modelProgramaMjerenja.set_usedMjerenja(self.kalendarStatus)
                msg = 'Kanal je ucitan u dokument, kanal = {0}'.format(str(kanal))
                logging.info(msg)
            else:
                msg = 'Kanal nije ucitan u dokument, kanal = {0}'.format(str(kanal))
                logging.info(msg)
        self.gui.restIzbornik.treeView.model().layoutChanged.emit()
        #update boju na kalendaru ovisno o ucitanim podacima
        self.promjena_boje_kalendara()
        logging.info('kraj ucitavanja podataka')

    def napravi_listu_dana(self, datum, brojDana):
        """
        Funkcija uzima datum string formata 'YYYY-MM-DD' i integer broja dana.
        Izlaz fukcije je lista QDate objekata (datum i N prethodnih dana)
        """
        msg = 'Napravi_listu_dana za datum={0} i brojdana={1}'.format(str(datum), str(brojDana))
        logging.debug(msg)
        date = datetime.datetime.strptime(datum, '%Y-%m-%d')
        popis = [date-datetime.timedelta(days=i) for i in range(brojDana)]
        izlaz = [QtCore.QDate(i) for i in popis]
        msg = 'Napravi_listu_dana output lista QDate objekata, lista={0}'.format(str(izlaz))
        logging.debug(msg)
        return izlaz

    def promjena_aktivnog_taba(self, x):
        """
        Promjena aktivnog taba u displayu
        - promjeni member self.aktivniTab
        - kreni crtati grafove za ciljani tab ako prije nisu nacrtani
        """
        msg = 'zaprimljen zahtjev za promjenom prikazanog taba. tab={0}'.format(str(x))
        logging.info(msg)
        self.aktivniTab = x
        if x is 0 and not self.drawStatus[0]:
            self.crtaj_satni_graf()
            self.drawStatus[0] = True
        elif x is 1 and not self.drawStatus[1]:
            self.crtaj_zero_span()
            if hasattr(self, 'webZahtjev'):
                referentni = self.get_tablice_zero_span_referentnih_vrijednosti()
                self.gui.zsPanel.update_zero_span_referentne_vrijednosti(referentni)
            self.drawStatus[1] = True
        #prebacivanje na tab komentara...
        elif x is 3:
            try:
                #TODO! update komentare
                self.get_bitne_komentare(self.gKanal, self.pocetnoVrijeme, self.zavrsnoVrijeme)
            except Exception as err:
                #expected fail.. ako vrijeme i/ili kanal nije izabran
                msg = 'ocekivani problem sa updateom komentara kanal:{0}, pocetak:{1}, kraj:{2}'.format(str(self.gKanal), str(self.pocetnoVrijeme), str(self.zavrsnoVrijeme))
                logging.info(msg)
                logging.info(str(err), exc_info=True)

    def crtaj_satni_graf(self):
        """
        Metoda zaduzena za crtanje satnog grafa.
        Prije delegiranja naredbe ciljanom canvasu provjerava se ispravnost
        ulaznih argumenata (pocetnoVrijeme, zavrsnoVrijeme, gKanal).
        Crta se samo ako su parametri dobro zadani.
        """
        logging.info('crtaj_satni_graf, start')
        if (self.pocetnoVrijeme != None) and (self.zavrsnoVrijeme != None) and (self.gKanal != None):
            arg = {'kanalId': self.gKanal,
                   'pocetnoVrijeme': self.pocetnoVrijeme,
                   'zavrsnoVrijeme': self.zavrsnoVrijeme}
            msg = 'argumenti za crtanje: {0}'.format(str(arg))
            logging.debug(msg)
            #relevantni agregirani frejmovi za satni graf
            self.agregiraniFrejmovi = self.dokument.dohvati_agregirane_frejmove(
                lista=self.sviBitniKanali,
                tmin=self.pocetnoVrijeme,
                tmax=self.zavrsnoVrijeme)
            #naredba za crtanje satnog grafa
            logging.debug('start naredbe za crtanje satnog grafa')
            self.gui.koncPanel.satniGraf.crtaj(self.agregiraniFrejmovi, arg)
            #promjena labela u panelima sa grafovima, opis
            try:
                #opis naredbi koje sljede:
                #Zanima nas da li je netko prethodno odabrao satni interval za minutni graf.
                #Zanima nas da li je satni interval unutar izabranog datuma.
                #Bitno je, jer u slucaju promjene datuma minutni graf ce ostati
                #prikazivati zadnji satni interval. Da ne bi doslo do zabune (potencijalno
                #dva grafa mogu prikazivati razlicite kanale i/ili datume), moramo
                #"clearati" graf ili narediti ponovno crtanje minutnog grafa.
                if self.sat is not None:
                    if (self.sat >= self.pocetnoVrijeme) and (self.sat <= self.zavrsnoVrijeme):
                        #nacrtaj minutni graf
                        msg = 'Crtanje minutnog grafa za predhodno izabrani sat, vrijeme={0}'.format(str(self.sat))
                        logging.debug(msg)
                        self.crtaj_minutni_graf(self.sat)
                    else:
                        #clear minutni graf ako se datum pomakne
                        logging.debug('Clear minutnog grafa, izabrani sat nije u intervalu')
                        self.gui.koncPanel.minutniGraf.clear_graf()
                        #clear izabrani label sata (prosljedi prazan string)
                        self.gui.koncPanel.change_satLabel('')
            except (TypeError, LookupError) as err:
                logging.error('App exception', exc_info=True)
                self.prikazi_error_msg(err)
        logging.info('crtaj_satni_graf, kraj')

    def crtaj_minutni_graf(self, izabrani_sat):
        """
        Funkcija crta minutni graf za izabrani sat.
        Ova funkcija se brine za pravilni odgovor na ljevi klik tocke na satno
        agregiranom grafu. Za zadani sat, odredjuje rubove intervala te
        poziva crtanje minutnog grafa.
        """
        logging.info('crtaj_minutni_graf, start')
        msg = 'Izabrani sat spremljen u member self.sat, sat={0}'.format(str(izabrani_sat))
        logging.info(msg)
        self.sat = izabrani_sat
        dodatni_sati = self.brojSatiMinutni - 1 #1 sat je uracunat.
        if (self.zavrsnoVrijeme >= self.sat) and (self.sat >= self.pocetnoVrijeme):
            highLim = self.sat
            lowLim = highLim - datetime.timedelta(minutes=59) - datetime.timedelta(hours=dodatni_sati)
            lowLim = pd.to_datetime(lowLim)
            # update labela izabranog sata
            logging.info('update satni label na koncentracijskom panelu')
            self.gui.koncPanel.change_satLabel(self.sat)
            arg = {'kanalId': self.gKanal,
                   'pocetnoVrijeme': lowLim,
                   'zavrsnoVrijeme': highLim}
            # naredba za dohvacanje podataka
            msg = 'Dohvacanje podataka iz dokumenta. tmin={0} , tmax={1} , kanali={2}'.format(str(lowLim), str(highLim), str(self.sviBitniKanali))
            logging.debug(msg)
            self.frejmovi = self.dokument.dohvati_minutne_frejmove(
                lista=self.sviBitniKanali,
                tmin=lowLim,
                tmax=highLim)
            #naredba za crtanje
            logging.debug('naredba za crtanje minutnog grafa')
            self.gui.koncPanel.minutniGraf.crtaj(self.frejmovi, arg)
        logging.info('crtaj_minutni_graf, kraj')

    def crtaj_zero_span(self):
        """
        Crtanje zero span podataka.
        -Clear podataka
        -Dohvati podatke sa REST servisa
        -Nacrtaj ako ima podataka
        """
        logging.info('crtaj_zero_span, start')
        # clear grafove
        logging.debug('Clear zero i span grafa prije crtanja')
        self.gui.zsPanel.spanGraf.clear_zero_span()
        self.gui.zsPanel.zeroGraf.clear_zero_span()
        # provjeri da li je izabran glavni kanal i datum.
        msg = 'provjera membera prije crtanja. self.gKanal={0} , self.pickedDate={1}'.format(str(self.gKanal), str(self.pickedDate))
        logging.debug(msg)
        if self.gKanal is not None and self.pickedDate is not None:
            #dohvati zero i span podatke sa REST-a
            try:
                #promjeni cursor u wait cursor
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                #redefinicija argumenata
                tmax = datetime.datetime.strptime(self.pickedDate, '%Y-%m-%d')
                tmin = tmax - datetime.timedelta(days=self.brojDana)
                arg = {'kanalId': self.gKanal,
                       'pocetnoVrijeme': tmin,
                       'zavrsnoVrijeme': tmax,
                       'ndana':self.brojDana}
                #dohvati frejmove
                self.zeroFrejm, self.spanFrejm = self.dohvati_zero_span()
                #crtanje zero
                if len(self.zeroFrejm) > 0:
                    if 'vrijeme' in self.zeroFrejm.columns:
                        #fix duplicate rows (if any)
#                        self.zeroFrejm.drop_duplicates(subset='vrijeme',
#                                                       take_last=True,
#                                                       inplace=True)
#                        self.zeroFrejm.sort()
                        self.zeroFrejm.drop_duplicates(subset='vrijeme',
                                                       keep='last',
                                                       inplace=True)
                        self.zeroFrejm.sort_index(inplace=True)
                        logging.debug('naredba za crtanje zero grafa')
                        msg = 'ZERO graf argumenti za crtanje.\narg={0}\nfrejm=\n{1}'.format(str(arg), str(self.zeroFrejm))
                        logging.info(msg)
                        self.gui.zsPanel.zeroGraf.crtaj(self.zeroFrejm, arg)
                #crtanje span
                if len(self.spanFrejm) > 0:
                    if 'vrijeme' in self.spanFrejm.columns:
                        #fix duplicate rows (if any)
#                        self.spanFrejm.drop_duplicates(subset='vrijeme',
#                                                       take_last=True,
#                                                       inplace=True)
#                        self.spanFrejm.sort()
                        self.spanFrejm.drop_duplicates(subset='vrijeme',
                                                       keep='last',
                                                       inplace=True)
                        self.spanFrejm.sort_index(inplace=True)
                        logging.debug('naredba za crtanje span grafa')
                        msg = 'SPAN graf argumenti za crtanje.\narg={0}\nfrejm=\n{1}'.format(str(arg), str(self.spanFrejm))
                        logging.info(msg)
                        self.gui.zsPanel.spanGraf.crtaj(self.spanFrejm, arg)
            except AttributeError:
                #moguci fail ako se funkcija pozove prije inicijalizacije REST interfacea.
                logging.error('web interface nije incijaliziran, Potrebno se ulogirati.', exc_info=True)
            except (TypeError, ValueError, AssertionError):
                #mofuci fail za lose formatirani json string
                logging.error('greska kod parsanja json stringa za zero i span.', exc_info=True)
            finally:
                QtGui.QApplication.restoreOverrideCursor()
            logging.info('crtaj_zero_span, kraj')


    def get_tablice_zero_span_referentnih_vrijednosti(self):
        """
        Metoda je zaduzena da sa REST servisa prikupi referentne vrijednosti
        za zero i span. Te da updatea tablice.
        """
        msg = 'update_tablice_zero_span_referentnih_vrijednosti za self.gKanal={0}'.format(str(self.gKanal))
        logging.info(msg)
        zeroRefCheck = True
        spanRefCheck = True
        #zero
        try:
            zeroref = self.webZahtjev.get_zerospan_referentne_liste(self.gKanal, 'zero')
            zeroref = pd.read_json(zeroref, orient='records', convert_dates=['pocetakPrimjene'])
            zeroref.set_index('pocetakPrimjene', inplace=True) #set vremenski indeks
            zeroref.rename(columns={'vrijednost':'ZERO'}, inplace=True) #rename stupca u ZERO
            zeroref.drop(['id', 'vrsta'], axis=1, inplace=True) #drop nebitne stupce
        except Exception as err:
            logging.error(str(err), exc_info=True)
            msg = """
                Error je kod dohvacanja zero referentnih vrijednosti sa REST.
                Moguce nije valjani json.
                Kanal: {0}
                JSON: {1}""".format(str(self.gKanal), str(zeroref))
            logging.error(msg)
            zeroRefCheck = False
        if not zeroRefCheck:
            zeroref = pd.DataFrame(columns=['ZERO'])
        #span
        try:
            spanref = self.webZahtjev.get_zerospan_referentne_liste(self.gKanal, 'span')
            spanref = pd.read_json(spanref, orient='records', convert_dates=['pocetakPrimjene'])
            spanref.set_index('pocetakPrimjene', inplace=True) #set vremenski indeks
            spanref.rename(columns={'vrijednost':'SPAN'}, inplace=True) #rename stupca u SPAN
            spanref.drop(['id', 'vrsta'], axis=1, inplace=True) #drop nebitne stupce
        except Exception as err:
            logging.error(str(err), exc_info=True)
            msg = """
                Error je kod dohvacanja span referentnih vrijednosti sa REST.
                Moguce nije valjani json.
                Kanal: {0}
                JSON: {1}""".format(str(self.gKanal), str(spanref))
            logging.error(msg)
            spanRefCheck = False
        if not spanRefCheck:
            spanref = pd.DataFrame(columns=['SPAN'])
        #merge tablica u jednu
        result = pd.concat([zeroref, spanref])
        #sortiraj po indeksu
        #result.sort(inplace=True, ascending=False)
        result.sort_index(inplace=True, ascending=False)
        return result

    def dohvati_zero_span(self):
        """
        Za ulazni json string, convert i vrati zero i span frejm.
        Moguci exceptioni su:
        ArrtibuteError --> self.webZahtjev mozda nije inicijaliziran i ne postoji
        pomocne_funkcije.AppExcept --> fail prilikom ucitavanja json stringa sa REST
        AssertionError --> los format ulaznog frejma
        ValueError, TypeError --> krivi argumenti za json parser ili los json
        """
        msg = 'dohvati_zero_span za self.gKanal={0} , self.pickedDate={1} , self.brojDana={2}'.format(str(self.gKanal), str(self.pickedDate), str(self.brojDana))
        logging.info(msg)
        try:
            jsonText = self.webZahtjev.get_zero_span(self.gKanal, self.pickedDate, self.brojDana)
            frejm = pd.read_json(jsonText, orient='records', convert_dates=['vrijeme'])
        except ValueError:
            logging.error('App exception', exc_info=True)
            msg = """
                Error je kod dohvacanja zero/span podataka sa resta.
                Moguce nije valjani json.
                Kanal: {0}
                Datum: {1}
                JSON: {2}""".format(str(self.gKanal), str(self.pickedDate), str(jsonText))
            logging.error(msg)
            #vrati dva prazna datafrejma, nista se nece crtati dalje
            return pd.DataFrame(), pd.DataFrame()
        # test za strukturu frejma
        assert 'vrsta' in frejm.columns
        assert 'vrijeme' in frejm.columns
        assert 'vrijednost' in frejm.columns
        zeroFrejm = frejm[frejm['vrsta'] == "Z"]
        spanFrejm = frejm[frejm['vrsta'] == "S"]
        zeroFrejm = zeroFrejm.set_index(zeroFrejm['vrijeme'])
        spanFrejm = spanFrejm.set_index(spanFrejm['vrijeme'])
        # kontrola za besmislene vrijednosti (tipa -999)
        zeroFrejm = zeroFrejm[zeroFrejm['vrijednost'] > -998.0]
        spanFrejm = spanFrejm[spanFrejm['vrijednost'] > -998.0]
        msg = 'ZERO frejm : \n {0}'.format(zeroFrejm)
        logging.debug(msg)
        msg = 'SPAN frejm : \n {0}'.format(spanFrejm)
        logging.debug(msg)
        return zeroFrejm, spanFrejm

    def nacrtaj_rest_satne(self, mapa):
        """
        Metoda je zaduzena da preuzme podatke sa REST servisa, pripremi ih
        za crtanje i pokrene crtanje direktnom naredbom zaduzenom kanvasu

        ulazna mapa ima sljedeca polja:
        'datumOd','datumDo', 'kanal', 'valjani','validacija'

        P.S. ista mapa se mora prosljediti webZahtjevu da povuce podatke sa RESTA
        """
        logging.info('nacrtaj_rest_satne, start')
        try:
            maska = [i.isChecked() for i in self.vdRadioButtons]
            ind = maska.index(True)
            povezani = self.mapaMjerenjeIdToOpis[self.gKanal]['povezaniKanali']
            kanal = povezani[ind]
            mapa['kanal'] = kanal #set izabrani podkanal...
            jsonText = self.webZahtjev.get_satne_podatke(mapa)
            df = pd.read_json(jsonText, orient='records', convert_dates=['vrijeme'])
            frames, metaData = self.adapt_rest_satni_frejm(df)
            metaData['pocetnoVrijeme'] = pd.to_datetime(mapa['datumOd'])
            metaData['zavrsnoVrijeme'] = pd.to_datetime(mapa['datumDo'])
            self.gui.visednevniPanel.satniRest.crtaj(frames, metaData)

        except (ValueError, AssertionError):
            #parsig error kod jsona
            logging.error('App exception prilikom crtanja rest satnih podataka', exc_info=True)
            msg = """
                Error je kod dohvacanja satnih podataka sa resta.
                Moguce nije valjani json.
                Kanal: {0}
                Datum: {1}
                JSON:{2}""".format(str(self.gKanal), str(self.pickedDate), str(jsonText))
            logging.error(msg)
        logging.info('nacrtaj_rest_satne, start')

    def adapt_rest_satni_frejm(self, frejm):
        """
        metoda prilagodjava ulazni dataframe i sve potrebno za crtanje.
        frejm i mapu sa meta_podacima
        """
        assert isinstance(frejm, pd.core.frame.DataFrame), 'Nije pandas frejm'
        stupci = list(frejm.columns)
        assert 'vrijeme' in stupci, 'Nedostaje stupac "vrijeme"'
        assert 'programMjerenjaId' in stupci, 'Nedostaje stupac "programMjerenjaId"'
        assert 'valjan' in stupci, 'Nedostaje stupac "valjan"'
        assert 'vrijednost' in stupci, 'Nedostaje stupac "vrijednost"'
        frejm = frejm.set_index(frejm['vrijeme'])
        #min max vrijeme kao pandas timestamp...
        pocetno = frejm.index.min()
        zavrsno = frejm.index.max()
        kanal = frejm.loc[pocetno, 'programMjerenjaId']
        frejm.rename(columns={'valjan':'flag', 'vrijednost':'avg'}, inplace=True)
        frejm['flag'] = frejm['flag'].map(self.adapt_valjan)
        frejmovi = {kanal:frejm}
        metaMap = {'kanalId': kanal,
                   'pocetnoVrijeme': pocetno,
                   'zavrsnoVrijeme': zavrsno}
        return frejmovi, metaMap

    def adapt_valjan(self, x):
        """hellper converter iz booleana u flag"""
        if x:
            return 1
        else:
            return -1

    def dodaj_novu_referentnu_vrijednost(self):
        """
        Poziv dijaloga za dodavanje nove referentne vrijednosti za zero ili
        span. Upload na REST servis.
        """
        logging.info('dodaj_novu_referentnu_vrijednost, start.')
        if self.mapaMjerenjeIdToOpis != None and self.gKanal != None:
            # dict sa opisnim parametrima za kanal
            postaja = self.mapaMjerenjeIdToOpis[self.gKanal]['postajaNaziv']
            komponenta = self.mapaMjerenjeIdToOpis[self.gKanal]['komponentaNaziv']
            formula = self.mapaMjerenjeIdToOpis[self.gKanal]['komponentaFormula']
            opis = '{0}, {1}( {2} )'.format(postaja, komponenta, formula)
            dijalog = dodaj_ref_zs.DijalogDodajRefZS(parent=None, opisKanal=opis, idKanal=self.gKanal)
            if dijalog.exec_():
                podaci = dijalog.vrati_postavke()
                try:
                    #test da li je sve u redu?
                    msg = 'Neuspjeh. Podaci nisu spremljeni na REST servis.\nReferentna vrijednost je krivo zadana.'
                    assert isinstance(podaci['vrijednost'], float), msg
                    #napravi json string za upload (dozvoljeno odstupanje je placeholder)
                    #int od vremena... output je double zboj milisekundi
                    jS = {"vrijeme": int(podaci['vrijeme']),
                          "vrijednost": podaci['vrijednost'],
                          "vrsta": podaci['vrsta'],
                          "maxDozvoljeno": 0.0,
                          "minDozvoljeno": 0.0}
                    #dict to json dump
                    jS = json.dumps(jS)
                    msg = 'json referentne vrijednosti za upload json={0}'.format(str(jS))
                    logging.debug(msg)
                    #potvrda za unos!
                    odgovor = QtGui.QMessageBox.question(self.gui,
                                                         "Potvrdi upload na REST servis",
                                                         "Potvrdite spremanje podataka na REST servis",
                                                         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

                    if odgovor == QtGui.QMessageBox.Yes:
                        #put json na rest!
                        logging.debug('dijalog prihvacen, spremi na REST')
                        uspjeh = self.webZahtjev.upload_ref_vrijednost_zs(jS, self.gKanal)
                        if uspjeh:
                            #confirmation da je uspjelo
                            QtGui.QMessageBox.information(self.gui,
                                                          "Potvrda unosa na REST",
                                                          "Podaci sa novom referentnom vrijednosti uspjesno su spremljeni na REST servis")
                        else:
                            logging.error('Pogreska kod uploada referentne vrijednosti zero/span na servis.')
                            self.prikazi_error_msg('Referentna vrijednost nije uspjesno spremljena na REST servis')

                        msg = 'Uspjesno dodana nova referentna vrijednost zero/span. json = {0}'.format(jS)
                        logging.info(msg)
                except AssertionError as err:
                    logging.error('Pogreska kod zadavanja referentne vrijednosti za zero ili span (nije float)',
                                  exc_info=True)
                    self.prikazi_error_msg(str(err))
        else:
            logging.info('pokusaj dodavanje ref vrijednosti bez ucitanih kanala mjerenja ili bez izabranog kanala')
            self.prikazi_error_msg('Neuspjeh. Programi mjerenja nisu ucitani ili kanal nije izabran')
        logging.info('dodaj_novu_referentnu_vrijednost, start.')

    def promjeni_flag(self, ulaz):
        """
        Odgovor kontrolora na zahtjev za promjenom flaga. Kontrolor naredjuje
        dokumentu da napravi odgovarajucu izmjenu.

        Ulazni parametar je mapa:
        ulaz['od'] -->pocetno vrijeme, pandas timestamp
        ulaz['do'] -->zavrsno vrijeme, pandas timestamp
        ulaz['noviFlag'] -->novi flag
        ulaz['kanal'] -->kanal koji se mijenja

        P.S. dokument ima vlastiti signal da javi kada je doslo do promjene

        QtCore.SIGNAL('model_flag_changed')
        """
        #naredi promjenu flaga
        msg = 'promjeni_flag, start. Argumenti={0}'.format(str(ulaz))
        logging.info(msg)
        kanalizapromjenu = self.mapaMjerenjeIdToOpis[ulaz['kanal']]['povezaniKanali']
        for kanal in kanalizapromjenu:
            self.dokument.change_flag(key=kanal, tmin=ulaz['od'], tmax=ulaz['do'], flag=ulaz['noviFlag'])
            #mankni sve datume nakon promjene flaga u dokumentu iz "self.kalendarStatus['ok']" liste
            if kanal in self.kalendarStatus:
                tsRasponDana = list(pd.date_range(start=ulaz['od'], end=ulaz['do']))
                strRasponDana = [QtCore.QDate.fromString(dan.strftime('%Y-%m-%d'), 'yyyy-MM-dd') for dan in tsRasponDana]
                for dan in strRasponDana:
                    if dan in self.kalendarStatus[kanal]['ok']:
                        self.kalendarStatus[kanal]['ok'].remove(dan)
                msg = 'Refresh kalendar u rest izborniku, mapa datuma : {0}'.format(str(self.kalendarStatus[kanal]))
                logging.debug(msg)
                self.gui.restIzbornik.calendarWidget.refresh_dates(self.kalendarStatus[kanal])
        logging.info('promjeni_flag, kraj')

    def update_kalendarStatus(self, progMjer, datum, tip):
        """
        dodavanje datuma na popis ucitanih i ili validiranih ovisno o tipu
        i programu mjerenja.

        progMjer --> program mjerenja id, integer
        datum --> string reprezentacija datuma  'yyyy-MM-dd' formata
        tip --> 'ucitani' ili 'spremljeni'
        """
        msg = 'update_kalendarStatus, start. Argumenti : progMjer={0} , datum={1} , tip={2}'.format(str(progMjer), str(datum), str(tip))
        logging.info(msg)
        pyDanas = datetime.datetime.now().strftime('%Y-%m-%d')
        qDanas = QtCore.QDate.fromString(pyDanas, 'yyyy-MM-dd')
        datum = QtCore.QDate.fromString(datum, 'yyyy-MM-dd')
        if datum != qDanas:
            if progMjer in self.kalendarStatus:
                if tip == 'spremljeni':
                    if datum not in self.kalendarStatus[progMjer]['ok']:
                        self.kalendarStatus[progMjer]['ok'].append(datum)
                else:
                    if datum not in self.kalendarStatus[progMjer]['bad']:
                        self.kalendarStatus[progMjer]['bad'].append(datum)
                    #provjera validiranosti
                    test1 = self.dokument.provjeri_validiranost_dana(self.gKanal, datum)
                    #provjera postojanja medju validiranima
                    test2 = datum not in self.kalendarStatus[progMjer]['ok']
                    if test1 and test2:
                        self.kalendarStatus[progMjer]['ok'].append(datum)
            else:
                self.kalendarStatus[progMjer] = {'ok': [], 'bad': [datum]}
        logging.info('update_kalendarStatus, kraj')

    def promjena_boje_kalendara(self):
        """
        Funkcija mjenja boju kalendara ovisno o podacima za glavni kanal.
        self.kalendarStatus je mapa koja za svaki kanal prati koji su datumi
        ucitani, a koji su spremljeni na REST servis.

        P.S. izdvojeno van kao funkcija samo radi citljivosti.
        """
        logging.debug('zahtvev za updateom boja na kalendaru rest izbornika')
        if self.gKanal in self.kalendarStatus:
            self.gui.restIzbornik.calendarWidget.refresh_dates(self.kalendarStatus[self.gKanal])

    def promjeni_datum(self, x):
        """
        Odgovor na zahtjev za pomicanjem datuma za 1 dan (gumbi sljedeci/prethodni)
        Emitiraj signal da izbornik promjeni datum ovisno o x. Ako je x == 1
        prebaci 1 dan naprijed, ako je x == -1 prebaci jedan dan nazad
        """
        msg = 'naredba za prebacivanje {0} dana u kalendaru'.format(x)
        logging.info(msg)
        self.gui.restIzbornik.pomakni_dan(x)

    def promjeni_max_broj_dana_satnog(self, x):
        """
        promjena raspona max broja dana za satno agregirani graf. Ulazni parametar
        x je broj dana u rasponu [1-5].
        """
        self.brojDanaSatni = int(x)
        msg = 'Promjena broja dana za prikaz na satno agregiranom grafu. n={0}'.format(str(x))
        logging.info(msg)
        #ako su izabrani glank i datum, ponovno nacrtaj graf
        if self.gKanal != None and self.pickedDate != None:
            self.priredi_podatke({'programMjerenjaId':self.gKanal, 'datumString':self.pickedDate})

    def promjeni_max_broj_sati_minutnog(self, x):
        """
        Promjena raspona max broja sata za minutni graf. Ulazni paremetar x je
        broj sati.
        """
        self.brojSatiMinutni = int(x)
        msg = 'Promjena broja sati za prikaz na minutnom grafu. n={0}'.format(str(x))
        logging.info(msg)
        if self.gKanal != None and self.pickedDate != None and self.sat != None:
            self.crtaj_minutni_graf(self.sat)

    def update_zs_broj_dana(self, x):
        """
        Preuzimanje zahtjeva za promjenom broja dana na zero span grafu.
        Ponovno crtanje grafa.
        """
        msg = 'zaprimljen zahtjev za promjenom broja dana na zero i span grafu. N={0}'.format(str(x))
        logging.debug(msg)
        self.brojDana = int(x)
        self.crtaj_zero_span()
        if hasattr(self, 'webZahtjev'):
            referentni = self.get_tablice_zero_span_referentnih_vrijednosti()
            self.gui.zsPanel.update_zero_span_referentne_vrijednosti(referentni)
        self.drawStatus[1] = True


    def apply_promjena_izgleda_grafova(self):
        """
        funkcija se pokrece nakon izlaska iz dijaloga za promjenu grafova.
        Naredba da se ponovno nacrtaju svi grafovi.
        """
        logging.info('Apply promjenu izgleda grafova. Ponovo crtanje')
        self.drawStatus = [False, False] # promjena izgleda grafa, tretiraj kao da nisu nacrtani
        if self.gKanal != None:
            mapa = {'programMjerenjaId':self.gKanal, 'datumString':self.pickedDate}
            self.priredi_podatke(mapa)
