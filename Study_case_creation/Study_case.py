
# -*- coding: utf-8 -*-
"""
Created on May 2021

@author: aalarcon
"""

from pyomo.opt import SolverStatus, TerminationCondition
import pyomo.environ as pyo
import pyomo.gdp as gdp

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ast

import random
import datetime

# Initial Setpoint
Setpoint = pd.read_excel(open('Setpoint_initial.xlsx', 'rb'),sheet_name='Initial',index_col=0) # Baseline injections at each nodes (negative for retrieval)

# Index for nodes
bus = pd.read_excel(open('network33bus.xlsx','rb'),sheet_name='Bus',index_col=0)
nodes = list(bus.index)

# Index for branches
branch= pd.read_excel(open('network33bus.xlsx','rb'),sheet_name='Branch',index_col=0)
lines = list(branch.index)

branch['B'] = 1/branch['X']
n_ref = 'n1'


#%% Optimization problem to identify the flexible requests to make the initial setpoint feasible
def flex_req():
    
    m = pyo.ConcreteModel()
    
    # Sets creation
    m.T = pyo.Set(initialize = Setpoint.index, doc='Time_periods')
    m.N = pyo.Set(initialize = Setpoint.columns, doc = 'Nodes')
    m.L = pyo.Set(initialize = lines)
    
    # variables
    m.slack_up = pyo.Var(m.T,m.N, domain=pyo.NonNegativeReals)
    m.slack_down = pyo.Var(m.T,m.N, domain=pyo.NonNegativeReals)
    m.theta = pyo.Var(m.N,m.T, bounds=(-1.5, 1.5), domain=pyo.Reals) 
    m.f = pyo.Var(m.L,m.T, domain=pyo.Reals)
    
    # Constraints
    m.ang_ref = pyo.ConstraintList() # Constraint 1: Reference angle
    m.flow_eq = pyo.ConstraintList() # Constraint 2: Distribution lines limits
    m.flow_bounds = pyo.ConstraintList() # Constraint 2: Distribution lines limits
    m.nod_bal = pyo.ConstraintList(doc = 'Nodes') # Constraint 3: Power balance per node
    
    # Objective function: Minimize the modifications of the setpoint to make it feasible
    m.obj_req = pyo.Objective(expr= sum(m.slack_up[T,N] + m.slack_down[T,N] for N in m.N for T in m.T), sense=pyo.minimize)

    for T in m.T:

        # Constraint 1: Reference angle
        m.ang_ref.add(m.theta[n_ref,T] == 0) 
        
        # Constraint 2: Distribution lines limits
        for L in m.L:
            m.flow_eq.add(m.f[L,T] - branch.loc[L,'B']*(m.theta[branch.loc[L,'From'],T] - m.theta[branch.loc[L,'To'],T]) == 0)
            m.flow_bounds.add(pyo.inequality(-branch.loc[L,'Lim'],m.f[L,T],branch.loc[L,'Lim']))
        
        # Constraint 3: Power balance
        for N in m.N:
            m.nod_bal.add(Setpoint.at[T,N] + m.slack_up[T,N] - m.slack_down[T,N]
                               - sum(branch.at[L,'B']*(m.theta[branch.at[L,'From'],T] - m.theta[branch.at[L,'To'],T]) for L in branch.index if branch.at[L,'From'] == N)
                               - sum(branch.at[L,'B']*(m.theta[branch.at[L,'To'],T] - m.theta[branch.at[L,'From'],T]) for L in branch.index if branch.at[L,'To'] == N) == 0)
    return m
  
m = flex_req()

#choose the solver
opt = pyo.SolverFactory('gurobi')
results = opt.solve(m)
#m.display()
#m.dual.display()

# Line flow calculations:
line_flow = pd.DataFrame(columns = ['Time_target','Line','Power_flow','Line_limit']) 
line_flow_per = pd.DataFrame(columns = ['Time Period','l1','l2','l3','l4','l5','l6','l7','l8','l9','l10','l11','l12','l13','l14','l15','l16','l17','l18','l19','l20','l21','l22','l23','l24','l25','l26','l27','l28','l29','l30','l31','l32'])
line_flow_per.set_index('Time Period',inplace=True)
for T in Setpoint.index:
    for L in lines: 
        line_flow = line_flow.append({'Time_target':T,'Line':L,'Power_flow': abs(m.f[L,T].value),'Line_limit':branch.at[L,'Lim'],'Line_capacity':100*abs(m.f[L,T].value)/branch.at[L,'Lim']},ignore_index=True)                    
        line_flow_per.at[T,L] = round(abs(m.f[L,T].value)/branch.at[L,'Lim'],2)

