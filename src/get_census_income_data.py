import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

STATE_FIPS = "34" 
output_folder = "./data/raw"
output_file = os.path.join(output_folder, "census_income_data.csv")
BASE_URL = "https://api.census.gov/data/2023/acs/acs5/subject"
groups = "NAME,S1901_C01_012E,S1901_C01_013E"

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
    "S1901_C01_012E": "Median_Income",
    "S1901_C01_013E": "Mean_Income"
})

df['Median_Income'] = pd.to_numeric(df['Median_Income'], errors='coerce')
df['Mean_Income'] = pd.to_numeric(df['Mean_Income'], errors='coerce')

df['NAME'] = df['NAME'].apply(lambda x: x.split(';')[1].strip())
df['GEOID'] = df['state'] + df['county'] + df['tract']

df_final = df[['NAME', 'Median_Income', 'Mean_Income', 'GEOID']]

os.makedirs(output_folder, exist_ok=True)
df_final.to_csv(output_file, index=False)
print(f"Saved {len(df)} tracts to {output_file}")

