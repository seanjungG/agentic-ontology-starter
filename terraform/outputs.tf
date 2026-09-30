output "project_id" {
  description = "Provisioned GCP Project ID"
  value       = var.project_id
}

output "bigquery_dataset_id" {
  description = "Provisioned BigQuery Dataset ID"
  value       = google_bigquery_dataset.starter_ontology_dw.dataset_id
}

output "gcs_bucket_name" {
  description = "Provisioned GCS Wiki Bucket Name"
  value       = google_storage_bucket.starter_ontology_wiki.name
}

output "provisioned_tables" {
  description = "List of 10 provisioned BigQuery physical tables"
  value = [
    google_bigquery_table.tb_device_master.table_id,
    google_bigquery_table.tb_plan_master.table_id,
    google_bigquery_table.tb_subsidy_policy.table_id,
    google_bigquery_table.tb_customer_contract.table_id,
    google_bigquery_table.tb_doc_chunks.table_id,
    google_bigquery_table.tb_domain_rules.table_id,
    google_bigquery_table.edge_contract_device.table_id,
    google_bigquery_table.edge_contract_plan.table_id,
    google_bigquery_table.edge_subsidy_binding.table_id,
    google_bigquery_table.edge_rule_applies_to_plan.table_id,
  ]
}

output "cloud_run_url" {
  description = "Studio portal URL (Cloud Run)"
  value       = google_cloud_run_v2_service.studio.uri
}

output "graph_engine_mode" {
  description = "Configured Graph Engine Mode (bigquery | spanner | both)"
  value       = var.graph_engine
}

output "spanner_instance_id" {
  description = "Provisioned Cloud Spanner Instance ID (null when graph_engine == 'bigquery')"
  value       = local.enable_spanner ? google_spanner_instance.starter_spanner[0].name : null
}

output "spanner_database_id" {
  description = "Provisioned Cloud Spanner Database ID (null when graph_engine == 'bigquery')"
  value       = local.enable_spanner ? google_spanner_database.starter_ontology_db[0].name : null
}

output "bq_spanner_connection_id" {
  description = "BigQuery Cloud Spanner Connection ID for EXTERNAL_QUERY (null unless graph_engine == 'both')"
  value       = local.enable_fabric ? google_bigquery_connection.spanner_fabric_conn[0].name : null
}

