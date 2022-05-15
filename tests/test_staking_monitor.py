from brownie import exceptions, StakingMonitor
import pytest

from scripts.helpful_scripts import get_account, get_contract
from web3 import Web3


@pytest.fixture
def deploy_staking_monitor_contract():
    # Arrange / Act
    interval = 3 * 60  # 3 minutes in seconds
    staking_monitor = StakingMonitor.deploy(
        get_contract("eth_usd_price_feed").address,
        get_contract("dai_token").address,
        interval,
        {"from": get_account()},
    )
    block_confirmations = 6
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        block_confirmations = 1
    staking_monitor.tx.wait(block_confirmations)
    # Assert
    assert staking_monitor is not None
    return staking_monitor


def test_can_get_latest_price(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract()
    # Act
    value = staking_monitor.getPrice({"from": get_account()})
    # Assert
    assert isinstance(value, int)
    assert value > 0


def test_deposit(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract()
    value = Web3.toWei(0.01, "ether")
    # Act
    deposit_tx_0 = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx_0.wait(1)

    value_1 = Web3.toWei(0.03, "ether")
    deposit_tx_1 = staking_monitor.deposit({"from": get_account(1), "value": value_1})
    deposit_tx_1.wait(1)

    # check that the balance has increased by the amount of the deposit
    assert staking_monitor.s_userInfos(get_account().address)["depositBalance"] == value
    # check if address is added to watchlist
    assert staking_monitor.s_watchList(0) == get_account().address

    # check that the balance has increased by the amount of the deposit
    assert (
        staking_monitor.s_userInfos(get_account(1).address)["depositBalance"] == value_1
    )
    # check if address is added to watchlist
    assert staking_monitor.s_watchList(1) == get_account(1).address


def test_get_deposit_balance():
    # Arrange
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": get_account()})
    value = Web3.toWei(0.01, "ether")
    # Act
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    # returns tuple
    balance = staking_monitor.getDepositBalance({"from": get_account()})
    assert balance == value


def test_set_price_limit_if_user_has_not_deposited_reverts():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    price_limit = 30000000000
    # Act & Assert
    with pytest.raises(exceptions.VirtualMachineError):
        price_limit_tx = staking_monitor.setOrder(price_limit, 40, {"from": account})
        price_limit_tx.wait(1)


def test_set_balances_to_swap():
    # Arrange
    account = get_account(2)
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    assert account.balance() == 100000000000000000000
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": get_account(2), "value": value})
    deposit_tx.wait(1)
    assert account.balance() == 99990000000000000000
    assert (
        staking_monitor.s_userInfos(account.address)["latestBalance"]
        == 99990000000000000000
    )

    account_1 = get_account(1)
    account_1.transfer(account, "10 ether")
    # assert account.balance() == 109990000000000000000

    tx = staking_monitor.setBalancesToSwap()
    tx.wait(1)
    watch_list_entry_for_address = staking_monitor.s_watchList(0)
    assert watch_list_entry_for_address == account.address
    assert (
        staking_monitor.s_userInfos(watch_list_entry_for_address)["balanceToSwap"]
        == 10000000000000000000
    )

    # Act

    # Assert


def test_can_set_order():
    # Arrange
    account = get_account()
    address = get_contract("eth_usd_price_feed").address
    staking_monitor = StakingMonitor.deploy(address, {"from": account})
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)
    price_limit = 30000000000
    # percentage to swap is given in percentages, the portion will be calculated in the contract
    percentage_to_swap = 40
    # Act
    price_bound_tx = staking_monitor.setOrder(
        price_limit, percentage_to_swap, {"from": account}
    )
    price_bound_tx.wait(1)
    # Assert
    assert staking_monitor.s_userInfos(account.address)["priceLimit"] == price_limit
    assert (
        staking_monitor.s_userInfos(account.address)["percentageToSwap"]
        == percentage_to_swap
    )


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
    price_bound_tx = staking_monitor.setOrder(price_limit, 40, {"from": account})
    price_bound_tx.wait(1)
    # Assert
    assert staking_monitor.s_lowestPriceLimit() == price_limit


# def test_can_get_latest_price():
#     # Arrange
#
#     # Act
#     account = get_account()
#     address = get_contract("eth_usd_price_feed").address
#     staking_monitor = StakingMonitor.deploy(address, {"from": account})
#     # Assert
#     value = staking_monitor.getPrice({"from": get_account()})
#     assert isinstance(value, int)
#     assert value > 0


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
    price_limit_tx = staking_monitor.setOrder(user_price_limit, 40, {"from": account})
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
    price_limit_tx = staking_monitor.setOrder(user_price_limit, 40, {"from": account})
    price_limit_tx.wait(1)

    # Act
    upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
        "",
        {"from": account},
    )
    assert upkeepNeeded == False
    assert isinstance(performData, bytes)
