use std::collections::{HashMap, VecDeque};
use std::time::{Duration, Instant};
use std::sync::Arc;
use tokio::sync::{Mutex, RwLock};
use tokio::time::sleep;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MemoryLevel {
    Register,      // ~0.5-1 ns
    L1Cache,       // ~1-4 ns
    L2Cache,       // ~10-20 ns
    L3Cache,       // ~40-100 ns
    MainMemory,    // ~100-300 ns
    SSD,           // ~0.1-1 ms
    HDD,           // ~5-10 ms
    NetworkStorage, // ~10-100 ms
    ArchivalStorage, // ~seconds
}

impl MemoryLevel {
    pub fn latency(&self) -> Duration {
        match self {
            MemoryLevel::Register => Duration::from_nanos(1),
            MemoryLevel::L1Cache => Duration::from_nanos(2),
            MemoryLevel::L2Cache => Duration::from_nanos(15),
            MemoryLevel::L3Cache => Duration::from_nanos(70),
            MemoryLevel::MainMemory => Duration::from_nanos(200),
            MemoryLevel::SSD => Duration::from_micros(100),
            MemoryLevel::HDD => Duration::from_millis(7),
            MemoryLevel::NetworkStorage => Duration::from_millis(50),
            MemoryLevel::ArchivalStorage => Duration::from_secs(1),
        }
    }

    pub fn capacity(&self) -> usize {
        match self {
            MemoryLevel::Register => 1024,           // 1KB - very limited
            MemoryLevel::L1Cache => 64 * 1024,       // 64KB per core
            MemoryLevel::L2Cache => 512 * 1024,      // 512KB
            MemoryLevel::L3Cache => 32 * 1024 * 1024, // 32MB shared
            MemoryLevel::MainMemory => 32 * 1024 * 1024 * 1024, // 32GB
            MemoryLevel::SSD => 1024 * 1024 * 1024 * 1024, // 1TB
            MemoryLevel::HDD => 10 * 1024 * 1024 * 1024 * 1024, // 10TB
            MemoryLevel::NetworkStorage => usize::MAX, // Unlimited
            MemoryLevel::ArchivalStorage => usize::MAX, // Unlimited
        }
    }
}

#[derive(Debug, Clone)]
pub enum ReplacementPolicy {
    LRU,  // Least Recently Used
    LFU,  // Least Frequently Used
    FIFO, // First In, First Out
    Random,
}

#[derive(Debug, Clone)]
pub struct MemoryBlock {
    pub key: String,
    pub data: Vec<u8>,
    pub access_count: u64,
    pub last_access: Instant,
    pub created_at: Instant,
}

impl MemoryBlock {
    pub fn new(key: String, data: Vec<u8>) -> Self {
        let now = Instant::now();
        Self {
            key,
            data,
            access_count: 1,
            last_access: now,
            created_at: now,
        }
    }

    pub fn access(&mut self) {
        self.access_count += 1;
        self.last_access = Instant::now();
    }

    pub fn size(&self) -> usize {
        self.data.len()
    }
}

pub struct Cache {
    level: MemoryLevel,
    capacity: usize,
    current_size: usize,
    policy: ReplacementPolicy,
    data: HashMap<String, MemoryBlock>,
    access_order: VecDeque<String>,
}

impl Cache {
    pub fn new(level: MemoryLevel, policy: ReplacementPolicy) -> Self {
        Self {
            level,
            capacity: level.capacity(),
            current_size: 0,
            policy,
            data: HashMap::new(),
            access_order: VecDeque::new(),
        }
    }

    pub async fn get(&mut self, key: &str) -> Option<Vec<u8>> {
        sleep(self.level.latency()).await;

        if let Some(block) = self.data.get_mut(key) {
            block.access();
            let data = block.data.clone();
            self.update_access_order(key);
            Some(data)
        } else {
            None
        }
    }

    pub async fn put(&mut self, key: String, data: Vec<u8>) -> bool {
        sleep(self.level.latency()).await;

        let block_size = data.len();
        
        while self.current_size + block_size > self.capacity {
            if !self.evict_one() {
                return false; // Cannot evict, cache full
            }
        }

        let block = MemoryBlock::new(key.clone(), data);
        self.current_size += block_size;
        self.data.insert(key.clone(), block);
        self.access_order.push_back(key);
        
        true
    }

    fn evict_one(&mut self) -> bool {
        let key_to_evict = match self.policy {
            ReplacementPolicy::LRU => self.access_order.front().cloned(),
            ReplacementPolicy::FIFO => self.access_order.front().cloned(),
            ReplacementPolicy::LFU => {
                self.data.iter()
                    .min_by_key(|(_, block)| block.access_count)
                    .map(|(key, _)| key.clone())
            },
            ReplacementPolicy::Random => {
                use rand::seq::SliceRandom;
                let keys: Vec<_> = self.data.keys().collect();
                keys.choose(&mut rand::thread_rng()).map(|k| (*k).clone())
            }
        };

        if let Some(key) = key_to_evict {
            if let Some(block) = self.data.remove(&key) {
                self.current_size -= block.size();
                self.access_order.retain(|k| k != &key);
                return true;
            }
        }
        false
    }

