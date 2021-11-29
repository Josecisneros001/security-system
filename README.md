# HackMty2021 - SecuritySystem
This project aims to run a script ([main.py](main.py)) capable of processing a video/stream and store recordings of a whole week.
- Algorithms implemented:
  - Face Recognition - Azure Cognitive Services
- Uses Flask to publish the image post-processed into a web-page to localhost:8080. It could receive query parameters to access recordings from past days. deltaDays, deltaHours, deltaMinutes, deltaSeconds. (Ex. localhost:8080/camara?deltaHours=2 -> Returns a Stream with the recordings from 2 Hours Ago.)
