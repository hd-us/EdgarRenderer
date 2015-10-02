''' 
Inline XBRL Document Set (formerly a) plug-in.

Supports opening manifest file that identifies inline documents of a document set.

Saves extracted instance document.

(Does not currently support multiple target instance documents in a document set.)

(c) Copyright 2013 Mark V Systems Limited, All rights reserved.
'''
from arelle import ModelXbrl, ValidateXbrlDimensions, XmlUtil, XbrlConst
from arelle.PrototypeDtsObject import LocPrototype
from arelle.ModelDocument import ModelDocument, ModelDocumentReference, Type, load
from arelle.ValidateFilingText import CDATApattern, copyHtml
import os, zipfile
from optparse import SUPPRESS_HELP
from lxml.etree import XML, XMLSyntaxError

MANIFEST_NAMESPACE = "http://disclosure.edinet-fsa.go.jp/2013/manifest"
DEFAULT_INSTANCE_EXT = ".xml"  # the extension on the instance to be saved
DEFAULT_DISTINGUISHING_SUFFIX = "_htm."  # suffix tacked onto the base name of the source inline document
USUAL_INSTANCE_EXTS = {"xml", "xbrl"}

class ModelInlineXbrlDocumentSet(ModelDocument):
    
    def discoverInlineXbrlDocumentSet(self):
        instanceTag = "{" + self.manifestNamespace + "}instance"
        preferredFilenameAtt = 'preferredFilename'
        ixbrlTag = "{" + MANIFEST_NAMESPACE + "}ixbrl"
        for instanceElt in self.xmlRootElement.iter(tag=instanceTag):
            targetId = instanceElt.id
            self.targetDocumentId = targetId
            self.targetDocumentPreferredFilename = instanceElt.get(preferredFilenameAtt)
            self.targetDocumentSchemaRefs = set()  # union all the instance schemaRefs
            for ixbrlElt in instanceElt.iter(tag=ixbrlTag):
                uri = ixbrlElt.textValue.strip()
                if uri:
                    doc = load(self.modelXbrl, uri, base=self.filepath, referringElement=instanceElt)
                    if doc is not None and doc not in self.referencesDocument:
                        referencedDocument = ModelDocumentReference("inlineDocument", instanceElt)
                        referencedDocument.targetId = targetId
                        self.referencesDocument[doc] = referencedDocument
                        for referencedDoc in doc.referencesDocument.keys():
                            if referencedDoc.type == Type.SCHEMA:
                                self.targetDocumentSchemaRefs.add(doc.relativeUri(referencedDoc.uri))
        return True
    
def identifyInlineXbrlDocumentSet(modelXbrl, rootNode, filepath):
    for manifestElt in rootNode.iter(tag="{" + MANIFEST_NAMESPACE + "}manifest"):
        return (Type.INLINEXBRLDOCUMENTSET, ModelInlineXbrlDocumentSet, manifestElt)
    return None  # not a document set


def discoverInlineXbrlDocumentSet(modelDocument):
    if isinstance(modelDocument, ModelInlineXbrlDocumentSet):
        return modelDocument.discoverInlineXbrlDocumentSet()        
    return False  # not discoverable

