#!/usr/bin/python3
from scripts.helpful_scripts import get_account
from brownie import StakingMonitor, config, network


def deploy_staking_monitor():
    account = get_account()
    return StakingMonitor.deploy(
        config["networks"][network.show_active()]["eth_usd_price_feed"],
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )


def main():
    deploy_staking_monitor()
