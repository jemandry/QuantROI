
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS memory_access_stats (
    time TIMESTAMPTZ NOT NULL,
    memory_level TEXT NOT NULL,
    operation TEXT NOT NULL, -- 'get', 'put', 'evict'
    key_hash TEXT NOT NULL,
    latency_ns BIGINT NOT NULL,
    hit BOOLEAN NOT NULL,
    data_size_bytes INTEGER,
    metadata JSONB
);

SELECT create_hypertable('memory_access_stats', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_memory_access_level_time ON memory_access_stats (memory_level, time DESC);
CREATE INDEX IF NOT EXISTS idx_memory_access_operation ON memory_access_stats (operation, time DESC);
CREATE INDEX IF NOT EXISTS idx_memory_access_key_hash ON memory_access_stats (key_hash, time DESC);

CREATE TABLE IF NOT EXISTS braided_models (
    time TIMESTAMPTZ NOT NULL,
    model_id TEXT NOT NULL,
    num_strands INTEGER NOT NULL,
    time_steps INTEGER NOT NULL,
    quantization_level TEXT NOT NULL,
    sparsity REAL NOT NULL,
    pruning_strategy TEXT,
    weights_linear BYTEA,
    weights_conv BYTEA,
    metadata JSONB
);

SELECT create_hypertable('braided_models', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_braided_models_id ON braided_models (model_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_braided_models_quantization ON braided_models (quantization_level, time DESC);

CREATE TABLE IF NOT EXISTS ai_optimization_metadata (
    time TIMESTAMPTZ NOT NULL,
    model_id TEXT NOT NULL,
    optimization_type TEXT NOT NULL, -- 'quantization', 'pruning'
    original_size_bytes BIGINT NOT NULL,
    optimized_size_bytes BIGINT NOT NULL,
    accuracy_retention REAL NOT NULL,
    speedup_factor REAL NOT NULL,
    calibration_data_hash TEXT,
    metadata JSONB
);

SELECT create_hypertable('ai_optimization_metadata', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ai_optimization_model ON ai_optimization_metadata (model_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_ai_optimization_type ON ai_optimization_metadata (optimization_type, time DESC);

CREATE TABLE IF NOT EXISTS braided_path_analysis (
    time TIMESTAMPTZ NOT NULL,
    analysis_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    initial_conditions REAL[] NOT NULL,
    paths JSONB NOT NULL,
    risk_moments REAL[] NOT NULL,
    braid_invariants JSONB,
    processing_time_ms REAL NOT NULL,
    metadata JSONB
);

SELECT create_hypertable('braided_path_analysis', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_braided_analysis_id ON braided_path_analysis (analysis_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_braided_analysis_model ON braided_path_analysis (model_id, time DESC);

CREATE OR REPLACE VIEW memory_hierarchy_performance AS
SELECT 
    memory_level,
    DATE_TRUNC('minute', time) as minute,
    COUNT(*) as total_operations,
    AVG(latency_ns) as avg_latency_ns,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ns) as p95_latency_ns,
    SUM(CASE WHEN hit THEN 1 ELSE 0 END)::REAL / COUNT(*) as hit_rate,
    AVG(data_size_bytes) as avg_data_size_bytes
FROM memory_access_stats
WHERE time >= NOW() - INTERVAL '1 hour'
GROUP BY memory_level, DATE_TRUNC('minute', time)
ORDER BY minute DESC, memory_level;

CREATE OR REPLACE VIEW ai_optimization_summary AS
SELECT 
    model_id,
    optimization_type,
    DATE_TRUNC('hour', time) as hour,
    AVG(accuracy_retention) as avg_accuracy_retention,
    AVG(speedup_factor) as avg_speedup_factor,
    AVG((original_size_bytes - optimized_size_bytes)::REAL / original_size_bytes) as avg_compression_ratio
FROM ai_optimization_metadata
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY model_id, optimization_type, DATE_TRUNC('hour', time)
ORDER BY hour DESC, model_id;

SELECT add_retention_policy('memory_access_stats', INTERVAL '30 days');
SELECT add_retention_policy('braided_models', INTERVAL '90 days');
SELECT add_retention_policy('ai_optimization_metadata', INTERVAL '180 days');
SELECT add_retention_policy('braided_path_analysis', INTERVAL '60 days');

SELECT add_compression_policy('memory_access_stats', INTERVAL '7 days');
SELECT add_compression_policy('braided_models', INTERVAL '14 days');
SELECT add_compression_policy('ai_optimization_metadata', INTERVAL '30 days');
SELECT add_compression_policy('braided_path_analysis', INTERVAL '14 days');
