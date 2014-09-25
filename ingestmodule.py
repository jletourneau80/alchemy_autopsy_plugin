import jarray
from java.lang import System
from java.lang import Byte
from java.io import BufferedInputStream
from org.sleuthkit.datamodel import SleuthkitCase
from org.sleuthkit.datamodel import AbstractFile
from org.sleuthkit.datamodel import ReadContentInputStream
from org.sleuthkit.datamodel import BlackboardArtifact
from org.sleuthkit.datamodel import BlackboardAttribute
from org.sleuthkit.autopsy.ingest import IngestModule
from org.sleuthkit.autopsy.ingest import DataSourceIngestModule
from org.sleuthkit.autopsy.ingest import FileIngestModule
from org.sleuthkit.autopsy.ingest import IngestModuleFactoryAdapter
from org.sleuthkit.autopsy.ingest import IngestMessage
from org.sleuthkit.autopsy.ingest import IngestServices
from org.sleuthkit.autopsy.casemodule import Case
from org.sleuthkit.autopsy.casemodule.services import Services
from org.sleuthkit.autopsy.casemodule.services import FileManager
from alchemyapi_python.alchemyapi import AlchemyAPI
import json

class SampleJythonDataSourceIngestModule(DataSourceIngestModule):

    def __init__(self):
        self.context = None

    def startUp(self, context):
        self.context = context

    def process(self, dataSource, progressBar):
        if self.context.isJobCancelled():
            return IngestModule.ProcessResult.OK

        # There are two tasks to do.
        progressBar.switchToDeterminate(2)

        autopsyCase = Case.getCurrentCase()
        sleuthkitCase = autopsyCase.getSleuthkitCase()
        services = Services(sleuthkitCase)
        fileManager = services.getFileManager()

        #Get count of files with .doc extension.
        fileCount = 0;
        docFiles = fileManager.findFiles(dataSource, "%.doc")
        for docFile in docFiles:
            fileCount += 1
        progressBar.progress(1)

        if self.context.isJobCancelled():
            return IngestModule.ProcessResult.OK

        # Get files by creation time.
        currentTime = System.currentTimeMillis() / 1000
        minTime = currentTime - (14 * 24 * 60 * 60) # Go back two weeks.
        otherFiles = sleuthkitCase.findFilesWhere("crtime > %d" % minTime)
        for otherFile in otherFiles:
            fileCount += 1
        progressBar.progress(1);

        if self.context.isJobCancelled():
            return IngestModule.ProcessResult.OK;

        #Post a message to the ingest messages in box.
        message = IngestMessage.createMessage(IngestMessage.MessageType.DATA, "Sample Jython Data Source Ingest Module", "Found %d files" % fileCount)
        IngestServices.getInstance().postMessage(message)

        return IngestModule.ProcessResult.OK;

        
class SampleJythonFileIngestModule(FileIngestModule):

    def startUp(self, context):
        pass

    def getByteArray(self,fileUrl):
          inS = ReadContentInputStream(fileUrl);
          inputStream = BufferedInputStream(inS);
          length = fileUrl.getSize()
          print("File length:" + str(length))
          bytes = jarray.zeros(length, 'b')
          #Read in the bytes
          offset = 0
          numRead = 0
          while offset<length:
              if numRead>= 0:
                  
                  numRead=inputStream.read(bytes, offset, length-offset)
                  offset = offset + numRead
                  print ("Bytes read:" + str(numRead))
          return bytes

    def process(self, file):
        if file.getName().endswith(".jpg"):
            alchemyapi = AlchemyAPI()
            tagsManager = Case.getCurrentCase().getServices().getTagsManager()
            data = self.getByteArray(file)
            response = alchemyapi.imageTagging('image',  data)

            if response['status'] == 'OK':
                print('## Response Object ##')
                print(json.dumps(response, indent=4))

                print('')
                print('## Keywords ##')
                for keyword in response['imageKeywords']:
                    print(keyword['text'], ' : ', keyword['score'])
                     
                    tags = tagsManager.getAllTagNames();
                    theTagName = None
                    for t in tags:
                        if t.getDisplayName()==keyword['text']:
                            theTagName = t
                    
                    if theTagName == None:
                        theTagName=tagsManager.addTagName(keyword['text'])
                    
                    tagsManager.addContentTag(file, theTagName);
                    
                print('')
            else:
                print('Error in image tagging call: ', response['statusInfo'])
            
    # If the file has a txt extension, post an artifact to the blackboard.
        return IngestModule.ProcessResult.OK

    def shutDown(self):
        pass

class SampleJythonIngestModuleFactory(IngestModuleFactoryAdapter):

    def getModuleDisplayName(self):
        return "Alchemy Image Tagging API Module"

    def getModuleDescription(self):
        return "Alchemy Image Tagging API Module"

    def getModuleVersionNumber(self):
        return "1.0"

    def isDataSourceIngestModuleFactory(self):
        return True

    def createDataSourceIngestModule(self, ingestOptions):
        return SampleJythonDataSourceIngestModule()

    def isFileIngestModuleFactory(self):
        return True

    def createFileIngestModule(self, ingestOptions):
        return SampleJythonFileIngestModule()