    fn update_access_order(&mut self, key: &str) {
        match self.policy {
            ReplacementPolicy::LRU => {
                self.access_order.retain(|k| k != key);
                self.access_order.push_back(key.to_string());
            },
            _ => {} // Other policies don't need access order updates
        }
    }

    pub fn hit_rate(&self) -> f64 {
        if self.data.is_empty() {
            0.0
        } else {
            let total_accesses: u64 = self.data.values().map(|b| b.access_count).sum();
            let hits = self.data.len() as u64;
            hits as f64 / total_accesses as f64
        }
    }

    pub fn utilization(&self) -> f64 {
        self.current_size as f64 / self.capacity as f64
    }
}

pub struct MemoryHierarchy {
    registers: Arc<Mutex<Cache>>,
    l1_cache: Arc<Mutex<Cache>>,
    l2_cache: Arc<Mutex<Cache>>,
    l3_cache: Arc<Mutex<Cache>>,
    main_memory: Arc<RwLock<Cache>>,
    ssd_storage: Arc<RwLock<Cache>>,
    hdd_storage: Arc<RwLock<Cache>>,
    network_storage: Arc<RwLock<HashMap<String, Vec<u8>>>>,
    archival_storage: Arc<RwLock<HashMap<String, Vec<u8>>>>,
    
    access_stats: Arc<Mutex<AccessStats>>,
}

#[derive(Debug, Default)]
pub struct AccessStats {
    pub total_accesses: u64,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub total_latency: Duration,
    pub level_accesses: HashMap<MemoryLevel, u64>,
}

impl MemoryHierarchy {
    pub fn new() -> Self {
        Self {
            registers: Arc::new(Mutex::new(Cache::new(MemoryLevel::Register, ReplacementPolicy::LRU))),
            l1_cache: Arc::new(Mutex::new(Cache::new(MemoryLevel::L1Cache, ReplacementPolicy::LRU))),
            l2_cache: Arc::new(Mutex::new(Cache::new(MemoryLevel::L2Cache, ReplacementPolicy::LRU))),
            l3_cache: Arc::new(Mutex::new(Cache::new(MemoryLevel::L3Cache, ReplacementPolicy::LRU))),
            main_memory: Arc::new(RwLock::new(Cache::new(MemoryLevel::MainMemory, ReplacementPolicy::LFU))),
            ssd_storage: Arc::new(RwLock::new(Cache::new(MemoryLevel::SSD, ReplacementPolicy::LFU))),
            hdd_storage: Arc::new(RwLock::new(Cache::new(MemoryLevel::HDD, ReplacementPolicy::FIFO))),
            network_storage: Arc::new(RwLock::new(HashMap::new())),
            archival_storage: Arc::new(RwLock::new(HashMap::new())),
            access_stats: Arc::new(Mutex::new(AccessStats::default())),
        }
    }

    pub async fn get(&self, key: &str) -> Option<Vec<u8>> {
        let start_time = Instant::now();
        {
            let mut stats = self.access_stats.lock().await;
            stats.total_accesses += 1;
        }

        let levels = [
            (MemoryLevel::Register, &self.registers),
            (MemoryLevel::L1Cache, &self.l1_cache),
            (MemoryLevel::L2Cache, &self.l2_cache),
            (MemoryLevel::L3Cache, &self.l3_cache),
        ];

        for (level, cache_ref) in levels.iter() {
            if let Ok(mut cache) = cache_ref.try_lock() {
                if let Some(data) = cache.get(key).await {
                    self.record_access(*level, start_time, true).await;
                    return Some(data);
                }
            }
        }

        if let Ok(mut memory) = self.main_memory.try_write() {
            if let Some(data) = memory.get(key).await {
                self.record_access(MemoryLevel::MainMemory, start_time, true).await;
                self.promote_to_cache(key, &data).await;
                return Some(data);
            }
        }

        if let Ok(mut ssd) = self.ssd_storage.try_write() {
            if let Some(data) = ssd.get(key).await {
                self.record_access(MemoryLevel::SSD, start_time, true).await;
                self.promote_to_memory(key, &data).await;
                return Some(data);
            }
        }

        if let Ok(mut hdd) = self.hdd_storage.try_write() {
            if let Some(data) = hdd.get(key).await {
                self.record_access(MemoryLevel::HDD, start_time, true).await;
                self.promote_to_memory(key, &data).await;
                return Some(data);
            }
        }

        let network_data = {
            let network = self.network_storage.read().await;
            sleep(MemoryLevel::NetworkStorage.latency()).await;
            network.get(key).cloned()
        };
        
        if let Some(data) = network_data {
            self.record_access(MemoryLevel::NetworkStorage, start_time, true).await;
            self.promote_to_storage(key, &data).await;
            return Some(data);
        }

        let archival_data = {
            let archival = self.archival_storage.read().await;
            sleep(MemoryLevel::ArchivalStorage.latency()).await;
            archival.get(key).cloned()
        };
        
        if let Some(data) = archival_data {
            self.record_access(MemoryLevel::ArchivalStorage, start_time, true).await;
            self.promote_to_storage(key, &data).await;
            return Some(data);
        }

        self.record_access(MemoryLevel::ArchivalStorage, start_time, false).await;
        None
    }

