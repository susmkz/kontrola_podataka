# -*- coding: utf-8 -*-
"""
Created on Thu Apr  9 12:27:25 2015

@author: DHMZ-Milic

"""
import logging
import datetime
import matplotlib
import functools
import pandas as pd
import numpy as np
import copy
from PyQt4 import QtGui, QtCore #import djela Qt frejmworka
from app.view.dijalog_komentar import DijalogKomentar
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure #import figure
from matplotlib.widgets import RectangleSelector, SpanSelector
from matplotlib.dates import HourLocator, MinuteLocator, DateFormatter
from matplotlib.dates import AutoDateLocator, AutoDateFormatter
from matplotlib.ticker import NullFormatter, AutoMinorLocator


class Kanvas(FigureCanvas):
    """
    Canvas za prikaz i interakciju sa grafovima
    """
    def __init__(self, konfig, parent=None, width=6, height=5, dpi=100):
        """
        Canvas se inicijalizira sa svojim konfig objektom, mapom pomocnih grafova
        definiranom u objektu tipa KonfigAplikacije u memberu dictPomocnih.
        """
        #osnovna definicija figure, axes i canvasa
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(
            self,
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        #podrska za kontekstni meni
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #bitni memberi
        self.konfig = konfig #konfig dto objekt
        self.data = {} #prazan dict koji ce sadrzavati frejmove sa podacima
        self.gKanal = None #kanal id glavnog kanala
        self.pocetnoVrijeme = None #min zadano vrijeme za prikaz
        self.zavrsnoVrijeme = None #max zadano vrijeme za prikaz
        self.statusGlavniGraf = False #status glavnog grafa (da li je glavni kanal nacrtan)
        self.statusHighlight = False #status prikaza oznacene izabrane tocke
        self.lastHighlight = (None, None) #kooridinate zadnjeg highlighta
        self.legenda = None #placeholder za legendu
        self.highlightSize = 15 #dynamic size za highlight (1.5 puta veci od markera)
        self.xlim_original = [0, 1] #defaultna definicija raspona x osi grafa (zoom)
        self.ylim_original = [0, 1] #defaultna definicija raspona y osi grafa (zoom)
        self.zoomStack = [] #stack za zoom levele

        self.initialize_interaction(self.span_select, self.rect_zoom)
        self.reinit_ticks_grid_legend()

    def initialize_interaction(self, span_func, zoom_func):
        """
        Setup inicijalnih postavki interakcije sa grafom (zoom, cursor, span selector, pick)

        Ulazni argumenti:

        span_func
        -referenca na funkciju koja ce biti callback za span selektor
        -ulazni parametri su 'min' i 'max' vrijednosti x kooridinate raspona.

        zoom_func
        -referenca na funkciju koja ce biti callback za zoom.
        -ulazni parametri su matplotlib canvas click eventi 'event_click' i 'event_release'
        -npr. kooridinate prve tocke su (event_click.xdata, event_click.ydata)
        """
        #caller id za pick callbackove
        self.cid = None #placeholder

        #zoom implement, inicijalizacija rectangle selectora za zoom
        self.zoomBoxInfo = dict(facecolor='yellow',
                                edgecolor='black',
                                alpha=0.5,
                                zorder=10,
                                fill=True)
        #zoom koji se toggla sa clikcom na zoom ikonu
        self.zoomSelector = RectangleSelector(self.axes,
                                              zoom_func,
                                              drawtype='box',
                                              button=1,
                                              useblit=True,
                                              rectprops=self.zoomBoxInfo)
        #permanentni zoom na middle mouse clicku, uvijek aktivan
        self.zoomSelectorPersistent = RectangleSelector(self.axes,
                                                        zoom_func,
                                                        drawtype='box',
                                                        button=2,
                                                        useblit=True,
                                                        rectprops=self.zoomBoxInfo)
        #iskljuci zoom vezan na ljevi klik
        self.zoomSelector.set_active(False)

        if self.konfig.TIP in ['SATNI', 'MINUTNI', 'ZERO', 'SPAN']:
            #span selector, inicijalizacija span selectora (izbor vise tocaka po x osi)
            self.spanBoxInfo = dict(alpha=0.3, facecolor='yellow')
            self.spanSelector = SpanSelector(self.axes,
                                             span_func,
                                             direction='horizontal',
                                             useblit=True,
                                             rectprops=self.spanBoxInfo)

    def reinit_ticks_grid_legend(self):
        """
        Postavljanje stanja tickova i grida.
        """
        #inicijalizacija tickova
        self.axes.minorticks_on()
        #inicijalizacija grida
        if self.konfig.Grid:
            self.axes.grid(which='major',
                           color='black',
                           linestyle='-',
                           linewidth='0.4',
                           alpha=0.6)
            self.axes.grid(which='minor',
                           color='black',
                           linestyle=':',
                           linewidth='0.2',
                           alpha=0.6)
        else:
            self.axes.grid(False, which='both')
        #inicijalizacija legende (ako postoji)
        if self.legenda != None:
            self.legenda.get_frame().set_alpha(0.8)
            #LEGEND - visibility
            self.legenda.set_visible(self.konfig.Legend)


    def toggle_zoom(self):
        """
        Toggle za zoom. funkcija aktivira zoom na grafu, ali samo jednom.
        Svaki zoom in mora ponovno aktivirati funkciju.
        """
        #TODO! zooming
        logging.debug('toggle "single shot" zoom')
        #aktiviraj zoomiranje
        self.zoomSelector.set_active(True)
        #ako postoji span selector, disable radi konfilikta sa ljevim klikom
        if self.spanSelector != None:
            self.spanSelector.visible = False

    def zoom_out_full(self):
        """
        Reset granica x i y osi da pokrivaju isti raspon kao i originalna slika.
        Full zoom out.
        """
        logging.info('full zoom out')
        #clear stack
        self.zoomStack.clear()
        self.axes.set_xlim(self.xlim_original)
        self.axes.set_ylim(self.ylim_original)
        #nacrtaj promjenu
        self.draw()

    def crtaj_scatter(self, x, y, konfig):
        """
        pomocna funkcija za crtanje scatter grafova
        x, y, su liste kooridinata, konfig je cfg objekt sa postavkama grafa
        """
        self.axes.plot(x,
                       y,
                       marker=konfig.markerStyle,
                       markersize=konfig.markerSize,
                       linestyle='None',
                       color=konfig.color,
                       markeredgecolor=konfig.color,
                       zorder=konfig.zorder,
                       label=konfig.label)

    def crtaj_line(self, x, y, konfig):
        """
        pomocna funkcija za crtanje line grafova
        x, y su liste kooridinata, konfig je cfg objekt sa postavkama grafa
        """
        self.axes.plot(x,
                       y,
                       linestyle=konfig.lineStyle,
                       linewidth=konfig.lineWidth,
                       color=konfig.color,
                       zorder=konfig.zorder,
                       label=konfig.label)

    def crtaj_fill(self, x, y1, y2, konfig):
        """
        pomocna funkcija za crtanje fill grafova
        x definira x os, y1 i y2 su granice izmedju kojih se sjenca,
        konfig je cfg objekt sa postavkama grafa"""
        self.axes.fill_between(x,
                               y1,
                               y2,
                               color=konfig.color,
                               zorder=konfig.zorder,
                               label=konfig.label)

    def toggle_grid(self, x):
        """
        Toggle grida on i off, ovisno o ulaznoj vrijednosti x (boolean)
        """
        msg = 'toggle grid, draw status={0}'.format(str(x))
        logging.info(msg)
        self.reinit_ticks_grid_legend()
        self.draw()

    def toggle_legend(self, x):
        """
        Toggle legende on i off, ovisno o ulaznoj vrijednosti x (boolean)
        """
        msg = 'toggle legend, draw status={0}'.format(str(x))
        logging.info(msg)
        self.reinit_ticks_grid_legend()
        self.draw()

    def span_select(self, tmin, tmax):
        """
        span select placeholder, funkcija ima dva ulazna parametra. Minimalnu i
        maksimalnu vrijednosti izabarnog raspona po x kooridinati grafa.
        """
        pass

    def rect_zoom(self, eclick, erelease):
        """
        Primjer callback funkcije za zoom.
        Callback funkcija za rectangle zoom canvasa. Funkcija lovi click i release
        evente (rubovi kvadrata) te povecava izabrani dio slike preko cijelog
        canvasa.
        """
        x = sorted([eclick.xdata, erelease.xdata])
        y = sorted([eclick.ydata, erelease.ydata])
        if x[0] != x[1] and y[0] != y[1]:
            #dodaj zoom tocke na stack
            self.zoomStack.append((x, y))
            #set nove granice osi za sve axese
            for ax in self.fig.axes:
                ax.set_xlim(x)
                ax.set_ylim(y)
            #redraw
            self.draw()
            #disable zoom
            self.zoomSelector.set_active(False)
            #enable spanSelector
            if self.spanSelector != None:
                self.spanSelector.visible = True

    def zoom_out(self):
        """
        Reset granica x i y osi da pokrivaju isti raspon kao i originalna slika.
        Full zoom out.

        vrijednosti su spremljene u memberima u obliku tuple
        self.xlim_original --> (xmin, xmax)
        self.ylim_original --> (ymin, ymax)
        """
        if len(self.zoomStack) > 1:
            self.zoomStack.pop() #makni zadnji element sa zoom stacka
            x, y = self.zoomStack[-1] #prikazi vrijednost elementa odmah ispod
            for ax in self.fig.axes:
                ax.set_xlim(x)
                ax.set_ylim(y)
        else:
            self.axes.set_xlim(self.xlim_original)
            self.axes.set_ylim(self.ylim_original)
        #nacrtaj promjenu
        self.draw()

    def clear_graf(self):
        """
        clear grafa
        """
        self.clear_graf_sans_draw()
        self.draw()

    def clear_graf_sans_draw(self):
        """
        clear grafa
        """
        logging.debug('clear graf')
        self.axes.clear()
        self.zoomStack.clear()
        self.data = {} #spremnik za frejmove (ucitane)
        self.statusGlavniGraf = False
        #redo Axes labels
        self.axes.set_ylabel(self.konfig.TIP)
        self.reinit_ticks_grid_legend()


    def setup_ticks(self):
        """
        Postavljanje pozicije i formata tickova x osi. Reimplementiraj za
        pojedini graf
        """
        pass

    def setup_legend(self):
        """
        Setup legende na canvas.
        """
        self.legenda = self.axes.legend(loc=1,
                                        fontsize=8,
                                        fancybox=True)

    def prosiri_granice_grafa(self, tmin, tmax, t):
        """
        Funkcija 'pomice' rubove intervala [tmin, tmax] na [tmin-t, tmax+t].
        Koristi se da se malo prosiri canvas na kojem se crtaju podaci tako da
        rubne tocke nisu na samom rubu canvasa.

        -> t je integer, broj minuta
        -> tmin, tmax su pandas timestampovi (pandas.tslib.Timestamp)

        izlazne vrijednosti su 2 'pomaknuta' pandas timestampa
        """
        tmin = tmin - datetime.timedelta(minutes=t)
        tmax = tmax + datetime.timedelta(minutes=t)
        tmin = pd.to_datetime(tmin)
        tmax = pd.to_datetime(tmax)
        return tmin, tmax

    def zaokruzi_vrijeme(self, dt_objekt, nSekundi):
        """
        Funkcija zaokruzuje zlazni datetime objekt na najblize vrijeme zadano
        sa nSekundi.

        dt_objekt -> ulaz je datetime.datetime objekt
        nSekundi -> broj sekundi na koje se zaokruzuje, npr.
            60 - minuta
            3600 - sat

        izlaz je datetime.datetime objekt ili None (po defaultu)
        """
        if dt_objekt is None:
            return None
        else:
            tmin = datetime.datetime.min
            delta = (dt_objekt - tmin).seconds
            zaokruzeno = ((delta + (nSekundi / 2)) // nSekundi) * nSekundi
            izlaz = dt_objekt + datetime.timedelta(0, zaokruzeno-delta, -dt_objekt.microsecond)
            return izlaz

    def crtaj(self, frejmovi, mapaParametara):
        """
        Glavna metoda za crtanje grafa.
        Ulazni parametri su:
        frejmovi --> mapa {programMjerenjaId:pandas datafrejm}
        mapaParametara --> dict sa 'meta' podacima (glavni kanal, pocetno vrijeme,
        zavrsno vrijeme....)
        """
        pass


class SatniMinutniKanvas(Kanvas):
    """
    Kanvas klasa sa zajednickim elementima za satni i minutni graf.
    Inicijalizacija sa konfig objektom i mapom pomocnih kanala.
    """
    def __init__(self, konfig, masterkonfig, parent=None, width=6, height=5, dpi=100):
        Kanvas.__init__(self, konfig)
        #mapa pomocnih kanala {kanalId:dto objekt za kanal}
        self.masterKonfig = masterkonfig
        self.statusMap = {} #defaultni satusMap je prazan dict
        self.kontrolaProvedenaBit = None
        self.okolisniUvjetiBit = None
        self.cid = self.mpl_connect('button_press_event', self.on_pick) #callback za pick

    def set_statusMap(self, mapa):
        """
        Setter za dict koji povezuje poziciju bita sa opisom statusa.
        """
        self.statusMap = mapa
        for i in self.statusMap:
            if self.statusMap[i] == 'KONTROLA_PROVEDENA':
                self.kontrolaProvedenaBit = i
            elif self.statusMap[i] == 'OKOLISNI_UVJETI':
                self.okolisniUvjetiBit = i

    def check_bit(self, broj, bit_position):
        """
        Pomocna funkcija za testiranje statusa

        Napravi temporary integer koji ima samo jedan bit vrijednosti 1 na poziciji
        bit_position. Napravi binary and takvog broja i ulaznog broja.
        Ako oba broja imaju bit 1 na istoj poziciji vrati True, inace vrati False.
        """
        if bit_position != None:
            temp = 1 << int(bit_position) #left shift bit za neki broj pozicija
            if int(broj) & temp > 0: # binary and izmjedju ulaznog broja i testnog broja
                return True
            else:
                return False

    def check_status_flags(self, broj):
        """
        provjeri stauts integera broj dekodirajuci ga sa hash tablicom
        {bit_pozicija:opisni string}. Vrati csv string opisa.
        """
        bitchk = [self.check_bit(broj, i) for i in self.statusMap]
        return [bitchk, self.statusMap]

    def crtaj_scatter_value_ovisno_o_flagu(self, komponenta, konfig, flag):
        """
        Pomocna funkcija za crtanje scatter tipa grafa (samo tocke).
        -komponenta je opisni string ( ['min', 'max', 'koncentracija', 'avg'])
        -konfig je objekt sa postavkama grafa
        -flag je int vrijednost flaga za razlikovanje validacije ili None (za sve
        tocke neovisno o flagu)

        Metodu koristi satni i minutni graf jer jedino oni crtaju tocke ovisno
        o flagu. Flag moze biti None, u tom slucaju se crtaju sve tocke (primjer
        je crtanje ekstremnih vrijednosti na satnom grafu).
        """
        frejm = self.data[self.gKanal]
        if flag:
            frejm = frejm[frejm[self.konfig.FLAG] == flag]
        x = list(frejm.index)
        #crtaj samo ako ima podataka
        if len(x):
            if komponenta == 'min':
                y = list(frejm['min'])
            elif komponenta == 'max':
                y = list(frejm['max'])
            elif komponenta == 'koncentracija':
                y = list(frejm['koncentracija'])
            elif komponenta == 'avg':
                y = list(frejm['avg'])
            else:
                return
            #naredba za plot
            self.crtaj_scatter(x, y, konfig)
            self.statusGlavniGraf = True

    def highlight_pick(self, tpl, size):
        """
        naredba za crtanje highlight tocke na grafu na koridinatama
        tpl = (x, y), velicine size.
        """
        msg = 'highlight_pick start. tpl={0} , size={1}'.format(str(tpl), str(size))
        logging.debug(msg)
        x, y = tpl
        if self.statusHighlight:
            if tpl is not self.lastHighlight:
                self.axes.lines.remove(self.highlight[0])
                self.make_highlight(x, y, size)
        else:
            self.make_highlight(x, y, size)
        self.draw()
        logging.debug('highlight_pick, kraj.')


    def make_highlight(self, x, y, size):
        """
        Generiranje instance highlight tocke na kooridinati x, y za prikaz.
        Velicina markera je definirana sa ulaznim parametrom size.
        """
        self.highlight = self.axes.plot(x,
                                        y,
                                        marker='o',
                                        markersize=int(size),
                                        color='yellow',
                                        markeredgecolor='yellow',
                                        alpha=0.5,
                                        zorder=10)
        self.lastHighlight = (x, y)
        self.statusHighlight = True
        #setup odgovarajucih labela tjekom highlighta
        self.setup_annotation_text(x)

    def crtaj_pomocne(self):
        """
        Metoda za crtanje pomocnih grafova.
        """
        logging.debug('crtanje pomocnih grafova, start')
        pomocni = self.masterKonfig.dictPomocnih[self.gKanal]
        for key in pomocni:
            if key in self.data:
                frejm = self.data[key]
                if len(frejm):
                    x = list(frejm.index)
                    y = list(frejm[self.konfig.MIDLINE])
                    self.axes.plot(x,
                                   y,
                                   marker=pomocni[key].markerStyle,
                                   markersize=pomocni[key].markerSize,
                                   linestyle=pomocni[key].lineStyle,
                                   linewidth=pomocni[key].lineWidth,
                                   color=pomocni[key].color,
                                   markeredgecolor=pomocni[key].color,
                                   zorder=pomocni[key].zorder,
                                   label=pomocni[key].label)
        logging.debug('crtanje pomocnih grafova, kraj')

    def crtaj_povezane(self):
        """crtanje povezanih kanala."""
        logging.debug('crtanje povezanih grafova, start')
        povezani = self.masterKonfig.dictPovezanih[self.gKanal]
        for key in povezani:
            if key in self.data:
                frejm = self.data[key]
                if len(frejm):
                    x = list(frejm.index)
                    y = list(frejm[self.konfig.MIDLINE])
                    self.axes.plot(x,
                                   y,
                                   marker=povezani[key].markerStyle,
                                   markersize=povezani[key].markerSize,
                                   linestyle=povezani[key].lineStyle,
                                   linewidth=povezani[key].lineWidth,
                                   color=povezani[key].color,
                                   markeredgecolor=povezani[key].color,
                                   zorder=povezani[key].zorder,
                                   label=povezani[key].label)
        logging.debug('crtanje povezanih grafova, kraj')


    def crtaj_oznake_statusa(self):
        """
        Crtanje oznaka za sve tocke gdje je status razlicit od nule, a da nije
        provedena kontrola nad tim podacima.
        Prikazuje se scatter plot (samo tocke) ispod gornjeg ruba grafa.
        """
        #TODO! problem je false flagging ako nema podataka o temperaturi na istoj postaji
        logging.debug('crtanje status warninga, start')
        if self.konfig.statusWarning.crtaj and self.okolisniUvjetiBit != None:
            frejm = self.data[self.gKanal]
            if isinstance(frejm, pd.core.frame.DataFrame):
                #eliminacija svih kojima je status 0
                frejm = frejm[frejm[self.konfig.STATUS] != 0]
                #u frejmu su samo indeksi koji nisu prije kontrolirani,
                #a imaju neki status kod razlicit od 0

                if self.gKanal not in self.masterKonfig.warningBlackList:
                    #TODO! zanemari okolišne uvijete na određenenim postajama...
                    okolisStatus = 1 << self.okolisniUvjetiBit
                    #samo okolisni uvijeti
                    frame1 = frejm.copy()
                    frame1 = frame1[frame1[self.konfig.STATUS] == okolisStatus]

                    #provjeri da li je frejm prazan prije pokusaja crtanja
                    if len(frame1):
                        x = list(frame1.index)
                        y1, y2 = self.ylim_original
                        c = y2 - 0.05 * abs(y2 - y1)  # odmak od gornjeg ruba za 5% max raspona
                        y = [c for i in x]
                        self.crtaj_scatter(x, y, self.konfig.statusWarningOkolis)

                #ostali statusi
                frame2 = frejm.copy()
                frame2 = frame2[frame2[self.konfig.STATUS] != okolisStatus]

                if len(frame2):
                    x = list(frame2.index)
                    y1, y2 = self.ylim_original
                    c = y2 - 0.05 * abs(y2 - y1)  # odmak od gornjeg ruba za 5% max raspona
                    y = [c for i in x]
                    self.crtaj_scatter(x, y, self.konfig.statusWarning)

        logging.debug('crtanje status warninga, kraj')

    def setup_annotation_text(self, xpoint):
        """
        Definiranje teksta za prikaz annotationa (labeli ispod grafova za izabranu tocku).
        Ulazni parametar je tocka za koju radimo annotation. Funkcija vraca dict
        stringova za labele. Reimplementiraj za satni i minutni graf.
        """
        pass

    def zaokruzi_na_najblize_vrijeme(self, x):
        """
        Metoda sluzi za zaokruzivanje vremena tocke na neku mjernu jedinicu.
        Reimplementiraj za pojedini canvas
        """
        pass

    def adaptiraj_tocku_od_pick_eventa(self, event):
        """
        Metoda je zaduzena da prilagodi podatke iz eventa.
        Metoda vraca x i y kooridinate tocke.
        """
        xpoint = matplotlib.dates.num2date(event.xdata) #datetime.datetime
        #problem.. rounding offset aware i offset naive datetimes..workaround
        xpoint = datetime.datetime(xpoint.year,
                                   xpoint.month,
                                   xpoint.day,
                                   xpoint.hour,
                                   xpoint.minute,
                                   xpoint.second)
        #round na najblize vrijeme
        xpoint = self.zaokruzi_na_najblize_vrijeme(xpoint)
        #konverzija iz datetime.datetime objekta u pandas.tislib.Timestamp
        xpoint = pd.to_datetime(xpoint)
        #pazimo da x vrijednost ne iskace od zadanih granica
        if xpoint >= self.zavrsnoVrijeme:
            xpoint = self.zavrsnoVrijeme
        if xpoint <= self.pocetnoVrijeme:
            xpoint = self.pocetnoVrijeme
        #kooridinate ako nedostaju podaci za highlight
        ymin, ymax = self.axes.get_ylim()
        defaultY = (ymax+ymin) / 2
        if xpoint in list(self.data[self.gKanal].index):
            ypoint = self.data[self.gKanal].loc[xpoint, self.konfig.MIDLINE]
            if ypoint < ymin or ypoint > ymax or str(ypoint) == 'nan':
                ypoint = defaultY
        else:
            ypoint = defaultY

        return xpoint, ypoint

    def on_pick(self, event):
        """
        Resolve pick eventa za satni i minutni graf.
        """
        pass

    def span_select(self, xmin, xmax):
        """
        Primjer callback metode za span selektor.
        Metoda je povezana sa span selektorom (ako je inicijaliziran).
        Metoda je zaduzena da prikaze kontekstni dijalog za promjenu flaga
        na mjestu gdje "releasamo" ljevi klik za satni i minutni graf.

        t1 i t2 su timestampovi, ali ih treba adaptirati iz matplotlib vremena u
        "zaokruzene" pandas timestampove. (na minutnom grafu se zaokruzuje na najblizu
        minutu, dok na satnom na najblizi sat)
        """
        msg = 'span_select called. xmin={0} , xmax={1}'.format(str(xmin), str(xmax))
        logging.debug(msg)
        if self.statusGlavniGraf: #glavni graf mora biti nacrtan
            #konverzija ulaznih vrijednosti u pandas timestampove
            t1 = matplotlib.dates.num2date(xmin)
            t2 = matplotlib.dates.num2date(xmax)
            t1 = datetime.datetime(t1.year, t1.month, t1.day, t1.hour, t1.minute, t1.second)
            t2 = datetime.datetime(t2.year, t2.month, t2.day, t2.hour, t2.minute, t2.second)
            #vremena se zaokruzuju
            t1 = self.zaokruzi_na_najblize_vrijeme(t1)
            t2 = self.zaokruzi_na_najblize_vrijeme(t2)
            #adapt from datetime.datetime objekta u pandas timestamp
            t1 = pd.to_datetime(t1)
            t2 = pd.to_datetime(t2)
            #osiguranje da se ne preskoce granice glavnog kanala (izbjegavanje index errora)
            if t1 < self.pocetnoVrijeme:
                t1 = self.pocetnoVrijeme
            if t1 > self.zavrsnoVrijeme:
                t1 = self.zavrsnoVrijeme
            if t2 < self.pocetnoVrijeme:
                t2 = self.pocetnoVrijeme
            if t2 > self.zavrsnoVrijeme:
                t2 = self.zavrsnoVrijeme
            #tocke ne smiju biti iste (izbjegavamo paljenje dijaloga na ljevi klik)
            if t1 != t2:
                #pronadji lokaciju desnog klika u Qt kooridinatama.
                loc = QtGui.QCursor.pos()
                self.show_context_menu(loc, t1, t2) #poziv kontekstnog menija

    def show_context_menu(self, pos, tmin, tmax):
        """
        Metoda iscrtava kontekstualni meni sa opcijama za promjenom flaga
        na minutnom i satnom grafu.
        Promjena se radi na minutnim podacima pa je nuzno pripaziti kod promjene
        na satnom grafu jer moramo prilikom poziva ove metode pomaknuti tmin
        59 minuta unazad da uhvatimo sve relevantne podatke.
        """
        msg = 'show_context_menu called, pos={0} , tmin={1} , tmax={2}'.format(str(pos), str(tmin), str(tmax))
        logging.debug(msg)
        #zapamti rubna vremena intervala, trebati ce za druge metode
        self.__lastTimeMin = tmin
        self.__lastTimeMax = tmax
        #definiraj menu i postavi akcije u njega
        menu = QtGui.QMenu(self)
        menu.setTitle('Promjeni flag')
        action1 = QtGui.QAction("Flag: dobar", menu)
        action2 = QtGui.QAction("Flag: los", menu)
        action3 = QtGui.QAction("Komentar", menu)
        menu.addAction(action1)
        menu.addAction(action2)
        menu.addAction(action3)
        #povezi akcije menua sa metodama
        action1.triggered.connect(functools.partial(self.promjena_flaga, flag=1000))
        action2.triggered.connect(functools.partial(self.promjena_flaga, flag=-1000))
        action3.triggered.connect(self.dodaj_komentar)
        #prikazi menu na definiranoj tocki grafa
        menu.popup(pos)

    def dodaj_komentar(self, defaultTekst=None, defaultTimeMin=None, defaultTimeMax=None):
        """
        Dodavanje komentara za neki raspon
        """
        popupDijalog = DijalogKomentar(tmin=self.__lastTimeMin, tmax=self.__lastTimeMax)
        if defaultTekst:
            popupDijalog.set_tekst(defaultTekst)
        if defaultTimeMin:
            popupDijalog.set_time_min(defaultTimeMin)
        if defaultTimeMax:
            popupDijalog.set_time_max(defaultTimeMax)
        ok = popupDijalog.exec_()
        if ok:
            tekst = popupDijalog.get_tekst()
            dodajSvima = popupDijalog.get_checkbox_state() #dodavanje svim kanalima na postaji
            mapa = {'kanal':self.gKanal,
                    'od':self.__lastTimeMin,
                    'do':self.__lastTimeMax,
                    'tekst':tekst,
                    'dodajSvima':dodajSvima}
            if not dodajSvima:
                #emit signala za dodavanje komentara
                self.emit(QtCore.SIGNAL('dodaj_novi_komentar(PyQt_PyObject)'), mapa)
            else:
                #ako je checkbox za spremanje na sve kanale koji su na postaji OK, trazi dodatnu provjeru
                potvrda = QtGui.QMessageBox.question(self,
                                                     'Potvrdi spremanje komentara',
                                                     'Da li ste sigurni da zelite dodati komentar svim uredjajima na postaji?',
                                                     QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel)
                if potvrda == QtGui.QMessageBox.Ok:
                    logging.debug('Potvrda za spremanje an sve kanale - OK')
                    #emit signala za dodavanje komentara
                    self.emit(QtCore.SIGNAL('dodaj_novi_komentar(PyQt_PyObject)'), mapa)
                else:
                    logging.debug('Potvrda za spremanje an sve kanale - CANCEL')
                    #redisplay the dialog...
                    self.dodaj_komentar(defaultTekst=tekst,
                                        defaultTimeMin=self.__lastTimeMin,
                                        defaultTimeMax=self.__lastTimeMax)

    def promjena_flaga(self, flag=1):
        """
        Metoda sluzi za promjenu flaga.
        """
        tmin = self.__lastTimeMin
        tmax = self.__lastTimeMax
        arg = {'od': tmin,
               'do': tmax,
               'noviFlag': flag,
               'kanal': self.gKanal}
        #generalni emit za promjenu flaga
        msg = 'emit zahtjeva za promjenom flaga. argumenti={0}'.format(str(arg))
        logging.debug(msg)
        self.emit(QtCore.SIGNAL('promjeni_flag(PyQt_PyObject)'), arg)

    def crtaj(self, frejmovi, mapaParametara):
        """
        PROMJENA : direktno prosljedjivanje frejmova za crtanje...bez signala

        Glavna metoda za crtanje na canvas. Eksplicitne naredbe za crtanje.
        ulazni argumenti:
        frejmovi:
        -Mapa programMjerenjaId:pandas dataframe.
        -Podaci za crtanje

        mapaParametara:
        -mapa sa potrebnim parametrima
        -mapaParametara['kanalId'] --> program mjerenja id glavnog kanala [int]
        -mapaParametara['pocetnoVrijeme'] --> pocetno vrijeme [pandas timestamp]
        -mapaParametara['zavrsnoVrijeme'] --> zavrsno vrijeme [pandas timestamp]
        """
        logging.debug('crtaj, start')
        #clear prethodnog grafa
        self.clear_graf_sans_draw()
        #reinicijalizacija membera i podataka
        self.data = frejmovi
        self.pocetnoVrijeme = mapaParametara['pocetnoVrijeme']
        self.zavrsnoVrijeme = mapaParametara['zavrsnoVrijeme']
        self.gKanal = mapaParametara['kanalId']
        if self.gKanal in self.data:
            #naredba za crtanje glavnog grafa, overload za pojedini graf
            self.crtaj_glavni_kanal()
            #naredba za crtanje povezanih
            self.crtaj_povezane()
            #naredba za crtanje pomocnih
            self.crtaj_pomocne()
            ###micanje tocaka od rubova, tickovi, legenda...
            self.setup_limits()
            self.setup_legend()
            self.setup_ticks()
            self.reinit_ticks_grid_legend()
            #toggle ticks, legend, grid
            self.crtaj_oznake_statusa()
            #highlight prijasnje tocke
            if self.statusHighlight:
                hx, hy = self.lastHighlight
                if hx in self.data[self.gKanal].index:
                    #pronadji novu y vrijednosti indeksa
                    hy = self.data[self.gKanal].loc[hx, self.konfig.MIDLINE]
                    self.make_highlight(hx, hy, self.highlightSize)
                else:
                    self.statusHighlight = False
                    self.lastHighlight = (None, None)
                    #reset labele u panelu --
                    self.setup_annotation_text('')
        else:
            self.axes.text(0.5,
                           0.5,
                           'Nije moguce pristupiti podacima za trazeni kanal.',
                           horizontalalignment='center',
                           verticalalignment='center',
                           fontsize=8,
                           transform=self.axes.transAxes)
        self.draw()
        logging.debug('crtaj, kraj')


class SatniKanvas(SatniMinutniKanvas):
    """
    Klasa kanvasa za satni graf.
    Inicijalizacija sa konfig objektom i mapom pomocnih kanala
    """
    def __init__(self, konfig, pomocni, parent=None, width=6, height=5, dpi=100):
        SatniMinutniKanvas.__init__(self, konfig, pomocni)
        self.highlightSize = 1.5 * self.konfig.VOK.markerSize
        self.axes.set_ylabel(self.konfig.TIP)

    def setup_ticks(self):
        """
        Postavljanje pozicije i formata tickova x osi.
        """
        ndana = self.zavrsnoVrijeme - self.pocetnoVrijeme
        #major ticks
        majorLocator = HourLocator(interval=ndana.days+1)
        majorFormat = DateFormatter('%H:%M')
        #minor ticks
        minorLocator = AutoMinorLocator(n=4)
        minorFormat = NullFormatter()

        self.axes.xaxis.set_major_locator(majorLocator)
        self.axes.xaxis.set_major_formatter(majorFormat)
        self.axes.xaxis.set_minor_locator(minorLocator)
        self.axes.xaxis.set_minor_formatter(minorFormat)

        self.fig.autofmt_xdate()
        allXLabels = self.axes.get_xticklabels(which='both') #dohvati sve labele
        for label in allXLabels:
            #label.set_rotation(30)
            label.set_fontsize(8)

    def crtaj_glavni_kanal(self):
        """
        crtanje podataka glavnog kanala.
        """
        #midline
        frejm = self.data[self.gKanal]
        if type(frejm) == pd.core.frame.DataFrame:
            x = list(frejm.index)
            y = list(frejm[self.konfig.MIDLINE])
            logging.debug('crtanje glavnog kanala - midline')
            self.crtaj_line(x, y, self.konfig.Midline)
            #fill izmedju komponenti
            if self.konfig.Fill.crtaj:
                logging.debug('crtanje glavnog kanala - fill')
                self.crtaj_fill(x,
                                list(frejm[self.konfig.Fill.komponenta1]),
                                list(frejm[self.konfig.Fill.komponenta2]),
                                self.konfig.Fill)
            #ekstremi min i max
            if self.konfig.EksMin.crtaj:
                logging.debug('crtanje glavnog kanala - min, max ekstremi')
                self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MINIMUM,
                                                        self.konfig.EksMin,
                                                        None)
                self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MAKSIMUM,
                                                        self.konfig.EksMax,
                                                        None)
            #plot tocaka ovisno o flagu i validaciji
            logging.debug('crtanje glavnog kanala - validan ok')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.VOK,
                                                    1000)
            logging.debug('crtanje glavnog kanala - validan los')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.VBAD,
                                                    -1000)
            logging.debug('crtanje glavnog kanala - nevalidan ok')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.NVOK,
                                                    1)
            logging.debug('crtanje glavnog kanala - nevalidan los')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.NVBAD,
                                                    -1)
            self.statusGlavniGraf = True

    def setup_limits(self):
        """
        Prosirivanje granica grafa da ticke nisu na rubu.
        Konacne granice se spremaju u member xlim_original i ylim_original
        radi implementacije zoom out metode.
        """
        #odmakni x granice za specificni interval ovisno o tipu
        tmin, tmax = self.prosiri_granice_grafa(self.pocetnoVrijeme, self.zavrsnoVrijeme, 60)
        #set granice za max zoom out
        self.xlim_original = (tmin, tmax)
        self.ylim_original = self.axes.get_ylim()
        y1, y2 = self.ylim_original
        c = abs(y2 - y1) * 0.1
        self.ylim_original = (y1, y2 + c)
        #set granice grafa
        self.axes.set_xlim(self.xlim_original)
        self.axes.set_ylim(self.ylim_original)
        #set limite prilikom crtanja na zoom stack
        self.zoomStack.append((self.xlim_original, self.ylim_original))

    def setup_annotation_text(self, xpoint):
        """
        Definiranje teksta za prikaz annotationa (sto ce biti unutar annotationa).
        Ulazni parametar je tocka za koju radimo annotation. Funkcija vraca string
        teksta annotationa.
        """
        output = {'vrijeme':'',
                  'average':'',
                  'min': '',
                  'max': '',
                  'count':'',
                  'status':[[], self.statusMap]}
        if xpoint in list(self.data[self.gKanal].index):
            ystatus = self.data[self.gKanal].loc[xpoint, self.konfig.STATUS]
            ystatus = self.check_status_flags(ystatus)
            output = {'vrijeme':str(xpoint),
                      'average':round(self.data[self.gKanal].loc[xpoint, self.konfig.MIDLINE], 3),
                      'min':round(self.data[self.gKanal].loc[xpoint, self.konfig.MINIMUM], 3),
                      'max':round(self.data[self.gKanal].loc[xpoint, self.konfig.MAKSIMUM], 3),
                      'count':int(self.data[self.gKanal].loc[xpoint, self.konfig.COUNT]),
                      'status':ystatus}
        #emit signal to update
        self.emit(QtCore.SIGNAL('set_labele_satne_tocke(PyQt_PyObject)'), output)

    def zaokruzi_na_najblize_vrijeme(self, xpoint):
        """
        Metoda sluzi za zaokruzivanje vremena zadanog ulaznim parametrom xpoint na
        najblizi puni sat.
        """
        return self.zaokruzi_vrijeme(xpoint, 3600)

    def on_pick(self, event):
        """
        Resolve pick eventa za satni graf.
        ljevi klik misa --> highlight tocke i naredba za crtanje minutnog grafa
        desni klik misa --> poziv kontektsnog menija za promjenu flaga
        """
        msg = 'pick event = {0}'.format(str(event))
        logging.debug(msg)
        if self.statusGlavniGraf and event.inaxes == self.axes:
            if not self.zoomSelector.get_active(): #zanemari pick opcije ako je aktivan zoom
                xpoint, ypoint = self.adaptiraj_tocku_od_pick_eventa(event)
                if event.button == 1:
                    logging.debug('emit naredbe za crtanje minutnog grafa')
                    #crtanje minutnog
                    self.emit(QtCore.SIGNAL('crtaj_minutni_graf(PyQt_PyObject)'),
                              xpoint)
                    #highlight odabir, size pointa
                    self.highlight_pick((xpoint, ypoint),
                                        self.highlightSize)
                elif event.button == 3:
                    logging.debug('emit naredbe za crtanje minutnog grafa')
                    #crtanje minutnog
                    self.emit(QtCore.SIGNAL('crtaj_minutni_graf(PyQt_PyObject)'),
                              xpoint)
                    #napravi button release event za spanSelector
                    mouseEventRelease = matplotlib.backend_bases.MouseEvent('button_release_event',
                                                                            event.canvas,
                                                                            event.x,
                                                                            event.y,
                                                                            button=3,
                                                                            key=event.key,
                                                                            step=event.step,
                                                                            dblclick=event.dblclick,
                                                                            guiEvent=event.guiEvent)
                    #moram direktno releasati spanSelector sa modificiranim mouse eventom
                    self.spanSelector.release(mouseEventRelease)
                    #highlight odabir, size pointa
                    self.highlight_pick((xpoint, ypoint),
                                        self.highlightSize)
                    loc = QtGui.QCursor.pos() #lokacija klika
                    #odmakni donj limit intervala za 59 minuta od izabrane tocke xpoint
                    lowlim = xpoint - datetime.timedelta(minutes=59)
                    lowlim = pd.to_datetime(lowlim)
                    #interval koji treba promjeniti
                    self.show_context_menu(loc, lowlim, xpoint)

    def span_select(self, xmin, xmax):
        """
        Primjer callback metode za span selektor.
        Metoda je povezana sa span selektorom (ako je inicijaliziran).
        Metoda je zaduzena da prikaze kontekstni dijalog za promjenu flaga
        na mjestu gdje "releasamo" ljevi klik za satni i minutni graf.

        t1 i t2 su timestampovi, ali ih treba adaptirati iz matplotlib vremena u
        "zaokruzene" pandas timestampove. (na minutnom grafu se zaokruzuje na najblizu
        minutu, dok na satnom na najblizi sat)
        """
        msg = 'span_select called. xmin={0} , xmax={1}'.format(str(xmin), str(xmax))
        logging.debug(msg)
        if self.statusGlavniGraf: #glavni graf mora biti nacrtan
            #konverzija ulaznih vrijednosti u pandas timestampove
            t1 = matplotlib.dates.num2date(xmin)
            t2 = matplotlib.dates.num2date(xmax)
            t1 = datetime.datetime(t1.year, t1.month, t1.day, t1.hour, t1.minute, t1.second)
            t2 = datetime.datetime(t2.year, t2.month, t2.day, t2.hour, t2.minute, t2.second)
            #vremena se zaokruzuju
            t1 = self.zaokruzi_na_najblize_vrijeme(t1)
            t2 = self.zaokruzi_na_najblize_vrijeme(t2)
            #adapt from datetime.datetime objekta u pandas timestamp
            t1 = pd.to_datetime(t1)
            t2 = pd.to_datetime(t2)
            #osiguranje da se ne preskoce zadane granice grafa
            if t1 < self.pocetnoVrijeme:
                t1 = self.pocetnoVrijeme
            if t1 > self.zavrsnoVrijeme:
                t1 = self.zavrsnoVrijeme
            if t2 < self.pocetnoVrijeme:
                t2 = self.pocetnoVrijeme
            if t2 > self.zavrsnoVrijeme:
                t2 = self.zavrsnoVrijeme
            #tocke ne smiju biti iste (izbjegavamo paljenje dijaloga na ljevi klik)
            if t1 != t2:
                #pronadji lokaciju u Qt kooridinatama.
                loc = QtGui.QCursor.pos()
                #odmakni donj limit intervala za 59 minuta od izabrane tocke xpoint
                lowlim = t1 - datetime.timedelta(minutes=59)
                lowlim = pd.to_datetime(lowlim)
                self.show_context_menu(loc, lowlim, t2) #poziv kontekstnog menija

