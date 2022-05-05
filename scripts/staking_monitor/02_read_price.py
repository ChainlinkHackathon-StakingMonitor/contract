#!/usr/bin/python3
from brownie import StakingMonitor


def main():
    staking_monitor = StakingMonitor[-1]
    print(f"Reading data from {staking_monitor.address}")
    print(staking_monitor.getPrice())
