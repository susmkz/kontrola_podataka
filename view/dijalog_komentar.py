# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 12:30:13 2016

@author: DHMZ-Milic
"""

from PyQt4 import uic

base51, form51 = uic.loadUiType('./app/view/ui_files/dijalog_komentar.ui')
class DijalogKomentar(base51, form51):
    def __init__(self, tmin=None, tmax=None, parent=None):
        super(base51, self).__init__(parent)
        self.setupUi(self)

        self.tmin = tmin
        self.tmax = tmax
        
        self.setup_label()

    def setup_label(self):
        if self.tmin == self.tmax:
            msg = " ".join([
                'Komentar za vrijeme',
                '<b>',
                str(self.tmin),
                '</b>'])
        else:
            msg = " ".join([
                'Komentar za raspon vremena od',
                '<b>',
                str(self.tmin),
                '</b>',
                'do',
                '<b>',
                str(self.tmax),
                '</b>'])
        self.label.setText(msg)

    def set_time_min(self, defaultTimeMin):
        self.tmin = defaultTimeMin
        self.setup_label()
    
    def set_time_max(self, defaultTimeMax):
        self.tmax = defaultTimeMax
        self.setup_label()

    def get_tekst(self):
        return self.plainTextEdit.toPlainText()

    def set_tekst(self, tekst):
        self.plainTextEdit.setPlainText(tekst)
        
    def get_checkbox_state(self):
        return self.checkBoxDodajSvima.isChecked()
        