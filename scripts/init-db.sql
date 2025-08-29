
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE SCHEMA IF NOT EXISTS causal_analysis;
CREATE SCHEMA IF NOT EXISTS audit_logs;
CREATE SCHEMA IF NOT EXISTS performance_metrics;
CREATE SCHEMA IF NOT EXISTS benchmark_validation;

CREATE TABLE IF NOT EXISTS causal_analysis.ladder_escalations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal_id VARCHAR(255) NOT NULL,
    from_rung INTEGER NOT NULL CHECK (from_rung IN (1, 2, 3)),
    to_rung INTEGER NOT NULL CHECK (to_rung IN (1, 2, 3)),
    escalation_reason TEXT,
    correlation_score DECIMAL(5,4),
    p_value DECIMAL(10,8),
    confidence_interval_lower DECIMAL(10,6),
    confidence_interval_upper DECIMAL(10,6),
    effect_estimate DECIMAL(10,6),
    latency_ns BIGINT,
    audit_hash VARCHAR(64)
);

SELECT create_hypertable('causal_analysis.ladder_escalations', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ladder_escalations_signal_id ON causal_analysis.ladder_escalations (signal_id);
CREATE INDEX IF NOT EXISTS idx_ladder_escalations_rung ON causal_analysis.ladder_escalations (from_rung, to_rung);
CREATE INDEX IF NOT EXISTS idx_ladder_escalations_timestamp ON causal_analysis.ladder_escalations (timestamp DESC);

CREATE TABLE IF NOT EXISTS benchmark_validation.validation_results (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validation_id VARCHAR(255) NOT NULL,
    internal_effect DECIMAL(10,6),
    external_effect DECIMAL(10,6),
    data_source VARCHAR(100),
    confidence_score DECIMAL(5,4),
    validation_passed BOOLEAN,
    latency_ns BIGINT,
    gdpr_compliant BOOLEAN DEFAULT TRUE,
    audit_hash VARCHAR(64)
);

SELECT create_hypertable('benchmark_validation.validation_results', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_validation_results_validation_id ON benchmark_validation.validation_results (validation_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_source ON benchmark_validation.validation_results (data_source);
CREATE INDEX IF NOT EXISTS idx_validation_results_timestamp ON benchmark_validation.validation_results (timestamp DESC);

CREATE TABLE IF NOT EXISTS performance_metrics.latency_measurements (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service_name VARCHAR(100) NOT NULL,
    operation_name VARCHAR(100) NOT NULL,
    latency_ns BIGINT NOT NULL,
    rung_level INTEGER CHECK (rung_level IN (1, 2, 3)),
    target_latency_ns BIGINT,
    performance_target_met BOOLEAN,
    concurrent_requests INTEGER DEFAULT 1,
    memory_usage_mb DECIMAL(10,2),
    cpu_usage_percent DECIMAL(5,2)
);

SELECT create_hypertable('performance_metrics.latency_measurements', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_latency_measurements_service ON performance_metrics.latency_measurements (service_name, operation_name);
CREATE INDEX IF NOT EXISTS idx_latency_measurements_rung ON performance_metrics.latency_measurements (rung_level);
CREATE INDEX IF NOT EXISTS idx_latency_measurements_timestamp ON performance_metrics.latency_measurements (timestamp DESC);

CREATE TABLE IF NOT EXISTS audit_logs.causal_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    input_data_hash VARCHAR(64),
    output_data_hash VARCHAR(64),
    ipfs_hash VARCHAR(64),
    solana_transaction_id VARCHAR(88),
    decision_metadata JSONB,
    immutable_proof BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable('audit_logs.causal_decisions', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_causal_decisions_decision_id ON audit_logs.causal_decisions (decision_id);
CREATE INDEX IF NOT EXISTS idx_causal_decisions_service ON audit_logs.causal_decisions (service_name);
CREATE INDEX IF NOT EXISTS idx_causal_decisions_ipfs ON audit_logs.causal_decisions (ipfs_hash);
CREATE INDEX IF NOT EXISTS idx_causal_decisions_solana ON audit_logs.causal_decisions (solana_transaction_id);
CREATE INDEX IF NOT EXISTS idx_causal_decisions_timestamp ON audit_logs.causal_decisions (timestamp DESC);

CREATE TABLE IF NOT EXISTS causal_analysis.kafka_routing_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal_id VARCHAR(255) NOT NULL,
    routing_path VARCHAR(50) NOT NULL CHECK (routing_path IN ('hot', 'warm', 'cold')),
    signal_priority INTEGER CHECK (signal_priority BETWEEN 1 AND 10),
    latency_requirement_ns BIGINT,
    actual_latency_ns BIGINT,
    kafka_topic VARCHAR(255),
    kafka_partition INTEGER,
    processing_successful BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

SELECT create_hypertable('causal_analysis.kafka_routing_decisions', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_kafka_routing_signal_id ON causal_analysis.kafka_routing_decisions (signal_id);
CREATE INDEX IF NOT EXISTS idx_kafka_routing_path ON causal_analysis.kafka_routing_decisions (routing_path);
CREATE INDEX IF NOT EXISTS idx_kafka_routing_timestamp ON causal_analysis.kafka_routing_decisions (timestamp DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS performance_metrics.rung_performance_summary AS
SELECT 
    rung_level,
    service_name,
    DATE_TRUNC('minute', timestamp) as minute_bucket,
    COUNT(*) as request_count,
    AVG(latency_ns) as avg_latency_ns,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ns) as median_latency_ns,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ns) as p95_latency_ns,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ns) as p99_latency_ns,
    SUM(CASE WHEN performance_target_met THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) as target_success_rate
FROM performance_metrics.latency_measurements
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY rung_level, service_name, DATE_TRUNC('minute', timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rung_performance_summary_unique 
ON performance_metrics.rung_performance_summary (rung_level, service_name, minute_bucket);


DO $$
DECLARE
    app_user TEXT := COALESCE(current_setting('app.user_name', true), current_user);
BEGIN
    EXECUTE format('GRANT USAGE ON SCHEMA causal_analysis TO %I', app_user);
    EXECUTE format('GRANT USAGE ON SCHEMA audit_logs TO %I', app_user);
    EXECUTE format('GRANT USAGE ON SCHEMA performance_metrics TO %I', app_user);
    EXECUTE format('GRANT USAGE ON SCHEMA benchmark_validation TO %I', app_user);

    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA causal_analysis TO %I', app_user);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA audit_logs TO %I', app_user);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA performance_metrics TO %I', app_user);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA benchmark_validation TO %I', app_user);

    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA causal_analysis TO %I', app_user);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit_logs TO %I', app_user);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA performance_metrics TO %I', app_user);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA benchmark_validation TO %I', app_user);
END $$;

INSERT INTO performance_metrics.latency_measurements (
    service_name, operation_name, latency_ns, rung_level, target_latency_ns, performance_target_met
) VALUES 
    ('ladder-escalator', 'rung1_association', 50000, 1, 50000, TRUE),
    ('ladder-escalator', 'rung2_intervention', 500000000, 2, 500000000, TRUE),
    ('ladder-escalator', 'rung3_counterfactual', 10000000000, 3, 10000000000, TRUE),
    ('benchmark-validator', 'external_validation', 30000000, NULL, 30000000, TRUE),
    ('kafka-router', 'hot_path_routing', 75000, NULL, 100000, TRUE)
ON CONFLICT DO NOTHING;

COMMIT;
