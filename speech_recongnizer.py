# -*- coding: utf-8 -*-
"""
Created on Thu Jul 23 14:09:18 2020

@author: TakMashhido
"""
# import the module 
import speech_recognition as spr 

# create the recognizer 
r = spr.Recognizer() 

# define the microphone 
mic = spr.Microphone(device_index=1) 

# record your speech 
with mic as source: 
    audio = r.listen(source) 

# speech recognition 
result = r.recognize_google(audio)

# export the result 
with open('my_result.txt',mode ='w') as file: 
    file.write("Recognized text:") 
    file.write("\n") 
    file.write(result) 
print("Exporting process completed!")