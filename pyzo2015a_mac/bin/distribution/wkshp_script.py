#Ferguson Workshop - Python Script

import time
import calendar
import codecs
import datetime
import json
import sys
import gzip
import string
import glob
import os
import numpy as np

if ( sys.version_info.major == 3 ):
    from functools import reduce

### Bringing in the Data
tweetPath = os.path.join("data_files", "twitter")
tweetFiles = {
   "time01": os.path.join(tweetPath, "statuses.*.gz")
}

frequencyMap = {}
globalTweetCounter = 0

timeFormat = "%a %b %d %H:%M:%S +0000 %Y"

reader = codecs.getreader("utf-8")

for (key, path) in tweetFiles.items():
    localTweetList = []
    for filePath in glob.glob(path):
        print ("Reading File:", filePath)
        
        for line in gzip.open(filePath, 'rb'):

            # Try to read tweet JSON into object
            tweetObj = None
            try:
                tweetObj = json.loads(reader.decode(line)[0])
            except Exception as e:
                continue

            # Deleted status messages and protected status must be skipped
            if ( "delete" in tweetObj.keys() or "status_withheld" in tweetObj.keys() ):
                continue

            # Try to extract the time of the tweet
            try:
                currentTime = datetime.datetime.strptime(tweetObj['created_at'], timeFormat)
            except:
                print (line)
                raise

            currentTime = currentTime.replace(second=0)
            
            # Increment tweet count
            globalTweetCounter += 1
            
            # If our frequency map already has this time, use it, otherwise add
            if ( currentTime in frequencyMap.keys() ):
                timeMap = frequencyMap[currentTime]
                timeMap["count"] += 1
                timeMap["list"].append(tweetObj)
            else:
                frequencyMap[currentTime] = {"count":1, "list":[tweetObj]}

# Fill in any gaps
times = sorted(frequencyMap.keys())
firstTime = times[0]
lastTime = times[-1]
thisTime = firstTime

timeIntervalStep = datetime.timedelta(0, 60)    # Time step in seconds
while ( thisTime <= lastTime ):
    if ( thisTime not in frequencyMap.keys() ):
        frequencyMap[thisTime] = {"count":0, "list":[]}
        
    thisTime = thisTime + timeIntervalStep

print ("Processed Tweet Count:", globalTweetCounter)

