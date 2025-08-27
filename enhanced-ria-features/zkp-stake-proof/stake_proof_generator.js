/**
 * Zero-Knowledge Stake Proof Generator
 * Generates and verifies ZK proofs for anonymous stake-based voting
 * Integrates with Circom circuits and snarkjs for Groth16 proofs
 */

const snarkjs = require("snarkjs");
const circomlib = require("circomlib");
const crypto = require("crypto");
const fs = require("fs").promises;
const path = require("path");

class StakeProofGenerator {
    constructor(config = {}) {
        this.config = {
            circuitPath: config.circuitPath || "./stake_proof_circuit.circom",
            wasmPath: config.wasmPath || "./stake_proof.wasm",
            zkeyPath: config.zkeyPath || "./stake_proof_final.zkey",
            vkeyPath: config.vkeyPath || "./verification_key.json",
            merkleTreeDepth: config.merkleTreeDepth || 20,
            ...config
        };
        
        this.merkleTree = null;
        this.stakes = new Map(); // walletAddress -> stakeAmount
        this.nullifiers = new Set(); // Track used nullifiers
    }
    
    /**
     * Initialize the stake proof system with trusted setup
     */
    async initialize() {
        try {
            const wasmExists = await this.fileExists(this.config.wasmPath);
            const zkeyExists = await this.fileExists(this.config.zkeyPath);
            
            if (!wasmExists || !zkeyExists) {
                console.log("Circuit files not found, compiling circuit...");
                await this.compileCircuit();
                await this.setupTrustedSetup();
            }
            
            this.verificationKey = JSON.parse(
                await fs.readFile(this.config.vkeyPath, "utf8")
            );
            
            console.log("Stake proof system initialized successfully");
            return true;
        } catch (error) {
            console.error("Failed to initialize stake proof system:", error);
            return false;
        }
    }
    
    /**
     * Add stake to the system and update Merkle tree
     */
    async addStake(walletAddress, stakeAmount, walletSecret) {
        if (stakeAmount <= 0) {
            throw new Error("Stake amount must be positive");
        }
        
        const stakeCommitment = this.generateStakeCommitment(stakeAmount, walletSecret);
        
        this.stakes.set(walletAddress, {
            amount: stakeAmount,
            commitment: stakeCommitment,
            secret: walletSecret
        });
        
        await this.rebuildMerkleTree();
        
        console.log(`Added stake: ${walletAddress} -> ${stakeAmount}`);
        return stakeCommitment;
    }
    
    /**
     * Generate zero-knowledge proof of stake
     */
    async generateStakeProof(walletAddress, minStakeThreshold, votingRoundId) {
        const stake = this.stakes.get(walletAddress);
        if (!stake) {
            throw new Error("Wallet not found in stake registry");
        }
        
        if (stake.amount < minStakeThreshold) {
            throw new Error("Insufficient stake for voting");
        }
        
        const nullifier = this.generateNullifier(stake.secret, this.merkleTree.root, votingRoundId);
        
        if (this.nullifiers.has(nullifier)) {
            throw new Error("Vote already cast for this round");
        }
        
        const merkleProof = this.getMerkleProof(stake.commitment);
        
        const circuitInputs = {
            merkleRoot: this.merkleTree.root,
            minStakeThreshold: minStakeThreshold.toString(),
            nullifierHash: nullifier,
            
            stakeAmount: stake.amount.toString(),
            walletSecret: stake.secret,
            merkleProof: merkleProof.pathElements,
            merkleIndices: merkleProof.pathIndices
        };
        
        console.log("Generating ZK proof...");
        const { proof, publicSignals } = await snarkjs.groth16.fullProve(
            circuitInputs,
            this.config.wasmPath,
            this.config.zkeyPath
        );
        
        this.nullifiers.add(nullifier);
        
        return {
            proof: this.formatProof(proof),
            publicSignals,
            nullifier,
            merkleRoot: this.merkleTree.root,
            timestamp: Date.now()
        };
    }
    
    /**
     * Verify zero-knowledge stake proof
     */
    async verifyStakeProof(proof, publicSignals, expectedMerkleRoot) {
        try {
            const isValid = await snarkjs.groth16.verify(
                this.verificationKey,
                publicSignals,
                proof
            );
            
            if (!isValid) {
                return { valid: false, reason: "Invalid cryptographic proof" };
            }
            
            const [merkleRoot, minStakeThreshold, nullifierHash] = publicSignals;
            
            if (merkleRoot !== expectedMerkleRoot) {
                return { valid: false, reason: "Merkle root mismatch" };
            }
            
            if (this.nullifiers.has(nullifierHash)) {
                return { valid: false, reason: "Nullifier already used (double voting)" };
            }
            
            const validStake = publicSignals[3]; // Output from circuit
            if (validStake !== "1") {
                return { valid: false, reason: "Insufficient stake proven" };
            }
            
            return {
                valid: true,
                nullifier: nullifierHash,
                minStakeThreshold: minStakeThreshold,
                merkleRoot: merkleRoot
            };
            
        } catch (error) {
            console.error("Proof verification error:", error);
            return { valid: false, reason: "Verification error", error: error.message };
        }
    }
    
