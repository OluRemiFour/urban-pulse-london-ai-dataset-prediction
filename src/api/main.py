import pandas as pd
import numpy as np

zillow_dataset = pd.read_csv('zillow_properties_listing.csv')
# print(f"Zillow dataset shape: {zillow_dataset.shape}")
# print(f"Zillow dataset columns: {zillow_dataset.columns.tolist()}")

# print(zillow_dataset.isnull().sum())

# pd.set_option('display.max_columns', None)
# print(zillow_dataset.columns.tolist())
# for col in zillow_dataset.columns:
#     print(col)

essential_cols = [
    "zpid", "latitude", "longitude", "city", "zipcode", "county",
    "price", "zestimate", "rentZestimate", "lastSoldPrice", "priceHistory",
    "bedrooms", "bathrooms", "livingArea", "sqft", "lotSize", "yearBuilt", "homeType",
    "daysOnZillow", "tourViewCount", "num_of_contacts", "num_of_applications",
    "sold_to_list_ratio", "getting_around_scores", "climate_risks",
    "homeStatus", "listingTypeDimension", "isOffMarket", "dateSold", "availability_date"
]

dataset = zillow_dataset[essential_cols]
# print(f"After selecting essential cols: {dataset.shape}")
# print(dataset['num_of_applications'].isnull().sum())

    
# non-numeric columns like date, priceHistory dateSold etc can not be calculate to median()
# so we convert date columns to datetime:
dataset['dateSold'] = pd.to_datetime(dataset['dateSold'], errors='coerce')
dataset['availability_date'] = pd.to_datetime(dataset['availability_date'], errors='coerce')

num_cols = ['dateSold', 'availability_date' ,"zestimate", "rentZestimate", "lastSoldPrice", "livingArea", "sqft", "lotSize", "sold_to_list_ratio", "num_of_contacts", "bedrooms", "bathrooms", "yearBuilt", "tourViewCount", "num_of_applications"]
for col in num_cols:
    dataset[col] = dataset[col].fillna(dataset[col].median())

print(f"After filling NaN values: {dataset.shape}")
print(f"NaN values after filling: {dataset.isnull().sum().sum()}")

print(dataset.tail())
