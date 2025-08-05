import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

STATE_FIPS = "34"  
output_folder = "./data/raw"
output_file = os.path.join(output_folder, "census_disability_data.csv")
BASE_URL = "https://api.census.gov/data/2023/acs/acs5/subject"
groups = "NAME,S1810_C01_001E,S1810_C02_001E"

params = {
    "get": groups,
    "for": "tract:*",
    "in": f"state:{STATE_FIPS}",
    "key": CENSUS_API_KEY
}

response = requests.get(BASE_URL, params=params)
response.raise_for_status()
data = response.json()

df = pd.DataFrame(data[1:], columns=data[0])

df = df.rename(columns={
    "S1810_C01_001E": "Total_Population",
    "S1810_C02_001E": "Population_With_Disability"
})

df['Total_Population'] = pd.to_numeric(df['Total_Population'], errors='coerce')
df['Population_With_Disability'] = pd.to_numeric(df['Population_With_Disability'], errors='coerce')

df['NAME'] = df['NAME'].apply(lambda x: x.split(';')[1].strip())
df['GEOID'] = df['state'] + df['county'] + df['tract']
    
df_final = df[['NAME', 'Total_Population', 'Population_With_Disability', 'GEOID']]

os.makedirs(output_folder, exist_ok=True)
df.to_csv(output_file, index=False)
print(f"Saved {len(df)} tracts to {output_file}")