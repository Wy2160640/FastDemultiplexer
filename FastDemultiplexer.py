#!/usr/bin/python
# encoding: UTF-8
# author: Sébastien Boisvert
# this is GPL code

#import profile
import gzip
import zlib
import sys
import os
import os.path

if len(sys.argv)!=4:
	print "usage"
	print "FastDemultilexer SampleSheet.csv Project_XYZ/Sample_lane1 Demultiplexed"
	sys.exit(0)

FTEXT, FHCRC, FEXTRA, FNAME, FCOMMENT = 1, 2, 4, 8, 16

class GzFileReader:
	def __init__(self,file):
		print file
		self.m_file=open(file)
		self.m_bufferSize=4096*4096
		
		self.readHeader()

		data=self.m_file.read(self.m_bufferSize)
		self.m_buffer=self.decompress(data)


	def readHeader(self):
		magic = self.m_file.read(2)
		method = ord( self.m_file.read(1))
		flag = ord( self.m_file.read(1) )
		mtime = self.m_file.read(4)
		self.m_file.read(2)
		
		print str(flag)


	def decompress(self,data):
		return zlib.decompress(data)

	def readline(self):
		#if we have a new line in the buffer, return it.
		i=0
		theLength=len(self.m_buffer)
		while i<theLength:
			if self.m_buffer[i]=='\n':
				line=self.m_buffer[0:i+1]
				newBuffer=self.m_buffer[i+1:theLength]
				self.m_buffer=newBuffer
				return line

		# we found no new line
		# we need to read the file again
	
		data=m_file.read(self.m_bufferSize)
	
		# the last line may not have any new line
		if len(data)==0:
			return self.m_buffer

		self.m_buffer=self.m_buffer+self.decompress(data)

		# we already know how to do it
		return self.readline()

class Entry:
	def __init__(self,project,sample,index1,index2):
		#print "entry with "+project+" "+sample+" "+index1+" "+index2
		self.m_project=project
		self.m_sample=sample
		self.m_index1=index1
		self.m_index2=index2

	def getProject(self):
		return self.m_project
	def getSample(self):
		return self.m_sample
	def getIndex1(self):
		return self.m_index1
	def getIndex2(self):
		return self.m_index2

class SampleSheet:
	def __init__(self,sampleSheet,lane):
		# C0947ACXX,4,CQDM1-1,No,TAAGGCGA-TAGATCGC,P2J0-1,N,PE_indexing,LR,CQDM
		projectColumn=9
		sampleColumn=2
		indexColumn=4
		laneColumn=1

		self.m_entries=[]

		for line in open(sampleSheet):
			tokens=line.split(",")
			if len(tokens)<4:
				continue

			theLane=tokens[laneColumn]

			if lane!=theLane:
				continue

			project=tokens[projectColumn].strip()
			sample=tokens[sampleColumn]
			index=tokens[indexColumn]

			tokens2=index.split("-")
			index1=tokens2[0]
			index2=""
			if len(tokens2)==2:
				index2=tokens2[1]

			entry=Entry(project,sample,index1,index2)
			
			self.m_entries.append(entry)

		self.makeIndex()

	def getErrorList(self,base):
		list=[]

		i=0
		changes=['A','T','C','G','N']

		theLength=len(base)

		while i<theLength:
			actual=base[i]
			for j in changes:
				if j==actual:
					continue
				before=base[0:i]
				after=base[(i+1):(theLength)]
				newSequence=before+j+after
				list.append(newSequence)

				#print "1MISS "+ newSequence
			i+=1

		return list

	def makeIndex(self):
		self.m_index={}
		for entry in self.m_entries:
			key=entry.getIndex1()+entry.getIndex2()
			value=[entry.getProject(),entry.getSample()]
			self.m_index[key]=value

			# generate things with 1 error in index1
			index1ErrorList=self.getErrorList(entry.getIndex1())
	
			for i in index1ErrorList:
				key=i+entry.getIndex2()
				self.m_index[key]=value

			# generate things with 1 error in index2
			index2ErrorList=self.getErrorList(entry.getIndex2())

			for i in index2ErrorList:
				key=entry.getIndex1()+i
				self.m_index[key]=value

			# generate things with 1 error in index1 and 1 error in index2
			for i in index1ErrorList:
				for j in index2ErrorList:
					key=i+j
					self.m_index[key]=value

		print "IndexSize= "+str(len(self.m_index))
				

	def compare(self,sequence1,sequence2):
		score=0
		i=0
		len1=len(sequence1)
		len2=len(sequence2)

		while i<len1 and i<len2:
			if sequence1[i]!=sequence2[i]:
				score+=1
			i+=1
		
		return score

	def classify(self,index1,index2,lane):
		key=index1+index2

		if key in self.m_index:
			return self.m_index[key]

		threshold=4

		for entry in self.m_entries:
			score1=self.compare(entry.getIndex1(),index1)
			score2=self.compare(entry.getIndex2(),index2)

			#print entry.getSample()+" "+str(score1)+" "+str(score2)

			if score1<threshold and score2<threshold:
				return [entry.getProject(),entry.getSample()]

		return ["Undetermined_indices","Sample_lane"+lane]

