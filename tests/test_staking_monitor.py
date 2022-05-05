from brownie import exceptions, StakingMonitor
import pytest

from scripts.helpful_scripts import get_account, get_contract
from web3 import Web3


def test_can_get_latest_price():
    # Arrange
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": get_account()})
    # Assert
    value = staking_monitor.getPrice({"from": get_account()})
    assert isinstance(value, int)
    assert value > 0


def test_deposit():
    # Arrange
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": get_account()})
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    # returns tuple
    assert staking_monitor.s_userInfos(get_account().address)[0] == value


def test_can_set_price_limit():
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    price_limit = 30000000000

    price_bound_tx = staking_monitor.setPriceLimit(price_limit, {"from": account})

    price_bound_tx.wait(1)

    assert staking_monitor.s_userInfos(account.address)[2] == Web3.toWei(3, "ether")


# def test_should_throw_error_if_price_mismatch():
#     account = get_account()
#     staking_monitor = deploy_staking_monitor()
#     upper_bound = 30000000000
#     lower_bound = 25000000000
#
#     with pytest.raises(exceptions.VirtualMachineError):
#         staking_monitor.setPriceBounds(lower_bound, upper_bound, {"from": account})


def test_can_get_latest_price():
    # Arrange

    # Act
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    # Assert
    value = staking_monitor.getPrice({"from": get_account()})
    assert isinstance(value, int)
    assert value > 0


def test_can_call_check_upkeep():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
        "",
        {"from": account},
    )
    assert isinstance(upkeepNeeded, bool)
    assert isinstance(performData, bytes)
