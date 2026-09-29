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
  default     = "asia-northeast3-docker.pkg.dev/seanjung-poc/cloud-run-source-deploy/agentic-ontology-starter:goal147-fcb798f"
}

variable "gemini_model" {
  description = "Vertex AI Gemini model used by the agent (VERTEX_GEMINI_MODEL)"
  type        = string
  default     = "gemini-3.8-flash"
}
