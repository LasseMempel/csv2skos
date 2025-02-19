import pandas as pd
import datetime
import math
import os
from rdflib import Graph, URIRef, BNode, Literal, Namespace, XSD
from rdflib.namespace import SKOS, RDF, DC, PROV, DCTERMS, RDFS

# global column names, properties and datatypes of scheme
schemePropertyDict = {"title": (DC.title, Literal, True),
                        "description": (SKOS.definition, Literal, True),
                        "creator": (DC.creator, Literal, False),
                        "publisher": (DCTERMS.publisher, Literal, False),
                        "license": (DCTERMS.license, Literal, False),
                        "rights": (DCTERMS.rights, Literal, False),
                        "contributor": (DCTERMS.contributor, Literal, False),
                        "subject": (DCTERMS.subject, Literal, True),
                        }

# global column names, properties and datatypes of concepts
conceptPropertyDict = {"notation": (SKOS.notation, Literal, False),
                        "prefLabel": (SKOS.prefLabel, Literal, True),
                        "altLabel": (SKOS.altLabel, Literal, True),
                        "definition": (SKOS.definition, Literal, True),
                        "broader": (SKOS.broader, URIRef, False),
                        "narrower": (SKOS.narrower, URIRef, False),
                        "related": (SKOS.related, URIRef, False),
                        "closeMatch": (SKOS.closeMatch, URIRef, False),
                        "relatedMatch": (SKOS.relatedMatch, URIRef, False),
                        "exactMatch": (SKOS.exactMatch, URIRef, False),
                        "source": (DC.source, Literal, False),
                        "creator": (DC.creator, Literal, False),
                        "seeAlso": (RDFS.seeAlso, Literal, False)
                        }

def buildTriples(g, df, subject, propertyDict, conceptScheme, conceptPrefix, seperator, baseLanguage):
    # iterate over all rows in df
    for index, row in df.iterrows():
        rowDict = {key:value for key, value in row.items()}

        if subject == "scheme":
            subject = conceptScheme
        else:
            subject = URIRef(conceptPrefix + rowDict["notation"])
            g.add((subject, RDF.type, SKOS.Concept))
            g.add((subject, SKOS.inScheme, conceptScheme))

        for key in propertyDict:
            if key in rowDict:
                value = rowDict[key]

                if isinstance(value, float) and math.isnan(value):
                    if key == "broader":
                        g.add((conceptScheme, SKOS.hasTopConcept, subject))
                        g.add((subject, SKOS.topConceptOf, conceptScheme))
                    continue

                values = value.split(seperator)
                property, datatype, isLangString = propertyDict[key]
                langDict = {}
                for object in values:
                    if property in [SKOS.broader, SKOS.narrower, SKOS.related]:
                        object = conceptPrefix + object

                    if isLangString:
                        if len(object.split("@")) > 1:
                            object, language = object.split("@")
                        else:
                            object, language = object, baseLanguage
                        if language not in langDict:
                            langDict[language] = 0
                        else:
                            langDict[language] += 1
                        if langDict[language] > 0 and property == SKOS.prefLabel:
                            print(f"Multiple prefLabels for language @{language} at concept {subject}. Switching to altLabel.")
                            g.add((subject, SKOS.altLabel, Literal(object, lang=language)))
                        else:    
                            g.add((subject, property, Literal(object, lang=language)))

                    else:
                        g.add((subject, property, datatype(object)))
                    if property == SKOS.broader and "narrower" not in rowDict:
                        g.add((URIRef(object), SKOS.narrower, subject))
                    if property == SKOS.narrower and "broader" not in rowDict:
                            g.add((URIRef(object), SKOS.broader, subject))
                            
    return g

def main(conceptCsvPath, schemeCsvPath, scriptRepositoryPath, seperator, baseLanguage, baseUri):

    # initialization of graph and provenance entities
    g = Graph()
    thesaurusCreation = BNode()
    g.add((thesaurusCreation, RDF.type, PROV.Activity))
    g.add((thesaurusCreation, PROV.startedAtTime, Literal(datetime.datetime.now(), datatype=XSD.dateTime)))
    pythonScript = URIRef(scriptRepositoryPath)
    g.add((pythonScript, RDF.type, PROV.SoftwareAgent))
    g.add((thesaurusCreation, PROV.wasAssociatedWith, pythonScript))

    # generate dataframes from csv paths   
    conceptsDf = pd.read_csv(conceptCsvPath)
    schemeDf = pd.read_csv(schemeCsvPath)

    # create concept scheme and connect to provenance
    conceptScheme = URIRef(baseUri)
    g.add((conceptScheme, RDF.type, SKOS.ConceptScheme))
    g.add((conceptScheme, RDF.type, PROV.Entity))
    g.add((conceptScheme, PROV.wasGeneratedBy, thesaurusCreation))
    g.add((conceptScheme, PROV.wasAttributedTo, pythonScript))

    conceptPrefix = baseUri + "/"

    # enrich concept scheme with metadata
    g = buildTriples(g, schemeDf, "scheme", schemePropertyDict, conceptScheme, conceptPrefix, seperator, baseLanguage)

    # create concepts and connect them to concept scheme
    g = buildTriples(g, conceptsDf, "concept", conceptPropertyDict, conceptScheme, conceptPrefix, seperator, baseLanguage)

    # add end time for thesaurus creation activity
    g.add((thesaurusCreation, PROV.endedAtTime, Literal(datetime.datetime.now(), datatype=XSD.dateTime)))

    # save graph to file
    g.serialize(destination="thesaurus.ttl",format="turtle")

# paths to csv files
conceptCsvPath = "concepts.csv"
schemeCsvPath = "scheme.csv"

# repository url of this script
scriptRepositoryPath = "https://github.com/LasseMempel/csv2skos/blob/master/csv2skos.py"

# seperator character for multivalue cells in csv
seperator = "|"

# fallback language if no language is given in value
baseLanguage = "de"

# base uri of the thesaurus and the concepts
baseUri = "https://www.example.com/terminologies/sausagethesaurus"

main(conceptCsvPath, schemeCsvPath, scriptRepositoryPath, seperator, baseLanguage, baseUri)