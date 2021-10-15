# market clearing mechanisms
Code for performing auction-based and continuous clearing in local flexibility markets (LFM) including block bids and network constraints. The repository is associated with the Master's 
Thesis *Market Clearing Mechanisms for Local Flexibility Markets in Distribution Grids* by A. Alarcón Cobacho.

## Study case files
 * **network33bus.xlsx**: Network data.
 * **Bids_energy_33.xlsx**: Flexibility single and block bids (offers and requests), with a random, best and worst arrival order.
 * **Setpoint_nodes.xlsx**: Initial value of the bus setpoints, together with some studies and calculations of the Setpoint.

## Run the Auction-based clearing algorithm
The script **Market_clearing_energy.py** should be run to simulate the matching of the bis in **Bids_energy.csv** by the continuous market.

## Run the Continuous clearing algorithm



## Grid contraints
Grid constraints are checked by the function implemented in **PTDF_check.py**, which is called by **Market_clearing_energy.py**
