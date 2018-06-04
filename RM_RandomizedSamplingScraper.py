#!/usr/bin/env python

# Dependencies

from lxml import html
#url management library
import requests
#Data management library
import pandas as pd
#Time management library
import datetime as dt
# Database Library
import numpy as np
# open floorplan
import io
#OCR
import pytesseract
#Regex
import re 
#Pillow image management
from PIL import Image
# functors 
from RE_Functions import functor_words_eliminator
#database
import sqlite3
import time
import random

class rightmove_data(object):
    """The rightmove_data web scraper works by implementing an instance of the class 
    on the URL returned by a search on the rightmove website. Go to rightmove.co.uk
    and search for whatever you want, then create an instance of the class on the URL 
    returned by the search. The class returns an object which includes various 
    methods for extracting data from the search results, the most useful being the 
    .get_results() method which returns all results as a pandas DataFrame object.
    """
    
    def __init__(self, url , outcode, express):
        # FG the self variable represents the instance of the object itself.
        # FG declared explicitly
        # FG __init__ method represents a constructor in Python.
        # FG call rightmove_data() Python creates an object and passes it as the first parameter to the __init__ method.
        # FG Any additional parameters (url) will also get passed as argument
        self.url = url
        self.postcode = outcode
        self.express = express
        # determine if the url is a property search result. works for rent and sale
        try:
            if "searchType=SALE" in self.url or "property-for-sale" in self.url:
                self.rent_or_sale = "SALE"
            elif "searchType=RENT" in self.url or "property-to-rent" in self.url:
                self.rent_or_sale = "RENT"
        except ValueError:
            print("Not a valid rightmove search URL.")
        
        # the number of search results
        self.results_count = self.__results_count()
        # the number of pages to get all the results
        self.result_pages_count = self.__result_pages_count()
        
        # Get the properties already in the database to avoid doing the work twice!
        conn = sqlite3.connect('RM_properties.sqlite')
        cur = conn.cursor()
        sqlstr = 'SELECT DISTINCT RM_ID FROM Properties'
        cur.execute(sqlstr)
        ID = cur.fetchall()
        self.P_ID = [i[0] for i in ID]
        conn.close
       

    def __results_count(self):
        """Returns an integer of the total number of results returned by the search URL."""
        
        # FG ping the url for information
        page = requests.get(self.url)
        # FG Get the content of the hhtp/url and parse it using the html module
        tree = html.fromstring(page.content)
        # FG 
        xp_result_count = """//span[@class="searchHeader-resultCount"]/text()"""
        # FG query in tree for the result count on the page
        return int(tree.xpath(xp_result_count)[0].replace(",", ""))

    
    def __result_pages_count(self):
        """Returns the number of result pages returned by the search URL.
        There are 24 results on each results page, but note that the
        rightmove website limits results pages to a maximum of 42 pages."""

        page_count = self.results_count // 24
        
        if self.results_count % 24 > 0:
            page_count += 1

        # Rightmove will return a maximum of 42 results pages, hence:
        if page_count > 42: page_count = 42

        return page_count

    def __get_individual_info(self,property_url, firstdesc):
        """This is a hidden method to scrape the data from the individual property page
           It is used iteratively by the .get_results() and _get_page_results
           """
        # Set the xpaths for the description
        xp_keyfeatures = """//div[@class="sect key-features"]\
                           //ul[@class="list-two-col list-style-square"]//li/text()"""
        xp_desc = """//div[@class="sect "]\
                     //p[@itemprop="description"]/text()"""
        xp_firstlisted =  """//div[@id="firstListedDateValue"]/text()"""
        
        # Set the xpaths for the geo location of the property
        xp_latlong = """//div[@class="pos-rel"]\
                        //a[@class="block js-tab-trigger js-ga-minimap"]\
                       //img/@src"""
         
        # set the path for the floorplan
        xp_floorplan = """//div[@id="floorplanTabs"]\
                          //img/@src"""
        
                
        # Use the requests library to get the whole web page.
        page = requests.get(property_url)
