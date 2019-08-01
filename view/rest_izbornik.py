# -*- coding: utf-8 -*-
"""
Created on Thu Jan 22 10:55:55 2015

@author: User
"""
from PyQt4 import QtGui, QtCore, uic
import logging
import datetime  # potreban za provjeru da li je izabrani dan u buducnosti
import app.model.model_drva as model_drva


base1, form1 = uic.loadUiType('./app/view/ui_files/rest_izbornik.ui')
class RestIzbornik(base1, form1):
    """
    REST izbornik (gumbi, treeView, kalendar...).
    """
    def __init__(self, parent=None):
        super(base1, self).__init__(parent)
        self.setupUi(self)
        self.model = None
        # set custom kalendar u widget
        self.calendarWidget = CustomKalendar(parent=None)
        self.calendarLayout.addWidget(self.calendarWidget)

        #doubleclick/enter na kalendar
        self.calendarWidget.activated.connect(self.get_mjerenje_datum)
        #single click/select na kalendar
        self.calendarWidget.clicked.connect(self.get_mjerenje_datum)
        #doubleclick/enter na element u treeViewu (program mjerenja)
        self.treeView.activated.connect(self.get_mjerenje_datum)
        #singleclick ma element u treeViewu sa programima mjerenja
        self.treeView.clicked.connect(self.get_mjerenje_datum)

    def get_mjerenje_datum(self, x):
        """
        Funkcija se poziva prilikom:
            -doubleclicka na valjani program mjerenja
            -singleclick ili doubleclick datuma na kalendaru

        Emitira se signal sa izborom [programMjerenjaId, datum] kao listu
        Ne emitira listu ako je izabrani datum u "buducnosti" (jos nema podataka).

        P.S. ulazni argument x mora postojati radi signala activated/clicked
        prilikom pozivanja ove funkcije slobodno prosljedi True kao ulazni argument
        """
        # dohvacanje i formatiranje trenutno aktivnog datuma u kalendaru
        qdan = self.calendarWidget.selectedDate()  #dohvaca QDate objekt
        pdan = qdan.toPyDate()  #convert u datetime.datetime python objekt
        dan = pdan.strftime('%Y-%m-%d')  #transformacija u zadani string format
        #provjeri datum, ako je u "buducnosti", zanemari naredbu
        danas = datetime.datetime.now()
        sutra = danas + datetime.timedelta(days=1)
        sutra = sutra.date()
        try:
            if pdan < sutra and type(self.model) == model_drva.ModelDrva:
                #dohvacanje programa mjerenja
                ind = self.treeView.currentIndex()  #dohvati trenutni aktivni indeks
                item = self.model.getItem(ind)  #dohvati specificni objekt pod tim indeksom
                prog = item._data[2]  #dohvati program mjerenja iz liste podataka
                if prog is not None:
                    output = {'programMjerenjaId': int(prog),
                              'datumString': dan}
                    #print('Izabrana kombinacija: {0}'.format(output))
                    self.emit(QtCore.SIGNAL('priredi_podatke(PyQt_PyObject)'), output)
                    msg = 'izabrana kombinacija kanala i datuma : {0}'.format(str(output))
                    logging.info(msg)
                else:
                    #TODO!
                    self.emit(QtCore.SIGNAL('prikazi_komentare_za_stanicu(PyQt_PyObject)'), str(item))
        except Exception as err:
            tekst = 'Opcenita pogreska, problem sa dohvacanjem programa mjerenja\n' + str(err)
            logging.error('App exception', exc_info=True)
            self.emit(QtCore.SIGNAL('prikazi_error_msg(PyQt_PyObject)'), tekst)

    def pomakni_dan(self, brojDana):
        """
        Metoda "pomice dan" u kalendaru za neki broj dana od trenutno selektiranog.
        brojDana moze biti negativan (pomicanje unazad) i pozitivan (pomicanje unaprijed)
        """
        # dohvati trenutno selektirani dan
        dan = self.calendarWidget.selectedDate()
        #smanji za 1
        dan2 = dan.addDays(brojDana)
        #postavi novi dan kao trenutno selektirani
        self.calendarWidget.setSelectedDate(dan2)
        #informiraj kontroler o promjeni
        self.get_mjerenje_datum(True)


class CustomKalendar(QtGui.QCalendarWidget):
    """
    Subklasa kalendara koja boja odredjene datume u zadane boje.

    samo mu treba prosljediti dict QtCore.QDate objekata organiziranih u dvije
    liste preko metode refresh_dates(dict datuma)

    'ok' --> zelena boja
    'bad' --> crvena boja
    """
    def __init__(self, parent=None, datumi=None):
        QtGui.QCalendarWidget.__init__(self, parent)
        # dict QDate objekata koji se trebaju razlicito obojati
        if datumi == None:
            self.datumi = {'ok': [], 'bad': []}
        else:
            self.datumi = datumi
        self.setFirstDayOfWeek(QtCore.Qt.Monday)
        #boja za nedovrsene datume
        self.color1 = QtGui.QColor(255, 0, 0)
        self.color1.setAlpha(50)
        #boja za dovrsene datume
        self.color2 = QtGui.QColor(0, 255, 0)
        self.color2.setAlpha(50)
        #boja za select
        self.color3 = QtGui.QColor(0, 0, 255)
        self.color3.setAlpha(50)
        self.selectionChanged.connect(self.updateCells)

    def paintCell(self, painter, rect, date):
        """Painter za celije kalendara"""
        QtGui.QCalendarWidget.paintCell(self, painter, rect, date)

        if date in self.datumi['bad'] and date not in self.datumi['ok']:
            painter.fillRect(rect, self.color1)
        elif date in self.datumi['ok']:
            painter.fillRect(rect, self.color2)

        izabrani = self.selectedDate()
        if date == izabrani:
            painter.fillRect(rect, self.color3)

    def refresh_dates(self, qdatesdict):
        """Setter za novi popis datuma koji treba drugacije obojati i update
        izgleda kalendara u jednom."""
        self.datumi = qdatesdict
        # updateCells, forsira ponovno iscrtavanje
        self.updateCells()
