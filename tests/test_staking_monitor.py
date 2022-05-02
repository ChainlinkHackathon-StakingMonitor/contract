from brownie import StakingMonitor
from scripts.helpful_scripts import get_account, get_contract


def test_can_get_latest_price():
    # Arrange
    address = get_contract("eth_usd_price_feed").address
    # StakingMonitor
    staking_monitor = StakingMonitor.deploy(address, {"from": get_account()})
    # Assert
    value = staking_monitor.getLatestPrice({"from": get_account()})
    assert isinstance(value, int)
    assert value > 0