#        property_ID = property_url[54:-5]

        # Process the html.
        tree = html.fromstring(page.content)
        
        # Create data lists from Xpaths.
        fd = tree.xpath(xp_firstlisted)
        if len(fd)!=0 : firstd =fd[0]
        else: firstd = None  
        firstlisted = pd.to_datetime(firstd, dayfirst=True,format= '%d %B %Y',errors='ignore')        
        # any text describing the property
        list_key_features = tree.xpath(xp_keyfeatures)
        keyfeatures = ' '.join(list_key_features) 
        keyfeatures = keyfeatures.replace('/',' ')
        desc = tree.xpath(xp_desc)
        description = ' '.join(desc) 
        #the full text available to mining
        description = description+' '+ keyfeatures + ' ' + firstdesc
        desc = description.lower()
        description = desc.replace('/',' ').replace('.',' ').replace('\'',' ').replace(',',' ').replace('"','')
        dws= description.split()
        #the unique words in the descriptions
        dwset= set(dws)
        # we eliminate grammatical and non informative words: 'the' 'is' ....
        dWs =list(dwset)
        descWords = functor_words_eliminator (dWs)
        
        #first attempt at finding the square footage
        # If found then the floorplan is not looked at (time and download economy)
        sqftagenotfound = True
        print(property_url)
        regex = r'(?:(?<=\s))(\b\d{1,3}(?:[,.\s]*\d{3})*\b(?!,))(?:(?=\s*[sS]{1}\s*[qQ]{1}.?(uare)?\s*[fF]{1}(ee)?\s*[tT]?))'
        tuplessqftages=re.findall(regex,desc,re.IGNORECASE)
        
        listsqftage=[i[0] for i in tuplessqftages]
     #   print('Description Footage', listsqftage)
        f=[float(i.replace(',','').replace(" ",""))for i in listsqftage]
        if len(f)!=0 :
            sqftage=float(max(f))
            sqftagenotfound= False
        else: 
            sqftage = None  
            sqftagenotfound= True
       
       
                
        # find square footage in the floorplan only if not found earlier
        if sqftagenotfound and not self.express :
           floorplan_urls = tree.xpath(xp_floorplan)
           if len(floorplan_urls)!=0 : 
              floorplan_url =floorplan_urls[0]
              response = requests.get(floorplan_url)
              flrpln = Image.open(io.BytesIO(response.content))
              
              ### if we want to save floorplans #########
