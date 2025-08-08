import asyncio
import logging
import json
import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    import openai
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch
    LLM_LIBS_AVAILABLE = True
except ImportError:
    LLM_LIBS_AVAILABLE = False
    logging.warning("OpenAI/Transformers not available - using mock implementations")

@dataclass
class CausalHypothesis:
    hypothesis_id: str
    causal_template: str  # "Because X, therefore Y"
    confidence_score: float
    evidence_sources: List[str]
    extracted_entities: Dict[str, str]
    temporal_markers: List[str]
    generated_at: datetime
    market_impact_prediction: str = "NEUTRAL"

@dataclass
class CausalInsightReport:
    total_hypotheses: int
    high_confidence_count: int
    avg_confidence: float
    dominant_patterns: List[str]
    temporal_distribution: Dict[str, int]
    entity_frequency: Dict[str, int]
    generated_at: datetime

class LLMAssistedCausalInference:
    """LLM-assisted causal discovery for unstructured financial data"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = openai_api_key
        
        if LLM_LIBS_AVAILABLE and openai_api_key:
            openai.api_key = openai_api_key
            self.logger.info("OpenAI API initialized")
        
        self.sentiment_analyzer = None
        self.ner_pipeline = None
        
        if LLM_LIBS_AVAILABLE:
            try:
                self.sentiment_analyzer = pipeline("sentiment-analysis", 
                                                 model="ProsusAI/finbert")
                self.ner_pipeline = pipeline("ner", 
                                           model="dbmdz/bert-large-cased-finetuned-conll03-english",
                                           aggregation_strategy="simple")
                self.logger.info("Local NLP models initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize local models: {e}")
        
        self.causal_templates = {
            'earnings_impact': "Because {company} reported {earnings_type} earnings, therefore {stock_symbol} price {direction}",
            'fed_policy': "Because the Federal Reserve {policy_action}, therefore {sector} stocks {market_reaction}",
            'merger_announcement': "Because {acquirer} announced acquisition of {target}, therefore {target_symbol} price {price_movement}",
            'regulatory_change': "Because {regulator} announced {regulation_type}, therefore {affected_sector} experienced {market_impact}",
            'geopolitical_event': "Because {event_description} occurred in {location}, therefore {asset_class} showed {volatility_pattern}",
            'commodity_shock': "Because {commodity} prices {price_direction} due to {cause}, therefore {related_sectors} {sector_response}"
        }
    
    async def extract_causal_patterns_from_news(self, news_text: str, 
                                              source: str = "unknown") -> List[CausalHypothesis]:
        """Extract causal patterns from news text using LLM analysis with enhanced accuracy"""
        try:
            if LLM_LIBS_AVAILABLE and self.openai_api_key:
                return await self._openai_causal_extraction(news_text, source)
            else:
                return await self._enhanced_rule_based_extraction(news_text, source)
                
        except Exception as e:
            self.logger.error(f"✗ Error extracting causal patterns: {e}")
            return []
    
    async def _openai_causal_extraction(self, news_text: str, source: str) -> List[CausalHypothesis]:
        """Use OpenAI GPT-4 for sophisticated causal pattern extraction"""
        try:
            prompt = f"""
            Analyze the following financial news text and extract causal relationships in the format "Because X, therefore Y".
            Focus on identifying:
            1. Clear cause-and-effect relationships
            2. Financial entities (companies, stocks, sectors)
            3. Quantitative impacts (percentages, dollar amounts)
            4. Temporal relationships
            5. Market implications
            
            News text: {news_text}
            
            Return a JSON array of causal relationships with the following structure:
            {{
                "causal_template": "Because X, therefore Y",
                "confidence_score": 0.0-1.0,
                "entities": {{"cause": "X", "effect": "Y", "companies": [], "sectors": []}},
                "temporal_markers": ["time indicators"],
                "market_impact": "predicted impact"
            }}
            
            Only include relationships with confidence > 0.6.
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial analyst expert at identifying causal relationships in market news."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            try:
                causal_data = json.loads(content)
                if not isinstance(causal_data, list):
                    causal_data = [causal_data]
            except json.JSONDecodeError:
                return await self._enhanced_rule_based_extraction(news_text, source)
            
            hypotheses = []
            for item in causal_data:
                hypothesis_id = hashlib.md5(f"{item.get('causal_template', '')}{source}".encode()).hexdigest()[:12]
                
                hypothesis = CausalHypothesis(
                    hypothesis_id=hypothesis_id,
                    causal_template=item.get('causal_template', ''),
                    confidence_score=item.get('confidence_score', 0.5),
                    evidence_sources=[source],
                    extracted_entities=item.get('entities', {}),
                    temporal_markers=item.get('temporal_markers', []),
                    generated_at=datetime.now(),
                    market_impact_prediction=item.get('market_impact')
                )
                
                hypothesis.validation_score = await self._validate_hypothesis_against_market_data(hypothesis)
                
                hypotheses.append(hypothesis)
            
            self.logger.info(f"✓ GPT-4 extracted {len(hypotheses)} causal hypotheses from {source}")
            return hypotheses
            
        except Exception as e:
            self.logger.warning(f"⚠ GPT-4 extraction failed: {e}. Falling back to rule-based extraction.")
            return await self._enhanced_rule_based_extraction(news_text, source)
    
    async def _enhanced_rule_based_extraction(self, news_text: str, source: str) -> List[CausalHypothesis]:
        """Enhanced rule-based causal pattern extraction with improved accuracy"""
        hypotheses = []
        
        try:
            entities = self._extract_financial_entities(news_text)
            
            sentiment_score = 0.5
            if self.sentiment_analyzer:
                try:
                    sentiment_result = self.sentiment_analyzer(news_text[:512])  # Limit text length
                    sentiment_score = sentiment_result[0]['score'] if sentiment_result[0]['label'] == 'POSITIVE' else 1 - sentiment_result[0]['score']
                except Exception as e:
                    self.logger.debug(f"Sentiment analysis failed: {e}")
            
            causal_patterns = [
                (r'(?:because|due to|as a result of|following)\s+(.+?),?\s+(?:therefore|thus|consequently|so|this led to|this caused)\s+(.+?)(?:\.|$)', 'explicit_causal'),
                (r'(.+?)\s+(?:caused|led to|resulted in|triggered)\s+(.+?)(?:\.|$)', 'direct_causal'),
                (r'(?:after|following)\s+(.+?),\s*(.+?)\s+(?:rose|fell|increased|decreased|jumped|dropped)', 'temporal_causal'),
                (r'(.+?)\s+(?:announcement|news|report)\s+(?:sent|pushed|drove)\s+(.+?)\s+(?:higher|lower|up|down)', 'announcement_impact')
            ]
            
            for pattern, pattern_type in causal_patterns:
                matches = re.finditer(pattern, news_text, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    cause = match.group(1).strip()
                    effect = match.group(2).strip()
                    
                    if len(cause) < 10 or len(effect) < 10:
                        continue
                    
                    causal_template = f"Because {cause}, therefore {effect}"
                    
                    confidence = self._calculate_rule_based_confidence(
                        cause, effect, entities, sentiment_score, pattern_type
                    )
                    
                    if confidence >= 0.6:  # Only include high-confidence hypotheses
                        hypothesis_id = hashlib.md5(f"{causal_template}{source}".encode()).hexdigest()[:12]
                        
                        hypothesis = CausalHypothesis(
                            hypothesis_id=hypothesis_id,
                            causal_template=causal_template,
                            confidence_score=confidence,
                            evidence_sources=[source],
                            extracted_entities=entities,
                            temporal_markers=self._extract_temporal_markers(news_text),
                            generated_at=datetime.now(),
                            market_impact_prediction=self._predict_market_impact(cause, effect, entities)
                        )
                        
                        hypotheses.append(hypothesis)
            
            self.logger.info(f"✓ Rule-based extraction found {len(hypotheses)} causal hypotheses from {source}")
            return hypotheses
            
        except Exception as e:
            self.logger.error(f"✗ Enhanced rule-based extraction failed: {e}")
            return []
    
    def _extract_financial_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract financial entities using regex patterns and NER"""
        entities = {
            'stock_symbols': [],
            'companies': [],
            'percentages': [],
            'dollar_amounts': [],
            'dates': [],
            'sectors': []
        }
        
        try:
            for entity_type, pattern in self.financial_patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities[entity_type] = list(set(matches))  # Remove duplicates
            
            if self.ner_pipeline:
                try:
                    ner_results = self.ner_pipeline(text[:512])  # Limit text length
                    for entity in ner_results:
                        if entity['entity_group'] in ['ORG', 'MISC']:
                            entities['companies'].append(entity['word'])
                except Exception as e:
                    self.logger.debug(f"NER extraction failed: {e}")
            
            for key in entities:
                entities[key] = list(set([item.strip() for item in entities[key] if item.strip()]))
            
            return entities
            
        except Exception as e:
            self.logger.debug(f"Entity extraction failed: {e}")
            return entities
    
    def _calculate_rule_based_confidence(self, cause: str, effect: str, entities: Dict, 
                                       sentiment_score: float, pattern_type: str) -> float:
        """Calculate confidence score for rule-based causal extraction"""
        confidence = 0.5  # Base confidence
        
        pattern_bonuses = {
            'explicit_causal': 0.2,
            'direct_causal': 0.15,
            'temporal_causal': 0.1,
            'announcement_impact': 0.15
        }
        confidence += pattern_bonuses.get(pattern_type, 0)
        
        if entities.get('stock_symbols') or entities.get('companies'):
            confidence += 0.1
        if entities.get('percentages') or entities.get('dollar_amounts'):
            confidence += 0.1
        
        if abs(sentiment_score - 0.5) > 0.2:  # Strong sentiment
            confidence += 0.05
        
        if len(cause.split()) >= 5 and len(effect.split()) >= 3:
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Extract temporal markers from text"""
        temporal_patterns = [
            r'\b(?:today|yesterday|tomorrow|now|currently|recently|soon)\b',
            r'\b(?:this|next|last)\s+(?:week|month|quarter|year)\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            r'\bQ[1-4]\s+\d{4}\b',
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b'
        ]
        
        markers = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            markers.extend(matches)
        
        return list(set(markers))
    
    def _predict_market_impact(self, cause: str, effect: str, entities: Dict) -> str:
        """Predict market impact based on cause and effect"""
        cause_lower = cause.lower()
        effect_lower = effect.lower()
        
        positive_indicators = ['beat', 'exceed', 'strong', 'growth', 'increase', 'rise', 'up', 'positive', 'good']
        negative_indicators = ['miss', 'weak', 'decline', 'decrease', 'fall', 'down', 'negative', 'poor', 'loss']
        
        positive_score = sum(1 for indicator in positive_indicators if indicator in cause_lower or indicator in effect_lower)
        negative_score = sum(1 for indicator in negative_indicators if indicator in cause_lower or indicator in effect_lower)
        
        if positive_score > negative_score:
            return "BULLISH"
        elif negative_score > positive_score:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    async def _openai_causal_extraction(self, news_text: str, source: str) -> List[CausalHypothesis]:
        """Use OpenAI GPT for sophisticated causal pattern extraction"""
        try:
            prompt = f"""
            Analyze the following financial news text and extract causal relationships in the format "Because X, therefore Y".
            Focus on identifying:
            1. Clear cause-and-effect relationships
            2. Financial entities (companies, sectors, assets)
            3. Temporal indicators (when events occurred)
            4. Confidence level of each causal claim
            
            News text: {news_text}
            
            Return a JSON array of causal hypotheses with this structure:
            {{
                "causal_template": "Because X, therefore Y",
                "confidence_score": 0.0-1.0,
                "extracted_entities": {{"cause": "X", "effect": "Y"}},
                "temporal_markers": ["time indicators"],
                "evidence_strength": "high/medium/low"
            }}
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial causal analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            try:
                causal_data = json.loads(content)
                hypotheses = []
                
                for i, item in enumerate(causal_data):
                    hypothesis = CausalHypothesis(
                        hypothesis_id=f"llm_{datetime.now().timestamp()}_{i}",
                        causal_template=item.get('causal_template', ''),
                        confidence_score=item.get('confidence_score', 0.5),
                        evidence_sources=[source],
                        extracted_entities=item.get('extracted_entities', {}),
                        temporal_markers=item.get('temporal_markers', []),
                        generated_at=datetime.now()
                    )
                    hypotheses.append(hypothesis)
                
                return hypotheses
                
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse OpenAI JSON response")
                return await self._rule_based_causal_extraction(news_text, source)
                
        except Exception as e:
            self.logger.error(f"OpenAI causal extraction error: {e}")
            return await self._rule_based_causal_extraction(news_text, source)
    
    async def _rule_based_causal_extraction(self, news_text: str, source: str) -> List[CausalHypothesis]:
        """Fallback rule-based causal pattern extraction"""
        hypotheses = []
        
        try:
            entities = {}
            if self.ner_pipeline:
                ner_results = self.ner_pipeline(news_text)
                for entity in ner_results:
                    entities[entity['entity_group']] = entity['word']
            
            causal_indicators = [
                r'because of (.+?), (.+?) (rose|fell|increased|decreased|surged|plunged)',
                r'due to (.+?), (.+?) (gained|lost|rallied|declined)',
                r'following (.+?), (.+?) (jumped|dropped|soared|tumbled)',
                r'after (.+?), (.+?) (climbed|slipped|advanced|retreated)'
            ]
            
            for i, pattern in enumerate(causal_indicators):
                matches = re.finditer(pattern, news_text, re.IGNORECASE)
                
                for match in matches:
                    cause = match.group(1).strip()
                    effect_subject = match.group(2).strip()
                    effect_direction = match.group(3).strip()
                    
                    causal_template = f"Because {cause}, therefore {effect_subject} {effect_direction}"
                    
                    confidence = 0.7 if any(word in cause.lower() for word in 
                                          ['earnings', 'fed', 'announcement', 'report']) else 0.5
                    
                    hypothesis = CausalHypothesis(
                        hypothesis_id=f"rule_{datetime.now().timestamp()}_{i}",
                        causal_template=causal_template,
                        confidence_score=confidence,
                        evidence_sources=[source],
                        extracted_entities={'cause': cause, 'effect': f"{effect_subject} {effect_direction}"},
                        temporal_markers=self._extract_temporal_markers(news_text),
                        generated_at=datetime.now()
                    )
                    
                    hypotheses.append(hypothesis)
            
            return hypotheses
            
        except Exception as e:
            self.logger.error(f"Rule-based extraction error: {e}")
            return []
    
    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Extract temporal markers from text"""
        temporal_patterns = [
            r'\b(today|yesterday|tomorrow)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(\d{1,2}:\d{2}\s*(am|pm))\b',
            r'\b(morning|afternoon|evening|night)\b',
            r'\b(before|after|during|following)\s+market\s+(open|close)\b',
            r'\b(pre|post)-market\b'
        ]
        
        markers = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            markers.extend([match if isinstance(match, str) else match[0] for match in matches])
        
        return list(set(markers))
    
    async def analyze_earnings_call_causality(self, transcript: str, 
                                            company_symbol: str) -> List[CausalHypothesis]:
        """Specialized analysis for earnings call transcripts"""
        try:
            earnings_patterns = [
                r'(revenue|sales|earnings) (increased|decreased|grew|declined) (?:by )?(\d+%?) (?:due to|because of|as a result of) (.+?)(?:\.|,)',
                r'(guidance|outlook) (?:was )?(?:raised|lowered|maintained) (?:due to|because of) (.+?)(?:\.|,)',
                r'(margin|profitability) (improved|deteriorated|expanded|compressed) (?:due to|because of) (.+?)(?:\.|,)'
            ]
            
            hypotheses = []
            
            for i, pattern in enumerate(earnings_patterns):
                matches = re.finditer(pattern, transcript, re.IGNORECASE)
                
                for match in matches:
                    if len(match.groups()) >= 4:
                        metric = match.group(1)
                        direction = match.group(2)
                        magnitude = match.group(3) if len(match.groups()) > 3 else ""
                        cause = match.group(-1).strip()
                        
                        causal_template = f"Because {cause}, therefore {company_symbol} {metric} {direction} {magnitude}".strip()
                        
                        hypothesis = CausalHypothesis(
                            hypothesis_id=f"earnings_{company_symbol}_{datetime.now().timestamp()}_{i}",
                            causal_template=causal_template,
                            confidence_score=0.8,  # Higher confidence for earnings calls
                            evidence_sources=[f"earnings_call_{company_symbol}"],
                            extracted_entities={
                                'company': company_symbol,
                                'metric': metric,
                                'direction': direction,
                                'cause': cause
                            },
                            temporal_markers=self._extract_temporal_markers(transcript),
                            generated_at=datetime.now()
                        )
                        
                        hypotheses.append(hypothesis)
            
            return hypotheses
            
        except Exception as e:
            self.logger.error(f"Earnings call analysis error: {e}")
            return []
    
    async def validate_causal_hypothesis(self, hypothesis: CausalHypothesis, 
                                       market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate causal hypothesis against market data"""
        try:
            validation_result = {
                'hypothesis_id': hypothesis.hypothesis_id,
                'original_confidence': hypothesis.confidence_score,
                'market_validation_score': 0.0,
                'supporting_evidence': [],
                'contradicting_evidence': [],
                'final_confidence': hypothesis.confidence_score
            }
            
            entities = hypothesis.extracted_entities
            
            if 'effect' in entities and 'cause' in entities:
                effect = entities['effect'].lower()
                
                if any(word in effect for word in ['rose', 'increased', 'gained', 'surged']):
                    expected_direction = 'positive'
                elif any(word in effect for word in ['fell', 'decreased', 'lost', 'plunged']):
                    expected_direction = 'negative'
                else:
                    expected_direction = 'neutral'
                
                actual_return = market_data.get('price_change_percent', 0)
                
                if expected_direction == 'positive' and actual_return > 0.01:
                    validation_result['market_validation_score'] = 0.8
                    validation_result['supporting_evidence'].append('Price movement matches prediction')
                elif expected_direction == 'negative' and actual_return < -0.01:
                    validation_result['market_validation_score'] = 0.8
                    validation_result['supporting_evidence'].append('Price movement matches prediction')
                elif abs(actual_return) < 0.005:  # Neutral movement
                    validation_result['market_validation_score'] = 0.4
                    validation_result['supporting_evidence'].append('Neutral price movement')
                else:
                    validation_result['market_validation_score'] = 0.2
                    validation_result['contradicting_evidence'].append('Price movement contradicts prediction')
            
            validation_result['final_confidence'] = (
                hypothesis.confidence_score * 0.6 + 
                validation_result['market_validation_score'] * 0.4
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Hypothesis validation error: {e}")
            return {'error': str(e)}
    
    async def generate_causal_insights_report(self, hypotheses: List[CausalHypothesis]) -> Dict[str, Any]:
        """Generate comprehensive causal insights report"""
        try:
            if not hypotheses:
                return {'error': 'No hypotheses to analyze'}
            
            confidence_distribution = [h.confidence_score for h in hypotheses]
            entity_frequency = {}
            temporal_patterns = {}
            
            for hypothesis in hypotheses:
                for entity_type, entity_value in hypothesis.extracted_entities.items():
                    if entity_type not in entity_frequency:
                        entity_frequency[entity_type] = {}
                    if entity_value not in entity_frequency[entity_type]:
                        entity_frequency[entity_type][entity_value] = 0
                    entity_frequency[entity_type][entity_value] += 1
                
                for marker in hypothesis.temporal_markers:
                    if marker not in temporal_patterns:
                        temporal_patterns[marker] = 0
                    temporal_patterns[marker] += 1
            
            report = {
                'total_hypotheses': len(hypotheses),
                'average_confidence': sum(confidence_distribution) / len(confidence_distribution),
                'high_confidence_count': len([h for h in hypotheses if h.confidence_score > 0.7]),
                'entity_frequency': entity_frequency,
                'temporal_patterns': temporal_patterns,
                'top_causal_templates': [h.causal_template for h in 
                                       sorted(hypotheses, key=lambda x: x.confidence_score, reverse=True)[:5]],
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Report generation error: {e}")
            return {'error': str(e)}

async def integrate_llm_with_existing_systems():
    """Integration function to connect LLM causal inference with existing systems"""
    try:
        from .causal_driver_graph import CausalDriverGraph
        from .neo4j_spatio_temporal_graph import Neo4jSpatioTemporalGraph
        
        llm_inference = LLMAssistedCausalInference()
        
        sample_news = """
        Apple Inc. reported better-than-expected quarterly earnings, with revenue increasing 8% 
        due to strong iPhone sales in China. Following the announcement, AAPL shares surged 5% 
        in after-hours trading. The company also raised its guidance for the next quarter 
        because of continued demand for its services segment.
        """
        
        hypotheses = await llm_inference.extract_causal_patterns_from_news(
            sample_news, "financial_news"
        )
        
        insights_report = await llm_inference.generate_causal_insights_report(hypotheses)
        
        return {
            'llm_integration': True,
            'hypotheses_generated': len(hypotheses),
            'insights_report': insights_report,
            'sample_hypothesis': hypotheses[0].causal_template if hypotheses else None
        }
        
    except Exception as e:
        logging.error(f"LLM integration error: {e}")
        return {'llm_integration': False, 'error': str(e)}