#%% Flexible Requests Creation to obtain a feasible setpoint

requests = pd.DataFrame(columns = ['ID','Bid','Bus','Direction','Quantity','Price','Time_target','Time_stamp','Block'])

if len(nodes) == 33: # Print results 33 nodes
    print ('33nodes')
    req_up = 0
    req_down = 0
    req_up_quantity = 0
    req_down_quantity = 0
    slack_up_all = pd.DataFrame(columns = ['Time Period','n1','n2','n3','n4','n5','n6','n7','n8','n9','n10','n11','n12','n13','n14','n15','n16','n17','n18','n19','n20','n21','n22','n23','n24','n25','n26','n27','n28','n29','n30','n31','n32','n33'])
    slack_up_all.set_index('Time Period',inplace=True)
    slack_down_all = pd.DataFrame(columns = ['Time Period','n1','n2','n3','n4','n5','n6','n7','n8','n9','n10','n11','n12','n13','n14','n15','n16','n17','n18','n19','n20','n21','n22','n23','n24','n25','n26','n27','n28','n29','n30','n31','n32','n33'])
    slack_down_all.set_index('Time Period',inplace=True)
    
    for n in Setpoint.columns:
        for t in Setpoint.index:
            slack_up_all.at[t,n] = m.slack_up[t,n].value
            slack_down_all.at[t,n] = -m.slack_down[t,n].value
            if m.slack_up[t,n].value != 0:
                req_up +=1
                req_up_quantity += m.slack_up[t,n].value
            if m.slack_down[t,n].value != 0:
                req_down +=1
                req_down_quantity += m.slack_down[t,n].value
                
    print ('req_up',req_up,req_up_quantity,'req_down',req_down,req_down_quantity)
    
if len(nodes) == 15: # Print results 15 nodes
    print ('15nodes')
    req_up = 0
    req_down = 0
    req_up_quantity = 0
    req_down_quantity = 0
    slack_up_all = pd.DataFrame(columns = ['Time Period','n1','n2','n3','n4','n5','n6','n7','n8','n9','n10','n11','n12','n13','n14','n15'])
    slack_up_all.set_index('Time Period',inplace=True)
    slack_down_all = pd.DataFrame(columns = ['Time Period','n1','n2','n3','n4','n5','n6','n7','n8','n9','n10','n11','n12','n13','n14','n15'])
    slack_down_all.set_index('Time Period',inplace=True)
    
    for n in Setpoint.columns:
        for t in Setpoint.index:
            slack_up_all.at[t,n] = m.slack_up[t,n].value
            slack_down_all.at[t,n] = -m.slack_down[t,n].value
            if m.slack_up[t,n].value != 0:
                req_up +=1
                req_up_quantity += m.slack_up[t,n].value
            if m.slack_down[t,n].value != 0:
                req_down +=1
                req_down_quantity += m.slack_down[t,n].value     

    print ('req_up',req_up,req_up_quantity,'req_down',req_down,req_down_quantity)

for t in slack_up_all.index: # Create Flex_req
    for n in slack_up_all.columns: # Only consider the requests >= 0.01
        if round(slack_up_all.at[t,n],2) != 0:
            req_ID = random.choice(range(1000))
            req_n = n
            req_dir = 'Up'
            req_Q = round(slack_up_all.at[t,n],2)
            req_price = random.choice(range(250,300))
            req_tt = t
            requests = requests.append({'ID':req_ID,'Bid':'Request','Bus':req_n,'Direction':req_dir,'Quantity':req_Q,'Price':req_price,'Time_target':req_tt,'Time_stamp':0,'Block':'No'},ignore_index=True)
        if round(slack_down_all.at[t,n],2) != 0:
            req_ID = random.choice(range(1000))
            req_n = n
            req_dir = 'Down'
            req_Q = -round(slack_down_all.at[t,n],2)
            req_price = random.choice(range(35,45)) # 250-350
            req_tt = t
            requests = requests.append({'ID':req_ID,'Bid':'Request','Bus':req_n,'Direction':req_dir,'Quantity':req_Q,'Price':req_price,'Time_target':req_tt,'Time_stamp':0,'Block':'No'},ignore_index=True)


