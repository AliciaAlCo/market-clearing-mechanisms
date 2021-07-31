# energy-continuous
Code for flexibility energy continuous market

## Case files
 * **network15bus.xls**: Network data.
 * **Bids_energy.csv**: Flexibility bids (offers and requests).
 * **Setpoint.csv**: Initial value of the bus setpoints.

## Run the market clearing algorithm
The script **Market_clearing_energy.py** should be run to simulate the matching of the bis in **Bids_energy.csv** by the continuous market.

## Grid contraints
Grid constraints are checked by the function implemented in **PTDF_check.py**, which is called by **Market_clearing_energy.py**
