use anchor_lang::prelude::*;
use sha3::{Digest, Sha3_256};

declare_id!("KnowledgeVerificationProgram1111111111111");

#[program]
pub mod knowledge_verification {
    use super::*;

    pub fn create_knowledge_test(
        ctx: Context<CreateKnowledgeTest>,
        test_id: u64,
        question_hashes: Vec<[u8; 32]>,
        passing_score: u8,
        time_limit: u32,
    ) -> Result<()> {
        let test = &mut ctx.accounts.knowledge_test;
        let clock = Clock::get()?;
        
        require!(passing_score <= 100, KnowledgeError::InvalidPassingScore);
        require!(question_hashes.len() <= 50, KnowledgeError::TooManyQuestions);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&test_id.to_le_bytes());
        hasher.update(ctx.accounts.test_creator.key().as_ref());
        for hash in &question_hashes {
            hasher.update(hash);
        }
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let test_hash = hasher.finalize();
        
        test.test_id = test_id;
        test.creator = ctx.accounts.test_creator.key();
        test.question_hashes = question_hashes;
        test.passing_score = passing_score;
        test.time_limit = time_limit;
        test.created_at = clock.unix_timestamp;
        test.is_active = true;
        test.total_attempts = 0;
        test.total_passed = 0;
        test.integrity_hash = test_hash.to_vec();
        
