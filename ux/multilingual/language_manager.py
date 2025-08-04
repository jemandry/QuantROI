#!/usr/bin/env python3
"""
Multilingual Language Manager
Supports 10+ languages with cultural adaptation
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

class LanguageManager:
    """Manages multilingual support and cultural adaptation"""
    
    def __init__(self):
        self.supported_languages = [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko', 'ar', 'hi'
        ]
        self.translations = self._load_translations()
        self.cultural_adaptations = self._load_cultural_adaptations()
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translation dictionaries"""
        return {
            'en': {
                'dashboard_title': '🔮 QuantROI Financial Oracle',
                'causal_analysis': 'Causal Analysis',
                'market_narrative': 'Market Narrative',
                'voice_prompt': 'Speak your market quest...',
                'portfolio_management': 'Portfolio Management',
                'risk_assessment': 'Risk Assessment',
                'compliance_status': 'Compliance Status',
                'trading_signals': 'Trading Signals',
                'welcome_message': 'Welcome to your financial journey',
                'loading': 'Analyzing market forces...',
                'error_message': 'The oracle encountered turbulence',
                'success_message': 'Quest completed successfully'
            },
            'es': {
                'dashboard_title': '🔮 Oráculo Financiero QuantROI',
                'causal_analysis': 'Análisis Causal',
                'market_narrative': 'Narrativa del Mercado',
                'voice_prompt': 'Habla tu búsqueda del mercado...',
                'portfolio_management': 'Gestión de Cartera',
                'risk_assessment': 'Evaluación de Riesgo',
                'compliance_status': 'Estado de Cumplimiento',
                'trading_signals': 'Señales de Trading',
                'welcome_message': 'Bienvenido a tu viaje financiero',
                'loading': 'Analizando fuerzas del mercado...',
                'error_message': 'El oráculo encontró turbulencias',
                'success_message': 'Búsqueda completada exitosamente'
            },
            'fr': {
                'dashboard_title': '🔮 Oracle Financier QuantROI',
                'causal_analysis': 'Analyse Causale',
                'market_narrative': 'Récit du Marché',
                'voice_prompt': 'Parlez votre quête de marché...',
                'portfolio_management': 'Gestion de Portefeuille',
                'risk_assessment': 'Évaluation des Risques',
                'compliance_status': 'Statut de Conformité',
                'trading_signals': 'Signaux de Trading',
                'welcome_message': 'Bienvenue dans votre parcours financier',
                'loading': 'Analyse des forces du marché...',
                'error_message': 'L\'oracle a rencontré des turbulences',
                'success_message': 'Quête terminée avec succès'
            },
            'de': {
                'dashboard_title': '🔮 QuantROI Finanz-Orakel',
                'causal_analysis': 'Kausalanalyse',
                'market_narrative': 'Markterzählung',
                'voice_prompt': 'Sprechen Sie Ihre Marktsuche...',
                'portfolio_management': 'Portfolio-Management',
                'risk_assessment': 'Risikobewertung',
                'compliance_status': 'Compliance-Status',
                'trading_signals': 'Handelssignale',
                'welcome_message': 'Willkommen zu Ihrer Finanzreise',
                'loading': 'Analysiere Marktkräfte...',
                'error_message': 'Das Orakel stieß auf Turbulenzen',
                'success_message': 'Quest erfolgreich abgeschlossen'
            },
            'zh': {
                'dashboard_title': '🔮 QuantROI 金融神谕',
                'causal_analysis': '因果分析',
                'market_narrative': '市场叙述',
                'voice_prompt': '说出您的市场探索...',
                'portfolio_management': '投资组合管理',
                'risk_assessment': '风险评估',
                'compliance_status': '合规状态',
                'trading_signals': '交易信号',
                'welcome_message': '欢迎开始您的金融之旅',
                'loading': '分析市场力量中...',
                'error_message': '神谕遇到了湍流',
                'success_message': '探索成功完成'
            },
            'ja': {
                'dashboard_title': '🔮 QuantROI 金融オラクル',
                'causal_analysis': '因果分析',
                'market_narrative': 'マーケットナラティブ',
                'voice_prompt': 'マーケットクエストを話してください...',
                'portfolio_management': 'ポートフォリオ管理',
                'risk_assessment': 'リスク評価',
                'compliance_status': 'コンプライアンス状況',
                'trading_signals': 'トレーディングシグナル',
                'welcome_message': '金融の旅へようこそ',
                'loading': '市場の力を分析中...',
                'error_message': 'オラクルが乱気流に遭遇しました',
                'success_message': 'クエストが正常に完了しました'
            }
        }
    
    def _load_cultural_adaptations(self) -> Dict[str, Dict[str, Any]]:
        """Load cultural adaptation settings"""
        return {
            'en': {
                'currency_symbol': '$',
                'date_format': 'MM/DD/YYYY',
                'number_format': 'en-US',
                'market_hours': 'US Eastern',
                'cultural_context': 'individualistic',
                'risk_tolerance': 'moderate'
            },
            'es': {
                'currency_symbol': '€',
                'date_format': 'DD/MM/YYYY',
                'number_format': 'es-ES',
                'market_hours': 'European',
                'cultural_context': 'relationship-focused',
                'risk_tolerance': 'conservative'
            },
            'fr': {
                'currency_symbol': '€',
                'date_format': 'DD/MM/YYYY',
                'number_format': 'fr-FR',
                'market_hours': 'European',
                'cultural_context': 'formal',
                'risk_tolerance': 'moderate'
            },
            'de': {
                'currency_symbol': '€',
                'date_format': 'DD.MM.YYYY',
                'number_format': 'de-DE',
                'market_hours': 'European',
                'cultural_context': 'precision-focused',
                'risk_tolerance': 'conservative'
            },
            'zh': {
                'currency_symbol': '¥',
                'date_format': 'YYYY/MM/DD',
                'number_format': 'zh-CN',
                'market_hours': 'Asian',
                'cultural_context': 'collective',
                'risk_tolerance': 'moderate'
            },
            'ja': {
                'currency_symbol': '¥',
                'date_format': 'YYYY/MM/DD',
                'number_format': 'ja-JP',
                'market_hours': 'Asian',
                'cultural_context': 'hierarchical',
                'risk_tolerance': 'conservative'
            }
        }
    
    def get_translation(self, key: str, language: str = 'en') -> str:
        """Get translation for a specific key"""
        if language not in self.supported_languages:
            language = 'en'
        
        return self.translations.get(language, {}).get(key, 
            self.translations['en'].get(key, key))
    
    def get_cultural_adaptation(self, language: str = 'en') -> Dict[str, Any]:
        """Get cultural adaptation settings for a language"""
        if language not in self.supported_languages:
            language = 'en'
        
        return self.cultural_adaptations.get(language, self.cultural_adaptations['en'])
    
    def format_currency(self, amount: float, language: str = 'en') -> str:
        """Format currency according to cultural preferences"""
        adaptation = self.get_cultural_adaptation(language)
        symbol = adaptation['currency_symbol']
        
        if language in ['en']:
            return f"{symbol}{amount:,.2f}"
        elif language in ['es', 'fr']:
            return f"{amount:,.2f} {symbol}"
        elif language in ['de']:
            return f"{amount:,.2f} {symbol}".replace(',', '.')
        elif language in ['zh', 'ja']:
            return f"{symbol}{amount:,.0f}"
        else:
            return f"{symbol}{amount:,.2f}"
    
    def format_date(self, date: datetime, language: str = 'en') -> str:
        """Format date according to cultural preferences"""
        adaptation = self.get_cultural_adaptation(language)
        date_format = adaptation['date_format']
        
        if date_format == 'MM/DD/YYYY':
            return date.strftime('%m/%d/%Y')
        elif date_format == 'DD/MM/YYYY':
            return date.strftime('%d/%m/%Y')
        elif date_format == 'DD.MM.YYYY':
            return date.strftime('%d.%m.%Y')
        elif date_format == 'YYYY/MM/DD':
            return date.strftime('%Y/%m/%d')
        else:
            return date.strftime('%Y-%m-%d')
    
    def get_market_narrative_style(self, language: str = 'en') -> Dict[str, str]:
        """Get narrative style preferences for different cultures"""
        styles = {
            'en': {
                'tone': 'confident',
                'metaphors': 'adventure, quest, journey',
                'formality': 'casual'
            },
            'es': {
                'tone': 'warm',
                'metaphors': 'family, community, growth',
                'formality': 'respectful'
            },
            'fr': {
                'tone': 'sophisticated',
                'metaphors': 'art, cuisine, elegance',
                'formality': 'formal'
            },
            'de': {
                'tone': 'precise',
                'metaphors': 'engineering, precision, efficiency',
                'formality': 'professional'
            },
            'zh': {
                'tone': 'harmonious',
                'metaphors': 'balance, flow, wisdom',
                'formality': 'respectful'
            },
            'ja': {
                'tone': 'respectful',
                'metaphors': 'seasons, nature, harmony',
                'formality': 'very formal'
            }
        }
        
        return styles.get(language, styles['en'])

def main():
    """Example usage of Language Manager"""
    lang_manager = LanguageManager()
    
    print("Multilingual Support Demo:")
    
    for lang in ['en', 'es', 'fr', 'de', 'zh', 'ja']:
        title = lang_manager.get_translation('dashboard_title', lang)
        welcome = lang_manager.get_translation('welcome_message', lang)
        currency = lang_manager.format_currency(1234.56, lang)
        date = lang_manager.format_date(datetime.now(), lang)
        
        print(f"\n{lang.upper()}:")
        print(f"  Title: {title}")
        print(f"  Welcome: {welcome}")
        print(f"  Currency: {currency}")
        print(f"  Date: {date}")

if __name__ == "__main__":
    main()