def saveTargetDocumentIfNeeded(cntlr, options, modelXbrl, suffix="_htm.", iext=".xml"):   
    if (modelXbrl is None): return
    if not (isinstance(modelXbrl.modelDocument, ModelInlineXbrlDocumentSet) or
            modelXbrl.modelDocument.type == Type.INLINEXBRL):
        cntlr.logTrace(_("No Inline XBRL document or manifest."))
        return
    if not (options.saveTargetFiling or options.saveTargetInstance): return
    modelDocument = modelXbrl.modelDocument
    if isinstance(modelDocument, ModelInlineXbrlDocumentSet):
        targetInstanceName = modelDocument.targetDocumentPreferredFilename
        targetSchemaRefs = modelDocument.targetDocumentSchemaRefs
    else:
        filebase, fileext = os.path.splitext(os.path.basename(modelDocument.filepath))
        if fileext not in USUAL_INSTANCE_EXTS: fileext = iext
        targetInstanceName = filebase + fileext
        targetSchemaRefs = set(modelDocument.relativeUri(referencedDoc.uri)
                               for referencedDoc in modelDocument.referencesDocument.keys()
                               if referencedDoc.type == Type.SCHEMA)  
    base = os.path.splitext(os.path.basename(targetInstanceName))[0]
    
    filingFiles = set()
    def addRefDocs(doc):
        for refDoc in doc.referencesDocument.keys():
            if refDoc.uri not in filingFiles:
                filingFiles.add(refDoc.uri)
                addRefDocs(refDoc)
    addRefDocs(modelDocument)
    
    targetInstance = buildTargetInstance(modelXbrl, targetInstanceName, targetSchemaRefs
                        , filingFiles=filingFiles, suffix=suffix)
       
    # Save as standalone instance
    if options.saveTargetInstance:
        saveTargetPath = os.path.join(cntlr.reportsFolder, base + suffix + 'xml')
        targetInstance.saveInstance(overrideFilepath=saveTargetPath)
        cntlr.logDebug('Saved {}'.format(os.path.basename(saveTargetPath)))
    # Save as zip with all locally referenced files.
    if options.saveTargetFiling:
        saveTargetPath = os.path.join(cntlr.reportsFolder, base + suffix + 'zip')
        filingZip = zipfile.ZipFile(saveTargetPath, mode='w', compression=zipfile.ZIP_DEFLATED, allowZip64=False)
        instDir = os.path.dirname(modelDocument.filepath)
        targetInstance.saveInstance(outputZip=filingZip)
        for refFile in filingFiles:
            if refFile.startswith(instDir):
                filingZip.write(refFile, modelDocument.relativeUri(refFile))
        cntlr.logDebug('Saved {}'.format(os.path.basename(saveTargetPath)))
        
    modelXbrl.modelManager.showStatus(_("Saved extracted instance"), clearAfter=5000)
                
     
