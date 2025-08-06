use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataItem {
    pub key: String,
    pub value: Vec<u8>,
    pub timestamp: Instant,
    pub access_count: u64,
    pub tier: DataTier,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DataTier {
    Hot,    // Redis, <10ns access
    Warm,   // PostgreSQL, 100μs-10ms
    Cold,   // TimescaleDB, >10ms
}

#[async_trait]
pub trait TierStorage: Send + Sync {
    async fn get(&self, key: &str) -> Result<Option<DataItem>, Box<dyn std::error::Error>>;
    async fn put(&self, item: DataItem) -> Result<(), Box<dyn std::error::Error>>;
    async fn delete(&self, key: &str) -> Result<(), Box<dyn std::error::Error>>;
    fn tier(&self) -> DataTier;
    fn target_latency(&self) -> Duration;
}

pub struct MemoryHierarchy {
    hot_tier: Box<dyn TierStorage>,
    warm_tier: Box<dyn TierStorage>,
    cold_tier: Box<dyn TierStorage>,
    access_stats: RwLock<HashMap<String, AccessStats>>,
}

#[derive(Debug, Clone)]
struct AccessStats {
    access_count: u64,
    last_access: Instant,
    promotion_score: f64,
}

impl MemoryHierarchy {
    pub fn new(
        hot_tier: Box<dyn TierStorage>,
        warm_tier: Box<dyn TierStorage>,
        cold_tier: Box<dyn TierStorage>,
    ) -> Self {
        Self {
            hot_tier,
            warm_tier,
            cold_tier,
            access_stats: RwLock::new(HashMap::new()),
        }
    }

    pub async fn get(&self, key: &str) -> Result<Option<DataItem>, Box<dyn std::error::Error>> {
        if let Some(item) = self.hot_tier.get(key).await? {
            self.update_access_stats(key).await;
            return Ok(Some(item));
        }

        if let Some(item) = self.warm_tier.get(key).await? {
            self.update_access_stats(key).await;
            if self.should_promote(key).await {
                let mut promoted_item = item.clone();
                promoted_item.tier = DataTier::Hot;
                self.hot_tier.put(promoted_item).await?;
            }
            return Ok(Some(item));
        }

        if let Some(item) = self.cold_tier.get(key).await? {
            self.update_access_stats(key).await;
            return Ok(Some(item));
        }

        Ok(None)
    }

    async fn update_access_stats(&self, key: &str) {
        let mut stats = self.access_stats.write().await;
        let entry = stats.entry(key.to_string()).or_insert(AccessStats {
            access_count: 0,
            last_access: Instant::now(),
            promotion_score: 0.0,
        });
        entry.access_count += 1;
        entry.last_access = Instant::now();
        entry.promotion_score = self.calculate_promotion_score(entry);
    }

    fn calculate_promotion_score(&self, stats: &AccessStats) -> f64 {
        let recency_factor = 1.0 / (stats.last_access.elapsed().as_secs() as f64 + 1.0);
        let frequency_factor = (stats.access_count as f64).ln();
        recency_factor * frequency_factor
    }

    async fn should_promote(&self, key: &str) -> bool {
        let stats = self.access_stats.read().await;
        if let Some(stat) = stats.get(key) {
            stat.promotion_score > 5.0 // Configurable threshold
        } else {
            false
        }
    }
}

pub struct RedisHotTier {
    connection_pool: redis::aio::ConnectionManager,
}

impl RedisHotTier {
    pub async fn new(redis_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let client = redis::Client::open(redis_url)?;
        let connection_pool = redis::aio::ConnectionManager::new(client).await?;
        Ok(Self { connection_pool })
    }
}

#[async_trait]
impl TierStorage for RedisHotTier {
    async fn get(&self, key: &str) -> Result<Option<DataItem>, Box<dyn std::error::Error>> {
        use redis::AsyncCommands;
        let mut conn = self.connection_pool.clone();
        
        let value: Option<Vec<u8>> = conn.get(key).await?;
        
        if let Some(data) = value {
            Ok(Some(DataItem {
                key: key.to_string(),
                value: data,
                timestamp: Instant::now(),
                access_count: 1,
                tier: DataTier::Hot,
            }))
        } else {
            Ok(None)
        }
    }

    async fn put(&self, item: DataItem) -> Result<(), Box<dyn std::error::Error>> {
        use redis::AsyncCommands;
        let mut conn = self.connection_pool.clone();
        
        conn.set_ex(&item.key, &item.value, 3600).await?; // 1 hour TTL
        Ok(())
    }

    async fn delete(&self, key: &str) -> Result<(), Box<dyn std::error::Error>> {
        use redis::AsyncCommands;
        let mut conn = self.connection_pool.clone();
        
        conn.del(key).await?;
        Ok(())
    }

    fn tier(&self) -> DataTier {
        DataTier::Hot
    }

    fn target_latency(&self) -> Duration {
        Duration::from_nanos(10) // <10ns target
    }
}

pub struct PostgresWarmTier {
    pool: sqlx::PgPool,
}

impl PostgresWarmTier {
    pub async fn new(database_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let pool = sqlx::PgPool::connect(database_url).await?;
        
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS warm_tier_data (
                key VARCHAR PRIMARY KEY,
                value BYTEA NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                access_count BIGINT DEFAULT 1
            )
            "#
        )
        .execute(&pool)
        .await?;
        
        Ok(Self { pool })
    }
}