class Sequence:
	def __init__(self,line1,line2,line3,line4):
		#print "Initiating "+line1
		self.m_line1=line1
		self.m_line2=line2
		self.m_line3=line3
		self.m_line4=line4

	def getLine1(self):
		return self.m_line1
	def getLine2(self):
		return self.m_line2
	def getLine3(self):
		return self.m_line3
	def getLine4(self):
		return self.m_line4

class FileReader:
	def __init__(self,filePath):
		print "Opening "+filePath
		if filePath.find(".gz")>=0:
			self.m_file=gzip.open(filePath)
		else:
			self.m_file=open(filePath)
		
		self.m_buffer=self.m_file.readline().strip()

	def hasNext(self):
		return len(self.m_buffer)>0

	def getNext(self):
		sequence=Sequence(self.m_buffer,self.m_file.readline().strip(),self.m_file.readline().strip(),self.m_file.readline().strip())
		
		self.m_buffer=self.m_file.readline().strip()

		return sequence

class InputDirectory:
	def __init__(self,laneDirectory):
		self.m_directory=laneDirectory

		self.m_r1Files=[]
		self.m_r2Files=[]
		self.m_r3Files=[]
		self.m_r4Files=[]

		for i in os.listdir(self.m_directory):
			if i.find("_R1_")>=0:
				self.m_r1Files.append(i)
				self.m_r2Files.append(i.replace("_R1_","_R2_"))
				self.m_r3Files.append(i.replace("_R1_","_R3_"))
				self.m_r4Files.append(i.replace("_R1_","_R4_"))

		self.m_current=0

		self.setReadersToCurrent()

		while not self.m_reader1.hasNext() and self.m_current<len(self.m_r1Files):
			self.m_current+=1
			self.setReadersToCurrent()

	def setReadersToCurrent(self):
		if not self.m_current<len(self.m_r1Files):
			return

		self.m_reader1=FileReader(self.m_directory+"/"+self.m_r1Files[self.m_current])
		self.m_reader2=FileReader(self.m_directory+"/"+self.m_r2Files[self.m_current])
		self.m_reader3=FileReader(self.m_directory+"/"+self.m_r3Files[self.m_current])
		self.m_reader4=FileReader(self.m_directory+"/"+self.m_r4Files[self.m_current])
			

	def hasNext(self):
		if self.m_current>=len(self.m_r1Files):
			return False

		while not self.m_reader1.hasNext() and self.m_current<len(self.m_r1Files):
			print "opening next files"
			self.m_current+=1
			self.setReadersToCurrent()

		return self.m_reader1.hasNext()

	def getNext(self):
		return [self.m_reader1.getNext(),self.m_reader2.getNext(),self.m_reader3.getNext(),self.m_reader4.getNext()]

