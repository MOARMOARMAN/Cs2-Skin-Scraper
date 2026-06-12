import requests
import csv
def create_skin_names_csv():
    response = requests.get("https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json")
    js = response.json()
    invalid = ["knife", "bayonet", "karambit", "daggers", "gloves", "wraps", "howl"]
    skin_name = []
    with open("skin_names.csv", "w", encoding="utf-8") as csvf:
        csvw = csv.writer(csvf, lineterminator='\n')
        for skin in js:
            if not any(word in skin.get("name").lower() for word in invalid):
                collections = skin.get("collections", [])
                if collections:
                    csvw.writerow([skin.get("name"), collections[0].get("name"), skin.get("min_float"), skin.get("max_float"), skin.get("rarity").get("name")])
        
