#!/usr/bin/python
from xml.dom.minidom import parse as xmlParse
import subprocess
import optparse
import os
import sys
from functools import reduce
from time import *
from multiprocessing import pool
from multiprocessing.dummy import Pool as ThreadPool

class SvnLogKit:
    def __init__(self, svnOptions, svnRepoAddr, nameList, logDirectory, diffDirectory, processNum, featureList):
        self.featureList = featureList
        self.svnRepoAddr = svnRepoAddr
        self.nameList = nameList
        self.logDirectory = logDirectory
        self.processNum = processNum
        if not os.path.isdir(logDirectory):
            os.mkdir(logDirectory)
        self.svnLogName = logDirectory + '/' + r'svnLog.log'
        self.svnOptions = svnOptions
        self.createSvnLog()
        self.changes = self.getChanges()
        self.ignoreList = self.getIgnoreList()
        if diffDirectory is None:
            diffDirectory = logDirectory + r'/' + r'diffFiles' 
        self.diffDirectory = diffDirectory
        if not os.path.isdir(diffDirectory):
            os.mkdir(diffDirectory)

    def createSvnLog(self):
        cmd = "svn log" + " " + self.svnOptions + " " + self.svnRepoAddr + ">" + self.svnLogName
        print("start create svn log with svn option: " + self.svnOptions)
        subprocess.call(cmd, shell=True)
        print("svn log creation finished, it is stored within: " + self.svnLogName)

    def getChanges(self):
        print("Start parse svn log file...")
        dom = xmlParse(self.svnLogName)
        data = dom.documentElement.getElementsByTagName('logentry')
        print("svn log file parse finished.")
        return data

    def getFullNameList(self, targetFile):
        print("Start get full author list")
        f = open(targetFile, 'w')
        nameList = []
        for change in self.changes:
            name = change.getElementsByTagName("author")[0].childNodes[0].nodeValue
            if (name not in nameList):
                nameList.append(name)
        print("Found below authors:")
        for name in nameList:
            print(name)
            f.write(name + "\n")
        f.close()
        print("Authors are stored within: " + targetFile)

    def getIgnoreList(self):
        ignoreList = []
        for change in self.changes:
            msg = change.getElementsByTagName("msg")[0].childNodes[0].nodeValue
            if msg.startswith(r"[REVERT]"):
                info = msg.split(' ')[1].strip(',')
                ignoreList.append(info)
        return ignoreList

    def isDataWithinChecklist(self, data, checkList):
        if checkList is not None:
            return data in checkList
        return True

    def getFeature(self, change):
        if self.featureList is None:
            return "FULL"
        msg = change.getElementsByTagName("msg")[0].childNodes[0].nodeValue
        for feature in self.featureList:
            if feature in msg:
                return feature
        return None

    def isIgnored(self, change):
        name = change.getElementsByTagName("author")[0].childNodes[0].nodeValue
        if str(self.getRevision(change)) in self.ignoreList or not self.isDataWithinChecklist(name, self.nameList) or self.getFeature(change) is None:
            return True
        return False

    def getRevision(self, change):
        return int(change.getAttribute("revision"))
    
    def getAuthor(self, change):
        return change.getElementsByTagName("author")[0].childNodes[0].nodeValue

    def createDiff(self, revision):
        preRevision = revision - 1
        targetDiffName = self.diffDirectory + r"/" + "diff-" + str(revision)
        cmd = "svn diff -r" + " " + str(preRevision) + ":" + str(revision) + " " + self.svnRepoAddr + ">" + targetDiffName
        subprocess.call(cmd, shell=True)
        return targetDiffName
    
    def calculateChangedLines(self, change):
        currentR = self.getRevision(change)
        diffFile = self.createDiff(currentR)
        changedLines = int(ToolKit.newCalculateChangedLines(diffFile))
        return changedLines

    def calculateTotalChangedLines(self):
        totalLines = self.getFeatureDic(True)
        changeDic = self.CalculateLineChangesByAuthor()
        print("start calculate total lines...")
        for key in changeDic.keys():
            for value in changeDic[key].values():
                totalLines[key] += value
        print("finish calculate total lines")
        return totalLines

    def calculateChangeLinesMap(self, change):
        if not self.isIgnored(change):
            author = self.getAuthor(change)
            feature = self.getFeature(change)
            changedLines = self.calculateChangedLines(change)
            return [feature, author, changedLines]
        else:
            return None

    def getAuthorDic(self):
        if self.nameList is None:
            return {}
        authorDic = {}
        for author in self.nameList:
            if author not in authorDic.keys():
                authorDic.setdefault(author, 0)
        return authorDic

    def getFeatureDic(self, isTotalLines = False):
        featureDic = {}
        if self.featureList is None:
            featureDic.setdefault("FULL", 0 if isTotalLines else self.getAuthorDic())
        else:
            for feature in self.featureList:
                featureDic.setdefault(feature, 0 if isTotalLines else self.getAuthorDic())
        return featureDic

    def CalculateLineChangesByAuthor(self):
        pool = ThreadPool(self.processNum)
        print("start process svn changes...")
        result = list(pool.map(self.calculateChangeLinesMap, self.changes))
        print("finish process svn changes")
        pool.close()
        pool.join()
        totalLines = self.getFeatureDic()
        print("start re-org data by author...")
        for item in result:
            if item is not None:
                if item[1] not in totalLines[item[0]].keys():
                    totalLines[item[0]].setdefault(item[1], 0)
                totalLines[item[0]][item[1]] += item[2]
        print("finished data re-org")
        return totalLines
