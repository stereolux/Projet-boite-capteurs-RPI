#!/usr/bin/env python

import time
import os
import RPi.GPIO as GPIO
import time

from uuid import getnode as get_mac
IDRASPBERRY = get_mac() 		# MAC is used like id for Raspberry

DEBUG = 1
# change these as desired - they're the pins connected from the
# SPI port on the ADC to the Cobbler
SPICLK 			= 18
SPIMISO 		= 23
SPIMOSI 		= 24
SPICS0 			= 25

ADCTEMP			= 0
ADCMAG			= 1

ALIM_VOLTAGE 		= 3300.0	# In millivolts
RESOLUTION		= 1024.0	# Resolution of the ADC

INDIDSENSOR		= 0
INDNUMCS		= 1
INDNUMADC		= 2
INDTYPE			= 3
INDUNIT			= 4
INDACTIV		= 5
INDPERIODRT		= 6
INDPERIODDB		= 7

MFLIMIT			= 1024 / 2

SERVER_IP		= '192.168.43.12:3000'

########### This part of the code relates to the management of sensors ###########

# List of sensors
sensorList = [];

# This function return the ID of the sensor
#
# @param sensor : information relates to the sensor
# @return the ID of the sensor
def getIDSensor(sensor):
	return sensor[INDIDSENSOR]

# This function return the CS pin of the
# ADC which is connected to the sensor
#
# @param sensor : information relates to the sensor
# @return the number of the CS pin of the ADC
def getNumCS(sensor):
	return sensor[INDNUMCS]

# This function return the number of the pin of the
# ADC which is connected to the sensor
#
# @param sensor : information relates to the sensor
# @return the number of the pin of the ADC
def getNumADC(sensor):
	return sensor[INDNUMADC]

# This function return the type of data of the sensor
#
# @param sensor : information relates to the sensor
# @return the type of data of the sensor
def getType(sensor):
	return sensor[INDTYPE]

# This function return the unit of the type of data of the sensor
#
# @param sensor : information relates to the sensor
# @return the unit of the type of data of the sensor
def getUnit(sensor):
	return sensor[INDUNIT]

# This function return True if the sensor is activate
#
# @param sensor : information relates to the sensor
# @return the state of activation of the sensor
def getActiv(sensor):
	return sensor[INDACTIV]

# This function return the period of the measure to send
# to RT API
#
# @param sensor : information relates to the sensor
# @return the period of the measure (in second)
def getPeriodRT(sensor):
	return sensor[INDPERIODRT]

# This function return the period of the measure to send to
# database
#
# @param sensor : information relates to the sensor
# @return the period of the measure (in second)
def getPeriodDB(sensor):
	return sensor[INDPERIODDB]

# This method permit to activate or disactivate the sensor measure
#
# @param sensor : information relates to the sensor
# @param value : the state of activation of the sensor
def setActiv(sensor, value):
	sensor[INDACTIV] = value

# This method activate the sensor which the IDSensor is the
# same than the IDSensor in parameter
#
# @param IDSensor : the ID of the sensor to activate
def activateSensor(IDSensor):
	found = False
	i = 0
	while ((found == False) and (i < len(sensorList))):
		if (IDSensor == getIDSensor(sensorList[i])):
			setActiv(sensorList[i], True)
			found = True
			if DEBUG:
				print("Activation effectuee")
				print('\n')
		i += 1

# This method deactivate the sensor which the IDSensor is the
# same than the IDSensor in parameter
#
# @param IDSensor : the ID of the sensor to deactivate
def deactivateSensor(IDSensor):
	found = False
	i = 0
	while ((found == False) and (i < len(sensorList))):
		if (IDSensor == getIDSensor(sensorList[i])):
			setActiv(sensorList[i], False)
			found = True
			if DEBUG :
				print("Desactivation effectuee")
				print('\n')
		i += 1

