#!/usr/bin/env python3
"""
Forked from https://github.com/daniel-widrick/zap2it-GuideScraping
All credit goes to daniel-widrick.

Updated to use python3. Switching to python3 improved CPU usage and reduced A
processing time to generate xmlguide.xmltv.
"""
#Required libraries
import configparser
import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse
import json
import time
import math
import html
#Additional Libraries for Parameter Parsing
import sys, getopt
#Libraries for historical copies
import datetime, os

def sanitizeData(data):
	#https://stackoverflow.com/questions/1091945/what-characters-do-i-need-to-escape-in-xml-documents
	sData = data.replace('"','&quot;')
	sData = sData.replace("'",'&apos;')
	sData = sData.replace('<','&lt;')
	sData = sData.replace('<','&gt;')
	sData = sData.replace('&','&amp;')
	return sData;
def buildXMLChannel(channel):
	xml = ""
	xml = xml + '    <channel id="' +  sanitizeData(channel["channelId"]) + '">' + "\n"
	xml = xml + '      <display-name>' + sanitizeData(channel["channelNo"] + " " + channel["callSign"]) + '</display-name>' + "\n"
	xml = xml + '      <display-name>' + sanitizeData(channel["channelNo"]) + '</display-name>' + "\n"
	xml = xml + '      <display-name>' + sanitizeData(channel["callSign"]) + '</display-name>' + "\n"
	xml = xml + '    </channel>' + "\n"
	return xml

def buildXMLProgram(event,channelId):
	#2018-04-11T21:00:00Z
	#20180408120000 +0000
	xml = ""
	xml = xml + '    <programme start="' + buildXMLDate(event["startTime"]) + '" '
	xml = xml + 'stop="' + buildXMLDate(event["endTime"]) + '" channel="' + sanitizeData(channelId) + '">' + "\n"
	xml = xml + '      <title lang="' + optLanguage + '">' + sanitizeData(event["program"]["title"]) + '</title>' + "\n"
	if event["program"]["episodeTitle"] is not None:
		xml = xml + '      <sub-title lang="' + optLanguage + '">' + sanitizeData(event["program"]["episodeTitle"]) + ' </sub-title>' + "\n"
	if event["program"]["shortDesc"] is None:
		event["program"]["shortDesc"] = "Unavailable"
	xml = xml + '      <desc lang="' + optLanguage + '">' + html.escape(event["program"]["shortDesc"]) + '</desc>' + "\n"
	xml = xml + '      <length units="minutes">' + sanitizeData(event["duration"]) + '</length>' + "\n"
	for category in event["filter"]:
		xml = xml + '      <category>' + sanitizeData(category.replace('filter-','')) + '</category>' + "\n"
	if event["thumbnail"] is not None:
		xml = xml + '      <thumbnail>http://zap2it.tmsimg.com/assets/' + event["thumbnail"] + '.jpg</thumbnail>' + "\n"
		xml = xml + '      <icon src="http://zap2it.tmsimg.com/assets/' + event["thumbnail"] + '.jpg" />' + "\n"
	if event["rating"] is not None:
		xml = xml + '      <rating>' + "\n"
		xml = xml + '           <value>' + event["rating"] + '</value>' + "\n"
		xml = xml + '      </rating>' + "\n"
	xml = xml + '      <subtitles type="teletext" />' + "\n"
	season = "0"
	episode = "0"
	episodeid = ""
	
	try:
	#if "season" in event:
		if event["program"]["season"] is not None:
			season = str(event["program"]["season"])
		if event["program"]["episode"] is not None:
			episode = str(event["program"]["episode"])

	#if "id" in event:
		if event["program"]["id"] is not None:
			episodeid = str(event["program"]["id"])
	except KeyError:
		print("no season for:" + event["program"]["title"])
		
	#print season + "." + episode
	if ((int(season) != 0) and (int(episode) != 0)):
		if int(season) < 10:
			season = "0" + str(season)
		if int(episode) < 10:
			episode = "0" + str(episode)
		xml = xml + '      <episode-num system="SxxExx">S' + season + "E" + episode + "</episode-num>" + "\n"
		xml = xml + '      <episode-num system="common">S' + season + "E" + episode + "</episode-num>" + "\n"

	showid = event["seriesId"].replace('SH','')
	episodeid = episodeid.replace('EP' + showid,'')
	xml = xml + '      <episode-num system="dd_progid">EP' + sanitizeData(showid + '.' + episodeid) + '</episode-num>' + "\n"
	
	xml = xml + '    </programme>'+"\n"
	return xml

def buildXMLDate(inputDateString):
	outputDate = inputDateString.replace('-','')
	outputDate = outputDate.replace('T','')
	outputDate = outputDate.replace(':','')
	outputDate = outputDate.replace('Z',' +0000')
	return outputDate

