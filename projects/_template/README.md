# 프로젝트 템플릿 (`projects/_template/`)

고객별 또는 고객 데이터 영역별로 프로젝트를 나눌 때 쓰는 폴더 템플릿입니다. 기본 샘플(저장소 루트)은 그대로 두고, 새 고객 데이터는 `projects/<id>/`에 넣습니다.

## 1. 프로젝트 추가

```bash
python3 new_project.py acme-claims --name "Acme 보험금 심사" --customer "Acme" --domain "보험금 청구·심사"
python3 -m src.web.studio_server        # http://127.0.0.1:8080/?project=acme-claims
python3 run_pipeline.py --project acme-claims
```

- `projects/acme-claims/`가 생성되고 스튜디오 상단 `PROJECT` 선택기에 나타납니다. 폴더를 스캔하므로 별도 등록 파일이 없습니다.
- 기본 GCP 리소스 이름: 데이터셋 `acme_claims_dw`, 버킷 `<GCP 프로젝트>-acme-claims`. Terraform으로 먼저 생성합니다. 생성 전에는 MCP 호출 결과가 `BQ_QUERY_ERROR`로 표시됩니다.
- `projects/*`는 `.gitignore` 대상입니다(`_template` 제외). 고객 데이터가 공개 저장소에 올라가지 않도록 기본 차단합니다.

## 2. 폴더 구성 (루트 샘플과 같은 구조)

| 경로 | 내용 |
| :--- | :--- |
| `project.json` | 이름·고객·도메인·트랙(`auto`)·그래프 엔진·GCP(`project_id`, `dataset_id`, `gcs_bucket`), `tables`(고객 테이블 CSV 목록), `synthetic.allowed`(기본 `false`), 선택 항목 `*_module` (아래) |
| `customer_doc/` | 고객 원본 문서(PDF·DOCX·MD·TXT). `pipeline/extract_docs.py`가 `data/input/01_guides/`에 원문 변환본을 만든다 |
| `config/portal_profile.json`, `config/eval_rubric.json` | 샘플에서 복사됨. 도메인에 맞게 수정 |
| `config/lineage_spec.json` | Stage 5 리니지 스펙 (3절) |
| `data/input/01_guides` · `03_tables` · `04_cq` · `05_glossary` | 원문 변환본(직접 쓰지 않음) · 고객이 준 CSV(행마다 `provenance`·`source_ref`) · Golden CQ/바운더리 질의(`evidence_type` sql 또는 citation) · 용어집 |
| `data/output`, `data/llm_wiki` | 파이프라인 산출물 (`input_manifest.json`, `gate0_report.json` 포함) |

`tables`가 비어 있으면 트랙은 lite로 정해지고 테이블 없이 문서만 적재합니다. 고객이 주지 않은 테이블은 만들지 않습니다(`AGENTS.md` 고객 데이터 원칙).

도메인 스키마가 샘플과 다르면 공용 코드(`pipeline/`, `src/agent/`)를 고치지 말고, 공용 파일을 이 폴더에 복사해 수정한 뒤 `project.json`에 경로(프로젝트 폴더 기준)를 적습니다. 서버 코드에 프로젝트별 `if` 분기를 추가하지 않습니다.

| 키 | 복사 원본 | 노출해야 할 이름 |
| :--- | :--- | :--- |
| `mcp_module` | `src/agent/mcp_server.py` | 클래스 `DomainMcpServer` |
| `engine_module` | `src/agent/reasoning_engine.py` | 클래스 `AiFdeAgentEngine` |
| `ingest_module` / `graph_module` / `validator_module` | `pipeline/ingest.py` / `graph_builder.py` / `validator.py` | 함수 `run_ingest` / `build_graph` / `run_validation` |

- 복사한 파이프라인은 데이터 경로를 환경변수 `STARTER_PROJECT_ROOT`(= 이 폴더, `run_pipeline.py --project`가 설정) 기준으로 읽습니다.
- Stage 5 KPI는 stage3 MCP의 `duplicate_keys_total`(숫자)을 읽습니다. 반환하지 않으면 `N/A`로 표시됩니다.

## 3. 리니지 스펙 (`config/lineage_spec.json`)

메인 스튜디오 리니지와 같은 7개 카테고리 열(PII 열은 기본 숨김)에 노드와 엣지를 채웁니다. 작성 예시는 루트의 `config/lineage_spec.json`입니다.

| 노드 필드 | 필수 | 설명 |
| :--- | :---: | :--- |
| `id` | O | 고유 ID (예: `RAW_TB_ORDERS`) |
| `cat` | O | 카테고리 ID |
| `title` / `title_en` | O / - | 카드 제목 |
| `resource` | - | 물리 위치. `{fq}` `{project_id}` `{dataset_id}` `{bucket}` `{model}` 치환 |
| `bq_table` | - | 지정하면 BigQuery `__TABLES__` 실측 행 수를 볼륨으로 표시 |
| `volume` / `volume_en` | - | `bq_table`이 없을 때 표시할 값. 추정 수치는 적지 않음 |
| `desc` / `desc_en` | - | 상세 패널 설명 |
| `x`, `y` | - | 생략하면 카테고리 열 기준 자동 배치 |

- 엣지: `{"source": "<id>", "target": "<id>", "label": "<관계>"}`. 왼쪽에서 오른쪽으로 흐르게 하고 같은 열 안의 엣지는 피합니다.
- PII 열을 숨기면 해당 노드를 거치는 엣지는 상류에서 하류로 바로 이어서 표시됩니다.
