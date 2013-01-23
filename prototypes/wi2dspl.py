#!/usr/bin/python
# -*- coding: utf-8 -*-
__version__ = "1.0"
__authors__ = "Jose María Alvarez"
__license__ = "MIT License <http://www.opensource.org/licenses/mit-license.php>"
__contact__ = "chema.ar@gmail.com"
__date__    = "2013-01-22"

import os
import sys
import time
import re
import urllib
from string import Template
import sparql
import getopt

def createSubindexesSPARQLQuery(graph):
	q = Template('SELECT DISTINCT ?label ?comment \n FROM <$graph> WHERE{ ?index rdf:type  wi-onto:Index .\n\
			  ?index rdfs:comment ?comment . ?index rdfs:label ?label . \n}') 	
	return q.substitute(graph=graph)

def createComponentsSPARQLQuery(graph):
	q = Template('SELECT DISTINCT ?label ?comment \n FROM <$graph> WHERE{ ?component rdf:type  wi-onto:Component .\n\
   	  		?component rdfs:comment ?comment . ?component rdfs:label ?label . \n}') 		
	return q.substitute(graph=graph)

def createIndicatorsSPARQLQuery(graph, primary=True):
	typeIndicator = "wi-onto:PrimaryIndicator" if primary else "wi-onto:SecondaryIndicator" 
	q = Template('SELECT DISTINCT  ?label  ?comment \n FROM <$graph> WHERE{ ?indicator rdf:type ?typeIndicator.\n\
			  ?indicator rdfs:label ?label. \n\
			  ?indicator rdfs:comment ?comment. \n\
			  FILTER(?typeIndicator=$typeIndicator).  \n}') 	
	return q.substitute(graph=graph, typeIndicator=typeIndicator)

def createCountriesSPARQLQuery(graph):
	q = Template('SELECT ?countryLabel ?id ?lat ?long \n FROM <$graph> WHERE { ?country rdf:type wi-onto:Country.\n\
			  ?country rdfs:label ?countryLabel. \n\
			   FILTER (lang(?countryLabel) = \'en\') . \n\
  		          ?country wi-onto:has-iso-alpha3-code ?id. \n\
			  ?country geo:lat ?lat. \n\
			  ?country geo:long ?long. \n}') 	
	return q.substitute(graph=graph)

def createRestrictedCountriesSPARQLQuery(graph):
	q = Template('SELECT DISTINCT ?countryLabel ?id ?lat ?long \n FROM <$graph> WHERE { ?obs wi-onto:ref-indicator ?indicator. \n\
			  ?obs wi-onto:ref-indicator ?indicator. \n\
			  ?indicator rdf:type wi-onto:PrimaryIndicator. \n\
 			  ?obs wi-onto:ref-area ?country. \n\
			  ?country rdfs:label ?countryLabel. \n\
			  FILTER (lang(?countryLabel) = \'en\') . \n\
  		          ?country wi-onto:has-iso-alpha3-code ?id. \n\
			  ?country geo:lat ?lat. \n\
			  ?country geo:long ?long. \n}') 	
	return q.substitute(graph=graph)

def rowToList(result):
	resultList = []
	for row in result:
		values = sparql.unpack_row(row)
		resultList.append(values)
	return resultList

def listSubindexes(endpoint, graph):
	query = createSubindexesSPARQLQuery(graph)
	result = sparql.query(endpoint, query)
	return rowToList(result)

def listComponents(endpoint, graph):
	query = createComponentsSPARQLQuery(graph)
	result = sparql.query(endpoint, query)
	return rowToList(result)

def listIndicators(endpoint, graph,primary=True):
	query = createIndicatorsSPARQLQuery(graph, primary)
	result = sparql.query(endpoint, query)
	return rowToList(result)

def listCountries(endpoint, graph):
#	query = createCountriesSPARQLQuery(graph) #Full list of countries but wi is only available for 61 countries
	query = createRestrictedCountriesSPARQLQuery(graph)
	result = sparql.query(endpoint, query)
	return rowToList(result)

def listSecondaryYears():
	return [2007, 2008, 2009, 2010, 2011]

def listPrimaryYears():
	return [2011]


def listObservations(endpoint, graph, countries, indicators, datasets, years):
	allObservations = []
	q = Template('SELECT ?value ?indicatorLabel ?idcountry ?year  \n FROM <$graph> WHERE{ ?obs rdf:type qb:Observation.\n\
			  ?obs wi-onto:ref-indicator ?indicator. \n\
			  FILTER(?indicator = wi-indicator:$indicator). \n\
			  ?indicator rdfs:label ?indicatorLabel. \n\
			  ?obs qb:dataSet ?dataset. \n\
			  FILTER(?dataset = wi-dataset:$indicator-$dataset). \n\
			  ?obs wi-onto:ref-area ?country. \n\
			  FILTER(?country = wi-country:$country). \n\
			  ?country wi-onto:has-iso-alpha3-code ?idcountry. \n\
			  ?obs wi-onto:ref-year ?year. \n\
			  FILTER(?year = $year). \n\
			  ?obs sdmx-concept:obsStatus ?status. \n\
			  ?obs wi-onto:value ?value.  \n}') 	

	for country in countries:       
		for indicator in indicators:
		        for dataset in datasets:
				for year in years:
					query = q.substitute(graph=graph, indicator=indicator[0], dataset=dataset, year=year, country=country[1])
					print "Selecting ", indicator[0], year, country[1]
					result = sparql.query(endpoint, query)
					allObservations.append(rowToList(result))
	return allObservations

