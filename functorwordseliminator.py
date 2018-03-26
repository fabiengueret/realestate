# -*- coding: utf-8 -*-
"""
Created on Mon Mar 26 12:29:12 2018

@author: Fabien Gueret 4 TerraMollis Ltd.

This function take a list of words (list of strings) and eliminate functional 
words that have a grammatical use but do not content information (content word)

"""



def functor_words_eliminator (word_list):
    
    filename = 'functors.txt'    
    f= open(filename,'r')
    data = f.read().replace('\n','')
    fw = data.split()
    fw=  [item.strip().lower() for item in fw]
    original_list = word_list
    for word in fw:
        if word in word_list : original_list.remove(word)
    return original_list        
 
    
########## Testing
original_word_list = [ 'parking', 'you', 'some']    
list= functor_words_eli
