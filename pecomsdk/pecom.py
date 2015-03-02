# -*- coding: utf-8 -*-
# Pecom Kabinet SDK
# Russian PEC cargo company  API wrapper
# Ported from PHP version https://kabinet.pecom.ru/api/v1#toc-usage-phpsdk
# for Teleme Team project
# Author Oleg Rybkin aka Fish (okfish@yandex.ru)

import os
import json
import pycurl

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

location = lambda x: os.path.join(
    os.path.dirname(os.path.realpath(__file__)), x)


API_SSL_KEYFILE = location('cacert-kabinet_pecom_ru.pem') 
API_VERSION = '1.0'
API_BASE_URL = 'https://kabinet.pecom.ru/api/v1/'

# Source: https://kabinet.pecom.ru/api/v1/help/calculator#toc-method-calculateprice
PECOM_CALC_OPTIONS = { 
   "senderCityId": '', # Код города отправителя [Number]
   "receiverCityId": '', # Код города получателя [Number]
   "isOpenCarSender": False, # Растентовка отправителя [Boolean]
   "senderDistanceType": 0, # Тип доп. услуг отправителя [Number]
                            # 0 - доп. услуги не нужны
                            # 1 - СК
                            # 2 - МОЖД
                            # 3 - ТТК
   "isDayByDay": False, # Необходим забор день в день [Boolean]
   "isOpenCarReceiver": False, # Растентовка получателя [Boolean]
   "receiverDistanceType": 0, # Тип доп. услуг отправителя [Number]
                              # кодируется аналогично senderDistanceType
   "isHyperMarket": False, # признак гипермаркета [Boolean]
   "calcDate": "2014-01-21", # расчетная дата [Date]
   "isInsurance": True, # Страхование [Boolean]
   "isInsurancePrice": 0, # Оценочная стоимость, руб [Number]
   "isPickUp": False, # Нужен забор [Boolean]
   "isDelivery": False, # Нужна доставка [Boolean]
   "Cargos": [{ # Данные о грузах [Array]
      "length": 0, # Длина груза, м [Number]
      "width": 0, # Ширина груза, м [Number]
      "height": 0, # Высота груза, м [Number]
      "volume": 0, # Объем груза, м3 [Number]
      "maxSize": 3.2, # Максимальный габарит, м [Number]
      "isHP": False, # Жесткая упаковка [Boolean]
      "sealingPositionsCount": 0, # Количество мест для пломбировки [Number]
      "weight": 10, # Вес, кг [Number]
      "overSize": False # Негабаритный груз [Boolean]
   },]
}

def curl_setopt_array(curl, opts):
    for key in opts:
        curl.setopt(getattr(curl, key), opts[key])
        
class PecomCabinetException(Exception):
    """
    PecomCabinet class can raise this exception
    """
    pass

class PecomCabinet(object):
    """
    Main Pecom SDK class. 
    Handles calls to the Pecom Kabinet API via pycURL
    """
    #API user name
    __api_login = ''

    # API access key
    __api_key = ''

    # Base URL
    __api_url = '';

    # CURL options overrides
    __curl_opts = {}
    
    # CURL instance
    __ch = None;
    
    # CURL IO buffer
    __buffer = None
    
    def __init__(self, api_login, api_key, api_url=None, curl_opts={}):
        """
        Cabinet constructor 
        required parameters: api_login, api_key, api_url
        """
        self.__api_login = api_login
        self.__api_key = api_key
        self.__api_url = api_url or API_BASE_URL
        self.__curl_opts = curl_opts
        self.__buffer = BytesIO()
  
    def __init_curl(self):
       self.__ch = pycurl.Curl()
       opts = {'WRITEDATA':  self.__buffer,
               #'RETURNTRANSFER': True,
               'POST': True,
               'SSL_VERIFYPEER': True,
               'SSL_VERIFYHOST': 2,
               'CAINFO': API_SSL_KEYFILE,
               'HTTPAUTH': pycurl.HTTPAUTH_BASIC,
               'USERPWD': "%s:%s" % (self.__api_login, self.__api_key),
               'ENCODING': 'gzip',
               'HTTPHEADER': ['Content-Type: application/json; charset=utf-8',],
               'NOSIGNAL' : 1 # see http://stackoverflow.com/questions/9191668/error-longjmp-causes-uninitialized-stack-frame
               }
       opts.update(self.__curl_opts)
       curl_setopt_array(self.__ch, opts)

    def __construct_api_url(self, controller, action):
        return '%s%s/%s/' % (self.__api_url, controller, action)
    
    def close(self):
        if self.__ch:
            self.__ch.close()
        if not self.__buffer.closed:
            self.__buffer.close()
            
    def call(self, controller, action, data, assoc=False):
        """Makes a call to remote API. 
        
        """
        result = None
        #if self.__buffer.closed:
        #    self.__buffer = BytesIO()
                    
        if self.__ch is None:
            self.__init_curl()

        json_data = json.dumps(data)
        curl_setopt_array(self.__ch, { 'URL' : self.__construct_api_url(controller, action),
                                       'POSTFIELDS' : json_data,
                                       })
        try:
            self.__ch.perform()
        except pycurl.error as e:
            raise PecomCabinetException(e)
        result = self.__buffer.getvalue()
        if self.__ch.errstr():
            raise PecomCabinetException(self.__ch.c.errstr())
        else:
            http_code = self.__ch.getinfo(pycurl.HTTP_CODE)
            if http_code <> 200:
                raise PecomCabinetException("HTTP Error code: %d" % http_code)
            else:
                result = json.loads(result)
        self.__buffer.truncate(0)
        self.__buffer.seek(0)
        return result
    
    def findbytitle(self, city):
        """
        Finds PEC city code by title given.
        Return tuple (result, error), where result is a list of tuples
        (cityId, branchtitle, cityTitle) 
        See: https://kabinet.pecom.ru/api/v1/help/branches#toc-method-findbytitle
        """
        result = []
        data = { 'title' : city }
        try:
            res = self.call('branches', 'findbytitle', data)
        except PecomCabinetException as e:
            return None, e
        if res['success']:
            for city in res['items']:
                result.append(((city['cityId'] or city['branchId']),
                              city['branchTitle'],
                              city['cityTitle'],
                              ))
            return result, 0
        else:
            return None, 'not_found'
        
    def get_branches(self):
        """
        Returns a tuple of (list, error) of all PEC branches 
        and cities in the native API format.
        See: https://kabinet.pecom.ru/api/v1/help/branches#toc-method-all
        """
        res = []
        data = {}
        try:
            res = self.call('branches', 'all', data)
        except PecomCabinetException as e:
            return None, e
        if res['branches']:
            return res['branches'], 0
        else:
            return None, 'no_branches_found'
        
    def calculate(self, payload):
        """
        Calculates shipping charge using API.
        See: https://kabinet.pecom.ru/api/v1/help/calculator#toc-method-calculateprice
        """
        data = PECOM_CALC_OPTIONS
        data.update(payload)
        
        res = []
        
        try:
            res = self.call('calculator', 'calculateprice', data)
        except PecomCabinetException as e:
            return None, e
        return res, 0