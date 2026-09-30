# Studio portal (src/web/studio_server.py) on Cloud Run.
# The container image is built separately with Cloud Build and passed in, e.g.
#   TF_VAR_container_image=asia-northeast3-docker.pkg.dev/<project>/cloud-run-source-deploy/agentic-ontology-starter:<tag> \
#   python3 terraform/apply_terraform.py
resource "google_cloud_run_v2_service" "studio" {
  name     = var.cloud_run_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = var.runtime_service_account

    scaling {
      max_instance_count = 3
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true # keep request-based CPU allocation (must be explicit when resources is set)
        startup_cpu_boost = true
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "BQ_DATASET_ID"
        value = google_bigquery_dataset.starter_ontology_dw.dataset_id
      }
      env {
        name  = "BQ_LOCATION"
        value = var.region
      }
      env {
        name  = "GCS_WIKI_BUCKET"
        value = google_storage_bucket.starter_ontology_wiki.name
      }
      env {
        name  = "VERTEX_GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "GRAPH_ENGINE_MODE"
        value = var.graph_engine
      }
      env {
        name  = "SPANNER_INSTANCE_ID"
        value = local.enable_spanner ? google_spanner_instance.starter_spanner[0].name : ""
      }
      env {
        name  = "SPANNER_DATABASE_ID"
        value = local.enable_spanner ? google_spanner_database.starter_ontology_db[0].name : ""
      }
      env {
        name  = "BQ_SPANNER_CONNECTION_ID"
        value = local.enable_fabric ? google_bigquery_connection.spanner_fabric_conn[0].connection_id : ""
      }
    }
  }

  labels = {
    workload   = "agentic_ontology_starter"
    managed_by = "terraform"
    datacloud  = "jetski"
  }
}

resource "google_cloud_run_v2_service_iam_member" "studio_public_invoker" {
  name     = google_cloud_run_v2_service.studio.name
  location = google_cloud_run_v2_service.studio.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
