#!/usr/bin/python3
from scripts.helpful_scripts import get_account, get_contract
from brownie import StakingMonitor, config, network


def deploy_staking_monitor():
    account = get_account()
    eth_usd_price_feed_address = get_contract("eth_usd_price_feed").address
    return StakingMonitor.deploy(
        eth_usd_price_feed_address,
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )


def main():
    deploy_staking_monitor()
