/**
 * Test suite for Noir circuit compilation and verification
 */

import { NoirIntegrationManager } from '../src/noir-circuit-compiler';


describe('Noir Circuit Compilation', () => {
    let integrationManager: NoirIntegrationManager;

    beforeEach(() => {
        integrationManager = new NoirIntegrationManager();
    });

    describe('Circuit Compilation', () => {
        test('should initialize and compile all circuits', async () => {
            const initialized = await integrationManager.initialize();
            expect(initialized).toBe(true);
            
            const compiledCircuits = integrationManager.listCompiledCircuits();
            expect(compiledCircuits).toContain('voter_authentication');
            expect(compiledCircuits).toContain('plume_voting');
            expect(compiledCircuits).toContain('homomorphic_tally');
            expect(compiledCircuits).toContain('wallet_signature_verification');
            expect(compiledCircuits).toContain('vote_format_compliance');
            expect(compiledCircuits).toContain('external_eligibility');
        });

        test('should provide circuit information', async () => {
            await integrationManager.initialize();
            
            const circuitInfo = integrationManager.getCircuitInfo('voter_authentication');
            expect(circuitInfo).toBeDefined();
            expect(circuitInfo.wasmPath).toBeDefined();
            expect(circuitInfo.zkeyPath).toBeDefined();
            expect(circuitInfo.verificationKey).toBeDefined();
        });
    });

    describe('Proof Generation and Verification', () => {
        test('should generate and verify voter authentication proof', async () => {
            await integrationManager.initialize();
            
            const proof = await integrationManager.generateVoterAuthenticationProof(
                'test_voter_secret_12345',
                'test_eligibility_root_67890'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
            
            const isValid = await integrationManager.verifyProof(
                'voter_authentication',
                proof.proof,
                proof.publicSignals
            );
            expect(isValid).toBe(true);
        });

        test('should generate and verify PLUME voting proof', async () => {
            await integrationManager.initialize();
            
            const message = new Uint8Array([65, 73, 95, 80, 111, 108, 105, 99, 121, 95, 86, 111, 116, 101, 95, 50, 48, 50, 53]); // 'AI_Policy_Vote_2025' as bytes
            const proof = await integrationManager.generatePLUMEVotingProof(
                message,
                '123456789',
                '987654321',
                'test_public_key_abc123'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
            
            const isValid = await integrationManager.verifyProof(
                'plume_voting',
                proof.proof,
                proof.publicSignals
            );
            expect(isValid).toBe(true);
        });

        test('should generate and verify homomorphic tally proof', async () => {
            await integrationManager.initialize();
            
            const encryptedVotes = ['1000', '2000', '3000', '4000', '5000'];
            const proof = await integrationManager.generateHomomorphicTallyProof(
                encryptedVotes,
                '5',
                'test_election_pubkey_xyz789'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
            
            const isValid = await integrationManager.verifyProof(
                'homomorphic_tally',
                proof.proof,
                proof.publicSignals
            );
            expect(isValid).toBe(true);
        });

        test('should generate and verify wallet signature proof', async () => {
            await integrationManager.initialize();
            
            const voteHash = new Uint8Array([118, 111, 116, 101, 95, 104, 97, 115, 104, 95, 99, 111, 110, 116, 101, 110, 116]); // 'vote_hash_content' as bytes
            const ed25519Sig = { r: '111111', s: '222222' };
            const proof = await integrationManager.generateWalletSignatureProof(
                voteHash,
                ed25519Sig,
                null,
                'test_wallet_pubkey_def456'
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
            
            const isValid = await integrationManager.verifyProof(
                'wallet_signature_verification',
                proof.proof,
                proof.publicSignals
            );
            expect(isValid).toBe(true);
        });

        test('should generate and verify compliance proof', async () => {
            await integrationManager.initialize();
            
            const voteData = new Uint8Array([67, 79, 77, 80, 76, 73, 65, 78, 84, 95, 86, 79, 84, 69, 95, 70, 79, 82, 77, 65, 84, 95, 50, 48, 50, 53]); // 'COMPLIANT_VOTE_FORMAT_2025' as bytes
            const proof = await integrationManager.generateComplianceProof(
                voteData,
                'compliance_pattern_hash_123',
                true
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
            
            const isValid = await integrationManager.verifyProof(
                'vote_format_compliance',
                proof.proof,
                proof.publicSignals
            );
            expect(isValid).toBe(true);
        });

        test('should generate and verify external eligibility proof', async () => {
            await integrationManager.initialize();
            
            const eligibilityData = new Uint8Array([86, 79, 84, 69, 82, 95, 69, 76, 73, 71, 73, 66, 76, 69, 95, 86, 69, 82, 73, 70, 73, 69, 68]); // 'VOTER_ELIGIBLE_VERIFIED' as bytes
            const proof = await integrationManager.generateEligibilityProof(
                eligibilityData,
                'tls_proof_hash_456',
                'authority_pubkey_ghi789',
                true
            );
            
            expect(proof.proof).toBeDefined();
            expect(proof.publicSignals).toBeDefined();
            expect(proof.verified).toBe(true);
            
            const isValid = await integrationManager.verifyProof(
                'external_eligibility',
                proof.proof,
                proof.publicSignals
            );
            expect(isValid).toBe(true);
        });
    });

    describe('Error Handling', () => {
        test('should handle invalid circuit names', async () => {
            await integrationManager.initialize();
            
            try {
                await integrationManager.generateVoterAuthenticationProof('', '');
            } catch (error) {
                expect(error).toBeDefined();
            }
        });

        test('should handle verification of invalid proofs', async () => {
            await integrationManager.initialize();
            
            const invalidProof = new Uint8Array([0, 0, 0, 0]);
            const invalidSignals = ['invalid'];
            
            const isValid = await integrationManager.verifyProof(
                'voter_authentication',
                invalidProof,
                invalidSignals
            );
            
            expect(typeof isValid).toBe('boolean');
        });
    });
});
