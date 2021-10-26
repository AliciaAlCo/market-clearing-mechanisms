# market clearing mechanisms
Code for performing auction-based and continuous clearing in local flexibility markets (LFM) including block bids and network constraints. The repository is associated with the Master's 
Thesis *Market Clearing Mechanisms for Local Flexibility Markets in Distribution Grids* by A. Alarcón Cobacho.

## Study case files
 * **network33bus.xlsx**: Network data.
 * **Bids_energy_33.xlsx**: Flexibility single and block bids (offers and requests), with a random, best and worst arrival order.
 * **Setpoint_nodes.xlsx**: Initial value of the bus setpoints, together with some studies and calculations of the Setpoint.

## Run the Auction-based clearing algorithm
The script **Auction_Energy_BlockBids.py** should be run to simulate the matching of the bids in **Bids_energy_33.xlsx** by the auction-based market.

## Run the Continuous clearing algorithm
The script **Market_clearing_Energy_Block_Bids.py** should be run to simulate the matching of the bids in **Bids_energy_33.xlsx** by the continuous market.

## Grid contraints
* **Auction_Energy_BlockBids.py** performs a DC optimal power flow analysis using the data in **network33bus.xlsx** and **Setpoint_nodes.xlsx**.
* **Market_clearing_Energy_Block_Bids.py** calls **PTDF_check.py**, which uses the PTDF factors given in **network33bus.xlsx**.
