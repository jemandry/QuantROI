use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer, Mint};
use mpl_token_metadata::state::Metadata;
use sha3::{Digest, Sha3_256};

declare_id!("NFTMarketplaceProgram1111111111111111111111");

#[program]
pub mod nft_marketplace {
    use super::*;

    pub fn initialize_marketplace(ctx: Context<InitializeMarketplace>) -> Result<()> {
        let marketplace = &mut ctx.accounts.marketplace;
        marketplace.authority = ctx.accounts.authority.key();
        marketplace.total_nfts_minted = 0;
        marketplace.certification_count = 0;
        marketplace.investment_position_count = 0;
        marketplace.reward_count = 0;
        
        emit!(MarketplaceInitialized {
            authority: marketplace.authority,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn mint_certification_nft(
        ctx: Context<MintNFT>,
        metadata: NFTMetadata,
        quiz_score: u8,
        competency_level: CompetencyLevel,
    ) -> Result<()> {
        require!(quiz_score >= 80, ErrorCode::InsufficientQuizScore);
        
        let marketplace = &mut ctx.accounts.marketplace;
        let nft_account = &mut ctx.accounts.nft_account;
        
        nft_account.nft_type = NFTType::Certification;
        nft_account.owner = ctx.accounts.user.key();
        nft_account.metadata = metadata.clone();
        nft_account.mint_timestamp = Clock::get()?.unix_timestamp;
        nft_account.quiz_score = Some(quiz_score);
        nft_account.competency_level = Some(competency_level);
        nft_account.is_transferable = true;
        nft_account.marketplace_listed = false;
        
        let metadata_hash = create_metadata_hash(&metadata)?;
        nft_account.metadata_hash = metadata_hash;
        
        marketplace.total_nfts_minted += 1;
        marketplace.certification_count += 1;
        
        emit!(NFTMinted {
            nft_type: NFTType::Certification,
            owner: ctx.accounts.user.key(),
            metadata_hash,
            quiz_score: Some(quiz_score),
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn mint_investment_position_nft(
        ctx: Context<MintNFT>,
        metadata: NFTMetadata,
        position_data: PositionData,
    ) -> Result<()> {
        let marketplace = &mut ctx.accounts.marketplace;
        let nft_account = &mut ctx.accounts.nft_account;
        
        nft_account.nft_type = NFTType::InvestmentPosition;
        nft_account.owner = ctx.accounts.user.key();
        nft_account.metadata = metadata.clone();
        nft_account.mint_timestamp = Clock::get()?.unix_timestamp;
        nft_account.position_data = Some(position_data.clone());
        nft_account.is_transferable = true;
        nft_account.marketplace_listed = false;
        
        let metadata_hash = create_metadata_hash(&metadata)?;
        nft_account.metadata_hash = metadata_hash;
        
        marketplace.total_nfts_minted += 1;
        marketplace.investment_position_count += 1;
        
        emit!(NFTMinted {
            nft_type: NFTType::InvestmentPosition,
            owner: ctx.accounts.user.key(),
            metadata_hash,
            quiz_score: None,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn mint_reward_nft(
        ctx: Context<MintNFT>,
        metadata: NFTMetadata,
        reward_type: RewardType,
        milestone_achieved: String,
    ) -> Result<()> {
        let marketplace = &mut ctx.accounts.marketplace;
        let nft_account = &mut ctx.accounts.nft_account;
        
        nft_account.nft_type = NFTType::Reward;
        nft_account.owner = ctx.accounts.user.key();
        nft_account.metadata = metadata.clone();
        nft_account.mint_timestamp = Clock::get()?.unix_timestamp;
        nft_account.reward_type = Some(reward_type);
        nft_account.milestone_achieved = Some(milestone_achieved);
        nft_account.is_transferable = true;
        nft_account.marketplace_listed = false;
        
        let metadata_hash = create_metadata_hash(&metadata)?;
        nft_account.metadata_hash = metadata_hash;
        
        marketplace.total_nfts_minted += 1;
        marketplace.reward_count += 1;
        
        emit!(NFTMinted {
            nft_type: NFTType::Reward,
            owner: ctx.accounts.user.key(),
            metadata_hash,
            quiz_score: None,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn list_nft_for_sale(
        ctx: Context<ListNFT>,
        price: u64,
    ) -> Result<()> {
        let nft_account = &mut ctx.accounts.nft_account;
        
        require!(nft_account.owner == ctx.accounts.user.key(), ErrorCode::UnauthorizedNFTOwner);
        require!(nft_account.is_transferable, ErrorCode::NFTNotTransferable);
        
        nft_account.marketplace_listed = true;
        nft_account.listing_price = Some(price);
        nft_account.listing_timestamp = Some(Clock::get()?.unix_timestamp);
        
        emit!(NFTListed {
            nft_account: ctx.accounts.nft_account.key(),
            owner: ctx.accounts.user.key(),
            price,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn purchase_nft(ctx: Context<PurchaseNFT>) -> Result<()> {
        let nft_account = &mut ctx.accounts.nft_account;
        
        require!(nft_account.marketplace_listed, ErrorCode::NFTNotListed);
        require!(nft_account.owner != ctx.accounts.buyer.key(), ErrorCode::CannotBuyOwnNFT);
        
        let price = nft_account.listing_price.unwrap();
        
        let transfer_instruction = Transfer {
            from: ctx.accounts.buyer_token_account.to_account_info(),
            to: ctx.accounts.seller_token_account.to_account_info(),
            authority: ctx.accounts.buyer.to_account_info(),
        };
        
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                transfer_instruction,
            ),
            price,
        )?;
        
        nft_account.owner = ctx.accounts.buyer.key();
        nft_account.marketplace_listed = false;
        nft_account.listing_price = None;
        nft_account.listing_timestamp = None;
        
        emit!(NFTPurchased {
            nft_account: ctx.accounts.nft_account.key(),
            seller: ctx.accounts.seller.key(),
            buyer: ctx.accounts.buyer.key(),
            price,
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }

    pub fn burn_nft_on_objective_failure(ctx: Context<BurnNFT>) -> Result<()> {
        let nft_account = &ctx.accounts.nft_account;
        
        require!(nft_account.owner == ctx.accounts.user.key(), ErrorCode::UnauthorizedNFTOwner);
        
        emit!(NFTBurned {
            nft_account: ctx.accounts.nft_account.key(),
            owner: ctx.accounts.user.key(),
            reason: "Objective failure".to_string(),
            timestamp: Clock::get()?.unix_timestamp,
        });
        
        Ok(())
    }
}

fn create_metadata_hash(metadata: &NFTMetadata) -> Result<[u8; 32]> {
    let mut hasher = Sha3_256::new();
    hasher.update(metadata.name.as_bytes());
    hasher.update(metadata.description.as_bytes());
    hasher.update(metadata.image_url.as_bytes());
    
    for attr in &metadata.attributes {
        hasher.update(attr.trait_type.as_bytes());
        hasher.update(attr.value.as_bytes());
    }
    
    Ok(hasher.finalize().into())
}

#[derive(Accounts)]
pub struct InitializeMarketplace<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + Marketplace::INIT_SPACE
    )]
    pub marketplace: Account<'info, Marketplace>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct MintNFT<'info> {
    #[account(mut)]
    pub marketplace: Account<'info, Marketplace>,
    #[account(
        init,
        payer = user,
        space = 8 + NFTAccount::INIT_SPACE
    )]
    pub nft_account: Account<'info, NFTAccount>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ListNFT<'info> {
    #[account(mut)]
    pub nft_account: Account<'info, NFTAccount>,
    pub user: Signer<'info>,
}

#[derive(Accounts)]
pub struct PurchaseNFT<'info> {
    #[account(mut)]
    pub nft_account: Account<'info, NFTAccount>,
    #[account(mut)]
    pub buyer: Signer<'info>,
    #[account(mut)]
    pub seller: AccountInfo<'info>,
    #[account(mut)]
    pub buyer_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub seller_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct BurnNFT<'info> {
    #[account(mut, close = user)]
    pub nft_account: Account<'info, NFTAccount>,
    #[account(mut)]
    pub user: Signer<'info>,
}

#[account]
#[derive(InitSpace)]
pub struct Marketplace {
    pub authority: Pubkey,
    pub total_nfts_minted: u64,
    pub certification_count: u64,
    pub investment_position_count: u64,
    pub reward_count: u64,
}

#[account]
#[derive(InitSpace)]
pub struct NFTAccount {
    pub nft_type: NFTType,
    pub owner: Pubkey,
    #[max_len(500)]
    pub metadata: NFTMetadata,
    pub metadata_hash: [u8; 32],
    pub mint_timestamp: i64,
    pub quiz_score: Option<u8>,
    pub competency_level: Option<CompetencyLevel>,
    #[max_len(200)]
    pub position_data: Option<PositionData>,
    pub reward_type: Option<RewardType>,
    #[max_len(100)]
    pub milestone_achieved: Option<String>,
    pub is_transferable: bool,
    pub marketplace_listed: bool,
    pub listing_price: Option<u64>,
    pub listing_timestamp: Option<i64>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct NFTMetadata {
    #[max_len(50)]
    pub name: String,
    #[max_len(200)]
    pub description: String,
    #[max_len(100)]
    pub image_url: String,
    #[max_len(10)]
    pub attributes: Vec<NFTAttribute>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct NFTAttribute {
    #[max_len(30)]
    pub trait_type: String,
    #[max_len(50)]
    pub value: String,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct PositionData {
    #[max_len(50)]
    pub strategy_name: String,
    pub roi_target: f64,
    pub investment_amount: u64,
    pub delegation_timestamp: i64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum NFTType {
    Certification,
    InvestmentPosition,
    Reward,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum CompetencyLevel {
    Beginner,
    Intermediate,
    Advanced,
    Expert,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum RewardType {
    ROIMilestone,
    ReferralBonus,
    ComplianceAchievement,
    TradingVolume,
}

#[event]
pub struct MarketplaceInitialized {
    pub authority: Pubkey,
    pub timestamp: i64,
}

#[event]
pub struct NFTMinted {
    pub nft_type: NFTType,
    pub owner: Pubkey,
    pub metadata_hash: [u8; 32],
    pub quiz_score: Option<u8>,
    pub timestamp: i64,
}

#[event]
pub struct NFTListed {
    pub nft_account: Pubkey,
    pub owner: Pubkey,
    pub price: u64,
    pub timestamp: i64,
}

#[event]
pub struct NFTPurchased {
    pub nft_account: Pubkey,
    pub seller: Pubkey,
    pub buyer: Pubkey,
    pub price: u64,
    pub timestamp: i64,
}

#[event]
pub struct NFTBurned {
    pub nft_account: Pubkey,
    pub owner: Pubkey,
    #[max_len(100)]
    pub reason: String,
    pub timestamp: i64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Insufficient quiz score for certification NFT")]
    InsufficientQuizScore,
    #[msg("Unauthorized NFT owner")]
    UnauthorizedNFTOwner,
    #[msg("NFT is not transferable")]
    NFTNotTransferable,
    #[msg("NFT is not listed for sale")]
    NFTNotListed,
    #[msg("Cannot buy your own NFT")]
    CannotBuyOwnNFT,
}
