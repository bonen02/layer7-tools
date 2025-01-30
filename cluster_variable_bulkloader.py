#!/usr/bin/env python3
'''
Script per la creazione di molteplici cluster-wide properties in API Gateway

Legge variabili dallo stdin e le crea nuove via RestMan

Author: Enrico Bonato <enrico.bonato@hcl.com>
Version: 0.1.0
Date: 29/06/2022

'''

import xml.etree.ElementTree as ET
from sys import stdin
import os
import ssl
import logging
import base64
import http.client
import configparser

class RestMan:
    """
    Connection to API Gateway RestMan service
    """
    def __init__(self, config):
        """
        Constructor for 'APIMCertLoader', sets the default parameters from a config
        
        :param config: a dictionary containing the configuration parameters 
        """
        level=logging._nameToLevel[config.get("log_level", 'INFO').upper()]
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level)
        logging.info("new RestMan client initialized")
        
        # Set connection parameters
        self.server    = config.get("server")
        self.port      = config.get("port", "8443")
        
        # Set headers with Authorization: Basic
        username  = config.get("username", "admin")
        password  = config.get("password")
        
        
        cred_str = username + ":" + password
        cred_bytes = base64.b64encode(cred_str.encode('utf-8'))
        authorization="Basic " + cred_bytes.decode('utf-8')
        
        logging.debug("authorization header: " + authorization)
        
        self.headers = {
            'content-type': "application/xml",
            'authorization': authorization
        }
        
        # unlikely to be modified
        self.NS = config.get("namespace", '{http://ns.l7tech.com/2010/04/gateway-management}')
        self.baseurl = config.get("baseurl", '/restman/1.0')
    
    def get_conn(self):
        """
        Get a new connection to API Gateway RESTMAN service url, with a custom SSL context
        
        :return: the connection object
        """
        
        # Initialize custom context 
        sslcontext = ssl._create_unverified_context()
        sslcontext.set_ciphers('ALL:@SECLEVEL=1')
        
        conn = http.client.HTTPSConnection(
            self.server, 
            port=self.port,
            context=sslcontext
        )
        logging.debug("new connection to %s:%s", self.server, self.port)
        return conn

    def create_variable(self, key, value, do_check=True):
        """
        Create a new variable on API Gateway
        
        :param key: the variable name (mandatory)
        :param value: the variable value (mandatory)
        :return: the ID of the variable created
        """
        # XML Template
        payload_template="""
<l7:ClusterProperty xmlns:l7="http://ns.l7tech.com/2010/04/gateway-management">
                <l7:Name>{key}</l7:Name>
                <l7:Value>{value}</l7:Value>
</l7:ClusterProperty>
        """
        
        serviceurl = self.baseurl + "/clusterProperties"
        
        
        payload=payload_template.format(key=key, value=value)
        logging.debug("payload formatted: %s", payload)
        
        #Create User
        c = self.get_conn()
        logging.debug("connection set")
        
        c.request("POST", serviceurl, payload, headers=self.headers)
        response = c.getresponse()
        
        #get RESTMAN response
        content = response.read()
        logging.debug("response: " + str(content))

        #return None if failed, log status and message
        if response.getcode() >= 400:
            logging.error("variable creation failed: HTTP %d", response.getcode())
            logging.error("message: %s",  xml_root.find(self.NS + 'Detail').text)
            return None
        
        logging.debug("Completed creation of variable %s", key)
        
        xml_root = ET.XML(content.decode('utf-8'))
        var_id = xml_root.find(self.NS + 'Id').text

        return var_id
    

if __name__ == '__main__':
    parser = configparser.ConfigParser()
    parser.read('config.ini')
    config = parser["gateway"]
    restman = RestMan(config)
    
    for line in stdin:
        key, value = line.strip().split('=')
        logging.info("Creation of variable %s", key)
        restman.create_variable(key, value)