# This method add a sensor 
#
# @param IDSensor : the ID of the sensor
# @param numCS : the number of the CS pin of the ADC
# @param numADC : the number of the pin of the ADC
# @param type : the type of data of the sensor
# @param unit : the unit of the type of data of the sensor
# @param activ : the state of activation of the sensor
# @param periodRT : the periode of the measure (in second) for RT
# @param periodDB : the periode of the measure (in second) for DB
def addSensor(IDSensor, numCS, numADC, type, unit, activ, periodRT, periodDB):
	sensorList.append([IDSensor, numCS, numADC, type, unit, activ, periodRT, periodDB])
	if DEBUG:
		print("Ajout effectue!")
		print('\n')

# This method delete a sensor 
#
# @param IDSensor : the ID of the sensor
def deleteSensor(IDSensor):
	found = False
	i = 0
	while ((found == False) and (i < len(sensorList))):
		if (IDSensor == getIDSensor(sensorList[i])):
			sensorList.remove(sensorList[i])
			found = True
			if DEBUG:
				print("Suppression effectuee")
				print('\n')
		i += 1

# This method initialise the list of sensors
def initSensors():
	sensorList = []
	addSensor(1000, SPICS0, ADCTEMP, "Temperature", "degre Celsius", True, 1.0, 5.0)
	addSensor(1001, SPICS0, ADCMAG, "Champ_magnetique", "TOR", True, 2.0, 10.0)

############## Code relates to ADCs connected to the Raspberry #####################

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
        if ((adcnum > 7) or (adcnum < 0)):
                return -1
        GPIO.output(cspin, True)

        GPIO.output(clockpin, False)  # start clock low
        GPIO.output(cspin, False)     # bring CS low

        commandout = adcnum
        commandout |= 0x18  # start bit + single-ended bit
        commandout <<= 3    # we only need to send 5 bits here
        for i in range(5):
                if (commandout & 0x80):
                        GPIO.output(mosipin, True)
                else:   
                        GPIO.output(mosipin, False)
                commandout <<= 1
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)

        adcout = 0
        # read in one empty bit, one null bit and 10 ADC bits
        for i in range(12):
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)
                adcout <<= 1
                if (GPIO.input(misopin)):
                        adcout |= 0x1

        GPIO.output(cspin, True)

        adcout /= 2       # first bit is 'null' so drop it
        return adcout

##################### Code relates to the signal processing ###################

# This function convert the value send by the ADC to the raspeberry
# in millivolts
# 
# @param ADCvalue : the value from the ADC
# @return the value of the ADC convert in millivolts
def convert_millivolts(ADCvalue):
	# convert analog reading to millivolts = ADC * ( 3300 / 1024 )
        return ADCvalue * (ALIM_VOLTAGE / RESOLUTION)

# This function filter the temperature and convert the value in deg Celsius
#
# @param ADCvalue_millivolts : the value of the ADC convert in millivolts
# @return the temperature filtered in deg Celsius
def filterTemp(ADCvalue_millivolts):
	
        # 10 mv per degree 
        temp_C = ((ADCvalue_millivolts - 100.0) / 10.0) - 40.0

        # show only one decimal place for temperature and voltage readings
        return "%.1f" % temp_C

# This function filter the magnetic field and convert the value in TOR
#
# @param ADCvalue_millivolts : the value of the ADC convert in millivolts
# @return the magnetic field filtered in TOR
def filterMF(ADCvalue_millivolts):
	
        if (ADCvalue_millivolts > MFLIMIT):
		return 1
	else:
		return 0

# This function filter the data in function of its type
#
# @param millivolts : the value in millivolts of the ADC
# @param type : the type of the value
# @return the value filtered
def filter(ADCvalue_millivolts, type):
	if (type == 'Temperature'):
		return filterTemp(ADCvalue_millivolts)
	elif (type == 'Champ_magnetique'):
		return filterMF(ADCvalue_millivolts)
	else:
		return ADCvalue_millivolts

############ Code relates to the communication between Raspberry and Server #########