def run(template, endpoint, graph, outputdir):
 	#List subindexes (uri, label)
	subindexes = listSubindexes(endpoint, graph)
	#List components (uri, label)
	components = listComponents(endpoint, graph)
	#List indicators (uri, label)
	primaryIndicators = listIndicators(endpoint, graph)
	secondaryIndicators = listIndicators(endpoint, graph, False)
	#List countries ?countryLabel ?id ?lat ?long 
	countries = listCountries(endpoint, graph)
	#Slice [(indicator, component, subindex), dataset=dataset, year=year, country=country]
	datasets = ['Normalised']
	#For testing select just one country, indicator and year, [0:1] when list parameter is passed to function
  	observations = listObservations(endpoint, graph, countries, primaryIndicators, datasets, listPrimaryYears())
	saveObservations(outputdir,observations,"observations")	
	observations = listObservations(endpoint, graph, countries, secondaryIndicators, datasets, listSecondaryYears())
	saveObservations(outputdir,observations,"secondary-observations")
	saveCountries(outputdir, countries)	
	saveMeta(outputdir, primaryIndicators,"indicator")
	saveMeta(outputdir, secondaryIndicators,"secondary-indicators")
	saveMeta(outputdir, components,"components")
#TODO: save component values
	saveMeta(outputdir, subindexes,"subindexes")
#TODO: save index values
	save(outputdir+"/"+"dataset.xml",template)
	zipDir(outputdir,"outputdir.zip")
#	try:
#		template = unicode(template)
#	except UnicodeDecodeError, e:
#		template = unicode(template.decode('utf-8'))
#	try:
#        	template = template % (unicode("hola"), unicode("adis"))
#        	template += "<!-- specification regenerated by SpecGen5 at %s -->" % time.strftime('%X %x %Z')
#	except TypeError, e:
#        	print "Error filling the template! Please, be sure you respected both '%s' on your template" % "%s"
#    
	return template

def saveObservations(outputdir, observations,name):
	text = "value,indicator,code,year\n"
	for obs in observations:
		for i in obs:
			text = text + ",".join([str(k) for k in i]) +"\n"
	save(outputdir+"/"+name+".csv",text)

def saveCountries(outputdir, countries):
	text = "label,code,lat,long\n"
	for country in countries:
		text = text + ",".join(country) +"\n"
	save(outputdir+"/countries.csv",text)

def saveMeta(outputdir, elements,name):
	text = "label,comment\n"
	for element in elements:
		text = text + ",".join(element) +"\n"
	save(outputdir+"/"+name+".csv",text)

def save(path, text):
    try:
        f = open(path, "w")
        f.write(text.encode("utf-8"))
        f.flush()
        f.close()
    except Exception, e:
        print "Error writting in file %s: %s" % (path, e)

def zipDir(path, zip):
    subprocess.Popen('7z a -tzip %s %s'%(path, zip))

#Based on: https://bitbucket.org/wikier/specgen/src/35aba3595cd83f31382a34db65717237d8cfadd0/specgen.py?at=default
def __getScriptPath():
    path = sys.argv[0]
    if path.startswith("./"):
        return path
    else:
        base = "/".join(path.split("/")[:-1])
        for one in os.environ["PATH"].split(":"):
            if base == one:
                return path.split("/")[-1]
        return path

def usage():
    script = __getScriptPath()
    print """Usage: 
    %s template endpoint output-dir

        template    : DSPL template
        endpoint : SPARQL URL endpoint
	graph: URI of the named graph containing statistics
	output-dir: Dir to write generated files

examples:
    %s template.xml http://data.webfoundation.org/sparql http://data.webfoundation.org/webindex/ wi

""" % (script, script)
    sys.exit(-1)

if __name__ == "__main__":
    """Webindex DSPL generator tool"""
    
    args = sys.argv[1:]
    if (len(args) < 4):
        usage()
    else:
        
        #template
        temploc = args[0]
        template = None
        try:
            f = open(temploc, "r")
            template = f.read()
        except Exception, e:
            print "Error reading from template \"" + temploc + "\": " + str(e)
            usage()

        #SPARQL endpoint
        endpoint = args[1]

	#Named graph
        graph = args[2]

 	#Output dir
	outputdir = args[3]
        
	run(template, endpoint, graph, outputdir)


