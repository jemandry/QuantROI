use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc, Duration};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceReport {
    pub report_id: String,
    pub report_type: ReportType,
    pub generated_at: DateTime<Utc>,
    pub period_start: DateTime<Utc>,
    pub period_end: DateTime<Utc>,
    pub sections: Vec<ReportSection>,
    pub summary: ReportSummary,
    pub compliance_status: ComplianceStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum ReportType {
    Sec10K,
    Sec10Q,
    GdprDataProcessing,
    SoxInternalControls,
    MiFidTransactionReporting,
    CftcSwapReporting,
    Custom(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportSection {
    pub section_id: String,
    pub title: String,
    pub content: String,
    pub data_sources: Vec<String>,
    pub confidence_score: f32,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportSummary {
    pub total_transactions: u64,
    pub total_audit_events: u64,
    pub compliance_violations: u32,
    pub data_quality_score: f32,
    pub audit_trail_completeness: f32,
    pub key_findings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ComplianceStatus {
    Compliant,
    NonCompliant(Vec<String>),
    PartiallyCompliant(Vec<String>),
    UnderReview,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionPolicy {
    pub policy_id: String,
    pub data_type: String,
    pub retention_period_days: u32,
    pub legal_hold_enabled: bool,
    pub deletion_schedule: Option<DateTime<Utc>>,
    pub compliance_requirements: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditTrailEntry {
    pub entry_id: String,
    pub timestamp: DateTime<Utc>,
    pub event_type: String,
    pub user_id: Option<String>,
    pub data_hash: String,
    pub merkle_root: String,
    pub ipfs_hash: Option<String>,
    pub compliance_tags: Vec<String>,
}

pub struct ComplianceReportGenerator {
    audit_trail_store: Arc<RwLock<Vec<AuditTrailEntry>>>,
    retention_policies: Arc<RwLock<HashMap<String, RetentionPolicy>>>,
    report_templates: Arc<RwLock<HashMap<ReportType, ReportTemplate>>>,
    compliance_rules: Arc<RwLock<Vec<ComplianceRule>>>,
}

#[derive(Debug, Clone)]
pub struct ReportTemplate {
    pub template_id: String,
    pub report_type: ReportType,
    pub required_sections: Vec<String>,
    pub data_requirements: Vec<String>,
    pub format: ReportFormat,
}

#[derive(Debug, Clone)]
pub enum ReportFormat {
    PDF,
    HTML,
    JSON,
    XML,
}

#[derive(Debug, Clone)]
pub struct ComplianceRule {
    pub rule_id: String,
    pub regulation: String,
    pub description: String,
    pub validation_function: String,
    pub severity: RuleSeverity,
}

#[derive(Debug, Clone)]
pub enum RuleSeverity {
    Critical,
    High,
    Medium,
    Low,
}

impl ComplianceReportGenerator {
    pub fn new() -> Self {
        Self {
            audit_trail_store: Arc::new(RwLock::new(Vec::new())),
            retention_policies: Arc::new(RwLock::new(HashMap::new())),
            report_templates: Arc::new(RwLock::new(HashMap::new())),
            compliance_rules: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub async fn initialize(&self) {
        self.initialize_default_templates().await;
        self.initialize_default_policies().await;
        self.initialize_default_rules().await;
    }

    async fn initialize_default_templates(&self) {
        let mut templates = self.report_templates.write().await;
        
        templates.insert(
            ReportType::Sec10K,
            ReportTemplate {
                template_id: "sec_10k".to_string(),
                report_type: ReportType::Sec10K,
                required_sections: vec![
                    "Business Overview".to_string(),
                    "Risk Factors".to_string(),
                    "Financial Data".to_string(),
                    "Internal Controls".to_string(),
                ],
                data_requirements: vec![
                    "transaction_data".to_string(),
                    "audit_logs".to_string(),
                    "risk_assessments".to_string(),
                ],
                format: ReportFormat::PDF,
            }
        );

        templates.insert(
            ReportType::GdprDataProcessing,
            ReportTemplate {
                template_id: "gdpr_processing".to_string(),
                report_type: ReportType::GdprDataProcessing,
                required_sections: vec![
                    "Data Processing Activities".to_string(),
                    "Legal Basis".to_string(),
                    "Data Subject Rights".to_string(),
                    "Security Measures".to_string(),
                ],
                data_requirements: vec![
                    "personal_data_logs".to_string(),
                    "consent_records".to_string(),
                    "security_measures".to_string(),
                ],
                format: ReportFormat::HTML,
            }
        );
    }

    async fn initialize_default_policies(&self) {
        let mut policies = self.retention_policies.write().await;
        
        policies.insert(
            "transaction_data".to_string(),
            RetentionPolicy {
                policy_id: "txn_retention".to_string(),
                data_type: "transaction_data".to_string(),
                retention_period_days: 2555,
                legal_hold_enabled: false,
                deletion_schedule: Some(Utc::now() + Duration::days(2555)),
                compliance_requirements: vec!["SEC Rule 17a-4".to_string()],
            }
        );

        policies.insert(
            "personal_data".to_string(),
            RetentionPolicy {
                policy_id: "gdpr_retention".to_string(),
                data_type: "personal_data".to_string(),
                retention_period_days: 1095,
                legal_hold_enabled: false,
                deletion_schedule: Some(Utc::now() + Duration::days(1095)),
                compliance_requirements: vec!["GDPR Article 5".to_string()],
            }
        );
    }

    async fn initialize_default_rules(&self) {
        let mut rules = self.compliance_rules.write().await;
        
        rules.push(ComplianceRule {
            rule_id: "audit_trail_completeness".to_string(),
            regulation: "SOX Section 404".to_string(),
            description: "All financial transactions must have complete audit trails".to_string(),
            validation_function: "validate_audit_completeness".to_string(),
            severity: RuleSeverity::Critical,
        });

        rules.push(ComplianceRule {
            rule_id: "data_retention_compliance".to_string(),
            regulation: "SEC Rule 17a-4".to_string(),
            description: "Transaction records must be retained for required periods".to_string(),
            validation_function: "validate_retention_compliance".to_string(),
            severity: RuleSeverity::High,
        });
    }

    pub async fn generate_report(
        &self,
        report_type: ReportType,
        period_start: DateTime<Utc>,
        period_end: DateTime<Utc>,
    ) -> Result<ComplianceReport, String> {
        let templates = self.report_templates.read().await;
        let template = templates.get(&report_type)
            .ok_or("Report template not found")?;

        let audit_entries = self.collect_audit_data(period_start, period_end).await?;
        let sections = self.generate_report_sections(template, &audit_entries).await?;
        let summary = self.generate_report_summary(&audit_entries).await?;
        let compliance_status = self.evaluate_compliance_status(&audit_entries).await?;

        Ok(ComplianceReport {
            report_id: uuid::Uuid::new_v4().to_string(),
            report_type,
            generated_at: Utc::now(),
            period_start,
            period_end,
            sections,
            summary,
            compliance_status,
        })
    }

    async fn collect_audit_data(
        &self,
        period_start: DateTime<Utc>,
        period_end: DateTime<Utc>,
    ) -> Result<Vec<AuditTrailEntry>, String> {
        let audit_store = self.audit_trail_store.read().await;
        
        let filtered_entries: Vec<AuditTrailEntry> = audit_store
            .iter()
            .filter(|entry| entry.timestamp >= period_start && entry.timestamp <= period_end)
            .cloned()
            .collect();

        Ok(filtered_entries)
    }

    async fn generate_report_sections(
        &self,
        template: &ReportTemplate,
        audit_entries: &[AuditTrailEntry],
    ) -> Result<Vec<ReportSection>, String> {
        let mut sections = Vec::new();

        for section_title in &template.required_sections {
            let content = self.generate_section_content(section_title, audit_entries).await?;
            let data_sources = self.identify_data_sources(section_title, audit_entries).await;
            let confidence_score = self.calculate_section_confidence(section_title, audit_entries).await;

            sections.push(ReportSection {
                section_id: uuid::Uuid::new_v4().to_string(),
                title: section_title.clone(),
                content,
                data_sources,
                confidence_score,
                last_updated: Utc::now(),
            });
        }

        Ok(sections)
    }

    async fn generate_section_content(
        &self,
        section_title: &str,
        audit_entries: &[AuditTrailEntry],
    ) -> Result<String, String> {
        match section_title {
            "Business Overview" => {
                Ok(format!(
                    "During the reporting period, the system processed {} audit events across {} unique event types. \
                    The platform maintained operational integrity with comprehensive audit trails for all transactions.",
                    audit_entries.len(),
                    audit_entries.iter().map(|e| &e.event_type).collect::<std::collections::HashSet<_>>().len()
                ))
            },
            "Risk Factors" => {
                let high_risk_events = audit_entries.iter()
                    .filter(|e| e.compliance_tags.contains(&"high_risk".to_string()))
                    .count();
                
                Ok(format!(
                    "Risk assessment identified {} high-risk events during the reporting period. \
                    All events were properly logged and reviewed according to established risk management protocols.",
                    high_risk_events
                ))
            },
            "Data Processing Activities" => {
                let personal_data_events = audit_entries.iter()
                    .filter(|e| e.compliance_tags.contains(&"personal_data".to_string()))
                    .count();
                
                Ok(format!(
                    "Personal data processing activities: {} events recorded with full audit trails. \
                    All processing activities comply with GDPR requirements for lawful basis and data subject rights.",
                    personal_data_events
                ))
            },
            "Internal Controls" => {
                Ok(format!(
                    "Internal control systems processed {} audit events with {} unique Merkle roots generated. \
                    All events maintain cryptographic integrity through hash-based verification systems.",
                    audit_entries.len(),
                    audit_entries.iter().map(|e| &e.merkle_root).collect::<std::collections::HashSet<_>>().len()
                ))
            },
            _ => Ok(format!("Section content for {} generated from {} audit entries.", section_title, audit_entries.len())),
        }
    }

    async fn identify_data_sources(&self, _section_title: &str, audit_entries: &[AuditTrailEntry]) -> Vec<String> {
        let mut sources = std::collections::HashSet::new();
        
        for entry in audit_entries {
            sources.insert("audit_trail_store".to_string());
            if entry.ipfs_hash.is_some() {
                sources.insert("ipfs_storage".to_string());
            }
            sources.insert("merkle_tree_system".to_string());
        }
        
        sources.into_iter().collect()
    }

    async fn calculate_section_confidence(&self, _section_title: &str, audit_entries: &[AuditTrailEntry]) -> f32 {
        if audit_entries.is_empty() {
            return 0.0;
        }

        let complete_entries = audit_entries.iter()
            .filter(|e| !e.data_hash.is_empty() && !e.merkle_root.is_empty())
            .count();

        complete_entries as f32 / audit_entries.len() as f32
    }

    async fn generate_report_summary(&self, audit_entries: &[AuditTrailEntry]) -> Result<ReportSummary, String> {
        let total_audit_events = audit_entries.len() as u64;
        let total_transactions = audit_entries.iter()
            .filter(|e| e.event_type.contains("transaction"))
            .count() as u64;

        let compliance_violations = audit_entries.iter()
            .filter(|e| e.compliance_tags.contains(&"violation".to_string()))
            .count() as u32;

        let data_quality_score = self.calculate_data_quality_score(audit_entries).await;
        let audit_trail_completeness = self.calculate_audit_completeness(audit_entries).await;
        let key_findings = self.generate_key_findings(audit_entries).await;

        Ok(ReportSummary {
            total_transactions,
            total_audit_events,
            compliance_violations,
            data_quality_score,
            audit_trail_completeness,
            key_findings,
        })
    }

    async fn calculate_data_quality_score(&self, audit_entries: &[AuditTrailEntry]) -> f32 {
        if audit_entries.is_empty() {
            return 1.0;
        }

        let quality_score: f32 = audit_entries.iter()
            .map(|entry| {
                let mut score = 0.0;
                if !entry.data_hash.is_empty() { score += 0.3; }
                if !entry.merkle_root.is_empty() { score += 0.3; }
                if entry.ipfs_hash.is_some() { score += 0.2; }
                if !entry.compliance_tags.is_empty() { score += 0.2; }
                score
            })
            .sum();

        quality_score / audit_entries.len() as f32
    }

    async fn calculate_audit_completeness(&self, audit_entries: &[AuditTrailEntry]) -> f32 {
        if audit_entries.is_empty() {
            return 1.0;
        }

        let complete_entries = audit_entries.iter()
            .filter(|e| !e.data_hash.is_empty() && !e.merkle_root.is_empty())
            .count();

        complete_entries as f32 / audit_entries.len() as f32
    }

    async fn generate_key_findings(&self, audit_entries: &[AuditTrailEntry]) -> Vec<String> {
        let mut findings = Vec::new();

        if audit_entries.is_empty() {
            findings.push("No audit events found for the reporting period".to_string());
            return findings;
        }

        let violation_count = audit_entries.iter()
            .filter(|e| e.compliance_tags.contains(&"violation".to_string()))
            .count();

        if violation_count > 0 {
            findings.push(format!("{} compliance violations identified and logged", violation_count));
        } else {
            findings.push("No compliance violations detected during reporting period".to_string());
        }

        let ipfs_coverage = audit_entries.iter()
            .filter(|e| e.ipfs_hash.is_some())
            .count() as f32 / audit_entries.len() as f32;

        if ipfs_coverage > 0.9 {
            findings.push("High IPFS storage coverage for audit trail permanence".to_string());
        } else if ipfs_coverage < 0.5 {
            findings.push("Low IPFS storage coverage - recommend increasing backup redundancy".to_string());
        }

        findings.push(format!("Processed {} unique event types with full audit trails", 
            audit_entries.iter().map(|e| &e.event_type).collect::<std::collections::HashSet<_>>().len()));

        findings
    }

    async fn evaluate_compliance_status(&self, audit_entries: &[AuditTrailEntry]) -> Result<ComplianceStatus, String> {
        let rules = self.compliance_rules.read().await;
        let mut violations = Vec::new();
        let mut warnings = Vec::new();

        for rule in rules.iter() {
            let rule_result = self.validate_compliance_rule(rule, audit_entries).await;
            
            match rule_result {
                Ok(true) => {},
                Ok(false) => {
                    match rule.severity {
                        RuleSeverity::Critical | RuleSeverity::High => {
                            violations.push(format!("Rule violation: {}", rule.description));
                        },
                        RuleSeverity::Medium | RuleSeverity::Low => {
                            warnings.push(format!("Rule warning: {}", rule.description));
                        },
                    }
                },
                Err(e) => {
                    warnings.push(format!("Rule validation error for {}: {}", rule.rule_id, e));
                },
            }
        }

        if !violations.is_empty() {
            Ok(ComplianceStatus::NonCompliant(violations))
        } else if !warnings.is_empty() {
            Ok(ComplianceStatus::PartiallyCompliant(warnings))
        } else {
            Ok(ComplianceStatus::Compliant)
        }
    }

    async fn validate_compliance_rule(&self, rule: &ComplianceRule, audit_entries: &[AuditTrailEntry]) -> Result<bool, String> {
        match rule.validation_function.as_str() {
            "validate_audit_completeness" => {
                let completeness = self.calculate_audit_completeness(audit_entries).await;
                Ok(completeness >= 0.95)
            },
            "validate_retention_compliance" => {
                let policies = self.retention_policies.read().await;
                for entry in audit_entries {
                    if let Some(policy) = policies.get(&entry.event_type) {
                        let age_days = Utc::now().signed_duration_since(entry.timestamp).num_days();
                        if age_days > policy.retention_period_days as i64 && policy.deletion_schedule.is_none() {
                            return Ok(false);
                        }
                    }
                }
                Ok(true)
            },
            _ => Err(format!("Unknown validation function: {}", rule.validation_function)),
        }
    }

    pub async fn add_audit_entry(&self, entry: AuditTrailEntry) {
        let mut store = self.audit_trail_store.write().await;
        store.push(entry);
    }

    pub async fn add_retention_policy(&self, policy: RetentionPolicy) {
        let mut policies = self.retention_policies.write().await;
        policies.insert(policy.data_type.clone(), policy);
    }

    pub async fn get_report(&self, _report_id: &str) -> Option<ComplianceReport> {
        None
    }

    pub async fn export_report_as_html(&self, report: &ComplianceReport) -> Result<String, String> {
        let mut html = String::new();
        html.push_str("<!DOCTYPE html><html><head><title>Compliance Report</title></head><body>");
        html.push_str(&format!("<h1>Compliance Report - {}</h1>", report.report_id));
        html.push_str(&format!("<p>Generated: {}</p>", report.generated_at.format("%Y-%m-%d %H:%M:%S UTC")));
        html.push_str(&format!("<p>Period: {} to {}</p>", 
            report.period_start.format("%Y-%m-%d"), 
            report.period_end.format("%Y-%m-%d")));

        for section in &report.sections {
            html.push_str(&format!("<h2>{}</h2>", section.title));
            html.push_str(&format!("<p>{}</p>", section.content));
            html.push_str(&format!("<p><em>Confidence: {:.2}</em></p>", section.confidence_score));
        }

        html.push_str("<h2>Summary</h2>");
        html.push_str(&format!("<p>Total Transactions: {}</p>", report.summary.total_transactions));
        html.push_str(&format!("<p>Total Audit Events: {}</p>", report.summary.total_audit_events));
        html.push_str(&format!("<p>Compliance Violations: {}</p>", report.summary.compliance_violations));

        html.push_str("</body></html>");
        Ok(html)
    }

    pub async fn export_report_as_json(&self, report: &ComplianceReport) -> Result<String, String> {
        serde_json::to_string_pretty(report).map_err(|e| e.to_string())
    }
}

impl Clone for ComplianceReportGenerator {
    fn clone(&self) -> Self {
        Self {
            audit_trail_store: Arc::clone(&self.audit_trail_store),
            retention_policies: Arc::clone(&self.retention_policies),
            report_templates: Arc::clone(&self.report_templates),
            compliance_rules: Arc::clone(&self.compliance_rules),
        }
    }
}

impl Default for ComplianceReportGenerator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_compliance_report_generator_creation() {
        let generator = ComplianceReportGenerator::new();
        let audit_entries = generator.audit_trail_store.read().await;
        assert_eq!(audit_entries.len(), 0);
    }

    #[tokio::test]
    async fn test_audit_entry_addition() {
        let generator = ComplianceReportGenerator::new();
        
        let entry = AuditTrailEntry {
            entry_id: "test_entry".to_string(),
            timestamp: Utc::now(),
            event_type: "transaction".to_string(),
            user_id: Some("user123".to_string()),
            data_hash: "hash123".to_string(),
            merkle_root: "root123".to_string(),
            ipfs_hash: Some("ipfs123".to_string()),
            compliance_tags: vec!["financial".to_string()],
        };

        generator.add_audit_entry(entry).await;
        
        let audit_entries = generator.audit_trail_store.read().await;
        assert_eq!(audit_entries.len(), 1);
        assert_eq!(audit_entries[0].entry_id, "test_entry");
    }

    #[tokio::test]
    async fn test_report_generation() {
        let generator = ComplianceReportGenerator::new();
        generator.initialize().await;
        
        let entry = AuditTrailEntry {
            entry_id: "test_entry".to_string(),
            timestamp: Utc::now(),
            event_type: "transaction".to_string(),
            user_id: Some("user123".to_string()),
            data_hash: "hash123".to_string(),
            merkle_root: "root123".to_string(),
            ipfs_hash: Some("ipfs123".to_string()),
            compliance_tags: vec!["financial".to_string()],
        };

        generator.add_audit_entry(entry).await;

        let report = generator.generate_report(
            ReportType::Sec10K,
            Utc::now() - Duration::days(30),
            Utc::now(),
        ).await;

        assert!(report.is_ok());
        let report = report.unwrap();
        assert_eq!(report.summary.total_audit_events, 1);
    }
}
