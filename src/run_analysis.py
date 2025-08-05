import os
import pandas as pd
import geopandas as gpd
import time
from tqdm import tqdm
from src import analyzer

API_DELAY_SECONDS = 0.5
GTFS_STOPS_PATH = "./data/raw/stops.txt"
CENSUS_DISABILITY_DATA_PATH = "./data/raw/census_disability_data.csv"
CENSUS_INCOME_DATA_PATH = "./data/raw/census_income_data.csv"
TRACT_SHAPEFILE_PATH = "./data/nj_census_tract_boundaries/tl_2023_34_tract.shp"
PROCESSED_DATA_PATH = "./data/processed/full_data.csv"
ANALYSIS_QUANTILE = 0.20

def main():
    disability_df = pd.read_csv(CENSUS_DISABILITY_DATA_PATH, dtype={'GEOID': str})
    income_df = pd.read_csv(CENSUS_INCOME_DATA_PATH, dtype={'GEOID': str})
    tracts_gdf = gpd.read_file(TRACT_SHAPEFILE_PATH)
    
    disability_df = disability_df.rename(columns={
        'Population_With_Disability': 'disability_population',
        'Total_Population': 'total_population'
    })

    income_df = income_df.rename(columns={
        'Median_Income': 'median_income',
        'Mean_Income': 'mean_income'
    })
    
    income_df['median_income'] = income_df['median_income'].clip(lower=0)
    census_df = pd.merge(disability_df, income_df, on="GEOID", how="left")
    
    stops_df = pd.read_csv(GTFS_STOPS_PATH)
    stops_gdf = gpd.GeoDataFrame(
        stops_df,
        geometry=gpd.points_from_xy(stops_df.stop_lon, stops_df.stop_lat),
        crs="EPSG:4326"
    )

    stops_gdf = stops_gdf.to_crs(tracts_gdf.crs)
    stops_with_tracts = gpd.sjoin(stops_gdf, tracts_gdf, how="inner", predicate="within")

    master_df = pd.merge(stops_with_tracts, census_df, on="GEOID", how="left")

    master_df.dropna(subset=['total_population', 'disability_population', 'median_income'], inplace=True)
    master_df['disability_percentage'] = (master_df['disability_population'] / master_df['total_population']) * 100

    low_quantile = ANALYSIS_QUANTILE
    high_quantile = 1 - ANALYSIS_QUANTILE

    low_disability_threshold = master_df['disability_percentage'].quantile(low_quantile)
    high_disability_threshold = master_df['disability_percentage'].quantile(high_quantile)
    low_income_threshold = master_df['median_income'].quantile(low_quantile)
    high_income_threshold = master_df['median_income'].quantile(high_quantile)

    master_df['disability_group'] = "N/A"
    master_df['income_group'] = "N/A"
    master_df.loc[master_df['disability_percentage'] <= low_disability_threshold, 'disability_group'] = "Low"
    master_df.loc[master_df['disability_percentage'] >= high_disability_threshold, 'disability_group'] = "High"
    master_df.loc[master_df['median_income'] <= low_income_threshold, 'income_group'] = "Low"
    master_df.loc[master_df['median_income'] >= high_income_threshold, 'income_group'] = "High"
    
    stops_to_analyze = master_df[
        (master_df['disability_group'] != "N/A") | (master_df['income_group'] != "N/A")
    ].copy()

    processed_stops = set()
    output_file_path = PROCESSED_DATA_PATH
    if os.path.exists(output_file_path):
        processed_df = pd.read_csv(output_file_path)
        processed_stops = set(processed_df['stop_id'])
    
    output_mode = 'a' if os.path.exists(output_file_path) else 'w'
    header = not os.path.exists(output_file_path)
    
    with open(output_file_path, mode=output_mode, newline='', encoding='utf-8') as f:
        for index, stop in tqdm(stops_to_analyze.iterrows(), total=len(stops_to_analyze), desc="Analyzing Stops"):
            if stop['stop_id'] in processed_stops:
                continue

            stop_lat = stop.geometry.y
            stop_lon = stop.geometry.x
            analysis_data = analyzer.analyze_stop_accessibility(stop_lat, stop_lon)

            result_row = {
                'stop_id': stop['stop_id'], 'stop_name': stop['stop_name'],
                'latitude': stop_lat, 'longitude': stop_lon,
                'income_group': stop['income_group'], 'disability_group': stop['disability_group'],
                'median_income': stop['median_income'], 
                'disability_percentage': stop['disability_percentage'],
                **analysis_data
            }
            
            df_row = pd.DataFrame([result_row])
            df_row.to_csv(f, header=header, index=False)
            header = False
            f.flush()
            time.sleep(API_DELAY_SECONDS)

    print(f"\nsaved to {output_file_path}")


if __name__ == "__main__":
    main()