
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 18 13:31:09 2020
@author: emapr and aalarcon
"""

import pandas as pd
import numpy as np

from PTDF_check import PTDF_check
from itertools import combinations
from operator import add
import ast

#%% Case data

Setpoint_ini = pd.read_excel(open('Setpoint_nodes.xlsx', 'rb'),sheet_name='Nodes33lines+0.1',index_col=0)

Setpoint = pd.DataFrame(columns = ['Time_target','Setpoint_P'])
Setpoint.set_index('Time_target',inplace=True)

setpoint = []
for t in Setpoint_ini.index:
    setpoint = []
    for n in Setpoint_ini.columns:
        setpoint.append(Setpoint_ini.at[t,n])
    Setpoint.at[t,'Setpoint_P'] = setpoint

Setpoint1 = Setpoint


# Initial Social Welfare and Flexibility Procurement Cost
Social_Welfare = 0
Flex_procurement = 0

# Index for nodes
bus = pd.read_excel(open('network33bus.xlsx', 'rb'),sheet_name='Bus',index_col=0)
nodes = list(bus.index)

# Upload bids
                                                         #'T1_best','T1_worst','T1_random'
all_bids = pd.read_excel(open('Bids_energy_33.xlsx','rb'),sheet_name='T1_random',index_col=0)

# Create empty dataframes to contain the bids that were not matched (order book)
orderbook_offer = pd.DataFrame(columns = ['ID','Bus','Direction','Quantity','Price','Time_target','Time_stamp','Block'])
orderbook_offer.set_index('ID',inplace=True)
orderbook_request = pd.DataFrame(columns = ['ID','Bus','Direction','Quantity','Price','Time_target','Time_stamp','Temporary']) 
orderbook_request.set_index('ID',inplace=True)
# Create empty dataframes to contain the bids that were not temporary matched
orderbook_temporary = pd.DataFrame(columns = ['Offer','Offer Bus','Offer Block','Offer Price','Offer Time_stamp','Request','Request Bus','Request Time_stamp','Direction','Quantity','Matching Price','Time_target'])

#%% Function to match a new offer
def continuous_clearing(new_bid, orderbook_request, orderbook_offer, orderbook_temporary, Setpoint, Social_Welfare, Flex_procurement):
    
    matches = pd.DataFrame(columns = ['Offer','Offer Bus','Offer Block','Request','Request Bus','Direction','Quantity','Matching Price','Time_target','Social Welfare'])

#%% Function to match an offer
    def matching(bid_type, Setpoint, bid, orderbook_request, orderbook_offer, orderbook_temporary,  matches, Social_Welfare, Flex_procurement):
        
        #bid_type: new or old
        
        epsilon = 0.00001 # Tolerance
        status = 'no match' # Marker to identify if there was a match with unconditional requests or not (if so, the order book should be checked for new matches)
        flag = 'NaN' # initialize the output flag 
        
        time_target = bid.at['Time_target']
        Setpoint_t = Setpoint.at[time_target,'Setpoint_P']
        direction = bid.at['Direction']
        temporary = 'No'
        
        if bid_type == 'new':
            bid_nature = bid.at['Bid'] # Offer or request
        elif bid_type == 'old':
            bid_nature = 'Offer' 
            
        if bid_nature == 'Offer':
            offer_bus = nodes.index(bid.at['Bus'])
            offer_price = bid.at['Price']
            offer_quantity = bid.at['Quantity']
            offer_index = bid.name
            offer_time_stamp = bid.at['Time_stamp']
            offer_block = bid.at['Block']
            
            # Make sure that there are requests left to be matched
            if orderbook_request[(orderbook_request.Direction == direction) & (orderbook_request.Time_target == time_target)].empty:
                flag = 'Empty orderbook'
                orderbook_offer.loc[offer_index]=[nodes[offer_bus],direction,offer_quantity,offer_price,time_target,offer_time_stamp,offer_block]
                orderbook_offer.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,True,True], inplace=True) # Sort by price and by time submission and gather by time target
                return Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag, Social_Welfare, Flex_procurement
            
            # Else, list of requests to look into
            orderbook = orderbook_request
            
        elif bid_nature == 'Request':
            request_bus = nodes.index(bid.at['Bus'])
            request_price = bid.at['Price']
            request_quantity = bid.at['Quantity']
            request_index = bid.name
            request_time_stamp = bid.at['Time_stamp']
            
            # Make sure that there are offers left to be matched
            if orderbook_offer[(orderbook_offer.Direction == direction) & (orderbook_offer.Time_target == time_target)].empty:
                flag = 'Empty orderbook'
                orderbook_request.loc[request_index]=[nodes[request_bus],direction,request_quantity,request_price,time_target,request_time_stamp,temporary]
                orderbook_request.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,False,True], inplace=True) # Sort by price and by time submission and gather by time target
                return Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag, Social_Welfare, Flex_procurement
            
            # Else, list of requests to look into
            orderbook = orderbook_offer
    
        # Check matching with all the requests (in the same direction)
        for ID in orderbook.index:
            
            if orderbook.at[ID,'Direction'] == direction and orderbook.at[ID,'Time_target'] == time_target:
                print ('---There is a possible match of {} with {}'.format(bid.name,ID))
                
                if bid_nature == 'Offer':
                    if ID not in orderbook_request.index:
                        continue
                    
                    request_price = orderbook_request.at[ID,'Price']
                    request_index = ID
                elif bid_nature == 'Request':
                    offer_price = orderbook_offer.at[ID,'Price']
                    offer_index = ID
            
                # Make sure that the prices are matching
                if offer_price <= request_price:
                    print ('Prices are matching')
                    if bid_nature == 'Offer':
                        request_bus = nodes.index(orderbook_request.at[ID,'Bus'])
                        request_index = ID
                        Offered = offer_quantity
                        Requested = orderbook_request.at[ID,'Quantity']
                        request_time_stamp = orderbook_request.at[ID,'Time_stamp']
                    elif bid_nature == 'Request':
                        offer_bus = nodes.index(orderbook_offer.at[ID,'Bus'])
                        offer_index = ID
                        Offered = orderbook_offer.at[ID,'Quantity']
                        Requested = request_quantity
                        offer_time_stamp = orderbook_offer.at[ID,'Time_stamp']
                        offer_block = orderbook_offer.at[ID,'Block']
                        
                    Quantity = min(Offered,Requested) # Initially, the maximum quantity that can be exchanged is the minimum of the quantities of the bids
                    
                    if request_bus != offer_bus: # Network check, only if offer and request are not located at the same bus
                        # Check for this match only
                        Quantity = PTDF_check(Setpoint_t,Quantity,offer_bus,request_bus,direction) # Returns the maximum quantity that can be exchanged without leading to congestions
                        
                    print ('Quantity exchanged',Quantity)
                    if Quantity >= 0.01: # Line constraints are respected
                        print ('THERE IS A MATCH')
                        flag = 'Match'
                        # The older bid sets the price
                        if request_time_stamp < offer_time_stamp:
                            matching_price = request_price
                        elif request_time_stamp > offer_time_stamp:
                            matching_price = offer_price
                        SW_single = (request_price-offer_price)*Quantity
                        # Flex_procurement += matching_price*Quantity
                        matches = matches.append({'Offer':offer_index,'Offer Bus':nodes[offer_bus],'Offer Block':offer_block,'Request':request_index,'Request Bus':nodes[request_bus],'Matching Price':matching_price,'Direction':direction,'Quantity':Quantity, 'Time_target':time_target, 'Social Welfare':SW_single},ignore_index=True)               

                        # Calculate the corresponding changes in the Setpoint
                        Delta = [0] * len(Setpoint_t)
                        if direction == 'Up':
                            Delta[offer_bus]+=Quantity
                            Delta[request_bus]-=Quantity
                        elif direction == 'Down':
                            Delta[offer_bus]-=Quantity
                            Delta[request_bus]+=Quantity
                            
                        # Modify the Setpoint and update the status marker
                        Setpoint.at[time_target,'Setpoint_P'] = list(map(add,Setpoint_t,Delta))
                        status = 'match'
                                                       
#-----------------------#Check if the new bid is a block bid
                        if offer_block != 'No':
                            flag = 'Temporary match'
                            status = 'Temporary match'
                            print ('The offer is a block bid')
                          # Check if any part of the BB has been already matched with the same request  
                            a =0
                            for Offer in orderbook_temporary.index:      
                                if orderbook_temporary.at[Offer,'Offer'] == offer_index and orderbook_temporary.at[Offer,'Request'] == request_index:
                                    print ('There is a match with this bid already')
                                    matches = matches.drop([matches.shape[0]-1], axis=0) # Remove the match
                                    a = 1
                                    break

                            if a ==1: # Continue with the next bid
                                continue
                            
                          # Update quantities of both offer and request 
                            if bid_nature == 'Offer': 
                                offer_quantity = Offered - Quantity # Calculate the quantity matched #OFFERED=BID.QUANTITY
                                orderbook_request.at[ID,'Quantity'] = Requested # Leave the quantity as it is in the orderbook
                                orderbook_request.at[ID,'Temporary'] = 'Yes' # Mark it as temporary
                                if offer_quantity > epsilon: # If the offer was not completely matched after trying all requests, update and order the book
                                    orderbook_temporary = orderbook_temporary.append({'Offer':offer_index,'Offer Bus':nodes[offer_bus],'Offer Block':offer_block,'Offer Price':offer_price,'Offer Time_stamp':offer_time_stamp,'Request':request_index,'Request Bus':nodes[request_bus],'Request Time_stamp':request_time_stamp,'Direction':direction,'Quantity':Quantity,'Matching Price':matching_price, 'Time_target':time_target},ignore_index=True)
                                    orderbook_temporary.sort_values(by=['Time_target','Matching Price'], ascending=[True,True], inplace=True) # Sort by price and by time submission and gather by time target
                                    orderbook_offer.loc[offer_index]=[nodes[offer_bus],direction,offer_quantity,offer_price,time_target,offer_time_stamp,offer_block]
                                    orderbook_offer.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,True,True], inplace=True) # Sort by price and by time submission and gather by time target
                                    matches = matches.drop([matches.shape[0]-1], axis=0) # Remove the match
                                    
                                    print ('The offer was not completely matched after trying all requests')                                   
                                    
                                if offer_quantity < epsilon: # If the part of the offer was completely matched
                                    print ('Complete match of these part of the BB')
                                    if bid_type == 'old': # In the case of checking the bids in the orderbook, the corresponding row must be dropped
                                        orderbook_offer = orderbook_offer.drop([offer_index], axis=0)
                                        
                                    # Asses the match 
                                    if (orderbook_temporary.empty) or (offer_block not in orderbook_temporary.values) or (offer_block in orderbook_offer.values):
                                        print ('1. The match of the whole BB is NOT completed')
                                        # If the temporary orderbook is empty, the other part of the BB is not on it or any part of the BB is still in the offer orderbook, consider it as a 'temporary match'
                                        matches = matches.drop([matches.shape[0]-1], axis=0) # Remove the match
                                        
                                        # Include the temporary match in the temporary orderbook             
                                        orderbook_temporary = orderbook_temporary.append({'Offer':offer_index,'Offer Bus':nodes[offer_bus],'Offer Block':offer_block,'Offer Price':offer_price,'Offer Time_stamp':offer_time_stamp,'Request':request_index,'Request Bus':nodes[request_bus],'Request Time_stamp':request_time_stamp,'Direction':direction,'Quantity':Quantity,'Matching Price':matching_price, 'Time_target':time_target},ignore_index=True)
                                        orderbook_temporary.sort_values(by=['Time_target','Matching Price'], ascending=[True,True], inplace=True) # Sort by price and by time submission and gather by time target
                                        if offer_index in orderbook_offer.index: # If the bid is in the orderbook, remove it
                                            orderbook_offer = orderbook_offer.drop([offer_index], axis=0)
 
                                    else: 
                                        print('2. The match of the whole BB is completed')            
                                        flag = 'Match'
                                        # Update the request in the request orderbook
                                        orderbook_request.at[request_index,'Quantity'] -= Quantity
                                        orderbook_request.at[request_index,'Temporary'] = 'No'           
                                        if orderbook_request.at[request_index,'Quantity'] < epsilon: # If the request is completely matched, remove it
                                            orderbook_request = orderbook_request.drop([request_index], axis=0)
        
                                        # Check the bids involves in the complete match of the BB  
                                        for Offer in orderbook_temporary.index:
                                            if orderbook_temporary.at[Offer,'Offer Block'] == offer_block: 
                                                # SW calculation
                                                O = orderbook_temporary.at[Offer,'Offer']
                                                R = orderbook_temporary.at[Offer,'Request']
                                                PO = all_bids.at[O,'Price']
                                                PR = all_bids.at[R,'Price']
                                                SW_single = orderbook_temporary.at[Offer,'Quantity']*(PR-PO)
                                                
                                                matches = matches.append({'Offer':orderbook_temporary.at[Offer,'Offer'],'Offer Bus':orderbook_temporary.at[Offer,'Offer Bus'],'Offer Block':orderbook_temporary.at[Offer,'Offer Block'],'Request':orderbook_temporary.at[Offer,'Request'],'Request Bus':orderbook_temporary.at[Offer,'Request Bus'],'Matching Price':orderbook_temporary.at[Offer,'Matching Price'],'Direction':orderbook_temporary.at[Offer,'Direction'],'Quantity':orderbook_temporary.at[Offer,'Quantity'], 'Time_target':orderbook_temporary.at[Offer,'Time_target'],'Social Welfare':SW_single},ignore_index=True)
                                                # Identify the requests matched with the other parts of the BB and update the orderbook 
                                                request_ID = orderbook_temporary.at[Offer,'Request']
                                                if request_ID in orderbook_request.index:
                                                    orderbook_request.at[request_ID,'Quantity'] -= orderbook_temporary.at[Offer,'Quantity']
                                                    orderbook_request.at[request_ID,'Temporary'] = 'No'
                                                    if orderbook_request.at[request_ID,'Quantity'] < epsilon: # If the request is completely matched, drop it
                                                        orderbook_request = orderbook_request.drop([request_ID], axis=0) 
                                                # Remove the temporary match
                                                orderbook_temporary = orderbook_temporary.drop([Offer], axis=0)
                                   
                                    return Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag, Social_Welfare, Flex_procurement
                                  
                                   
                            elif bid_nature == 'Request': # Add the request in the orderbook marked as temporary and update the offer orderbook
                                temporary = 'Yes'
                                print ('It is a request')
                                orderbook_request.loc[request_index] = [nodes[request_bus],direction,Requested,request_price,time_target,request_time_stamp,temporary]
                                orderbook_request.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,False,True], inplace=True) # Sort by price and by time submission and gather by time target
                                
                                orderbook_offer.at[ID,'Quantity'] = Offered - Quantity
                                
                                if orderbook_offer.at[ID,'Quantity'] < epsilon: # If the offer was completely matched
                                    orderbook_offer = orderbook_offer.drop([ID], axis=0) # Remove it from the orderbook
                                    
                                    # Asses the match 
                                    if (orderbook_temporary.empty) or (offer_block not in orderbook_temporary.values) or (offer_block in orderbook_offer.values):
                                        # The match of the whole BB is NOT completed
                                        print('The match of the whole BB is NOT compelted')
                                        flag = 'Temporary match'
                                        status = 'Temporary match'
                                        for match in matches.index:
                                            if matches.at[match,'Offer Block'] == offer_block:
                                                matches = matches.drop([match]) # It is not considered as match
                                        # Include the temporary match in the temporary orderbook             
                                        orderbook_temporary = orderbook_temporary.append({'Offer':offer_index,'Offer Bus':nodes[offer_bus],'Offer Block':offer_block,'Offer Price':offer_price,'Offer Time_stamp':offer_time_stamp,'Request':request_index,'Request Bus':nodes[request_bus],'Request Time_stamp':request_time_stamp,'Direction':direction,'Quantity':Quantity,'Matching Price':matching_price, 'Time_target':time_target},ignore_index=True)
                                        orderbook_temporary.sort_values(by=['Time_target','Matching Price'], ascending=[True,True], inplace=True) # Sort by price and by time submission and gather by time target
                                        
                                    else: # The match of the whole BB is completed              
                                        flag = 'Match'
                                        print('The match of the whole BB IS compelted')
                                        request_quantity = Requested - Quantity
                                        # Update the request in the request orderbook
                                        orderbook_request.at[request_index,'Quantity'] -= Quantity
                                        orderbook_request.at[request_index,'Temporary'] = 'No'           
                                        if orderbook_request.at[request_index,'Quantity'] < epsilon: # If the request is completely matched, remove it
                                            orderbook_request = orderbook_request.drop([request_index], axis=0)
        
                                        # Check the bids involves in the complete match of the BB  
                                        for Offer in orderbook_temporary.index:
                                         
                                            if orderbook_temporary.at[Offer,'Offer Block'] == offer_block: 
                                                
                                                # SW calculation
                                                O = orderbook_temporary.at[Offer,'Offer']
                                                R = orderbook_temporary.at[Offer,'Request']
                                                PO = all_bids.at[O,'Price']
                                                PR = all_bids.at[R,'Price']
                                                SW_single = orderbook_temporary.at[Offer,'Quantity']*(PR-PO)
                                                
                                                matches = matches.append({'Offer':orderbook_temporary.at[Offer,'Offer'],'Offer Bus':orderbook_temporary.at[Offer,'Offer Bus'],'Offer Block':orderbook_temporary.at[Offer,'Offer Block'],'Request':orderbook_temporary.at[Offer,'Request'],'Request Bus':orderbook_temporary.at[Offer,'Request Bus'],'Matching Price':orderbook_temporary.at[Offer,'Matching Price'],'Direction':orderbook_temporary.at[Offer,'Direction'],'Quantity':orderbook_temporary.at[Offer,'Quantity'], 'Time_target':orderbook_temporary.at[Offer,'Time_target'],'Social Welfare':SW_single},ignore_index=True)
                                                
                                                # Identify the requests matched with the other parts of the BB and update the orderbook 
                                                request_ID = orderbook_temporary.at[Offer,'Request']
                                                
                                                if request_ID in orderbook_request.index:
                                                                     
                                                    orderbook_request.at[request_ID,'Quantity'] -= orderbook_temporary.at[Offer,'Quantity']
                                                    orderbook_request.at[request_ID,'Temporary'] = 'No'
                                                    if orderbook_request.at[request_ID,'Quantity'] < epsilon: # If the request is completely matched, drop it
                                                        orderbook_request = orderbook_request.drop([request_ID], axis=0) 
                                                    # Remove the temporary match
                                                orderbook_temporary = orderbook_temporary.drop([Offer], axis=0)
                                    
                                else:
                                    orderbook_temporary = orderbook_temporary.append({'Offer':offer_index,'Offer Bus':nodes[offer_bus],'Offer Block':offer_block,'Offer Price':offer_price,'Offer Time_stamp':offer_time_stamp,'Request':request_index,'Request Bus':nodes[request_bus],'Request Time_stamp':request_time_stamp,'Direction':direction,'Quantity':Quantity,'Matching Price':matching_price, 'Time_target':time_target},ignore_index=True)
                                    orderbook_temporary.sort_values(by=['Time_target','Matching Price'], ascending=[True,True], inplace=True) # Sort by price and by time submission and gather by time target
                                    for match in matches.index:
                                        if matches.at[match,'Offer Block'] == offer_block:
                                            matches = matches.drop([match])

                        # If the bid it is not a BB
                        else:
                            print ('No BB involved')
                            
                            Social_Welfare += (request_price-offer_price)*Quantity
                            # Update quantities of these offer and request
                            if bid_nature == 'Offer':
                                offer_quantity = Offered - Quantity
                                orderbook_request.at[ID,'Quantity'] = Requested - Quantity

                                if orderbook_request.at[ID,'Temporary'] == 'Yes': # Check if the request match has a previous temporary match with a BB
                                    # Identify the matches that can be broken
                                    request_broken = orderbook_temporary.loc[orderbook_temporary['Request']==ID]
                                    
                                    for i in request_broken.index: # Update the offer orderbook and asses if the temporary match is broken
                                        offer_broken = request_broken.at[i,'Offer']
                                        if orderbook_request.at[ID,'Quantity'] < request_broken.at[i,'Quantity']: # If the quantity is not enough for the temporary match to exist
                                            print ('Cancelled match of {}'.format(offer_broken))
                                            if offer_broken in orderbook_offer.index: # If the offer is already in the orderbook, update it
                                                orderbook_offer.at[offer_broken,'Quantity'] += orderbook_temporary.at[i,'Quantity']
                                                
                                            else: # If not, add it
                                                orderbook_offer.loc[offer_broken]=[orderbook_temporary.at[i,'Offer Bus'],orderbook_temporary.at[i,'Direction'],orderbook_temporary.at[i,'Quantity'],orderbook_temporary.at[i,'Offer Price'],orderbook_temporary.at[i,'Time_target'],orderbook_temporary.at[i,'Offer Time_stamp'], orderbook_temporary.at[i,'Offer Block']]
                                                orderbook_offer.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,True,True], inplace=True) # Sort by price and by time submission and gather by time target     
                                                                               
                                            orderbook_temporary = orderbook_temporary.drop([i], axis=0) # Remove the temporary match  
                                            # Try to match the calcelled offer again
                                            print ('Try to match the cancelled offer again')
                                            Setpoint, status1, orderbook_request, orderbook_offer, orderbook_temporary, matches, flag1, Social_Welfare, Flex_procurement = matching('old', Setpoint, orderbook_offer.loc[offer_broken], orderbook_request, orderbook_offer, orderbook_temporary,  matches, Social_Welfare, Flex_procurement)
                                
                                if ID in orderbook_request.index:
                                    if orderbook_request.at[ID,'Quantity'] < epsilon: # If the request was completely matched
                                        orderbook_request = orderbook_request.drop([ID], axis=0)

                                if offer_quantity < epsilon: # If the offer was completely matched
                                    print ('Offer completely matched')
                                    flag = 'Match'
                                    status = 'Match'
                                    if bid_type == 'old': # In the case of checking the bids in the order book, the corresponding row must be dropped
                                        orderbook_offer = orderbook_offer.drop([offer_index], axis=0)
                                    return Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag, Social_Welfare, Flex_procurement
                                
                            elif bid_nature == 'Request':
                                
                                request_quantity = Requested - Quantity
                                orderbook_offer.at[ID,'Quantity'] = Offered - Quantity
                                print ('Request quantity remaining',request_quantity)
              
                                if request_index in orderbook_request.index:
                                    if orderbook_request.at[request_index,'Temporary'] == 'Yes': # Check if the request match has a previous temporary match with a BB
                                        print ('The request was temporary matched')    
                                        orderbook_request.loc[request_index]=[nodes[request_bus],direction,request_quantity,request_price,time_target,request_time_stamp,temporary]
                                        orderbook_request.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,False,True], inplace=True) # Sort by price and by time submission and gather by time target
                                        if orderbook_request.at[request_index,'Quantity'] < epsilon:
                                            orderbook_request = orderbook_request.drop([request_index], axis=0)
   
                                        # Identify the matches that can be broken 
                                        request_broken = orderbook_temporary.loc[orderbook_temporary['Request']==request_index]
                                        
                                        for i in request_broken.index: # Update the offer orderbook and asses if the temporary match is broken
                                            offer_broken = request_broken.at[i,'Offer']
                                            if request_quantity < request_broken.at[i,'Quantity']: # If the quantity is not enough for the temporary match to exist
                                                print ('Cancelled match of {}'.format(offer_broken))
                                                if offer_broken in orderbook_offer.index: # If the offer is already in the orderbook, update it
                                                    orderbook_offer.at[offer_broken,'Quantity'] += orderbook_temporary.at[i,'Quantity']
                                                    
                                                else: # If not, add it                                                                                 
                                                    orderbook_offer.loc[offer_broken]=[orderbook_temporary.at[i,'Offer Bus'],orderbook_temporary.at[i,'Direction'],orderbook_temporary.at[i,'Quantity'],orderbook_temporary.at[i,'Offer Price'],orderbook_temporary.at[i,'Time_target'],orderbook_temporary.at[i,'Offer Time_stamp'], orderbook_temporary.at[i,'Offer Block']]
                                                    orderbook_offer.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,True,True], inplace=True) # Sort by price and by time submission and gather by time target     
                                                                                   
                                                orderbook_temporary = orderbook_temporary.drop([i], axis=0) # Remove the temporary match  
                                                # Try to match the calcelled offer again
                                                print ('Try to match the cancelled offer again')
                                                Setpoint, status1, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag1, Social_Welfare, Flex_procurement = matching('old', Setpoint, orderbook_offer.loc[offer_broken], orderbook_request, orderbook_offer, orderbook_temporary,  matches, Social_Welfare, Flex_procurement)
                              
                                if orderbook_offer.at[ID,'Quantity'] < epsilon: # If the offer was completely matched
                                    orderbook_offer = orderbook_offer.drop([ID], axis=0)
    
                                if request_quantity < epsilon: # If the request was completely matched
                                    return Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag, Social_Welfare, Flex_procurement
                    
                    else:
                        flag = 'No match (congestions)'
                        print ('No match (congestions)')
                else:
                    flag = 'No match (price)'
                    break
        
        if bid_nature == 'Offer':
            if offer_quantity > epsilon: # If the offer was not completely matched after trying all requests, update and order the book
                orderbook_offer.loc[offer_index]=[nodes[offer_bus],direction,offer_quantity,offer_price,time_target,offer_time_stamp,offer_block]
                orderbook_offer.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,True,True], inplace=True) # Sort by price and by time submission and gather by time target
                
        elif bid_nature == 'Request': 
            if request_quantity > epsilon: # If the request was not completely matched after trying all offers, update and order the book
                orderbook_request.loc[request_index]=[nodes[request_bus],direction,request_quantity,request_price,time_target,request_time_stamp,temporary]
                orderbook_request.sort_values(by=['Time_target','Price','Time_stamp'], ascending=[True,False,True], inplace=True) # Sort by price and by time submission and gather by time target
                
        return Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary, matches, flag, Social_Welfare, Flex_procurement

#%% Check the power flows using PTDFs each time a bid is added

    Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag, Social_Welfare, Flex_procurement = matching('new', Setpoint, new_bid, orderbook_request, orderbook_offer, orderbook_temporary,  matches, Social_Welfare, Flex_procurement)
    
    # If there was at least a match with an unconditional request, try again on older bids
    if status == 'match' and not orderbook_offer[(orderbook_offer.Direction == new_bid.at['Direction']) & (orderbook_offer.Time_target == new_bid.at['Time_target'])].empty:
        general_status = 'match'
        while general_status == 'match': # As long as previous offers are matching with unconditional requests, check for matches
            general_status = 'no match'
            for O in orderbook_offer.index:
                old_offer = orderbook_offer.loc[O].copy()               
                if old_offer['Time_target'] == new_bid.at['Time_target']:
                    if new_bid.name not in orderbook_offer.index:
                        break
                    else:
                        Setpoint, status, orderbook_request, orderbook_offer, orderbook_temporary,  matches, flag_tp, Social_Welfare, Flex_procurement = matching('old',Setpoint, old_offer, orderbook_request, orderbook_offer, orderbook_temporary,  matches, Social_Welfare, Flex_procurement)
                    if status == 'match':
                        general_status = 'match'
    return matches, orderbook_request, orderbook_offer, orderbook_temporary,  Setpoint, flag, Social_Welfare, Flex_procurement

All_Matches = []
market_result = pd.DataFrame(columns = ['Offer','Offer Bus','Offer Block','Request','Request Bus','Direction','Quantity','Matching Price','Time_target','Social Welfare'])
energy_volume = pd.DataFrame(columns = ['Time_target','Energy_volume'])
energy_volume.set_index('Time_target',inplace=True)
energy_volume_up = pd.DataFrame(columns = ['Time_target','Energy_volume'])
energy_volume_up.set_index('Time_target',inplace=True)
energy_volume_down = pd.DataFrame(columns = ['Time_target','Energy_volume'])
energy_volume_down.set_index('Time_target',inplace=True)

SocialW = pd.DataFrame(columns = ['Time_target','Social Welfare'])
SocialW.set_index('Time_target',inplace=True)
for t in Setpoint.index:
    SocialW.at[t,'Social Welfare'] = 0

n=0
for b in all_bids.index:
    
    n+=1
    print ('')
    print('---------------- Betting round nb {} -----------------'.format(n))
    print ('')
    print('New bid: ({}, {}, {}, {}, {}, {}, {}, Block:{})'.format(b,all_bids.at[b,'Bid'],all_bids.at[b,'Bus'],all_bids.at[b,'Direction'],all_bids.at[b,'Quantity'],all_bids.at[b,'Price'],all_bids.at[b,'Time_target'],all_bids.at[b,'Block']))
    new_bid = all_bids.loc[b]
    matches, orderbook_request, orderbook_offer, orderbook_temporary,  Setpoint, flag, Social_Welfare, Flex_procurement = continuous_clearing(new_bid, orderbook_request, orderbook_offer, orderbook_temporary,  Setpoint, Social_Welfare, Flex_procurement)
    All_Matches.append([flag,matches])
    
    if not matches.empty:
        print('HOLAAAAAAAAAAAA')
        for i in matches.index:
            market_result = market_result.append({'Offer':matches.at[i,'Offer'],'Offer Bus':matches.at[i,'Offer Bus'],'Offer Block':matches.at[i,'Offer Block'],'Request':matches.at[i,'Request'],'Request Bus':matches.at[i,'Request Bus'],'Direction':matches.at[i,'Direction'],'Quantity':matches.at[i,'Quantity'],'Matching Price':matches.at[i,'Matching Price'],'Time_target':matches.at[i,'Time_target'],'Social Welfare':matches.at[i,'Social Welfare']},ignore_index=True)
            market_result.sort_values(by=['Time_target'],ascending=[True], inplace=True)
            t = matches.at[i,'Time_target']
            SocialW.at[t,'Social Welfare'] += matches.at[i,'Social Welfare']
            
    print ('SOCIAL WELFARE', Social_Welfare)
    print ('')
    print ('State:',flag)
    print ('REQUESTS')
    print (orderbook_request.iloc[:,[1,2,3,4,6]])
    print ('OFFERS')
    print (orderbook_offer.iloc[:,[1,2,3,4,6]]) 
    print ('TEMPORARY')
    print (orderbook_temporary.iloc[:,[0,2,5,9]]) 
    print ('MATCH')
    print (matches.iloc[:,[0,3,6,7]])
       
print ('Market Result',market_result)
SocWel = 0

total_volume = 0
for t in Setpoint.index:
    vol = 0
    vol_up = 0
    vol_down = 0
    for i in market_result.index:
        if market_result.at[i,'Time_target'] == t:
            vol += market_result.at[i,'Quantity']
            if market_result.at[i,'Direction'] == 'Up':
                vol_up += market_result.at[i,'Quantity']
            else:
                vol_down += market_result.at[i,'Quantity']
    total_volume += vol
    energy_volume.at[t,'Energy_volume'] = vol
    energy_volume_up.at[t,'Energy_volume'] = vol_up
    energy_volume_down.at[t,'Energy_volume'] = vol_down
    SocWel += SocialW.at[t,'Social Welfare']
    
print (energy_volume)

print ('Total Social Welfare', SocWel)
print ('Total Volume',total_volume)

requests_accepted = pd.DataFrame(columns = ['Time_target','Direction','Quantity','Price','ID','Bus','Time_stamp'])
requests_accepted_up = pd.DataFrame(columns = ['Time_target','Direction','Quantity','Price','ID','Bus','Time_stamp'])
requests_accepted_down = pd.DataFrame(columns = ['Time_target','Direction','Quantity','Price','ID','Bus','Time_stamp'])

offers_accepted = pd.DataFrame(columns = ['Time_target','Direction','Quantity','Price','ID','Bus','Time_stamp','Block'])
offers_accepted_up = pd.DataFrame(columns = ['Time_target','Direction','Quantity','Price','ID','Bus','Time_stamp','Block'])
offers_accepted_down = pd.DataFrame(columns = ['Time_target','Direction','Quantity','Price','ID','Bus','Time_stamp','Block'])

volume_up = 0
for matches in market_result.index:
    offer = market_result.at[matches,'Offer']
    offers_accepted = offers_accepted.append({'Time_target':all_bids.at[offer,'Time_target'], 'Direction':all_bids.at[offer,'Direction'], 'Quantity':market_result.at[matches,'Quantity'], 'Price':all_bids.at[offer,'Price'], 'ID':offer, 'Bus':all_bids.at[offer,'Bus'], 'Time_stamp':all_bids.at[offer,'Time_stamp'], 'Block':all_bids.at[offer,'Block']},ignore_index=True)                                        
    request = market_result.at[matches,'Request']
    requests_accepted = requests_accepted.append({'Time_target':all_bids.at[request,'Time_target'], 'Direction':all_bids.at[request,'Direction'], 'Quantity':market_result.at[matches,'Quantity'], 'Price':all_bids.at[request,'Price'], 'ID':request, 'Bus':all_bids.at[request,'Bus'], 'Time_stamp':all_bids.at[request,'Time_stamp'], 'Block':all_bids.at[request,'Block']},ignore_index=True)
 
    if market_result.at[matches,'Direction'] == 'Up':
        offers_accepted_up = offers_accepted_up.append({'Time_target':all_bids.at[offer,'Time_target'], 'Direction':all_bids.at[offer,'Direction'], 'Quantity':market_result.at[matches,'Quantity'], 'Price':all_bids.at[offer,'Price'], 'ID':offer, 'Bus':all_bids.at[offer,'Bus'], 'Time_stamp':all_bids.at[offer,'Time_stamp'], 'Block':all_bids.at[offer,'Block']},ignore_index=True)                                        
        requests_accepted_up = requests_accepted_up.append({'Time_target':all_bids.at[request,'Time_target'], 'Direction':all_bids.at[request,'Direction'], 'Quantity':market_result.at[matches,'Quantity'], 'Price':all_bids.at[request,'Price'], 'ID':request, 'Bus':all_bids.at[request,'Bus'], 'Time_stamp':all_bids.at[request,'Time_stamp'], 'Block':all_bids.at[request,'Block']},ignore_index=True)
 
    else:
        offers_accepted_down = offers_accepted_down.append({'Time_target':all_bids.at[offer,'Time_target'], 'Direction':all_bids.at[offer,'Direction'], 'Quantity':market_result.at[matches,'Quantity'], 'Price':all_bids.at[offer,'Price'], 'ID':offer, 'Bus':all_bids.at[offer,'Bus'], 'Time_stamp':all_bids.at[offer,'Time_stamp'], 'Block':all_bids.at[offer,'Block']},ignore_index=True)                                        
        requests_accepted_down = requests_accepted_down.append({'Time_target':all_bids.at[request,'Time_target'], 'Direction':all_bids.at[request,'Direction'], 'Quantity':market_result.at[matches,'Quantity'], 'Price':all_bids.at[request,'Price'], 'ID':request, 'Bus':all_bids.at[request,'Bus'], 'Time_stamp':all_bids.at[request,'Time_stamp'], 'Block':all_bids.at[request,'Block']},ignore_index=True)


    
    
    
    
    
    
    
    
    
    
    
    