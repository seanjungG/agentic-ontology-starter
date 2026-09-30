variable "project_id" {
  description = "Target GCP Project ID for Agentic Ontology Starter"
  type        = string
  default     = "seanjung-poc"
}

variable "region" {
  description = "Default GCP Region (Seoul)"
  type        = string
  default     = "asia-northeast3"
}

variable "bigquery_dataset_id" {
  description = "BigQuery Dataset ID for Starter Structured DW & Ontology Property Graph"
  type        = string
  default     = "starter_ontology_dw"
}

variable "gcs_bucket_name" {
  description = "Cloud Storage Bucket for 3-Layer OKF Wiki (raw/, parsed/, ontology/)"
  type        = string
  default     = "seanjung-poc-starter-ontology"
}

variable "runtime_service_account" {
  description = "Cloud Run runtime service account email"
  type        = string
  default     = "924723860007-compute@developer.gserviceaccount.com"
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name for the studio portal"
  type        = string
  default     = "agentic-ontology-starter"
}

variable "container_image" {
  description = "Studio container image built by Cloud Build"
  type        = string
  default     = "asia-northeast3-docker.pkg.dev/seanjung-poc/cloud-run-source-deploy/agentic-ontology-starter:grill010-v2"
}

variable "gemini_model" {
  description = "Vertex AI Gemini model used by the agent (VERTEX_GEMINI_MODEL)"
  type        = string
  default     = "gemini-3.8-flash"
}

variable "graph_engine" {
  description = "Graph engine selection ('bigquery', 'spanner', or 'both'). Sample default is 'both' to provision BigQuery Property Graph, Cloud Spanner Graph, and Graph Fabric connection."
  type        = string
  default     = "both"
  validation {
    condition     = contains(["bigquery", "spanner", "both"], var.graph_engine)
    error_message = "graph_engine must be one of: bigquery, spanner, both."
  }
}

variable "spanner_instance_id" {
  description = "Cloud Spanner instance ID for Online Graph Traversal (provisioned when graph_engine is 'spanner' or 'both')"
  type        = string
  default     = "starter-spanner"
}

variable "spanner_database_id" {
  description = "Cloud Spanner database ID for Starter Ontology Property Graph"
  type        = string
  default     = "starter_ontology_db"
}

variable "spanner_processing_units" {
  description = "Minimum Cloud Spanner processing units (100 PU = 0.1 node, Enterprise edition for Spanner Graph)"
  type        = number
  default     = 100
}

variable "bq_spanner_connection_id" {
  description = "BigQuery Cloud Spanner connection ID for EXTERNAL_QUERY Graph Fabric federation (when graph_engine is 'both')"
  type        = string
  default     = "spanner_fabric_conn"
}

