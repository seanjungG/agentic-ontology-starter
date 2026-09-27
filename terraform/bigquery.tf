# ==============================================================================
# BigQuery Structured DW, Unstructured OKF Rules/Chunks & Graph Edge Tables
# ==============================================================================

# 1. Device Master (tb_device_master)
resource "google_bigquery_table" "tb_device_master" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "tb_device_master"
  description         = "단말기 출고가 마스터 원장 (Stage 1 Structured DW)"
  deletion_protection = false

  schema = jsonencode([
    { name = "device_id",         type = "STRING",  mode = "REQUIRED", description = "단말기 고유 ID (PK)" },
    { name = "device_name",       type = "STRING",  mode = "REQUIRED", description = "단말기 모델명" },
    { name = "manufacturer",      type = "STRING",  mode = "REQUIRED", description = "제조사" },
    { name = "storage_gb",        type = "INTEGER", mode = "REQUIRED", description = "내장 메모리 용량 (GB)" },
    { name = "factory_price_krw", type = "INTEGER", mode = "REQUIRED", description = "출고가 (KRW)" },
    { name = "release_date",      type = "STRING",  mode = "NULLABLE", description = "출시일 (YYYY-MM-DD)" }
  ])
}

# 2. Plan Master (tb_plan_master)
resource "google_bigquery_table" "tb_plan_master" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "tb_plan_master"
  description         = "모바일 요금제 마스터 원장 (Stage 1 Structured DW)"
  deletion_protection = false

  schema = jsonencode([
    { name = "plan_id",                 type = "STRING",  mode = "REQUIRED", description = "요금제 고유 ID (PK)" },
    { name = "plan_name",               type = "STRING",  mode = "REQUIRED", description = "요금제 공식 명칭" },
    { name = "tier_category",           type = "STRING",  mode = "REQUIRED", description = "요금제 등급 분류 (5G_HIGH, 5G_MID, 5G_LOW, 5G_WELFARE)" },
    { name = "monthly_fee_krw",         type = "INTEGER", mode = "REQUIRED", description = "월정액 요금 (KRW)" },
    { name = "min_maintenance_days",    type = "INTEGER", mode = "REQUIRED", description = "공시지원금 의무 유지 일수 (180일 등)" },
    { name = "selective_discount_rate", type = "FLOAT",   mode = "REQUIRED", description = "선택약정 요금할인율 (0.25)" }
  ])
}

# 3. Subsidy Policy Master (tb_subsidy_policy)
resource "google_bigquery_table" "tb_subsidy_policy" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "tb_subsidy_policy"
  description         = "단말기×요금제별 공시지원금 및 유통망 추가지원금 정책 원장"
  deletion_protection = false

  schema = jsonencode([
    { name = "policy_id",                  type = "STRING",  mode = "REQUIRED", description = "지원금 정책 ID (PK)" },
    { name = "device_id",                  type = "STRING",  mode = "REQUIRED", description = "단말기 ID (FK)" },
    { name = "plan_id",                    type = "STRING",  mode = "REQUIRED", description = "요금제 ID (FK)" },
    { name = "base_subsidy_krw",           type = "INTEGER", mode = "REQUIRED", description = "공시지원금 (KRW)" },
    { name = "additional_subsidy_cap_krw", type = "INTEGER", mode = "REQUIRED", description = "유통망 추가지원금 상한 (공시지원금의 15%, KRW)" },
    { name = "mandatory_retention_days",   type = "INTEGER", mode = "REQUIRED", description = "최소 의무 유지기간 (180일)" },
    { name = "effective_from",             type = "STRING",  mode = "NULLABLE", description = "시행 기준일" }
  ])
}

# 4. Customer Contract Ledger (tb_customer_contract)
resource "google_bigquery_table" "tb_customer_contract" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "tb_customer_contract"
  description         = "비식별화 고객 약정 원장 (Stage 1 Structured DW)"
  deletion_protection = false

  schema = jsonencode([
    { name = "customer_id",         type = "STRING",  mode = "REQUIRED", description = "비식별화 고객 ID (PK)" },
    { name = "contract_id",         type = "STRING",  mode = "REQUIRED", description = "약정 계약 ID" },
    { name = "customer_segment",    type = "STRING",  mode = "REQUIRED", description = "고객 세그먼트" },
    { name = "age_group",           type = "STRING",  mode = "REQUIRED", description = "연령대" },
    { name = "device_id",           type = "STRING",  mode = "REQUIRED", description = "개통 단말기 ID (FK)" },
    { name = "plan_id",             type = "STRING",  mode = "REQUIRED", description = "가입 요금제 ID (FK)" },
    { name = "contract_type",       type = "STRING",  mode = "REQUIRED", description = "약정 유형 (PUBLIC_SUBSIDY / SELECTIVE_DISCOUNT_25)" },
    { name = "commitment_months",   type = "INTEGER", mode = "REQUIRED", description = "약정 기간 (개월)" },
    { name = "elapsed_days",        type = "INTEGER", mode = "REQUIRED", description = "개통 후 경과일수" },
    { name = "granted_subsidy_krw", type = "INTEGER", mode = "REQUIRED", description = "지급받은 총 지원금 (KRW)" },
    { name = "welfare_status",      type = "STRING",  mode = "REQUIRED", description = "복지 감면/특례 자격" },
    { name = "status",              type = "STRING",  mode = "REQUIRED", description = "회선 상태" }
  ])
}

