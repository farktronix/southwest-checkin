#! /usr/bin/python

# Southwest automatic checkin tool
#
# This tool will automatically check in passengers for any number of reservations 
# as close to 24 hours in advance of the flight as possible. 
# Southwest has open seating, but orders its boarding line based on the order that
# passengers check in. Checking in first means you have a better chance of snagging
# the best seat in the plane.

# ===============
# The MIT License
#
# Copyright (c) 2008 Joe Beda
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Based on script by Ken Washington
#   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496790

# TODO: Rewrite scraping/REs using something more sane, like BeautifulSoup

import re
import sys
import time as time_module
import datetime
import sched
import string
import urllib
import urllib2
import httplib
import smtplib
import getpass
from BeautifulSoup import BeautifulSoup

from datetime import datetime,date,timedelta,time
from pytz import timezone,utc
import calendar

# If we are unable to check in, how soon should we retry?
RETRY_INTERVAL = 5

# How many minutes before the designated time should we try to check in?
CHECKIN_WINDOW = 3

# Email confuration
should_send_email = False
email_from = None
email_to = None

# SMTP server config
if False:  # local config
  smtp_server = "localhost"
  smtp_auth = False
  smtp_user = email_from
  smtp_password = ""  # if blank, we will prompt first and send test message       
  smtp_use_tls = False
else:  # gmail config
  smtp_server = "smtp.gmail.com"
  smtp_auth = True
  smtp_user = email_from
  smtp_password = ""  # if blank, we will prompt first and send test message
  smtp_use_tls = True

DEBUG_SCH = 0

# ========================================================================
# fixed page locations and parameters
# DO NOT change these parameters
main_url = 'www.southwest.com'
checkin_url = '/travel_center/retrieveCheckinDoc.html'
itinerary_url = '/travel_center/retrieveItinerary.html'
defaultboxes = ["recordLocator", "firstName", "lastName"]

# ========================================================================

# Common US time zones
tz_alaska = timezone('US/Alaska')
tz_aleutian = timezone('US/Aleutian')
tz_arizona = timezone('US/Arizona')
tz_central = timezone('US/Central')
tz_east_indiana = timezone('US/East-Indiana')
tz_eastern = timezone('US/Eastern')
tz_hawaii = timezone('US/Hawaii')
tz_indiana_starke = timezone('US/Indiana-Starke')
tz_michigan = timezone('US/Michigan')
tz_mountain = timezone('US/Mountain')
tz_pacific = timezone('US/Pacific')

airport_timezone_map = {
  'ABQ': tz_mountain,
  'ALB': tz_eastern,
  'AMA': tz_central,
  'AUS': tz_central,
  'BDL': tz_eastern,
  'BHM': tz_central,
  'BNA': tz_central,
  'BOI': tz_mountain,
  'BUF': tz_eastern,
  'BUR': tz_pacific,
  'BWI': tz_eastern,
  'CLE': tz_eastern,
  'CMH': tz_eastern,
  'CRP': tz_central,
  'DAL': tz_central,
  'DEN': tz_mountain,
  'DTW': tz_eastern,
  'ELP': tz_mountain,
  'FLL': tz_eastern,
  'GEG': tz_pacific,
  'HOU': tz_central,
  'HRL': tz_central,
  'IAD': tz_eastern,
  'IND': tz_eastern,
  'ISP': tz_eastern,
  'JAN': tz_eastern,
  'JAX': tz_eastern,
  'LAS': tz_pacific,
  'LAX': tz_pacific,
  'LBB': tz_central,
  'LIT': tz_central,
  'MAF': tz_central,
  'MCI': tz_central,
  'MCO': tz_eastern,
  'MDW': tz_central,
  'MHT': tz_eastern,
  'MSP': tz_central,
  'MSY': tz_central,
  'OAK': tz_pacific,
  'OKC': tz_central,
  'OMA': tz_central,
  'ONT': tz_pacific,
  'ORF': tz_eastern,
  'PBI': tz_eastern,
  'PDX': tz_pacific,
  'PHL': tz_eastern,
  'PHX': tz_arizona,
  'PIT': tz_eastern,
  'PVD': tz_eastern,
  'RDU': tz_eastern,
  'RNO': tz_pacific,
  'RSW': tz_eastern,
  'SAN': tz_pacific,
  'SAT': tz_central,
  'SDF': tz_eastern,
  'SEA': tz_pacific,
  'SFO': tz_pacific,
  'SJC': tz_pacific,
  'SLC': tz_mountain,
  'SMF': tz_pacific,
  'SMF': tz_pacific,
  'SNA': tz_pacific,
  'STL': tz_central,
  'TPA': tz_eastern,
  'TUL': tz_central,
  'TUS': tz_arizona,
}


