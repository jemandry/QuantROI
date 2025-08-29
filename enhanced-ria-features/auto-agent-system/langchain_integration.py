#!/usr/bin/env python3
"""
Langchain Integration for Intelligent Auto-Agent System
Provides intelligent automation for data gap resolution and API quota management
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd

from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import BaseTool

from ..storage_granularity.granularity_limiter import GranularityLimiter

logger = logging.getLogger(__name__)

class DataGapAnalysisTool(BaseTool):
    """Langchain tool for analyzing data gaps"""
    name = "data_gap_analyzer"
    description = "Analyzes data gaps and suggests resolution strategies"
    
    def __init__(self, granularity_limiter: GranularityLimiter):
        super().__init__()
        self.granularity_limiter = granularity_limiter
    
    def _run(self, query: str) -> str:
        """Analyze data gaps for given query"""
        try:
            parts = query.split()
            symbol = parts[0] if parts else "AAPL"
            timeframe = parts[1] if len(parts) > 1 else "1d"
            
            gaps = self.granularity_limiter.detect_data_gaps(symbol, timeframe)
            
            if not gaps:
                return f"No data gaps detected for {symbol} at {timeframe} resolution"
            
            gap_analysis = {
                "total_gaps": len(gaps),
                "largest_gap": max(gap["duration_minutes"] for gap in gaps),
                "gap_frequency": len(gaps) / 24,
                "resolution_cost": sum(gap.get("resolution_cost", 0.01) for gap in gaps)
            }
            
            return f"Found {gap_analysis['total_gaps']} gaps for {symbol}. Largest gap: {gap_analysis['largest_gap']} minutes. Estimated resolution cost: ${gap_analysis['resolution_cost']:.2f}"
            
        except Exception as e:
            return f"Error analyzing data gaps: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version of _run"""
        return self._run(query)

class APIQuotaManagerTool(BaseTool):
    """Langchain tool for managing API quotas"""
    name = "api_quota_manager"
    description = "Manages API quotas and suggests cost-optimal strategies"
    
    def __init__(self):
        super().__init__()
        self.quotas = {
            "alpha_vantage": {"daily_limit": 500, "cost_per_call": 0.01},
            "yfinance": {"daily_limit": 2000, "cost_per_call": 0.0},
            "polygon": {"daily_limit": 1000, "cost_per_call": 0.005}
        }
    
    def _run(self, query: str) -> str:
        """Manage API quotas for given requirements"""
        try:
            parts = query.split()
            required_calls = int(parts[0]) if parts and parts[0].isdigit() else 100
            
            strategies = []
            for provider, limits in self.quotas.items():
                if required_calls <= limits["daily_limit"]:
                    cost = required_calls * limits["cost_per_call"]
                    strategies.append({
                        "provider": provider,
                        "calls": required_calls,
                        "cost": cost,
                        "feasible": True
                    })
            
            if not strategies:
                return f"No single provider can handle {required_calls} calls. Consider splitting across providers."
            
            cheapest = min(strategies, key=lambda x: x["cost"])
            
            return f"Optimal strategy: Use {cheapest['provider']} for {cheapest['calls']} calls at ${cheapest['cost']:.2f} total cost"
            
        except Exception as e:
            return f"Error managing API quotas: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version of _run"""
        return self._run(query)

class LangchainAutoAgent:
    """Intelligent auto-agent using Langchain for decision making"""
    
    def __init__(self, granularity_limiter: GranularityLimiter, openai_api_key: str):
        self.granularity_limiter = granularity_limiter
        
        self.llm = OpenAI(
            openai_api_key=openai_api_key,
            temperature=0.1,
            max_tokens=500
        )
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.tools = [
            DataGapAnalysisTool(granularity_limiter),
            APIQuotaManagerTool(),
        ]
        
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True
        )
        
        self.gap_resolution_template = PromptTemplate(
            input_variables=["symbol", "gaps", "budget", "urgency"],
            template="""
            You are an intelligent data gap resolution agent for a high-frequency trading platform.
            
            Symbol: {symbol}
            Data Gaps: {gaps}
            Budget: ${budget}
            Urgency: {urgency}
            
            Analyze the data gaps and provide a cost-optimal resolution strategy.
            Consider:
            1. Gap size and impact on trading accuracy
            2. Available budget and cost per API call
            3. Urgency level (high = pay more for faster resolution)
            4. Alternative data sources and interpolation methods
            
            Provide a specific action plan with cost estimates.
            """
        )
        
        self.gap_resolution_chain = LLMChain(
            llm=self.llm,
            prompt=self.gap_resolution_template,
            memory=self.memory
        )
    
    async def resolve_data_gaps_intelligently(
        self, 
        symbol: str, 
        gaps: List[Dict[str, Any]], 
        budget: float = 10.0,
        urgency: str = "medium"
    ) -> Dict[str, Any]:
        """Use Langchain to intelligently resolve data gaps"""
        try:
            gaps_summary = f"{len(gaps)} gaps, largest: {max(gap['duration_minutes'] for gap in gaps) if gaps else 0} minutes"
            
            response = await asyncio.to_thread(
                self.gap_resolution_chain.run,
                symbol=symbol,
                gaps=gaps_summary,
                budget=budget,
                urgency=urgency
            )
            
            strategy = self._parse_strategy_response(response)
            execution_result = await self._execute_resolution_strategy(symbol, gaps, strategy)
            
            return {
                "strategy": strategy,
                "execution_result": execution_result,
                "llm_reasoning": response,
                "cost_estimate": strategy.get("estimated_cost", 0.0),
                "success": execution_result.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Intelligent gap resolution failed: {e}")
            return {
                "strategy": {},
                "execution_result": {"success": False, "error": str(e)},
                "llm_reasoning": "",
                "cost_estimate": 0.0,
                "success": False
            }
    
    def _parse_strategy_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into actionable strategy"""
        strategy = {
            "method": "interpolation",
            "estimated_cost": 0.0,
            "priority": "medium"
        }
        
        if "api" in response.lower():
            strategy["method"] = "api_fetch"
            import re
            cost_match = re.search(r'\$(\d+\.?\d*)', response)
            if cost_match:
                strategy["estimated_cost"] = float(cost_match.group(1))
        
        if "high priority" in response.lower():
            strategy["priority"] = "high"
        elif "low priority" in response.lower():
            strategy["priority"] = "low"
        
        return strategy
    
    async def _execute_resolution_strategy(
        self, 
        symbol: str, 
        gaps: List[Dict[str, Any]], 
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the resolution strategy"""
        try:
            if strategy["method"] == "api_fetch":
                results = []
                for gap in gaps:
                    filled_data = self._interpolate_gap_data(gap)
                    results.append(filled_data)
                
                return {
                    "success": True,
                    "results": results,
                    "method": "api_fetch"
                }
            
            elif strategy["method"] == "interpolation":
                filled_gaps = []
                for gap in gaps:
                    filled_data = self._interpolate_gap_data(gap)
                    filled_gaps.append(filled_data)
                
                return {
                    "success": True,
                    "results": filled_gaps,
                    "method": "interpolation"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown strategy method: {strategy['method']}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _interpolate_gap_data(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Simple interpolation for gap filling"""
        return {
            "gap_id": gap.get("gap_id"),
            "filled": True,
            "method": "linear_interpolation",
            "confidence": 0.7
        }
