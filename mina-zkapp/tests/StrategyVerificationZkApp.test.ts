import { StrategyVerificationZkApp } from '../src/StrategyVerificationZkApp';
import {
  Field,
  Mina,
  PrivateKey,
  PublicKey,
  AccountUpdate,
  Signature,
  Poseidon,
  Bool,
} from 'o1js';

describe('StrategyVerificationZkApp', () => {
  let deployerAccount: PublicKey,
      deployerKey: PrivateKey,
      senderAccount: PublicKey,
      senderKey: PrivateKey,
      zkAppAddress: PublicKey,
      zkAppPrivateKey: PrivateKey,
      zkApp: StrategyVerificationZkApp;

  beforeAll(async () => {
    const Local = Mina.LocalBlockchain({ proofsEnabled: false });
    Mina.setActiveInstance(Local);
    
    ({ privateKey: deployerKey, publicKey: deployerAccount } = Local.testAccounts[0]);
    ({ privateKey: senderKey, publicKey: senderAccount } = Local.testAccounts[1]);
    
    zkAppPrivateKey = PrivateKey.random();
    zkAppAddress = zkAppPrivateKey.toPublicKey();
    
    zkApp = new StrategyVerificationZkApp(zkAppAddress);
  });

  async function localDeploy() {
    const txn = await Mina.transaction(deployerAccount, () => {
      AccountUpdate.fundNewAccount(deployerAccount);
      zkApp.deploy();
    });
    await txn.prove();
    await txn.sign([deployerKey, zkAppPrivateKey]).send();
  }

  it('generates and deploys the `StrategyVerificationZkApp` smart contract', async () => {
    await localDeploy();
    const isActive = zkApp.isActive.get();
    expect(isActive).toEqual(Bool(false));
  });

  it('correctly initializes the contract state', async () => {
    await localDeploy();
    
    const txn = await Mina.transaction(senderAccount, () => {
      zkApp.init();
    });
    await txn.prove();
    await txn.sign([senderKey]).send();

    const strategyCommitment = zkApp.strategyCommitment.get();
    const performanceTarget = zkApp.performanceTarget.get();
    const verificationCount = zkApp.verificationCount.get();
    const isActive = zkApp.isActive.get();

    expect(strategyCommitment).toEqual(Field(0));
    expect(performanceTarget).toEqual(Field(0));
    expect(verificationCount).toEqual(Field(0));
    expect(isActive).toEqual(Bool(false));
  });

  it('creates a strategy commitment with valid signature', async () => {
    await localDeploy();
    
    const commitment = Field(12345);
    const target = Field(150);
    
    const signature = Signature.create(senderKey, [commitment, target]);
    
    const txn = await Mina.transaction(senderAccount, () => {
      zkApp.createStrategyCommitment(commitment, target, signature, senderAccount);
    });
    await txn.prove();
    await txn.sign([senderKey]).send();

    const strategyCommitment = zkApp.strategyCommitment.get();
    const performanceTarget = zkApp.performanceTarget.get();
    const isActive = zkApp.isActive.get();

    expect(strategyCommitment).toEqual(commitment);
    expect(performanceTarget).toEqual(target);
    expect(isActive).toEqual(Bool(true));
  });

  it('verifies strategy performance with valid proof', async () => {
    await localDeploy();
    
    const commitment = Field(12345);
    const target = Field(150);
    const signature = Signature.create(senderKey, [commitment, target]);
    
    let txn = await Mina.transaction(senderAccount, () => {
      zkApp.createStrategyCommitment(commitment, target, signature, senderAccount);
    });
    await txn.prove();
    await txn.sign([senderKey]).send();

    const performanceClaim = Field(175);
    const proof = Poseidon.hash([commitment, performanceClaim]);
    const verifierSignature = Signature.create(senderKey, [performanceClaim, proof]);
    
    txn = await Mina.transaction(senderAccount, () => {
      const result = zkApp.verifyStrategyPerformance(
        performanceClaim, 
        proof, 
        verifierSignature, 
        senderAccount
      );
      result.assertTrue();
    });
    await txn.prove();
    await txn.sign([senderKey]).send();

    const verificationCount = zkApp.verificationCount.get();
    expect(verificationCount).toEqual(Field(1));
  });
});
