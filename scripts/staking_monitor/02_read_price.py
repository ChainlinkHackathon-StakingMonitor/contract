#!/usr/bin/python3
from brownie import StakingMonitor


def main():
    staking_monitor_contract = StakingMonitor[-1]
    print(f"Reading data from {staking_monitor_contract.address}")
    print(staking_monitor_contract.getPrice())