# ========================================================================
# Debugging

verbose = True
def dlog(str):
  if verbose:
    print "DEBUG: %s" % str


# ========================================================================
# Classes

class Reservation(object):
  def __init__(self, first_name, last_name, confcode):
    self.first_name = first_name
    self.last_name = last_name
    self.confcode = confcode

    self.trip = None

class Trip(object):
  def __init__(self, awayFlights, returnFlights):
    self.awayFlights = awayFlights
    self.returnFlights = returnFlights

class Flight(object):
  def __init__(self):
    self.number = 0
    self.depart_airport= None
    self.depart_time = time() 

    # not currently filled in
    self.arrive_airport = None
    self.arrive_time = time()


# ========================================================================
# Utility Functions

def DateTimeToString(time):
  return time.strftime("%I:%M%p %b %d %Y %Z");

def WriteFile(filename, data):
  fd = open(filename, "w")
  fd.write(data)
  fd.close()

def ReadFile(filename):
  fd = open(filename, "r")
  data = fd.read()
  fd.close()
  return data

# this function reads a URL and returns the text of the page
def ReadUrl(host, path):
  url = "http://%s%s" % (host, path)
  dlog("GET to %s" % url)
  wdata = ""

  try:
    req = urllib2.Request(url=url)
    resp = urllib2.urlopen(req)
  except:
    print "Error: Cannot connect in GET mode to ", url
    sys.exit(1)

  wdata = resp.read()

  return wdata

# this function sends a post just like you clicked on a submit button
def PostUrl(host, path, dparams):
  wdata = ""
  url = "http://%s%s" % (host, path)
  params = urllib.urlencode(dparams, True)
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

  dlog("POST to %s" % url)
  dlog("  data: %s" % params)
  dlog("  headers: %s" % headers)

  try:
    req = urllib2.Request(url=url, data=params, headers=headers)
    resp = urllib2.urlopen(req)
  except:
    print "Error: Cannot connect in POST mode to ", url
    print "Params = ", dparams
    print sys.exc_info()[1]
    sys.exit(1)

  wdata = resp.read()

  return wdata

def flightInfoMessage(res):
  message = ""
  message += "Confirmation number: %s\r\n" % res.confcode
  message += "Passenger name: %s %s\r\n" % (res.first_name, res.last_name)

  message += "Departing Flight:\n"
  for (i, flight) in enumerate(res.trip.awayFlights):
    message += "Flight %d:\n  Departs: %s @ %s\n" \
          % (flight.number, flight.depart_airport,
             DateTimeToString(flight.depart_time))

  message += "\nReturning Flight:\n"
  for (i, flight) in enumerate(res.trip.returnFlights):
    message += "Flight %d:\n  Departs: %s @ %s\n" \
          % (flight.number, flight.depart_airport,
             DateTimeToString(flight.depart_time))
  return message

def displayFlightInfo(res):
   print flightInfoMessage(res)

# ========================================================================
# Email

def send_email(subject, message):
  if not should_send_email:
    return
  
  try:
    smtp = smtplib.SMTP(smtp_server, 587)
    smtp.ehlo()
    if smtp_use_tls:
      smtp.starttls()
      smtp.ehlo()
    if smtp_auth:
      smtp.login(smtp_user, smtp_password)
    print "sending mail"
    for to in [string.strip(s) for s in string.split(email_to, ",")]:
      smtp.sendmail(email_from, email_to, """From: %s
To: %s
Subject: %s

%s
""" % (email_from, email_to, subject, message));
    print "EMail sent successfully."
    smtp.close()
  except:
    print "Error sending email!"
    print sys.exc_info()[1]

def emailFlightInfo(res):
  if not should_send_email:
    return
  message = getFlightInfo(res)
  send_email("Waiting for SW flight", message);


# ========================================================================
# Flight itinerary parsing

def getFlightNumber(routingSoup):
  fnSep = routingSoup.findAll('td', attrs={"class" : "flightNumberSeparator "})
  return int(fnSep[0].string[1:])

def getFlightAirportCode(routingSoup):
  details = routingSoup.findAll('td', attrs={"class" : "routingDetailsStops "})
  airportCodeRegex = re.compile('.*Depart.*\((\w+)\).*')
  airportCodeMatch = airportCodeRegex.search(str(details[0]))
  if airportCodeMatch != None:
    return airportCodeMatch.group(1)
  else:
    return None

def getFlightTimeOfDayString(routingSoup):
  details = routingSoup.findAll('td', attrs={"class" : "routingDetailsTimes "})
  return str(details[0].contents[1].string)

