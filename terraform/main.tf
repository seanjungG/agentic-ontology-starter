terraform {
  required_version = ">= 1.5.0"
  backend "gcs" {
    bucket = "seanjung-poc-agent"
    prefix = "terraform/agentic_ontology_starter"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "starter_ontology_wiki" {
  name                        = var.gcs_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  labels = {
    workload   = "agentic_ontology_starter"
    managed_by = "terraform"
    datacloud  = "jetski"
  }
}

resource "google_bigquery_dataset" "starter_ontology_dw" {
  dataset_id                 = var.bigquery_dataset_id
  friendly_name              = "Agentic Ontology Starter DW & Property Graph Dataset"
  description                = "De-identified enterprise telecom structured DW tables, 3-Layer OKF ontology rules/chunks, and SQL:2023 Property Graph (STARTER_ONTOLOGY_GRAPH)"
  location                   = var.region
  delete_contents_on_destroy = true

  labels = {
    workload   = "agentic_ontology_starter"
    managed_by = "terraform"
    datacloud  = "jetski"
  }
}

resource "google_bigquery_dataset_iam_member" "runtime_sa_bq_editor" {
  dataset_id = google_bigquery_dataset.starter_ontology_dw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.runtime_service_account}"
}

resource "google_storage_bucket_iam_member" "runtime_sa_gcs_viewer" {
  bucket = google_storage_bucket.starter_ontology_wiki.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.runtime_service_account}"
}
