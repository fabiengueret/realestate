# -*- coding: utf-8 -*-
"""
Created on Wed May 30 18:05:45 2018

@author: Fabien Gueret 4 TerraMollis Ltd.
"""

from lxml import html
#url management library
import requests

# open floorplan
import io
#OCR
import pytesseract
#Regex
import re 
#Pillow image management
from PIL import Image
#database
import sqlite3
import time

regex = r'(?:(?<=\s))(\b\d{1,3}(?:[,.\s]*\d{3})*\b(?!,))(?:(?=\s*[sS]{1}\s*[qQ]{1}.?(uare)?\s*[fF]{1}(ee)?\s*[tT]?))'
sqftages=[]

file= "t4.png"
path = 'F:/New folder/Job Search/Real Estate Project/CodeRE/'
flrpln = Image.open(file)
              
img = flrpln
width,height = img.size
left = 0
top = 5*height/6
right = width 
bottom = height
cropped_img= img.crop((left,top,right,bottom))
cropped_img=cropped_img.resize((width*2, height//6*2),Image.ANTIALIAS)


# the OCR proper using neural networks
#textA = pytesseract.image_to_string(img, config='--psm 12 --oem 2 --user-words')
#print('fullimage',textA)
textB= pytesseract.image_to_string(cropped_img, config='--psm 12 --oem 2 --user-words')
print('croppedimage',textB)

# parse the text find square footage or square metrage     
tuplessqftages =re.findall(regex,textB,re.IGNORECASE)
              
sqftages=[i[0] for i in tuplessqftages]
#  print(i, 'Floorplan Footage', sqftages)
f=[float(i.replace(',',''))for i in sqftages]
print(f)