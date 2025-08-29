import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { DelegationManagement } from "../target/types/delegation_management";
import { expect } from "chai";

describe("Enhanced Delegation System", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.DelegationManagement as Program<DelegationManagement>;
  
  let founder: anchor.web3.Keypair;
  let boardMember1: anchor.web3.Keypair;
  let boardMember2: anchor.web3.Keypair;
  let cto: anchor.web3.Keypair;
  
  let configPda: anchor.web3.PublicKey;
  let boardDelegationsPda: anchor.web3.PublicKey;

  before(async () => {
    founder = anchor.web3.Keypair.generate();
    boardMember1 = anchor.web3.Keypair.generate();
    boardMember2 = anchor.web3.Keypair.generate();
    cto = anchor.web3.Keypair.generate();

    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(founder.publicKey, 2 * anchor.web3.LAMPORTS_PER_SOL)
    );
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(boardMember1.publicKey, 1 * anchor.web3.LAMPORTS_PER_SOL)
    );

    [configPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("config")],
      program.programId
    );

    [boardDelegationsPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("board_delegations")],
      program.programId
    );
  });

  it("Initializes the delegation system", async () => {
    await program.methods
      .initialize()
      .accounts({
        signer: founder.publicKey,
        config: configPda,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([founder])
      .rpc();

    const config = await program.account.config.fetch(configPda);
    expect(config.founder.toString()).to.equal(founder.publicKey.toString());
    expect(config.isInitialized).to.be.true;
  });

  it("Founder delegates authority to board member", async () => {
    const [delegationPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), boardMember1.publicKey.toBuffer()],
      program.programId
    );

    const expiry = Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60; // 1 year from now

    await program.methods
      .delegateBoard(boardMember1.publicKey, new anchor.BN(expiry))
      .accounts({
        signer: founder.publicKey,
        config: configPda,
        boardDelegations: boardDelegationsPda,
        delegation: delegationPda,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([founder])
      .rpc();

    const boardDelegations = await program.account.boardDelegations.fetch(boardDelegationsPda);
    expect(boardDelegations.delegates).to.have.lengthOf(1);
    expect(boardDelegations.delegates[0].toString()).to.equal(boardMember1.publicKey.toString());

    const delegation = await program.account.delegation.fetch(delegationPda);
    expect(delegation.delegate.toString()).to.equal(boardMember1.publicKey.toString());
    expect(delegation.role).to.deep.equal({ board: {} });
    expect(delegation.delegatedBy.toString()).to.equal(founder.publicKey.toString());
    expect(delegation.expiry.toNumber()).to.equal(expiry);
  });

  it("Board member delegates authority to CTO", async () => {
    const [boardDelegationPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), boardMember1.publicKey.toBuffer()],
      program.programId
    );

    const [ctoDelegationPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), cto.publicKey.toBuffer()],
      program.programId
    );

    const expiry = Math.floor(Date.now() / 1000) + 180 * 24 * 60 * 60; // 6 months from now

    await program.methods
      .delegateCto(cto.publicKey, new anchor.BN(expiry))
      .accounts({
        signer: boardMember1.publicKey,
        config: configPda,
        callerDelegation: boardDelegationPda,
        delegation: ctoDelegationPda,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([boardMember1])
      .rpc();

    const delegation = await program.account.delegation.fetch(ctoDelegationPda);
    expect(delegation.delegate.toString()).to.equal(cto.publicKey.toString());
    expect(delegation.role).to.deep.equal({ cto: {} });
    expect(delegation.delegatedBy.toString()).to.equal(boardMember1.publicKey.toString());
    expect(delegation.expiry.toNumber()).to.equal(expiry);
  });

  it("Founder can revoke board member delegation", async () => {
    await program.methods
      .revokeBoard(boardMember1.publicKey)
      .accounts({
        signer: founder.publicKey,
        config: configPda,
        boardDelegations: boardDelegationsPda,
      })
      .signers([founder])
      .rpc();

    const boardDelegations = await program.account.boardDelegations.fetch(boardDelegationsPda);
    expect(boardDelegations.delegates).to.have.lengthOf(0);
  });

  it("Board member can revoke CTO delegation", async () => {
    const [delegationPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), boardMember1.publicKey.toBuffer()],
      program.programId
    );

    const expiry = Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60;

    await program.methods
      .delegateBoard(boardMember1.publicKey, new anchor.BN(expiry))
      .accounts({
        signer: founder.publicKey,
        config: configPda,
        boardDelegations: boardDelegationsPda,
        delegation: delegationPda,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([founder])
      .rpc();

    await program.methods
      .revokeCto(cto.publicKey)
      .accounts({
        signer: boardMember1.publicKey,
        config: configPda,
        callerDelegation: delegationPda,
      })
      .signers([boardMember1])
      .rpc();
  });

  it("Prevents unauthorized delegation", async () => {
    const unauthorizedUser = anchor.web3.Keypair.generate();
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(unauthorizedUser.publicKey, 1 * anchor.web3.LAMPORTS_PER_SOL)
    );

    const [delegationPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), boardMember2.publicKey.toBuffer()],
      program.programId
    );

    try {
      await program.methods
        .delegateBoard(boardMember2.publicKey, null)
        .accounts({
          signer: unauthorizedUser.publicKey,
          config: configPda,
          boardDelegations: boardDelegationsPda,
          delegation: delegationPda,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([unauthorizedUser])
        .rpc();
      
      expect.fail("Should have thrown unauthorized access error");
    } catch (error) {
      expect(error.message).to.include("UnauthorizedAccess");
    }
  });

  it("Prevents double initialization", async () => {
    try {
      await program.methods
        .initialize()
        .accounts({
          signer: founder.publicKey,
          config: configPda,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .signers([founder])
        .rpc();
      
      expect.fail("Should have thrown already initialized error");
    } catch (error) {
      expect(error.message).to.include("AlreadyInitialized");
    }
  });

  it("Supports multiple board members", async () => {
    const [delegation1Pda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), boardMember1.publicKey.toBuffer()],
      program.programId
    );

    const [delegation2Pda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("delegation"), boardMember2.publicKey.toBuffer()],
      program.programId
    );

    const expiry = Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60;

    await program.methods
      .delegateBoard(boardMember2.publicKey, new anchor.BN(expiry))
      .accounts({
        signer: founder.publicKey,
        config: configPda,
        boardDelegations: boardDelegationsPda,
        delegation: delegation2Pda,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([founder])
      .rpc();

    const boardDelegations = await program.account.boardDelegations.fetch(boardDelegationsPda);
    expect(boardDelegations.delegates).to.have.lengthOf(2);
    expect(boardDelegations.delegates.map(d => d.toString())).to.include(boardMember1.publicKey.toString());
    expect(boardDelegations.delegates.map(d => d.toString())).to.include(boardMember2.publicKey.toString());
  });
});
