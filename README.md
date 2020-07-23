# Speech-Recongnizer
Convert Your Speech to Text using Python

In this project I will use the SpeechRecognition module, if you don’t have it already let’s install it real quick. No worries, installing a module in Python is super easy.
just use below commond for installing SpeechRecognition module
```
pip install SpeechRecognition
```
## Notes

Before run the `speech_recongnizer.py` you have to check the microphone instance because there might be multiple input devices plugged into your computer and 
you need to choose which one you are planning to use. As you know machines are dummies, you have to tell them exactly what to do! Using the following code 
you will be able to see your input devices.
```
print(spr.Microphone.list_microphone_names())
```
![mic list of my computer](https://github.com/TakMashhido/Speech-Recongnizer/blob/master/Mic_list.png)

Here you can see the results of me checking the input devices. I recommend running this script before you define your microphone, because you may get a different result. 
The script returns an array list with input names, for me I want to use the “Microphone (2- Realtek High Def”, so the second element of the array list. Defining the microphone code will look as follows:
```
mic = spr.Microphone(device_index=1) 
```
###### `device_index` is defined by the index number of your input device from the input device array which is discussed earlier and the index of python array elements starts from `0`

#### The result will be saved on `my_result.txt` file
