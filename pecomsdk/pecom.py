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
        result = None
        #if self.__buffer.closed:
        #    self.__buffer = BytesIO()
                    
        if self.__ch is None:
            self.__init_curl()

        json_data = json.dumps(data)
        curl_setopt_array(self.__ch, { 'URL' : self.__construct_api_url(controller, action),
                                       'POSTFIELDS' : json_data,
                                       })
        self.__ch.perform()
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
        result = []
        data = { 'title' : city }
        try:
            res = self.call('branches', 'findbytitle', data)
        except PecomCabinetException(e):
            return False, e
        if res['success']:
            for city in res['items']:
                result.append(((city['cityId'] or city['branchId']),
                              city['branchTitle'],
                              city['cityTitle'],
                              ))
            return result, 0
        else:
            return False, 'not_found'
        