import requests
import pandas as pd

API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
params = {
    "format": "geojson",
    "limit": 50,
    "orderby": "time",
}

try:
    response = requests.get(API_URL, params=params, timeout=30)

    if not response.ok:
        print("Request failed:", response.status_code)
        print(response.text[:500]) 
        raise SystemExit(1)

    data = response.json()

    print("API CONNECTION SUCCESSFUL")
    print("HTTP status code:", response.status_code)
    print("Number of earthquake records:", len(data["features"]))

    print("\nTop level keys:")
    print(list(data.keys()))

    print("\nFirst earthquake record:")
    props = data["features"][0]["properties"]
    print("Place:", props["place"])
    print("Magnitude:", props["mag"])
    print("Time:", props["time"])
    print(data["features"][0]["geometry"]["coordinates"])

except requests.exceptions.RequestException as error:
    print("API request failed:", error)

except (KeyError, IndexError, ValueError) as error:
    print("Unexpected response format:", error)


features = data["features"]
records=[]

for feature in features:
    properties = feature["properties"]
    geometry = feature["geometry"] or {}
    coordinates = geometry.get("coordinates") or [None, None, None]

    records.append({
        "id":feature.get("id"),
        "magnitude":properties.get("mag"),
        "place":properties.get("place"),
        "time": properties.get("time"),
        "status": properties.get("status"),
        "longitude": coordinates[0],
        "latitude": coordinates[1],
        "depth": coordinates[2]
    })

df = pd.DataFrame(records)

df.to_csv("earthquake.csv", index=False)
print("\nDataset saved to earthquake.csv")