class OutputDirectory:
	def __init__(self,outputDirectory,maxInFile):
		self.m_directory=outputDirectory
		self.m_max=maxInFile

		self.makeDirectory(self.m_directory)
		self.m_files1={}
		self.m_files2={}

		self.m_counts={}
		self.m_currentNumbers={}

	def makeDirectory(self,name):
		if not os.path.exists(name):
			os.mkdir(name)

	def closeFiles(self):
		for i in self.m_files1.items():
			i[1].close()

		for i in self.m_files2.items():
			i[1].close()

	def write(self,project,sample,lane,sequenceTuple):
		#print "Writing to "+project+" "+sample+" "+lane

		key=project+sample+lane

		if (key not in self.m_files1) or self.m_counts[key]==self.m_max:

			#close the old files
			if key in self.m_files1 and self.m_counts[key]==self.m_max:
				self.m_files1[key].close()
				self.m_files2[key].close()
				self.m_currentNumbers[key]+=1
			else:
				self.m_currentNumbers[key]=1

			self.m_counts[key]=0

			projectDir=project
			sampleDir=sample

			if project!="Undetermined_indices":
				projectDir="Project_"+project
				sampleDir="Sample_"+sample

			self.makeDirectory(self.m_directory+"/"+projectDir)
			self.makeDirectory(self.m_directory+"/"+projectDir+"/"+sampleDir)

			file1=self.m_directory+"/"+projectDir+"/"+sampleDir+"/"+sample+"_Lane"+lane+"_R1_"+str(self.m_currentNumbers[key])+".fastq.gz"
			file2=self.m_directory+"/"+projectDir+"/"+sampleDir+"/"+sample+"_Lane"+lane+"_R2_"+str(self.m_currentNumbers[key])+".fastq.gz"

			self.m_files1[key]=gzip.open(file1,"w")
			self.m_files2[key]=gzip.open(file2,"w")

		f1=self.m_files1[key]
		f1.write(sequenceTuple[0].getLine1()+"\n"+sequenceTuple[0].getLine2()+"\n"+sequenceTuple[0].getLine3()+"\n"+sequenceTuple[0].getLine4()+"\n")

		f2=self.m_files2[key]
		f2.write(sequenceTuple[1].getLine1()+"\n"+sequenceTuple[1].getLine2()+"\n"+sequenceTuple[1].getLine3()+"\n"+sequenceTuple[1].getLine4()+"\n")

		self.m_counts[key]+=1

		#print sample+" "+sequenceTuple[0].getLine1()


class Demultiplexer:
	def __init__(self,sampleSheet,inputDirectoryPath,outputDirectoryPath,lane):
		sheet=SampleSheet(sampleSheet,lane)
		inputDirectory=InputDirectory(inputDirectoryPath)

		maxInFile=4000000

		outputDirectory=OutputDirectory(outputDirectoryPath,maxInFile)

		processed=0

		while inputDirectory.hasNext():
			sequenceTuple=inputDirectory.getNext()
			index1=sequenceTuple[1].getLine2()
			index2=sequenceTuple[2].getLine2()

			[project,sample]=sheet.classify(index1,index2,lane)

			outputDirectory.write(project,sample,lane,[sequenceTuple[0],sequenceTuple[3]])
		
			processed+=1

			if processed%10000==0:
				print "Processed: "+str(processed)
				sys.stdout.flush()

		outputDirectory.closeFiles()

def main():
	sheet=sys.argv[1]
	inputDir=sys.argv[2].replace("\/","")
	outputDir=sys.argv[3].replace("\/","")

	lane=inputDir.split("lane")[1].strip()

	demultiplexer=Demultiplexer(sheet,inputDir,outputDir,lane)

if __name__=="__main__":
#	doProfiling=False

#	if doProfiling:
#		profile.run('main()')
#	else:

	main()