class SatniRestKanvas(SatniKanvas):
    """
    Klasa za prikaz satno agregiranih srednjaka preuzetih direktno sa REST servisa.
    """
    def __init__(self, konfig, parent=None, width=6, height=5, dpi=100):
        SatniKanvas.__init__(self, konfig, pomocni={}) #nema pomocnih, zato prosljedjen prazan dict
        self.axes.set_ylabel(self.konfig.TIP)
        self.axes.figure.subplots_adjust(top=0.98)
        self.axes.figure.subplots_adjust(bottom=0.08)
        self.axes.figure.subplots_adjust(left=0.08)
        self.axes.figure.subplots_adjust(right=0.98)
        self.spanSelector = None

    def setup_ticks(self):
        """
        automatsko postavljane tickova i labela
        """
        locator = AutoDateLocator(minticks=5, maxticks=24, interval_multiples=True)
        majorTickFormat = AutoDateFormatter(locator, defaultfmt='%Y-%m-%d')
        majorTickFormat.scaled[30.] = '%Y-%m-%d'
        majorTickFormat.scaled[1.0] = '%Y-%m-%d'
        majorTickFormat.scaled[1. / 24.] = '%H:%M:%S'
        majorTickFormat.scaled[1. / (24. * 60.)] = '%M:%S'
        self.axes.xaxis.set_major_locator(locator)
        self.axes.xaxis.set_major_formatter(majorTickFormat)
        self.fig.autofmt_xdate()
        allXLabels = self.axes.get_xticklabels(which='both') #dohvati sve labele
        for label in allXLabels:
            #label.set_rotation(30)
            label.set_fontsize(8)

    def crtaj(self, frejmovi, mapaParametara):
        """
        PROMJENA : direktno prosljedjivanje frejmova za crtanje...bez signala

        Glavna metoda za crtanje na canvas. Eksplicitne naredbe za crtanje.
        ulazni argumenti:
        frejmovi:
        -Mapa programMjerenjaId:pandas dataframe.
        -Podaci za crtanje

        mapaParametara:
        -mapa sa potrebnim parametrima
        -mapaParametara['kanalId'] --> program mjerenja id glavnog kanala [int]
        -mapaParametara['pocetnoVrijeme'] --> pocetno vrijeme [pandas timestamp]
        -mapaParametara['zavrsnoVrijeme'] --> zavrsno vrijeme [pandas timestamp]
        """
        logging.debug('crtaj, start')
        #clear prethodnog grafa, reinicijalizacija membera
        self.clear_graf_sans_draw()
        self.data = frejmovi
        self.pocetnoVrijeme = mapaParametara['pocetnoVrijeme']
        self.zavrsnoVrijeme = mapaParametara['zavrsnoVrijeme']
        self.gKanal = mapaParametara['kanalId']
        if self.gKanal in self.data.keys():
            #naredba za crtanje glavnog grafa
            self.crtaj_glavni_kanal()
            ###micanje tocaka od rubova, tickovi, legenda...
            self.setup_limits()
            self.setup_legend()
            self.setup_ticks()
            self.reinit_ticks_grid_legend()
            #highlight prijasnje tocke
            if self.statusHighlight:
                hx, hy = self.lastHighlight
                if hx in self.data[self.gKanal].index:
                    #pronadji novu y vrijednosti indeksa
                    hy = self.data[self.gKanal].loc[hx, self.konfig.MIDLINE]
                    self.make_highlight(hx, hy, self.highlightSize)
                else:
                    self.statusHighlight = False
                    self.lastHighlight = (None, None)
                    #reset labele u panelu --
                    self.setup_annotation_text('')
            self.draw()
        else:
            self.axes.text(
                0.5,
                0.5,
                'Nije moguce pristupiti podacima za trazeni kanal.',
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=8,
                transform=self.axes.transAxes)
            self.draw()
        logging.debug('crtaj, kraj')

    def crtaj_glavni_kanal(self):
        """
        Metoda za crtanje glavnog grafa, overload za pojedini graf
        """
        logging.debug('crtaj_glavni_kanal, start')
        frejm = self.data[self.gKanal]
        if type(frejm) == pd.core.frame.DataFrame:
            frejm = frejm[frejm[self.konfig.MIDLINE] > -99]
            srednjaci = frejm[self.konfig.MIDLINE]
            srednjaci = srednjaci.asfreq('H') #resample na satne intervale, NaN gdje nema podataka
            #graf koji se crta bi trebao imati 'rupe' tamo gdje nema podataka
            x = list(srednjaci.index)
            y = list(srednjaci)
            self.crtaj_line(x, y, self.konfig.Midline)
            self.statusGlavniGraf = True
        logging.debug('crtaj_glavni_kanal, end')

    def on_pick(self, event):
        """
        Resolve pick eventa.
        """
        msg = 'pick event = {0}'.format(str(event))
        logging.debug(msg)
        if self.statusGlavniGraf and event.inaxes == self.axes:
            if not self.zoomSelector.get_active(): #zanemari pick opcije ako je aktivan zoom
                xpoint, ypoint = self.adaptiraj_tocku_od_pick_eventa(event)
                if event.button == 1:
                    self.highlight_pick((xpoint, ypoint), self.highlightSize)

    def setup_annotation_text(self, xpoint):
        """
        Definiranje teksta za prikaz annotationa.
        Ulazni parametar je tocka za koju radimo annotation. Funkcija vraca string
        teksta annotationa.
        """
        output = {'vrijeme': '',
                  'average': '',
                  'obuhvat': '',
                  'status': [[], self.statusMap]}
        if xpoint in list(self.data[self.gKanal].index):
            ystatus = self.data[self.gKanal].loc[xpoint, self.konfig.STATUS]
            ystatus = self.check_status_flags(ystatus)
            output = {'vrijeme':str(xpoint),
                      'average':round(self.data[self.gKanal].loc[xpoint, self.konfig.MIDLINE], 3),
                      'obuhvat':self.data[self.gKanal].loc[xpoint, self.konfig.COUNT],
                      'status':ystatus}
        #emit signal to update label
        self.emit(QtCore.SIGNAL('set_labele_rest_satne_tocke(PyQt_PyObject)'), output)

    def span_select(self, xmin, xmax):
        pass


