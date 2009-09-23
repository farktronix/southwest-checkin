#! /usr/bin/python

import unittest
import os
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

if __name__=='__main__':
  unittest.main()
