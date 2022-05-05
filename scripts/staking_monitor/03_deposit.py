from brownie import StakingMonitor, Wei
from scripts.helpful_scripts import get_account


def deposit():
    staking_monitor = StakingMonitor[-1]
    account = get_account()
    deposit_value = Wei("0.01 ether")
    staking_monitor.deposit({"from": account, "value": deposit_value})


def read_user_info():
    staking_monitor = StakingMonitor[-1]
    account = get_account()
    userInfos = staking_monitor.s_userInfos({"from": account})
    print(userInfos)


def main():
    deposit()
    read_user_info()