# This method send data to the server
# 
# @param dataJSON : the string in JSON which contain information
# @param url : the URL of the server
def sendDataJSON(dataJSON, url):
	aux = 'curl -X POST -H "Content-Type: application/json" '
	aux += '-d \'' + dataJSON + '\' '
	aux += url

	if DEBUG:
		print(aux)
		print('\n')

	os.system(aux)

# This method send the data in JSON to the RT
#
# @param value_norm the value normalise to the unit
# @param dateMeasure the date of the measure
# @param sensor information about sensor
# @param url : url of the server
def sendDataSensorJSONtoRT(value_norm, dateMeasure, hourMeasure, sensor, url):
	dataJSON = '{"IDRaspberry" : "' + str(IDRASPBERRY) + \
		'", "IDSensor" : "' + str(getIDSensor(sensor)) + \
		'", "type" : "' + getType(sensor) + \
		'", "unit" : "' + getUnit(sensor) + \
		'", "RT" : "1' + \
		'", "value" : "' + str(value_norm) + \
		'", "date" : "' + dateMeasure + \
		'", "hour" : "' + hourMeasure + '"}'
	sendDataJSON(dataJSON, url)

# This method send the data in JSON to the DB
#
# @param value_norm the value normalise to the unit
# @param dateMeasure the date of the measure
# @param sensor information about sensor
# @param url : url of the server
def sendDataSensorJSONtoDB(value_norm, dateMeasure, hourMeasure, sensor, url):
	dataJSON = '{"IDRaspberry" : "' + str(IDRASPBERRY) + \
		'", "IDSensor" : "' + str(getIDSensor(sensor)) + \
		'", "type" : "' + getType(sensor) + \
		'", "unit" : "' + getUnit(sensor) + \
		'", "RT" : "0' + \
		'", "value" : "' + str(value_norm) + \
		'", "date" : "' + dateMeasure + \
		'", "hour" : "' + hourMeasure + '"}'
	sendDataJSON(dataJSON, url)

############### Code relates to the initialisation of the Raspberry ################

# This method initialise the Raspberry
def start():

	GPIO.setmode(GPIO.BCM)

	# set up the SPI interface pins
	GPIO.setup(SPIMOSI, GPIO.OUT)
	GPIO.setup(SPIMISO, GPIO.IN)
	GPIO.setup(SPICLK, GPIO.OUT)
	GPIO.setup(SPICS0, GPIO.OUT)

	initSensors()

################## Code relates to the comportment of the Raspberry ##############

# Initialisation of the Raspberry
start()

for sensor in sensorList:

	newPid = os.fork()
	if (newPid == 0):
		cptSendDB = 0
		while True:			

        		# read the analog pin (sensor)
        		ADCValue = readadc(getNumADC(sensor), SPICLK, SPIMOSI, SPIMISO, getNumCS(sensor))
		
			# converion of the value in millivolts
			millivolts = convert_millivolts(ADCValue)

			# filter of the 
			value_norm = filter(millivolts, getType(sensor))

			# Recovery the date
			dateMeasure = time.strftime('%d-%m-%y', time.localtime())
			hourMeasure = time.strftime('%H:%M:%S', time.localtime())
			if DEBUG:
				print(dateMeasure + "  " + hourMeasure + "\n")
			
			#send data in RT
			sendDataSensorJSONtoRT(value_norm, dateMeasure, hourMeasure, sensor, 'http://' + SERVER_IP + '/publish')
			
			if (cptSendDB > getPeriodDB(sensor)/getPeriodRT(sensor)):
				sendDataSensorJSONtoDB(value_norm, dateMeasure, hourMeasure, sensor, 'http://' + SERVER_IP + '/publish')
				cptSendDB = 0
			
        		# time to wait before the next measure
			# the time should be a floating like 0.5, which
			# represent half of a second
        		time.sleep(getPeriodRT(sensor))

			cptSendDB += 1

os._exit(0)
