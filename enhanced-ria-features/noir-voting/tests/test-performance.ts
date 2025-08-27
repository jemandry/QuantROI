/**
 * Performance test suite for Noir ZKP integration
 */

import { NoirEnhancedVotingSystem, PLUMEVerifier, HomomorphicEncryption } from '../src/enhanced-noir-integration';
import { NoirIntegrationManager } from '../src/noir-circuit-compiler';


describe('Noir ZKP Performance Tests', () => {
    let votingSystem: NoirEnhancedVotingSystem;
    let integrationManager: NoirIntegrationManager;
    let plumeVerifier: PLUMEVerifier;
    let homomorphicEncryption: HomomorphicEncryption;

    beforeEach(async () => {
        votingSystem = new NoirEnhancedVotingSystem();
        integrationManager = new NoirIntegrationManager();
        plumeVerifier = new PLUMEVerifier();
        homomorphicEncryption = new HomomorphicEncryption();
        
        await integrationManager.initialize();
    });

    describe('PLUME Signature Performance', () => {
        test('should generate PLUME signatures within performance targets', async () => {
            const message = 'performance_test_vote_data';
            const privateKey = 'performance_test_private_key';
            
            const startTime = Date.now();
            const signature = await plumeVerifier.sign(message, privateKey);
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(1000);
            expect(signature.r).toBeDefined();
            expect(signature.s).toBeDefined();
            expect(signature.nullifier).toBeDefined();
        });

        test('should verify PLUME signatures quickly', async () => {
            const message = 'performance_test_vote_data';
            const privateKey = 'performance_test_private_key';
            const publicKey = 'performance_test_public_key';
            
            const signature = await plumeVerifier.sign(message, privateKey);
            
            const startTime = Date.now();
            const isValid = await plumeVerifier.verify(message, signature, publicKey);
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(100);
            expect(isValid).toBe(true);
        });
    });

    describe('Homomorphic Encryption Performance', () => {
        test('should encrypt votes efficiently', async () => {
            const vote = 1;
            const publicKey = 'performance_test_public_key';
            
            const startTime = Date.now();
            const encryptedVote = await homomorphicEncryption.encryptVote(vote, publicKey);
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(500);
            expect(encryptedVote.encryptedValue).toBeDefined();
            expect(encryptedVote.proof).toBeDefined();
        });

        test('should perform homomorphic addition quickly', async () => {
            const vote1 = { encryptedValue: '1000', proof: 'proof1' };
            const vote2 = { encryptedValue: '2000', proof: 'proof2' };
            
            const startTime = Date.now();
            const sum = await homomorphicEncryption.homomorphicAdd(vote1, vote2);
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(100);
            expect(sum.encryptedValue).toBeDefined();
            expect(sum.proof).toBeDefined();
        });

        test('should tally multiple votes within performance targets', async () => {
            const encryptedVotes = Array.from({ length: 100 }, (_, i) => ({
                encryptedValue: (i * 100).toString(),
                proof: `proof_${i}`
            }));
            const privateKey = 'performance_test_private_key';
            
            const startTime = Date.now();
            const tally = await homomorphicEncryption.tallyVotes(encryptedVotes, privateKey);
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(2000);
            expect(typeof tally).toBe('number');
            expect(tally).toBeGreaterThan(0);
        });
    });

    describe('Circuit Proof Generation Performance', () => {
        test('should generate voter authentication proofs within target time', async () => {
            const voterSecret = 'performance_test_voter_secret';
            const eligibilityRoot = 'performance_test_eligibility_root';
            
            const startTime = Date.now();
            const proof = await integrationManager.generateVoterAuthenticationProof(
                voterSecret,
                eligibilityRoot
            );
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(5000);
            expect(proof.verified).toBe(true);
        });

        test('should generate PLUME voting proofs efficiently', async () => {
            const message = new Uint8Array([112, 101, 114, 102, 111, 114, 109, 97, 110, 99, 101, 95, 116, 101, 115, 116, 95, 118, 111, 116, 101]); // 'performance_test_vote' as bytes
            const signatureR = 'performance_test_r';
            const signatureS = 'performance_test_s';
            const publicKey = 'performance_test_public_key';
            
            const startTime = Date.now();
            const proof = await integrationManager.generatePLUMEVotingProof(
                message,
                signatureR,
                signatureS,
                publicKey
            );
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(5000);
            expect(proof.verified).toBe(true);
        });

        test('should generate homomorphic tally proofs within target time', async () => {
            const encryptedVotes = Array.from({ length: 50 }, (_, i) => (i * 100).toString());
            const tallyResult = '50';
            const electionPubkey = 'performance_test_election_pubkey';
            
            const startTime = Date.now();
            const proof = await integrationManager.generateHomomorphicTallyProof(
                encryptedVotes,
                tallyResult,
                electionPubkey
            );
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(5000);
            expect(proof.verified).toBe(true);
        });
    });

    describe('End-to-End Voting Performance', () => {
        test('should complete enhanced vote submission within performance targets', async () => {
            const vote = 'performance_test_ai_policy_vote';
            const walletSignature = {
                ed25519: { r: 'perf_test_r', s: 'perf_test_s' },
                publicKey: 'perf_test_public_key'
            };
            
            const startTime = Date.now();
            const result = await votingSystem.submitEnhancedVote(vote, walletSignature);
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            expect(duration).toBeLessThan(10000);
            expect(result.verified).toBe(true);
            expect(result.plumeSignature).toBeDefined();
            expect(result.homomorphicVote).toBeDefined();
        });

        test('should handle batch vote processing efficiently', async () => {
            const votes = Array.from({ length: 10 }, (_, i) => `batch_vote_${i}`);
            const walletSignature = {
                ed25519: { r: 'batch_test_r', s: 'batch_test_s' },
                publicKey: 'batch_test_public_key'
            };
            
            const startTime = Date.now();
            const results = await Promise.all(
                votes.map(vote => votingSystem.submitEnhancedVote(vote, walletSignature))
            );
            const endTime = Date.now();
            
            const duration = endTime - startTime;
            const averageTime = duration / votes.length;
            
            expect(averageTime).toBeLessThan(5000);
            expect(results.length).toBe(votes.length);
            results.forEach(result => {
                expect(result.verified).toBe(true);
            });
        });
    });

    describe('Memory and Resource Usage', () => {
        test('should maintain reasonable memory usage during operations', async () => {
            const initialMemory = process.memoryUsage().heapUsed;
            
            for (let i = 0; i < 50; i++) {
                const vote = `memory_test_vote_${i}`;
                const walletSignature = {
                    ed25519: { r: `mem_test_r_${i}`, s: `mem_test_s_${i}` },
                    publicKey: `mem_test_public_key_${i}`
                };
                
                await votingSystem.submitEnhancedVote(vote, walletSignature);
            }
            
            const finalMemory = process.memoryUsage().heapUsed;
            const memoryIncrease = finalMemory - initialMemory;
            const memoryIncreaseInMB = memoryIncrease / (1024 * 1024);
            
            expect(memoryIncreaseInMB).toBeLessThan(100);
        });
    });
});
