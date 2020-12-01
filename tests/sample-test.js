const { expect } = require("chai");

describe("Greeter", function () {
  let usdt;
  let lpToken;
  let weth;
  let crusdt;
  let crweth;
  let mockOracle;
  let oracle;
  let homora;
  let basicSpell;
  let houseHoldSpell;

  beforeEach(async () => {
    const [owner, alice, bob] = await ethers.getSigners();
    const provider = ethers.getDefaultProvider();
    console.log("JJJ", (await owner.getBalance()).toString());
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    const WETH9 = await ethers.getContractFactory("MockWETH9");
    const MockCErc20 = await ethers.getContractFactory("MockCErc20");
    const MockOracle = await ethers.getContractFactory("MockOracle");
    const ProxyOracle = await ethers.getContractFactory("ProxyOracle");
    const HomoraBank = await ethers.getContractFactory("HomoraBank");
    const BasicSpell = await ethers.getContractFactory("BasicSpell");
    const HouseHoldSpell = await ethers.getContractFactory("HouseHoldSpell");
    usdt = await MockERC20.deploy("USDT", "USDT");
    await usdt.deployed();
    lpToken = await MockERC20.deploy("LP_TOKEN", "LP_TOKEN");
    await lpToken.deployed();
    weth = await WETH9.deploy();
    await weth.deployed();
    let tx = {
      to: weth.address,
      value: ethers.utils.parseEther("1000"),
    };
    await owner.sendTransaction(tx);
    console.log("WE", (await weth.totalSupply()).toString());
    crusdt = await MockCErc20.deploy(usdt.address);
    crweth = await MockCErc20.deploy(weth.address);
    await crusdt.deployed();
    mockOracle = await MockOracle.deploy();
    await mockOracle.deployed();
    await mockOracle.setETHPx(usdt.address, ethers.utils.parseEther("500"));
    await mockOracle.setETHPx(lpToken.address, ethers.utils.parseEther("250"));
    await mockOracle.setETHPx(weth.address, ethers.utils.parseEther("1"));
    oracle = await ProxyOracle.deploy();
    await oracle.deployed();
    await oracle.setOracles(
      [usdt.address, lpToken.address, weth.address],
      [
        [mockOracle.address, 10000, 10000, 10000],
        [mockOracle.address, 10000, 10000, 10000],
        [mockOracle.address, 10000, 10000, 10000],
      ]
    );
    homora = await HomoraBank.deploy();
    await homora.deployed();
    await homora.initializeX(oracle.address, 1000);
    await homora.addBank(usdt.address, crusdt.address);
    await homora.addBank(weth.address, crweth.address);
    basicSpell = await BasicSpell.deploy(homora.address, weth.address);
    await basicSpell.deployed();
    houseHoldSpell = await HouseHoldSpell.deploy(homora.address, weth.address);
    await basicSpell.deployed();
  });

  it("can take collateral", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    await lpToken
      .connect(alice)
      .mint(alice.address, ethers.utils.parseEther("500"));
    console.log(
      "alice lp start",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp start",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await lpToken
      .connect(alice)
      .approve(homora.address, ethers.constants.MaxUint256);
    await homora
      .connect(alice)
      .execute(
        0,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("putCollateral", [
          lpToken.address,
          ethers.utils.parseEther("10"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    const positionId = await homora.nextPositionId();
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("takeCollateral", [
          lpToken.address,
          ethers.utils.parseEther("1"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    expect(1).to.equal(1);
  });

  it("can borrow", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    await lpToken
      .connect(alice)
      .mint(alice.address, ethers.utils.parseEther("500"));
    console.log(
      "alice lp start",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp start",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await lpToken
      .connect(alice)
      .approve(homora.address, ethers.constants.MaxUint256);
    await homora
      .connect(alice)
      .execute(
        0,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("putCollateral", [
          lpToken.address,
          ethers.utils.parseEther("10"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "alice usdt before",
      (await usdt.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    const positionId = await homora.nextPositionId();
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("borrow", [
          usdt.address,
          ethers.utils.parseEther("1"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "alice usdt after",
      (await usdt.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    expect(1).to.equal(1);
  });

  it("can repay", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    await lpToken
      .connect(alice)
      .mint(alice.address, ethers.utils.parseEther("500"));
    console.log(
      "alice lp start",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp start",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await lpToken
      .connect(alice)
      .approve(homora.address, ethers.constants.MaxUint256);
    await homora
      .connect(alice)
      .execute(
        0,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("putCollateral", [
          lpToken.address,
          ethers.utils.parseEther("10"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "alice usdt before",
      (await usdt.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    const positionId = await homora.nextPositionId();
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("borrow", [
          usdt.address,
          ethers.utils.parseEther("1"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "alice usdt after",
      (await usdt.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await usdt
      .connect(alice)
      .approve(homora.address, ethers.constants.MaxUint256);
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("repay", [
          usdt.address,
          ethers.utils.parseEther("1"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "alice usdt after",
      (await usdt.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    expect(1).to.equal(1);
  });

  it("can borrow ETH", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    await lpToken
      .connect(alice)
      .mint(alice.address, ethers.utils.parseEther("500"));
    console.log(
      "alice lp start",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp start",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await lpToken
      .connect(alice)
      .approve(homora.address, ethers.constants.MaxUint256);
    await homora
      .connect(alice)
      .execute(
        0,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("putCollateral", [
          lpToken.address,
          ethers.utils.parseEther("10"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log("alice eth before", (await alice.getBalance()).toString());
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    const positionId = await homora.nextPositionId();
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("borrowETH", [
          ethers.utils.parseEther("1"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log("alice eth after", (await alice.getBalance()).toString());
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    expect(1).to.equal(1);
  });

  it("can repay ETH", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    await lpToken
      .connect(alice)
      .mint(alice.address, ethers.utils.parseEther("500"));
    console.log(
      "alice lp start",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log(
      "bank lp start",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await lpToken
      .connect(alice)
      .approve(homora.address, ethers.constants.MaxUint256);
    await homora
      .connect(alice)
      .execute(
        0,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("putCollateral", [
          lpToken.address,
          ethers.utils.parseEther("10"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log("alice eth before", (await alice.getBalance()).toString());
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    const positionId = await homora.nextPositionId();
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("borrowETH", [
          ethers.utils.parseEther("1"),
        ])
      );
    console.log(
      "alice lp after",
      (await lpToken.balanceOf(alice.address)).toString()
    );
    console.log("alice eth after", (await alice.getBalance()).toString());
    console.log(
      "bank lp after",
      (await lpToken.balanceOf(homora.address)).toString()
    );
    await homora
      .connect(alice)
      .execute(
        positionId - 1,
        houseHoldSpell.address,
        lpToken.address,
        houseHoldSpell.interface.encodeFunctionData("repayETH", [
          ethers.utils.parseEther("1"),
        ]),
        { value: ethers.utils.parseEther("1") }
      );
    expect(1).to.equal(1);
  });
});