class MinutniKanvas(SatniMinutniKanvas):
    """
    Klasa kanvasa za minutni graf.
    Inicijalizacija sa konfig objektom i mapom pomocnih kanala
    """
    def __init__(self, konfig, pomocni, parent=None, width=6, height=5, dpi=100):
        SatniMinutniKanvas.__init__(self, konfig, pomocni)
        self.highlightSize = 1.5 * self.konfig.VOK.markerSize
        self.axes.set_ylabel(self.konfig.TIP)

    def setup_ticks(self):
        """
        Postavljanje pozicije i formata tickova x osi.
        """
        #major ticks
        majorLocator = MinuteLocator(interval=5)
        majorFormat = DateFormatter('%H:%M')
        minorLocator = AutoMinorLocator(n=5)
        minorFormat = NullFormatter()

        self.axes.xaxis.set_major_locator(majorLocator)
        self.axes.xaxis.set_major_formatter(majorFormat)
        self.axes.xaxis.set_minor_locator(minorLocator)
        self.axes.xaxis.set_minor_formatter(minorFormat)

        self.fig.autofmt_xdate()
        allXLabels = self.axes.get_xticklabels(which='both') #dohvati sve labele
        for label in allXLabels:
            #label.set_rotation(30)
            label.set_fontsize(8)

    def crtaj_glavni_kanal(self):
        """
        crtanje podataka glavnog kanala.
        """
        logging.debug('crtaj_glavni_kanal, start')
        #midline
        frejm = self.data[self.gKanal]
        if type(frejm) == pd.core.frame.DataFrame:
            x = list(frejm.index)
            y = list(frejm[self.konfig.MIDLINE])
            logging.debug('crtaj glavni kanal --> midline')
            self.crtaj_line(x, y, self.konfig.Midline)
            #plot tocaka ovisno o flagu i validaciji
            logging.debug('crtaj glavni kanal --> validan ok')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.VOK,
                                                    1000)
            logging.debug('crtaj glavni kanal --> validan los')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.VBAD,
                                                    -1000)
            logging.debug('crtaj glavni kanal --> nevalidan ok')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.NVOK,
                                                    1)
            logging.debug('crtaj glavni kanal --> nevalidan los')
            self.crtaj_scatter_value_ovisno_o_flagu(self.konfig.MIDLINE,
                                                    self.konfig.NVBAD,
                                                    -1)
            self.statusGlavniGraf = True
        logging.debug('crtaj_glavni_kanal, kraj')

    def setup_limits(self):
        """
        Prosirivanje granica grafa da ticke nisu na rubu.
        Konacne granice se spremaju u member xlim_original i ylim_original
        radi implementacije zoom out metode.
        """
        #odmakni x granice za specificni interval ovisno o tipu
        tmin, tmax = self.prosiri_granice_grafa(self.pocetnoVrijeme, self.zavrsnoVrijeme, 4)
        #set granice za max zoom out
        self.xlim_original = (tmin, tmax)
        self.ylim_original = self.axes.get_ylim()
        y1, y2 = self.ylim_original
        c = abs(y2 - y1) * 0.1
        self.ylim_original = (y1, y2 + c)
        #set granice grafa
        self.axes.set_xlim(self.xlim_original)
        self.axes.set_ylim(self.ylim_original)
        #set limite prilikom crtanja na zoom stack
        self.zoomStack.append((self.xlim_original, self.ylim_original))

    def setup_annotation_text(self, xpoint):
        """
        Definiranje teksta za prikaz annotationa (sto ce biti unutar annotationa).
        Ulazni parametar je tocka za koju radimo annotation. Funkcija vraca string
        teksta annotationa.
        """
        output = {'vrijeme': '',
                  'koncentracija': '',
                  'id':0,
                  'status': [[], self.statusMap]}
        if xpoint in list(self.data[self.gKanal].index):
            ystat = self.data[self.gKanal].loc[xpoint, self.konfig.STATUS]
            ystat = self.check_status_flags(ystat)
            konc = round(self.data[self.gKanal].loc[xpoint, self.konfig.MIDLINE], 3)
            output = {'vrijeme': str(xpoint),
                      'koncentracija':konc,
                      'status': ystat,
                      'id':self.data[self.gKanal].loc[xpoint, 'id']}
        #emit za promjenu minutnog statusa
        self.emit(QtCore.SIGNAL('set_labele_minutne_tocke(PyQt_PyObject)'), output)

    def zaokruzi_na_najblize_vrijeme(self, xpoint):
        """
        Metoda sluzi za zaokruzivanje vremena zadanog ulaznim parametrom xpoint na
        najblizu punu minutu.
        """
        return self.zaokruzi_vrijeme(xpoint, 60)

    def on_pick(self, event):
        """
        Resolve pick eventa za minutni graf.
        ljevi klik misa --> highlight tocke i naredba za crtanje minutnog grafa
        desni klik misa --> poziv kontektsnog menija za promjenu flaga
        """
        msg = 'pick event = {0}'.format(str(event))
        logging.debug(msg)
        if self.statusGlavniGraf and event.inaxes == self.axes:
            if not self.zoomSelector.get_active(): #zanemari pick opcije ako je aktivan zoom
                xpoint, ypoint = self.adaptiraj_tocku_od_pick_eventa(event)
                if event.button == 1:
                    #highlight odabir, size pointa
                    self.highlight_pick((xpoint, ypoint), self.highlightSize)
                elif event.button == 3:
                    #napravi button release event za spanSelector
                    mouseEventRelease = matplotlib.backend_bases.MouseEvent('button_release_event',
                                                                            event.canvas,
                                                                            event.x,
                                                                            event.y,
                                                                            button=3,
                                                                            key=event.key,
                                                                            step=event.step,
                                                                            dblclick=event.dblclick,
                                                                            guiEvent=event.guiEvent)
                    #moram direktno releasati spanSelector sa modificiranim mouse eventom
                    self.spanSelector.release(mouseEventRelease)
                    #highlight odabir, size pointa
                    self.highlight_pick((xpoint, ypoint), self.highlightSize)
                    loc = QtGui.QCursor.pos() #lokacija klika
                    #interval koji treba promjeniti
                    self.show_context_menu(loc, xpoint, xpoint)


