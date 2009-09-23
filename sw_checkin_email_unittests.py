#! /usr/bin/python

import unittest
import os
import datetime
from pytz import timezone
from BeautifulSoup import BeautifulSoup

import sw_checkin_email as sw

class ItineraryParserUnitTest(unittest.TestCase):
    def setUp(self):
        itineraryPath = os.getcwd() + "/itinerary.html"
        self.itineraryData = sw.ReadFile(itineraryPath)
        assert self.itineraryData != None, "Could not load itinerary data from %s" % itineraryPath

        self.soup = BeautifulSoup(self.itineraryData)
        assert self.soup != None, "Couldn't create a soup from the Itinerary data"

        self.flightDetails = self.soup.findAll('td', attrs={"class" : "flightInfoDetails"})
        assert self.flightDetails != None, "Could not get flight details from the itinerary page"
        assert len(self.flightDetails) == 2, "Expected two flight details, got %d" % len(self.flightDetails)
        self.flightRouting = self.soup.findAll('td', attrs={"class" : "flightRouting"})
        assert self.flightDetails != None, "Could not get flight routing from the itinerary page"
        assert len(self.flightRouting) == 2, "Expected two flight routings, got %d" % len(self.flightDetails)

        self.awayFlightDetails = self.flightDetails[0]
        assert self.awayFlightDetails != None, "Could not get away flight details"
        self.returnFlightDetails = self.flightDetails[-1]
        assert self.returnFlightDetails != None, "Could not get return flight details"
        self.awayFlightRouting = self.flightRouting[0]
        assert self.awayFlightRouting != None, "Could not get away flight routing"
        self.returnFlightRouting = self.flightRouting[-1]
        assert self.returnFlightRouting != None, "Could not get return flight routing"

    def testGetFlightNumberFromItinerary(self):
        flightNumber = sw.getFlightNumber(self.awayFlightRouting)
        assert flightNumber == 1476, "Incorrect flight number returned for away flight. Expected 1476, but got %s" % flightNumber

        flightNumber = sw.getFlightNumber(self.returnFlightRouting)
        assert flightNumber == 34, "Incorrect flight number returned for return flight. Expected 34, but got %s" % flightNumber

    def testGetFlightAirportCodesFromItinerary(self):
        airportCode = sw.getFlightAirportCode(self.awayFlightRouting)
        assert airportCode == "SJC", "Incorrect airport code for away flight. Expected \"SJC\" but got \"%s\"" % airportCode 

        airportCode = sw.getFlightAirportCode(self.returnFlightRouting)
        assert airportCode == "TUL", "Incorrect airport code for return flight. Expected \"TUL\" but got \"%s\"" % airportCode 

    def testGetFlightTimeOfDayStringFromItinerary(self):
        timeOfDayString = sw.getFlightTimeOfDayString(self.awayFlightRouting)
        assert timeOfDayString == "11:15 AM", "Incorrect time of day for away flight. Expected \"11:15 AM\" but got \"%s\"" % timeOfDayString

        timeOfDayString = sw.getFlightTimeOfDayString(self.returnFlightRouting)
        assert timeOfDayString == "5:45 PM", "Incorrect time of day for return flight. Expected \"5:45 PM\" but got \"%s\"" % timeOfDayString

    def testGetFlightTravelDateStringFromItinerary(self):
        travelDateString = sw.getFlightTravelDateString(self.awayFlightDetails)
        expectedDateString = "Thursday, October 22, 2009"
        assert travelDateString == expectedDateString, "Incorrect date string for away flight. Expected \"%s\" but got \"%s\"" % (expectedDateString, travelDateString)

        travelDateString = sw.getFlightTravelDateString(self.returnFlightDetails)
        expectedDateString = "Sunday, October 25, 2009"
        assert travelDateString == expectedDateString, "Incorrect date string for return flight. Expected \"%s\" but got \"%s\"" % (expectedDateString, travelDateString)

    def testGetTripFromItinerary(self):
        trip = sw.getTripFromItinerary(self.soup)
        assert trip != None, "Could not get a trip from the itinerary soup"
        assert len(trip.awayFlights) > 0, "Expected at least one away flight, but got %d" % len(trip.awayFlights)
        assert len(trip.returnFlights) > 0, "Expected at least one return flight, but got %d" % len(trip.returnFlights)

        awayFlight = trip.awayFlights[0]
        returnFlight = trip.returnFlights[0]

        assert awayFlight != None, "Away flight is empty"
        assert returnFlight != None, "Return flight is empty"

        assert awayFlight.depart_airport == "SJC", "Incorrect airport code for away flight. Expected \"SJC\", but got \"%s\"" % awayFlight.depart_airport
        departTime = datetime.datetime(2009, 10, 22, 11, 15, tzinfo=timezone('US/Pacific'))
        assert awayFlight.depart_time == departTime, "Incorrect departure time for away flight" 

        assert returnFlight.depart_airport == "TUL", "Incorrect airport code for away flight. Expected \"TUL\", but got \"%s\"" % returnFlight.depart_airport
        departTime = datetime.datetime(2009, 10, 25, 17, 45, tzinfo=timezone('US/Central'))
        assert returnFlight.depart_time == departTime, "Incorrect departure time for return flight" 

class RetrieveItineraryParserUnitTest(unittest.TestCase):
    def runTest(self):
        reservationPath = os.getcwd() + "/retrieveItinerary.html"
        reservationData = sw.ReadFile(reservationPath)
        assert reservationData != None, "Could not load reservation data from %s" % reservationPath
        
        postURL = sw.getFlightItineraryURLFromData(reservationData)
        assert postURL == "/flight/retrieve-air-reservation.html;jsessionid=0B37A0DF7A4102773B328E46B50715BE", "The post URL is not what was expected: %s" % postURL

class RetrieveCheckinURLUnitTest(unittest.TestCase):
    def runTest(self):
        checkinPath = os.getcwd() + "/checkin.html"
        checkinData = sw.ReadFile(checkinPath)
        assert checkinData != None, "Could not load checkin data from %s" % checkinPath 
    
        postURL = sw.getCheckinPostURLFromData(checkinData)
        assert postURL == "/cgi-bin/selectBoardingPass", "The post URL is not what was expected: %s" % postURL

if __name__=='__main__':
  unittest.main()
