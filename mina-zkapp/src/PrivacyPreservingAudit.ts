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
  MerkleTree,
  MerkleWitness,
  Circuit,
} from 'o1js';

class MerkleWitness8 extends MerkleWitness(8) {}

export class PrivacyPreservingAudit extends SmartContract {
  @state(Field) auditRoot = State<Field>();
  @state(Field) auditCount = State<Field>();
  @state(Bool) verificationEnabled = State<Bool>();
  @state(Field) lastVerificationTime = State<Field>();

  deploy(args: DeployArgs) {
    super.deploy(args);
    this.setPermissions({
      ...Permissions.default(),
      editState: Permissions.proofOrSignature(),
    });
  }

  @method init() {
    super.init();
    const emptyTreeRoot = new MerkleTree(8).getRoot();
    this.auditRoot.set(emptyTreeRoot);
    this.auditCount.set(Field(0));
    this.verificationEnabled.set(Bool(true));
    this.lastVerificationTime.set(Field(0));
  }

  @method submitPrivateAuditProof(
    auditDataHash: Field,
    merkleWitness: MerkleWitness8,
    newRoot: Field,
    auditorSignature: Signature,
    auditorPublicKey: PublicKey,
    timestamp: Field
  ): Bool {
    const isEnabled = this.verificationEnabled.get();
    this.verificationEnabled.requireEquals(isEnabled);
    isEnabled.assertTrue();

    const currentRoot = this.auditRoot.get();
    this.auditRoot.requireEquals(currentRoot);

    const proofHash = Poseidon.hash([auditDataHash, timestamp]);
    auditorSignature.verify(auditorPublicKey, [proofHash]);

    const calculatedRoot = merkleWitness.calculateRoot(auditDataHash);
    calculatedRoot.assertEquals(newRoot);

    this.auditRoot.set(newRoot);

    const currentCount = this.auditCount.get();
    this.auditCount.requireEquals(currentCount);
    this.auditCount.set(currentCount.add(1));

    this.lastVerificationTime.set(timestamp);

    return Bool(true);
  }

  @method verifyAuditInclusion(
    auditDataHash: Field,
    merkleWitness: MerkleWitness8
  ): Bool {
    const currentRoot = this.auditRoot.get();
    this.auditRoot.requireEquals(currentRoot);

    const calculatedRoot = merkleWitness.calculateRoot(auditDataHash);
    const isIncluded = calculatedRoot.equals(currentRoot);

    return isIncluded;
  }

  @method verifyPrivacyPreservingClaim(
    claimHash: Field,
    proofOfKnowledge: Field,
    verifierSignature: Signature,
    verifierPublicKey: PublicKey
  ): Bool {
    const isEnabled = this.verificationEnabled.get();
    this.verificationEnabled.requireEquals(isEnabled);
    isEnabled.assertTrue();

    const expectedProof = Poseidon.hash([claimHash, Field(42)]);
    proofOfKnowledge.assertEquals(expectedProof);

    verifierSignature.verify(verifierPublicKey, [claimHash, proofOfKnowledge]);

    return Bool(true);
  }

  @method batchVerifyAudits(
    auditHashes: Field[],
    batchProof: Field,
    batchSignature: Signature,
    batchVerifierPublicKey: PublicKey
  ): Bool {
    const isEnabled = this.verificationEnabled.get();
    this.verificationEnabled.requireEquals(isEnabled);
    isEnabled.assertTrue();

    let combinedHash = Field(0);
    for (let i = 0; i < auditHashes.length; i++) {
      combinedHash = Poseidon.hash([combinedHash, auditHashes[i]]);
    }

    const expectedBatchProof = Poseidon.hash([combinedHash, Field(auditHashes.length)]);
    batchProof.assertEquals(expectedBatchProof);

    batchSignature.verify(batchVerifierPublicKey, [batchProof]);

    const currentCount = this.auditCount.get();
    this.auditCount.requireEquals(currentCount);
    this.auditCount.set(currentCount.add(Field(auditHashes.length)));

    return Bool(true);
  }

  @method updateVerificationStatus(
    enabled: Bool,
    adminSignature: Signature,
    adminPublicKey: PublicKey
  ) {
    const statusMessage = Poseidon.hash([Field(enabled.toField().toBigInt())]);
    adminSignature.verify(adminPublicKey, [statusMessage]);
    
    this.verificationEnabled.set(enabled);
  }

  @method getAuditStatistics(): Field {
    const currentCount = this.auditCount.get();
    this.auditCount.requireEquals(currentCount);
    
    const lastTime = this.lastVerificationTime.get();
    this.lastVerificationTime.requireEquals(lastTime);

    const statsHash = Poseidon.hash([currentCount, lastTime]);
    return statsHash;
  }
}
