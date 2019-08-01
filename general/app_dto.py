# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 14:42:54 2015

@author: User
"""
import logging
import random
import configparser
import app.general.pomocne_funkcije as pomocne_funkcije


class KonfigAplikacije():
    """
    Glavni konfiguracijski objekt aplikacije
    """
    def __init__(self, cfg):
        """
        Inicijalizacija sa cfg configparser objektom.

        Konfig sadrzava podatke za:
        -satni graf
        -minutni graf
        -zero graf
        -span graf
        -REST servis
        -opcenite postavke grafa
        """
        logging.debug('Inicijalizacija DTO za sve grafove, start')
        self.conf = cfg
        # mapa dto objekata pomocnih grafova - spremljnih pod kljucem programMjerenjaId
        self.dictPomocnih = {}
        # mapa dto objekata povezanih grafova - spremljenih pod kljucem programMjerenjaId
        self.dictPovezanih = {}

        # blacklista kanala za ignoriranje warninga okolisnih uvijeta
        meh = pomocne_funkcije.load_config_item(cfg, 'MAIN_WINDOW', 'WARNING_BLACKLIST', "", str)
        self.warningBlackList = [int(i) for i in meh.split(sep=',')]

        self.satni = SatniGrafKonfig(cfg)
        self.minutni = MinutniGrafKonfig(cfg)
        self.zero = ZeroGrafKonfig(cfg)
        self.span = SpanGrafKonfig(cfg)
        self.REST = RESTKonfig(cfg)
        self.satniRest = SatniRestGrafKonfig(cfg)
        logging.debug('Inicijalizacija DTO za sve grafove, end')

    def overwrite_konfig_file(self):
        """
        Metoda prepisuje svojstva objekta u konfig file.
        """
        logging.debug('pocetak spremanja novih podataka u konfig file')
        sectioni = ['LOG_SETUP', 'REST_INFO', 'MAIN_WINDOW', 'SATNI_REST',
                    'SATNI', 'MINUTNI', 'ZERO', 'SPAN']
        new_config = configparser.ConfigParser()
        for section in sectioni:
            new_config.add_section(section)

        #log_setup
        new_config.set('LOG_SETUP', 'file', 'applog.log')
        new_config.set('LOG_SETUP', 'mode', 'w')
        new_config.set('LOG_SETUP', 'lvl', 'INFO')
        #REST_INFO
        new_config.set('REST_INFO', 'base_url', str(self.REST.RESTBaseUrl))
        new_config.set('REST_INFO', 'program_mjerenja', str(self.REST.RESTProgramMjerenja))
        new_config.set('REST_INFO', 'sirovi_podaci', str(self.REST.RESTSiroviPodaci))
        new_config.set('REST_INFO', 'satni_podaci', str(self.REST.RESTSatniPodaci))
        new_config.set('REST_INFO', 'zero_span', str(self.REST.RESTZeroSpan))
        new_config.set('REST_INFO', 'status_map', str(self.REST.RESTStatusMap))
        new_config.set('REST_INFO', 'komentari', str(self.REST.RESTkomentari))
        #MAIN WINDOW
        new_config.set('MAIN_WINDOW', 'WARNING_BLACKLIST', str(self.warningBlackList)[1:-1]) #bez zagrada
        new_config.set('MAIN_WINDOW', 'action_satni_grid', str(self.satni.Grid))
        new_config.set('MAIN_WINDOW', 'action_satni_legend', str(self.satni.Legend))
        new_config.set('MAIN_WINDOW', 'action_minutni_grid', str(self.minutni.Grid))
        new_config.set('MAIN_WINDOW', 'action_minutni_legend', str(self.minutni.Legend))
        new_config.set('MAIN_WINDOW', 'action_ZERO_grid', str(self.zero.Grid))
        new_config.set('MAIN_WINDOW', 'action_ZERO_legend', str(self.zero.Legend))
        new_config.set('MAIN_WINDOW', 'action_SPAN_grid', str(self.span.Grid))
        new_config.set('MAIN_WINDOW', 'action_SPAN_legend', str(self.span.Legend))
        new_config.set('MAIN_WINDOW', 'action_satni_rest_grid', str(self.satniRest.Grid))
        new_config.set('MAIN_WINDOW', 'action_satni_rest_legend', str(self.satniRest.Legend))
        new_config.set('MAIN_WINDOW', 'status_warning_crtaj_', str(self.satni.statusWarning.crtaj))
        new_config.set('MAIN_WINDOW', 'status_warning_markerStyle_', str(self.satni.statusWarning.markerStyle))
        new_config.set('MAIN_WINDOW', 'status_warning_markerSize_', str(self.satni.statusWarning.markerSize))
        new_config.set('MAIN_WINDOW', 'status_warning_rgb_', str(self.satni.statusWarning.rgb)[1:-1]) #bez zagrada
        new_config.set('MAIN_WINDOW', 'status_warning_alpha_', str(self.satni.statusWarning.alpha))
        new_config.set('MAIN_WINDOW', 'status_warning_zorder_', str(self.satni.statusWarning.zorder))
        new_config.set('MAIN_WINDOW', 'status_warning_label_', str(self.satni.statusWarning.label))
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_crtaj_', str(self.satni.statusWarningOkolis.crtaj))
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_markerStyle_', str(self.satni.statusWarningOkolis.markerStyle))
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_markerSize_', str(self.satni.statusWarningOkolis.markerSize))
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_rgb_', str(self.satni.statusWarningOkolis.rgb)[1:-1])
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_alpha_', str(self.satni.statusWarningOkolis.alpha))
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_zorder_', str(self.satni.statusWarningOkolis.zorder))
        new_config.set('MAIN_WINDOW', 'status_warning_okolis_label_', str(self.satni.statusWarningOkolis.label))
        #SATNI_REST
        new_config.set('SATNI_REST', 'midline_crtaj_', str(self.satniRest.Midline.crtaj))
        new_config.set('SATNI_REST', 'midline_rgb_', str(self.satniRest.Midline.rgb)[1:-1])
        new_config.set('SATNI_REST', 'midline_alpha_', str(self.satniRest.Midline.alpha))
        new_config.set('SATNI_REST', 'midline_lineStyle_', str(self.satniRest.Midline.lineStyle))
        new_config.set('SATNI_REST', 'midline_lineWidth_', str(self.satniRest.Midline.lineWidth))
        new_config.set('SATNI_REST', 'midline_zorder_', str(self.satniRest.Midline.zorder))
        new_config.set('SATNI_REST', 'midline_label_', str(self.satniRest.Midline.label))
        #SATNI
        new_config.set('SATNI', 'midline_crtaj_', str(self.satni.Midline.crtaj))
        new_config.set('SATNI', 'midline_rgb_', str(self.satni.Midline.rgb)[1:-1])
        new_config.set('SATNI', 'midline_alpha_', str(self.satni.Midline.alpha))
        new_config.set('SATNI', 'midline_lineStyle_', str(self.satni.Midline.lineStyle))
        new_config.set('SATNI', 'midline_lineWidth_', str(self.satni.Midline.lineWidth))
        new_config.set('SATNI', 'midline_zorder_', str(self.satni.Midline.zorder))
        new_config.set('SATNI', 'midline_label_', str(self.satni.Midline.label))
        new_config.set('SATNI', 'ekstrem_crtaj_', str(self.satni.EksMax.crtaj))
        new_config.set('SATNI', 'ekstrem_rgb_', str(self.satni.EksMax.rgb)[1:-1])
        new_config.set('SATNI', 'ekstrem_alpha_', str(self.satni.EksMax.alpha))
        new_config.set('SATNI', 'ekstrem_markerStyle_', str(self.satni.EksMax.markerStyle))
        new_config.set('SATNI', 'ekstrem_markerSize_', str(self.satni.EksMax.markerSize))
        new_config.set('SATNI', 'ekstrem_zorder_', str(self.satni.EksMax.zorder))
        new_config.set('SATNI', 'ekstrem_label_', str(self.satni.EksMax.label))
        new_config.set('SATNI', 'VOK_crtaj_', str(self.satni.VOK.crtaj))
        new_config.set('SATNI', 'VOK_rgb_', str(self.satni.VOK.rgb)[1:-1])
        new_config.set('SATNI', 'VOK_alpha_', str(self.satni.VOK.alpha))
        new_config.set('SATNI', 'VOK_markerStyle_', str(self.satni.VOK.markerStyle))
        new_config.set('SATNI', 'VOK_markerSize_', str(self.satni.VOK.markerSize))
        new_config.set('SATNI', 'VOK_zorder_', str(self.satni.VOK.zorder))
        new_config.set('SATNI', 'VOK_label_', str(self.satni.VOK.label))
        new_config.set('SATNI', 'VBAD_crtaj_', str(self.satni.VBAD.crtaj))
        new_config.set('SATNI', 'VBAD_rgb_', str(self.satni.VBAD.rgb)[1:-1])
        new_config.set('SATNI', 'VBAD_alpha_', str(self.satni.VBAD.alpha))
        new_config.set('SATNI', 'VBAD_markerStyle_', str(self.satni.VBAD.markerStyle))
        new_config.set('SATNI', 'VBAD_markerSize_', str(self.satni.VBAD.markerSize))
        new_config.set('SATNI', 'VBAD_zorder_', str(self.satni.VBAD.zorder))
        new_config.set('SATNI', 'VBAD_label_', str(self.satni.VBAD.label))
        new_config.set('SATNI', 'NVOK_crtaj_', str(self.satni.NVOK.crtaj))
        new_config.set('SATNI', 'NVOK_rgb_', str(self.satni.NVOK.rgb)[1:-1])
        new_config.set('SATNI', 'NVOK_alpha_', str(self.satni.NVOK.alpha))
        new_config.set('SATNI', 'NVOK_markerStyle_', str(self.satni.NVOK.markerStyle))
        new_config.set('SATNI', 'NVOK_markerSize_', str(self.satni.NVOK.markerSize))
        new_config.set('SATNI', 'NVOK_zorder_', str(self.satni.NVOK.zorder))
        new_config.set('SATNI', 'NVOK_label_', str(self.satni.NVOK.label))
        new_config.set('SATNI', 'NVBAD_crtaj_', str(self.satni.NVBAD.crtaj))
        new_config.set('SATNI', 'NVBAD_rgb_', str(self.satni.NVBAD.rgb)[1:-1])
        new_config.set('SATNI', 'NVBAD_alpha_', str(self.satni.NVBAD.alpha))
        new_config.set('SATNI', 'NVBAD_markerStyle_', str(self.satni.NVBAD.markerStyle))
        new_config.set('SATNI', 'NVBAD_markerSize_', str(self.satni.NVBAD.markerSize))
        new_config.set('SATNI', 'NVBAD_zorder_', str(self.satni.NVBAD.zorder))
        new_config.set('SATNI', 'NVBAD_label_', str(self.satni.NVBAD.label))
        new_config.set('SATNI', 'fill1_crtaj_', str(self.satni.Fill.crtaj))
        new_config.set('SATNI', 'fill1_rgb_', str(self.satni.Fill.rgb)[1:-1])
        new_config.set('SATNI', 'fill1_alpha_', str(self.satni.Fill.alpha))
        new_config.set('SATNI', 'fill1_komponenta1_', str(self.satni.Fill.komponenta1))
        new_config.set('SATNI', 'fill1_komponenta2_', str(self.satni.Fill.komponenta2))
        new_config.set('SATNI', 'fill1_zorder_', str(self.satni.Fill.zorder))
        #MINUTNI
        new_config.set('MINUTNI', 'midline_crtaj_', str(self.minutni.Midline.crtaj))
        new_config.set('MINUTNI', 'midline_rgb_', str(self.minutni.Midline.rgb)[1:-1])
        new_config.set('MINUTNI', 'midline_alpha_', str(self.minutni.Midline.alpha))
        new_config.set('MINUTNI', 'midline_lineStyle_', str(self.minutni.Midline.lineStyle))
        new_config.set('MINUTNI', 'midline_lineWidth_', str(self.minutni.Midline.lineWidth))
        new_config.set('MINUTNI', 'midline_zorder_', str(self.minutni.Midline.zorder))
        new_config.set('MINUTNI', 'midline_label_', str(self.minutni.Midline.label))
        new_config.set('MINUTNI', 'VOK_crtaj_', str(self.minutni.VOK.crtaj))
        new_config.set('MINUTNI', 'VOK_rgb_', str(self.minutni.VOK.rgb)[1:-1])
        new_config.set('MINUTNI', 'VOK_alpha_', str(self.minutni.VOK.alpha))
        new_config.set('MINUTNI', 'VOK_markerStyle_', str(self.minutni.VOK.markerStyle))
        new_config.set('MINUTNI', 'VOK_markerSize_', str(self.minutni.VOK.markerSize))
        new_config.set('MINUTNI', 'VOK_zorder_', str(self.minutni.VOK.zorder))
        new_config.set('MINUTNI', 'VOK_label_', str(self.minutni.VOK.label))
        new_config.set('MINUTNI', 'VBAD_crtaj_', str(self.minutni.VBAD.crtaj))
        new_config.set('MINUTNI', 'VBAD_rgb_', str(self.minutni.VBAD.rgb)[1:-1])
        new_config.set('MINUTNI', 'VBAD_alpha_', str(self.minutni.VBAD.alpha))
        new_config.set('MINUTNI', 'VBAD_markerStyle_', str(self.minutni.VBAD.markerStyle))
        new_config.set('MINUTNI', 'VBAD_markerSize_', str(self.minutni.VBAD.markerSize))
        new_config.set('MINUTNI', 'VBAD_zorder_', str(self.minutni.VBAD.zorder))
        new_config.set('MINUTNI', 'VBAD_label_', str(self.minutni.VBAD.label))
        new_config.set('MINUTNI', 'NVOK_crtaj_', str(self.minutni.NVOK.crtaj))
        new_config.set('MINUTNI', 'NVOK_rgb_', str(self.minutni.NVOK.rgb)[1:-1])
        new_config.set('MINUTNI', 'NVOK_alpha_', str(self.minutni.NVOK.alpha))
        new_config.set('MINUTNI', 'NVOK_markerStyle_', str(self.minutni.NVOK.markerStyle))
        new_config.set('MINUTNI', 'NVOK_markerSize_', str(self.minutni.NVOK.markerSize))
        new_config.set('MINUTNI', 'NVOK_zorder_', str(self.minutni.NVOK.zorder))
        new_config.set('MINUTNI', 'NVOK_label_', str(self.minutni.NVOK.label))
        new_config.set('MINUTNI', 'NVBAD_crtaj_', str(self.minutni.NVBAD.crtaj))
        new_config.set('MINUTNI', 'NVBAD_rgb_', str(self.minutni.NVBAD.rgb)[1:-1])
        new_config.set('MINUTNI', 'NVBAD_alpha_', str(self.minutni.NVBAD.alpha))
        new_config.set('MINUTNI', 'NVBAD_markerStyle_', str(self.minutni.NVBAD.markerStyle))
        new_config.set('MINUTNI', 'NVBAD_markerSize_', str(self.minutni.NVBAD.markerSize))
        new_config.set('MINUTNI', 'NVBAD_zorder_', str(self.minutni.NVBAD.zorder))
        new_config.set('MINUTNI', 'NVBAD_label_', str(self.minutni.NVBAD.label))
        #ZERO
        new_config.set('ZERO', 'midline_crtaj_', str(self.zero.Midline.crtaj))
        new_config.set('ZERO', 'midline_rgb_', str(self.zero.Midline.rgb)[1:-1])
        new_config.set('ZERO', 'midline_alpha_', str(self.zero.Midline.alpha))
        new_config.set('ZERO', 'midline_lineStyle_', str(self.zero.Midline.lineStyle))
        new_config.set('ZERO', 'midline_lineWidth_', str(self.zero.Midline.lineWidth))
        new_config.set('ZERO', 'midline_zorder_', str(self.zero.Midline.zorder))
        new_config.set('ZERO', 'midline_label_', str(self.zero.Midline.label))
        new_config.set('ZERO', 'VOK_crtaj_', str(self.zero.VOK.crtaj))
        new_config.set('ZERO', 'VOK_rgb_', str(self.zero.VOK.rgb)[1:-1])
        new_config.set('ZERO', 'VOK_alpha_', str(self.zero.VOK.alpha))
        new_config.set('ZERO', 'VOK_markerStyle_', str(self.zero.VOK.markerStyle))
        new_config.set('ZERO', 'VOK_markerSize_', str(self.zero.VOK.markerSize))
        new_config.set('ZERO', 'VOK_zorder_', str(self.zero.VOK.zorder))
        new_config.set('ZERO', 'VOK_label_', str(self.zero.VOK.label))
        new_config.set('ZERO', 'VBAD_crtaj_', str(self.zero.VBAD.crtaj))
        new_config.set('ZERO', 'VBAD_rgb_', str(self.zero.VBAD.rgb)[1:-1])
        new_config.set('ZERO', 'VBAD_alpha_', str(self.zero.VBAD.alpha))
        new_config.set('ZERO', 'VBAD_markerStyle_', str(self.zero.VBAD.markerStyle))
        new_config.set('ZERO', 'VBAD_markerSize_', str(self.zero.VBAD.markerSize))
        new_config.set('ZERO', 'VBAD_zorder_', str(self.zero.VBAD.zorder))
        new_config.set('ZERO', 'VBAD_label_', str(self.zero.VBAD.label))
        new_config.set('ZERO', 'fill1_crtaj_', str(self.zero.Fill1.crtaj))
        new_config.set('ZERO', 'fill1_rgb_', str(self.zero.Fill1.rgb)[1:-1])
        new_config.set('ZERO', 'fill1_alpha_', str(self.zero.Fill1.alpha))
        new_config.set('ZERO', 'fill1_zorder_', str(self.zero.Fill1.zorder))
        new_config.set('ZERO', 'fill1_label_', str(self.zero.Fill1.label))
        new_config.set('ZERO', 'fill2_crtaj_', str(self.zero.Fill2.crtaj))
        new_config.set('ZERO', 'fill2_rgb_', str(self.zero.Fill2.rgb)[1:-1])
        new_config.set('ZERO', 'fill2_alpha_', str(self.zero.Fill2.alpha))
        new_config.set('ZERO', 'fill2_zorder_', str(self.zero.Fill2.zorder))
        new_config.set('ZERO', 'fill2_label_', str(self.zero.Fill2.label))
        new_config.set('ZERO', 'warning_crtaj_', str(self.zero.Warning1.crtaj))
        new_config.set('ZERO', 'warning_rgb_', str(self.zero.Warning1.rgb)[1:-1])
        new_config.set('ZERO', 'warning_alpha_', str(self.zero.Warning1.alpha))
        new_config.set('ZERO', 'warning_lineStyle_', str(self.zero.Warning1.lineStyle))
        new_config.set('ZERO', 'warning_lineWidth_', str(self.zero.Warning1.lineWidth))
        new_config.set('ZERO', 'warning_zorder_', str(self.zero.Warning1.zorder))
        new_config.set('ZERO', 'warning_label_', str(self.zero.Warning1.label))
        #SPAN
        new_config.set('SPAN', 'midline_crtaj_', str(self.span.Midline.crtaj))
        new_config.set('SPAN', 'midline_rgb_', str(self.span.Midline.rgb)[1:-1])
        new_config.set('SPAN', 'midline_alpha_', str(self.span.Midline.alpha))
        new_config.set('SPAN', 'midline_lineStyle_', str(self.span.Midline.lineStyle))
        new_config.set('SPAN', 'midline_lineWidth_', str(self.span.Midline.lineWidth))
        new_config.set('SPAN', 'midline_zorder_', str(self.span.Midline.zorder))
        new_config.set('SPAN', 'midline_label_', str(self.span.Midline.label))
        new_config.set('SPAN', 'VOK_crtaj_', str(self.span.VOK.crtaj))
        new_config.set('SPAN', 'VOK_rgb_', str(self.span.VOK.rgb)[1:-1])
        new_config.set('SPAN', 'VOK_alpha_', str(self.span.VOK.alpha))
        new_config.set('SPAN', 'VOK_markerStyle_', str(self.span.VOK.markerStyle))
        new_config.set('SPAN', 'VOK_markerSize_', str(self.span.VOK.markerSize))
        new_config.set('SPAN', 'VOK_zorder_', str(self.span.VOK.zorder))
        new_config.set('SPAN', 'VOK_label_', str(self.span.VOK.label))
        new_config.set('SPAN', 'VBAD_crtaj_', str(self.span.VBAD.crtaj))
        new_config.set('SPAN', 'VBAD_rgb_', str(self.span.VBAD.rgb)[1:-1])
        new_config.set('SPAN', 'VBAD_alpha_', str(self.span.VBAD.alpha))
        new_config.set('SPAN', 'VBAD_markerStyle_', str(self.span.VBAD.markerStyle))
        new_config.set('SPAN', 'VBAD_markerSize_', str(self.span.VBAD.markerSize))
        new_config.set('SPAN', 'VBAD_zorder_', str(self.span.VBAD.zorder))
        new_config.set('SPAN', 'VBAD_label_', str(self.span.VBAD.label))
        new_config.set('SPAN', 'fill1_crtaj_', str(self.span.Fill1.crtaj))
        new_config.set('SPAN', 'fill1_rgb_', str(self.span.Fill1.rgb)[1:-1])
        new_config.set('SPAN', 'fill1_alpha_', str(self.span.Fill1.alpha))
        new_config.set('SPAN', 'fill1_zorder_', str(self.span.Fill1.zorder))
        new_config.set('SPAN', 'fill1_label_', str(self.span.Fill1.label))
        new_config.set('SPAN', 'fill2_crtaj_', str(self.span.Fill2.crtaj))
        new_config.set('SPAN', 'fill2_rgb_', str(self.span.Fill2.rgb)[1:-1])
        new_config.set('SPAN', 'fill2_alpha_', str(self.span.Fill2.alpha))
        new_config.set('SPAN', 'fill2_zorder_', str(self.span.Fill2.zorder))
        new_config.set('SPAN', 'fill2_label_', str(self.span.Fill2.label))
        new_config.set('SPAN', 'warning_crtaj_', str(self.span.Warning1.crtaj))
        new_config.set('SPAN', 'warning_rgb_', str(self.span.Warning1.rgb)[1:-1])
        new_config.set('SPAN', 'warning_alpha_', str(self.span.Warning1.alpha))
        new_config.set('SPAN', 'warning_lineStyle_', str(self.span.Warning1.lineStyle))
        new_config.set('SPAN', 'warning_lineWidth_', str(self.span.Warning1.lineWidth))
        new_config.set('SPAN', 'warning_zorder_', str(self.span.Warning1.zorder))
        new_config.set('SPAN', 'warning_label_', str(self.span.Warning1.label))
        #Pregazi stari config.ini sa novim podacima iz objekta new_config
        with open('./config.ini', mode='w') as fajl:
            new_config.write(fajl)
        logging.debug('Kraj spremanja podataka u konfig file "config.ini"')

    def reset_pomocne(self, mapa):
        """
        Reset nested dicta pomocnih kanala na nulu
        - mapa je opisna mapa svih kanala (kljuc je programMjerenjaId sto je bitno)
        """
        self.dictPomocnih = {}
        for masterkey in mapa:
            self.dictPomocnih[masterkey] = {}
        logging.debug('Reset mape pomocnih kanala gotov. Svi pomocni grafovi su izbrisani.')

    def reset_povezane(self, mapa):
        """
        Reset nested dicta povezanih kanala na nulu
        - ulaz (mapa) je dict svih programa mjerenja...
        """
        self.dictPovezanih = {}
        for masterkey in mapa:
            self.dictPovezanih[masterkey] = {}
        logging.debug('Reset mape povezanih kanala je gotov. Svi povezani kanali su izbrisiani.')

    def dodaj_pomocni(self, masterkey, key):
        """
        --> key : programMjerenjaId grafa koji se dodaje
        --> masterkey : programMjerenjaId "glavnog grafa"
        Metoda dodaje  id grafa u mapu pomocnih grafova pod kljucem masterkey.
        """
        name = 'plot' + str(key)
        if masterkey in self.dictPomocnih:
            self.dictPomocnih[masterkey][key] = GrafDTO(self.conf, tip='POMOCNI', podtip=name, oblik='plot')
        else:
            self.dictPomocnih[masterkey] = {key:GrafDTO(self.conf, tip='POMOCNI', podtip=name, oblik='plot')}
        msg = 'Pomocni graf id={0} dodan za glavni graf programMjerenjaId={1}'.format(key, masterkey)
        logging.debug(msg)

    def dodaj_povezani(self, masterkey, key):
        """
        --> key : programMjerenjaId grafa koji se dodaje
        --> masterkey : programMjerenjaId "glavnog grafa"
        Metoda dodaje  id grafa u mapu pomocnih grafova pod kljucem masterkey.
        """
        name = 'plot' + str(key)
        if masterkey in self.dictPovezanih:
            self.dictPovezanih[masterkey][key] = GrafDTO(self.conf, tip='POMOCNI', podtip=name, oblik='plot')
        else:
            self.dictPovezanih[masterkey] = {key:GrafDTO(self.conf, tip='POMOCNI', podtip=name, oblik='plot')}
        msg = 'Pvezani graf id={0} dodan za glavni graf programMjerenjaId={1}'.format(key, masterkey)
        logging.debug(msg)

    def makni_pomocni(self, masterkey, key):
        """
        Metoda brise pomocni graf (key je id programa mjerenja) sa popisa pomocnih
        grafova za graf masterkey (id programa mjerenja 'glavnog kanala').
        """
        self.dictPomocnih[masterkey].pop(key)
        msg = 'Graf id={0} maknut sa popisa pomocnih za programMjerenjaId={1}'.format(key, masterkey)
        logging.debug(msg)

    def dodaj_random_pomocni(self, masterkey, key, naziv):
        """
        dodavanje pomocnog grafa ali sa random postavkama... samo za inicijalizaciju
        """
        name = 'plot'+str(key)
        graf = GrafDTO(self.conf, tip='POMOCNI', podtip=name, oblik='line')
        rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        graf.set_rgb(rgb)
        graf.set_label('pomocni graf -- {0}'.format(naziv))
        if masterkey in self.dictPomocnih:
            self.dictPomocnih[masterkey][key] = graf
        else:
            self.dictPomocnih[masterkey] = {key:graf}
        msg = 'Pomocni graf id={0} dodan za glavni graf programMjerenjaId={1}'.format(key, masterkey)
        logging.debug(msg)

    def dodaj_random_povezani(self, masterkey, key, naziv):
        """
        dodavanje povezanog grafa ali sa random postavkama... samo za inicijalizaciju
        """
        name = 'plot'+str(key)
        graf = GrafDTO(self.conf, tip='POMOCNI', podtip=name, oblik='line')
        rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        graf.set_rgb(rgb)
        graf.set_label('povezani graf -- {0}'.format(naziv))
        if masterkey in self.dictPovezanih:
            self.dictPovezanih[masterkey][key] = graf
        else:
            self.dictPovezanih[masterkey] = {key:graf}
        msg = 'Povezani graf id={0} dodan za glavni graf programMjerenjaId={1}'.format(key, masterkey)
        logging.debug(msg)


class MetaConfig():
    """
    Zajednicke postavke za grafove.
    """
    def __init__(self):
        """
        Definira zajednicke metoda za konfig graf klase.
        """
        self.Midline = None
        self.VOK = None
        self.VBAD = None
        self.NVOK = None
        self.NVBAD = None
        self.EksMin = None
        self.EksMax = None
        self.Fill = None
        self.Grid = False
        self.Legend = False
        self.Selector = False
        self.Fill1 = None
        self.Fill2 = None
        self.Warning1 = None
        self.Warning2 = None

    def set_grid(self, x):
        """boolean setter za prikaz cursora"""
        self.Grid = x
        msg = 'Grid status promjenjen, value={0}'.format(x)
        logging.debug(msg)

    def set_legend(self, x):
        """boolean setter za prikaz legende"""
        self.Legend = x
        msg = 'Legend status promjenjen, value={0}'.format(x)
        logging.debug(msg)


class SatniRestGrafKonfig(MetaConfig):
    """
    Konfiguracija grafa satno agregiranih podataka preuzetih sa REST servisa.
    Sluzi za visednevni prikaz.
    """
    def __init__(self, cfg):
        logging.debug('Pocetak inicijalizacije postavki grafa sa visednevnim prikazom satnih podataka')
        super(SatniRestGrafKonfig, self).__init__()
        self.TIP = 'SATNO AGREGIRANI, REST'
        self.MIDLINE = 'avg'
        self.STATUS = 'status'
        self.COUNT = 'obuhvat'
        #podaci o grafovima
        self.Midline = GrafDTO(cfg, tip='SATNI_REST', podtip='midline', oblik='line')
        self.VOK = GrafDTO(cfg, tip='SATNI', podtip='VOK', oblik='scatter') #potreban za highlight
        #interakcija sa grafom
        self.Grid = pomocne_funkcije.load_config_item(cfg,
                                                      'MAIN_WINDOW',
                                                      'action_satni_rest_grid',
                                                      False,
                                                      bool)
        self.Legend = pomocne_funkcije.load_config_item(cfg,
                                                        'MAIN_WINDOW',
                                                        'action_satni_rest_legend',
                                                        False,
                                                        bool)
        logging.debug('Kraj inicijalizacije postavki grafa sa visednevnim prikazom satnih podataka')


class SatniGrafKonfig(MetaConfig):
    """
    Konfiguracija grafa satno agregiranih podataka.
    """
    def __init__(self, cfg):
        logging.debug('Pocetak inicijalizacije postavki grafa sa satno agregiranim podacima')
        super(SatniGrafKonfig, self).__init__()
        self.TIP = 'SATNI'
        self.MIDLINE = 'avg'
        self.MINIMUM = 'min'
        self.MAKSIMUM = 'max'
        self.STATUS = 'status'
        self.COUNT = 'count'
        self.FLAG = 'flag'
        #podaci o grafovima
        self.Midline = GrafDTO(cfg, tip='SATNI', podtip='midline', oblik='line')
        self.VOK = GrafDTO(cfg, tip='SATNI', podtip='VOK', oblik='scatter')
        self.VBAD = GrafDTO(cfg, tip='SATNI', podtip='VBAD', oblik='scatter')
        self.NVOK = GrafDTO(cfg, tip='SATNI', podtip='NVOK', oblik='scatter')
        self.NVBAD = GrafDTO(cfg, tip='SATNI', podtip='NVBAD', oblik='scatter')
        self.EksMin = GrafDTO(cfg, tip='SATNI', podtip='ekstrem', oblik='scatter')
        self.EksMax = GrafDTO(cfg, tip='SATNI', podtip='ekstrem', oblik='scatter')
        self.Fill = GrafDTO(cfg, tip='SATNI', podtip='fill1', oblik='fill')
        #interakcija sa grafom
        self.Grid = pomocne_funkcije.load_config_item(cfg,
                                                      'MAIN_WINDOW',
                                                      'action_satni_grid',
                                                      False,
                                                      bool)
        self.Legend = pomocne_funkcije.load_config_item(cfg,
                                                        'MAIN_WINDOW',
                                                        'action_satni_legend',
                                                        False,
                                                        bool)
        self.statusWarning = GrafDTO(cfg,
                                     tip='MAIN_WINDOW',
                                     podtip='status_warning',
                                     oblik='scatter')
        self.statusWarningOkolis = GrafDTO(cfg,
                                           tip='MAIN_WINDOW',
                                           podtip='status_warning_okolis',
                                           oblik='scatter')
        logging.debug('Kraj inicijalizacije postavki grafa sa satno agregiranim podacima')


class MinutniGrafKonfig(MetaConfig):
    """
    Konfiguracija grafa minutnih podataka.
    """
    def __init__(self, cfg):
        logging.debug('Pocetak inicijalizacije postavki grafa sa minutnim podacima')
        super(MinutniGrafKonfig, self).__init__()
        self.TIP = 'MINUTNI'
        self.MIDLINE = 'koncentracija'
        self.STATUS = 'status'
        self.FLAG = 'flag'
        #podaci o grafovima
        self.Midline = GrafDTO(cfg, tip='MINUTNI', podtip='midline', oblik='line')
        self.VOK = GrafDTO(cfg, tip='MINUTNI', podtip='VOK', oblik='scatter')
        self.VBAD = GrafDTO(cfg, tip='MINUTNI', podtip='VBAD', oblik='scatter')
        self.NVOK = GrafDTO(cfg, tip='MINUTNI', podtip='NVOK', oblik='scatter')
        self.NVBAD = GrafDTO(cfg, tip='MINUTNI', podtip='NVBAD', oblik='scatter')
        #interakcija sa grafom
        self.Grid = pomocne_funkcije.load_config_item(cfg,
                                                      'MAIN_WINDOW',
                                                      'action_minutni_grid',
                                                      False,
                                                      bool)
        self.Legend = pomocne_funkcije.load_config_item(cfg,
                                                        'MAIN_WINDOW',
                                                        'action_minutni_legend',
                                                        False,
                                                        bool)
        self.statusWarning = GrafDTO(cfg,
                                     tip='MAIN_WINDOW',
                                     podtip='status_warning',
                                     oblik='scatter')
        self.statusWarningOkolis = GrafDTO(cfg,
                                           tip='MAIN_WINDOW',
                                           podtip='status_warning_okolis',
                                           oblik='scatter')
        logging.debug('Kraj inicijalizacije postavki grafa sa minutnim podacima')


class ZeroGrafKonfig(MetaConfig):
    """
    Konfiguracija grafa ZERO podataka.
    """
    def __init__(self, cfg):
        logging.debug('Pocetak inicijalizacije postavki grafa sa ZERO podacima')
        super(ZeroGrafKonfig, self).__init__()
        self.TIP = 'ZERO'
        self.MIDLINE = 'vrijednost'
        self.WARNING_LOW = 'minDozvoljeno'
        self.WARNING_HIGH = 'maxDozvoljeno'
        #podaci o grafovima
        self.Midline = GrafDTO(cfg, tip='ZERO', podtip='midline', oblik='line')
        self.VOK = GrafDTO(cfg, tip='ZERO', podtip='VOK', oblik='scatter')
        self.VBAD = GrafDTO(cfg, tip='ZERO', podtip='VBAD', oblik='scatter')
        self.Fill1 = GrafDTO(cfg, tip='ZERO', podtip='fill1', oblik='fill')
        self.Fill2 = GrafDTO(cfg, tip='ZERO', podtip='fill2', oblik='fill')
        self.Warning1 = GrafDTO(cfg, tip='ZERO', podtip='warning', oblik='line')
        self.Warning2 = GrafDTO(cfg, tip='ZERO', podtip='warning', oblik='line')
        #interakcija sa grafom
        self.Grid = pomocne_funkcije.load_config_item(cfg,
                                                      'MAIN_WINDOW',
                                                      'action_ZERO_grid',
                                                      False,
                                                      bool)
        self.Legend = pomocne_funkcije.load_config_item(cfg,
                                                        'MAIN_WINDOW',
                                                        'action_ZERO_legend',
                                                        False,
                                                        bool)
        logging.debug('Kraj inicijalizacije postavki grafa sa ZERO podacima')


class SpanGrafKonfig(MetaConfig):
    """
    Konfiguracija grafa SPAN podataka.
    """
    def __init__(self, cfg):
        logging.debug('Pocetak inicijalizacije postavki grafa sa SPAN podacima')
        super(SpanGrafKonfig, self).__init__()
        self.TIP = 'SPAN'
        self.MIDLINE = 'vrijednost'
        self.WARNING_LOW = 'minDozvoljeno'
        self.WARNING_HIGH = 'maxDozvoljeno'
        #podaci o grafovima
        self.Midline = GrafDTO(cfg, tip='SPAN', podtip='midline', oblik='line')
        self.VOK = GrafDTO(cfg, tip='SPAN', podtip='VOK', oblik='scatter')
        self.VBAD = GrafDTO(cfg, tip='SPAN', podtip='VBAD', oblik='scatter')
        self.Fill1 = GrafDTO(cfg, tip='SPAN', podtip='fill1', oblik='fill')
        self.Fill2 = GrafDTO(cfg, tip='SPAN', podtip='fill2', oblik='fill')
        self.Warning1 = GrafDTO(cfg, tip='SPAN', podtip='warning', oblik='line')
        self.Warning2 = GrafDTO(cfg, tip='SPAN', podtip='warning', oblik='line')
        #interakcija sa grafom
        self.Grid = pomocne_funkcije.load_config_item(cfg,
                                                      'MAIN_WINDOW',
                                                      'action_SPAN_grid',
                                                      False,
                                                      bool)
        self.Legend = pomocne_funkcije.load_config_item(cfg,
                                                        'MAIN_WINDOW',
                                                        'action_SPAN_legend',
                                                        False,
                                                        bool)
        logging.debug('Kraj inicijalizacije postavki grafa sa SPAN podacima')


class RESTKonfig():
    """
    Konfiguracija REST servisa (base url, relative url do ciljanih servisa).
    """
    def __init__(self, cfg):
        logging.debug('Pocetak inicijalizacije postavki REST servisa')
        self.RESTBaseUrl = pomocne_funkcije.load_config_item(cfg,
                                                             'REST_INFO',
                                                             'base_url',
                                                             'http://172.20.1.166:9090/SKZ-war/webresources/',
                                                             str)
        self.RESTProgramMjerenja = pomocne_funkcije.load_config_item(cfg,
                                                                     'REST_INFO',
                                                                     'program_mjerenja',
                                                                     'dhz.skz.aqdb.entity.programmjerenja',
                                                                     str)
        self.RESTSiroviPodaci = pomocne_funkcije.load_config_item(cfg,
                                                                  'REST_INFO',
                                                                  'sirovi_podaci',
                                                                  'dhz.skz.rs.sirovipodaci',
                                                                  str)
        self.RESTZeroSpan = pomocne_funkcije.load_config_item(cfg,
                                                              'REST_INFO',
                                                              'zero_span',
                                                              'dhz.skz.rs.zerospan',
                                                              str)
        self.RESTSatniPodaci = pomocne_funkcije.load_config_item(cfg,
                                                                 'REST_INFO',
                                                                 'satni_podaci',
                                                                 'dhz.skz.rs.satnipodatak',
                                                                 str)
        self.RESTStatusMap = pomocne_funkcije.load_config_item(cfg,
                                                               'REST_INFO',
                                                               'status_map',
                                                               'dhz.skz.rs.sirovipodaci/statusi',
                                                               str)
        self.RESTkomentari = pomocne_funkcije.load_config_item(cfg,
                                                               'REST_INFO',
                                                               'komentari',
                                                               'dhz.skz.rs.komentar',
                                                               str)
        logging.debug('Kraj inicijalizacije postavki REST servisa')


class GrafDTO():
    """
    Objekt u kojem se pohranjuju postavke pojedinog grafa.
    Samo se pohranjuje informacija o izgledu grafa (markeri, linije ...)

    ulazni parametri za inicijalizaciju:
    cfg
        -instanca configparser objekta
    tip
        -string
        -section naziv unutar cfg
        -dozvoljeni su [SATNI, MINUTNI, POMOCNI, ZERO, SPAN]
    podtip
        -string
        -prvi dio optiona npr. 'midline'
        -dozvoljeni su [midline, ekstrem, VOK, VBAD, NVOK, NVBAD, fill1,
                        fill2, warning]
    oblik
        -string
        -oblik grafa za crtanje [plot, line, scatter, fill]
        -regulira tjek inicijalizacije, tj. sto se inicijalizira
        -npr. scatter graf nemaju podatke o liniji, line grafu ne treba
        informacija o izgledu markera...
    """

    def __init__(self, cfg, tip='', podtip='', oblik='plot'):
        msg = 'Pocetak inicijalizacije postavki grafa za {0} - {1} - {2}'.format(tip, podtip, oblik)
        logging.debug(msg)
        self._sviMarkeri = ['None', 'o', 'ˇ', '^', '<', '>', '|', '_',
                            's', 'p', '*', 'h', '+', 'x', 'd']
        self._sveLinije = ['None', '-', '--', '-.', ':']
        self._sveAgregiraneKomponente = ['avg', 'q05', 'q95', 'min', 'max', 'medijan']
        self.tip = tip
        self.podtip = podtip
        self.oblik = oblik
        #rgb, alpha, status crtanja, zorder, label grafa se definiraju neovisno o obliku
        self.rgb = self.init_rgb(cfg, self.tip, self.podtip)
        self.alpha = self.init_alpha(cfg, self.tip, self.podtip)
        self.color = pomocne_funkcije.make_color(self.rgb, self.alpha)
        self.crtaj = self.init_crtaj(cfg, self.tip, self.podtip)
        self.zorder = self.init_zorder(cfg, self.tip, self.podtip)
        self.label = self.init_label(cfg, self.tip, self.podtip)
        if oblik == 'plot':
            #marker i linija
            self.markerStyle = self.init_markerStyle(cfg, self.tip, self.podtip)
            self.markerSize = self.init_markerSize(cfg, self.tip, self.podtip)
            self.lineStyle = self.init_lineStyle(cfg, self.tip, self.podtip)
            self.lineWidth = self.init_lineWidth(cfg, self.tip, self.podtip)
        elif oblik == 'line':
            #samo linija
            self.markerStyle = 'None'
            self.markerSize = 12
            self.lineStyle = self.init_lineStyle(cfg, self.tip, self.podtip)
            self.lineWidth = self.init_lineWidth(cfg, self.tip, self.podtip)
        elif oblik == 'scatter':
            #samo marker
            self.markerStyle = self.init_markerStyle(cfg, self.tip, self.podtip)
            self.markerSize = self.init_markerSize(cfg, self.tip, self.podtip)
            self.lineStyle = 'None'
            self.lineWidth = 1.0
        elif oblik == 'fill':
            self.markerStyle = 'None'
            self.markerSize = 12
            self.lineStyle = 'None'
            self.lineWidth = 1.0
            if tip == 'SATNI':
                #fill between satnog grafa, izmedju kojih komponenti se sjenca
                self.komponenta1 = self.init_komponenta1(cfg, self.tip, self.podtip)
                self.komponenta2 = self.init_komponenta2(cfg, self.tip, self.podtip)
        msg = 'Kraj inicijalizacije postavki grafa za {0} - {1} - {2}'.format(tip, podtip, oblik)
        logging.debug(msg)

    def init_label(self, cfg, tip, podtip):
        """inicijalizacija labela grafa"""
        placeholder = podtip + ' label placeholder'
        podtip += '_label_'
        val = pomocne_funkcije.load_config_item(cfg, tip, podtip, placeholder, str)
        return str(val)

    def set_label(self, x):
        """setter za label grafa"""
        self.label = str(x)
        msg = 'Promjena rgb za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
        logging.debug(msg)

    def init_zorder(self, cfg, tip, podtip):
        """inicijalizacija zorder grafa"""
        podtip += '_zorder_'
        val = pomocne_funkcije.load_config_item(cfg, tip, podtip, 2, int)
        if self.test_zorder(val):
            return int(val)
        else:
            return 2

    def set_zorder(self, x):
        """setter zorder grafa"""
        if self.test_zorder(x):
            self.zorder = x
            msg = 'Promjena zorder za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def test_zorder(self, x):
        """provjera ispravnosti zorder"""
        if x > 1:
            return True
        else:
            return False

    def init_komponenta1(self, cfg, tip, podtip):
        """inicijalizacija prve komponente za sjencanje grafa (od)"""
        podtip += '_komponenta1_'
        val = pomocne_funkcije.load_config_item(cfg, tip, podtip, 'q05', str)
        if self.test_fill_komponenta(val):
            return val
        else:
            return 'q05'

    def init_komponenta2(self, cfg, tip, podtip):
        """inicijalizacija druge komponente za sjencanje grafa (do)"""
        podtip += '_komponenta2_'
        val = pomocne_funkcije.load_config_item(cfg, tip, podtip, 'q95', str)
        if self.test_fill_komponenta(val):
            return val
        else:
            return 'q95'

    def test_fill_komponenta(self, x):
        """provjera ispravnosti zadane komponente za sjencanje grafa"""
        if x in self._sveAgregiraneKomponente:
            return True
        else:
            return False

    def set_komponenta1(self, x):
        """setter prve komponente za sjencanje grafa (od)"""
        if self.test_fill_komponenta:
            self.komponenta1 = x
            msg = 'Promjena fill komponente za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def set_komponenta2(self, x):
        """setter druge komponente za sjencanje grafa (od)"""
        if self.test_fill_komponenta:
            self.komponenta2 = x
            msg = 'Promjena fill komponente za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def init_rgb(self, cfg, tip, podtip):
        """inicjalizacija rgb boje grafa"""
        podtip += '_rgb_'
        rgb = pomocne_funkcije.load_config_item(cfg, tip, podtip, (0, 0, 255), tuple)
        # dohvati samo prva 3 elementa
        rgb = rgb[:3]
        #convert to integer vrijednost
        rgb = tuple([int(i) for i in rgb])
        if self.test_rgb(rgb):
            return rgb
        else:
            return 0, 0, 255

    def test_rgb(self, x):
        """provjera ispravnosti rgb boje grafa"""
        out = True
        for i in x:
            if 0 <= i <= 255:
                out = (out and True)
            else:
                out = (out and False)
        return out

    def set_rgb(self, x):
        """setter rgb boje grafa"""
        if self.test_rgb(x):
            self.rgb = x
            self.color = pomocne_funkcije.make_color(x, self.alpha)
            msg = 'Promjena rgb (boje) za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def init_alpha(self, cfg, tip, podtip):
        """inicjalizacija alpha, prozirnosti grafa"""
        podtip += '_alpha_'
        alpha = pomocne_funkcije.load_config_item(cfg, tip, podtip, 1.0, float)
        if self.test_alpha(alpha):
            return alpha
        else:
            return 1.0

    def test_alpha(self, x):
        """provjera ispravnosti alpha, prozirnosti grafa"""
        if x >= 0.0 and x <= 1.0:
            return True
        else:
            return False

    def set_alpha(self, x):
        """setter alpha, prozirnosti grafa"""
        if self.test_alpha(x):
            self.alpha = x
            self.color = pomocne_funkcije.make_color(self.rgb, x)
            msg = 'Promjena alpha (prozirnost) za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def init_crtaj(self, cfg, tip, podtip):
        """inicjalizacija statusa crtanja grafa"""
        podtip += '_crtaj_'
        boolCrtaj = pomocne_funkcije.load_config_item(cfg, tip, podtip, True, bool)
        return boolCrtaj

    def set_crtaj(self, x):
        """setter statusa crtanja grafa"""
        self.crtaj = x
        msg = 'Promjena statusa crtanja za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
        logging.debug(msg)

    def init_markerStyle(self, cfg, tip, podtip):
        """inicjalizacija stila markera grafa"""
        podtip += '_markerStyle_'
        marker = pomocne_funkcije.load_config_item(cfg, tip, podtip, 'o', str)
        if self.test_markerStyle(marker):
            return marker
        else:
            return 'o'

    def test_markerStyle(self, x):
        """provjera ispravnosti stila markera grafa"""
        if x in self._sviMarkeri:
            return True
        else:
            return False

    def set_markerStyle(self, x):
        """setter stila markera grafa"""
        if self.test_markerStyle(x):
            self.markerStyle = x
            msg = 'Promjena stila markera za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def init_markerSize(self, cfg, tip, podtip):
        """inicjalizacija velicine markera grafa"""
        podtip += '_markerSize_'
        size = pomocne_funkcije.load_config_item(cfg, tip, podtip, 12, int)
        if self.test_markerSize(size):
            return size
        else:
            return 12

    def test_markerSize(self, x):
        """provjera ispravnosti velicine markera grafa"""
        if x > 0:
            return True
        else:
            return False

    def set_markerSize(self, x):
        """setter velicine markera grafa"""
        if self.test_markerSize(x):
            self.markerSize = x
            msg = 'Promjena velicine markera za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def init_lineStyle(self, cfg, tip, podtip):
        """inicijalizacija stila linije grafa"""
        podtip += '_lineStyle_'
        stil = pomocne_funkcije.load_config_item(cfg, tip, podtip, '-', str)
        if self.test_lineStyle(stil):
            return stil
        else:
            return '-'

    def test_lineStyle(self, x):
        """provjera ispravnosti stila linije grafa"""
        if x in self._sveLinije:
            return True
        else:
            return False

    def set_lineStyle(self, x):
        """setter stila linije grafa"""
        if self.test_lineStyle(x):
            self.lineStyle = x
            msg = 'Promjena stila linije za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)

    def init_lineWidth(self, cfg, tip, podtip):
        """inicijalizacija sirine linije grafa"""
        podtip += '_lineWidth_'
        sirina = pomocne_funkcije.load_config_item(cfg, tip, podtip, 1.0, float)
        if self.test_lineWidth(sirina):
            return sirina
        else:
            return 1.0

    def test_lineWidth(self, x):
        """provjera ispravnosti sirine linije grafa"""
        if x > 0:
            return True
        else:
            return False

    def set_lineWidth(self, x):
        """setter sirine linije grafa"""
        if self.test_lineWidth(x):
            self.lineWidth = x
            msg = 'Promjena sirine linije za {0} - {1}, nova vrijednost={2}'.format(self.tip, self.podtip, str(x))
            logging.debug(msg)
