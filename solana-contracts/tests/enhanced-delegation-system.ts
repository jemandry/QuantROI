import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { DelegationManagement } from "../target/types/delegation_management";
import { expect } from "chai";

describe("Enhanced Smart Contract Delegation System", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.DelegationManagement as Program<DelegationManagement>;
  
  let delegationAccount: anchor.web3.Keypair;
  let ceoKeypair: anchor.web3.Keypair;
  let assistantKeypair: anchor.web3.Keypair;
  let aiAuditorKeypair: anchor.web3.Keypair;

  beforeEach(async () => {
    delegationAccount = anchor.web3.Keypair.generate();
    ceoKeypair = anchor.web3.Keypair.generate();
    assistantKeypair = anchor.web3.Keypair.generate();
    aiAuditorKeypair = anchor.web3.Keypair.generate();
  });

  it("Creates CEO-to-assistant delegation with enhanced features", async () => {
    const tx = await program.methods
      .initializeDelegation(
        assistantKeypair.publicKey,
        new anchor.BN(1000000),
        { ceoToAssistant: {} }
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        bankAuthority: ceoKeypair.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([delegationAccount, ceoKeypair])
      .rpc();

    const delegationData = await program.account.delegationAccount.fetch(
      delegationAccount.publicKey
    );

    expect(delegationData.delegationType).to.deep.equal({ ceoToAssistant: {} });
    expect(delegationData.aiPolicyPubkey.toString()).to.equal(
      assistantKeypair.publicKey.toString()
    );
  });

  it("Assigns duty and completes with AI auditor assessment", async () => {
    await program.methods
      .initializeDelegation(
        assistantKeypair.publicKey,
        new anchor.BN(1000000),
        { ceoToAssistant: {} }
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        bankAuthority: ceoKeypair.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([delegationAccount, ceoKeypair])
      .rpc();

    await program.methods
      .assignDuty(
        new anchor.BN(1),
        "Complete project plan with AI optimization",
        assistantKeypair.publicKey,
        new anchor.BN(Date.now() + 86400000),
        new anchor.BN(100000),
        true,
        true
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        assigner: ceoKeypair.publicKey,
      })
      .signers([ceoKeypair])
      .rpc();

    const completionProof = Buffer.from("Project plan completed with AI recommendations", "utf-8");
    await program.methods
      .completeDuty(new anchor.BN(1), Array.from(completionProof))
      .accounts({
        delegation: delegationAccount.publicKey,
        assignee: assistantKeypair.publicKey,
      })
      .signers([assistantKeypair])
      .rpc();

    await program.methods
      .aiAuditDuty(
        new anchor.BN(1),
        85,
        90,
        ["High quality work", "Met all requirements", "Innovative approach"]
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        aiAuditor: aiAuditorKeypair.publicKey,
      })
      .signers([aiAuditorKeypair])
      .rpc();

    const delegationData = await program.account.delegationAccount.fetch(
      delegationAccount.publicKey
    );

    const dutyRecord = delegationData.dutyRecords.find(
      (duty) => duty.dutyId.toNumber() === 1
    );

    expect(dutyRecord.status).to.deep.equal({ aiAudited: {} });
    expect(dutyRecord.completenessScore).to.equal(85);
    expect(dutyRecord.sincerityScore).to.equal(90);
  });

  it("Configures VRF-based random audit mechanism", async () => {
    await program.methods
      .initializeDelegation(
        assistantKeypair.publicKey,
        new anchor.BN(1000000),
        { ceoToAssistant: {} }
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        bankAuthority: ceoKeypair.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([delegationAccount, ceoKeypair])
      .rpc();

    await program.methods
      .configureVrfAudit(
        { random: {} },
        { weekly: {} },
        null,
        null
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        authority: ceoKeypair.publicKey,
      })
      .signers([ceoKeypair])
      .rpc();

    const auditorKeypair = anchor.web3.Keypair.generate();
    await program.methods
      .executeRandomAudit(
        ["All duties completed on time", "No compliance issues found", "VRF randomness verified"],
        95
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        auditor: auditorKeypair.publicKey,
      })
      .signers([auditorKeypair])
      .rpc();

    const delegationData = await program.account.delegationAccount.fetch(
      delegationAccount.publicKey
    );

    expect(delegationData.auditConfiguration).to.not.be.null;
    expect(delegationData.auditConfiguration.auditHistory).to.have.length(1);
    expect(delegationData.auditConfiguration.auditHistory[0].complianceScore).to.equal(95);
    expect(delegationData.auditConfiguration.vrfSeed).to.not.be.null;
  });

  it("Configures and executes employee voting system", async () => {
    await program.methods
      .initializeDelegation(
        assistantKeypair.publicKey,
        new anchor.BN(1000000),
        { employeeVoting: {} }
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        bankAuthority: ceoKeypair.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([delegationAccount, ceoKeypair])
      .rpc();

    await program.methods
      .configureVotingSystem(
        { employeeVoting: {} },
        25,
        75,
        true,
        0.8,
        true
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        authority: ceoKeypair.publicKey,
      })
      .signers([ceoKeypair])
      .rpc();

    const employeeKeypair = anchor.web3.Keypair.generate();
    await program.methods
      .submitVote(
        new anchor.BN(1),
        true,
        { employeeVoting: {} },
        0.85
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        voter: employeeKeypair.publicKey,
      })
      .signers([employeeKeypair])
      .rpc();

    const delegationData = await program.account.delegationAccount.fetch(
      delegationAccount.publicKey
    );

    expect(delegationData.votingConfiguration).to.not.be.null;
    expect(delegationData.votingConfiguration.employeeWeightPercent).to.equal(25);
    expect(delegationData.votingConfiguration.aiClassificationEnabled).to.be.true;
  });

  it("Verifies delivery with oracle integration", async () => {
    await program.methods
      .initializeDelegation(
        assistantKeypair.publicKey,
        new anchor.BN(1000000),
        { projectManagement: {} }
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        bankAuthority: ceoKeypair.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([delegationAccount, ceoKeypair])
      .rpc();

    const termsHash = Array.from(new Uint8Array(32).fill(1));
    const milestonePayments = [
      {
        milestoneId: new anchor.BN(1),
        description: "Phase 1 completion",
        amount: new anchor.BN(50000),
        completionCriteria: "Oracle verified delivery",
        verificationRequired: true,
        oracleVerification: true,
        completed: false,
        paymentExecuted: false,
      }
    ];

    await program.methods
      .setupContractTermsWithOracle(
        termsHash,
        true,
        ["Oracle verification required", "Quality check passed"],
        milestonePayments,
        { weekly: {} },
        true
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        authority: ceoKeypair.publicKey,
        oracleFeed: null,
      })
      .signers([ceoKeypair])
      .rpc();

    await program.methods
      .assignDuty(
        new anchor.BN(1),
        "Deliver Phase 1 with oracle verification",
        assistantKeypair.publicKey,
        new anchor.BN(Date.now() + 86400000),
        new anchor.BN(50000),
        true,
        false
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        assigner: ceoKeypair.publicKey,
      })
      .signers([ceoKeypair])
      .rpc();

    const completionProof = Buffer.from("Phase 1 delivered", "utf-8");
    await program.methods
      .completeDuty(new anchor.BN(1), Array.from(completionProof))
      .accounts({
        delegation: delegationAccount.publicKey,
        assignee: assistantKeypair.publicKey,
      })
      .signers([assistantKeypair])
      .rpc();

    await program.methods
      .verifyDeliveryWithOracle(
        new anchor.BN(1),
        "Quality standards met"
      )
      .accounts({
        delegation: delegationAccount.publicKey,
        verifier: ceoKeypair.publicKey,
        oracleFeed: null,
      })
      .signers([ceoKeypair])
      .rpc();

    const delegationData = await program.account.delegationAccount.fetch(
      delegationAccount.publicKey
    );

    const dutyRecord = delegationData.dutyRecords.find(
      (duty) => duty.dutyId.toNumber() === 1
    );

    expect(dutyRecord.status).to.deep.equal({ verified: {} });
    expect(dutyRecord.paymentTriggered).to.be.true;
    expect(delegationData.contractTerms.oracleVerificationRequired).to.be.true;
  });
});