#[async_trait]
impl TierStorage for PostgresWarmTier {
    async fn get(&self, key: &str) -> Result<Option<DataItem>, Box<dyn std::error::Error>> {
        let row = sqlx::query!(
            "SELECT value, access_count FROM warm_tier_data WHERE key = $1",
            key
        )
        .fetch_optional(&self.pool)
        .await?;
        
        if let Some(record) = row {
            sqlx::query!(
                "UPDATE warm_tier_data SET access_count = access_count + 1 WHERE key = $1",
                key
            )
            .execute(&self.pool)
            .await?;
            
            Ok(Some(DataItem {
                key: key.to_string(),
                value: record.value,
                timestamp: Instant::now(),
                access_count: record.access_count as u64 + 1,
                tier: DataTier::Warm,
            }))
        } else {
            Ok(None)
        }
    }

    async fn put(&self, item: DataItem) -> Result<(), Box<dyn std::error::Error>> {
        sqlx::query!(
            r#"
            INSERT INTO warm_tier_data (key, value, access_count)
            VALUES ($1, $2, $3)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                access_count = EXCLUDED.access_count
            "#,
            item.key,
            item.value,
            item.access_count as i64
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    async fn delete(&self, key: &str) -> Result<(), Box<dyn std::error::Error>> {
        sqlx::query!("DELETE FROM warm_tier_data WHERE key = $1", key)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    fn tier(&self) -> DataTier {
        DataTier::Warm
    }

    fn target_latency(&self) -> Duration {
        Duration::from_micros(100) // 100μs-10ms range
    }
}

pub struct TimescaleColdTier {
    pool: sqlx::PgPool,
}

impl TimescaleColdTier {
    pub async fn new(database_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let pool = sqlx::PgPool::connect(database_url).await?;
        
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS cold_tier_data (
                time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                key VARCHAR NOT NULL,
                value BYTEA NOT NULL,
                access_count BIGINT DEFAULT 1
            )
            "#
        )
        .execute(&pool)
        .await?;
        
        let _ = sqlx::query(
            "SELECT create_hypertable('cold_tier_data', 'time', if_not_exists => TRUE)"
        )
        .execute(&pool)
        .await;
        
        Ok(Self { pool })
    }
}

#[async_trait]
impl TierStorage for TimescaleColdTier {
    async fn get(&self, key: &str) -> Result<Option<DataItem>, Box<dyn std::error::Error>> {
        let row = sqlx::query!(
            "SELECT value, access_count FROM cold_tier_data WHERE key = $1 ORDER BY time DESC LIMIT 1",
            key
        )
        .fetch_optional(&self.pool)
        .await?;
        
        if let Some(record) = row {
            Ok(Some(DataItem {
                key: key.to_string(),
                value: record.value,
                timestamp: Instant::now(),
                access_count: record.access_count as u64,
                tier: DataTier::Cold,
            }))
        } else {
            Ok(None)
        }
    }

    async fn put(&self, item: DataItem) -> Result<(), Box<dyn std::error::Error>> {
        sqlx::query!(
            "INSERT INTO cold_tier_data (key, value, access_count) VALUES ($1, $2, $3)",
            item.key,
            item.value,
            item.access_count as i64
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    async fn delete(&self, key: &str) -> Result<(), Box<dyn std::error::Error>> {
        sqlx::query!("DELETE FROM cold_tier_data WHERE key = $1", key)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    fn tier(&self) -> DataTier {
        DataTier::Cold
    }

    fn target_latency(&self) -> Duration {
        Duration::from_millis(10) // >10ms acceptable
    }
}
