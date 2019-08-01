# -*- coding: utf-8 -*-
"""
Created on Fri Feb  6 12:48:25 2015

@author: User
"""
from PyQt4 import uic
import app.general.pomocne_funkcije as pomocne_funkcije

base6, form6 = uic.loadUiType('./app/view/ui_files/glavni_graf_widget.ui')
class GrafIzbor(base6, form6):
    """
    Prikaz kontrolnih widgeta za postavljanje opcija glavnog grafa
    npr. boja, tip markera, tip linije, fill, ekstremi itd.

    Inicjializira se sa:
    defaulti
        --> konfiguracijski objekt aplikacije (podaci o grafovima)

    listHelpera
        --> lista koja sadrzi dictove sa konverziju matplotlib vrijednositi
            u smislenije podatke i nazad .. npr '-' : 'Puna linija'

        --> struktura liste je definirana na sljedeci nacin po poziciji:
            element 0 : mpl.marker --> opisni marker
            element 1 : opisni marker --> mpl.marker
            element 2 : mpl.linestyle --> opis stila linije
            element 3 : opis stila linije --> mpl.linestyle
            element 4 : agregirani kanal --> dulji opis kanala
            element 5 : dulji opis kanala --> agregirani kanal
    """
    def __init__(self, parent=None, defaulti=None, listHelpera=None):
        super(base6, self).__init__(parent)
        self.setupUi(self)
        markeri = sorted(list(listHelpera[1].keys()))
        linije = sorted(list(listHelpera[3].keys()))
        agKanal = sorted(list(listHelpera[5].keys()))
        ###marker###
        # sirovi, nevalidirani podatak
        self.normalMarker.addItems(markeri)
        normal = listHelpera[0][defaulti.satni.NVOK.markerStyle]
        self.normalMarker.setCurrentIndex(self.normalMarker.findText(normal))
        #validirani podatak
        self.validanMarker.addItems(markeri)
        validan = listHelpera[0][defaulti.satni.VOK.markerStyle]
        self.validanMarker.setCurrentIndex(self.validanMarker.findText(validan))
        #velicina markera
        self.glavniMarkerSize.setValue(defaulti.satni.NVOK.markerSize)
        #boja dobro flagiranih podataka
        self.set_widget_color_style(defaulti.satni.VOK.rgb,
                                    defaulti.satni.VOK.alpha,
                                    "QPushButton",
                                    self.bojaOK)
        #boja lose flagiranih podataka
        self.set_widget_color_style(defaulti.satni.VBAD.rgb,
                                    defaulti.satni.VBAD.alpha,
                                    "QPushButton",
                                    self.bojaBAD)
        #prozirnost markera
        self.glavniMarkerAlpha.setValue(defaulti.satni.VOK.alpha)
        ###centralna linija###
        #stil linije
        self.midlineStil.addItems(linije)
        ml = listHelpera[2][defaulti.satni.Midline.lineStyle]
        self.midlineStil.setCurrentIndex(self.midlineStil.findText(ml))
        #sirina centralne linije
        self.midlineWidth.setValue(defaulti.satni.Midline.lineWidth)
        #boja centralne linije
        self.set_widget_color_style(defaulti.satni.Midline.rgb,
                                    defaulti.satni.Midline.alpha,
                                    "QPushButton",
                                    self.midlineBoja)
        #prozirnost centralne linije
        self.midlineAlpha.setValue(defaulti.satni.Midline.alpha)
        ###ekstremi###
        self.ekstremCrtaj.setChecked(defaulti.satni.EksMin.crtaj)
        #stil markera ekstremnih vrijednosti
        self.ekstremMarker.addItems(markeri)
        e = listHelpera[0][defaulti.satni.EksMin.markerStyle]
        self.ekstremMarker.setCurrentIndex(self.ekstremMarker.findText(e))
        #velicina markera ekstremnih vrijednosti
        self.ekstremSize.setValue(defaulti.satni.EksMin.markerSize)
        #boja markera ekstremnih vrijednosti
        self.set_widget_color_style(defaulti.satni.EksMin.rgb,
                                    defaulti.satni.EksMin.alpha,
                                    "QPushButton",
                                    self.ekstremBoja)
        #prozirnost markera ekstremnih vrijednosti
        self.ekstremAlpha.setValue(defaulti.satni.EksMin.alpha)
        #disable/enable kontrole ovisno o statusu checkboxa
        if defaulti.satni.EksMin.crtaj:
            self.ekstremMarker.setEnabled(True)
            self.ekstremSize.setEnabled(True)
            self.ekstremBoja.setEnabled(True)
            self.ekstremAlpha.setEnabled(True)
        else:
            self.ekstremMarker.setEnabled(False)
            self.ekstremSize.setEnabled(False)
            self.ekstremBoja.setEnabled(False)
            self.ekstremAlpha.setEnabled(False)
        ###fill###
        self.fillCrtaj.setChecked(defaulti.satni.Fill.crtaj)
        #izbor komponente1
        self.fillKomponenta1.addItems(agKanal)
        k1 = listHelpera[4][defaulti.satni.Fill.komponenta1]
        self.fillKomponenta1.setCurrentIndex(self.fillKomponenta1.findText(k1))
        #izbor komponente2
        self.fillKomponenta2.addItems(agKanal)
        k2 = listHelpera[4][defaulti.satni.Fill.komponenta2]
        self.fillKomponenta2.setCurrentIndex(self.fillKomponenta2.findText(k2))
        #izbor boje filla
        self.set_widget_color_style(defaulti.satni.Fill.rgb,
                                    defaulti.satni.Fill.alpha,
                                    "QPushButton",
                                    self.fillBoja)
        #izbor prozirnosti filla
        self.fillAlpha.setValue(defaulti.satni.Fill.alpha)
        #enable/disable ovisno o statusu crtanja
        if defaulti.satni.Fill.crtaj:
            self.fillKomponenta1.setEnabled(True)
            self.fillKomponenta2.setEnabled(True)
            self.fillBoja.setEnabled(True)
            self.fillAlpha.setEnabled(True)
        else:
            self.fillKomponenta1.setEnabled(False)
            self.fillKomponenta2.setEnabled(False)
            self.fillBoja.setEnabled(False)
            self.fillAlpha.setEnabled(False)
        #postavke za status warning
        #izbor stila markera
        self.statusStil.addItems(markeri)
        tmark = listHelpera[0][defaulti.satni.statusWarning.markerStyle]
        self.statusStil.setCurrentIndex(self.statusStil.findText(tmark))
        #izbor velicine markera
        self.statusSize.setValue(defaulti.satni.statusWarning.markerSize)
        #izbor boje statusa
        self.set_widget_color_style(defaulti.satni.statusWarning.rgb,
                                    defaulti.satni.statusWarning.alpha,
                                    "QPushButton",
                                    self.statusBoja)
        self.set_widget_color_style(defaulti.satni.statusWarningOkolis.rgb,
                                    defaulti.satni.statusWarningOkolis.alpha,
                                    "QPushButton",
                                    self.okolisStatusBoja)
        #izbor prozirnosti temperature kontejnera
        self.statusAlpha.setValue(defaulti.satni.statusWarning.alpha)
        self.okolisStatusAlpha.setValue(defaulti.satni.statusWarningOkolis.alpha)
        #enable/disable ovisno o statusu crtanja
        self.statusCrtaj.setChecked(defaulti.satni.statusWarning.crtaj)
        if defaulti.satni.statusWarning.crtaj:
            self.statusAlpha.setEnabled(True)
            self.statusBoja.setEnabled(True)
            self.statusSize.setEnabled(True)
            self.statusStil.setEnabled(True)
            self.okolisStatusBoja.setEnabled(True)
            self.okolisStatusAlpha.setEnabled(True)
        else:
            self.statusAlpha.setEnabled(False)
            self.statusBoja.setEnabled(False)
            self.statusSize.setEnabled(False)
            self.statusStil.setEnabled(False)
            self.okolisStatusBoja.setEnabled(False)
            self.okolisStatusAlpha.setEnabled(False)

    def set_widget_color_style(self, rgb, a, tip, target):
        """
        izrada stila widgeta
        tip - qwidget tip, npr "QPushButton"
        target - instanca widgeta kojem mjenjamo stil
        """
        # get string name of target object
        name = str(target.objectName())
        #napravi stil
        stil = pomocne_funkcije.rgba_to_style_string(rgb, a, tip, name)
        #set stil u target
        target.setStyleSheet(stil)
