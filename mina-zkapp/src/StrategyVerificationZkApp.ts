import {
  SmartContract,
  state,
  State,
  method,
  DeployArgs,
  Permissions,
  Field,
  Signature,
  PublicKey,
  Poseidon,
  Bool,
} from 'o1js';

export class StrategyVerificationZkApp extends SmartContract {
  @state(Field) strategyCommitment = State<Field>();
  @state(Field) performanceTarget = State<Field>();
  @state(Field) verificationCount = State<Field>();
  @state(Bool) isActive = State<Bool>();

  deploy(args: DeployArgs) {
    super.deploy(args);
    this.setPermissions({
      ...Permissions.default(),
      editState: Permissions.proofOrSignature(),
    });
  }

  @method init() {
    super.init();
    this.strategyCommitment.set(Field(0));
    this.performanceTarget.set(Field(0));
    this.verificationCount.set(Field(0));
    this.isActive.set(Bool(false));
  }

  @method createStrategyCommitment(
    commitment: Field,
    target: Field,
    creatorSignature: Signature,
    creatorPublicKey: PublicKey
  ) {
    creatorSignature.verify(creatorPublicKey, [commitment, target]);

    this.strategyCommitment.set(commitment);
    this.performanceTarget.set(target);
    this.isActive.set(Bool(true));
    this.verificationCount.set(Field(0));
  }

  @method verifyStrategyPerformance(
    performanceClaim: Field,
    proof: Field,
    verifierSignature: Signature,
    verifierPublicKey: PublicKey
  ): Bool {
    const currentCommitment = this.strategyCommitment.get();
    this.strategyCommitment.requireEquals(currentCommitment);
    
    const currentTarget = this.performanceTarget.get();
    this.performanceTarget.requireEquals(currentTarget);
    
    const isActive = this.isActive.get();
    this.isActive.requireEquals(isActive);
    isActive.assertTrue();

    const expectedProof = Poseidon.hash([currentCommitment, performanceClaim]);
    proof.assertEquals(expectedProof);

    verifierSignature.verify(verifierPublicKey, [performanceClaim, proof]);

    const meetsTarget = performanceClaim.greaterThanOrEqual(currentTarget);

    const currentCount = this.verificationCount.get();
    this.verificationCount.requireEquals(currentCount);
    this.verificationCount.set(currentCount.add(1));

    return meetsTarget;
  }

  @method deactivateStrategy(
    ownerSignature: Signature,
    ownerPublicKey: PublicKey
  ) {
    const currentCommitment = this.strategyCommitment.get();
    this.strategyCommitment.requireEquals(currentCommitment);
    
    ownerSignature.verify(ownerPublicKey, [currentCommitment]);
    
    this.isActive.set(Bool(false));
  }
}