class ZeroSpanKanvas(Kanvas):
    """
    Kanvas klasa sa zajednickim elementima za zero i span graf.
    Inicijalizacija sa konfig objektom
    """
    def __init__(self, konfig, parent=None, width=6, height=5, dpi=100):
        Kanvas.__init__(self, konfig)
        self.cid = self.mpl_connect('pick_event', self.on_pick)
        #self.spanSelector = None
        #zoom support
        paket = {'x':self.xlim_original,
                 'y':self.ylim_original,
                 'tip':self.konfig.TIP}
        self.emit(QtCore.SIGNAL('report_original_size(PyQt_PyObject)'), paket)

    def pronadji_najblizi_time_indeks(self, lista, vrijednost):
        """
        Helper funkcija za pronalazak najblizeg indeksa (po vrijednosti) od zadane
        vrijednosti.
        Pretpostavka:
        -lista je pandas dataframe indeks (pandas timestampovi)
        -vrijednost je takodjer pandas timestamp
        """
        msg = 'pronadji_najblizi_time_indeks, lista={0} , vrijednost={1}'.format(str(lista), str(vrijednost))
        logging.debug(msg)
        #1 sklepaj np.array od liste
        inList = np.array(lista)
        #2 sklepaj konstanti np.array sa vrijednosti iste duljine kao i ulazna lista
        const = [vrijednost for i in range(len(lista))]
        const = np.array(const, dtype='datetime64[ns]') #tip mora odgovarati
        #oduzmi dvije liste teprimjeni apsolutnu vrijednost na ostatak.
        #minimum tako dobivene liste je najbliza vrijednost
        najblizi = (np.abs(inList - const)).argmin()
        msg = 'najblizi indeks={0}'.format(str(najblizi))
        logging.debug(msg)
        return najblizi

    def pick_nearest(self, argList):
        """
        Nakon sto netko na komplementarnom grafu izabere index, pronadji najblizi
        te ga highlitaj i updateaj labele na panelu

        argList je dict

        argList = {'xtocka': str(x),
                   'ytocka': str(y),
                   'minDozvoljenoOdstupanje': str(minD),
                   'maxDozvoljenoOdstupanje': str(maxD),
                   'status': str(status)}
        """
        msg = 'pick_nearest, arg={0}'.format(str(argList))
        logging.debug(msg)
        if self.statusGlavniGraf:
            ind = self.pronadji_najblizi_time_indeks(self.data.index, argList['xtocka'])
            x = self.data.index[ind]
            y = self.data.loc[x, self.konfig.MIDLINE]
            minD = 'not defined'
            maxD = 'not defined'
            status = 'not defined'
            if self.konfig.WARNING_LOW in self.data.columns:
                minD = self.data.loc[x, self.konfig.WARNING_LOW]
                maxD = self.data.loc[x, self.konfig.WARNING_HIGH]
                # ako postoje vise istih indeksa, uzmi zadnji
                if type(y) is pd.core.series.Series:
                    y = y[-1]
                    minD = minD[-1]
                    maxD = maxD[-1]
                if y >= minD and y <= maxD:
                    status = 'Dobar'
                else:
                    status = 'Ne valja'
            newArgMap = {'xtocka': str(x),
                         'ytocka': str(y),
                         'minDozvoljenoOdstupanje': str(minD),
                         'maxDozvoljenoOdstupanje': str(maxD),
                         'status': str(status)}
            msg = 'pick_nearest, output argument list={0}'.format(str(newArgMap))
            logging.debug(msg)
            self.highlight_pick((x, y), self.highlightSize)
            self.updateaj_labele_na_panelu('normal', newArgMap)

    def pripremi_zero_span_podatke_za_crtanje(self):
        """Pripremanje podataka za crtanje zero/span. Funkcija vraca dictionary
        sa podacima koji se dalje koriste za crtanje"""
        logging.debug('pripremi zero/span podatke za crtanje, start')
        #priprema podataka za crtanje
        frejm = self.data
        x = list(frejm.index) #svi indeksi
        y = list(frejm[self.konfig.MIDLINE]) #sve vrijednosti
        warningUp = y
        warningLow = y
        xok = []
        yok = []
        xbad = x
        ybad = y
        if self.konfig.WARNING_HIGH in frejm.columns and self.konfig.WARNING_LOW in frejm.columns:
            warningUp = list(frejm[self.konfig.WARNING_HIGH]) #warning up
            warningLow = list(frejm[self.konfig.WARNING_LOW]) #warning low
            #pronalazak samo ok tocaka
            tempfrejm = self.data.copy()
            okTocke = tempfrejm[tempfrejm[self.konfig.MIDLINE] <= tempfrejm[self.konfig.WARNING_HIGH]]
            okTocke = okTocke[okTocke[self.konfig.MIDLINE] >= okTocke[self.konfig.WARNING_LOW]]
            xok = list(okTocke.index)
            yok = list(okTocke[self.konfig.MIDLINE])
            #pronalazak losih tocaka
            tempfrejm = self.data.copy()
            badOver = tempfrejm[tempfrejm[self.konfig.MIDLINE] > tempfrejm[self.konfig.WARNING_HIGH]]
            tempfrejm = self.data.copy()
            badUnder = tempfrejm[tempfrejm[self.konfig.MIDLINE] < tempfrejm[self.konfig.WARNING_LOW]]
            badTocke = badUnder.append(badOver)
