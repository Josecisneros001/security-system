import requests
import json
  
url = "http://security-system.ngrok.io/api/v1/persons/"
data = {"id": "3afdbc89-d141-4716-925c-3b5ff1b6492c" }
  
jsonObject = json.dumps(data)

response = requests.post(url, json = data)
print(response.text)
  
print("Status Code", response.status_code)
print("JSON Response ", response.json())