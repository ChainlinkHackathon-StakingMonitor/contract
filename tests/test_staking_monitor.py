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
        price_limit_tx = staking_monitor.setPriceLimit(price_limit, {"from": account})
        price_limit_tx.wait(1)


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
    assert staking_monitor.s_userInfos(account.address)[2] == price_limit


def test_setting_the_lowest_price_limit_sets_lower_price_limit():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)
    price_limit = staking_monitor.getPrice({"from": get_account()}) - 1000
    # Act
    price_bound_tx = staking_monitor.setPriceLimit(price_limit, {"from": account})
    price_bound_tx.wait(1)
    # Assert
    assert staking_monitor.s_lowestPriceLimit() == price_limit


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
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    # get current price
    current_eth_price = staking_monitor.getPrice({"from": get_account()})
    # deposit some eth so that we can set a price limit
    deposit_value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit(
        {"from": get_account(), "value": deposit_value}
    )
    deposit_tx.wait(1)
    # set a price limit that is 100 less than current price so that upkeep is needed
    user_price_limit = current_eth_price - 100
    price_limit_tx = staking_monitor.setPriceLimit(user_price_limit, {"from": account})
    price_limit_tx.wait(1)

    # Act
    upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
        "",
        {"from": account},
    )
    assert upkeepNeeded == True
    assert isinstance(performData, bytes)


def test_upkeep_not_needed():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    # get current price
    current_eth_price = staking_monitor.getPrice({"from": get_account()})
    # deposit some eth so that we can set a price limit
    deposit_value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit(
        {"from": get_account(), "value": deposit_value}
    )
    deposit_tx.wait(1)
    # set a price limit that is 100 less than current price so that upkeep is needed
    user_price_limit = current_eth_price + 100
    price_limit_tx = staking_monitor.setPriceLimit(user_price_limit, {"from": account})
    price_limit_tx.wait(1)

    # Act
    upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
        "",
        {"from": account},
    )
    assert upkeepNeeded == False
    assert isinstance(performData, bytes)
