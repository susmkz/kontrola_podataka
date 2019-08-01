# -*- coding: utf-8 -*-
"""
Created on Tue Nov  4 15:56:53 2014

@author: User
"""

from PyQt4 import QtGui, QtCore
import app.general.pomocne_funkcije as pomocne_funkcije
import math
import logging
import numpy as np
import pandas as pd


class PomocniGrafovi(QtCore.QAbstractTableModel):
    """
    Ova klasa je "model" za dinamicki prikaz pomocnih grafova u qtableview widgetu

    P.S. imenovanje funkcija odskace od nacina na koji su pisane drugdje, ali
    Qt frejmwork inszistira da se funkcije zovu rowCount,  a ne row_count

    P.P.S. za inicijalizaciju su bitne 4 stvari
    1. grafInfo -> treba dati nested listu pomocnih grafova (inace je nested dictionary)
    2. markeri ->lista svih markera koji ulaze u izbor, opisni ('Krug'...)
    3. linije ->lista svih stilova linija, opisni ('Dash-Dot'...)
    """
    def __init__(self, grafInfo=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.headeri = ['Postaja', 'Komponenta', 'Usporedno']
        if grafInfo == None:
            self.grafInfo = []
        else:
            self.grafInfo = grafInfo

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        Nuzna metoda za rad klase
        -vraca informaciju o broju redaka display djelu
        """
        return len(self.grafInfo)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        Nuzna metoda za rad klase
        -vraca informaciju o broju stupaca display djelu
        HARDCODED, samo 3 stupca:
            ['Postaja', 'Komponenta', 'Usporedno']
        """
        return 3

    def flags(self, index):
        """
        -vraca van stanje svakog indeksa u prikazu tablice.
        -enabled, selectable i editable
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """
        Metoda zaduzena za postavljanje novih vrijednosti u model(editable).

        Cilj je delegirati editiranje na posebni dijalog.
        """
        if not index.isValid():
            return False

        if role == QtCore.Qt.EditRole:
            row = index.row()
            col = index.column()
            if col == 0:  # promjena Postaje
                self.grafInfo[row][1] = value  #promjeni Postaju
                #promjeni i programMjerenjaId
                postaja = self.grafInfo[1]
                komponenta = self.grafInfo[2]
                usporedno = self.grafInfo[3]
                self.grafInfo[row][0] = self.pomocnaMapa[postaja][komponenta][usporedno]
                return True
            elif col == 1:
                self.grafInfo[row][2] = value  # promjeni komponentu
                self.grafInfo[row][11] = value  # promjeni i label
                # promjeni i programMjerenjaId
                postaja = self.grafInfo[1]
                komponenta = self.grafInfo[2]
                usporedno = self.grafInfo[3]
                self.grafInfo[row][0] = self.pomocnaMapa[postaja][komponenta][usporedno]
                return True
            elif col == 2:
                self.grafInfo[row][3] = value  # promjeni usporedno
                # promjeni i programMjerenjaId
                postaja = self.grafInfo[1]
                komponenta = self.grafInfo[2]
                usporedno = self.grafInfo[3]
                self.grafInfo[row][0] = self.pomocnaMapa[postaja][komponenta][usporedno]
                return True

    def data(self, index, role):
        """
        Nuzna metoda za rad klase
        -za svaki role i indeks u tablici daje display djelu trazene vrijednosti
        """
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            column = index.column()
            if column == 0:
                value = self.grafInfo[row][1]  # stupac "Postaja"
            elif column == 1:
                value = self.grafInfo[row][2]  # stupac "Komponenta"
            elif column == 2:
                value = self.grafInfo[row][3]  # stupac "Usporedno"
            return value
        if role == QtCore.Qt.EditRole:
            row = index.row()
            column = index.column()
            if column == 0:
                value = self.grafInfo[row][1]  # stupac "Postaja"
            elif column == 1:
                value = self.grafInfo[row][2]  # stupac "Komponenta"
            elif column == 2:
                value = self.grafInfo[row][3]  # stupac "Usporedno"
            return value
        if role == QtCore.Qt.DecorationRole:
            row = index.row()
            column = index.column()
            if column == 0:
                # na stupcima 1 (komponenta)
                rgb = self.grafInfo[row][8]
                alpha = self.grafInfo[row][9]
                #stvaranje tocne nijanse kao QColor
                boja = pomocne_funkcije.default_color_to_qcolor(rgb, alpha)
                #izrada pixmapa i ikone koju dodajemo kao ukras
                pixmap = QtGui.QPixmap(20, 20)
                pixmap.fill(boja)
                icon = QtGui.QIcon(pixmap)
                return icon

    def headerData(self, section, orientation, role):
        """
        Metoda postavlja headere u tablicu
        """
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headeri[section]
            else:
                return section

    def insertRows(self, position, rows, parent=QtCore.QModelIndex(), sto=None):
        """
        metoda za umetanje redova u tablicu
        insert na poziciji : position
        broj redova za insertanje : rows
        parent = defaultni q model index
        """
        # mora se pozvati zbog sinhorizacije view-ova
        self.beginInsertRows(parent, position, position + rows - 1)
        #insert u podatke
        for i in range(rows):
            value = sto[i]
            self.grafInfo.insert(position, value)
        #mora se pozvati zbog sinhorizacije view-ova
        self.endInsertRows()
        #funkcija mora vratiti True da signalizira da su redovi umetnuti
        return True

    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):
        """
        metoda za brisanje redova iz tablice
        delete na poziciji : position
        broj redova za delete : rows
        parent = defaultni q model index
        """
        # mora se pozvati zbog sinhronizacije view-ova
        self.beginRemoveRows(parent, position, position + rows - 1)
        #sami delete
        for i in range(rows):
            self.grafInfo.pop(position)
        #mora se pozvati zbog sinhronizacije view-ova
        self.endRemoveRows()
        #funkcija mora vratiti True da signalizira da su redovi umetnuti
        return True

    def vrati_nested_listu(self):
        """
        funkcija vraca nested listu koja sadrzi podatke u modelu
        """
        return self.grafInfo


class BitModel(QtCore.QAbstractTableModel):
    """
    Model za prikaz statusa bit po bit.
    Broj stupaca --> 6
    """
    def __init__(self, data=None, smap=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        self.booldata = data # lista boolean vrijednosti
        self.smap = smap # status mapa

    def set_data_and_smap(self, lista, mapa):
        self.booldata = lista
        self.smap = mapa
        self.trueIndeksi = []
        for i in range(len(self.booldata)):
            if self.booldata[i] is True:
                self.trueIndeksi.append(i)
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if isinstance(self.smap, dict):
            return math.ceil(len(self.trueIndeksi)/6)
        else:
            return 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 6

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        ind = row * 6 + col #indeks u listi
        try:
            ind = self.trueIndeksi[ind] #convert indeksa
        except LookupError as err:
            logging.debug(str(err), exc_info=True) #expected index error
            ind = None
        if role == QtCore.Qt.DisplayRole:
            if ind in self.smap:
                return str(self.smap[ind])
            else:
                return ''
        if role == QtCore.Qt.BackgroundColorRole:
            try:
                if self.booldata[ind] == True:
                    return QtGui.QBrush(QtGui.QColor(255, 0, 0, 80))
                elif self.booldata[ind] == False:
                    return QtGui.QBrush(QtGui.QColor(0, 255, 0, 80))
            except Exception as err:
                logging.debug(str(err), exc_info=True) #XXX! ocekivani index errori
                return QtGui.QBrush(QtGui.QColor(255, 255, 255))
        if role == QtCore.Qt.ToolTipRole:
            try:
                description = str(self.smap[ind])
                check = str(self.booldata[ind])
                msg = '{0} : {1}'.format(description, check)
                return msg
            except Exception as err:
                logging.debug(str(err), exc_info=True) #XXX! ocekivani index errori
                return ''


class SatnoAgregiraniPodaciModel(QtCore.QAbstractTableModel):
    """
    Prikaz vrijednosti za izabranu satno agregiranu tocku
    """
    def __init__(self, data=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        if self.data is None:
            self.data = {'average':None, 'min':None, 'max':None, 'count':None}
        else:
            self.data = data
        self.headeri = ['srednjak', 'min', 'max', 'broj podataka']

    def set_data(self, mapa):
        self.data = mapa
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 1

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        col = index.column()
        if role == QtCore.Qt.DisplayRole and isinstance(self.data, dict):
            if col == 0:
                if 'average' in self.data:
                    return str(self.data['average'])
            elif col == 1:
                if 'min' in self.data:
                    return str(self.data['min'])
            elif col == 2:
                if 'max' in self.data:
                    return str(self.data['max'])
            elif col == 3:
                if 'count' in self.data:
                    return str(self.data['count'])

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headeri[section]

class MinutniPodaciModel(QtCore.QAbstractTableModel):
    """
    prikaz vrijednosti za izabranu minutnu tocku
    """
    def __init__(self, data=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        if self.data is None:
            self.data = {'koncentraicja':None}
        else:
            self.data = data
        self.headeri = ['koncentracija', 'mjeritelj']

    def set_data(self, mapa):
        self.data = mapa
#        #TODO! extendanje za n kljuceva
#        self.headeri = ['koncentracija']
#        for key in mapa:
#            self.headeri.append(key)
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 1

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2
        #TODO! extendanje za n kljuceva, vidi grafovi_panel za ostatak koda
#        return len(self.headeri)

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        col = index.column()
        if role == QtCore.Qt.DisplayRole and isinstance(self.data, dict):
            if col == 0:
                if 'koncentracija' in self.data:
                    return str(self.data['koncentracija'])
            if col == 1:
                if 'mjeritelj' in self.data:
                    return str(self.data['mjeritelj'])
            #TODO! extendanje za n kljuceva
#            key = self.headeri[col]
#            if key in self.data:
#                return str(self.data[key])

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headeri[section]

class RestAgregiraniModel(QtCore.QAbstractTableModel):
    """
    prikaz vrijednosti za izabranu minutnu tocku
    """
    def __init__(self, data=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        if self.data is None:
            self.data = {'srednjak':None, 'obuhvat':None}
        else:
            self.data = data
        self.headeri = ['srednjak', 'obuhvat']

    def set_data(self, mapa):
        self.data = mapa
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 1

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        col = index.column()
        if role == QtCore.Qt.DisplayRole and isinstance(self.data, dict):
            if col == 0:
                if 'average' in self.data:
                    return str(self.data['average'])
            elif col == 1:
                if 'obuhvat' in self.data:
                    return str(self.data['obuhvat'])

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headeri[section]

class ZeroSpanModel(QtCore.QAbstractTableModel):
    """
    prikaz vrijednosti zero i span
    """
    def __init__(self, dataZero=None, dataSpan=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)

        if dataZero is None:
            self.dataZero = {'xtocka':'',
                             'ytocka':'',
                             'minDozvoljenoOdstupanje':'',
                             'maxDozvoljenoOdstupanje':'',
                             'status':''}
        else:
            self.dataZero = dataZero

        if dataSpan is None:
            self.dataSpan = {'xtocka':'',
                             'ytocka':'',
                             'minDozvoljenoOdstupanje':'',
                             'maxDozvoljenoOdstupanje':'',
                             'status':''}
        else:
            self.dataSpan = dataSpan

        self.xheaderi = ['vrijeme', 'vrijednost', 'min. odstupanje', 'max. odstupanje', 'status']
        self.yheaderi = ['ZERO', 'SPAN']

    def set_data_zero(self, mapa):
        self.dataZero = mapa
        self.layoutChanged.emit()

    def set_data_span(self, mapa):
        self.dataSpan = mapa
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 2

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 5

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            if row == 0 and isinstance(self.dataZero, dict):
                if col == 0:
                    if 'xtocka' in self.dataZero:
                        return self.dataZero['xtocka']
                elif col == 1:
                    if 'ytocka' in self.dataZero:
                        return self.dataZero['ytocka']
                elif col == 2:
                    if 'minDozvoljenoOdstupanje' in self.dataZero:
                        return self.dataZero['minDozvoljenoOdstupanje']
                elif col == 3:
                    if 'maxDozvoljenoOdstupanje' in self.dataZero:
                        return self.dataZero['maxDozvoljenoOdstupanje']
                elif col == 4:
                    if 'status' in self.dataZero:
                        return self.dataZero['status']
            if row == 1 and isinstance(self.dataSpan, dict):
                if col == 0:
                    if 'xtocka' in self.dataSpan:
                        return self.dataSpan['xtocka']
                elif col == 1:
                    if 'ytocka' in self.dataSpan:
                        return self.dataSpan['ytocka']
                elif col == 2:
                    if 'minDozvoljenoOdstupanje' in self.dataSpan:
                        return self.dataSpan['minDozvoljenoOdstupanje']
                elif col == 3:
                    if 'maxDozvoljenoOdstupanje' in self.dataSpan:
                        return self.dataSpan['maxDozvoljenoOdstupanje']
                elif col == 4:
                    if 'status' in self.dataSpan:
                        return self.dataSpan['status']


    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.xheaderi[section]
            if orientation == QtCore.Qt.Vertical:
                return self.yheaderi[section]

class ZeroSpanRefModel(QtCore.QAbstractTableModel):
    """
    prikaz vrijednosti zero i span
    """
    def __init__(self, frejm=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)

        if not isinstance(frejm, pd.core.frame.DataFrame):
            frejm = pd.DataFrame(columns=['ZERO', 'SPAN'])
            msg = 'ZeroSpanRefModel.__init__() problem. nije zadan frejm. koristim prazan frejm kao default. frejm={0}'.format(str(frejm))
            logging.error(msg)
        self.frejm = frejm

    def set_frejm(self, frejm):
        if not isinstance(frejm, pd.core.frame.DataFrame):
            frejm = pd.DataFrame(columns=['ZERO', 'SPAN'])
            msg = 'ZeroSpanRefModel.set_frejm() problem. nije zadan frejm. koristim prazan frejm kao default. frejm={0}'.format(str(frejm))
            logging.error(msg)
        self.frejm = frejm
        self.layoutChanged.emit()

    def clear_frejm(self):
        frejm = pd.DataFrame(columns=['ZERO', 'SPAN'])
        self.frejm = frejm
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.frejm)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.frejm.columns)

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            value = self.frejm.iloc[row, col]
            if np.isnan(value):
                return ''
            else:
                return str(value)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.frejm.columns[section]
            if orientation == QtCore.Qt.Vertical:
                return str(self.frejm.index[section])

class KomentarModel(QtCore.QAbstractTableModel):
    """
    prikaz frejma komentara
    """
    def __init__(self, frejm=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent=parent)

        if not isinstance(frejm, pd.core.frame.DataFrame):
            frejm = pd.DataFrame(columns=['Kanal', 'Od', 'Do', 'Komentar'])
            msg = 'KomentarModel.__init__() problem. nije zadan frejm. koristim prazan frejm kao default. frejm={0}'.format(str(frejm))
            logging.error(msg)
        self.frejm = frejm

    def set_frejm(self, frejm):
        if not isinstance(frejm, pd.core.frame.DataFrame):
            frejm = pd.DataFrame(columns=['Kanal', 'Od', 'Do', 'Komentar'])
            msg = 'KomentarModel.__init__() problem. nije zadan frejm. koristim prazan frejm kao default. frejm={0}'.format(str(frejm))
            logging.error(msg)
        self.frejm = frejm
        self.layoutChanged.emit()

    def dohvati_tekst_za_red(self, red):
        #TODO!
        try:
            ind = self.frejm.index[red]
            out = self.frejm.loc[ind, 'Komentar']
        except Exception as err:
            logging.error(str(err), exc_info=True)
            out = ''
        finally:
            return out

    def clear_frejm(self):
        self.frejm = pd.DataFrame(columns=['Kanal', 'Od', 'Do', 'Komentar'])
        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.frejm)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        else:
            #TODO!
            return QtCore.Qt.ItemIsEnabled

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        red = self.frejm.index[row]
        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                value = self.frejm.loc[red, 'Kanal']
                return str(int(value))
            elif col == 1:
                value = self.frejm.loc[red, 'Od']
                return str(value)
            elif col == 2:
                value = self.frejm.loc[red, 'Do']
                return str(value)
            elif col == 3:
                value = self.frejm.loc[red, 'Komentar'][0:80]
                return str(value)
            else:
                return ''

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    return 'Kanal'
                elif section == 1:
                    return 'Od'
                elif section == 2:
                    return 'Do'
                elif section == 3:
                    return 'Komentar'
                else:
                    return ''

    def sort(self, column, order):
            """
            Sort stupca u nekom redu
            """
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            if order == QtCore.Qt.DescendingOrder:
                poredak = False
            else:
                poredak = True
            stupac = ''
            if column == 0:
                stupac = 'Kanal'
            elif column == 1:
                stupac = 'Od'
            elif column == 2:
                stupac = 'Do'
            elif column == 3:
                stupac = 'Komentar'
            self.frejm.sort(columns=[stupac], inplace=True, ascending=poredak)
            self.emit(QtCore.SIGNAL("layoutChanged()"))
