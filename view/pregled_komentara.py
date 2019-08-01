# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 13:26:36 2016

@author: DHMZ-Milic
"""
import pandas as pd
from PyQt4 import QtGui, QtCore
from app.model.table_model import KomentarModel

class PregledKomentara(QtGui.QWidget):
    def __init__(self, parent=None):
        super(PregledKomentara, self).__init__(parent)

        self.modelKomentara = KomentarModel()
        frejm = pd.DataFrame(columns=['Postaja', 'Kanal', 'Formula', 'Od', 'Do', 'Komentar'])
        self.modelKomentara.set_frejm(frejm)

        self.splitter = QtGui.QSplitter()

        self.plainTextEdit = QtGui.QPlainTextEdit()
        #self.plainTextEdit.setEnabled(False)

        self.filterLabel = QtGui.QLabel('Filter komentara :')
        self.filterLineEdit = QtGui.QLineEdit()
        hlay = QtGui.QHBoxLayout()
        hlay.addWidget(self.filterLabel)
        hlay.addWidget(self.filterLineEdit)

        self.tableView = QtGui.QTableView()
        self.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.resizeColumnsToContents()
        self.tableView.setSortingEnabled(True)

        self.filterProxy = QtGui.QSortFilterProxyModel()
        self.filterProxy.setSourceModel(self.modelKomentara)
        self.filterProxy.setFilterKeyColumn(3)
        self.tableView.setModel(self.filterProxy)

        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.tableView)
        self.splitter.addWidget(self.plainTextEdit)

        lay = QtGui.QVBoxLayout()
        lay.addLayout(hlay)
        lay.addWidget(self.splitter)
        self.setLayout(lay)

        self.tableView.clicked.connect(self.prikazi_puni_tekst)
        self.filterLineEdit.textChanged.connect(self.filterProxy.setFilterRegExp)

    def set_frejm_u_model(self, frejm):
        self.tableView.clearSelection() #TODO! unselect all
        self.plainTextEdit.clear()
        self.modelKomentara.set_frejm(frejm)
        #self.filterProxy.setSourceModel(self.modelKomentara) #TODO!
        self.tableView.resizeColumnsToContents()
        self.tableView.update()

    def prikazi_puni_tekst(self, x):
        #map to source index...
        praviRed = self.filterProxy.mapToSource(x)
        red = praviRed.row()
        tekst = self.modelKomentara.dohvati_tekst_za_red(red)
        self.plainTextEdit.setPlainText(tekst)

    def clear_tab_komentara(self):
        frejm = pd.DataFrame(columns=['Postaja', 'Kanal', 'Formula', 'Od', 'Do', 'Komentar'])
        self.set_frejm_u_model(frejm)
