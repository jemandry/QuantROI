#!/usr/bin/env python3
"""
Unit Tests for Storytelling UX and Voice Interface
Tests Grok 3 integration, multilingual support, and narrative generation
"""

import asyncio
import unittest
from .storytelling_dashboard import StorytellingDashboard
import sys
import os

sys.path.append('/home/ubuntu/repos/quantroi/ux/voice-interface')
sys.path.append('/home/ubuntu/repos/quantroi/ux/multilingual')

from grok_integration import GrokVoiceInterface
from language_manager import LanguageManager

class TestStorytellingUX(unittest.TestCase):
    """Test storytelling UX functionality"""
    
    def setUp(self):
        self.dashboard = StorytellingDashboard()
        self.voice_interface = GrokVoiceInterface()
        self.lang_manager = LanguageManager()
    
    def test_dashboard_initialization(self):
        """Test storytelling dashboard initializes correctly"""
        self.assertIsNotNone(self.dashboard)
        self.assertIsNotNone(self.dashboard.logger)
    
    def test_narrative_generation(self):
        """Test market narrative generation"""
        market_data = {
            'symbol': 'AAPL',
            'price_change': 0.025,
            'volume': 1000000,
            'sentiment': 0.8
        }
        
        narrative = self.dashboard.generate_market_narrative(market_data)
        
        self.assertIsInstance(narrative, str)
        self.assertIn('AAPL', narrative)
        self.assertTrue(len(narrative) > 50)
    
    def test_causal_heatmap_creation(self):
        """Test causal relationship heatmap creation"""
        causal_data = [
            {'source': 'AAPL', 'target': 'MSFT', 'strength': 0.8},
            {'source': 'MSFT', 'target': 'GOOGL', 'strength': 0.6},
            {'source': 'GOOGL', 'target': 'AAPL', 'strength': 0.7}
        ]
        
        heatmap = self.dashboard.create_causal_heatmap(causal_data)
        
        self.assertIsNotNone(heatmap)
    
    def test_voice_command_processing(self):
        """Test voice command processing"""
        async def run_test():
            mock_audio = b"show me causal analysis for apple stock"
            
            result = await self.voice_interface.process_financial_command(mock_audio, 'en')
            
            self.assertIn('transcription', result)
            self.assertIn('intent', result)
            self.assertIn('response', result)
            self.assertEqual(result['intent']['action'], 'causal_analysis')
            self.assertEqual(result['intent']['symbol'], 'AAPL')
        
        asyncio.run(run_test())
    
    def test_multilingual_voice_support(self):
        """Test multilingual voice command support"""
        async def run_test():
            test_cases = [
                (b"analyze apple stock", 'en'),
                (b"analizar acciones de apple", 'es'),
                (b"analyser les actions apple", 'fr')
            ]
            
            for audio, lang in test_cases:
                result = await self.voice_interface.process_financial_command(audio, lang)
                
                self.assertIn('transcription', result)
                self.assertIn('intent', result)
                self.assertIn('response', result)
        
        asyncio.run(run_test())
    
    def test_financial_intent_parsing(self):
        """Test financial intent parsing accuracy"""
        test_cases = [
            ("Show me causal analysis for Tesla", "causal_analysis", "TSLA"),
            ("Analyze correlation between tech stocks", "correlation_analysis", ["AAPL", "MSFT", "GOOGL", "TSLA"]),
            ("Generate hedging strategy", "hedging_strategy", None),
            ("Create compliance report", "compliance_report", None)
        ]
        
        async def run_test():
            for transcription, expected_action, expected_symbol in test_cases:
                intent = await self.voice_interface._parse_financial_intent(transcription)
                
                self.assertEqual(intent['action'], expected_action)
                if expected_symbol:
                    if isinstance(expected_symbol, list):
                        self.assertEqual(intent['symbols'], expected_symbol)
                    else:
                        self.assertEqual(intent['symbol'], expected_symbol)
        
        asyncio.run(run_test())
    
    def test_language_manager_translations(self):
        """Test language manager translation functionality"""
        test_languages = ['en', 'es', 'fr', 'de', 'zh', 'ja']
        
        for lang in test_languages:
            title = self.lang_manager.get_translation('dashboard_title', lang)
            welcome = self.lang_manager.get_translation('welcome_message', lang)
            
            self.assertIsInstance(title, str)
            self.assertIsInstance(welcome, str)
            self.assertTrue(len(title) > 0)
            self.assertTrue(len(welcome) > 0)
    
    def test_cultural_adaptation(self):
        """Test cultural adaptation features"""
        test_languages = ['en', 'es', 'fr', 'de', 'zh', 'ja']
        
        for lang in test_languages:
            adaptation = self.lang_manager.get_cultural_adaptation(lang)
            
            self.assertIn('currency_symbol', adaptation)
            self.assertIn('date_format', adaptation)
            self.assertIn('cultural_context', adaptation)
            self.assertIn('risk_tolerance', adaptation)
    
    def test_currency_formatting(self):
        """Test currency formatting for different cultures"""
        amount = 1234.56
        
        test_cases = [
            ('en', '$1,234.56'),
            ('de', '1,234.56 €'),
            ('zh', '¥1,235'),
            ('ja', '¥1,235')
        ]
        
        for lang, expected_pattern in test_cases:
            formatted = self.lang_manager.format_currency(amount, lang)
            self.assertIsInstance(formatted, str)
    
    def test_narrative_style_adaptation(self):
        """Test narrative style adaptation for different cultures"""
        test_languages = ['en', 'es', 'fr', 'de', 'zh', 'ja']
        
        for lang in test_languages:
            style = self.lang_manager.get_market_narrative_style(lang)
            
            self.assertIn('tone', style)
            self.assertIn('metaphors', style)
            self.assertIn('formality', style)
    
    def test_voice_interface_response_generation(self):
        """Test voice interface response generation"""
        async def run_test():
            test_intents = [
                {'action': 'causal_analysis', 'symbol': 'AAPL', 'confidence': 0.95},
                {'action': 'correlation_analysis', 'symbols': ['AAPL', 'MSFT'], 'confidence': 0.90},
                {'action': 'hedging_strategy', 'confidence': 0.88},
                {'action': 'compliance_report', 'confidence': 0.92}
            ]
            
            for intent in test_intents:
                response = await self.voice_interface._generate_financial_response(intent)
                
                self.assertIn('type', response)
                self.assertIn('narrative', response)
                self.assertIn('confidence_score', response)
                self.assertEqual(response['type'], intent['action'])
        
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