# 5. Unstructured OKF Document Chunks (tb_doc_chunks)
resource "google_bigquery_table" "tb_doc_chunks" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "tb_doc_chunks"
  description         = "3-Layer OKF 비정형 정책 가이드 청크 및 SHA-256 해시 앵커 (Stage 2)"
  deletion_protection = false

  schema = jsonencode([
    { name = "chunk_id",       type = "STRING", mode = "REQUIRED", description = "문서 청크 ID (PK)" },
    { name = "source_file",    type = "STRING", mode = "REQUIRED", description = "원천 가이드 파일명" },
    { name = "section_title",  type = "STRING", mode = "REQUIRED", description = "섹션 제목" },
    { name = "content",        type = "STRING", mode = "REQUIRED", description = "청크 원문 텍스트" },
    { name = "content_sha256", type = "STRING", mode = "REQUIRED", description = "SHA-256 무결성 해시 앵커" },
    { name = "trust_tier",     type = "STRING", mode = "REQUIRED", description = "신뢰 등급 (GOLDEN_VERIFIED)" }
  ])
}

# 6. Unstructured Domain Rules (tb_domain_rules)
resource "google_bigquery_table" "tb_domain_rules" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "tb_domain_rules"
  description         = "비정형 가이드에서 추출된 비즈니스 판정 규칙 및 산식 노드 (Stage 2 & 3)"
  deletion_protection = false

  schema = jsonencode([
    { name = "rule_id",         type = "STRING", mode = "REQUIRED", description = "비즈니스 규칙 ID (PK)" },
    { name = "rule_name",       type = "STRING", mode = "REQUIRED", description = "비즈니스 규칙 한글명" },
    { name = "rule_category",   type = "STRING", mode = "REQUIRED", description = "규칙 분류 (SUBSIDY_CAP, PENALTY_180D, TCO_24M, WELFARE_EXEMPT)" },
    { name = "condition_expr",  type = "STRING", mode = "REQUIRED", description = "조건 논리식" },
    { name = "formula_expr",    type = "STRING", mode = "REQUIRED", description = "산출 수식" },
    { name = "source_chunk_id", type = "STRING", mode = "REQUIRED", description = "근거 청크 ID (FK)" },
    { name = "description_ko",  type = "STRING", mode = "REQUIRED", description = "규칙 상세 설명" }
  ])
}

# 7. Graph Edge: Customer Contract -> Device (edge_contract_device)
resource "google_bigquery_table" "edge_contract_device" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "edge_contract_device"
  description         = "고객 약정 -> 개통 단말기 관계 엣지 테이블"
  deletion_protection = false

  schema = jsonencode([
    { name = "contract_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "device_id",   type = "STRING", mode = "REQUIRED" },
    { name = "edge_type",   type = "STRING", mode = "REQUIRED" }
  ])
}

# 8. Graph Edge: Customer Contract -> Plan (edge_contract_plan)
resource "google_bigquery_table" "edge_contract_plan" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "edge_contract_plan"
  description         = "고객 약정 -> 가입 요금제 관계 엣지 테이블"
  deletion_protection = false

  schema = jsonencode([
    { name = "contract_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "plan_id",     type = "STRING", mode = "REQUIRED" },
    { name = "edge_type",   type = "STRING", mode = "REQUIRED" }
  ])
}

# 9. Graph Edge: Device -> Plan via Subsidy Policy (edge_subsidy_binding)
resource "google_bigquery_table" "edge_subsidy_binding" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "edge_subsidy_binding"
  description         = "단말기 -> 요금제 지원금 정책 결합 엣지 테이블"
  deletion_protection = false

  schema = jsonencode([
    { name = "policy_id",         type = "STRING",  mode = "REQUIRED" },
    { name = "device_id",         type = "STRING",  mode = "REQUIRED" },
    { name = "plan_id",           type = "STRING",  mode = "REQUIRED" },
    { name = "total_subsidy_krw", type = "INTEGER", mode = "REQUIRED" },
    { name = "edge_type",         type = "STRING",  mode = "REQUIRED" }
  ])
}

# 10. Graph Edge: Domain Rule -> Plan Semantic Bridge (edge_rule_applies_to_plan)
resource "google_bigquery_table" "edge_rule_applies_to_plan" {
  dataset_id          = google_bigquery_dataset.starter_ontology_dw.dataset_id
  table_id            = "edge_rule_applies_to_plan"
  description         = "비정형 비즈니스 규칙(DomainRule) -> 정형 요금제(Plan) 시맨틱 브릿지 엣지 테이블"
  deletion_protection = false

  schema = jsonencode([
    { name = "edge_id",           type = "STRING", mode = "REQUIRED" },
    { name = "rule_id",           type = "STRING", mode = "REQUIRED" },
    { name = "plan_id",           type = "STRING", mode = "REQUIRED" },
    { name = "source_chunk_id",   type = "STRING", mode = "REQUIRED" },
    { name = "relation_label_ko", type = "STRING", mode = "REQUIRED" },
    { name = "edge_type",         type = "STRING", mode = "REQUIRED" }
  ])
}
