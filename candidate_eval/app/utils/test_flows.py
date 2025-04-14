import requests
url = "http://localhost:7860/api/v1/run/99ca7e88-27af-41a7-9d4a-0242a69f3aa9"  

text ="""Hola, soy Adrian Garcia and I'm originally from Liverpool.
My credit card number is 4095-2609-9393-4932 and my crypto wallet id is 16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ.
On 11/10/2024 I visited www.microsoft.com and sent an email to test@presidio.site,  from IP 192.168.0.1.
My passport: 191280342 and my phone number: (212) 555-1234.
This is a valid International Bank Account Number: IL150120690000003111111 . Can you please check the status on bank account 954567876544? 
Kate's social security number is 078-05-1126.  Her driver license? it is 1234567A. Python, C++, Java, and C# are my favorite programming languages. SQL"""

# Request payload configuration
payload = {
    "input_value": text,  # The input value to be processed by the flow
    "output_type": "chat",  # Specifies the expected output format
    "input_type": "text"  # Specifies the input format
}

# Request headers
headers = {
    "Content-Type": "application/json"
}

try:
    # Send API request
    response = requests.request("POST", url, json=payload, headers=headers)
    response.raise_for_status()  # Raise exception for bad status codes

    # Print response
    print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
except ValueError as e:
    print(f"Error parsing response: {e}")
    