    pub async fn put(&self, key: String, data: Vec<u8>) -> bool {
        let data_size = data.len();
        
        if let Ok(mut archival) = self.archival_storage.try_write() {
            archival.insert(key.clone(), data.clone());
        }

        if data_size <= MemoryLevel::SSD.capacity() / 100 {
            if let Ok(mut ssd) = self.ssd_storage.try_write() {
                ssd.put(key.clone(), data.clone()).await;
            }
        }

        if data_size <= MemoryLevel::MainMemory.capacity() / 100 {
            if let Ok(mut memory) = self.main_memory.try_write() {
                memory.put(key.clone(), data.clone()).await;
            }
        }

        if data_size <= MemoryLevel::L3Cache.capacity() / 10 {
            if let Ok(mut l3) = self.l3_cache.try_lock() {
                l3.put(key.clone(), data.clone()).await;
            }
        }

        true
    }

    async fn promote_to_cache(&self, key: &str, data: &[u8]) {
        if data.len() <= MemoryLevel::L3Cache.capacity() / 10 {
            if let Ok(mut l3) = self.l3_cache.try_lock() {
                l3.put(key.to_string(), data.to_vec()).await;
            }
        }
    }

    async fn promote_to_memory(&self, key: &str, data: &[u8]) {
        if let Ok(mut memory) = self.main_memory.try_write() {
            memory.put(key.to_string(), data.to_vec()).await;
        }
        self.promote_to_cache(key, data).await;
    }

    async fn promote_to_storage(&self, key: &str, data: &[u8]) {
        if let Ok(mut ssd) = self.ssd_storage.try_write() {
            ssd.put(key.to_string(), data.to_vec()).await;
        }
        self.promote_to_memory(key, data).await;
    }

    async fn record_access(&self, level: MemoryLevel, start_time: Instant, hit: bool) {
        let mut stats = self.access_stats.lock().await;
        if hit {
            stats.cache_hits += 1;
        } else {
            stats.cache_misses += 1;
        }
        stats.total_latency += start_time.elapsed();
        *stats.level_accesses.entry(level).or_insert(0) += 1;
    }

    pub async fn get_stats(&self) -> AccessStats {
        self.access_stats.lock().await.clone()
    }

    pub async fn get_performance_report(&self) -> String {
        let stats = self.get_stats().await;
        let hit_rate = if stats.total_accesses > 0 {
            stats.cache_hits as f64 / stats.total_accesses as f64 * 100.0
        } else {
            0.0
        };

        let avg_latency = if stats.total_accesses > 0 {
            stats.total_latency.as_nanos() as f64 / stats.total_accesses as f64
        } else {
            0.0
        };

        format!(
            "Memory Hierarchy Performance Report\n\
             ===================================\n\
             Total Accesses: {}\n\
             Cache Hit Rate: {:.2}%\n\
             Average Latency: {:.2} ns\n\
             \n\
             Access Distribution:\n\
             - Register: {}\n\
             - L1 Cache: {}\n\
             - L2 Cache: {}\n\
             - L3 Cache: {}\n\
             - Main Memory: {}\n\
             - SSD Storage: {}\n\
             - HDD Storage: {}\n\
             - Network Storage: {}\n\
             - Archival Storage: {}\n",
            stats.total_accesses,
            hit_rate,
            avg_latency,
            stats.level_accesses.get(&MemoryLevel::Register).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::L1Cache).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::L2Cache).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::L3Cache).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::MainMemory).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::SSD).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::HDD).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::NetworkStorage).unwrap_or(&0),
            stats.level_accesses.get(&MemoryLevel::ArchivalStorage).unwrap_or(&0),
        )
    }
}

impl Clone for AccessStats {
    fn clone(&self) -> Self {
        Self {
            total_accesses: self.total_accesses,
            cache_hits: self.cache_hits,
            cache_misses: self.cache_misses,
            total_latency: self.total_latency,
            level_accesses: self.level_accesses.clone(),
        }
    }
}
