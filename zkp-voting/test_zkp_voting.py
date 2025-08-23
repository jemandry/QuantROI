#!/usr/bin/env python3
"""
Unit Tests for ZKP Voting System
Tests circuit compilation, proof generation, and verification
"""

import asyncio
import unittest
import tempfile
import os
from datetime import datetime, timedelta
from .user_voting import ZKPVotingSystem

class TestZKPVotingSystem(unittest.TestCase):
    """Test ZKP voting system functionality"""
    
    def setUp(self):
        self.voting_system = ZKPVotingSystem()
    
    def test_voting_system_initialization(self):
        """Test voting system initializes correctly"""
        self.assertIsNotNone(self.voting_system)
        self.assertIsNotNone(self.voting_system.logger)
    
    def test_create_voting_issue(self):
        """Test voting issue creation"""
        async def run_test():
            issue = await self.voting_system.create_voting_issue(
                issue_title="Test Issue",
                issue_description="Test Description",
                voting_deadline=datetime.now() + timedelta(days=1),
                min_stake_required=1000
            )
            
            self.assertIn('issue_id', issue)
            self.assertEqual(issue['title'], "Test Issue")
            self.assertEqual(issue['min_stake_required'], 1000)
            self.assertEqual(issue['status'], 'active')
        
        asyncio.run(run_test())
    
    def test_vote_proof_generation(self):
        """Test ZKP proof generation"""
        async def run_test():
            proof_data = await self.voting_system.generate_vote_proof(
                vote=True,
                stake_amount=5000,
                voter_type=0,
                secret_key="test_secret",
                issue_id="test_issue",
                min_stake_required=1000,
                voting_deadline=int((datetime.now() + timedelta(days=1)).timestamp())
            )
            
            self.assertIn('proof', proof_data)
            self.assertIn('public_signals', proof_data)
            self.assertIn('vote_commitment', proof_data)
            self.assertIn('stake_proof', proof_data)
            self.assertIn('eligibility_proof', proof_data)
        
        asyncio.run(run_test())
    
    def test_vote_proof_verification(self):
        """Test ZKP proof verification"""
        async def run_test():
            proof_data = await self.voting_system.generate_vote_proof(
                vote=True,
                stake_amount=5000,
                voter_type=0,
                secret_key="test_secret",
                issue_id="test_issue",
                min_stake_required=1000,
                voting_deadline=int((datetime.now() + timedelta(days=1)).timestamp())
            )
            
            verification_result = await self.voting_system.verify_vote_proof(proof_data)
            self.assertTrue(verification_result)
        
        asyncio.run(run_test())
    
    def test_submit_vote_workflow(self):
        """Test complete vote submission workflow"""
        async def run_test():
            voting_issue = await self.voting_system.create_voting_issue(
                issue_title="AI Trading Strategy",
                issue_description="Should we implement new AI strategy?",
                voting_deadline=datetime.now() + timedelta(days=7),
                min_stake_required=1000
            )
            
            vote_result = await self.voting_system.submit_vote(
                voting_issue=voting_issue,
                vote=True,
                stake_amount=5000,
                voter_type=0,
                secret_key="employee_secret"
            )
            
            self.assertTrue(vote_result['success'])
            self.assertEqual(vote_result['total_votes'], 1)
            self.assertTrue(vote_result['vote_record']['proof_verified'])
        
        asyncio.run(run_test())
    
    def test_insufficient_stake_rejection(self):
        """Test vote rejection for insufficient stake"""
        async def run_test():
            voting_issue = await self.voting_system.create_voting_issue(
                issue_title="Test Issue",
                issue_description="Test Description",
                voting_deadline=datetime.now() + timedelta(days=1),
                min_stake_required=10000
            )
            
            with self.assertRaises(ValueError):
                await self.voting_system.submit_vote(
                    voting_issue=voting_issue,
                    vote=True,
                    stake_amount=5000,
                    voter_type=0,
                    secret_key="test_secret"
                )
        
        asyncio.run(run_test())
    
    def test_unauthorized_voter_type_rejection(self):
        """Test vote rejection for unauthorized voter type"""
        async def run_test():
            voting_issue = await self.voting_system.create_voting_issue(
                issue_title="Test Issue",
                issue_description="Test Description",
                voting_deadline=datetime.now() + timedelta(days=1),
                min_stake_required=1000,
                voter_types_allowed=[0]
            )
            
            with self.assertRaises(ValueError):
                await self.voting_system.submit_vote(
                    voting_issue=voting_issue,
                    vote=True,
                    stake_amount=5000,
                    voter_type=1,
                    secret_key="test_secret"
                )
        
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