def getFlightTravelDateString(detailSoup):
  dateTime = detailSoup.findAll('span', attrs={"class" : "travelDateTime"})
  return dateTime[0].contents[0]

def getFlightDateFromItinerary(routingSoup, detailSoup, airportCode):
  awayDateStr = getFlightTravelDateString(detailSoup)
  awayDateTime = getFlightTimeOfDayString(routingSoup)
  if awayDateStr == None or awayDateTime == None:
    return None

  return datetime(*time_module.strptime(awayDateStr + " " + awayDateTime, "%A, %B %d, %Y %I:%M %p")[0:5], tzinfo=airport_timezone_map[airportCode])

def getFlightFromItinerary(routingSoup, detailSoup):
  flight = Flight()

  flight.number = getFlightNumber(routingSoup)
  flight.depart_airport = getFlightAirportCode(routingSoup)
  date = getFlightDateFromItinerary(routingSoup, detailSoup, flight.depart_airport)
  flight.depart_time = date

  return flight

def getTripFromItinerary(itinerarySoup):
  flightDetails = itinerarySoup.findAll('td', attrs={"class" : "flightInfoDetails"})
  flightRouting = itinerarySoup.findAll('td', attrs={"class" : "flightRouting"})

  awayFlightDetails = flightDetails[0]
  returnFlightDetails = flightDetails[-1]
  awayFlightRouting = flightRouting[0]
  returnFlightRouting = flightRouting[-1]

  awayFlight = getFlightFromItinerary(awayFlightRouting, awayFlightDetails)
  returnFlight = getFlightFromItinerary(returnFlightRouting, returnFlightDetails)

  trip = Trip([awayFlight], [returnFlight])
  return trip

def getFlightItineraryURLFromData(itineraryData):
  soup = BeautifulSoup(itineraryData)
  if soup == None:
    print "Error: Could not parse data from ", main_url+itinerary_url
    return None

  itineraryForm = soup.findAll('form', id="itineraryLookup")
  if itineraryForm == None:
    print "Error: Could not find the itinerary lookup form"
    return None

  return itineraryForm[0]['action']

def getFlightItineraryURL(reservation):
  itinerarydata = ReadUrl(main_url, itinerary_url)

  if itinerarydata == None or len(itinerarydata) == 0:
    print "Error: no data returned from ", main_url+itinerary_url
    return None

  post_url = getFlightItineraryURLFromData(itinerarydata)
  if post_url == None:
    return None
  
  return (main_url, post_url, {"confirmationNumber" : reservation.confcode, "firstName" : reservation.first_name, "lastName" : reservation.last_name})

def getFlightItinerary(reservation):
  return PostUrl(*getFlightItineraryURL(reservation))

def addTripInfoToReservation(reservation):
  itinerary = getFlightItinerary(reservation) 
  if itinerary == None:
    return False 

  itinerarySoup = BeautifulSoup(itinerary)
  if itinerarySoup == None:
    print "Could not parse the itinerary data."
    return False 

  reservation.trip = getTripFromItinerary(itinerarySoup)
  if reservation.trip == None:
    return False
  return True


# ========================================================================
# Flight Checkin 

def getCheckinPostURLFromData(checkinData):
  soup = BeautifulSoup(checkinData)
  if soup == None:
    print "Error: could not parse checkin data"
    return None

  # The checkin form doesn't have an id, so we need to narrow down our search
  mainContent = soup.findAll('div', id='mainContentWrapper')
  if mainContent == None:
    print "Error: Couldn't find the main checkin content"
    return None
   
  form = mainContent[0].findAll('form')
  if form == None:
     print "Error: Couldn't find the checkin form"
     return None

  return form[0]['action']

def getCheckinPostURL(reservation):
  checkinData = ReadUrl(main_url, checkin_url)

  if checkinData == None or len(checkinData) == 0:
    print "error: no data returned from ", main_url+checkin_url
    return None

  post_url = getCheckinPostURLFromData(checkinData)
  if post_url == None:
    return None
  
  return (main_url, post_url, {"recordLocator" : reservation.confcode, "firstName" : reservation.first_name, "lastName" : reservation.last_name})

def checkinForFlight(reservation):
  return PostUrl(*getCheckinPostURL(reservation))

