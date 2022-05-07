from brownie import exceptions, StakingMonitor
import pytest

from scripts.helpful_scripts import get_account, get_contract
from web3 import Web3


def test_can_get_latest_price():
    # Arrange
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": get_account()})
    # Act
    value = staking_monitor.getPrice({"from": get_account()})
    # Assert
    assert isinstance(value, int)
    assert value > 0


def test_deposit():
    # Arrange
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": get_account()})
    value = Web3.toWei(0.01, "ether")
    # Act
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    # returns tuple
    assert staking_monitor.s_userInfos(get_account().address)[0] == value


def test_set_price_limit_if_user_has_not_deposited_reverts():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    price_limit = 30000000000
    # Act & Assert
    with pytest.raises(exceptions.VirtualMachineError):
        price_bound_tx = staking_monitor.setPriceLimit(price_limit, {"from": account})
        price_bound_tx.wait(1)


def test_can_set_price_limit():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)
    price_limit = 30000000000
    # Act
    price_bound_tx = staking_monitor.setPriceLimit(price_limit, {"from": account})
    price_bound_tx.wait(1)
    # Assert
    assert staking_monitor.s_userInfos(account.address)[2] == Web3.toWei(3, "ether")


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


def test_upkeep_needed():
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    # Assert
    value = staking_monitor.getPrice({"from": get_account()})
    assert value == 2000000000000000000000
    assert isinstance(value, int)
    assert value > 0
