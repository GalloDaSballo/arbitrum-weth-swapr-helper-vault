from brownie import (
    accounts,
    interface,
    Controller,
    SettV4,
    MyStrategy,
)
from config import (
    BADGER_DEV_MULTISIG,
    WANT,
    LP_COMPONENT,
    REWARD_TOKEN,
    PROTECTED_TOKENS,
    FEES,
)
from dotmap import DotMap
import pytest


@pytest.fixture
def deployed():
    """
    Deploys, vault, controller and strats and wires them up for you to test
    """
    deployer = accounts[0]

    strategist = deployer
    keeper = deployer
    guardian = deployer

    governance = accounts.at(BADGER_DEV_MULTISIG, force=True)

    controller = Controller.deploy({"from": deployer})
    controller.initialize(BADGER_DEV_MULTISIG, strategist, keeper, BADGER_DEV_MULTISIG)

    sett = SettV4.deploy({"from": deployer})
    sett.initialize(
        WANT,
        controller,
        BADGER_DEV_MULTISIG,
        keeper,
        guardian,
        False,
        "prefix",
        "PREFIX",
    )

    sett.unpause({"from": governance})
    controller.setVault(WANT, sett)

    ## TODO: Add guest list once we find compatible, tested, contract
    # guestList = VipCappedGuestListWrapperUpgradeable.deploy({"from": deployer})
    # guestList.initialize(sett, {"from": deployer})
    # guestList.setGuests([deployer], [True])
    # guestList.setUserDepositCap(100000000)
    # sett.setGuestList(guestList, {"from": governance})

    ## Start up Strategy
    strategy = MyStrategy.deploy({"from": deployer})
    strategy.initialize(
        BADGER_DEV_MULTISIG,
        strategist,
        controller,
        keeper,
        guardian,
        PROTECTED_TOKENS,
        FEES,
    )

    strategy.setStakingContract("0xe2A7CF0DEB83F2BC2FD15133a02A24B9981f2c17", {"from": governance})


    ## Tool that verifies bytecode (run independently) <- Webapp for anyone to verify

    ## Set up tokens
    want = interface.IERC20(WANT)
    lpComponent = interface.IERC20(LP_COMPONENT)
    rewardToken = interface.IERC20(REWARD_TOKEN)

    ## Wire up Controller to Strart
    ## In testing will pass, but on live it will fail
    controller.approveStrategy(WANT, strategy, {"from": governance})
    controller.setStrategy(WANT, strategy, {"from": deployer})

    ## Get some WETH
    WETH = interface.IERC20(strategy.WETH())
    WETH_DEP = interface.IWETH(strategy.WETH())
    WETH_DEP.deposit({"from": deployer, "value": 5000000000000000000})

    ## Get some SWAPR
    router = interface.IUniswapRouterV2(strategy.DX_SWAP_ROUTER())
    SWAPR = interface.IERC20(strategy.reward())
    router.swapExactETHForTokens(
        0,  ## Mint out
        [WETH, SWAPR],
        deployer,
        9999999999999999,
        {"from": deployer, "value": 5000000000000000000},
    )

    WETH.approve(router, WETH.balanceOf(deployer), {"from": deployer})
    SWAPR.approve(router, SWAPR.balanceOf(deployer), {"from": deployer})
    router.addLiquidity(
        WETH,
        SWAPR,
        WETH.balanceOf(deployer),
        SWAPR.balanceOf(deployer),
        0,
        0,
        deployer,
        9999999999999999,
        {"from": deployer},
    )

    return DotMap(
        deployer=deployer,
        controller=controller,
        vault=sett,
        sett=sett,
        strategy=strategy,
        # guestList=guestList,
        want=want,
        lpComponent=lpComponent,
        rewardToken=rewardToken,
    )


## Contracts ##


@pytest.fixture
def vault(deployed):
    return deployed.vault


@pytest.fixture
def sett(deployed):
    return deployed.sett


@pytest.fixture
def controller(deployed):
    return deployed.controller


@pytest.fixture
def strategy(deployed):
    return deployed.strategy


## Tokens ##


@pytest.fixture
def want(deployed):
    return deployed.want


@pytest.fixture
def tokens():
    return [WANT, LP_COMPONENT, REWARD_TOKEN]


## Accounts ##


@pytest.fixture
def deployer(deployed):
    return deployed.deployer


@pytest.fixture
def strategist(strategy):
    return accounts.at(strategy.strategist(), force=True)


@pytest.fixture
def settKeeper(vault):
    return accounts.at(vault.keeper(), force=True)


@pytest.fixture
def strategyKeeper(strategy):
    return accounts.at(strategy.keeper(), force=True)


## Forces reset before each test
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass
