# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 10:13:58 2015

@author: User
"""
from PyQt4 import uic

base4, form4 = uic.loadUiType('./app/view/ui_files/auth_login.ui')
class DijalogLoginAuth(base4, form4):
    """Dijalog za login, unos username i passworda"""
    def __init__(self, parent=None):
        super(base4, self).__init__(parent)
        self.setupUi(self)
        # memberi za user/pass
        self.u = None
        self.p = None
        #connection input widgeta
        self.LEUser.textEdited.connect(self.set_user)
        self.LEPass.textEdited.connect(self.set_pswd)

    def set_user(self, x):
        """setter za username"""
        self.u = str(x)

    def set_pswd(self, x):
        """setter za password"""
        self.p = str(x)

    def vrati_postavke(self):
        """getter za uneseni username i password"""
        return self.u, self.p