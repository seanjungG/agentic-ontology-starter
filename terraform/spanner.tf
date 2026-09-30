# ==============================================================================
# Cloud Spanner Graph (Opt-in when var.graph_engine is "spanner" or "both")
# & BigQuery Cloud Spanner Connection for Graph Fabric (EXTERNAL_QUERY)
# ==============================================================================

locals {
  enable_spanner = contains(["spanner", "both"], var.graph_engine)
  enable_fabric  = var.graph_engine == "both"
}

resource "google_project_service" "spanner_api" {
  project            = var.project_id
  service            = "spanner.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "bigqueryconnection_api" {
  project            = var.project_id
  service            = "bigqueryconnection.googleapis.com"
  disable_on_destroy = false
}

resource "google_spanner_instance" "starter_spanner" {
  count            = local.enable_spanner ? 1 : 0
  project          = var.project_id
  name             = var.spanner_instance_id
  config           = "regional-${var.region}"
  display_name     = "Starter Spanner Graph"
  edition          = "ENTERPRISE"
  processing_units = var.spanner_processing_units
  force_destroy    = true

  labels = {
    workload   = "agentic_ontology_starter"
    managed_by = "terraform"
    datacloud  = "jetski"
  }

  depends_on = [google_project_service.spanner_api]
}

resource "google_spanner_database" "starter_ontology_db" {
  count                    = local.enable_spanner ? 1 : 0
  project                  = var.project_id
  instance                 = google_spanner_instance.starter_spanner[0].name
  name                     = var.spanner_database_id
  version_retention_period = "1h"
  deletion_protection      = false

  ddl = [
    <<-EOT
    CREATE TABLE tb_device_master (
      device_id STRING(64) NOT NULL,
      device_name STRING(256) NOT NULL,
      manufacturer STRING(128) NOT NULL,
      storage_gb INT64 NOT NULL,
      factory_price_krw INT64 NOT NULL,
      release_date STRING(32),
      provenance STRING(64),
      source_ref STRING(256)
    ) PRIMARY KEY (device_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE tb_plan_master (
      plan_id STRING(64) NOT NULL,
      plan_name STRING(256) NOT NULL,
      tier_category STRING(64) NOT NULL,
      monthly_fee_krw INT64 NOT NULL,
      min_maintenance_days INT64 NOT NULL,
      selective_discount_rate FLOAT64 NOT NULL,
      provenance STRING(64),
      source_ref STRING(256)
    ) PRIMARY KEY (plan_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE tb_subsidy_policy (
      policy_id STRING(64) NOT NULL,
      device_id STRING(64) NOT NULL,
      plan_id STRING(64) NOT NULL,
      base_subsidy_krw INT64 NOT NULL,
      additional_subsidy_cap_krw INT64 NOT NULL,
      mandatory_retention_days INT64 NOT NULL,
      effective_from STRING(32),
      provenance STRING(64),
      source_ref STRING(256)
    ) PRIMARY KEY (policy_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE tb_customer_contract (
      customer_id STRING(64) NOT NULL,
      contract_id STRING(64) NOT NULL,
      customer_segment STRING(64) NOT NULL,
      age_group STRING(64) NOT NULL,
      device_id STRING(64) NOT NULL,
      plan_id STRING(64) NOT NULL,
      contract_type STRING(64) NOT NULL,
      commitment_months INT64 NOT NULL,
      elapsed_days INT64 NOT NULL,
      granted_subsidy_krw INT64 NOT NULL,
      welfare_status STRING(64) NOT NULL,
      status STRING(64) NOT NULL,
      provenance STRING(64),
      source_ref STRING(256)
    ) PRIMARY KEY (contract_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE tb_doc_chunks (
      chunk_id STRING(64) NOT NULL,
      source_file STRING(256) NOT NULL,
      section_title STRING(512) NOT NULL,
      content STRING(MAX) NOT NULL,
      content_sha256 STRING(128) NOT NULL,
      trust_tier STRING(64) NOT NULL,
      source_doc STRING(256),
      source_sha256 STRING(128),
      page_from INT64,
      page_to INT64,
      article_no STRING(64)
    ) PRIMARY KEY (chunk_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE tb_domain_rules (
      rule_id STRING(64) NOT NULL,
      rule_name STRING(256) NOT NULL,
      rule_category STRING(64) NOT NULL,
      condition_expr STRING(MAX) NOT NULL,
      formula_expr STRING(MAX) NOT NULL,
      source_chunk_id STRING(64) NOT NULL,
      description_ko STRING(MAX) NOT NULL,
      provenance STRING(64),
      source_ref STRING(256)
    ) PRIMARY KEY (rule_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE edge_contract_device (
      contract_id STRING(64) NOT NULL,
      customer_id STRING(64) NOT NULL,
      device_id STRING(64) NOT NULL,
      edge_type STRING(64) NOT NULL
    ) PRIMARY KEY (contract_id, device_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE edge_contract_plan (
      contract_id STRING(64) NOT NULL,
      customer_id STRING(64) NOT NULL,
      plan_id STRING(64) NOT NULL,
      edge_type STRING(64) NOT NULL
    ) PRIMARY KEY (contract_id, plan_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE edge_subsidy_binding (
      policy_id STRING(64) NOT NULL,
      device_id STRING(64) NOT NULL,
      plan_id STRING(64) NOT NULL,
      total_subsidy_krw INT64 NOT NULL,
      edge_type STRING(64) NOT NULL
    ) PRIMARY KEY (policy_id)
    EOT
    ,
    <<-EOT
    CREATE TABLE edge_rule_applies_to_plan (
      edge_id STRING(64) NOT NULL,
      rule_id STRING(64) NOT NULL,
      plan_id STRING(64) NOT NULL,
      source_chunk_id STRING(64) NOT NULL,
      relation_label_ko STRING(256) NOT NULL,
      edge_type STRING(64) NOT NULL,
      provenance STRING(64),
      source_ref STRING(256)
    ) PRIMARY KEY (edge_id)
    EOT
    ,
    <<-EOT
    CREATE OR REPLACE PROPERTY GRAPH STARTER_ONTOLOGY_GRAPH
      NODE TABLES (
        tb_customer_contract
          KEY (contract_id)
          LABEL CustomerContractNode
          PROPERTIES (contract_id, customer_id, customer_segment, age_group, device_id, plan_id, contract_type, commitment_months, elapsed_days, granted_subsidy_krw, welfare_status, status, provenance, source_ref),
        tb_device_master
          KEY (device_id)
          LABEL DeviceNode
          PROPERTIES (device_id, device_name, manufacturer, storage_gb, factory_price_krw, release_date, provenance, source_ref),
        tb_plan_master
          KEY (plan_id)
          LABEL PlanNode
          PROPERTIES (plan_id, plan_name, tier_category, monthly_fee_krw, min_maintenance_days, selective_discount_rate, provenance, source_ref),
        tb_subsidy_policy
          KEY (policy_id)
          LABEL SubsidyNode
          PROPERTIES (policy_id, device_id, plan_id, base_subsidy_krw, additional_subsidy_cap_krw, mandatory_retention_days, effective_from, provenance, source_ref),
        tb_doc_chunks
          KEY (chunk_id)
          LABEL DocChunkNode
          PROPERTIES (chunk_id, source_file, section_title, content, content_sha256, trust_tier, source_doc, source_sha256, page_from, page_to, article_no),
        tb_domain_rules
          KEY (rule_id)
          LABEL DomainRuleNode
          PROPERTIES (rule_id, rule_name, rule_category, condition_expr, formula_expr, source_chunk_id, description_ko, provenance, source_ref)
      )
      EDGE TABLES (
        edge_contract_device
          KEY (contract_id, device_id)
          SOURCE KEY (contract_id) REFERENCES tb_customer_contract (contract_id)
          DESTINATION KEY (device_id) REFERENCES tb_device_master (device_id)
          LABEL USES_DEVICE
          PROPERTIES (contract_id, customer_id, device_id, edge_type),
        edge_contract_plan
          KEY (contract_id, plan_id)
          SOURCE KEY (contract_id) REFERENCES tb_customer_contract (contract_id)
          DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
          LABEL SUBSCRIBES_PLAN
          PROPERTIES (contract_id, customer_id, plan_id, edge_type),
        edge_subsidy_binding
          KEY (policy_id)
          SOURCE KEY (device_id) REFERENCES tb_device_master (device_id)
          DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
          LABEL HAS_SUBSIDY_POLICY
          PROPERTIES (policy_id, device_id, plan_id, total_subsidy_krw, edge_type),
        edge_rule_applies_to_plan
          KEY (edge_id)
          SOURCE KEY (rule_id) REFERENCES tb_domain_rules (rule_id)
          DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
          LABEL APPLIES_TO_PLAN
          PROPERTIES (edge_id, rule_id, plan_id, source_chunk_id, relation_label_ko, edge_type, provenance, source_ref)
      )
    EOT
  ]

  lifecycle {
    ignore_changes = [ddl]
  }
}

# Grant Cloud Run Runtime SA database-level read access on Spanner Graph DB (D12)
resource "google_spanner_database_iam_member" "runtime_sa_spanner_reader" {
  count    = local.enable_spanner ? 1 : 0
  project  = var.project_id
  instance = google_spanner_instance.starter_spanner[0].name
  database = google_spanner_database.starter_ontology_db[0].name
  role     = "roles/spanner.databaseReader"
  member   = "serviceAccount:${var.runtime_service_account}"
}

# BigQuery Cloud Spanner Federated Connection for Graph Fabric (EXTERNAL_QUERY in "both" mode)
resource "google_bigquery_connection" "spanner_fabric_conn" {
  count         = local.enable_fabric ? 1 : 0
  project       = var.project_id
  location      = var.region
  connection_id = var.bq_spanner_connection_id
  friendly_name = "Starter Ontology Spanner Graph Fabric Connection"
  description   = "BigQuery EXTERNAL_QUERY federated connection to Cloud Spanner Graph (starter_ontology_db)"

  cloud_spanner {
    database = "projects/${var.project_id}/instances/${google_spanner_instance.starter_spanner[0].name}/databases/${google_spanner_database.starter_ontology_db[0].name}"
  }

  depends_on = [google_project_service.bigqueryconnection_api]
}

resource "google_bigquery_connection_iam_member" "runtime_sa_fabric_conn_user" {
  count         = local.enable_fabric ? 1 : 0
  project       = var.project_id
  location      = var.region
  connection_id = google_bigquery_connection.spanner_fabric_conn[0].connection_id
  role          = "roles/bigquery.connectionUser"
  member        = "serviceAccount:${var.runtime_service_account}"
}