#Add Paramter options for config file and guide file
optConfigFile = './xap2itconfig.ini'
optGuideFile = 'xmlguide.xmltv'
optLanguage = 'en'
try:
	opts, args = getopt.getopt(sys.argv[1:],"hi:o:l:",["ifile=","ofile=","language="])
except getopt.GetoptError:
	print("zap2it-GuideScrape.py [-i <inputfile> ] [-o <outputfile>] [-l <language>")
	sys.exit()

for opt, arg in opts:
	if opt == '-h':
		print("zap2it-GuideScrape.py [-i <inputfile> ] [-o <outputfile>]")
		sys.exit()
	elif opt in ("-i","--ifile"):
		optConfigFile = arg
	elif opt in ("-o","--ofile"):
		optGuideFile = arg
	elif opt in ("-l","--language"):
		optLanguage = arg

print("Loading config: ", optConfigFile, " and outputting: ", optGuideFile)

#Configuration loading
Config = configparser.ConfigParser()
Config
Config.read(optConfigFile)


#Build authentication request
url = 'https://tvlistings.zap2it.com/api/user/login'
parameters = {
	'emailid': Config.get("creds","username"),
	'password': Config.get("creds","password"),
	'isfacebookuser': "false",
	'usertype': 0,
	'objectid': ''
}
data = urllib.parse.urlencode(parameters)
data = data.encode('ascii') # data should be bytes
req = urllib.request.Request(url,data)

#Load Authentication resposne from server
response = ""
response = urllib.request.urlopen(req).read()
zapVars = json.loads(response)

#Save authentication token from server
zapToken = "placeHolder"
zapToken = zapVars["token"]



#Find previous half hour from now()
currentTimestamp = time.time() - 60 * 60 * 24
halfHourOffset = currentTimestamp % (60 * 30)
closestTimestamp = currentTimestamp - halfHourOffset
closestTimestamp = int(closestTimestamp)
endTimestamp = closestTimestamp + (60*60*336)
channelXML = ""
programXML = ""
addChannels = True

while(closestTimestamp < endTimestamp):

	print("Load guide for time: " + str(closestTimestamp)  + ' - ' + str(endTimestamp))
	#build parameters for grid call
	parameters = {
		'Activity_ID': 1,
		'FromPage': "TV%20Guide",
		'AffiliateId': "gapzap",
		'token': zapToken,
		'aid': 'gapzap',
		'lineupId':'DFLTE',
		'timespan':3,
		'headendId': 'lineupId',
		'country': Config.get("prefs","country"), 
		'device': '-',
		'postalCode': Config.get("prefs","zipCode"),
		'isOverride': "true",
		'time': closestTimestamp,
		'pref': 'm,p',
		'userId': '-'
	}
	data = urllib.parse.urlencode(parameters)
	url = "https://tvlistings.zap2it.com/api/grid?" + data
	req = urllib.request.Request(url)
	response = ""
	response = urllib.request.urlopen(req).read()
	guide = json.loads(response)
	for channel in guide["channels"]:
		if addChannels == True:
			channelXML = channelXML + buildXMLChannel(channel)
		for event in channel["events"]:
			programXML = programXML + buildXMLProgram(event,channel["channelId"])
	addChannels = False
	closestTimestamp = closestTimestamp + (60*60*3)

guideXML = '<?xml version="1.0" encoding="UTF-8"?>' + "\n"
guideXML = guideXML + '<!DOCTYPE tv SYSTEM "xmltv.dtd">' + "\n"

guideXML = guideXML + '<tv source-info-url="http://tvlistings.zap2it.com/" source-info-name="zap2it.com" generator-info-name="zap2it-GuideScraping" generator-info-url="daniel@widrick.net">' + "\n"

guideXML = guideXML + channelXML
guideXML = guideXML + programXML

guideXML = guideXML + '</tv>' + "\n"

file = open(optGuideFile,"wb")
file.write(guideXML.encode('utf8'))
file.close()

#Write a Copy of the file with the current timestamp
dateTimeObj = datetime.datetime.now()
timestampStr = "." + dateTimeObj.strftime("%Y%m%d%H%M%s") + '.xmltv'
histGuideFile = timestampStr.join(optGuideFile.rsplit('.xmltv',1))
file = open(histGuideFile,"wb")
file.write(guideXML.encode('utf8'))
file.close()

#Clean old files
outputFilePath = os.path.abspath(optGuideFile)
outputDir = os.path.dirname(outputFilePath)
for item in os.listdir(outputDir):
	fileName = os.path.join(outputDir,item)
	if os.path.isfile(fileName) & item.endswith('.xmltv') & (os.stat(fileName).st_mtime < time.time() - (int(Config.get("prefs","historicalGuideDays")) * 86400)):
		os.remove(fileName)
sys.exit()
