import os
import sys

def keyFunc(value):
    if ".jpg" in value:
        value = value[:len(value)-4]
        valueSplit = value.split('_')
        valueSecond = valueSplit[0]
        valueFid = valueSplit[1]
        return int(valueSecond) * 100 + int(valueFid)
    return -1

list_ = os.listdir(sys.argv[1])
list_.sort(key = keyFunc)
with open("file.txt", "w") as output:
    for value in list_:
        if ".jpg" in value:
            output.write("file '" + value + "'\n")