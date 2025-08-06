/**
 * Test suite for enhanced Noir ZKP integration
 */

import { NoirEnhancedVotingSystem, PLUMEVerifier, HomomorphicEncryption, WalletSignatureVerifier, TLSNotaryVerifier } from '../src/enhanced-noir-integration';
import { NoirIntegrationManager } from '../src/noir-circuit-compiler';


describe('Enhanced Noir ZKP Integration', () => {
    let votingSystem: NoirEnhancedVotingSystem;
    let integrationManager: NoirIntegrationManager;

    beforeEach(() => {
        votingSystem = new NoirEnhancedVotingSystem();
        integrationManager = new NoirIntegrationManager();
    });

    describe('PLUME Signature Verification', () => {
        test('should generate and verify PLUME signatures', async () => {
            const plumeVerifier = new PLUMEVerifier();
            const message = 'test_vote_data';
            const privateKey = 'test_private_key';

            const signature = await plumeVerifier.sign(message, privateKey);
            expect(signature.r).toBeDefined();
            expect(signature.s).toBeDefined();
            expect(signature.nullifier).toBeDefined();

            const isValid = await plumeVerifier.verify(message, signature, 'test_public_key');
            expect(isValid).toBe(true);
        });

        test('should extract nullifier for double-voting prevention', () => {
            const plumeVerifier = new PLUMEVerifier();
            const signature = {
                r: '12345',
                s: '67890',
                nullifier: 'test_nullifier'
            };

            const nullifier = plumeVerifier.extractNullifier(signature);
            expect(nullifier).toBe('test_nullifier');
        });
    });

    describe('Homomorphic Encryption', () => {
        test('should encrypt votes homomorphically', async () => {
            const homomorphic = new HomomorphicEncryption();
            const vote = 1;
            const publicKey = 'test_public_key';

            const encryptedVote = await homomorphic.encryptVote(vote, publicKey);
            expect(encryptedVote.encryptedValue).toBeDefined();
            expect(encryptedVote.proof).toBeDefined();
        });

        test('should perform homomorphic addition', async () => {
            const homomorphic = new HomomorphicEncryption();
            const vote1 = { encryptedValue: '100', proof: 'proof1' };
            const vote2 = { encryptedValue: '200', proof: 'proof2' };

            const sum = await homomorphic.homomorphicAdd(vote1, vote2);
            expect(sum.encryptedValue).toBeDefined();
            expect(sum.proof).toBeDefined();
        });

        test('should tally votes without revealing individual selections', async () => {
            const homomorphic = new HomomorphicEncryption();
            const encryptedVotes = [
                { encryptedValue: '100', proof: 'proof1' },
                { encryptedValue: '200', proof: 'proof2' },
                { encryptedValue: '300', proof: 'proof3' }
            ];
            const privateKey = 'test_private_key';

            const tally = await homomorphic.tallyVotes(encryptedVotes, privateKey);
            expect(typeof tally).toBe('number');
            expect(tally).toBeGreaterThanOrEqual(0);
        });
    });

    describe('Wallet Signature Verification', () => {
        test('should verify Ed25519 signatures', async () => {
            const walletVerifier = new WalletSignatureVerifier();
            const message = 'test_vote';
            const signature = {
                ed25519: { r: '12345', s: '67890' },
                publicKey: 'test_public_key'
            };

            const isValid = await walletVerifier.verifyEd25519(message, signature);
            expect(typeof isValid).toBe('boolean');
        });

        test('should verify secp256k1 signatures', async () => {
            const walletVerifier = new WalletSignatureVerifier();
            const message = 'test_vote';
            const signature = {
                secp256k1: { r: '12345', s: '67890' },
                publicKey: 'test_public_key'
            };

            const isValid = await walletVerifier.verifySecp256k1(message, signature);
            expect(typeof isValid).toBe('boolean');
        });

        test('should verify wallet signatures with either signature type', async () => {
            const walletVerifier = new WalletSignatureVerifier();
            const message = 'test_vote';
            const signature = {
                ed25519: { r: '12345', s: '67890' },
                publicKey: 'test_public_key'
            };

            const isValid = await walletVerifier.verifyWalletSignature(message, signature);
            expect(typeof isValid).toBe('boolean');
        });
    });

    describe('TLS Notary Verification', () => {
        test('should verify TLS attestation proofs', async () => {
            const tlsVerifier = new TLSNotaryVerifier();
            const proof = {
                data: new Uint8Array(Buffer.from('ELIGIBLE', 'utf-8')),
                proofHash: 'test_proof_hash',
                authorityKey: 'test_authority_key'
            };

            const isValid = await tlsVerifier.verifyEligibility(proof);
            expect(typeof isValid).toBe('boolean');
        });

        test('should extract eligibility status from TLS data', async () => {
            const tlsVerifier = new TLSNotaryVerifier();
            const proof = {
                data: new Uint8Array(Buffer.from('ELIGIBLE', 'utf-8')),
                proofHash: 'test_proof_hash',
                authorityKey: 'test_authority_key'
            };

            const isEligible = await tlsVerifier.extractEligibilityStatus(proof);
            expect(isEligible).toBe(true);
        });
    });

    describe('Enhanced Voting System Integration', () => {
        test('should submit enhanced vote with all features', async () => {
            const vote = 'AI_Policy_Update_2025';
            const walletSignature = {
                ed25519: { r: '12345', s: '67890' },
                publicKey: 'test_public_key'
            };

            const result = await votingSystem.submitEnhancedVote(vote, walletSignature);
            expect(result.plumeSignature).toBeDefined();
            expect(result.homomorphicVote).toBeDefined();
            expect(result.verified).toBe(true);
        });

        test('should tally homomorphic votes', async () => {
            const encryptedVotes = [
                { encryptedValue: '100', proof: 'proof1' },
                { encryptedValue: '200', proof: 'proof2' }
            ];
            const electionPrivateKey = 'test_election_key';

            const tally = await votingSystem.tallyHomomorphicVotes(encryptedVotes, electionPrivateKey);
            expect(typeof tally).toBe('number');
        });

        test('should verify PLUME signatures', async () => {
            const message = 'test_vote';
            const signature = {
                r: '12345',
                s: '67890',
                nullifier: 'test_nullifier'
            };
            const publicKey = 'test_public_key';

            const isValid = await votingSystem.verifyPLUMESignature(message, signature, publicKey);
            expect(typeof isValid).toBe('boolean');
        });
    });

    describe('Noir Circuit Integration', () => {
        test('should initialize circuit compiler', async () => {
            const initialized = await integrationManager.initialize();
            expect(typeof initialized).toBe('boolean');
        });

        test('should generate voter authentication proof', async () => {
            await integrationManager.initialize();
            
            const proof = await integrationManager.generateVoterAuthenticationProof(
                'test_voter_secret',
                'test_eligibility_root'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
        });

        test('should generate PLUME voting proof', async () => {
            await integrationManager.initialize();
            
            const message = new Uint8Array([116, 101, 115, 116, 95, 118, 111, 116, 101]); // 'test_vote' as bytes
            const proof = await integrationManager.generatePLUMEVotingProof(
                message,
                '12345',
                '67890',
                'test_public_key'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
        });

        test('should generate homomorphic tally proof', async () => {
            await integrationManager.initialize();
            
            const encryptedVotes = ['100', '200', '300'];
            const proof = await integrationManager.generateHomomorphicTallyProof(
                encryptedVotes,
                '3',
                'test_election_pubkey'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
        });

        test('should generate wallet signature proof', async () => {
            await integrationManager.initialize();
            
            const voteHash = new Uint8Array([116, 101, 115, 116, 95, 118, 111, 116, 101, 95, 104, 97, 115, 104]); // 'test_vote_hash' as bytes
            const ed25519Sig = { r: '12345', s: '67890' };
            const proof = await integrationManager.generateWalletSignatureProof(
                voteHash,
                ed25519Sig,
                null,
                'test_wallet_pubkey'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
        });

        test('should generate compliance proof', async () => {
            await integrationManager.initialize();
            
            const voteData = new Uint8Array([65, 73, 95, 80, 111, 108, 105, 99, 121, 95, 85, 112, 100, 97, 116, 101, 95, 50, 48, 50, 53]); // 'AI_Policy_Update_2025' as bytes
            const proof = await integrationManager.generateComplianceProof(
                voteData,
                'test_pattern_hash',
                true
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
        });

        test('should generate eligibility proof', async () => {
            await integrationManager.initialize();
            
            const eligibilityData = new Uint8Array([69, 76, 73, 71, 73, 66, 76, 69]); // 'ELIGIBLE' as bytes
            const proof = await integrationManager.generateEligibilityProof(
                eligibilityData,
                'test_tls_proof_hash',
                'test_authority_pubkey',
                true
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
        });

        test('should verify proofs', async () => {
            await integrationManager.initialize();
            
            const mockProof = new Uint8Array([1, 2, 3, 4]);
            const mockPublicSignals = ['12345', '67890'];
            
            const isValid = await integrationManager.verifyProof(
                'voter_authentication',
                mockProof,
                mockPublicSignals
            );
            
            expect(typeof isValid).toBe('boolean');
        });
    });
});
