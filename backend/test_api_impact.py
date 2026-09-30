import requests
import json

base_url = "http://localhost:8000"
repo = "ayushmanbhatt07__fastapi_tutorial"

# Impact for a function
req = {
    "repository": repo,
    "target": {
        "function_name": "get_db"
    },
    "max_depth": 3
}

res = requests.post(f"{base_url}/intelligence", json=req)
print("Response Status:", res.status_code)
print("Impact Result for get_db:\n", json.dumps(res.json(), indent=2))
