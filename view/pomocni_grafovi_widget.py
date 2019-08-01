# -*- coding: utf-8 -*-
"""
Created on Fri Feb  6 12:53:28 2015

@author: User
"""
from PyQt4 import QtGui, QtCore, uic
import app.model.table_model as table_model
import app.model.model_drva as model_drva
import app.view.dodavanje_pomocnih as dodavanje_pomocnih


base8, form8 = uic.loadUiType('./app/view/ui_files/pomocni_grafovi_widget.ui')
class PomocniIzbor(base8, form8):
    """
    Widget se sastoji od QtableView instance i dva gumba (za dodavanje i
    brisanje pomocnih grafova)

    inicijalizacija sa ulaznim keyword argumentima:

    defaulti
        --> konfiguracijski objekt aplikacije

    stablo
        --> instanca tree modela programa mjerenja

    cListe
        --> nested lista
        --> lista sa svim dozvoljenim elementima za comboboxeve (u listama)
        --> [markeri, linije]

    opisKanala
        --> dict sa opisom programa mjerenja za svaki programMjerenjaId
        --> informacija o postaji, komponenti...

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
    def __init__(self,
                 parent=None,
                 defaulti=None,
                 stablo=None,
                 cListe=None,
                 opisKanala=None,
                 listHelpera=None):
        super(base8, self).__init__(parent)
        self.setupUi(self)
        # __init__ parametri
        if defaulti == None:
            self.defaulti = {}
        else:
            self.defaulti = defaulti
        self.drvo = stablo
        if cListe == None:
            self.comboListe = []
        else:
            self.comboListe = cListe
        if opisKanala == None:
            self.mapaKanali = {}
        else:
            self.mapaKanali = opisKanala
        if listHelpera == None:
            self.dictHelperi = []
        else:
            self.dictHelperi = listHelpera
        self.tmodel = None
        #dodavanje stabla u tree view... izbor postaje
        self.treeView.setModel(self.drvo)
        #inicijalizacija parametara za tablicu
        initlista = [self.drvo,
                     self.comboListe,
                     self.mapaKanali]
        #inicijalizacija tablice
        self.tableView = Tablica(lista=initlista)
        #set selecting by rows
        self.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        #set selection mode, only one at a time
        self.tableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        #postavljanje tablice u layout dijaloga
        self.tableViewLayout.addWidget(self.tableView)

        #TODO! treba sklepati full tree sa svim kanalima...(bez kombiniranja NO, NO2 isl...)
        self.expandedDrvo = self.return_full_tree_model()

        self.veze()


    def return_full_tree_model(self):
        """
        sklapanje tree modela sa svim pojedinacnim kanalima
        """
        #root objekt za tree strukturu.
        tree = model_drva.TreeItem(['stanice', None, None, None], parent=None)
        #za svaku individualnu stanicu napravi TreeItem objekt, reference objekta spremi u dict
        stanice = []
        for i in sorted(list(self.mapaKanali.keys())):
            stanica = self.mapaKanali[i]['postajaNaziv']
            if stanica not in stanice:
                stanice.append(stanica)
        stanice = sorted(stanice)
        postaje = [model_drva.TreeItem([name, None, None, None], parent=tree) for name in stanice]
        strPostaje = [str(i) for i in postaje]
        for i in self.mapaKanali:
            komponenta = self.mapaKanali[i]['komponentaNaziv']
            stanica = self.mapaKanali[i]['postajaNaziv']  #parent = stanice[stanica]
            formula = self.mapaKanali[i]['komponentaFormula']
            mjernaJedinica = self.mapaKanali[i]['komponentaMjernaJedinica']
            opis = " ".join([formula, '[', mjernaJedinica, ']'])
            usporedno = self.mapaKanali[i]['usporednoMjerenje']
            data = [komponenta, usporedno, i, opis]
            redniBrojPostaje = strPostaje.index(stanica)
            #kreacija TreeItem objekta
            model_drva.TreeItem(data, parent=postaje[redniBrojPostaje])
        #napravi i vrati model
        return model_drva.ModelDrva(tree)


    def setup_table_model(self, x):
        """
        setup table modela ovisno o aktivnom kanalu
        """
        item = self.drvo.getItem(x)
        progmjer = item.data(2)
        if progmjer != None:
            self.tmodel = self.napravi_table_model(progmjer)
            self.tableView.setModel(self.tmodel)
            self.izabraniGlavniKanal = progmjer
            self.dodajGrafGumb.setEnabled(True)

        else:
            self.tmodel = table_model.PomocniGrafovi() #empty model
            self.tableView.setModel(self.tmodel)
            self.izabraniGlavniKanal = None
            self.dodajGrafGumb.setEnabled(False)

    def veze(self):
        """
        Povezivanje kontrolnih widgeta sa akcijama
        """
        self.dodajGrafGumb.clicked.connect(self.dodaj_graf)
        self.makniGrafGumb.clicked.connect(self.makni_pomocni_graf)
        self.treeView.clicked.connect(self.setup_table_model)
        self.connect(self.tableView.delegat,
                     QtCore.SIGNAL('update_dto(PyQt_PyObject)'),
                     self.update_dto)

    def napravi_table_model(self, kanal):
        """
        konstrukcija modela za QTableView
        """
        nLista = []
        pomocni = self.defaulti.dictPomocnih[kanal]
        if len(pomocni) == 0:
            nLista = []
        else:
            for key in pomocni:
                """
                !!!redosljed je jako bitan da model zna gdje su elementi!!!
                slaganje liste, u zagradi je broj indeksa:

                kanal/programMjerenjaId (0),
                postaja (1),
                komponenta naziv (2),
                usporedno (3),
                marker (4),
                merkersize (5),
                line (6),
                linewidth (7),
                rgb (8),
                alpha (9),
                zorder (10),
                label (11)
                """
                programMjerenjaId = int(key)
                postaja = self.mapaKanali[programMjerenjaId]['postajaNaziv']
                komponentaNaziv = self.mapaKanali[programMjerenjaId]['komponentaNaziv']
                usporedno = self.mapaKanali[programMjerenjaId]['usporednoMjerenje']
                # konstrukcija elementa nested liste
                temp = [programMjerenjaId,
                        postaja,
                        komponentaNaziv,
                        usporedno,
                        self.dictHelperi[0][pomocni[key].markerStyle],
                        pomocni[key].markerSize,
                        self.dictHelperi[2][pomocni[key].lineStyle],
                        pomocni[key].lineWidth,
                        pomocni[key].rgb,
                        pomocni[key].alpha,
                        pomocni[key].zorder,
                        pomocni[key].label]
                #dodaj element na nested listu
                nLista.append(temp)
        return table_model.PomocniGrafovi(grafInfo=nLista)

    def dodaj_graf(self):
        """
        Funkcija dodaje graf u table model preko dijaloga za dodavanje pomocnih
        grafova. Dijalog za pomocne grafove definira neke defaultne postavke
        grafa (ne definira postaju/kanal...).
        """
        # dijalog za izbor grafa, inicijaliziraj, prikazi
        if self.mapaKanali is not None:
            if len(self.mapaKanali.keys()) > 0:
                """self.mapaKanali mora biti pun - tree model mora imati elemente
                inace dodavanje nema smisla (nema programa mjerenja)"""
                #poziv dijaloga
                """
                dijalog se instancira na kompliciran nacin, puno opcija...

                1. parent
                    -definira tko je parent modalnom dijalogu
                    -po defaultu je None
                2. default
                    -defaultna lista za pomocni graf, ako se zada prazna lista
                    dijalog OpcijePomocnog ce definirati defaultne vrijednosti
                    -moze se zadati default ako se konstuira lista:
                    [programMjerenjaId, postaja, komponenta, usporedno, marker,
                    marker size, line, line width, rgb tuple, alpha, zorder, label]
                    -preciznije, jedan redak nested liste s kojom se instancira
                    self.tmodel
                3. stablo
                    	-instanca tree modela programa mjerenja
                     -sluzi da bi se unutar OpcijePomocnog mogao instancirati treeView
                     sa svim stanicama/komponentama
                4. copcije
                    -lista od 2 elementa [[lista svih markera], [lista svih linija]]
                    -sluzi za populiranje comboboxeva unutar OpcijePomocnog
                5. mapa
                    -pomocna mapa (nested) sa informacijom o stanici, komponenti, isl.
                    za svaki programMjerenjaId (glavni kljuc)
                    -sluzi da bi iz indeksa treeView-a mogli doci do podataka o stanici
                    komponenti i usprednom mjerenju
                """
                #TODO!
#                dijalog = dodavanje_pomocnih.OpcijePomocnog(
#                    default=None,
#                    stablo=self.drvo,
#                    copcije=self.comboListe,
#                    mapa=self.mapaKanali)
                dijalog = dodavanje_pomocnih.OpcijePomocnog(
                    default=None,
                    stablo=self.expandedDrvo,
                    copcije=self.comboListe,
                    mapa=self.mapaKanali)
                if dijalog.exec_():
                    pomocniKanal = dijalog.vrati_default_graf()
                    #neko mjerenje mora biti izabrano (programMjerenjaId != None)
                    if pomocniKanal[0] is not None:
                        #dodaj pomocniKanal u self.tmodel (table model)
                        self.tmodel.insertRows(0, 1, sto=[pomocniKanal])
                        #dodaj novi dto objekt u defaulte
                        key = pomocniKanal[0]
                        self.defaulti.dodaj_pomocni(self.izabraniGlavniKanal, key)
                        #set vrijednosti
                        self.change_pomocni(self.izabraniGlavniKanal, key, pomocniKanal)
        else:
            #javi problem, model dostupnih programa mjerenja nije uspjesno instanciran
            tekst = 'Mapa sa programima mjerenja nije instancirana.\nNije moguce dodati nove grafove.\nPokusaj obnoviti vezu sa REST servisom.'
            QtGui.QMessageBox.information(self, "Problem kod dodavanja grafova", tekst)

    def change_pomocni(self, masterkey, key, lista):
        """
        promjena graf dto objekta za pomocni graf
        masterkey - kljuc kanala za koji se definiraju pomocni
        key - programMjerenjaId, kljuc u dictu pomocnih
        lista - 'redak' iz tablice sa podacima
        """
        self.defaulti.dictPomocnih[masterkey][key].set_markerStyle(self.dictHelperi[1][lista[4]])
        self.defaulti.dictPomocnih[masterkey][key].set_markerSize(lista[5])
        self.defaulti.dictPomocnih[masterkey][key].set_lineStyle(self.dictHelperi[3][lista[6]])
        self.defaulti.dictPomocnih[masterkey][key].set_lineWidth(lista[7])
        self.defaulti.dictPomocnih[masterkey][key].set_rgb(lista[8])
        self.defaulti.dictPomocnih[masterkey][key].set_alpha(lista[9])
        self.defaulti.dictPomocnih[masterkey][key].set_zorder(lista[10])
        self.defaulti.dictPomocnih[masterkey][key].set_label(lista[11])

    def update_dto(self, lista):
        """
        update postojeceg pomocnog grafa
        """
        key = lista[0]
        self.change_pomocni(self.izabraniGlavniKanal, key, lista)

    def makni_pomocni_graf(self):
        """Brisanje selektiranog reda u qtableview"""
        try:
            indeks = self.tableView.currentIndex()
            red = indeks.row()
            # programMjerenjaId za izabrani index
            keyid = int(indeks.model().grafInfo[red][0])
        except AttributeError:
            red = -1
        if red >= 0:
            self.tmodel.removeRows(red, 1)
            #makni dto objekt iz dicta pomocnih
            self.defaulti.makni_pomocni(self.izabraniGlavniKanal, keyid)


class Tablica(QtGui.QTableView):
    """
    Ova klasa je zaduzena za prikaz modela pomocnih grafova.
    Subklasani QTableView, ciljano zahtjevamo da se odredjeni stupci
    ponasaju drugacije. Delegiramo editiranje modela drugoj klasi

    Cilj je umjesto line editora omoguciti poziv dijaloga za izbor opcija
    pomocnih grafova.
    """
    def __init__(self, parent=None, lista=None):
        QtGui.QTableView.__init__(self, parent)
        self.initLista = lista
        self.delegat = PromjeniPomocniDelegate(self, lista=self.initLista)
        # postavi isti delegate za sva 3 stupca [postaja, komponenta, usporedno]
        self.setItemDelegateForColumn(0, self.delegat)
        self.setItemDelegateForColumn(1, self.delegat)
        self.setItemDelegateForColumn(2, self.delegat)


class PromjeniPomocniDelegate(QtGui.QItemDelegate):
    """
    Mali hack, u biti ne delegira nista, direktno poziva dijalog za
    pomocne grafove. Inicijalizira se sa defaultnim vrijednostima vezanim
    za 'editirani' redak u tablici
    """

    def __init__(self, parent, lista=None):
        QtGui.QItemDelegate.__init__(self, parent)
        if lista is not None:
            #[program mjerenja tree,
            # combo liste za marker i line,
            # info mapa o programima mjerenja]
            self.lista = lista

    def createEditor(self, parent, option, index):
        """
        1. nadji defaultne podatke za redak
        2. inicijaliziraj i prikazi dijalog sa izabranim redkom
        3. ako je OK, postavi nove vrijednosti u tableModel
        """
        # pronadji defultni graf za izabrani redak
        red = index.row()
        grafRed = index.model().grafInfo[red]
        if self.lista is not None:
            #inicijaliziraj i prikazi dijalog sa izabranim redkom
            dijalog = dodavanje_pomocnih.OpcijePomocnog(
                parent=parent,
                default=grafRed,
                stablo=self.lista[0],  #tree programa mjerenja
                copcije=self.lista[1],  #vijednosti za comboboxeve
                mapa=self.lista[2])  #mapa koja povezuje program mjerenja i info (stanica, komponenta...)
            if dijalog.exec_():
                pomocniKanal = dijalog.vrati_default_graf()
                #neko mjerenje mora biti izabrano (programMjerenjaId != None)
                if pomocniKanal[0] is not None:
                    #zamjeni pomocni Kanal sa updateanom verzijom
                    index.model().grafInfo[red] = pomocniKanal
                    #dodatno, update graf dto
                    self.emit(QtCore.SIGNAL('update_dto(PyQt_PyObject)'),
                              pomocniKanal)
