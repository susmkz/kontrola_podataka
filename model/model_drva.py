# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 12:01:49 2015
@author: User
"""

from PyQt4 import QtCore, QtGui
import datetime


class TreeItem(object):
    """
    Posebna klasa za tree strukturu.
    Posjeduje 3 bitna membera i hrpu metoda koje se trebaju brinuti da
    QtCore.QAbstractItemModel fonkcionira.

    self._parent --> referencira parent node (takodjer TreeItem objekt)
    self._childItems --> LISTA djece (svi child itemi su TreeItem objekti)
    self._data --> kontenjer koji sadrzi neke podatke (npr, lista, dict...)
    """
    def __init__(self, data, parent=None):
        self._parent = parent
        self._data = data
        self._childItems = []
        if self._parent is not None:
            self._parent._childItems.append(self)

    def child(self, row):
        """
        vrati child za pozicije row
        """
        return self._childItems[row]

    def childCount(self):
        """
        ukupan broj child itema
        """
        return len(self._childItems)

    def childNumber(self):
        """
        vrati indeks pod kojim se ovaj objekt nalazi u listi djece
        parent objekta
        """
        if self._parent is not None:
            return self._parent._childItems.index(self)
        return 0

    def columnCount(self):
        """
        TreeItem objekt se inicijalizira sa "spremnikom" podataka
        ova funkcija vraca broj podataka u spremniku
        """
        return len(self._data)

    def data(self, column):
        """
        funkcija koja dohvaca element iz "spremnika" podataka

        promjeni implementaciju ako se promjeni 'priroda' spremnika
        npr. ako je spremnik integer vrijednost ovo nece raditi
        """
        return self._data[column]

    def parent(self):
        """
        vrati instancu parent objekta
        """
        return self._parent

    def __repr__(self):
        """
        print() reprezentacija objekta

        promjeni implementaciju ako se promjeni 'priroda' spremnika
        npr. ako je spremnik integer vrijednost ovo nece raditi
        """
        return str(self.data(0))


class ModelDrva(QtCore.QAbstractItemModel):
    """
    Specificna implementacija QtCore.QAbstractItemModel, model nije editable!

    Za inicijalizaciju modela bitno je prosljediti root item neke tree strukture
    koja se sastoji od TreeItem instanci.
    """
    def __init__(self, data, parent=None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        self.rootItem = data
        self.usedMjerenja = {} #kalendar status... nested dict

    def set_usedMjerenja(self, skup):
        """
        Setter za ucitana mjerenja. Cilj je u tree view izdvojiti kanale s kojima
        smo radili nesto.
        """
        danas = datetime.datetime.now().strftime('%Y-%m-%d')
        self.usedMjerenja = skup
        #ignore danasnji dan za provjeru spremanja na REST
        for key in self.usedMjerenja:
            if danas in self.usedMjerenja[key]['ok']:
                self.usedMjerenja[key]['ok'].remove(danas)
            if danas in self.usedMjerenja[key]['bad']:
                self.usedMjerenja[key]['bad'].remove(danas)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        funkcija vraca indeks u modelu za zadani red, stupac i parent
        """
        if parent.isValid() and parent.column() != 0:
            return QtCore.QModelIndex()

        parentItem = self.getItem(parent)
        childItem = parentItem.child(row)
        if childItem:
            # napravi index za red, stupac i child
            return self.createIndex(row, column, childItem)
        else:
            # vrati prazan QModelIndex
            return QtCore.QModelIndex()

    def getItem(self, index):
        """
        funckija vraca objekt pod indeksom index, ili rootItem ako indeks
        nije valjan
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.rootItem

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        primarni getter za vrijednost objekta
        za index i ulogu, vraca reprezentaciju view objektu

        ovaj dio ovisi o tipu "kontenjera" TreeItema, poziva se metoda
        TreeItema data. treba pripaziti da li je poziv metode smisleno srocen
        """
        if not index.isValid():
            return None
        item = self.getItem(index)
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return item.data(0)
            elif index.column() == 1:
                return item.data(3)
            elif index.column() == 2:
                return item.data(2)
            elif index.column() == 3:
                return item.data(1)
        if role == QtCore.Qt.BackgroundRole:
            mjerenje = item.data(2)
            if mjerenje == None:
                code = self.provjera_kontrole_postaja(item)
                if code == 1:
                    return QtGui.QBrush(QtGui.QColor(0, 255, 0, alpha=75))
                elif code == 2:
                    return QtGui.QBrush(QtGui.QColor(255, 0, 0, alpha=75))
            if mjerenje in self.usedMjerenja:
                test = self.provjera_kontrole_mjerenje(mjerenje)
                if test:
                    return QtGui.QBrush(QtGui.QColor(0, 255, 0, alpha=75))
                else:
                    return QtGui.QBrush(QtGui.QColor(255, 0, 0, alpha=75))

    def provjera_kontrole_mjerenje(self, mjerenje):
        """
        Helper funkcija za provjeru da li su svi dani za jedno mjerenje spremljeni na REST
        """
        spremljeni = set(self.usedMjerenja[mjerenje]['ok'])
        ucitani = set(self.usedMjerenja[mjerenje]['bad'])
        return ucitani == spremljeni

    def provjera_kontrole_postaja(self, item):
        """
        Helper funkcija za provjeru da li su za neku postaju svi ucitani programi
        mjerenja i dani spremljeni na rest
        """
        ukupniTest = 0
        for child in item._childItems:
            progMjer = child.data(2)
            if progMjer in self.usedMjerenja:
                test = self.provjera_kontrole_mjerenje(progMjer)
                if test:
                    ukupniTest = ukupniTest | 1
                else:
                    ukupniTest = ukupniTest | 2
        """
        return code...
        0 ako niti jedan program mjerenja parenta (postaje) nije ucitan
        1 ako su svi programi mjjerenja koji su ucitani, spremljeni na REST
        2 ako postoji barem jedan program mjerenja koji je ucitan a nije spremljen na REST
        """
        return ukupniTest

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        vrati broj redaka (children objekata) za parent
        """
        parentItem = self.getItem(parent)
        return parentItem.childCount()

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        vrati broj stupaca rootItema
        u principu, ova vrijednost odgovara broju stupaca u treeView widgetu
        te je jako bitna za metodu data ovog modela. Moguce ju je jednostavno
        hardcodirati na neku vrijednost.

        npr. return 1 (view ce imati samo jedan stupac (tree))
        npr. return 2 (view ce imati 2 stupca (tree, sto god odredis u metodi
        data da vrati u tom stupcu))
        """
        return 4

    def parent(self, index):
        """
        vrati parent od TreeItem objekta pod datim indeksom.
        Ako TreeItem name parenta, ili ako je indeks nevalidan, vrati
        defaultni QModelIndex (ostatak modela ga zanemaruje)
        """
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = self.getItem(index)
        parentItem = childItem.parent()
        if parentItem == self.rootItem:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parentItem.childNumber(), 0, parentItem)

    def headerData(self, section, orientation, role):
        """
        headeri
        """
        headeri = ['Stanica/komponenta', 'Formula', 'Id', 'Usporedno']
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headeri[section]

        return None
