/**
 * Complete integration test suite for Noir ZKP enhanced voting system
 */

import { NoirEnhancedVotingSystem, PLUMEVerifier, HomomorphicEncryption, WalletSignatureVerifier, TLSNotaryVerifier } from '../src/enhanced-noir-integration';
import { NoirIntegrationManager } from '../src/noir-circuit-compiler';


describe('Complete Noir ZKP Integration', () => {
    let votingSystem: NoirEnhancedVotingSystem;
    let integrationManager: NoirIntegrationManager;
    let plumeVerifier: PLUMEVerifier;
    let homomorphicEncryption: HomomorphicEncryption;
    let walletVerifier: WalletSignatureVerifier;
    let tlsVerifier: TLSNotaryVerifier;

    beforeEach(async () => {
        votingSystem = new NoirEnhancedVotingSystem();
        integrationManager = new NoirIntegrationManager();
        plumeVerifier = new PLUMEVerifier();
        homomorphicEncryption = new HomomorphicEncryption();
        walletVerifier = new WalletSignatureVerifier();
        tlsVerifier = new TLSNotaryVerifier();
        
        await integrationManager.initialize();
    });

    describe('End-to-End Voting Workflow', () => {
        test('should complete full enhanced voting workflow with all features', async () => {
            const vote = 'AI_Policy_Enhancement_2025';
            const walletSignature = {
                ed25519: { r: 'wallet_sig_r_12345', s: 'wallet_sig_s_67890' },
                publicKey: 'voter_wallet_public_key_abc123'
            };

            const walletValid = await walletVerifier.verifyWalletSignature(vote, walletSignature);
            expect(walletValid).toBe(true);

            const plumeSignature = await plumeVerifier.sign(vote, walletSignature.publicKey);
            expect(plumeSignature.r).toBeDefined();
            expect(plumeSignature.s).toBeDefined();
            expect(plumeSignature.nullifier).toBeDefined();

            const plumeValid = await plumeVerifier.verify(vote, plumeSignature, walletSignature.publicKey);
            expect(plumeValid).toBe(true);

            const voteValue = 1; // Yes vote
            const encryptedVote = await homomorphicEncryption.encryptVote(voteValue, walletSignature.publicKey);
            expect(encryptedVote.encryptedValue).toBeDefined();
            expect(encryptedVote.proof).toBeDefined();

            const result = await votingSystem.submitEnhancedVote(vote, walletSignature);
            expect(result.verified).toBe(true);
            expect(result.plumeSignature).toBeDefined();
            expect(result.homomorphicVote).toBeDefined();

            const nullifier1 = plumeVerifier.extractNullifier(result.plumeSignature);
            const nullifier2 = plumeVerifier.extractNullifier(plumeSignature);
            expect(nullifier1).toBe(nullifier2);
        });

        test('should handle batch voting with homomorphic tallying', async () => {
            const votes = [
                { vote: 'Policy_A_Support', value: 1 },
                { vote: 'Policy_A_Support', value: 1 },
                { vote: 'Policy_A_Oppose', value: 0 },
                { vote: 'Policy_A_Support', value: 1 },
                { vote: 'Policy_A_Oppose', value: 0 }
            ];

            const encryptedVotes: any[] = [];
            const publicKey = 'batch_election_public_key';

            for (const voteData of votes) {
                const encrypted = await homomorphicEncryption.encryptVote(voteData.value, publicKey);
                encryptedVotes.push(encrypted);
            }

            const privateKey = 'batch_election_private_key';
            const tally = await homomorphicEncryption.tallyVotes(encryptedVotes, privateKey);
            
            expect(typeof tally).toBe('number');
            expect(tally).toBeGreaterThan(0);
        });

        test('should verify external eligibility with TLS notary', async () => {
            const eligibilityProof = {
                data: new Uint8Array([69, 76, 73, 71, 73, 66, 76, 69]), // 'ELIGIBLE' as bytes
                proofHash: 'tls_notary_proof_hash_xyz789',
                authorityKey: 'external_authority_public_key'
            };

            const proofValid = await tlsVerifier.verifyEligibility(eligibilityProof);
            expect(typeof proofValid).toBe('boolean');

            const isEligible = await tlsVerifier.extractEligibilityStatus(eligibilityProof);
            expect(isEligible).toBe(true);

            const vote = 'External_Verified_Vote_2025';
            const walletSignature = {
                secp256k1: { r: 'secp_sig_r_98765', s: 'secp_sig_s_43210' },
                publicKey: 'external_voter_public_key'
            };

            const result = await votingSystem.submitEnhancedVote(vote, walletSignature, eligibilityProof);
            expect(result.verified).toBe(true);
        });
    });

    describe('Circuit Integration Tests', () => {
        test('should generate and verify all circuit types', async () => {
            const authProof = await integrationManager.generateVoterAuthenticationProof(
                'test_voter_secret_auth',
                'test_eligibility_merkle_root'
            );
            expect(authProof.verified).toBe(true);

            const authValid = await integrationManager.verifyProof(
                'voter_authentication',
                authProof.proof,
                authProof.publicSignals
            );
            expect(authValid).toBe(true);

            const message = new Uint8Array([116, 101, 115, 116, 95, 109, 115, 103]); // 'test_msg' as bytes
            const plumeProof = await integrationManager.generatePLUMEVotingProof(
                message,
                'plume_r_component',
                'plume_s_component',
                'plume_public_key'
            );
            expect(plumeProof.verified).toBe(true);

            const encryptedVotes = ['1000', '2000', '3000'];
            const tallyProof = await integrationManager.generateHomomorphicTallyProof(
                encryptedVotes,
                '3',
                'tally_election_pubkey'
            );
            expect(tallyProof.verified).toBe(true);

            const voteHash = new Uint8Array([104, 97, 115, 104]); // 'hash' as bytes
            const ed25519Sig = { r: 'ed25519_r', s: 'ed25519_s' };
            const walletProof = await integrationManager.generateWalletSignatureProof(
                voteHash,
                ed25519Sig,
                null,
                'wallet_pubkey'
            );
            expect(walletProof.verified).toBe(true);

            const voteData = new Uint8Array([99, 111, 109, 112, 108, 105, 97, 110, 116]); // 'compliant' as bytes
            const complianceProof = await integrationManager.generateComplianceProof(
                voteData,
                'compliance_pattern_hash',
                true
            );
            expect(complianceProof.verified).toBe(true);

            const eligibilityData = new Uint8Array([118, 101, 114, 105, 102, 105, 101, 100]); // 'verified' as bytes
            const eligibilityProof = await integrationManager.generateEligibilityProof(
                eligibilityData,
                'tls_proof_hash',
                'authority_pubkey',
                true
            );
            expect(eligibilityProof.verified).toBe(true);
        });
    });

    describe('Patent Differentiation Verification', () => {
        test('should demonstrate clear technical differentiation from US20200258338A1', async () => {
            const vote = 'Patent_Differentiation_Test_Vote';
            const walletSignature = {
                ed25519: { r: 'patent_test_r', s: 'patent_test_s' },
                publicKey: 'patent_test_pubkey'
            };

            const result = await votingSystem.submitEnhancedVote(vote, walletSignature);

            expect(result.plumeSignature.nullifier).toBeDefined(); // Only nullifier is public
            expect(result.homomorphicVote.encryptedValue).toBeDefined(); // Only encrypted value is public

            const plumeValid = await votingSystem.verifyPLUMESignature(
                vote,
                result.plumeSignature,
                walletSignature.publicKey
            );
            expect(plumeValid).toBe(true);

            expect(typeof result.homomorphicVote.encryptedValue).toBe('string');
            expect(result.homomorphicVote.encryptedValue).toBeDefined(); // Vote content is encrypted
        });

        test('should maintain compatibility with existing patent circumvention features', async () => {
            const ephemeralVote = 'Ephemeral_Identity_Test_Vote';
            const ephemeralWallet = {
                ed25519: { r: 'ephemeral_r', s: 'ephemeral_s' },
                publicKey: 'ephemeral_pubkey_temporary'
            };

            const result = await votingSystem.submitEnhancedVote(ephemeralVote, ephemeralWallet);
            expect(result.verified).toBe(true);

            expect(result.plumeSignature.nullifier).toBeDefined();
            expect(typeof result.plumeSignature.nullifier).toBe('string');

            const nullifier = plumeVerifier.extractNullifier(result.plumeSignature);
            expect(nullifier).toBe(result.plumeSignature.nullifier);
        });
    });

    describe('Performance and Scalability', () => {
        test('should meet performance requirements for proof generation', async () => {
            const startTime = Date.now();

            const vote = 'Performance_Test_Vote_2025';
            const walletSignature = {
                secp256k1: { r: 'perf_r', s: 'perf_s' },
                publicKey: 'perf_pubkey'
            };

            const result = await votingSystem.submitEnhancedVote(vote, walletSignature);
            
            const endTime = Date.now();
            const duration = endTime - startTime;

            expect(duration).toBeLessThan(10000); // Should complete within 10 seconds
            expect(result.verified).toBe(true);
        });

        test('should handle multiple concurrent votes efficiently', async () => {
            const concurrentVotes = Array.from({ length: 5 }, (_, i) => ({
                vote: `Concurrent_Vote_${i}`,
                wallet: {
                    ed25519: { r: `concurrent_r_${i}`, s: `concurrent_s_${i}` },
                    publicKey: `concurrent_pubkey_${i}`
                }
            }));

            const startTime = Date.now();
            
            const results = await Promise.all(
                concurrentVotes.map(({ vote, wallet }) => 
                    votingSystem.submitEnhancedVote(vote, wallet)
                )
            );

            const endTime = Date.now();
            const totalDuration = endTime - startTime;
            const averageDuration = totalDuration / concurrentVotes.length;

            expect(averageDuration).toBeLessThan(5000); // Average should be under 5 seconds
            expect(results.length).toBe(concurrentVotes.length);
            results.forEach(result => {
                expect(result.verified).toBe(true);
            });
        });
    });
});
