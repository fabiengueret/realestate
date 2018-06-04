from lxml import html, etree
import requests
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import RM_RandomizedSamplingScraper

import re
import sqlite3
from RE_Functions import urlRM, Outward
import json




#PostCodeT = input("Postcode? : ")
# Ask for type of property advertised. asking until the answer starts with S or R
# Initialisation 
#SaleorRent = "Begin"
#while SaleorRent.upper()[0] not in ["S","R"] :
#      SaleorRent = input("Sale or Rent / S or R ? : ") 
 
PostCodeT="SW9"
SaleorRent = "S"
     
#Cut the answer to the first letter and upper case it to limit errors
SaleorRent= SaleorRent.upper()[0]
#print(SaleorRent)
url = urlRM(Outward(PostCodeT),SaleorRent,0)
outcode = Outward(PostCodeT) 
# Prepare the database
#conn = sqlite3.connect('RM_properties.sqlite')
#cur = conn.cursor()

#cur.execute('DROP TABLE IF EXISTS Properties')

#cur.execute('''
#CREATE TABLE Properties (RM_ID TEXT, price REAL, type TEXT, address TEXT, latitude REAL,longitude REAL, sqftage TEXT,
#                         firstlisted TEXT, postcode TEXT, Date TEXT, Date_type TEXT, number_bedrooms REAL, flat INTEGER, house INTEGER,
#                         detached INTEGER, semi_d INTEGER, penthouse INTEGER, duplex INTEGER, land INTEGER, offplan INTEGER,
#                         search_date TEXT, description TEXT)''')

# Scrape the webpage
express = False
RMData = RM_RandomizedSamplingScraper.rightmove_data(url,outcode,express)

#print(rightmove_object.result_pages_count)
#print(rightmove_object.url)

# Create the DataFrame of results
df = RMData.get_results()



# Look at some of the results
print(set((df['date'])))


#print(rightmove_object.result_count)

# Quick look at the shape of the data.
df.describe()

# See which 'types' don't have bedroom number extracted
list(df[df.number_bedrooms.isnull()].type.unique())


# Create a DataFrame with summary statistics by number of bedrooms.
funcs = ["mean", "count"]
grouped_df = pd.DataFrame(df.groupby(["number_bedrooms"])["price"].agg(funcs).astype(int))
grouped_df.rename(columns={"mean":"average_price"}, inplace=True)
grouped_df

# Drop the outlier for plotting.
#grouped_df.drop(labels="6", axis=0, inplace=True)

# Create scatter plots to visualise price by bedroom
plt.figure(1,figsize=(10,6))
plt.scatter(df['number_bedrooms'],df['price'], c= df['house'],s=20)
plt.xlabel("Number of bedrooms")
plt.ylabel("£ Price")
# plt.ticklabel_format(style="plain")

# Create histogram chart to visualise bedroom distribution
plt.figure(num=2,figsize=(10,6))
plt.hist(df['number_bedrooms'],bins='auto',range=[0,13], normed=True,facecolor="green")
plt.xlabel("Number of bedrooms")
plt.ylabel("Density")
plt.axis([0, 14, 0, 3])
# plt.ticklabel_format(style="plain")


plt.show()


