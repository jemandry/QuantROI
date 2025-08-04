use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};
use sha3::{Digest, Sha3_256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingWealthEngine {
    pub projects: HashMap<String, CausalProject>,
    pub delegations: HashMap<String, ProjectDelegation>,
    pub wealth_milestones: Vec<WealthMilestone>,
    pub audit_trail: Vec<AuditEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CausalProject {
    pub project_id: String,
    pub name: String,
    pub causal_factors: Vec<String>,
    pub schedule: ProjectSchedule,
    pub delegated_tasks: Vec<DelegatedTask>,
    pub wealth_target: u64,
    pub current_progress: f32,
    pub hash_tracking: Vec<u8>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectSchedule {
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
    pub milestones: Vec<ScheduleMilestone>,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduleMilestone {
    pub milestone_id: String,
    pub name: String,
    pub target_date: DateTime<Utc>,
    pub completion_criteria: String,
    pub completed: bool,
    pub completion_date: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DelegatedTask {
    pub task_id: String,
    pub delegated_to: String,
    pub task_type: TaskType,
    pub completion_criteria: String,
    pub reward_amount: u64,
    pub audit_required: bool,
    pub status: TaskStatus,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskType {
    DataCollection,
    CausalAnalysis,
    RiskAssessment,
    ComplianceCheck,
    TradingExecution,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
    AuditRequired,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectDelegation {
    pub delegation_id: String,
    pub project_id: String,
    pub delegated_to: String,
    pub delegation_type: DelegationType,
    pub permissions: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DelegationType {
    FullProject,
    SpecificTasks,
    DataAccess,
    AnalysisOnly,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WealthMilestone {
    pub amount: u64,
    pub achieved: bool,
    pub date: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub entry_id: String,
    pub timestamp: DateTime<Utc>,
    pub action: String,
    pub description: String,
    pub hash: Vec<u8>,
    pub related_project: Option<String>,
}

impl TradingWealthEngine {
    pub fn new() -> Self {
        Self {
            projects: HashMap::new(),
            delegations: HashMap::new(),
            wealth_milestones: vec![
                WealthMilestone { amount: 100_000, achieved: false, date: None },
                WealthMilestone { amount: 500_000, achieved: false, date: None },
                WealthMilestone { amount: 1_000_000, achieved: false, date: None },
                WealthMilestone { amount: 5_000_000, achieved: false, date: None },
            ],
            audit_trail: Vec::new(),
        }
    }
    
    pub async fn create_causal_project(&mut self, name: String, causal_factors: Vec<String>, wealth_target: u64) -> String {
        let project_id = Uuid::new_v4().to_string();
        
        let mut hasher = Sha3_256::new();
        hasher.update(project_id.as_bytes());
        hasher.update(wealth_target.to_le_bytes());
        hasher.update(Utc::now().timestamp().to_le_bytes());
        let hash_tracking = hasher.finalize().to_vec();
        
        let project = CausalProject {
            project_id: project_id.clone(),
            name: name.clone(),
            causal_factors,
            schedule: ProjectSchedule {
                start_date: Utc::now(),
                end_date: Utc::now() + chrono::Duration::days(90),
                milestones: Vec::new(),
                dependencies: Vec::new(),
            },
            delegated_tasks: Vec::new(),
            wealth_target,
            current_progress: 0.0,
            hash_tracking,
        };
        
        self.projects.insert(project_id.clone(), project);
        self.add_audit_entry(format!("Created causal project: {} ({})", name, project_id));
        
        project_id
    }
    
    pub async fn delegate_task(&mut self, project_id: &str, task_type: TaskType, delegated_to: String, reward_amount: u64) -> Result<String, String> {
        if !self.projects.contains_key(project_id) {
            return Err("Project not found".to_string());
        }
        
        let task_id = Uuid::new_v4().to_string();
        let task = DelegatedTask {
            task_id: task_id.clone(),
            delegated_to: delegated_to.clone(),
            task_type,
            completion_criteria: "Task completion criteria to be defined".to_string(),
            reward_amount,
            audit_required: reward_amount > 10000,
            status: TaskStatus::Pending,
            created_at: Utc::now(),
        };
        
        if let Some(project) = self.projects.get_mut(project_id) {
            project.delegated_tasks.push(task);
        }
        
        self.add_audit_entry(format!("Delegated task {} to {} for project {}", task_id, delegated_to, project_id));
        
        Ok(task_id)
    }
    
    pub async fn create_project_delegation(&mut self, project_id: &str, delegated_to: String, delegation_type: DelegationType) -> Result<String, String> {
        if !self.projects.contains_key(project_id) {
            return Err("Project not found".to_string());
        }
        
        let delegation_id = Uuid::new_v4().to_string();
        let delegation = ProjectDelegation {
            delegation_id: delegation_id.clone(),
            project_id: project_id.to_string(),
            delegated_to: delegated_to.clone(),
            delegation_type,
            permissions: vec!["read".to_string(), "execute".to_string()],
            created_at: Utc::now(),
            expires_at: Some(Utc::now() + chrono::Duration::days(30)),
        };
        
        self.delegations.insert(delegation_id.clone(), delegation);
        self.add_audit_entry(format!("Created delegation {} for project {} to {}", delegation_id, project_id, delegated_to));
        
        Ok(delegation_id)
    }
    
    pub async fn update_wealth_milestone(&mut self, amount: u64) -> bool {
        for milestone in &mut self.wealth_milestones {
            if milestone.amount == amount && !milestone.achieved {
                milestone.achieved = true;
                milestone.date = Some(Utc::now());
                self.add_audit_entry(format!("Achieved wealth milestone: ${}", amount));
                return true;
            }
        }
        false
    }
    
    pub fn get_project(&self, project_id: &str) -> Option<&CausalProject> {
        self.projects.get(project_id)
    }
    
    pub fn get_wealth_milestones(&self) -> &Vec<WealthMilestone> {
        &self.wealth_milestones
    }
    
    pub fn get_audit_trail(&self) -> &Vec<AuditEntry> {
        &self.audit_trail
    }
    
    pub fn add_audit_entry(&mut self, description: String) {
        let entry_id = Uuid::new_v4().to_string();
        let timestamp = Utc::now();
        
        let mut hasher = Sha3_256::new();
        hasher.update(entry_id.as_bytes());
        hasher.update(description.as_bytes());
        hasher.update(timestamp.timestamp().to_le_bytes());
        let hash = hasher.finalize().to_vec();
        
        let entry = AuditEntry {
            entry_id,
            timestamp,
            action: "AUDIT".to_string(),
            description,
            hash,
            related_project: None,
        };
        
        self.audit_trail.push(entry);
    }
    
    pub async fn get_project_performance(&self, project_id: &str) -> Result<ProjectPerformance, String> {
        if let Some(project) = self.projects.get(project_id) {
            let completed_tasks = project.delegated_tasks.iter()
                .filter(|task| matches!(task.status, TaskStatus::Completed))
                .count();
            
            let total_tasks = project.delegated_tasks.len();
            let completion_rate = if total_tasks > 0 {
                completed_tasks as f32 / total_tasks as f32
            } else {
                0.0
            };
            
            Ok(ProjectPerformance {
                project_id: project_id.to_string(),
                completion_rate,
                current_progress: project.current_progress,
                wealth_target: project.wealth_target,
                days_remaining: (project.schedule.end_date - Utc::now()).num_days(),
            })
        } else {
            Err("Project not found".to_string())
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectPerformance {
    pub project_id: String,
    pub completion_rate: f32,
    pub current_progress: f32,
    pub wealth_target: u64,
    pub days_remaining: i64,
}

impl Default for TradingWealthEngine {
    fn default() -> Self {
        Self::new()
    }
}
