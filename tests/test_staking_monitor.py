from brownie import exceptions, StakingMonitor, network
import pytest
import math

from scripts.helpful_scripts import (
    get_account,
    get_contract,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
from web3 import Web3


@pytest.fixture
def deploy_staking_monitor_contract():
    # Arrange / Act
    interval = 3 * 60  # 3 minutes in seconds
    staking_monitor = StakingMonitor.deploy(
        get_contract("eth_usd_price_feed").address,
        get_contract("dai_token").address,
        get_contract("uniswap_v2").address,
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
    staking_monitor = deploy_staking_monitor_contract
    # Act
    value = staking_monitor.getPrice({"from": get_account()})
    # Assert
    assert isinstance(value, int)
    assert value > 0


def test_deposit(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    value = Web3.toWei(0.01, "ether")

    # Act
    deposit_tx_0 = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx_0.wait(1)

    value_1 = Web3.toWei(0.03, "ether")
    deposit_tx_1 = staking_monitor.deposit({"from": get_account(1), "value": value_1})
    deposit_tx_1.wait(1)

    # Assert
    # check that the balance has increased by the amount of the deposit
    assert staking_monitor.s_users(get_account().address)["depositBalance"] == value
    # check if address is added to watchlist
    assert staking_monitor.s_watchList(0) == get_account().address

    # check that the balance has increased by the amount of the deposit
    assert staking_monitor.s_users(get_account(1).address)["depositBalance"] == value_1
    # check if address is added to watchlist
    assert staking_monitor.s_watchList(1) == get_account(1).address


def test_withdraw_eth(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    value = Web3.toWei(0.01, "ether")
    account_original_balance = get_account().balance
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    # Act
    withdrawal_tx = staking_monitor.withdrawETH((value / 2), {"from": get_account()})
    withdrawal_tx.wait(1)

    # Assert
    assert staking_monitor.s_users(get_account().address)["depositBalance"] == value / 2
    assert get_account().balance == account_original_balance


def test_withdraw_eth(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    value = Web3.toWei(0.01, "ether")
    account_original_balance = get_account().balance
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    # Act
    withdrawal_tx = staking_monitor.withdrawETH((value / 2), {"from": get_account()})
    withdrawal_tx.wait(1)

    # Assert
    assert staking_monitor.s_users(get_account().address)["depositBalance"] == value / 2
    assert get_account().balance == account_original_balance


def test_withdraw_eth_reverts_if_not_enough_balance(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    value = Web3.toWei(0.01, "ether")
    account_original_balance = get_account().balance
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    with pytest.raises(exceptions.VirtualMachineError):
        withdrawal_tx = staking_monitor.withdrawETH(
            (value * 2), {"from": get_account()}
        )
        withdrawal_tx.wait(1)  # Act


def test_get_deposit_balance(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    value = Web3.toWei(0.01, "ether")
    # Act
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)

    # Assert
    # returns tuple
    balance = staking_monitor.getDepositBalance({"from": get_account()})
    assert balance == value


def test_can_set_order(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": get_account(), "value": value})
    deposit_tx.wait(1)
    price_limit = 20000

    # percentage to swap is given in percentages, the portion will be calculated in the contract
    percentage_to_swap = 40

    # Act
    set_order_tx = staking_monitor.setOrder(
        price_limit, percentage_to_swap, {"from": get_account()}
    )
    set_order_tx.wait(1)

    # Assert
    # 8 decimals are added to the price limit by the contract, to match what's returned by getPrice
    assert (
        staking_monitor.s_users(get_account().address)["priceLimit"]
        == price_limit * 100000000
    )
    assert (
        staking_monitor.s_users(get_account().address)["percentageToSwap"]
        == percentage_to_swap
    )


def test_get_user_data(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    deposit_value = Web3.toWei(0.01, "ether")
    # Act
    deposit_tx = staking_monitor.deposit(
        {"from": get_account(), "value": deposit_value}
    )
    deposit_tx.wait(1)

    price_limit = 20000

    # percentage to swap is given in percentages, the portion will be calculated in the contract
    percentage_to_swap = 40

    # Act
    set_order_tx = staking_monitor.setOrder(
        price_limit, percentage_to_swap, {"from": get_account()}
    )
    set_order_tx.wait(1)

    # Assert

    # returns tuple
    # from contract:
    # struct userData {
    #     bool created;
    #     bool enoughDepositForSwap;
    #     uint256 depositBalance;
    #     uint256 DAIBalance;
    #     uint256 priceLimit;
    #     uint256 percentageToSwap;
    #     uint256 balanceToSwap;
    #     uint256 previousBalance;
    # }

    userData = staking_monitor.getUserData({"from": get_account()})

    assert userData[0] == True
    assert userData[1] == True
    assert userData[2] == deposit_value
    assert userData[3] == 0
    assert userData[4] == price_limit * 100000000
    assert userData[5] == 40
    assert userData[6] == 0
    assert userData[7] == get_account().balance()

    # when user hasn't deposited yet
    userData = staking_monitor.getUserData({"from": get_account(8)})

    assert userData[0] == False


def test_set_order_if_user_has_not_deposited_reverts(
    deploy_staking_monitor_contract,
):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    price_limit = 2000
    # Act & Assert
    with pytest.raises(exceptions.VirtualMachineError):
        set_order_tx = staking_monitor.setOrder(
            price_limit, 40, {"from": get_account()}
        )
        set_order_tx.wait(1)


def test_calculate_user_balance_to_swap(deploy_staking_monitor_contract):
    current_balance = Web3.toWei(0.05, "ether")
    previous_balance = Web3.toWei(0.01, "ether")
    order_percentage_to_swap = 45
    staking_monitor = deploy_staking_monitor_contract
    result = staking_monitor.calculateUserBalanceToSwap(
        current_balance, previous_balance, order_percentage_to_swap
    )
    assert (
        result == (current_balance - previous_balance) * order_percentage_to_swap / 100
    )


def test_calculate_user_swap_share(deploy_staking_monitor_contract):
    total_token = Web3.toWei(1, "ether")
    user_balance_to_swap = Web3.toWei(0.003, "ether")
    total_amount = Web3.toWei(0.05, "ether")
    staking_monitor = deploy_staking_monitor_contract
    result = staking_monitor.calculateUserSwapShare(
        total_token, user_balance_to_swap, total_amount
    )
    assert result == total_token * user_balance_to_swap / total_amount


def test_set_balances_to_swap(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    user_account = get_account(2)
    # we deposit into the contract
    value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": user_account, "value": value})
    deposit_tx.wait(1)
    assert (
        staking_monitor.s_users(user_account.address)["previousBalance"]
        == user_account.balance()
    )

    # Act
    # we set the order for this user
    price_limit = 1000
    # percentage to swap is given in percentages, the portion will be calculated in the contract
    percentage_to_swap = 40

    set_order_tx = staking_monitor.setOrder(
        price_limit, percentage_to_swap, {"from": user_account}
    )
    set_order_tx.wait(1)

    # we mimic a staking reward by sending some ether from another account
    rewards_distributor = get_account(1)
    reward_amount = Web3.toWei(0.01, "ether")
    rewards_distributor.transfer(user_account, reward_amount)

    tx = staking_monitor.setBalancesToSwap()
    tx.wait(1)
    watch_list_entry_for_address = staking_monitor.s_watchList(0)

    # Assert
    assert watch_list_entry_for_address == user_account.address
    assert staking_monitor.s_users(user_account.address)[
        "balanceToSwap"
    ] == reward_amount * (percentage_to_swap / 100)


def test_set_balances_to_swap_accrues(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    user_account = get_account(3)
    # we deposit into the contract
    deposit_value = Web3.toWei(0.01, "ether")
    deposit_tx = staking_monitor.deposit({"from": user_account, "value": deposit_value})
    deposit_tx.wait(1)

    first_previous_balance = staking_monitor.s_users(user_account.address)[
        "previousBalance"
    ]

    # Act
    # we set the order for this user
    price_limit = 2000
    # percentage to swap is given in percentages, the portion will be calculated in the contract
    percentage_to_swap = 40

    set_order_tx = staking_monitor.setOrder(
        price_limit, percentage_to_swap, {"from": user_account}
    )
    set_order_tx.wait(1)

    # we mimic a staking reward by sending some ether from another account
    rewards_distributor = get_account(1)
    first_reward_amount = Web3.toWei(0.01, "ether")
    rewards_distributor.transfer(user_account, first_reward_amount)

    tx = staking_monitor.setBalancesToSwap()
    tx.wait(1)
    watch_list_entry_for_address = staking_monitor.s_watchList(0)

    assert watch_list_entry_for_address == user_account.address

    # we send more ether to user_account to mimic another staking reward
    second_reward_amount = Web3.toWei(0.02, "ether")
    rewards_distributor.transfer(user_account, second_reward_amount)
    tx = staking_monitor.setBalancesToSwap()
    tx.wait(1)

    assert staking_monitor.s_users(user_account.address)["balanceToSwap"] == (
        first_reward_amount * percentage_to_swap / 100
    ) + (second_reward_amount * percentage_to_swap / 100)


# this test fails currently, because the uniswapv2 mock seems to have an issue with it - mocking what it returns in the contract however makes the whole test pass...
# please see our stackexchange question here for more info: https://ethereum.stackexchange.com/questions/128720/mocking-and-testing-uniswapv2s-swapexactethfortokens-in-brownie-virtualmachine
def test_swap_eth_for_dai(deploy_staking_monitor_contract):
    amount_to_swap = Web3.toWei(0.02, "ether")
    staking_monitor = deploy_staking_monitor_contract
    dai_from_swap = staking_monitor.swapEthForDAI(
        amount_to_swap, {"from": get_account()}
    )
    assert dai_from_swap == 230000000000000


# this test fails currently, because the uniswapv2 mock seems to have an issue with it - mocking what it returns in the contract however makes the whole test pass...
# please see our stackexchange question here for more info: https://ethereum.stackexchange.com/questions/128720/mocking-and-testing-uniswapv2s-swapexactethfortokens-in-brownie-virtualmachine
def test_check_conditions_and_perform_swap(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    first_user_account = get_account(5)
    second_user_account = get_account(6)
    # we deposit into the contract
    first_user_deposit_value = Web3.toWei(0.01, "ether")
    second_user_deposit_value = Web3.toWei(0.02, "ether")
    first_user_deposit_tx = staking_monitor.deposit(
        {"from": first_user_account, "value": first_user_deposit_value}
    )
    first_user_deposit_tx.wait(1)
    second_user_deposit_tx = staking_monitor.deposit(
        {"from": second_user_account, "value": second_user_deposit_value}
    )
    second_user_deposit_tx.wait(1)

    # we get the latest price
    current_price = staking_monitor.getPrice({"from": get_account()})

    # we make sure that the price limit that will be set in the order is lower than the current price - 8 decimals
    price_limit = (current_price - 200000) / 100000000
    # percentage to swap is given in percentages, the portion will be calculated in the contract
    first_user_percentage_to_swap = 40
    second_user_percentage_to_swap = 55

    first_user_set_order_tx = staking_monitor.setOrder(
        price_limit, first_user_percentage_to_swap, {"from": first_user_account}
    )
    first_user_set_order_tx.wait(1)

    second_user_set_order_tx = staking_monitor.setOrder(
        price_limit, second_user_percentage_to_swap, {"from": second_user_account}
    )
    second_user_set_order_tx.wait(1)

    # we mimic a staking reward by sending some ether from another account
    rewards_distributor = get_account(1)
    first_user_reward_amount = Web3.toWei(0.003, "ether")
    second_user_reward_amount = Web3.toWei(0.006, "ether")
    rewards_distributor.transfer(first_user_account, first_user_reward_amount)
    rewards_distributor.transfer(second_user_account, second_user_reward_amount)

    tx = staking_monitor.setBalancesToSwap()
    tx.wait(1)
    watch_list_entry_for_first_user = staking_monitor.s_watchList(0)
    watch_list_entry_for_second_user = staking_monitor.s_watchList(1)

    assert watch_list_entry_for_first_user == first_user_account.address
    assert watch_list_entry_for_second_user == second_user_account.address

    first_user_balance_to_swap = staking_monitor.s_users(first_user_account.address)[
        "balanceToSwap"
    ]
    # 1200000000000000

    second_user_balance_to_swap = staking_monitor.s_users(second_user_account.address)[
        "balanceToSwap"
    ]

    # 3300000000000000

    assert (
        first_user_balance_to_swap
        == first_user_reward_amount * first_user_percentage_to_swap / 100
    )
    assert (
        second_user_balance_to_swap
        == second_user_reward_amount * second_user_percentage_to_swap / 100
    )

    total_amount_to_swap = first_user_balance_to_swap + second_user_balance_to_swap

    # Act
    tx = staking_monitor.checkConditionsAndPerformSwap({"from": get_account()})
    tx.wait(1)

    # Assert
    assert (
        staking_monitor.s_users(first_user_account.address)["priceLimit"]
        < current_price
    )

    first_user_dai_distributed = staking_monitor.s_users(first_user_account.address)[
        "DAIBalance"
    ]

    second_user_dai_distributed = staking_monitor.s_users(second_user_account.address)[
        "DAIBalance"
    ]

    total_dai_distributed = first_user_dai_distributed + second_user_dai_distributed

    what_first_user_dai_share_should_be = (
        total_dai_distributed * first_user_balance_to_swap
    ) / total_amount_to_swap

    what_second_user_dai_share_should_be = (
        total_dai_distributed * second_user_balance_to_swap
    ) / total_amount_to_swap

    assert first_user_dai_distributed == round(what_first_user_dai_share_should_be)
    assert second_user_dai_distributed == round(what_second_user_dai_share_should_be)
    assert staking_monitor.s_users(first_user_account.address)["balanceToSwap"] == 0


def test_can_call_check_upkeep(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
    upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
        "",
        {"from": get_account()},
    )
    assert isinstance(upkeepNeeded, bool)
    assert isinstance(performData, bytes)


# def test_upkeep_needed(deploy_staking_monitor_contract):
#     # Arrange
#     staking_monitor = deploy_staking_monitor_contract
#     # get current price
#     current_eth_price = staking_monitor.getPrice({"from": get_account()})
#     # deposit some eth so that we can set a price limit
#     deposit_value = Web3.toWei(0.01, "ether")
#     deposit_tx = staking_monitor.deposit(
#         {"from": get_account(), "value": deposit_value}
#     )
#     deposit_tx.wait(1)
#     # set a price limit that is 100 less than current price so that upkeep is needed
#     user_price_limit = current_eth_price - 100
#     price_limit_tx = staking_monitor.setOrder(
#         user_price_limit, 40, {"from": get_account()}
#     )
#     price_limit_tx.wait(1)
#
#     # Act
#     upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
#         "",
#         {"from": get_account()},
#     )
#     assert upkeepNeeded == True
#     assert isinstance(performData, bytes)


def test_upkeep_not_needed(deploy_staking_monitor_contract):
    # Arrange
    staking_monitor = deploy_staking_monitor_contract
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
    price_limit_tx = staking_monitor.setOrder(
        user_price_limit, 40, {"from": get_account()}
    )
    price_limit_tx.wait(1)

    # Act
    upkeepNeeded, performData = staking_monitor.checkUpkeep.call(
        "",
        {"from": get_account()},
    )
    assert upkeepNeeded == False
    assert isinstance(performData, bytes)
