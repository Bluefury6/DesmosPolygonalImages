This project is the full color version of my previous project: [https://github.com/Bluefury6/VideoToDesmos/blob/main/README.md]
It will take upwards of 8 hours to render anything over a minute long (30 fps) with this, because I cannot be bothered to improve the speed.
An example of its outcome can be found here: [https://www.youtube.com/watch?v=E09rIV8FJCU]
I would not reccomend actually trying to use this program, as it is more of a fun project for me to make, but if you want to here's how:

1. Replace the "Your API Key" and "Your Video Here" sections (located near the bottom of the the render-display and pythonServer files respectively) with the related information. The video path should be the relative file path.
2. Set any variables you want to in the bottom of the pythonServer file. If sorting is enabled, the program will take *significantly* longer than if it is not.
3. Start the python server, and load the html display.
4. Ensure the html page's embedded Desmos graph is visible to the screen; asyncscreenshot requires the graph to be able to be seen.
5. Click the "Run for Video" button to start the full video, or the "Run for Image" button to load the first (or whatever your frame_number variable is set to) frame.
6. Wait; it may take a while to load things. There will be updates regarding the status on both the local webpage and the python terminal.
7. Once image rendering is finished, you can look at the finished frame. Once video rendering is finished, you will see a "rendering complete" message in the python terminal.
8. To save the video, do NOT kill the terminal; create a copy of the output.mp4 file, *then* you can close the program. Do not close the program beforehand.
9. You have now rendered a video in Desmos, and have the video! There will be no audio, that will need to be added back in manually if desired.