#            badTocke.sort()
#            badTocke.drop_duplicates(subset='vrijeme',
#                                     take_last=True,
#                                     inplace=True) # za svaki slucaj ako dodamo 2 ista indeksa
            badTocke.sort_index(inplace=True)
            badTocke.drop_duplicates(subset='vrijeme',
                                     keep='last',
                                     inplace=True) # za svaki slucaj ako dodamo 2 ista indeksa

            xbad = list(badTocke.index)
            ybad = list(badTocke[self.konfig.MIDLINE])
        out = {'x': x,
               'y': y,
               'warningUp': warningUp,
               'warningLow': warningLow,
               'xok': xok,
               'yok': yok,
               'xbad': xbad,
               'ybad': ybad}
        msg = 'izlazna mapa podataka za crtanje, data={0}'.format(str(out))
        logging.debug(msg)
        logging.debug('pripremi zero/span podatke za crtanje, kraj')
        return out

    def postavi_novi_zoom_level(self, x, y):
        """
        postavlja nove limite x i y osi.
        """
        msg = 'postavi_novi_zoom_level, x={0} , y={1}'.format(str(x), str(y))
        logging.debug(msg)
        if x != None and y != None:
            for ax in self.fig.axes:
                ax.set_xlim(x)
                ax.set_ylim(y)
        else:
            for ax in self.fig.axes:
                ax.set_xlim(self.xlim_original)
                ax.set_ylim(self.ylim_original)
        #redraw
        self.draw()

    def rect_zoom(self, eclick, erelease):
        """
        Callback funkcija za rectangle zoom canvasa. Funkcija lovi click i release
        evente (rubovi kvadrata) te povecava izabrani dio slike preko cijelog
        canvasa. overloaded za zero i span graf
        """
        msg = 'rect_zoom called. eclick={0} , erelease={1}'.format(str(eclick), str(erelease))
        logging.debug(msg)
        if eclick.xdata != erelease.xdata and eclick.ydata != erelease.ydata:
            x = sorted([eclick.xdata, erelease.xdata])
            y = sorted([eclick.ydata, erelease.ydata])
            paket = {'x':x,
                     'y':y,
                     'tip':self.konfig.TIP}
            msg = 'zoom value emit - data={0}'.format(str(paket))
            logging.debug(msg)
            self.emit(QtCore.SIGNAL('add_zoom_level(PyQt_PyObject)'), paket)
            #TODO! disable zoom
            self.zoomSelector.set_active(False)
            #enable spanSelector
            if self.spanSelector != None:
                self.spanSelector.visible = True


    def highlight_pick(self, tpl, size):
        """
        naredba za crtanje highlight tocke na grafu na koridinatama
        tpl = (x, y), velicine size.
        """
        msg = 'highlight_pick, tpl={0} , size={1}'.format(str(tpl), str(size))
        logging.debug(msg)
        x, y = tpl
        if self.statusHighlight:
            if tpl is not self.lastHighlight:
                self.axes.lines.remove(self.highlight[0])
                self.make_highlight(x, y, size)
        else:
            self.make_highlight(x, y, size)

        self.draw()

    def make_highlight(self, x, y, size):
        """
        Generiranje instance highlight tocke na kooridinati x, y za prikaz.
        Velicina markera je definirana sa ulaznim parametrom size.
        """
        msg = 'make_highlight, x={0}, y={1}, size={2}'.format(str(x), str(y), str(size))
        logging.debug(msg)
        self.highlight = self.axes.plot(x,
                                        y,
                                        marker='o',
                                        markersize=int(size),
                                        color='yellow',
                                        alpha=0.5,
                                        zorder=10)
        self.lastHighlight = (x, y)
        self.statusHighlight = True

    def on_pick(self, event):
        """
        Callback za pick na ZERO ili SPAN grafu.
        """
        msg = 'pick event = {0}'.format(str(event))
        logging.debug(msg)
        #definiraj x i y preko izabrane tocke
        x = self.data.index[event.ind[0]]
        y = self.data.loc[x, self.konfig.MIDLINE]
        minD = 'not defined'
        maxD = 'not defined'
        status = 'not defined'
        if self.konfig.WARNING_LOW in self.data.columns:
            minD = self.data.loc[x, self.konfig.WARNING_LOW]
            maxD = self.data.loc[x, self.konfig.WARNING_HIGH]
            # ako postoje vise istih indeksa, uzmi zadnji
            if type(y) is pd.core.series.Series:
                y = y[-1]
                minD = minD[-1]
                maxD = maxD[-1]
            if minD <= y <= maxD:
                status = 'Dobar'
            else:
                status = 'Ne valja'
        if event.mouseevent.button == 1:
            #zanemari pick opcije ako je aktivan zoom
            if not self.zoomSelector.get_active():
                #left click
                #update labels
                argList = {'xtocka': str(x),
                           'ytocka': str(y),
                           'minDozvoljenoOdstupanje': str(minD),
                           'maxDozvoljenoOdstupanje': str(maxD),
                           'status': str(status)}
                #highlight tocku
                self.highlight_pick((x, y), self.highlightSize)
                #emit update vrijednosti
                self.updateaj_labele_na_panelu('pick', argList)

    def setup_limits(self):
        """
        Prosirivanje granica grafa da ticke nisu na rubu.
        Konacne granice se spremaju u member xlim_original i ylim_original
        radi implementacije zoom out metode.
        """
        #dohvati trenutne granice x osi
        tmin, tmax = self.prosiri_granice_grafa(self.pocetnoVrijeme, self.zavrsnoVrijeme, 1440)
        #set granice za max zoom out
        self.xlim_original = (tmin, tmax)
        self.ylim_original = self.axes.get_ylim()
        #set granice grafa
        self.axes.set_xlim(self.xlim_original)
        self.axes.set_ylim(self.ylim_original)
        #set limite prilikom crtanja na zoom stack
        paket = {'x':self.xlim_original,
                 'y':self.ylim_original,
                 'tip':self.konfig.TIP}
        self.emit(QtCore.SIGNAL('report_original_size(PyQt_PyObject)'), paket)

    def crtaj_glavni_kanal(self):
        """
        metoda zaduzena za crtanje glavnog grafa zero (ili span) podataka
        """
        logging.debug('crtaj_glavni_kanal, start')
        #priprema podataka za crtanje
        tocke = self.pripremi_zero_span_podatke_za_crtanje()
        #prije crtanja provjeri da li postoje podaci ili je prazan frejm
        if len(tocke['x']):
            #midline (plot je drugacije definiran zbog pickera)
            logging.debug('crtaj glavni kanal --> midline')
            self.axes.plot(tocke['x'],
                           tocke['y'],
                           linestyle=self.konfig.Midline.lineStyle,
                           linewidth=self.konfig.Midline.lineWidth,
                           color=self.konfig.Midline.color,
                           markeredgecolor=self.konfig.Midline.color,
                           zorder=self.konfig.Midline.zorder,
                           label=self.konfig.Midline.label,
                           picker=5)
            #ok values
            if len(tocke['xok']) > 0:
                logging.debug('crtaj glavni kanal --> validan i ok')
                self.crtaj_scatter(tocke['xok'], tocke['yok'], self.konfig.VOK)
            #bad values
            if len(tocke['xbad']) > 0:
                logging.debug('crtaj glavni kanal --> validan i los')
                self.crtaj_scatter(tocke['xbad'], tocke['ybad'], self.konfig.VBAD)

            rightshift = int(1440*int(self.daycount)/5) #1/5 raspona u minutama
            rightX = tocke['x'][-1] + datetime.timedelta(minutes=rightshift)
            #TODO! update zavrsno vrijeme
            self.zavrsnoVrijeme = rightX
            extendedX = copy.deepcopy(tocke['x'])
            extendedX.append(rightX)
            extendedWarningUp = copy.deepcopy(tocke['warningUp'])
            extendedWarningUp.append(tocke['warningUp'][-1])
            extendedWarningLow = copy.deepcopy(tocke['warningLow'])
            extendedWarningLow.append(tocke['warningLow'][-1])

            if self.konfig.Warning1.crtaj and len(extendedWarningUp) > 0:
                logging.debug('crtaj glavni kanal --> gornji i donji warning line')
                self.crtaj_line(extendedX, extendedWarningUp, self.konfig.Warning1)
                self.crtaj_line(extendedX, extendedWarningLow, self.konfig.Warning2)
            #fill
            ledge, hedge = self.axes.get_ylim() #y granice canvasa za fill
            if self.konfig.Fill1.crtaj and len(extendedWarningUp) > 0:
                logging.debug('crtaj glavni kanal --> fill izmedju')
                self.crtaj_fill(extendedX,
                                extendedWarningLow,
                                extendedWarningUp,
                                self.konfig.Fill1)
                logging.debug('crtaj glavni kanal --> fill iznad')
                self.crtaj_fill(extendedX,
                                extendedWarningUp,
                                hedge,
                                self.konfig.Fill2)
                logging.debug('crtaj glavni kanal --> fill ispod')
                self.crtaj_fill(extendedX,
                                ledge,
                                extendedWarningLow,
                                self.konfig.Fill2)
            self.statusGlavniGraf = True
        else:
            self.clear_zero_span()
        logging.debug('crtaj_glavni_kanal, kraj')

    def crtaj(self, frejm, mapaParametara):
        """
        PROMJENA : direktno prosljedjivanje frejmova za crtanje...bez signala

        Glavna metoda za crtanje na canvas. Eksplicitne naredbe za crtanje.
        ulazni argumenti:
        frejm:
        -pandas dataframe zero ili span podataka.
        -Podaci za crtanje

        mapaParametara:
        -mapa sa potrebnim parametrima
        -mapaParametara['kanalId'] --> program mjerenja id glavnog kanala [int]
        -mapaParametara['pocetnoVrijeme'] --> pocetno vrijeme [pandas timestamp]
        -mapaParametara['zavrsnoVrijeme'] --> zavrsno vrijeme [pandas timestamp]
        -mapaParametara['ndana'] --> broj dana za prikaz [integer]
        """
        logging.debug('crtaj, start')
        self.clear_graf_sans_draw()
        self.emit(QtCore.SIGNAL('clear_zerospan_zoomstack'))
        self.statusHighlight = False
        self.lastHighlight = (None, None)
        argMap = {'xtocka':'',
                  'ytocka':'',
                  'minDozvoljenoOdstupanje':'',
                  'maxDozvoljenoOdstupanje':'',
                  'status':''}
        self.updateaj_labele_na_panelu('normal', argMap)
        self.data = frejm
        self.daycount = mapaParametara['ndana']
        self.pocetnoVrijeme = mapaParametara['pocetnoVrijeme']
        self.zavrsnoVrijeme = mapaParametara['zavrsnoVrijeme']
        self.gKanal = mapaParametara['kanalId']
        self.crtaj_glavni_kanal()
        self.setup_ticks()
        self.setup_limits()
        self.setup_legend()
        self.reinit_ticks_grid_legend()
        self.draw()
        logging.debug('crtaj, start')

    def clear_zero_span(self):
        """
        clear grafa i replace sa porukom da nema dostupnih podataka
        """
        self.clear_graf_sans_draw()
        self.emit(QtCore.SIGNAL('clear_zerospan_zoomstack'))
        self.statusHighlight = False
        self.lastHighlight = (None, None)
        argMap = {'xtocka':'',
                  'ytocka':'',
                  'minDozvoljenoOdstupanje':'',
                  'maxDozvoljenoOdstupanje':'',
                  'status':''}
        self.updateaj_labele_na_panelu('normal', argMap)
        #napisi da nema podataka
        self.axes.text(0.5,
                       0.5,
                       'Nije moguce pristupiti zero span podacima za trazeni kanal.',
                       horizontalalignment='center',
                       verticalalignment='center',
                       fontsize=8,
                       transform=self.axes.transAxes)
        self.draw()

    def zaokruzi_na_najblize_vrijeme(self, xpoint):
        """
        Metoda sluzi za zaokruzivanje vremena zadanog ulaznim parametrom xpoint na
        najblizu punu minutu.
        """
        return self.zaokruzi_vrijeme(xpoint, 60)

    def span_select(self, tmin, tmax):
        """
        Primjer callback metode za span selektor.
        t1 i t2 su timestampovi, ali ih treba adaptirati iz matplotlib vremena u
        "zaokruzene" pandas timestampove. (na minutnom grafu se zaokruzuje na najblizu
        minutu, dok na satnom na najblizi sat)
        """
        msg = 'span_select called. xmin={0} , xmax={1}'.format(str(tmin), str(tmax))
        logging.debug(msg)
        if self.statusGlavniGraf:
            t1 = matplotlib.dates.num2date(tmin)
            t2 = matplotlib.dates.num2date(tmax)
            t1 = datetime.datetime(t1.year, t1.month, t1.day, t1.hour, t1.minute, t1.second)
            t2 = datetime.datetime(t2.year, t2.month, t2.day, t2.hour, t2.minute, t2.second)
            t1 = self.zaokruzi_na_najblize_vrijeme(t1)
            t2 = self.zaokruzi_na_najblize_vrijeme(t2)
            t1 = pd.to_datetime(t1)
            t2 = pd.to_datetime(t2)
            #tocke ne smiju biti iste (izbjegavamo paljenje dijaloga na ljevi klik)
            if t1 != t2:
                #pronadji lokaciju kursora u Qt kooridinatama.
                loc = QtGui.QCursor.pos()
                self.show_context_menu(loc, t1, t2) #poziv kontekstnog menija

    def show_context_menu(self, pos, tmin, tmax):
        """
        Metoda iscrtava kontekstualni meni sa opcijom za plot grafa trenda (linearna
        regresija kroz selektirane tocke)
        """
        msg = 'show_context_menu called, pos={0} , tmin={1} , tmax={2}'.format(str(pos), str(tmin), str(tmax))
        logging.debug(msg)
        #zapamti rubna vremena intervala, trebati ce za druge metode
        self.__lastTimeMin = tmin
        self.__lastTimeMax = tmax
        #definiraj menu i postavi akcije u njega
        menu = QtGui.QMenu(self)
        menu.setTitle('Linearna projekcija izabranih vrijednosti (LSE)')
        action1 = QtGui.QAction("Nacrtaj pravac", menu)
        action2 = QtGui.QAction("Makni linear fit pravac", menu)
        menu.addAction(action1)
        menu.addAction(action2)
        #povezi akcije menua sa metodama
        action1.triggered.connect(self.order_plot_linear_fit_pravac)
        action2.triggered.connect(self.reset_graf)
        #prikazi menu na definiranoj tocki grafa
        menu.popup(pos)

    def order_plot_linear_fit_pravac(self):
        """
        plot linearnog fita iz selektiranih podataka...
        """
        #ako nisu zadane granice uzmi zadnje zadane iz kontekstnog menija
        args = {'tmin':self.__lastTimeMin,
                'tmax':self.__lastTimeMax}
        #clear and reset both graphs
        self.reset_graf()
        #plot self
        self.plot_linear_fit_pravac(args)
        #dispatch the order to calculate and plot
        self.emit(QtCore.SIGNAL('plot_linear_fit_line(PyQt_PyObject)'), args)

    def plot_linear_fit_pravac(self, mapa):
        """
        naredba za plot grafa..fit linearnog modela i crtanje...
        """
        #TODO!
        self.__lastTimeMin = mapa['tmin']
        self.__lastTimeMax = mapa['tmax']

        #get slice of data
        plotdata = self.data[self.data.index > self.__lastTimeMin]
        plotdata = plotdata[plotdata.index < self.__lastTimeMax]

        if len(plotdata) > 4:
            x = np.array([matplotlib.dates.date2num(i) for i in plotdata.vrijeme])
            y = np.array(plotdata.vrijednost)
            a, b = self.get_line_data(x, y)
            lx, hx = self.axes.get_xlim()
            raspon = np.linspace(lx, hx, num=200)
            self.axes.plot(raspon, a*raspon + b, 'b--')
            self.draw()
            t = self.vrati_ocekivano_vrijeme_odstupanja(a, b)
            #TODO! intercept update
            self.emit(QtCore.SIGNAL('update_ocekivani_fail(PyQt_PyObject)'), t)
        else:
            pass

    def vrati_ocekivano_vrijeme_odstupanja(self, a, b):
        """
        pronadji vrijeme odstupanja za podatke
        """
        upperlimit = self.data['maxDozvoljeno'][-1]
        lowerlimit = self.data['minDozvoljeno'][-1]
        if a > 0:
            t = (upperlimit - b) / a
        else:
            t = (lowerlimit - b) / a
        t = matplotlib.dates.num2date(t)
        t = pd.to_datetime(datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second))
        return t

    def get_line_data(self, x, y):
        """
        use numpy to calculate least squares linear regression coefficients
        """
        A = np.vstack([x, np.ones(len(x))]).T
        a, b = np.linalg.lstsq(A, y)[0]
        return a, b

    def reset_graf(self):
        """
        reset orignalnog grafa
        """
        self.emit(QtCore.SIGNAL('reset_zs_graf'))

    def setup_ticks(self):
        """
        automatsko postavljane tickova i labela
        """
        locator = AutoDateLocator(minticks=5, maxticks=24, interval_multiples=True)
        majorTickFormat = AutoDateFormatter(locator, defaultfmt='%Y-%m-%d')
        majorTickFormat.scaled[30.] = '%Y-%m-%d'
        majorTickFormat.scaled[1.0] = '%Y-%m-%d'
        majorTickFormat.scaled[1. / 24.] = '%H:%M:%S'
        majorTickFormat.scaled[1. / (24. * 60.)] = '%M:%S'
        self.axes.xaxis.set_major_locator(locator)
        self.axes.xaxis.set_major_formatter(majorTickFormat)
        self.fig.autofmt_xdate()
        allXLabels = self.axes.get_xticklabels(which='both') #dohvati sve labele
        for label in allXLabels:
            #label.set_rotation(30)
            label.set_fontsize(8)