def buildTargetInstance(modelXbrl, targetDocumentFilename, targetDocumentSchemaRefs
                       , filingFiles=None
                       , suffix=DEFAULT_DISTINGUISHING_SUFFIX):
    sourceDir = os.path.dirname(modelXbrl.modelDocument.filepath)
    def addLocallyReferencedFile(elt,filingFileSet):
        if elt.tag in ("a", "img"):
            for attrTag, attrValue in elt.items():
                if attrTag in ("href", "src"):
                    file = os.path.join(sourceDir,attrValue)
                    if os.path.exists(file):
                        filingFiles.add(os.path.join(sourceDir,attrValue))
                    
    targetUrl = modelXbrl.modelManager.cntlr.webCache.normalizeUrl(targetDocumentFilename, modelXbrl.modelDocument.filepath)
    targetUrlParts = targetUrl.rpartition(".")
    targetUrl = targetUrlParts[0] + suffix + targetUrlParts[2]
    modelXbrl.modelManager.showStatus(_("Extracting instance ") + os.path.basename(targetUrl))
    targetInstance = ModelXbrl.create(modelXbrl.modelManager,
                                      newDocumentType=Type.INSTANCE,
                                      url=targetUrl,
                                      schemaRefs=targetDocumentSchemaRefs,
                                      isEntry=True)
    ValidateXbrlDimensions.loadDimensionDefaults(targetInstance)  # need dimension defaults - why?
    # roleRef and arcroleRef (of each inline document)
    for sourceRefs in (modelXbrl.targetRoleRefs, modelXbrl.targetArcroleRefs):
        for roleRefElt in sourceRefs.values():
            XmlUtil.addChild(targetInstance.modelDocument.xmlRootElement, roleRefElt.qname,
                             attributes=roleRefElt.items())
    
    # contexts
    for context in modelXbrl.contexts.values():
        ignore = targetInstance.createContext(context.entityIdentifier[0],
                                               context.entityIdentifier[1],
                                               'instant' if context.isInstantPeriod else
                                               'duration' if context.isStartEndPeriod
                                               else 'forever',
                                               context.startDatetime,
                                               context.endDatetime,
                                               None,
                                               context.qnameDims, [], [],
                                               id=context.id)
    for unit in modelXbrl.units.values():
        measures = unit.measures
        ignore = targetInstance.createUnit(measures[0], measures[1], id=unit.id)

    modelXbrl.modelManager.showStatus(_("Creating and validating facts"))
    newFactForOldObjId = {}
    def createFacts(facts, parent):
        for fact in facts:
            if fact.isItem and not fact in modelXbrl.duplicateFactSet:
                attrs = {"contextRef": fact.contextID}
                if fact.id:
                    attrs["id"] = fact.id
                if fact.isNumeric:
                    attrs["unitRef"] = fact.unitID
                    if fact.get("decimals"):
                        attrs["decimals"] = fact.get("decimals")
                    if fact.get("precision"):
                        attrs["precision"] = fact.get("precision")
                if fact.isNil:
                    attrs[XbrlConst.qnXsiNil] = "true"
                    text = None
                else:
                    text = fact.xValue if fact.xValid else fact.textValue
                newFact = targetInstance.createFact(fact.qname, attributes=attrs, text=text, parent=parent)
                newFactForOldObjId[fact.objectIndex] = newFact
                if filingFiles is not None and fact.concept is not None and fact.concept.isTextBlock:
                    # check for img and other filing references so that referenced files are included in the zip.
                    for xmltext in [text] + CDATApattern.findall(text):
                        try:
                            for elt in XML("<body>\n{0}\n</body>\n".format(xmltext)).iter():
                                addLocallyReferencedFile(elt, filingFiles)
                        except (XMLSyntaxError, UnicodeDecodeError):
                            pass  # TODO: Why ignore UnicodeDecodeError?
            elif fact.isTuple:
                newTuple = targetInstance.createFact(fact.qname, parent=parent)
                newFactForOldObjId[fact.objectIndex] = newTuple
                createFacts(fact.modelTupleFacts, newTuple)
                
    createFacts(modelXbrl.facts, None)
    modelXbrl.modelManager.showStatus(_("Creating and validating footnotes and relationships"))
    HREF = "{http://www.w3.org/1999/xlink}href"
    for linkKey, linkPrototypes in modelXbrl.baseSets.items():
        ignore, linkrole, linkqname, arcqname = linkKey
        if (linkrole and linkqname and arcqname and  # fully specified roles
            any(lP.modelDocument.type == Type.INLINEXBRL for lP in linkPrototypes)):
            for linkPrototype in linkPrototypes:
                newLink = XmlUtil.addChild(targetInstance.modelDocument.xmlRootElement, linkqname,
                                           attributes=linkPrototype.attributes)
                for linkChild in linkPrototype:
                    if isinstance(linkChild, LocPrototype) and HREF not in linkChild.attributes:
                        linkChild.attributes[HREF] = \
                        "#" + XmlUtil.elementFragmentIdentifier(newFactForOldObjId[linkChild.dereference().objectIndex])
                    XmlUtil.addChild(newLink, linkChild.qname,
                                     attributes=linkChild.attributes,
                                     text=linkChild.textValue)
                    if filingFiles is not None and linkChild.textValue:
                        footnoteHtml = XML("<body/>")
                        copyHtml(linkChild, footnoteHtml)
                        for elt in footnoteHtml.iter():
                            addLocallyReferencedFile(elt,filingFiles)
    return targetInstance    

def saveTargetDocumentCommandLineOptionExtender(parser):
    # extend command line options with a save DTS option
    parser.add_option("--saveTargetInstance",
                      action="store_true", dest="saveTargetInstance", help=_("Save target instance document"))
    parser.add_option("--saveTargetInstance".casefold(),  # lower case for WEB SERVICE use
                      action="store_true", dest="saveTargetInstance", help=SUPPRESS_HELP)
    parser.add_option("--saveTargetFiling",
                      action="store_true", dest="saveTargetFiling", help=_("Save instance and DTS in zip"))
    parser.add_option("--saveTargetFiling".casefold(),  # lower case for WEB SERVICE use
                      action="store_true", dest="saveTargetFiling", help=SUPPRESS_HELP)