#              RM_ID = property_url[54:-5]
#              path = 'F:/New folder/Job Search/Real Estate Project/RMFlooplans/'
#              extension = floorplan_url [-4:]
#              fulldestination = path + RM_ID + 'floorplan' + extension
#              flrpln.save(fulldestination)
              
              i=-1
              band = ['bottom','top']
              while sqftagenotfound and i<1 :
                  i = i+1
                  img = flrpln
                  width,height = img.size
                  
                  # starting from the top left corner
                  left = [0,0]
                  top = [5*height/6,0]
                  # to the lower right corner
                  right = [width,width] 
                  bottom = [height,height/6]
                  # crop the picture to bottom and top band 
                  img= img.crop((left[i],top[i],right[i],bottom[i]))
                  img= img.resize((width*2, height//6*2),Image.ANTIALIAS)
                                                    
                  # the OCR proper using neural networks
                  text = pytesseract.image_to_string(img, config='--psm 12 --oem 2 --user-words')
                  # et voila
                  # parse text to find square footage     
                  tuplessqftages =re.findall(regex,text,re.IGNORECASE)
              
                  sqftages=[t[0] for t in tuplessqftages]
                  print(band[i], 'Floorplan Footage', sqftages)
                  f=[float(i.replace(',',''))for i in sqftages]
                  if len(f)!=0 : 
                       sqftage=float(max(f))
                       sqftagenotfound = False
                  else : 
                      sqftage= None
                      sqftagenotfound = True
           else: 
               floorplan_url = None 
               sqftage = None
               
      
        print('Final footage' , sqftage)
        # Latitute longitude
        latlongs = tree.xpath(xp_latlong)
        latlong=' '.join(latlongs)
        regexlat = r'(?<=latitude=)(-?\d\d*[\.]?\d+)'
        regexlon = r'(?<=longitude=)(-?\d\d*[\.]?\d+)'
        lat=re.findall(regexlat,latlong)
        if len(lat)!=0 : latitude=lat[0]
        else: latitude = None
        lon = re.findall(regexlon,latlong)
        if len(lon)!=0 : longitude= lon[0]
        else: longitude = None
        
        
        
        return [latitude , longitude , descWords , sqftage , firstlisted]
    
    def __get_page_results(self,page_url):
        """This is a hidden method to scrape the data from a single page
        of search results. It is used iteratively by the .get_results()
        method to scrape data from every page returned by the search."""

        # Set the correct xpath for the price.
        if self.rent_or_sale == "RENT":
            xp_prices = """//span[@class="propertyCard-priceValue"]/text()"""
        elif self.rent_or_sale == "SALE":
            xp_prices = """//div[@class="propertyCard-priceValue"]/text()"""

        # Set the xpaths for listing title, property address, 
        # listing URL, and agent URL.
        xp_titles = """//div[@class="propertyCard-details"]\
        //a[@class="propertyCard-link"]\
        //h2[@class="propertyCard-title"]/text()"""
        xp_addresses = """//address[@class="propertyCard-address"]//span/text()"""
        xp_layus = """//div[@class="propertyCard-description"]\
        //a[@class="propertyCard-link"]//span/text()"""
        xp_addedon = """//div[@class="propertyCard-detailsFooter"]\
        //div[@class="propertyCard-branchSummary"]\
        //span[@class="propertyCard-branchSummary-addedOrReduced"]/text()"""
        xp_weblinks = """//div[@class="propertyCard-details"]\
        //a[@class="propertyCard-link"]/@href"""
     
        # Use the requests library to get the whole web page.
        page = requests.get(page_url)

        # Process the html.
        tree = html.fromstring(page.content)
        
        # Create data lists from Xpaths.
        price_pcm = tree.xpath(xp_prices)
        titles = tree.xpath(xp_titles)
        addresses = tree.xpath(xp_addresses)
        # laius is part of the descriptions we are collating together and extracting meaning words and maybe square footage
        laius = tree.xpath(xp_layus)
        addedon = tree.xpath(xp_addedon)
        urlbase = "http://www.rightmove.co.uk"
        weblinks = ["{}{}".format(urlbase, tree.xpath(xp_weblinks)[val]) \
                    for val in range(len(tree.xpath(xp_weblinks)))]
        IDs = [x[-13:-5] for x in weblinks]  
        AlreadIn = [x in self.P_ID for x in IDs]
        ######### obtain the supplementary info on individual pages
        latitude =[]
        longitude = []
        descwords=[]
        sqftage=[]
        firstlisted=[]
        # in what follows we are going to each property pages and extracting additional information
        # we send the url of the property and the search listing description 
        for i in range (0,len(weblinks)):
            #we do not fetch absent pages and properties already in the database
            if weblinks[i] != urlbase  and AlreadIn[i] == False :
                info = self.__get_individual_info(weblinks[i], laius[i])
            else : info = (None, None,[],None,None)
            latitude.append(info[0])
            longitude.append(info[1])
            descwords.append(info[2])
            sqftage.append(info[3])
            firstlisted.append(info[4])
            
       
          
        # Store the data in a temporary pandas DataFrame.
        data = [IDs, price_pcm, titles, addresses,  addedon , weblinks , latitude , longitude , descwords , sqftage , firstlisted, AlreadIn]
       
        temp_df = pd.DataFrame(data)
       
        temp_df = temp_df.transpose()
        temp_df.columns = ["RM_ID","price", "type", "address",  "listing date",'url','latitude','longitude', 'descwords','sqftage','firstlisted', "already in" ]
        
        # Drop empty rows which come from placeholders in the html.
        temp_df = temp_df[temp_df["address"].notnull()]
        # Drop properties already in the database
        temp_df = temp_df[temp_df["already in"]==False]
        # Drop the (already in) column
        temp_df = temp_df.drop(['already in'], axis= 1)
                       
        return temp_df
    

                
    def get_results(self):
            """Returns a pandas DataFrame with all results returned by the search."""

            # Random Page in the available ones
            page = random.randint(0, self.result_pages_count)

            # Create the URL of the specific results page.
            iteration_url = "{}{}{}".format(str(self.url), "&index=", str((page*24)))
            
            # time counter
            start_time=time.time()
            
            # Create a temporary dataframe of the page results.
            temp_df = self.__get_page_results(iteration_url)

            print('number of new results on ',page+1,' : ', len(temp_df))
            # Convert price column to numeric type.
            temp_df.price.replace(regex=True, inplace=True, to_replace=r"\D", value=r"")
            temp_df.price = pd.to_numeric(temp_df.price, errors = 'coerce')

            # Extract postcodes to a separate column.
            temp_df["postcode"] = self.postcode
            # Extract creation/modification date to a separate column.
         
            date_cond =    [temp_df["listing date"].str.contains("today",na=False),
                        temp_df["listing date"].str.contains("yesterday",na=False),
                        (~temp_df["listing date"].str.contains("today",na=False) & ~temp_df["listing date"].str.contains("yesterday",na=False))]
#           print(date_cond)
            date_choices = [ dt.date.today().strftime( '%d/%m/%Y'),
                             (dt.date.today()-dt.timedelta(1)).strftime( '%d/%m/%Y'),
                             temp_df["listing date"].str[-10:]]
                                       
#           print(date_choices)
            temp_df['date'] = np.select(date_cond, date_choices) 
                
            temp_df["date_type"] = temp_df["listing date"].str[:-10]
            temp_df["date_type"] = temp_df["date_type"].str.strip()
        
            # Extract RM property ID
#            temp_df["RM_ID"] = temp_df["url"].str[54:-5]
        
            #######Below we extract underlying information from type
            # Extract number of bedrooms from "type" to a separate column.
            temp_df["number_bedrooms"] = temp_df.type.str.extract(r"\b([\d][\d]?)\b", expand=True)
            temp_df.loc[temp_df["type"].str.contains("studio", case=False), "number_bedrooms"]=0
            temp_df["number_bedrooms"]=temp_df["number_bedrooms"].astype(float)
            # House, flat, detached, semi detached terraced penthouse duplex triplex
            temp_df['flat'] = temp_df.type.str.contains('apartment|flat|plex|maisonette|penthouse')
            temp_df['house'] = ~temp_df.type.str.contains('apartment|flat|plex|maisonette|penthouse|land|plot',na=False)
            temp_df['detached'] = temp_df.type.str.contains("detached") & ~temp_df.type.str.contains("semi",na=False)
            temp_df['semi-d'] = temp_df.type.str.contains('semi')
            temp_df['penthouse'] = temp_df.type.str.contains('penthouse')
            temp_df['duplex'] = temp_df.type.str.contains('plex')
            temp_df['land'] = temp_df.type.str.contains('land|plot')
            temp_df['offplan'] = temp_df.type.str.contains('off-plan')
        
            # Clean up annoying white spaces and newlines in "type" column.
            #for row in range(len(temp_df)):
            #    type_str = temp_df.loc[row, "type"]
            #    clean_str = type_str.strip(" ").strip()
            #    temp_df.loc[row, "type"] = clean_str
            temp_df['type']=temp_df['type'].str.strip()

            # Add column with datetime when the search was run (i.e. now).
            now = dt.datetime.today()
            temp_df["search_date"] = now
        
           # Remove superfluous columns and data
            temp_df = temp_df.drop(['listing date','url'], axis= 1)
            
           # copy data for concateniation and modify descwords to string
            df = temp_df
            
         #   path = "F:\\New folder\\Job Search\\Real Estate Project\\CodeRE\\"
         #   path = path +"results.json"+ PostCodeT + SaleorRent
         #   with open(path, "w+") as output_file:
         #        output_file.write(df.to_json())  
            
            
            temp_df['description']=temp_df['descwords'].apply(', '.join)
            temp_df = temp_df.drop(['descwords'], axis= 1)
            strings =['type', 'address', 'firstlisted', 'postcode', 'date', 'date_type', 'search_date']
            for c in strings:
                  temp_df[c] = temp_df[c].apply(str)

            sqlite_table_columns = ['RM_ID','price','type', 'address',  'latitude', 'longitude', 'sqftage',
                                    'firstlisted','postcode','date', 'date_type','number_bedrooms',
                                    'flat', 'house','detached', 'semi-d','penthouse', 'duplex',  'land', 'offplan',
                                    'search_date','description']
            temp_df= temp_df[sqlite_table_columns]

            # Add to the Sqlite database the partial results
            conn = sqlite3.connect('RM_properties.sqlite')
            cur = conn.cursor()
            
            wildcards = ','.join(['?']* len(temp_df.columns)) # row of ? for each variable
            data = [tuple(x) for x in temp_df.values]

            
            cur.executemany("INSERT INTO %s values(%s)" % ("Properties", wildcards), data)
            elapsed_time= time.time() - start_time
            print('#################')
            print(page+1, ' offload in sqlite successful in ',elapsed_time / 60, ' minutes')
            print('#################')
            conn.commit()
            conn.close()
            
          

            return 'Done'