class ZeroKanvas(ZeroSpanKanvas):
    """specificna implementacija Zero canvasa"""
    def __init__(self, konfig, parent=None, width=6, height=5, dpi=100):
        ZeroSpanKanvas.__init__(self, konfig)
        self.highlightSize = 1.5 * self.konfig.VOK.markerSize
        self.axes.xaxis.set_ticks_position('bottom')
        self.axes.figure.subplots_adjust(top=0.98)
        self.axes.figure.subplots_adjust(bottom=0.08)
        self.axes.figure.subplots_adjust(right=0.98)
        self.axes.set_ylabel(self.konfig.TIP)

    def updateaj_labele_na_panelu(self, tip, argMap):
        """
        update labela na zero span panelu (istovremeno i trigger za pick najblize
        tocke na drugom canvasu, npr. click na zero canvasu triggera span canvas...)
        """
        if tip == 'pick':
            self.emit(QtCore.SIGNAL('pick_nearest(PyQt_PyObject)'), argMap)
            self.emit(QtCore.SIGNAL('prikazi_info_zero(PyQt_PyObject)'), argMap)
        else:
            self.emit(QtCore.SIGNAL('prikazi_info_zero(PyQt_PyObject)'), argMap)


class SpanKanvas(ZeroSpanKanvas):
    """specificna implementacija span canvasa"""
    def __init__(self, konfig, parent=None, width=6, height=5, dpi=100):
        ZeroSpanKanvas.__init__(self, konfig)
        self.highlightSize = 1.5 * self.konfig.VOK.markerSize
        self.axes.xaxis.set_ticks_position('top')
        self.axes.figure.subplots_adjust(top=0.92)
        self.axes.figure.subplots_adjust(bottom=0.02)
        self.axes.figure.subplots_adjust(right=0.98)
        self.axes.set_ylabel(self.konfig.TIP)

    def updateaj_labele_na_panelu(self, tip, argMap):
        """
        update labela na zero span panelu (istovremeno i trigger za pick najblize
        tocke na drugom canvasu, npr. click na zero canvasu triggera span canvas...)
        """
        if tip == 'pick':
            self.emit(QtCore.SIGNAL('pick_nearest(PyQt_PyObject)'), argMap)
            self.emit(QtCore.SIGNAL('prikazi_info_span(PyQt_PyObject)'), argMap)
        else:
            self.emit(QtCore.SIGNAL('prikazi_info_span(PyQt_PyObject)'), argMap)