        emit!(KnowledgeTestCreated {
            test_id,
            creator: ctx.accounts.test_creator.key(),
            passing_score,
            question_count: question_hashes.len() as u8,
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn submit_test_answers(
        ctx: Context<SubmitTestAnswers>,
        test_id: u64,
        answers: Vec<u8>,
    ) -> Result<()> {
        let test = &mut ctx.accounts.knowledge_test;
        let submission = &mut ctx.accounts.test_submission;
        let clock = Clock::get()?;
        
        require!(test.is_active, KnowledgeError::TestInactive);
        require!(answers.len() == test.question_hashes.len(), KnowledgeError::AnswerCountMismatch);
        
        let mut hasher = Sha3_256::new();
        hasher.update(&test_id.to_le_bytes());
        hasher.update(ctx.accounts.participant.key().as_ref());
        for answer in &answers {
            hasher.update(&[*answer]);
        }
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let submission_hash = hasher.finalize();
        
        submission.test_id = test_id;
        submission.participant = ctx.accounts.participant.key();
        submission.answers = answers;
        submission.submitted_at = clock.unix_timestamp;
        submission.is_graded = false;
        submission.score = 0;
        submission.passed = false;
        submission.submission_hash = submission_hash.to_vec();
        
        test.total_attempts += 1;
        
        emit!(TestAnswersSubmitted {
            test_id,
            participant: ctx.accounts.participant.key(),
            answer_count: submission.answers.len() as u8,
            submission_hash: submission_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn verify_test_results(
        ctx: Context<VerifyTestResults>,
        test_id: u64,
        correct_answers: Vec<u8>,
    ) -> Result<()> {
        let test = &mut ctx.accounts.knowledge_test;
        let submission = &mut ctx.accounts.test_submission;
        let clock = Clock::get()?;
        
        require!(!submission.is_graded, KnowledgeError::AlreadyGraded);
        require!(correct_answers.len() == submission.answers.len(), KnowledgeError::AnswerCountMismatch);
        
        let mut correct_count = 0u8;
        for (i, &answer) in submission.answers.iter().enumerate() {
            if answer == correct_answers[i] {
                correct_count += 1;
            }
        }
        
        let score = (correct_count as u16 * 100 / submission.answers.len() as u16) as u8;
        let passed = score >= test.passing_score;
        
        submission.score = score;
        submission.passed = passed;
        submission.is_graded = true;
        submission.graded_at = Some(clock.unix_timestamp);
        
        if passed {
            test.total_passed += 1;
        }
        
        let mut hasher = Sha3_256::new();
        hasher.update(&test_id.to_le_bytes());
        hasher.update(submission.participant.as_ref());
        hasher.update(&score.to_le_bytes());
        hasher.update(&(passed as u8).to_le_bytes());
        hasher.update(&clock.unix_timestamp.to_le_bytes());
        let result_hash = hasher.finalize();
        
        emit!(TestResultsVerified {
            test_id,
            participant: submission.participant,
            score,
            passed,
            result_hash: result_hash.to_vec(),
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn track_user_competency(
        ctx: Context<TrackUserCompetency>,
        competency_area: CompetencyArea,
        score_adjustment: i8,
    ) -> Result<()> {
        let competency = &mut ctx.accounts.user_competency;
        let clock = Clock::get()?;
        
        if competency.user == Pubkey::default() {
            competency.user = ctx.accounts.user.key();
            competency.trading_competency = 50;
            competency.risk_management_competency = 50;
            competency.compliance_competency = 50;
            competency.ai_understanding_competency = 50;
            competency.last_updated = clock.unix_timestamp;
        }
        
        match competency_area {
            CompetencyArea::Trading => {
                competency.trading_competency = 
                    (competency.trading_competency as i16 + score_adjustment as i16)
                    .max(0).min(100) as u8;
            },
            CompetencyArea::RiskManagement => {
                competency.risk_management_competency = 
                    (competency.risk_management_competency as i16 + score_adjustment as i16)
                    .max(0).min(100) as u8;
            },
            CompetencyArea::Compliance => {
                competency.compliance_competency = 
                    (competency.compliance_competency as i16 + score_adjustment as i16)
                    .max(0).min(100) as u8;
            },
            CompetencyArea::AiUnderstanding => {
                competency.ai_understanding_competency = 
                    (competency.ai_understanding_competency as i16 + score_adjustment as i16)
                    .max(0).min(100) as u8;
            },
        }
        
        competency.last_updated = clock.unix_timestamp;
        
        emit!(UserCompetencyUpdated {
            user: ctx.accounts.user.key(),
            competency_area,
            new_score: match competency_area {
                CompetencyArea::Trading => competency.trading_competency,
                CompetencyArea::RiskManagement => competency.risk_management_competency,
                CompetencyArea::Compliance => competency.compliance_competency,
                CompetencyArea::AiUnderstanding => competency.ai_understanding_competency,
            },
            timestamp: clock.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn toggle_profile_switch(
        ctx: Context<ToggleSwitch>,
        switch_type: SwitchType,
        enabled: bool,
    ) -> Result<()> {
        let user_profile = &mut ctx.accounts.user_profile;
        
        require!(user_profile.owner == ctx.accounts.user.key(), KnowledgeError::UnauthorizedProfileAccess);
        
        match switch_type {
            SwitchType::AutoPauseOnQuizFail => user_profile.auto_pause_on_quiz_fail = enabled,
            SwitchType::RandomInspectorRotation => user_profile.random_inspector_rotation = enabled,
            SwitchType::AIPolicyAlerts => user_profile.ai_policy_alerts = enabled,
            SwitchType::ComplianceView => user_profile.compliance_view_enabled = enabled,
            SwitchType::RiskMonitoring => user_profile.risk_monitoring_enabled = enabled,
        }
        
        user_profile.last_switch_update = Clock::get()?.unix_timestamp;
        
        emit!(ProfileSwitchToggled {
            user: ctx.accounts.user.key(),
            switch_type,
            enabled,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn update_inspector_rotation(
        ctx: Context<UpdateRotation>,
        frequency: RotationFrequency,
        inspector_pool: Vec<Pubkey>,
    ) -> Result<()> {
        let user_profile = &mut ctx.accounts.user_profile;
        
        require!(user_profile.owner == ctx.accounts.user.key(), KnowledgeError::UnauthorizedProfileAccess);
        require!(inspector_pool.len() <= 10, KnowledgeError::TooManyInspectors);
        
        user_profile.inspector_rotation_frequency = frequency;
        user_profile.inspector_pool = inspector_pool;
        user_profile.last_rotation_timestamp = Clock::get()?.unix_timestamp;
        
        let next_rotation = calculate_next_rotation_time(frequency)?;
        user_profile.next_rotation_timestamp = next_rotation;
        
        emit!(InspectorRotationUpdated {
            user: ctx.accounts.user.key(),
            frequency,
            inspector_count: user_profile.inspector_pool.len() as u8,
            next_rotation,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn configure_ai_policy_alerts(
        ctx: Context<ConfigureAlerts>,
        alert_settings: AlertSettings,
    ) -> Result<()> {
        let user_profile = &mut ctx.accounts.user_profile;
        
        require!(user_profile.owner == ctx.accounts.user.key(), KnowledgeError::UnauthorizedProfileAccess);
        
        user_profile.alert_settings = Some(alert_settings.clone());
        user_profile.last_alert_config_update = Clock::get()?.unix_timestamp;
        
        emit!(AlertSettingsConfigured {
            user: ctx.accounts.user.key(),
            roi_threshold: alert_settings.roi_threshold,
            volatility_threshold: alert_settings.volatility_threshold,
            notification_frequency: alert_settings.notification_frequency,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn initialize_user_profile(ctx: Context<InitializeUserProfile>) -> Result<()> {
        let user_profile = &mut ctx.accounts.user_profile;
        
        user_profile.owner = ctx.accounts.user.key();
        user_profile.auto_pause_on_quiz_fail = true;
        user_profile.random_inspector_rotation = false;
        user_profile.ai_policy_alerts = true;
        user_profile.compliance_view_enabled = true;
        user_profile.risk_monitoring_enabled = true;
        user_profile.inspector_rotation_frequency = RotationFrequency::Weekly;
        user_profile.inspector_pool = Vec::new();
        user_profile.current_inspector = None;
        user_profile.creation_timestamp = Clock::get()?.unix_timestamp;
        user_profile.last_switch_update = Clock::get()?.unix_timestamp;
        user_profile.last_rotation_timestamp = 0;
        user_profile.next_rotation_timestamp = 0;
        user_profile.last_alert_config_update = Clock::get()?.unix_timestamp;
        user_profile.alert_settings = None;
        
        emit!(UserProfileInitialized {
            user: ctx.accounts.user.key(),
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn execute_inspector_rotation(ctx: Context<ExecuteRotation>) -> Result<()> {
        let user_profile = &mut ctx.accounts.user_profile;
        
        require!(user_profile.random_inspector_rotation, KnowledgeError::RotationNotEnabled);
        require!(
            Clock::get()?.unix_timestamp >= user_profile.next_rotation_timestamp,
            KnowledgeError::RotationNotDue
        );
        require!(!user_profile.inspector_pool.is_empty(), KnowledgeError::NoInspectorsAvailable);
        
        let current_time = Clock::get()?.unix_timestamp;
        let random_seed = (current_time % user_profile.inspector_pool.len() as i64) as usize;
        let selected_inspector = user_profile.inspector_pool[random_seed];
        
        user_profile.current_inspector = Some(selected_inspector);
        user_profile.last_rotation_timestamp = current_time;
        user_profile.next_rotation_timestamp = calculate_next_rotation_time(user_profile.inspector_rotation_frequency)?;
        
        emit!(InspectorRotationExecuted {
            user: ctx.accounts.user.key(),
            selected_inspector,
            rotation_timestamp: current_time,
            next_rotation: user_profile.next_rotation_timestamp,
        });
        
        Ok(())
    }
}

fn calculate_next_rotation_time(frequency: RotationFrequency) -> Result<i64> {
    let current_time = Clock::get()?.unix_timestamp;
    let seconds_to_add = match frequency {
        RotationFrequency::Daily => 24 * 60 * 60,
        RotationFrequency::Weekly => 7 * 24 * 60 * 60,
        RotationFrequency::Monthly => 30 * 24 * 60 * 60,
    };
    Ok(current_time + seconds_to_add)
}

#[account]
pub struct KnowledgeTest {
    pub test_id: u64,                    // 8 bytes
    pub creator: Pubkey,                 // 32 bytes
    pub question_hashes: Vec<[u8; 32]>,  // Variable size, max 50 questions
    pub passing_score: u8,               // 1 byte
    pub time_limit: u32,                 // 4 bytes (seconds)
    pub created_at: i64,                 // 8 bytes
    pub is_active: bool,                 // 1 byte
    pub total_attempts: u32,             // 4 bytes
    pub total_passed: u32,               // 4 bytes
    pub integrity_hash: Vec<u8>,         // 32 bytes (SHA-3)
}

#[account]
pub struct TestSubmission {
    pub test_id: u64,                    // 8 bytes
    pub participant: Pubkey,             // 32 bytes
    pub answers: Vec<u8>,                // Variable size
    pub submitted_at: i64,               // 8 bytes
    pub is_graded: bool,                 // 1 byte
    pub score: u8,                       // 1 byte
    pub passed: bool,                    // 1 byte
    pub graded_at: Option<i64>,          // 9 bytes
    pub submission_hash: Vec<u8>,        // 32 bytes (SHA-3)
}

#[account]
pub struct UserCompetency {
    pub user: Pubkey,
    pub trading_competency: u8,
    pub risk_management_competency: u8,
    pub compliance_competency: u8,
    pub ai_understanding_competency: u8,
    pub last_updated: i64,
}

#[account]
pub struct UserProfile {
    pub owner: Pubkey,
    pub auto_pause_on_quiz_fail: bool,
    pub random_inspector_rotation: bool,
    pub ai_policy_alerts: bool,
    pub compliance_view_enabled: bool,
    pub risk_monitoring_enabled: bool,
    pub inspector_rotation_frequency: RotationFrequency,
    pub inspector_pool: Vec<Pubkey>,
    pub current_inspector: Option<Pubkey>,
    pub creation_timestamp: i64,
    pub last_switch_update: i64,
    pub last_rotation_timestamp: i64,
    pub next_rotation_timestamp: i64,
    pub last_alert_config_update: i64,
    pub alert_settings: Option<AlertSettings>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq)]
pub enum CompetencyArea {
    Trading,
    RiskManagement,
    Compliance,
    AiUnderstanding,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum SwitchType {
    AutoPauseOnQuizFail,
    RandomInspectorRotation,
    AIPolicyAlerts,
    ComplianceView,
    RiskMonitoring,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum RotationFrequency {
    Daily,
    Weekly,
    Monthly,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct AlertSettings {
    pub roi_threshold: f64,
    pub volatility_threshold: f64,
    pub notification_frequency: RotationFrequency,
}

#[derive(Accounts)]
#[instruction(test_id: u64)]
pub struct CreateKnowledgeTest<'info> {
    #[account(
        init,
        payer = test_creator,
        space = 8 + 8 + 32 + 4 + (50 * 32) + 1 + 4 + 8 + 1 + 4 + 4 + 64, // Max space for 50 questions
        seeds = [b"knowledge_test", &test_id.to_le_bytes()],
        bump
    )]
    pub knowledge_test: Account<'info, KnowledgeTest>,
    #[account(mut)]
    pub test_creator: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(test_id: u64)]
pub struct SubmitTestAnswers<'info> {
    #[account(
        mut,
        seeds = [b"knowledge_test", &test_id.to_le_bytes()],
        bump
    )]
    pub knowledge_test: Account<'info, KnowledgeTest>,
    #[account(
        init,
        payer = participant,
        space = 8 + 8 + 32 + 4 + 50 + 8 + 1 + 1 + 1 + 9 + 64, // Max space for 50 answers
        seeds = [b"test_submission", &test_id.to_le_bytes(), participant.key().as_ref()],
        bump
    )]
    pub test_submission: Account<'info, TestSubmission>,
    #[account(mut)]
    pub participant: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(test_id: u64)]
pub struct VerifyTestResults<'info> {
    #[account(
        mut,
        seeds = [b"knowledge_test", &test_id.to_le_bytes()],
        bump
    )]
    pub knowledge_test: Account<'info, KnowledgeTest>,
    #[account(
        mut,
        seeds = [b"test_submission", &test_id.to_le_bytes(), test_submission.participant.as_ref()],
        bump
    )]
    pub test_submission: Account<'info, TestSubmission>,
    pub grader: Signer<'info>,
}

#[derive(Accounts)]
pub struct TrackUserCompetency<'info> {
    #[account(
        init_if_needed,
        payer = user,
        space = 8 + 32 + 1 + 1 + 1 + 1 + 8,
        seeds = [b"user_competency", user.key().as_ref()],
        bump
    )]
    pub user_competency: Account<'info, UserCompetency>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ToggleSwitch<'info> {
    #[account(mut)]
    pub user_profile: Account<'info, UserProfile>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct UpdateRotation<'info> {
    #[account(mut)]
    pub user_profile: Account<'info, UserProfile>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct ConfigureAlerts<'info> {
    #[account(mut)]
    pub user_profile: Account<'info, UserProfile>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct InitializeUserProfile<'info> {
    #[account(
        init,
        payer = user,
        space = 8 + 32 + 1 + 1 + 1 + 1 + 1 + 1 + 4 + (10 * 32) + 33 + 8 + 8 + 8 + 8 + 8 + 4 + 100,
        seeds = [b"user_profile", user.key().as_ref()],
        bump
    )]
    pub user_profile: Account<'info, UserProfile>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ExecuteRotation<'info> {
    #[account(mut)]
    pub user_profile: Account<'info, UserProfile>,
    pub user: Signer<'info>,
}

#[event]
pub struct KnowledgeTestCreated {
    pub test_id: u64,
    pub creator: Pubkey,
    pub passing_score: u8,
    pub question_count: u8,
    pub timestamp: i64,
}

#[event]
pub struct TestAnswersSubmitted {
    pub test_id: u64,
    pub participant: Pubkey,
    pub answer_count: u8,
    pub submission_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct TestResultsVerified {
    pub test_id: u64,
    pub participant: Pubkey,
    pub score: u8,
    pub passed: bool,
    pub result_hash: Vec<u8>,
    pub timestamp: i64,
}

#[event]
pub struct UserCompetencyUpdated {
    pub user: Pubkey,
    pub competency_area: CompetencyArea,
    pub new_score: u8,
    pub timestamp: i64,
}

#[event]
pub struct ProfileSwitchToggled {
    pub user: Pubkey,
    pub switch_type: SwitchType,
    pub enabled: bool,
    pub timestamp: i64,
}

#[event]
pub struct InspectorRotationUpdated {
    pub user: Pubkey,
    pub frequency: RotationFrequency,
    pub inspector_count: u8,
    pub next_rotation: i64,
    pub timestamp: i64,
}

#[event]
pub struct AlertSettingsConfigured {
    pub user: Pubkey,
    pub roi_threshold: f64,
    pub volatility_threshold: f64,
    pub notification_frequency: RotationFrequency,
    pub timestamp: i64,
}

#[event]
pub struct UserProfileInitialized {
    pub user: Pubkey,
    pub timestamp: i64,
}

#[event]
pub struct InspectorRotationExecuted {
    pub user: Pubkey,
    pub selected_inspector: Pubkey,
    pub rotation_timestamp: i64,
    pub next_rotation: i64,
}

#[error_code]
pub enum KnowledgeError {
    #[msg("Invalid passing score")]
    InvalidPassingScore,
    #[msg("Too many questions")]
    TooManyQuestions,
    #[msg("Test is not active")]
    TestInactive,
    #[msg("Answer count mismatch")]
    AnswerCountMismatch,
    #[msg("Test already graded")]
    AlreadyGraded,
    #[msg("Unauthorized profile access")]
    UnauthorizedProfileAccess,
    #[msg("Too many inspectors in pool")]
    TooManyInspectors,
    #[msg("Inspector rotation not enabled")]
    RotationNotEnabled,
    #[msg("Rotation not due yet")]
    RotationNotDue,
    #[msg("No inspectors available for rotation")]
    NoInspectorsAvailable,
}