#%%Offers creation

nodes = Setpoint.columns
time_periods = Setpoint.index

offers = pd.DataFrame(columns = ['ID','Bid','Bus','Direction','Quantity','Price','Time_target','Time_stamp','Block'])
#offers.set_index('ID',inplace=True)

# Random single offers creation
for i in range (100): # Number of offers you are creating
    ran_ID = random.choice(range(1000))
    ran_n = random.choice(nodes)
    ran_dir = random.choice(['Up','Down'])
    ran_Q = random.choice([0.01,0.02,0.03,0.04,0.05]) # Quantity for the offers
    ran_price = random.choice(range(30,40))
    ran_tt = random.choice(time_periods)
    offers.loc[i] = [ran_ID,'Offer',ran_n,ran_dir,ran_Q,ran_price,ran_tt,0,'No']
    
# Random block offers creation
for j in range (100): # Number of offers you are creating
    
    # First part of the BB
    ran_ID = random.choice(range(1000))
    ran_n1 = random.choice(['n1','n14','n18','n30'])
    ran_n2 = random.choice(nodes)
    ran_n = random.choice([ran_n1,ran_n2])
    #ran_n = random.choice(nodes)
    ran_dir = random.choice(['Up','Down'])
    ran_Q = random.choice([0.01,0.02,0.03,0.04,0.05]) # Quantity for the offers
    ran_price = random.choice(range(20,35))
    ran_tt1 = random.choice(time_periods[0:(len(time_periods))-1])
    ran_tt2 = random.choice(['t16','t17','t18','t19','t20','t21','t22'])
    ran_tt = random.choice([ran_tt1,ran_tt2])
    #ran_tt = random.choice(time_periods[0:(len(time_periods))-1])
    ran_bb = random.choice(range(10000))
    offers = offers.append({'ID':ran_ID,'Bid':'Offer','Bus':ran_n,'Direction':ran_dir,'Quantity':ran_Q,'Price':ran_price,'Time_target':ran_tt,'Time_stamp':0,'Block':ran_bb},ignore_index=True)

# Randomize arrival time
all_bids_ini = [requests,offers]
all_bids_ini = pd.concat(all_bids_ini)   
all_bids_ini = all_bids_ini.sample(frac=1).reset_index(drop=True)
all_bids = pd.DataFrame(columns = ['ID','Bid','Bus','Direction','Quantity','Price','Time_target','Time_stamp','Block'])

for bid in all_bids_ini.index:
    
    all_bids = all_bids.append(all_bids_ini.loc[bid,:], ignore_index=True)
    if all_bids_ini.at[bid,'Block'] != 'No':

        # Second part of the BB
        ran_ID = random.choice(range(1000))
        ran_n = all_bids_ini.at[bid,'Bus']
        if all_bids_ini.at[bid,'Direction'] == 'Up':
            ran_dir2 = 'Down'
        else:
            ran_dir2 = 'Up'
        ran_Q = random.choice([0.01,0.02,0.03,0.04,0.05]) # Quantity for the offers
        ran_price = all_bids_ini.at[bid,'Price']
        ran_bb = all_bids_ini.at[bid,'Block']
        for i in range(len(time_periods)):
            if time_periods[i]==all_bids_ini.at[bid,'Time_target']:
                ran_tt2 = time_periods[i+1]   
        all_bids = all_bids.append({'ID':ran_ID,'Bid':'Offer','Bus':ran_n,'Direction':ran_dir2,'Quantity':ran_Q,'Price':ran_price,'Time_target':ran_tt2,'Time_stamp':0,'Block':ran_bb},ignore_index=True)


#%% Check feasibility of the optimization problem
# if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
#      print ("this is feasible and optimal")
# elif results.solver.termination_condition == TerminationCondition.infeasible:
#      print ("do something about it? or exit?")
# else:
#      # something else is wrong
#      print (str(results.solver))






