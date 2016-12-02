import arcpy
import datetime
import re

def howManyPoints(polyLine, disInterval, speedTraveling):
	segmentCounts = polyLine.getLength('PLANAR', 'METERS') / disInterval
	if segmentCounts % 1 > 0:
		segmentShard = segmentCounts % 1
		segmentCounts -= segmentShard
		segmentCounts += 1
	
	return [segmentCounts, segmentShard, speedTraveling]

def sortUniqueValues(inputFeatureClass, idField, speed, cutLength,):
	trackGroups = {}
	
	with arcpy.da.SearchCursor(inputFeatureClass, (idField, speed,'SHAPE@')) as uniqueIDCursor:
		for id in uniqueIDCursor:
			distanceTraveled = float(id[1]) * float(cutLength)
			if id[0] not in trackGroups:
				trackGroups[id[0]] = [{id[2]:howManyPoints(id[2], distanceTraveled, id[1])}]
			else:
				trackGroups[id[0]].append({id[2]:howManyPoints(id[2], distanceTraveled, id[1])})	
			
	return trackGroups

def segmentingPoints(trackId, trackInfo, segRate):
	pointsDict = {}
	count = 0

	arcpy.AddMessage("Processing: " + trackId)
	
	for info in trackInfo:
		count +=1
	 	for line, data in info.items():
			for i in xrange(int(data[0])):
				pointDis = line.positionAlongLine((float(data[2]) * float(segRate)) * i, False)
				pointsDict[str(count) + trackId + str(i)] = pointDis.firstPoint
	
			if data[1] > 0: 
				pointDis = line.positionAlongLine(((float(data[2]) * float(segRate)) * i) + data[1], False)
				pointsDict[str(count) + trackId + str(i)] = pointDis.firstPoint

	arcpy.AddMessage(str(len(pointsDict)) + " Points Were Generated")
	arcpy.AddMessage('*'*50)
	return pointsDict

def addTime(tm, secs):
    fulldate = datetime.datetime(2016, 11, 15, tm.hour, tm.minute, tm.second)
    fulldate = fulldate + datetime.timedelta(seconds=secs)
    return fulldate

def createFeatureClass(sr):
	arcpy.CreateFeatureclass_management(arcpy.env.workspace, "tempFC", "POINT", "", "", "", sr)
	dict = {"X":['TEXT'], "Y":['TEXT'], "Z":['TEXT'], "M":['TEXT'], "UniqueID":['TEXT'], "Time":['DATE']}

	for k, v in dict.items():
		arcpy.AddField_management("tempFC", k, v[0])

def writePoints(dataDict, time, timeSecInterval, filePath):
	start = addTime(time, 0)
	
	for k, v in dataDict.items():
		rowOutput = str(v).split(' ')
		rowOutput.append(k)
		rowOutput[4] = re.findall('\d+|\D+', rowOutput[4])[1]
		rowOutput.append(start)
		rowOutput.append(arcpy.Point(float(rowOutput[0]), float(rowOutput[1])))
		with arcpy.da.InsertCursor("tempFC", ['X','Y','Z','M','UniqueID','Time', 'SHAPE@']) as insertCursor:
			insertCursor.insertRow(rowOutput)

		start = addTime(start, timeSecInterval)

	arcpy.Project_management("tempFC", "tempFCPRJ", 4326)
	arcpy.MakeFeatureLayer_management("tempFCPRJ", 'in_memory\eventLayer', "UniqueID = '" + rowOutput[4] +"'" )
	arcpy.ExportXYv_stats('in_memory\eventLayer', "OBJECTID;UniqueID;Time", "COMMA", filePath + "/" + rowOutput[4] + ".csv", "ADD_FIELD_NAMES")  #filePath + 
	arcpy.Delete_management('in_memory\eventLayer')
	
def main(*args):
	arcpy.env.workspace = args[0] 
	arcpy.env.overwriteOutput = True
	trackLines = args[1] 
	speedOfTravelField = args[2] 
	timeCutInterval = args[3] 
	uniqueIdField = args[4] 
	startDate = datetime.datetime.now().time()
	keepPointFC = args[5] 
	timeInterval = 300
	outputCSV = args[6] 

	sortedValues = sortUniqueValues(trackLines, uniqueIdField, speedOfTravelField, timeCutInterval) 
			
	createFeatureClass(arcpy.Describe(trackLines).spatialReference)

	for k,v in sortedValues.items():
		arcpy.AddMessage('*'*50)
		pointOutput = segmentingPoints(k, v, timeCutInterval)
		writePoints(pointOutput, startDate, timeInterval, outputCSV)
	
	if keepPointFC == 'false':
		arcpy.Delete_management("tempFC")
		arcpy.Delete_management("tempFCPRJ")
		
if __name__ == '__main__':

	arcpy.AddMessage('Converting line into points...')
	argv = tuple(arcpy.GetParameterAsText(i) for i in range(arcpy.GetArgumentCount()))
	main(*argv)
	arcpy.AddMessage('Completed.')
