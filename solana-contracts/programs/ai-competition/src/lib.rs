use anchor_lang::prelude::*;

declare_id!("AiCompetitionProgram111111111111111111111");

#[program]
pub mod ai_competition {
    use super::*;

    pub fn initialize(_ctx: Context<Initialize>) -> Result<()> {
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}