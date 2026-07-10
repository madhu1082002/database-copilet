-- DataOps Copilot — Databricks Database Setup
-- Run this in Databricks SQL Editor (see databricks/SETUP_GUIDE.md)
-- Free Edition uses catalog "workspace". Paid workspaces may use "main" instead.

CREATE SCHEMA IF NOT EXISTS workspace.dataops_copilot
COMMENT 'DataOps Copilot pipeline metadata for S3-D-08';

-- Table 1: Pipeline run status
CREATE TABLE IF NOT EXISTS workspace.dataops_copilot.pipeline_runs (
    pipeline_name   STRING NOT NULL,
    status          STRING NOT NULL,
    run_time        TIMESTAMP,
    duration_minutes DOUBLE,
    error_message   STRING,
    cluster_id      STRING,
    cpu_usage       DOUBLE,
    memory_usage    DOUBLE,
    dependencies    STRING,
    last_success    TIMESTAMP
)
USING DELTA
COMMENT 'Pipeline execution status — Feature 1: Pipeline Status Assistant';

-- Table 2: Failure diagnosis logs
CREATE TABLE IF NOT EXISTS workspace.dataops_copilot.failure_logs (
    pipeline_name     STRING NOT NULL,
    failure_time      TIMESTAMP,
    root_cause        STRING,
    error_details     STRING,
    cluster_logs      STRING,
    dependency_status STRING,
    suggested_actions STRING
)
USING DELTA
COMMENT 'Failure root cause data — Feature 2: Failure Diagnosis Assistant';

-- Table 3: Cluster optimization metrics
CREATE TABLE IF NOT EXISTS workspace.dataops_copilot.cluster_metrics (
    cluster_id            STRING NOT NULL,
    cluster_name          STRING,
    instance_type         STRING,
    recommended_type      STRING,
    avg_cpu_usage         DOUBLE,
    avg_memory_usage      DOUBLE,
    peak_cpu_usage        DOUBLE,
    peak_memory_usage     DOUBLE,
    monthly_cost_inr      INT,
    estimated_savings_inr INT,
    jobs_running          STRING,
    recommendation        STRING
)
USING DELTA
COMMENT 'Cluster utilization — Feature 3: Optimization Assistant';

-- Verify tables created
SHOW TABLES IN workspace.dataops_copilot;