class ToolKit:  
    @staticmethod
    def getFileContent(fileName):
        if fileName is None:
            return None
        content = []
        f = open(fileName, 'r')
        print("The content within " + fileName + " is:")
        for line in f.readlines():
            print(line.strip("\n"))
            content.append(line.strip("\n"))
        f.close()
        return content

    @staticmethod
    def calculateChangedLines(diffFile):
        cmdWl = "grep '^+' " + diffFile + "| " + "grep -v '^+++' | sed 's/^.//'| sed s/[[:space:]]//g |sed '/^$/d'|wc -l"
        calculation = subprocess.Popen(cmdWl, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        line, err = calculation.communicate()
        return line

    @staticmethod
    def newCalculateChangedLines(diffFile):
        f = open(diffFile, 'r')
        validFile = True
        changedLines = 0
        for line in f.readlines():
            line = line.strip("\n")
            if line.startswith(r"Index:"):
                if line.endswith(r".xml") or line.endswith(r".yaml"):
                    validFile = False
                else:
                    validFile = True
                continue
            if not validFile:
                continue
            if line.startswith(r"+++"):
                continue
            if line.startswith(r"+"):
                changedLines += 1
        f.close()
        return changedLines

    @staticmethod
    def initOptionParser():
        parser = optparse.OptionParser()
        parser.description = "This tool is used to calculate the changed code lines on svn repo.\n\n \
            If you are first time to use this tool, suggest use below sample command to get the author list first:\n\
            ./parser.py -c fullNameList.txt -t {2019-06-01}:{2020-03-20} -l ./logDirectory -s /var/fpwork/mwu/btsom_trunk/trunk \n \
            And after then, please modify the created fullNameList.txt to include the author names you care.\n \
            If you already have the name list of authors, can use below sample to calculate total changed lines:\n \
            ./parser.py -t {2019-08-01}:{2020-03-20} -s /var/fpwork/mwu/btsom_trunk/trunk/ -n ../svnlog_parser/PnPList.txt -a -j 52"
        parser.add_option("-c", "--createFullNameList", action = "store", dest = "creatNameList", help = "create the full name list from svn log")
        parser.add_option("-t", "--timeDuration", action = "store", dest = "duration", help = "format should be {yyyy-mm-dd}:{yyyy-mm-dd}")
        parser.add_option("-l", "--logFileDirectory", action = "store", dest = "logDirectory", default = "./svnLogFiles", help = "the location where the tmp diff file be located, default value is ./svnLogFiles")
        parser.add_option("-d", "--diffFileDirectory", action = "store", dest = "diffDirectory", help = "the location where diff file stored, default value is ./diffFiles under logFileDirectory")
        parser.add_option("-s", "--svnRepo", action = "store", dest = "svnRepo", help = "svn repo address")
        parser.add_option("-n", "--nameList", action = "store", dest = "nameList", help = "file which stores the name list")
        parser.add_option("-a", "--byAuthor", action = "store_true", dest = "byAuthor", help = "calculate by authors")
        parser.add_option("-j", "--processNum", action = "store", dest = "processNum", default = "32", help = "max concurrency processes number, default value is 32")
        parser.add_option("-f", "--featureList", action = "store", dest = "featureList", help = "file which stores the feature list")
        return parser

    @staticmethod
    def checkInputPar(options):
        if options.duration is None:
            raise Exception("no duration setting")
        if options.svnRepo is None:
            raise Exception("no svn repo setting")

if __name__ == "__main__":
    begin_time = time()
    parser = ToolKit.initOptionParser()
    (options, args) = parser.parse_args()
    ToolKit.checkInputPar(options)
    svnOptions = "-v --xml -r" + " " + options.duration

    if options.creatNameList is not None:
        logKit = SvnLogKit(svnOptions, options.svnRepo, None, options.logDirectory, None, int(options.processNum), None)
        fullNameListFile = options.logDirectory + r"/" + options.creatNameList
        logKit.getFullNameList(fullNameListFile)
        sys.exit(1)

    nameListFile = options.nameList
    nameList = ToolKit.getFileContent(nameListFile)

    featureList = None
    if options.featureList is not None:
        featureList = ToolKit.getFileContent(options.featureList)
    
    logKit = SvnLogKit(svnOptions, options.svnRepo, nameList, options.logDirectory, options.diffDirectory, int(options.processNum), featureList)
    if not options.byAuthor:
        totalLines = logKit.calculateTotalChangedLines()
        print("Total Changed Lines is:")
        for key, value in totalLines.items():
            print(key + ': ' + str(value))
    else:
        totalLines = logKit.CalculateLineChangesByAuthor()
        print("The changed Lines by Authors are:")
        for key1 in totalLines.keys():
            for key, value in totalLines[key1].items():
                print(key1 + ': ' + key + ': ' + str(value))
    
    end_time = time()
    run_time = end_time-begin_time
    print("consumed: ", run_time)