    /**
     * Generate stake commitment using Poseidon hash
     */
    generateStakeCommitment(stakeAmount, walletSecret) {
        const poseidon = circomlib.poseidon;
        return poseidon([BigInt(stakeAmount), BigInt(walletSecret)]).toString();
    }
    
    /**
     * Generate nullifier to prevent double voting
     */
    generateNullifier(walletSecret, merkleRoot, votingRoundId) {
        const poseidon = circomlib.poseidon;
        const roundHash = crypto.createHash('sha256')
            .update(merkleRoot + votingRoundId)
            .digest('hex');
        return poseidon([BigInt(walletSecret), BigInt('0x' + roundHash.slice(0, 16))]).toString();
    }
    
    /**
     * Rebuild Merkle tree from current stakes
     */
    async rebuildMerkleTree() {
        const commitments = Array.from(this.stakes.values()).map(stake => stake.commitment);
        
        const treeSize = Math.pow(2, this.config.merkleTreeDepth);
        while (commitments.length < treeSize) {
            commitments.push("0"); // Empty leaf
        }
        
        this.merkleTree = this.buildMerkleTree(commitments);
    }
    
    /**
     * Build Merkle tree from leaf commitments
     */
    buildMerkleTree(leaves) {
        const poseidon = circomlib.poseidon;
        
        let currentLevel = leaves.map(leaf => BigInt(leaf));
        const tree = [currentLevel];
        
        while (currentLevel.length > 1) {
            const nextLevel = [];
            
            for (let i = 0; i < currentLevel.length; i += 2) {
                const left = currentLevel[i];
                const right = i + 1 < currentLevel.length ? currentLevel[i + 1] : BigInt(0);
                const parent = poseidon([left, right]);
                nextLevel.push(parent);
            }
            
            tree.push(nextLevel);
            currentLevel = nextLevel;
        }
        
        return {
            root: currentLevel[0].toString(),
            tree: tree,
            leaves: leaves
        };
    }
    
    /**
     * Get Merkle proof for a specific commitment
     */
    getMerkleProof(commitment) {
        const leafIndex = this.merkleTree.leaves.indexOf(commitment);
        if (leafIndex === -1) {
            throw new Error("Commitment not found in Merkle tree");
        }
        
        const pathElements = [];
        const pathIndices = [];
        
        let currentIndex = leafIndex;
        
        for (let level = 0; level < this.merkleTree.tree.length - 1; level++) {
            const currentLevel = this.merkleTree.tree[level];
            const isRightNode = currentIndex % 2 === 1;
            const siblingIndex = isRightNode ? currentIndex - 1 : currentIndex + 1;
            
            if (siblingIndex < currentLevel.length) {
                pathElements.push(currentLevel[siblingIndex].toString());
            } else {
                pathElements.push("0");
            }
            
            pathIndices.push(isRightNode ? 1 : 0);
            currentIndex = Math.floor(currentIndex / 2);
        }
        
        return {
            pathElements,
            pathIndices,
            leafIndex
        };
    }
    
    /**
     * Format proof for transmission
     */
    formatProof(proof) {
        return {
            pi_a: [proof.pi_a[0].toString(), proof.pi_a[1].toString()],
            pi_b: [[proof.pi_b[0][1].toString(), proof.pi_b[0][0].toString()],
                   [proof.pi_b[1][1].toString(), proof.pi_b[1][0].toString()]],
            pi_c: [proof.pi_c[0].toString(), proof.pi_c[1].toString()]
        };
    }
    
    /**
     * Compile Circom circuit
     */
    async compileCircuit() {
        const { exec } = require('child_process');
        const util = require('util');
        const execAsync = util.promisify(exec);
        
        try {
            await execAsync(`circom ${this.config.circuitPath} --wasm --r1cs --sym`);
            console.log("Circuit compiled successfully");
        } catch (error) {
            console.error("Circuit compilation failed:", error);
            throw error;
        }
    }
    
    /**
     * Setup trusted ceremony (for development - use real ceremony in production)
     */
    async setupTrustedSetup() {
        const { exec } = require('child_process');
        const util = require('util');
        const execAsync = util.promisify(exec);
        
        try {
            await execAsync(`snarkjs groth16 setup stake_proof_circuit.r1cs powersOfTau28_hez_final_15.ptau stake_proof_0000.zkey`);
            await execAsync(`snarkjs zkey contribute stake_proof_0000.zkey stake_proof_final.zkey --name="First contribution" -v`);
            await execAsync(`snarkjs zkey export verificationkey stake_proof_final.zkey verification_key.json`);
            
            console.log("Trusted setup completed");
        } catch (error) {
            console.error("Trusted setup failed:", error);
            throw error;
        }
    }
    
    /**
     * Check if file exists
     */
    async fileExists(filePath) {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }
    
    /**
     * Export stake registry for backup/restore
     */
    exportStakeRegistry() {
        return {
            stakes: Array.from(this.stakes.entries()),
            merkleTree: this.merkleTree,
            nullifiers: Array.from(this.nullifiers)
        };
    }
    
    /**
     * Import stake registry from backup
     */
    importStakeRegistry(registryData) {
        this.stakes = new Map(registryData.stakes);
        this.merkleTree = registryData.merkleTree;
        this.nullifiers = new Set(registryData.nullifiers);
    }
}

module.exports = { StakeProofGenerator };
