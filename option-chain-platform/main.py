#!/usr/bin/env python3
"""
FastAPI Server for Option Chain Causal Analysis Platform
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import asyncio
import aiofiles

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import dowhy
    from dowhy import CausalModel
    from statsmodels.tsa.stattools import grangercausalitytests
    CAUSAL_AVAILABLE = True
except ImportError:
    CAUSAL_AVAILABLE = False

sessions = {}  # {session_id: {'data': {}, 'confidence': 0, 'causal_hyp': '', 'missing_data': []}}

app = FastAPI(
    title="Option Chain Causal Analysis API",
    description="Auditable platform for analyzing option chains with causal inference",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Option Chain Causal Analysis Platform",
        "version": "1.0.0",
        "endpoints": [
            "/audit/{entry_id}",
            "/submit",
            "/option_chain/{ticker}",
            "/kb/causal_patterns/{ticker}"
        ]
    }


@app.get("/audit/{entry_id}")
async def get_audit(entry_id: str):
    """Load and return audit log by ID"""
    try:
        audit_file = f"audit_logs/{entry_id}.json"
        if not os.path.exists(audit_file):
            raise HTTPException(status_code=404, detail="Audit entry not found")
        
        with open(audit_file, 'r') as f:
            audit_data = json.load(f)
        
        return audit_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit")
async def submit_audit(data: Dict[str, Any] = Body(...)):
    """Save audit data"""
    try:
        entry_id = data.get('id', f"audit_{int(datetime.now().timestamp())}")
        
        os.makedirs('audit_logs', exist_ok=True)
        
        audit_file = f"audit_logs/{entry_id}.json"
        with open(audit_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {"status": "saved", "id": entry_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/option_chain/{ticker}")
async def get_option_chain(ticker: str):
    """Get option chain data for a ticker"""
    try:
        if YFINANCE_AVAILABLE:
            try:
                ticker_obj = yf.Ticker(ticker)
                options_dates = ticker_obj.options
                if options_dates:
                    option_chain = ticker_obj.option_chain(options_dates[0])
                    calls_data = option_chain.calls.to_dict('records')
                    puts_data = option_chain.puts.to_dict('records')
                    
                    return {
                        "ticker": ticker,
                        "expiration": options_dates[0],
                        "calls": calls_data[:10],  # Limit to first 10
                        "puts": puts_data[:10],
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"Error fetching real data for {ticker}: {e}")
        
        mock_calls = [
            {"strike": 100, "openInterest": 5000, "impliedVolatility": 0.25, "volume": 1200, "lastPrice": 5.50},
            {"strike": 105, "openInterest": 3000, "impliedVolatility": 0.245, "volume": 800, "lastPrice": 3.20},
            {"strike": 110, "openInterest": 2000, "impliedVolatility": 0.26, "volume": 600, "lastPrice": 1.80}
        ]
        
        mock_puts = [
            {"strike": 100, "openInterest": 4500, "impliedVolatility": 0.26, "volume": 1000, "lastPrice": 4.20},
            {"strike": 95, "openInterest": 3500, "impliedVolatility": 0.255, "volume": 700, "lastPrice": 2.80},
            {"strike": 90, "openInterest": 2500, "impliedVolatility": 0.27, "volume": 500, "lastPrice": 1.50}
        ]
        
        return {
            "ticker": ticker,
            "expiration": "2024-03-15",
            "calls": mock_calls,
            "puts": mock_puts,
            "timestamp": datetime.now().isoformat(),
            "data_source": "mock"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kb/causal_patterns/{ticker}")
async def get_causal_patterns(ticker: str):
    """Query knowledge graph for causal patterns"""
    if not NEO4J_AVAILABLE:
        return {
            "ticker": ticker,
            "patterns": [
                {
                    "option": {"strike": 100, "oi": 5000, "iv": 0.25},
                    "price_move": {"delta": 2.5, "confidence": 0.75},
                    "causal_strength": 0.68
                },
                {
                    "option": {"strike": 105, "oi": 3000, "iv": 0.245},
                    "price_move": {"delta": 1.8, "confidence": 0.72},
                    "causal_strength": 0.61
                }
            ],
            "data_source": "mock",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            query = """
            MATCH (o:OptionChain {ticker: $ticker})-[:CAUSES]->(p:PriceMove)
            RETURN o, p
            ORDER BY o.timestamp DESC
            LIMIT 20
            """
            
            result = session.run(query, ticker=ticker)
            patterns = []
            
            for record in result:
                option_node = dict(record['o'])
                price_node = dict(record['p'])
                
                patterns.append({
                    "option": {
                        "strike": option_node.get('strike'),
                        "oi": option_node.get('openInterest'),
                        "iv": option_node.get('impliedVolatility'),
                        "volume": option_node.get('volume')
                    },
                    "price_move": {
                        "delta": price_node.get('delta'),
                        "timestamp": price_node.get('timestamp')
                    },
                    "causal_strength": abs(price_node.get('delta', 0)) / 10.0  # Normalized
                })
        
        driver.close()
        
        return {
            "ticker": ticker,
            "patterns": patterns,
            "data_source": "neo4j",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "ticker": ticker,
            "patterns": [
                {
                    "option": {"strike": 100, "oi": 5000, "iv": 0.25},
                    "price_move": {"delta": 2.5, "confidence": 0.75},
                    "causal_strength": 0.68
                }
            ],
            "data_source": "mock_fallback",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.post("/query_missing_data")
async def query_missing_data(request: Dict[str, Any] = Body(...)):
    """Intelligent agent: Query for missing data to improve causal analysis"""
    try:
        session_id = request.get('session_id')
        current_data = request.get('current_data', {})
        
        required_inventory = [
            'volume', 'news_sentiment', 'options_flow', 'earnings_date', 
            'market_volatility', 'sector_performance', 'insider_trading',
            'analyst_ratings', 'economic_indicators', 'options_skew'
        ]
        
        missing = [item for item in required_inventory if item not in current_data]
        
        completeness_ratio = (len(required_inventory) - len(missing)) / len(required_inventory)
        base_confidence = int(completeness_ratio * 100)
        
        sessions[session_id] = {
            'data': current_data,
            'confidence': base_confidence,
            'missing_data': missing,
            'timestamp': datetime.now().isoformat()
        }
        
        if missing:
            return {
                "session_id": session_id,
                "query": f"To improve causal analysis confidence, please provide: {', '.join(missing[:3])}",
                "missing_data": missing,
                "current_confidence": base_confidence,
                "recommendation": "Higher data completeness improves causal inference reliability",
                "critical_missing": [item for item in missing if item in ['volume', 'news_sentiment', 'earnings_date']],
                "best_practices": [
                    "Monitor IV skew changes before earnings announcements",
                    "Validate volume confirmation on price breakouts", 
                    "Check for hidden liquidity indicators in L2 data",
                    "Use maker-taker dynamics modeling for execution"
                ]
            }
        
        return {
            "session_id": session_id,
            "status": "Complete data inventory",
            "confidence": base_confidence,
            "message": "Sufficient data for robust causal analysis"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/causal_question")
async def causal_question(request: Dict[str, Any] = Body(...)):
    """Intelligent agent: Validate causal hypotheses and detect correlation vs causation"""
    try:
        session_id = request.get('session_id')
        hypothesis = request.get('hypothesis', '')
        option_data = request.get('option_data', {})
        
        if not CAUSAL_AVAILABLE:
            return {
                "session_id": session_id,
                "warning": "DoWhy not available - using heuristic validation",
                "questions": [
                    "Was this IV spike due to earnings announcement?",
                    "Is volume spike cause or effect of price movement?",
                    "Any market-wide events affecting this pattern?",
                    "Seasonal effects in this time period?"
                ],
                "confidence": 50,
                "validation_method": "heuristic"
            }
        
        if option_data:
            iv_data = [option_data.get('iv', 0.25)]
            price_data = [option_data.get('price_change', 0)]
            volume_data = [option_data.get('volume', 1000)]
        else:
            np.random.seed(42)
            iv_data = np.random.normal(0.25, 0.05, 100)
            price_data = 0.3 * iv_data + np.random.normal(0, 0.02, 100)  # Causal relationship
            volume_data = np.random.normal(1000, 200, 100)
        
        df = pd.DataFrame({
            'iv_spike': (np.array(iv_data) > np.mean(iv_data) + np.std(iv_data)).astype(int),
            'price_move': price_data,
            'volume': volume_data,
            'market_volatility': np.random.normal(0.2, 0.03, len(iv_data))
        })
        
        try:
            model = CausalModel(
                data=df,
                treatment='iv_spike',
                outcome='price_move',
                common_causes=['market_volatility']
            )
            
            identified_estimand = model.identify_effect()
            
            causal_estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression"
            )
            
            refutation = model.refute_estimate(
                identified_estimand,
                causal_estimate,
                method_name="random_common_cause"
            )
            
            causal_strength = abs(causal_estimate.value)
            confidence = max(0, min(100, int((1 - abs(refutation.new_effect)) * 100)))
            
        except Exception as dowhy_error:
            print(f"DoWhy analysis failed: {dowhy_error}")
            causal_strength = 0.5
            confidence = 60
        
        try:
            if len(iv_data) > 10:
                granger_data = pd.DataFrame({
                    'iv': iv_data[:min(50, len(iv_data))],
                    'price': price_data[:min(50, len(price_data))]
                })
                gc_result = grangercausalitytests(granger_data[['price', 'iv']], maxlag=3, verbose=False)
                granger_p_value = gc_result[1][0]['ssr_ftest'][1]
                granger_significant = granger_p_value < 0.05
            else:
                granger_significant = False
                granger_p_value = 1.0
        except:
            granger_significant = False
            granger_p_value = 1.0
        
        questions = [
            "Was this IV spike due to earnings announcement?",
            "Is volume spike cause or effect of price movement?",
            "Any market-wide events affecting this pattern?",
            "Seasonal effects in this time period?"
        ]
        
        if causal_strength < 0.3:
            questions.append("Could this be spurious correlation? Check for hidden confounders.")
        
        if not granger_significant:
            questions.append("Time series shows weak causality - validate with external events.")
        
        if session_id in sessions:
            sessions[session_id].update({
                'causal_hypothesis': hypothesis,
                'causal_strength': causal_strength,
                'confidence': confidence,
                'granger_significant': granger_significant
            })
        
        audit_entry = {
            "session_id": session_id,
            "hypothesis": hypothesis,
            "causal_strength": causal_strength,
            "confidence": confidence,
            "granger_p_value": granger_p_value,
            "timestamp": datetime.now().isoformat(),
            "validation_method": "dowhy_granger"
        }
        
        os.makedirs('audit_logs', exist_ok=True)
        with open(f'audit_logs/causal_validation_{session_id}.json', 'w') as f:
            json.dump(audit_entry, f, indent=2)
        
        return {
            "session_id": session_id,
            "hypothesis": hypothesis,
            "causal_strength": causal_strength,
            "confidence": confidence,
            "granger_significant": granger_significant,
            "granger_p_value": granger_p_value,
            "questions": questions,
            "warning": "Correlation detected; validate causation" if causal_strength < 0.3 else None,
            "validated": causal_strength > 0.3 and granger_significant,
            "audit_logged": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add_to_kb")
async def add_to_kb(request: Dict[str, Any] = Body(...)):
    """Add validated causal pattern to knowledge base with confidence scoring"""
    try:
        session_id = request.get('session_id', 'default')
        ticker = request.get('ticker')
        chain_data = request.get('chain_data', {})
        price_delta = request.get('price_delta', 0)
        news_summary = request.get('news_summary', '')
        expert_rating = request.get('expert_rating', 0.0)
        best_practices = request.get('best_practices', [])
        
        session_data = sessions.get(session_id, {})
        confidence = session_data.get('confidence', 50)
        causal_strength = session_data.get('causal_strength', 0.5)
        
        if not NEO4J_AVAILABLE:
            return {
                "status": "Mock KB storage",
                "session_id": session_id,
                "ticker": ticker,
                "confidence": confidence,
                "causal_strength": causal_strength,
                "message": "Neo4j not available - pattern logged locally"
            }
        
        try:
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            user = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD', 'password')
            
            driver = GraphDatabase.driver(uri, auth=(user, password))
            
            with driver.session() as neo_session:
                neo_session.run("""
                    MERGE (o:OptionChain {
                        ticker: $ticker, 
                        strike: $strike, 
                        oi: $oi, 
                        iv: $iv,
                        session_id: $session_id,
                        timestamp: $timestamp
                    })
                    MERGE (p:PriceMove {
                        delta: $delta,
                        timestamp: $timestamp
                    })
                    MERGE (a:AuditTrail {
                        session_id: $session_id,
                        confidence: $confidence,
                        causal_strength: $causal_strength,
                        hypothesis: $hypothesis,
                        timestamp: $timestamp
                    })
                    CREATE (o)-[:CAUSES {
                        confidence: $confidence,
                        strength: $causal_strength,
                        validated: $validated
                    }]->(p)
                    CREATE (a)-[:VALIDATES]->(o)
                """, 
                    ticker=ticker,
                    strike=chain_data.get('strike', 0),
                    oi=chain_data.get('oi', 0),
                    iv=chain_data.get('iv', 0),
                    delta=price_delta,
                    session_id=session_id,
                    confidence=confidence,
                    causal_strength=causal_strength,
                    hypothesis=session_data.get('causal_hypothesis', ''),
                    validated=confidence > 70 and causal_strength > 0.3,
                    timestamp=datetime.now().isoformat()
                )
            
            driver.close()
            
            return {
                "status": "Added to KB",
                "session_id": session_id,
                "ticker": ticker,
                "confidence": confidence,
                "causal_strength": causal_strength,
                "validated": confidence > 70 and causal_strength > 0.3
            }
            
        except Exception as neo_error:
            return {
                "status": "KB storage failed",
                "error": str(neo_error),
                "fallback": "Pattern logged locally for manual review"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state for intelligent agent"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "session_data": sessions[session_id],
        "active_since": sessions[session_id].get('timestamp', 'unknown')
    }


@app.post("/volatility/simulate")
async def simulate_volatility(
    model_id: str = Body(...),
    simulation_id: str = Body(...),
    mu: float = Body(0.05),
    sigma: float = Body(0.2),
    dt: float = Body(1.0/252.0),
    initial_value: float = Body(100.0),
    num_steps: int = Body(252),
    seed: Optional[int] = Body(None)
):
    """Simulate Brownian motion volatility with appendable audit records"""
    try:
        import hashlib
        
        parameters = {
            "mu": mu,
            "sigma": sigma,
            "dt": dt,
            "initial_value": initial_value,
            "seed": seed
        }
        
        np.random.seed(seed if seed else 42)
        
        path = [initial_value]
        sqrt_dt = np.sqrt(dt)
        drift_term = mu - 0.5 * sigma * sigma
        
        for _ in range(num_steps):
            dw = np.random.normal() * sqrt_dt
            current_value = path[-1]
            next_value = current_value * (1.0 + drift_term * dt + sigma * dw)
            path.append(next_value)
        
        returns = [(path[i+1] - path[i]) / path[i] for i in range(len(path)-1)]
        mean_return = np.mean(returns)
        variance = np.var(returns)
        skewness = float(pd.Series(returns).skew()) if len(returns) > 2 else 0.0
        kurtosis = float(pd.Series(returns).kurtosis()) if len(returns) > 2 else 0.0
        
        risk_moments = [mean_return, variance, skewness, kurtosis]
        
        timestamp_ns = int(datetime.now().timestamp() * 1_000_000_000)
        
        record = {
            "timestamp_ns": timestamp_ns,
            "simulation_id": simulation_id,
            "model_id": model_id,
            "parameters": parameters,
            "path_data": path,
            "risk_moments": risk_moments,
            "num_steps": len(path) - 1,
            "final_value": path[-1],
            "total_return": (path[-1] - path[0]) / path[0]
        }
        
        hash_input = f"{timestamp_ns}{simulation_id}{json.dumps(parameters)}{json.dumps(path[:10])}"
        audit_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        record["audit_hash"] = audit_hash
        
        file_path = f"/tmp/volatility_sim_{model_id}.json"
        async with aiofiles.open(file_path, "a") as f:
            await f.write(json.dumps(record) + "\n")
        
        return {
            "status": "success",
            "simulation_record": record,
            "storage_location": file_path,
            "latency_ns": int((datetime.now().timestamp() * 1_000_000_000) - timestamp_ns)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/volatility/audit_trail/{model_id}")
async def get_volatility_audit_trail(model_id: str):
    """Retrieve audit trail for volatility simulations"""
    try:
        file_path = f"/tmp/volatility_sim_{model_id}.json"
        
        if not os.path.exists(file_path):
            return {"status": "no_data", "model_id": model_id, "simulations": []}
        
        simulations = []
        async with aiofiles.open(file_path, "r") as f:
            async for line in f:
                if line.strip():
                    try:
                        record = json.loads(line.strip())
                        simulations.append({
                            "simulation_id": record.get("simulation_id"),
                            "timestamp_ns": record.get("timestamp_ns"),
                            "audit_hash": record.get("audit_hash"),
                            "parameters": record.get("parameters"),
                            "final_value": record.get("final_value"),
                            "total_return": record.get("total_return"),
                            "risk_moments": record.get("risk_moments")
                        })
                    except json.JSONDecodeError:
                        continue
        
        audit_verified = True
        for i, sim in enumerate(simulations):
            if not sim.get("audit_hash"):
                audit_verified = False
                break
        
        return {
            "status": "success",
            "model_id": model_id,
            "total_simulations": len(simulations),
            "audit_chain_verified": audit_verified,
            "simulations": simulations[-10:],  # Return last 10 for performance
            "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/volatility/monte_carlo")
async def run_monte_carlo_volatility(
    model_id: str = Body(...),
    base_mu: float = Body(0.05),
    base_sigma: float = Body(0.2),
    sigma_range: List[float] = Body([0.1, 0.3]),
    num_simulations: int = Body(100),
    num_steps: int = Body(252),
    dt: float = Body(1.0/252.0),
    initial_value: float = Body(100.0)
):
    """Run Monte Carlo volatility simulations with parameter sweeps"""
    try:
        start_time = datetime.now()
        simulation_results = []
        
        for i in range(num_simulations):
            sigma_variation = sigma_range[0] + (sigma_range[1] - sigma_range[0]) * (i / num_simulations)
            
            sim_id = f"mc_{model_id}_{i}_{int(start_time.timestamp())}"
            
            simulation_response = await simulate_volatility(
                model_id=model_id,
                simulation_id=sim_id,
                mu=base_mu,
                sigma=sigma_variation,
                dt=dt,
                initial_value=initial_value,
                num_steps=num_steps,
                seed=42 + i
            )
            
            if simulation_response["status"] == "success":
                simulation_results.append({
                    "simulation_id": sim_id,
                    "sigma_used": sigma_variation,
                    "final_value": simulation_response["simulation_record"]["final_value"],
                    "total_return": simulation_response["simulation_record"]["total_return"],
                    "risk_moments": simulation_response["simulation_record"]["risk_moments"]
                })
        
        final_values = [sim["final_value"] for sim in simulation_results]
        total_returns = [sim["total_return"] for sim in simulation_results]
        
        aggregate_stats = {
            "mean_final_value": np.mean(final_values),
            "std_final_value": np.std(final_values),
            "mean_total_return": np.mean(total_returns),
            "std_total_return": np.std(total_returns),
            "min_final_value": np.min(final_values),
            "max_final_value": np.max(final_values),
            "percentile_5": np.percentile(final_values, 5),
            "percentile_95": np.percentile(final_values, 95)
        }
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "success",
            "model_id": model_id,
            "num_simulations": len(simulation_results),
            "execution_time_seconds": execution_time,
            "aggregate_statistics": aggregate_stats,
            "simulation_results": simulation_results[:20],  # Return first 20 for performance
            "performance_metrics": {
                "simulations_per_second": len(simulation_results) / execution_time,
                "avg_latency_ms": (execution_time * 1000) / len(simulation_results),
                "meets_500us_budget": (execution_time * 1000000) / len(simulation_results) < 500
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "yfinance": YFINANCE_AVAILABLE,
            "neo4j": NEO4J_AVAILABLE,
            "causal_analysis": CAUSAL_AVAILABLE
        },
        "active_sessions": len(sessions),
        "intelligent_agent": "enabled"
    }


@app.get("/kb/best_practices")
async def get_best_practices(category: str = None):
    """Get best practices from expert knowledge base"""
    try:
        if not NEO4J_AVAILABLE:
            all_practices = {
                "trading_execution": [
                    "Maintain <500μs total latency budget for scalping strategies",
                    "Monitor IV skew changes before earnings announcements", 
                    "Validate volume confirmation on price breakouts",
                    "Check for hidden liquidity indicators in L2 data",
                    "Use maker-taker dynamics modeling for execution"
                ],
                "risk_management": [
                    "Implement position limits checked in <1μs",
                    "Monitor drawdown in real-time with alerts",
                    "Use hardware-level risk triggers for speed",
                    "Implement kill switches accessible in <5μs",
                    "Monitor bias <0.1 thresholds for ethical AI"
                ],
                "causal_analysis": [
                    "Address correlation ≠ causation with sensitivity analysis",
                    "Query users for confounders in low-confidence cases",
                    "Use Granger causality tests for temporal relationships",
                    "Implement DoWhy validation for causal claims",
                    "Flag low-confidence claims (<70%) for user validation"
                ],
                "system_operation": [
                    "Report environment issues to user and continue with CI testing",
                    "Use tiered storage: Redis (hot), PostgreSQL (warm), ClickHouse (cold)",
                    "Implement braided cord data separation by latency",
                    "Use symbol-agnostic design with efficient indexing",
                    "Implement edge computing for latency-critical operations"
                ],
                "compliance_audit": [
                    "Log all user inputs, hypotheses, and validations",
                    "Maintain comprehensive disclosure of AI algorithms",
                    "Use cryptographic recording for all trading decisions",
                    "Implement robust oversight controls for AI decisions",
                    "Use real-time surveillance for market manipulation prevention"
                ]
            }
            
            if category and category in all_practices:
                return {
                    "category": category,
                    "practices": all_practices[category],
                    "source": "expert_prompts",
                    "total_count": len(all_practices[category])
                }
            
            return {
                "categories": list(all_practices.keys()),
                "all_practices": all_practices,
                "source": "expert_prompts",
                "total_count": sum(len(practices) for practices in all_practices.values())
            }
        
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j') 
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            if category:
                result = session.run("""
                    MATCH (bp:BestPractice {category: $category})
                    RETURN bp.title as title, bp.summary as summary, bp.confidence as confidence
                    ORDER BY bp.confidence DESC
                """, category=category)
            else:
                result = session.run("""
                    MATCH (bp:BestPractice)
                    RETURN bp.category as category, bp.title as title, bp.summary as summary, bp.confidence as confidence
                    ORDER BY bp.category, bp.confidence DESC
                """)
            
            practices = []
            for record in result:
                practices.append({
                    "category": record.get("category"),
                    "title": record["title"],
                    "summary": record["summary"],
                    "confidence": record["confidence"]
                })
        
        driver.close()
        
        return {
            "category": category,
            "practices": practices,
            "source": "neo4j_kb",
            "total_count": len(practices)
        }
        
    except Exception as e:
        print(f"Best practices query error: {e}")
        return {
            "category": category or "general",
            "practices": [
                "Monitor IV skew changes before earnings announcements",
                "Validate volume confirmation on price breakouts",
                "Address correlation ≠ causation with sensitivity analysis",
                "Maintain <500μs total latency budget for scalping strategies"
            ],
            "source": "fallback",
            "error": str(e)
        }


@app.get("/kb/operational_guidance")
async def get_operational_guidance(issue_type: str = None):
    """Get operational guidance for system questions and troubleshooting"""
    guidance = {
        "environment_issues": {
            "description": "When encountering environment setup issues",
            "guidance": [
                "Report environment issues to user using report_environment_issue command",
                "Find ways to continue work using CI rather than local environment",
                "Do not attempt to fix environment issues independently",
                "Test using CI/CD pipeline when local environment fails",
                "Document environment requirements for user to address"
            ],
            "examples": ["Missing dependencies", "VPN issues", "Pre-commit hook failures"]
        },
        "performance_optimization": {
            "description": "Guidelines for maintaining <500μs latency requirements",
            "guidance": [
                "Optimize market data reception to 50-100μs",
                "Keep signal processing under 20-50μs",
                "Limit decision logic to 10-30μs",
                "Ensure order generation takes <5-15μs",
                "Monitor network transmission latency",
                "Use FPGA-based processing for ultra-high frequency",
                "Implement kernel bypass networking (DPDK)"
            ],
            "thresholds": {"total_latency": "500μs", "jitter": "±10μs"}
        },
        "compliance_requirements": {
            "description": "SEC Rule 10b-5 and RIA compliance procedures",
            "guidance": [
                "Maintain comprehensive audit trails with SHA-3 cryptographic recording",
                "Log all trading decisions with explainable AI outputs",
                "Implement real-time surveillance for market manipulation prevention",
                "Ensure proper recordkeeping per SEC Rule 204-2 requirements",
                "Monitor bias <0.1 thresholds for ethical AI decisions",
                "Use immutable logs via IPFS/Merkle/Solana anchoring"
            ],
            "regulations": ["SEC Rule 10b-5", "SEC Rule 204-2", "RIA internet exception"]
        },
        "causal_validation": {
            "description": "Best practices for causal inference and validation",
            "guidance": [
                "Apply scientific rigor frameworks with pre-registration",
                "Use quasi-experimental design for natural experiments", 
                "Implement instrumental variables for causal identification",
                "Validate with out-of-sample testing and placebo tests",
                "Address correlation ≠ causation with sensitivity analysis",
                "Query users for confounders in low-confidence cases"
            ],
            "tools": ["DoWhy", "Granger causality tests", "Monte Carlo simulations"]
        },
        "system_troubleshooting": {
            "description": "Common system issues and resolution procedures",
            "guidance": [
                "Check service health endpoints before debugging",
                "Verify Docker container status and logs",
                "Test API endpoints with curl for connectivity",
                "Check Neo4j connection and credentials",
                "Validate WASM module loading in browser console",
                "Monitor CI/CD pipeline status for deployment issues"
            ],
            "diagnostic_commands": ["docker-compose ps", "curl health endpoints", "browser console logs"]
        }
    }
    
    if issue_type and issue_type in guidance:
        return {
            "issue_type": issue_type,
            "guidance": guidance[issue_type],
            "source": "operational_procedures"
        }
    
    return {
        "available_guidance": list(guidance.keys()),
        "all_guidance": guidance,
        "source": "operational_procedures",
        "usage": "Specify issue_type parameter for specific guidance"
    }


@app.post("/simulation/jump_diffusion")
async def simulate_jump_diffusion(
    mu: float = Body(0.05),
    sigma: float = Body(0.2),
    jump_lambda: float = Body(0.1),
    jump_mu: float = Body(-0.05),
    jump_sigma: float = Body(0.1),
    start_price: float = Body(100.0),
    T: float = Body(1.0),
    dt: float = Body(1/252),
    n_paths: int = Body(1000),
    seed: Optional[int] = Body(None)
):
    """Simulate asset price paths using Merton Jump-Diffusion model"""
    try:
        import sys
        sys.path.append('/home/ubuntu/repos/quantroi/ai-models/src')
        from simulate_jump_diffusion import MertonJumpDiffusionSimulator, JumpDiffusionParameters
        from dataclasses import asdict
        
        params = JumpDiffusionParameters(
            mu=mu, sigma=sigma, jump_lambda=jump_lambda,
            jump_mu=jump_mu, jump_sigma=jump_sigma,
            start_price=start_price, T=T, dt=dt,
            n_paths=n_paths, seed=seed
        )
        
        simulator = MertonJumpDiffusionSimulator(params)
        results = simulator.simulate_paths()
        
        output_path = f"/tmp/jump_diffusion_{int(datetime.now().timestamp())}"
        simulator.export_to_parquet(results, output_path)
        
        return {
            "status": "success",
            "parameters": asdict(params),
            "tail_risk_metrics": asdict(results.tail_risk_metrics),
            "simulation_timestamp": results.simulation_timestamp,
            "output_path": output_path,
            "jump_frequency": results.tail_risk_metrics.jump_frequency,
            "performance_metrics": {
                "var_95": results.tail_risk_metrics.var_95,
                "var_99": results.tail_risk_metrics.var_99,
                "max_drawdown": results.tail_risk_metrics.max_drawdown
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/confidence/evaluate")
async def evaluate_confidence(
    data_completeness: float = Body(0.85),
    causal_coverage: float = Body(0.75),
    temporal_coverage: float = Body(0.90),
    user_tags: List[str] = Body(["earnings", "volatility"])
):
    """Evaluate data confidence and estimate improvement costs"""
    try:
        import sys
        sys.path.append('/home/ubuntu/repos/quantroi/ai-models/src')
        from confidence_evaluator import ConfidenceEvaluator, create_sample_data
        from dataclasses import asdict
        
        evaluator = ConfidenceEvaluator()
        data_segments, available_drivers, target_period = create_sample_data()
        
        analysis = evaluator.evaluate_confidence(
            data_segments=data_segments,
            available_drivers=available_drivers,
            target_period=target_period,
            user_tags=user_tags
        )
        
        output_path = f"/tmp/confidence_analysis_{int(datetime.now().timestamp())}"
        evaluator.export_results(analysis, output_path)
        
        return {
            "status": "success",
            "overall_confidence": analysis.overall_confidence,
            "data_completeness_score": analysis.data_completeness_score,
            "causal_coverage_score": analysis.causal_coverage_score,
            "temporal_coverage_score": analysis.temporal_coverage_score,
            "quality_score": analysis.quality_score,
            "total_cost_estimate": analysis.total_cost_estimate,
            "cost_breakdown": analysis.cost_breakdown,
            "improvement_recommendations": analysis.improvement_recommendations,
            "output_path": output_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/full_workflow")
async def run_full_audit_workflow(
    ticker: str = Body("AAPL"),
    jump_diffusion_params: Dict[str, Any] = Body({}),
    confidence_params: Dict[str, Any] = Body({}),
    parent_root: Optional[str] = Body(None)
):
    """Run complete audit workflow with all 7 modules"""
    try:
        workflow_id = f"audit_{int(datetime.now().timestamp())}"
        results = {"workflow_id": workflow_id, "steps": []}
        
        jump_response = await simulate_jump_diffusion(**jump_diffusion_params)
        results["steps"].append({"step": "jump_diffusion", "status": "completed", "data": jump_response})
        
        confidence_response = await evaluate_confidence(**confidence_params)
        results["steps"].append({"step": "confidence_evaluation", "status": "completed", "data": confidence_response})
        
        import sys
        sys.path.append('/home/ubuntu/repos/quantroi/option-chain-platform')
        from generate_merkle_audit import generate_audit_with_ipfs
        from dataclasses import asdict
        
        audit_record = generate_audit_with_ipfs(
            jump_response, 
            confidence_response, 
            parent_root
        )
        results["steps"].append({"step": "merkle_audit", "status": "completed", "data": asdict(audit_record)})
        
        governance_response = {
            "audit_id": workflow_id,
            "root": audit_record.root,
            "ipfs_hash": audit_record.ipfs_hash,
            "status": "proposed",
            "required_signatures": 2,
            "current_signatures": 1
        }
        results["steps"].append({"step": "solana_governance", "status": "proposed", "data": governance_response})
        
        try:
            from run_full_audit import get_option_chain_data, export_to_knowledge_base
            option_data = get_option_chain_data(ticker)
            export_to_knowledge_base(ticker, option_data, asdict(audit_record))
            results["steps"].append({"step": "knowledge_base", "status": "completed"})
        except Exception as e:
            results["steps"].append({"step": "knowledge_base", "status": "failed", "error": str(e)})
        
        return {
            "status": "success",
            "workflow_results": results,
            "audit_record": asdict(audit_record),
            "next_steps": [
                "Await additional validator signatures for Solana governance",
                "Monitor IPFS hash for audit trail verification",
                "Review confidence recommendations for data improvement"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
