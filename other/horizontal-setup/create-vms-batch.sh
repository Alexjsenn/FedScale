#!/usr/bin/env bash

# Set up for 2 aggregators, with 2 workers per aggregator
savi-run-server-ip m1.large Ubuntu-18-04.4 gabbys-key default H-F-S-150 10.30.74.150
savi-run-server-ip m1.large Ubuntu-18-04.4 gabbys-key default H-F-W-151 10.30.74.151
