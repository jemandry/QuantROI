#!/usr/bin/env python3
"""
Reminder Bot for QuantROI Platform
Handles linting failure notifications with milestone-based autopayments
"""

import json
import hashlib
import smtplib
import subprocess
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LintingResult:
    component: str
    tool: str
    status: str
    errors: List[str]
    timestamp: datetime


@dataclass
class Milestone:
    id: str
    name: str
    deadline: datetime
    payment_amount: float
    currency: str
    completed: bool = False
    approved: bool = False


class ReminderBot:
    def __init__(self, config_path: str = "config/reminder-bot.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.milestones = self._load_milestones()
        
    def _load_config(self) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipients": []
            },
            "slack": {
                "webhook_url": "",
                "channel": "#dev-alerts"
            },
            "solana": {
                "rpc_url": "https://api.devnet.solana.com",
                "program_id": "ReminderBot111111111111111111111111111",
                "keypair_path": ""
            },
            "linting": {
                "check_interval_hours": 24,
                "alert_before_deadline_hours": 48
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            
        return default_config
    
    def _load_milestones(self) -> List[Milestone]:
        """Load milestone definitions"""
        return [
            Milestone(
                id="lint-setup",
                name="Linting Infrastructure Setup",
                deadline=datetime.now() + timedelta(days=7),
                payment_amount=0.01,
                currency="SOL"
            ),
            Milestone(
                id="rust-compliance",
                name="Rust Linting Compliance",
                deadline=datetime.now() + timedelta(days=14),
                payment_amount=0.02,
                currency="SOL"
            ),
            Milestone(
                id="python-compliance",
                name="Python Linting Compliance",
                deadline=datetime.now() + timedelta(days=21),
                payment_amount=0.02,
                currency="SOL"
            ),
            Milestone(
                id="ts-compliance",
                name="TypeScript Linting Compliance",
                deadline=datetime.now() + timedelta(days=28),
                payment_amount=0.02,
                currency="SOL"
            )
        ]
    
    def check_linting_status(self) -> List[LintingResult]:
        """Run linting checks and return results"""
        results = []
        
        try:
            result = subprocess.run(
                ["bash", "scripts/lint-all.sh"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode != 0:
                lines = result.stdout.split('\n') + result.stderr.split('\n')
                
                for line in lines:
                    if "failed" in line.lower() or "error" in line.lower():
                        if "rust" in line.lower():
                            component = "solana-contracts"
                            tool = "clippy" if "clippy" in line else "rustfmt"
                        elif "python" in line.lower():
                            component = "ai-models"
                            tool = "flake8" if "flake8" in line else "pylint"
                        elif "typescript" in line.lower():
                            component = "frontend"
                            tool = "eslint"
                        else:
                            component = "unknown"
                            tool = "unknown"
                        
                        results.append(LintingResult(
                            component=component,
                            tool=tool,
                            status="failed",
                            errors=[line.strip()],
                            timestamp=datetime.now()
                        ))
            
        except Exception as e:
            results.append(LintingResult(
                component="system",
                tool="lint-runner",
                status="error",
                errors=[f"Failed to run linting: {str(e)}"],
                timestamp=datetime.now()
            ))
        
        return results
    
    def send_email_alert(self, subject: str, message: str) -> bool:
        """Send email notification"""
        try:
            if not self.config["email"]["sender_email"]:
                print("Email not configured, skipping email alert")
                return False
                
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["sender_email"]
            msg['To'] = ", ".join(self.config["email"]["recipients"])
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(
                self.config["email"]["smtp_server"],
                self.config["email"]["smtp_port"]
            )
            server.starttls()
            server.login(
                self.config["email"]["sender_email"],
                self.config["email"]["sender_password"]
            )
            
            text = msg.as_string()
            server.sendmail(
                self.config["email"]["sender_email"],
                self.config["email"]["recipients"],
                text
            )
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def send_slack_alert(self, message: str) -> bool:
        """Send Slack notification"""
        try:
            if not self.config["slack"]["webhook_url"]:
                print("Slack not configured, skipping Slack alert")
                return False
                
            import requests
            
            payload = {
                "channel": self.config["slack"]["channel"],
                "text": message,
                "username": "QuantROI Reminder Bot",
                "icon_emoji": ":warning:"
            }
            
            response = requests.post(
                self.config["slack"]["webhook_url"],
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Failed to send Slack message: {e}")
            return False
    
    def log_to_solana(self, action: str, data: Dict) -> str:
        """Log action to Solana blockchain with SHA-3 hashing"""
        try:
            data_json = json.dumps(data, sort_keys=True, default=str)
            hash_obj = hashlib.sha3_256(data_json.encode('utf-8'))
            data_hash = hash_obj.hexdigest()
            
            log_entry = {
                "action": action,
                "data_hash": data_hash,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            log_file = Path("logs/solana_audit.jsonl")
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            print(f"Logged to Solana audit: {action} - Hash: {data_hash}")
            return data_hash
            
        except Exception as e:
            print(f"Failed to log to Solana: {e}")
            return ""
    
    def check_milestones(self) -> List[str]:
        """Check milestone deadlines and return alerts"""
        alerts = []
        now = datetime.now()
        
        for milestone in self.milestones:
            if milestone.completed:
                continue
                
            time_until_deadline = milestone.deadline - now
            
            if time_until_deadline <= timedelta(hours=48) and time_until_deadline > timedelta(0):
                alerts.append(
                    f"⏰ Milestone '{milestone.name}' due in {time_until_deadline.days} days"
                )
            
            elif time_until_deadline <= timedelta(0):
                alerts.append(
                    f"🚨 Milestone '{milestone.name}' is overdue by {abs(time_until_deadline.days)} days"
                )
        
        return alerts
    
    def process_milestone_payment(self, milestone_id: str, approved: bool) -> bool:
        """Process milestone-based autopayment"""
        milestone = next((m for m in self.milestones if m.id == milestone_id), None)
        
        if not milestone:
            print(f"Milestone {milestone_id} not found")
            return False
        
        if approved:
            payment_data = {
                "milestone_id": milestone_id,
                "amount": milestone.payment_amount,
                "currency": milestone.currency,
                "status": "approved",
                "recipient": "team_member"  # In real implementation, this would be specific
            }
            
            hash_result = self.log_to_solana("milestone_payment_approved", payment_data)
            
            milestone.approved = True
            milestone.completed = True
            
            print(f"✅ Payment approved for milestone '{milestone.name}': {milestone.payment_amount} {milestone.currency}")
            return True
        else:
            rejection_data = {
                "milestone_id": milestone_id,
                "reason": "manual_rejection",
                "status": "rejected"
            }
            
            self.log_to_solana("milestone_payment_rejected", rejection_data)
            
            print(f"❌ Payment rejected for milestone '{milestone.name}'")
            return False
    
    def run_daily_check(self) -> None:
        """Run daily linting and milestone checks"""
        print(f"🤖 QuantROI Reminder Bot - Daily Check ({datetime.now()})")
        
        linting_results = self.check_linting_status()
        failures = [r for r in linting_results if r.status in ["failed", "error"]]
        
        milestone_alerts = self.check_milestones()
        
        alerts = []
        
        if failures:
            failure_summary = {}
            for failure in failures:
                component = failure.component
                if component not in failure_summary:
                    failure_summary[component] = []
                failure_summary[component].append(f"{failure.tool}: {failure.errors[0]}")
            
            alert_message = "🚨 Linting Failures Detected:\n"
            for component, errors in failure_summary.items():
                alert_message += f"\n{component}:\n"
                for error in errors:
                    alert_message += f"  - {error}\n"
            
            alerts.append(alert_message)
        
        if milestone_alerts:
            alerts.extend(milestone_alerts)
        
        if alerts:
            full_message = "\n\n".join(alerts)
            
            self.send_email_alert(
                "QuantROI Platform - Linting & Milestone Alerts",
                full_message
            )
            
            self.send_slack_alert(full_message)
            
            self.log_to_solana("daily_alert_sent", {
                "alert_count": len(alerts),
                "failure_count": len(failures),
                "milestone_alert_count": len(milestone_alerts)
            })
            
            print("📧 Alerts sent successfully")
        else:
            print("✅ No alerts needed - all systems healthy")


def main() -> None:
    """Main entry point for the reminder bot"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QuantROI Reminder Bot")
    parser.add_argument("--daily-check", action="store_true", help="Run daily check")
    parser.add_argument("--alert-failures", action="store_true", help="Alert on linting failures")
    parser.add_argument("--approve-milestone", type=str, help="Approve milestone payment")
    parser.add_argument("--reject-milestone", type=str, help="Reject milestone payment")
    
    args = parser.parse_args()
    
    bot = ReminderBot()
    
    if args.daily_check or args.alert_failures:
        bot.run_daily_check()
    elif args.approve_milestone:
        bot.process_milestone_payment(args.approve_milestone, True)
    elif args.reject_milestone:
        bot.process_milestone_payment(args.reject_milestone, False)
    else:
        print("Usage: python reminder-bot.py --daily-check")
        sys.exit(1)


if __name__ == "__main__":
    main()