def getBoardingPass(reservation):
  checkinResult = checkinForFlight(reservation)

  checkinSoup = BeautifulSoup(checkinResult)
  if checkinSoup == None:
    print "Error: Could not parse response from checkin"
    return -1
 
  title = str(checkinSoup.html.head.title.contents[0].string)
  if title == "Error":
    print "Could not check in at this time"
    return -2

  # parse the returned reservations page
  rh = HTMLSouthwestParser(checkinResult)

  # Extract the name of the post function to check into the flight
  final_url = rh.formaction

  # the returned web page contains three unique security-related hidden fields
  # plus a dynamically generated value for the checkbox or radio button
  # these must be sent to the next submit post to work properly
  # they are obtained from the parser object
  params = rh.hiddentags
  if len(params) < 4:
    dlog("Error: Fewer than the expect 4 special fields returned from %s" % main_url+post_url)
    return None

  # finally, lets check in the flight and make our success file
  if DEBUG_SCH > 1:
    checkinresult = ReadFile("Southwest Airlines - Retrieve-Print Boarding Pass.htm")
  else:
    checkinresult = PostUrl(main_url, final_url, params)

  # write the returned page to a file for later inspection
  if checkinresult==None or len(checkinresult)==0:
    dlog("Error: no data returned from %s" % main_url+final_url)
    return None

  # always save the returned file for later viewing
  # TODO: don't clobber files when we have multiple flights to check in
  WriteFile("boardingpass.htm", checkinresult)

  # look for what boarding letter and number we got in the file
  group = re.search(r"boarding([ABC])\.gif", checkinresult)
  num = re.search(r"bpPassNum\"[^>]*>(\d+)", checkinresult)

  if group and num:
    return "%s%s" % (group.group(1), num.group(1))
  else:
    return None


# print some information to the terminal for confirmation purposes
def TryCheckinFlight(res, flight, sch, attempt):
  print "-="*30
  print "Trying to checkin flight at %s" % DateTimeToString(datetime.now(utc))
  print "Attempt #%s" % attempt
  #emailFlightInfo(res)
  position = getBoardingPass(res)
  if position:
    message = ""
    message += "SUCCESS.  Checked in at position %s\r\n" % position
    message += getFlightInfo(res, [flight])
    print message
    send_email("Flight checked in!", message)
  else:
    if attempt > (CHECKIN_WINDOW * 2) / RETRY_INTERVAL:
      print "FAILURE.  Too many failures, giving up."
    else:
      print "FAILURE.  Scheduling another try in %d seconds" % RETRY_INTERVAL
      sch.enterabs(time_module.time() + RETRY_INTERVAL, 1,
                   TryCheckinFlight, (res, flight, sch, attempt + 1))

def scheduleFlightCheckin(sch, res, flight):
  flight_time = utc.localize(flight.depart_time.replace(tzinfo=None))
  if flight_time < datetime.utcnow().replace(tzinfo=utc):
    print "Flight already left!"
    return
  else:
    schDelta = timedelta(days=1, minutes=CHECKIN_WINDOW)
    sched_time = flight_time - schDelta #CHECKIN_WINDOW - 24*60*60
    print "Update Sched: %s" % DateTimeToString(flight.depart_time.tzinfo.localize(sched_time.replace(tzinfo=None)))
    #sch.enterabs(calendar.timegm(sched_time.utctimetuple()), 1, TryCheckinFlight, (res, flight, sch, 1))
    sch.enterabs(time_module.time() + 1, 1, TryCheckinFlight, (res, flight, sch, 1))



# ========================================================================
# Main program
def main():

  if (len(sys.argv) - 1) % 3 != 0 or len(sys.argv) < 4:
    print "Please provide name and confirmation code:"
    print "   %s (<firstname> <lastname> <confirmation code>)+" % sys.argv[0]
    sys.exit(1)

  reservations = []

  args = sys.argv[1:]
  while len(args):
    (firstname, lastname, confcode) = args[0:3]
    reservations.append(Reservation(firstname, lastname, confcode))
    del args[0:3]

  global smtp_user, smtp_password, email_from, email_to
  
  if should_send_email:
    if not email_from:
      email_from = raw_input("Email from: ");
    if not email_to:
      email_to = raw_input("Email to: ");
    if not smtp_user:
      smtp_user = email_from
    if not smtp_password and smtp_auth:
      smtp_password = getpass.getpass("Email Password: ");

  sch = sched.scheduler(time_module.time, time_module.sleep)

  # get the departure times in a tuple
  for res in reservations:
    addTripInfoToReservation(res)

    # print some information to the terminal for confirmation purposes
    displayFlightInfo(res)

    # Schedule all of the flights for checkin.  Schedule 3 minutes before our clock
    # says we are good to go
    for flight in res.trip.awayFlights:
      scheduleFlightCheckin(sch, res, flight)
    for flight in res.trip.returnFlights:
      scheduleFlightCheckin(sch, res, flight)

    
  print "Current time: %s" % DateTimeToString(datetime.now(utc))
  print "Flights scheduled.  Waiting..."
  sch.run()

if __name__=='__main__':
  main()
