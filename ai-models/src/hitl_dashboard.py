from flask import Flask, jsonify, request, render_template_string
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import time
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)

class HITLDashboard:
    """
    Human-in-the-Loop dashboard for AI decision oversight and intuition integration
    """
    
    def __init__(self):
        self.ai_decisions = []
        self.human_overrides = []
        self.causal_graphs = []
        self.mbd_reconstructions = []
        self.confidence_threshold = 0.7
        
    def log_ai_decision(self, decision_type: str, decision_data: Dict[str, Any], 
                       confidence: float) -> str:
        """Log AI decision for human review"""
        decision_id = hashlib.md5(
            f"{decision_type}_{time.time()}".encode()
        ).hexdigest()[:8]
        
        decision_entry = {
            'id': decision_id,
            'timestamp': datetime.now().isoformat(),
            'type': decision_type,
            'data': decision_data,
            'confidence': confidence,
            'flagged_for_review': confidence < self.confidence_threshold,
            'human_reviewed': False,
            'override_applied': False
        }
        
        self.ai_decisions.append(decision_entry)
        
        if len(self.ai_decisions) > 1000:
            self.ai_decisions = self.ai_decisions[-1000:]
        
        return decision_id
    
    def apply_human_override(self, decision_id: str, override_data: Dict[str, Any],
                           user_id: str, reasoning: str) -> Dict[str, Any]:
        """Apply human override to AI decision"""
        decision = None
        for d in self.ai_decisions:
            if d['id'] == decision_id:
                decision = d
                break
        
        if not decision:
            return {'error': 'Decision not found', 'decision_id': decision_id}
        
        override_entry = {
            'id': hashlib.md5(f"{decision_id}_{time.time()}".encode()).hexdigest()[:8],
            'decision_id': decision_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'reasoning': reasoning,
            'original_data': decision['data'].copy(),
            'override_data': override_data,
            'audit_trail': True
        }
        
        self.human_overrides.append(override_entry)
        
        decision['human_reviewed'] = True
        decision['override_applied'] = True
        decision['override_id'] = override_entry['id']
        
        blended_result = self._blend_ai_human_decisions(
            decision['data'], override_data, ai_weight=0.7
        )
        
        return {
            'status': 'override_applied',
            'decision_id': decision_id,
            'override_id': override_entry['id'],
            'blended_result': blended_result,
            'audit_logged': True
        }
    
    def _blend_ai_human_decisions(self, ai_data: Dict[str, Any], 
                                human_data: Dict[str, Any],
                                ai_weight: float = 0.7) -> Dict[str, Any]:
        """Blend AI and human decisions using weighted averaging"""
        blended = {}
        human_weight = 1.0 - ai_weight
        
        for key in ai_data:
            if key in human_data:
                ai_val = ai_data[key]
                human_val = human_data[key]
                
                if isinstance(ai_val, (int, float)) and isinstance(human_val, (int, float)):
                    blended[key] = ai_weight * ai_val + human_weight * human_val
                elif isinstance(ai_val, str) and isinstance(human_val, str):
                    blended[key] = human_val if human_val else ai_val
                else:
                    blended[key] = human_val
            else:
                blended[key] = ai_data[key]
        
        for key in human_data:
            if key not in blended:
                blended[key] = human_data[key]
        
        blended['_blend_metadata'] = {
            'ai_weight': ai_weight,
            'human_weight': human_weight,
            'blend_timestamp': datetime.now().isoformat()
        }
        
        return blended
    
    def get_flagged_decisions(self) -> List[Dict[str, Any]]:
        """Get decisions flagged for human review"""
        return [
            d for d in self.ai_decisions 
            if d['flagged_for_review'] and not d['human_reviewed']
        ]
    
    def generate_audit_trail(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate audit trail for compliance"""
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        period_decisions = [
            d for d in self.ai_decisions
            if start_dt <= datetime.fromisoformat(d['timestamp']) <= end_dt
        ]
        
        period_overrides = [
            o for o in self.human_overrides
            if start_dt <= datetime.fromisoformat(o['timestamp']) <= end_dt
        ]
        
        total_decisions = len(period_decisions)
        flagged_decisions = len([d for d in period_decisions if d['flagged_for_review']])
        reviewed_decisions = len([d for d in period_decisions if d['human_reviewed']])
        override_rate = len(period_overrides) / total_decisions if total_decisions > 0 else 0
        
        return {
            'audit_period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'statistics': {
                'total_decisions': total_decisions,
                'flagged_for_review': flagged_decisions,
                'human_reviewed': reviewed_decisions,
                'overrides_applied': len(period_overrides),
                'override_rate': override_rate,
                'review_rate': reviewed_decisions / flagged_decisions if flagged_decisions > 0 else 0
            },
            'decisions': period_decisions,
            'overrides': period_overrides,
            'compliance_status': 'COMPLIANT' if override_rate < 0.1 else 'REVIEW_NEEDED',
            'audit_hash': hashlib.sha256(
                json.dumps(period_decisions + period_overrides, sort_keys=True).encode()
            ).hexdigest()
        }

dashboard = HITLDashboard()

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>HITL Trading System Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .flagged { background-color: #ffebee; border-left: 4px solid #f44336; padding: 10px; margin: 10px 0; }
        .reviewed { background-color: #e8f5e8; border-left: 4px solid #4caf50; padding: 10px; margin: 10px 0; }
        .confidence-low { color: #f44336; font-weight: bold; }
        .confidence-high { color: #4caf50; font-weight: bold; }
        button { background-color: #2196f3; color: white; padding: 8px 16px; border: none; cursor: pointer; margin: 5px; }
        button:hover { background-color: #1976d2; }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0; }
        .override-form { background-color: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Human-in-the-Loop Trading System Dashboard</h1>
    
    <h2>Flagged AI Decisions (Confidence < 0.7)</h2>
    <div id="flagged-decisions">
        <!-- Flagged decisions will be loaded here -->
    </div>
    
    <h2>Recent AI Decisions</h2>
    <div id="recent-decisions">
        <!-- Recent decisions will be loaded here -->
    </div>
    
    <script>
        function loadFlaggedDecisions() {
            fetch('/api/flagged-decisions')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('flagged-decisions');
                    container.innerHTML = '';
                    
                    data.forEach(decision => {
                        const div = document.createElement('div');
                        div.className = 'flagged';
                        div.innerHTML = `
                            <h3>Decision ID: ${decision.id}</h3>
                            <p><strong>Type:</strong> ${decision.type}</p>
                            <p><strong>Confidence:</strong> <span class="confidence-low">${decision.confidence}</span></p>
                            <p><strong>Timestamp:</strong> ${decision.timestamp}</p>
                            <details>
                                <summary>Decision Data</summary>
                                <pre>${JSON.stringify(decision.data, null, 2)}</pre>
                            </details>
                            <div class="override-form">
                                <h4>Apply Override (70% AI + 30% Human Blend)</h4>
                                <input type="text" id="user-${decision.id}" placeholder="User ID" />
                                <textarea id="reasoning-${decision.id}" placeholder="Reasoning for override (e.g., market sentiment, intuition)"></textarea>
                                <textarea id="override-${decision.id}" placeholder="Override data (JSON format)"></textarea>
                                <input type="text" id="sentiment-${decision.id}" placeholder="Market sentiment override (e.g., bullish, bearish)" />
                                <button onclick="applyOverride('${decision.id}')">Apply Override</button>
                            </div>
                        `;
                        container.appendChild(div);
                    });
                });
        }
        
        function applyOverride(decisionId) {
            const userId = document.getElementById(`user-${decisionId}`).value;
            const reasoning = document.getElementById(`reasoning-${decisionId}`).value;
            const overrideData = document.getElementById(`override-${decisionId}`).value;
            const sentiment = document.getElementById(`sentiment-${decisionId}`).value;
            
            try {
                let parsedOverride = {};
                if (overrideData) {
                    parsedOverride = JSON.parse(overrideData);
                }
                
                if (sentiment) {
                    parsedOverride.market_sentiment_override = sentiment;
                }
                
                fetch('/api/apply-override', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        decision_id: decisionId,
                        user_id: userId,
                        reasoning: reasoning,
                        override_data: parsedOverride
                    })
                })
                .then(response => response.json())
                .then(data => {
                    alert(`Override applied successfully! Blended at 70% AI + 30% Human`);
                    loadFlaggedDecisions();
                });
            } catch (e) {
                alert('Invalid JSON in override data');
            }
        }
        
        // Load data on page load
        loadFlaggedDecisions();
        
        // Refresh every 30 seconds
        setInterval(loadFlaggedDecisions, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard_home():
    """Serve the main dashboard"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/flagged-decisions')
def get_flagged_decisions():
    """API endpoint to get flagged decisions"""
    flagged = dashboard.get_flagged_decisions()
    return jsonify(flagged)

@app.route('/api/apply-override', methods=['POST'])
def apply_override():
    """API endpoint to apply human override"""
    data = request.json
    
    result = dashboard.apply_human_override(
        decision_id=data['decision_id'],
        override_data=data['override_data'],
        user_id=data['user_id'],
        reasoning=data['reasoning']
    )
    
    return jsonify(result)

@app.route('/api/log-decision', methods=['POST'])
def log_ai_decision():
    """API endpoint for AI systems to log decisions"""
    data = request.json
    
    decision_id = dashboard.log_ai_decision(
        decision_type=data['type'],
        decision_data=data['data'],
        confidence=data['confidence']
    )
    
    return jsonify({'decision_id': decision_id, 'status': 'logged'})

@app.route('/api/audit-trail')
def get_audit_trail():
    """API endpoint to get audit trail"""
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', datetime.now().isoformat())
    
    audit_trail = dashboard.generate_audit_trail(start_date, end_date)
    return jsonify(audit_trail)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
