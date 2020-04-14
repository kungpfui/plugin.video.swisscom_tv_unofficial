# -*- coding: utf-8 -*-


_translate = {
  'Language': dict(en='Language', de='Sprache', fr='Langue', it='Lingua'),
  'Resolution': dict(en='Resolution', de='Auflösung', fr='Résolution', it='Risoluzione'),
}


import xbmc

class Lang:
    supported_lang = ('en', 'de', 'fr', 'it')
    def __init__(self, settings):
        """
        :return: iso639-1 language identification
        """
        # local override is possible
        self.lang = settings.getSetting("channel_description_language").lower()
        if self.lang not in self.supported_lang:
            # use 'default' interface language
            self.lang = xbmc.getLanguage(xbmc.ISO_639_1)
            if self.lang not in self.supported_lang:
                self.lang = self.supported_lang[0]

    def translate(self, text):
        if text not in _translate:
            return text
        return _translate[text][self.lang]

    def __str__(self):
        return self.lang
