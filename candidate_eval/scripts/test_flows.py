import requests
import json
url = "http://localhost:7860/api/v1/run/aceb9d9e-d4e0-4c4a-bcbe-fcb22d140deb" 

# Request payload configuration
payload = {
    "input_value": "Hola me llamo Juan Garcia y soy ingeniero de software. Resido en Nueva York y vivo en la calle 123.",  
    "output_type": "text",  
    "input_type": "text" 
}

# Request headers
headers = {
    "Content-Type": "application/json"
}

try:
    # Send API request
    response = requests.request("POST", url, json=payload, headers=headers)
    response.raise_for_status()  

    # Step 1: Parse outer JSON
    outer_json = response.json()

    # Step 2: Extract the inner JSON string from nested structure
    text_json_string = outer_json["outputs"][0]["outputs"][0]["results"]["text"]["data"]["text"]

    # Step 3: Parse that string as JSON to get the actual entities
    entities_json = json.loads(text_json_string)
    print(entities_json)

except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
except ValueError as e:
    print(f"Error parsing response: {e}")
    