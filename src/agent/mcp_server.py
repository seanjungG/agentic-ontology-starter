# -*- coding: utf-8 -*-
"""
Domain & Stage Pipeline MCP Server (Starter v2.0 - Live GCP).
Every tool executes real BigQuery SQL / SQL:2023 GRAPH_TABLE queries against
`seanjung-poc.starter_ontology_dw` (schema: terraform/bigquery.tf) and GCS.
- No hardcoded answers. Parameter values are validated against the live BigQuery catalog.
- BigQuery failures are returned as `BQ_QUERY_ERROR` (never as 0 rows).
"""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from src.gcp_client import (
    DEFAULT_DATASET_ID,
    DEFAULT_GCS_BUCKET,
    DEFAULT_PROJECT_ID,
    execute_bq_sql,
    list_gcs_objects,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CATALOG_TTL_SEC = 300


class BqQueryError(Exception):
    def __init__(self, res: Dict[str, Any]):
        super().__init__(res.get("error", "BigQuery error"))
        self.res = res


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(s or "").lower())


def _lit(s: str) -> str:
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


class DomainMcpServer:
    def __init__(self, project_id: str = DEFAULT_PROJECT_ID, dataset_id: str = DEFAULT_DATASET_ID,
                 gcs_bucket: str = DEFAULT_GCS_BUCKET, **_ignored):
        self.project_id = project_id
        self.gcs_bucket = gcs_bucket
        self.fq = f"{project_id}.{dataset_id}"
        self.graph = f"{self.fq}.STARTER_ONTOLOGY_GRAPH"
        self._catalog: Optional[Dict[str, Any]] = None
        self._catalog_at = 0.0

    # ------------------------------------------------------------------ helpers
    def _run(self, sql: str, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        res = execute_bq_sql(sql, project_id=self.project_id)
        jobs.append({"job_id": res.get("job_id"), "status": res.get("status"),
                     "elapsed_ms": res.get("elapsed_ms"), "rows": len(res.get("rows", [])),
                     "sql": " ".join(sql.split())})
        if res.get("status") != "SUCCESS":
            raise BqQueryError(res)
        return res.get("rows", [])

    def get_live_catalog(self, force: bool = False) -> Dict[str, Any]:
        """Device / plan / customer catalog read live from BigQuery (cached for 5 minutes)."""
        if self._catalog and not force and time.time() - self._catalog_at < CATALOG_TTL_SEC:
            return self._catalog
        jobs: List[Dict[str, Any]] = []
        rows = self._run(f"""
            SELECT 'device' AS kind, device_id AS id, device_name AS name, factory_price_krw AS amount, storage_gb AS extra
            FROM `{self.fq}.tb_device_master`
            UNION ALL
            SELECT 'plan', plan_id, plan_name, monthly_fee_krw, min_maintenance_days FROM `{self.fq}.tb_plan_master`
            UNION ALL
            SELECT 'customer', customer_id, customer_segment, elapsed_days, NULL FROM `{self.fq}.tb_customer_contract`
            ORDER BY kind, amount DESC""", jobs)
        self._catalog = {
            "devices": [r for r in rows if r["kind"] == "device"],
            "plans": [r for r in rows if r["kind"] == "plan"],
            "customers": [r for r in rows if r["kind"] == "customer"],
            "job_id": jobs[0]["job_id"],
        }
        self._catalog_at = time.time()
        return self._catalog

    def extract_params_from_text(self, text: str) -> Dict[str, Any]:
        """Deterministic extraction: literal numbers from text + exact catalog-name matches (no alias dictionary)."""
        cat = self.get_live_catalog()
        q, nq = str(text or ""), _norm(text)
        cust_ids = {c["id"] for c in cat["customers"]}
        customer_id = next((c for c in re.findall(r"CUST_[A-Z]+_\d{3}", q.upper()) if c in cust_ids), None)

        device_name = None
        dev_hits = [d["name"] for d in cat["devices"] if _norm(d["name"]) in nq]
        if dev_hits:
            device_name = max(dev_hits, key=len)

        plan_hits = []
        for p in cat["plans"]:
            keys = {_norm(p["name"]), _norm(re.sub(r"\(.*?\)", "", p["name"]))}
            pos = min((nq.find(k) for k in keys if k and nq.find(k) >= 0), default=-1)
            if pos >= 0:
                plan_hits.append((pos, p["name"]))
        plan_hits.sort()

        fees = [int(m.replace(",", "")) for m in re.findall(r"(\d{1,3}(?:,\d{3})+|\d{4,7})\s*(?:원|krw)", q, re.I)]
        days = [int(m) for m in re.findall(r"(\d{1,4})\s*일", q)]
        windows = {p["extra"] for p in cat["plans"] if p.get("extra")}  # live min_maintenance_days
        storage = re.findall(r"(\d{3,4})\s*gb", q, re.I)
        return {
            "customer_id": customer_id,
            "device_name": device_name,
            "storage_gb": int(storage[0]) if storage else None,
            "plan_name": plan_hits[0][1] if plan_hits else None,
            "target_plan_name": plan_hits[-1][1] if len(plan_hits) > 1 else None,
            "literal_fees_krw": fees,
            "literal_days": days,
            "elapsed_day_candidates": [d for d in days if d not in windows],
        }

    def resolve_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Uses structured args when provided; otherwise falls back to deterministic text extraction."""
        keys = ("customer_id", "device_name", "storage_gb", "plan_name", "monthly_fee_krw",
                "target_plan_name", "target_monthly_fee_krw", "elapsed_days")
        p = {k: args.get(k) for k in keys}
        if args.get("query") and not any(p.values()):
            det = self.extract_params_from_text(args["query"])
            fees, days = det["literal_fees_krw"], det["elapsed_day_candidates"]
            p.update({k: det[k] for k in ("customer_id", "device_name", "storage_gb", "plan_name", "target_plan_name")})
            if det["customer_id"]:
                p["target_monthly_fee_krw"] = fees[-1] if fees else None
            else:
                p["monthly_fee_krw"] = fees[0] if fees else None
                p["target_monthly_fee_krw"] = fees[1] if len(fees) > 1 else None
            p["elapsed_days"] = days[0] if days else None
        cat = self.get_live_catalog()
        if p["device_name"] and p["device_name"] not in {d["name"] for d in cat["devices"]}:
            p["device_name"] = None
        plan_names = {x["name"] for x in cat["plans"]}
        for k in ("plan_name", "target_plan_name"):
            if p[k] and p[k] not in plan_names:
                p[k] = None
        if p["customer_id"] and p["customer_id"] not in {c["id"] for c in cat["customers"]}:
            p["unknown_customer_id"] = p["customer_id"]
        for k in ("storage_gb", "monthly_fee_krw", "target_monthly_fee_krw", "elapsed_days"):
            p[k] = int(p[k]) if p.get(k) not in (None, "") else None
        return p

    # ------------------------------------------------------------------ catalog
    def get_tool_catalog(self) -> List[Dict[str, Any]]:
        def t(name, stage, cat, steps, ko, en, origin, src):
            return {"name": name, "stage": stage, "category": cat, "steps": steps, "description": ko,
                    "description_en": en, "spec_origin": origin, "spec_source": src}
        return [
            t("mcp_stage1_asset_discovery", "STAGE 1", "stage_pipeline",
              ["profile_tables", "scan_guides", "prune_noise", "tag_pii_governance"],
              "Stage 1 BigQuery 테이블 실측 프로파일링(__TABLES__) 및 고객 식별자 비식별화 규칙 검사",
              "Stage 1 live BigQuery table profiling and customer ID de-identification check",
              "GCP_NATIVE", f"BigQuery `{self.fq}.__TABLES__`, `tb_customer_contract`"),
            t("mcp_stage2_wiki_and_semantic", "STAGE 2", "stage_pipeline",
              ["compile_3layer_wiki", "extract_hash_anchors", "bind_semantic_bridges"],
              "Stage 2 GCS 위키 객체 목록 및 BigQuery 문서 청크·규칙 앵커 조회",
              "Stage 2 GCS wiki object listing and BigQuery chunk/rule anchor lookup",
              "CUSTOM_EXTENSION", f"GCS `gs://{self.gcs_bucket}` + BigQuery `tb_doc_chunks`, `tb_domain_rules`"),
            t("mcp_stage3_property_graph", "STAGE 3", "stage_pipeline",
              ["promote_dw_nodes", "synthesize_graph_ddl", "verify_gql_templates"],
              "Stage 3 노드 테이블 중복 키 검사 및 Property Graph GQL 경로 수 실측",
              "Stage 3 node-table duplicate-key check and Property Graph GQL path count",
              "GCP_NATIVE", f"BigQuery Property Graph `{self.graph}`"),
            t("mcp_stage4_agent_orchestration", "STAGE 4", "stage_pipeline",
              ["decompose_subgoals", "dispatch_domain_mcps", "verify_grounding_anchors"],
              "Stage 4 에이전트가 사용하는 도메인 규칙과 근거 청크를 BigQuery에서 조회",
              "Stage 4 domain rules and grounding chunks used by the agent (BigQuery)",
              "CUSTOM_EXTENSION", "src/agent/reasoning_engine.py + Vertex AI gemini-3.8-flash"),
            t("mcp_stage5_lineage_and_eval", "STAGE 5", "stage_pipeline",
              ["build_4tier_lineage", "run_golden_cq_suite", "diagnose_boundary_failures"],
              "Stage 5 고객 약정→단말·요금제·지원금→규칙→청크 리니지 조인 및 최근 검증 리포트 요약",
              "Stage 5 contract→device/plan/subsidy→rule→chunk lineage join and latest validation summary",
              "CUSTOM_EXTENSION", f"BigQuery `{self.fq}` + pipeline/validator.py report"),
            t("mcp_lookup_customer_profile", "RUNTIME", "runtime_domain",
              ["lookup_contract", "lookup_device_price", "lookup_subsidy_policy"],
              "고객 약정·단말 출고가·요금제별 공시지원금/추가지원금/실구매가 BigQuery 조회 (불일치 시 0건과 실제 카탈로그 반환)",
              "Customer contract, device price and subsidy lookup (returns 0 rows + live catalog on mismatch)",
              "CUSTOM_EXTENSION", f"BigQuery `{self.fq}.tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_customer_contract`"),
            t("mcp_calculate_penalty_rule", "RUNTIME", "runtime_domain",
              ["check_exemptions", "compute_180d_prorated_clawback", "compare_24m_tco"],
              "180일 차액정산 위약금·특례 면제·24개월 TCO를 BigQuery SQL로 계산",
              "180-day prorated penalty, exemption and 24-month TCO computed in BigQuery SQL",
              "CUSTOM_EXTENSION", f"BigQuery `{self.fq}.tb_subsidy_policy`, `tb_plan_master`, `tb_domain_rules`"),
            t("mcp_query_graph_and_wiki", "RUNTIME", "runtime_domain",
              ["traverse_property_graph", "fetch_okf_hash_anchor", "verify_dw_schema"],
              "Property Graph GRAPH_TABLE 멀티홉 탐색 및 규칙 근거 청크 원문 조회",
              "Property Graph GRAPH_TABLE multi-hop traversal and grounding chunk retrieval",
              "GCP_NATIVE", f"BigQuery `GRAPH_TABLE({self.graph})` + `tb_doc_chunks`"),
        ]

    # ------------------------------------------------------------------ dispatch
    def execute_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        aliases = {
            "mcp_get_device_factory_price": "mcp_lookup_customer_profile",
            "mcp_get_device_subsidy_by_plan": "mcp_lookup_customer_profile",
            "mcp_calculate_plan_change_penalty": "mcp_calculate_penalty_rule",
            "mcp_compare_contract_plans": "mcp_calculate_penalty_rule",
            "mcp_explore_property_graph": "mcp_query_graph_and_wiki",
            "mcp_get_policy_anchor_grounding": "mcp_query_graph_and_wiki",
            "mcp_inspect_dw_table_schema": "mcp_query_graph_and_wiki",
        }
        name = aliases.get(tool_name, tool_name)
        handler = getattr(self, "_" + name, None)
        if not handler:
            return {"status": "ERROR", "tool": tool_name, "message": f"Unknown MCP tool: {tool_name}"}
        jobs: List[Dict[str, Any]] = []
        t0 = time.perf_counter()
        try:
            out = handler(args, jobs)
        except BqQueryError as e:
            out = {"status": "BQ_QUERY_ERROR", "error": str(e.res.get("error", ""))[:1500],
                   "http_code": e.res.get("http_code")}
        out.update({
            "tool": name,
            "bq_jobs": jobs,
            "bq_job_id": jobs[-1]["job_id"] if jobs else None,
            "bq_job_ids": [j["job_id"] for j in jobs if j.get("job_id")],
            "bq_elapsed_ms": round(sum(j.get("elapsed_ms") or 0 for j in jobs), 2),
            "executed_sql": "\n\n".join(j["sql"] for j in jobs),
            "tool_elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        })
        out.setdefault("executed_steps", args.get("steps") or next(
            (t["steps"] for t in self.get_tool_catalog() if t["name"] == name), []))
        return out

    # ------------------------------------------------------------------ stage MCPs
    def _mcp_stage1_asset_discovery(self, args, jobs):
        tables = self._run(f"SELECT table_id, row_count, size_bytes FROM `{self.fq}.__TABLES__` ORDER BY table_id", jobs)
        pii = self._run(f"""
            SELECT COUNT(*) AS contracts,
                   COUNTIF(NOT REGEXP_CONTAINS(customer_id, r'^CUST_DEMO_[0-9]{{3}}$')) AS non_deidentified_ids
            FROM `{self.fq}.tb_customer_contract`""", jobs)[0]
        return {"status": "SUCCESS", "stage": "STAGE 1", "table_inventory": tables, "pii_check": pii,
                "summary": f"BigQuery `{self.fq}` 테이블 {len(tables)}개, 총 {sum(t['row_count'] for t in tables)}행 실측 · "
                           f"비식별 규칙 위반 고객 ID {pii['non_deidentified_ids']}건"}

    def _mcp_stage2_wiki_and_semantic(self, args, jobs):
        rows = self._run(f"""
            SELECT ch.chunk_id, ch.source_file, ch.section_title, ch.content_sha256 AS anchor, ch.trust_tier,
                   r.rule_id, r.rule_name, r.formula_expr
            FROM `{self.fq}.tb_doc_chunks` ch
            LEFT JOIN `{self.fq}.tb_domain_rules` r ON r.source_chunk_id = ch.chunk_id
            ORDER BY ch.chunk_id, r.rule_id""", jobs)
        objs = [f"gs://{self.gcs_bucket}/{o['name']}" for o in list_gcs_objects(bucket=self.gcs_bucket)]
        return {"status": "SUCCESS", "stage": "STAGE 2", "gcs_objects": objs, "anchored_chunks": rows,
                "anchor_format": "anchor_ + SHA-256 hex 앞 12자리 (pipeline/ingest.py)",
                "summary": f"GCS 객체 {len(objs)}개 · 청크/규칙 조인 {len(rows)}행"}

    def _mcp_stage3_property_graph(self, args, jobs):
        dup = self._run(f"""
            SELECT 'tb_device_master' AS node_table, COUNT(*) AS row_count, COUNT(*) - COUNT(DISTINCT device_id) AS duplicate_keys FROM `{self.fq}.tb_device_master`
            UNION ALL SELECT 'tb_plan_master', COUNT(*), COUNT(*) - COUNT(DISTINCT plan_id) FROM `{self.fq}.tb_plan_master`
            UNION ALL SELECT 'tb_subsidy_policy', COUNT(*), COUNT(*) - COUNT(DISTINCT policy_id) FROM `{self.fq}.tb_subsidy_policy`
            UNION ALL SELECT 'tb_customer_contract', COUNT(*), COUNT(*) - COUNT(DISTINCT contract_id) FROM `{self.fq}.tb_customer_contract`
            UNION ALL SELECT 'tb_doc_chunks', COUNT(*), COUNT(*) - COUNT(DISTINCT chunk_id) FROM `{self.fq}.tb_doc_chunks`
            UNION ALL SELECT 'tb_domain_rules', COUNT(*), COUNT(*) - COUNT(DISTINCT rule_id) FROM `{self.fq}.tb_domain_rules`""", jobs)
        paths = self._run(f"""
            SELECT COUNT(*) AS device_plan_rule_paths, COUNT(DISTINCT policy_id) AS subsidy_edges
            FROM GRAPH_TABLE(`{self.graph}`
              MATCH (d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)
              COLUMNS (hs.policy_id AS policy_id))""", jobs)[0]
        total_dup = sum(r["duplicate_keys"] for r in dup)
        return {"status": "SUCCESS", "stage": "STAGE 3", "engine": args.get("engine", "bigquery"),
                "graph_id": self.graph, "node_tables": dup, "duplicate_keys_total": total_dup, "gql_paths": paths,
                "summary": f"노드 테이블 중복 키 {total_dup}건 · GQL 경로(Device→Plan←Rule) {paths['device_plan_rule_paths']}개"}

    def _mcp_stage4_agent_orchestration(self, args, jobs):
        rules = self._run(f"""
            SELECT r.rule_id, r.rule_name, r.rule_category, r.condition_expr, r.formula_expr, r.source_chunk_id, ch.content_sha256 AS anchor
            FROM `{self.fq}.tb_domain_rules` r LEFT JOIN `{self.fq}.tb_doc_chunks` ch ON ch.chunk_id = r.source_chunk_id
            ORDER BY r.rule_id""", jobs)
        return {"status": "SUCCESS", "stage": "STAGE 4", "active_rules": rules,
                "summary": f"도메인 규칙 {len(rules)}개와 근거 청크 앵커 조회"}

    def _mcp_stage5_lineage_and_eval(self, args, jobs):
        rows = self._run(f"""
            SELECT c.contract_id, c.customer_id, d.device_name, p.plan_name, s.policy_id,
                   e.rule_id, e.source_chunk_id, ch.content_sha256 AS anchor, ch.source_file
            FROM `{self.fq}.tb_customer_contract` c
            JOIN `{self.fq}.tb_device_master` d ON d.device_id = c.device_id
            JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = c.plan_id
            LEFT JOIN `{self.fq}.tb_subsidy_policy` s ON s.device_id = c.device_id AND s.plan_id = c.plan_id
            LEFT JOIN `{self.fq}.edge_rule_applies_to_plan` e ON e.plan_id = c.plan_id
            LEFT JOIN `{self.fq}.tb_doc_chunks` ch ON ch.chunk_id = e.source_chunk_id
            ORDER BY c.contract_id, e.rule_id""", jobs)
        report, rp = {}, os.path.join(BASE_DIR, "data/output/cq_benchmark_report.json")
        if os.path.exists(rp):
            with open(rp, "r", encoding="utf-8") as f:
                r = json.load(f)
            report = {k: r.get(k) for k in ("evaluated_at", "total_cqs", "passed", "accuracy_rate", "method")}
        return {"status": "SUCCESS", "stage": "STAGE 5", "lineage_records": rows, "latest_validation_report": report,
                "summary": f"리니지 조인 {len(rows)}행 · 최근 검증 리포트: {report or '없음'}"}

    # ------------------------------------------------------------------ runtime MCPs
    def _mcp_lookup_customer_profile(self, args, jobs):
        p = self.resolve_params(args)
        where = []
        if p["customer_id"]:
            where.append(f"c.customer_id = {_lit(p['customer_id'])}")
        if p["device_name"]:
            where.append(f"d.device_name = {_lit(p['device_name'])}")
        elif p["storage_gb"]:
            where.append(f"d.storage_gb = {p['storage_gb']}")
        if p["plan_name"]:
            where.append(f"p.plan_name = {_lit(p['plan_name'])}")
        if p["monthly_fee_krw"] is not None:
            where.append(f"p.monthly_fee_krw = {p['monthly_fee_krw']}")
        cols = """d.device_id, d.device_name, d.storage_gb, d.factory_price_krw,
                  p.plan_id, p.plan_name, p.monthly_fee_krw, p.min_maintenance_days, p.selective_discount_rate,
                  s.policy_id, s.base_subsidy_krw, s.additional_subsidy_cap_krw,
                  s.base_subsidy_krw + s.additional_subsidy_cap_krw AS total_subsidy_krw,
                  d.factory_price_krw - (s.base_subsidy_krw + s.additional_subsidy_cap_krw) AS net_installment_principal_krw,
                  s.mandatory_retention_days, rr.rule_id AS applied_rule_id, rr.source_chunk_id AS grounded_chunk_id"""
        rule_join = f"CROSS JOIN (SELECT rule_id, source_chunk_id FROM `{self.fq}.tb_domain_rules` WHERE rule_id = 'RULE_SUBSIDY_CAP') rr"
        if p["customer_id"]:
            sql = f"""SELECT c.customer_id, c.contract_id, c.customer_segment, c.age_group, c.contract_type,
                             c.commitment_months, c.elapsed_days, c.granted_subsidy_krw, c.welfare_status, {cols}
                      FROM `{self.fq}.tb_customer_contract` c
                      JOIN `{self.fq}.tb_device_master` d ON d.device_id = c.device_id
                      JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = c.plan_id
                      LEFT JOIN `{self.fq}.tb_subsidy_policy` s ON s.device_id = c.device_id AND s.plan_id = c.plan_id
                      {rule_join}
                      WHERE {' AND '.join(where)}"""
        else:
            sql = f"""SELECT {cols}
                      FROM `{self.fq}.tb_device_master` d
                      LEFT JOIN `{self.fq}.tb_subsidy_policy` s ON s.device_id = d.device_id
                      LEFT JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = s.plan_id
                      {rule_join}
                      WHERE {' AND '.join(where) or 'TRUE'}
                      ORDER BY d.device_name, p.monthly_fee_krw DESC"""
        rows = self._run(sql, jobs)
        base = {"applied_params": p, "matched_rows_count": len(rows), "matched_rows": rows}
        if rows:
            return {"status": "SUCCESS", **base}
        if p.get("unknown_customer_id") or not where:
            base["mismatch_reason"] = (f"고객 ID `{p.get('unknown_customer_id')}`가 tb_customer_contract에 없음"
                                       if p.get("unknown_customer_id") else "조회 조건 없음")
        diag = []
        if p["plan_name"]:
            diag.append(f"SELECT 'plan_name_only' AS check_type, plan_name AS name, monthly_fee_krw AS value FROM `{self.fq}.tb_plan_master` WHERE plan_name = {_lit(p['plan_name'])}")
        if p["monthly_fee_krw"] is not None:
            diag.append(f"SELECT 'fee_only', plan_name, monthly_fee_krw FROM `{self.fq}.tb_plan_master` WHERE monthly_fee_krw = {p['monthly_fee_krw']}")
        if p["device_name"]:
            diag.append(f"SELECT 'device_only', device_name, factory_price_krw FROM `{self.fq}.tb_device_master` WHERE device_name = {_lit(p['device_name'])}")
        checks = self._run(" UNION ALL ".join(diag), jobs) if diag else []
        plans = self._run(f"SELECT plan_id, plan_name, monthly_fee_krw FROM `{self.fq}.tb_plan_master` ORDER BY monthly_fee_krw DESC", jobs)
        pol_where = f"WHERE d.device_name = {_lit(p['device_name'])}" if p["device_name"] else ""
        policies = self._run(f"""
            SELECT d.device_name, p.plan_name, p.monthly_fee_krw, s.base_subsidy_krw, s.additional_subsidy_cap_krw,
                   s.base_subsidy_krw + s.additional_subsidy_cap_krw AS total_subsidy_krw,
                   d.factory_price_krw - (s.base_subsidy_krw + s.additional_subsidy_cap_krw) AS net_installment_principal_krw
            FROM `{self.fq}.tb_subsidy_policy` s
            JOIN `{self.fq}.tb_device_master` d ON d.device_id = s.device_id
            JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = s.plan_id
            {pol_where} ORDER BY d.device_name, p.monthly_fee_krw DESC""", jobs)
        return {"status": "MATCH_NOT_FOUND", **base, "diagnostic_checks": checks,
                "available_plans_in_bq": plans, "available_subsidy_policies_in_bq": policies,
                "mismatch_reason": base.get("mismatch_reason") or
                f"조건 {json.dumps({k: v for k, v in p.items() if v is not None}, ensure_ascii=False)}과 일치하는 행 0건"}

    def _mcp_calculate_penalty_rule(self, args, jobs):
        p = self.resolve_params(args)
        rules = self._run(f"""
            SELECT r.rule_id, r.rule_name, r.condition_expr, r.formula_expr, r.source_chunk_id, r.description_ko,
                   ch.content_sha256 AS anchor
            FROM `{self.fq}.tb_domain_rules` r LEFT JOIN `{self.fq}.tb_doc_chunks` ch ON ch.chunk_id = r.source_chunk_id
            ORDER BY r.rule_id""", jobs)
        tf = []
        if p["target_plan_name"]:
            tf.append(f"plan_name = {_lit(p['target_plan_name'])}")
        if p["target_monthly_fee_krw"] is not None:
            tf.append(f"monthly_fee_krw = {p['target_monthly_fee_krw']}")
        if not p["customer_id"] and not p["device_name"]:
            missing = ["customer_id 또는 단말기(+가입 요금제)"]
            if p["elapsed_days"] is None:
                missing.append("개통 후 경과일수")
            if not tf:
                missing.append("변경 희망 요금제")
            out = {"status": "INSUFFICIENT_PARAMETERS", "applied_params": p, "missing_slots": missing, "domain_rules": rules}
            if p["elapsed_days"] is not None or tf:  # rule-only check that needs no contract data
                tw = " AND ".join(tf) or "FALSE"
                r = self._run(f"""
                    SELECT (SELECT MAX(mandatory_retention_days) FROM `{self.fq}.tb_subsidy_policy`) AS retention_days,
                           (SELECT MIN(monthly_fee_krw) FROM `{self.fq}.tb_plan_master` WHERE min_maintenance_days > 0) AS baseline_fee_krw,
                           (SELECT plan_name FROM `{self.fq}.tb_plan_master` WHERE {tw} LIMIT 1) AS target_plan_name,
                           (SELECT monthly_fee_krw FROM `{self.fq}.tb_plan_master` WHERE {tw} LIMIT 1) AS target_monthly_fee_krw,
                           (SELECT source_chunk_id FROM `{self.fq}.tb_domain_rules` WHERE rule_id = 'RULE_SIX_PLAN_180D') AS grounded_chunk_id""", jobs)[0]
                e, fee = p["elapsed_days"], r["target_monthly_fee_krw"]
                if e is not None and e >= r["retention_days"]:
                    st, pen = "EXEMPT_RETENTION_COMPLETED", 0
                elif fee is not None and fee >= r["baseline_fee_krw"]:
                    st, pen = "NO_PENALTY_ABOVE_BASELINE", 0
                else:
                    st, pen = "DEPENDS_ON_CONTRACT", None
                out["rule_only_determination"] = {**r, "elapsed_days": e, "status": st, "penalty_krw": pen,
                                                  "applied_rule_id": "RULE_SIX_PLAN_180D"}
            return out
        if p["customer_id"]:
            init = f"""SELECT c.customer_id, c.contract_id, c.welfare_status, c.contract_type, c.elapsed_days AS contract_elapsed_days,
                              d.device_id, d.device_name, d.factory_price_krw, p.plan_id, p.plan_name, p.monthly_fee_krw,
                              p.selective_discount_rate, s.policy_id, s.base_subsidy_krw, s.additional_subsidy_cap_krw, s.mandatory_retention_days
                       FROM `{self.fq}.tb_customer_contract` c
                       JOIN `{self.fq}.tb_device_master` d ON d.device_id = c.device_id
                       JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = c.plan_id
                       LEFT JOIN `{self.fq}.tb_subsidy_policy` s ON s.device_id = c.device_id AND s.plan_id = c.plan_id
                       WHERE c.customer_id = {_lit(p['customer_id'])}"""
        else:
            f = [f"d.device_name = {_lit(p['device_name'])}"]
            if p["plan_name"]:
                f.append(f"p.plan_name = {_lit(p['plan_name'])}")
            if p["monthly_fee_krw"] is not None:
                f.append(f"p.monthly_fee_krw = {p['monthly_fee_krw']}")
            init = f"""SELECT CAST(NULL AS STRING) AS customer_id, CAST(NULL AS STRING) AS contract_id, 'UNKNOWN' AS welfare_status,
                              'PUBLIC_SUBSIDY' AS contract_type, CAST(NULL AS INT64) AS contract_elapsed_days,
                              d.device_id, d.device_name, d.factory_price_krw, p.plan_id, p.plan_name, p.monthly_fee_krw,
                              p.selective_discount_rate, s.policy_id, s.base_subsidy_krw, s.additional_subsidy_cap_krw, s.mandatory_retention_days
                       FROM `{self.fq}.tb_subsidy_policy` s
                       JOIN `{self.fq}.tb_device_master` d ON d.device_id = s.device_id
                       JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = s.plan_id
                       WHERE {' AND '.join(f)}"""
        target_requested = bool(tf)
        elapsed = str(p["elapsed_days"]) if p["elapsed_days"] is not None else "i.contract_elapsed_days"
        sql = f"""
            WITH init AS ({init}),
            baseline AS (SELECT MIN(monthly_fee_krw) AS baseline_fee_krw FROM `{self.fq}.tb_plan_master` WHERE min_maintenance_days > 0),
            tgt AS (SELECT plan_id AS target_plan_id, plan_name AS target_plan_name, monthly_fee_krw AS target_monthly_fee_krw
                    FROM `{self.fq}.tb_plan_master` WHERE {' AND '.join(tf) or 'FALSE'} LIMIT 1),
            calc AS (
              SELECT i.*, b.baseline_fee_krw, t.target_plan_id, t.target_plan_name, t.target_monthly_fee_krw,
                     ts.base_subsidy_krw AS target_base_subsidy_krw, {elapsed} AS elapsed_days,
                     IF(i.welfare_status = 'SENIOR_EXEMPT', 'RULE_WELFARE_EXEMPT', 'RULE_SIX_PLAN_180D') AS applied_rule_id
              FROM init i CROSS JOIN baseline b LEFT JOIN tgt t ON TRUE
              LEFT JOIN `{self.fq}.tb_subsidy_policy` ts ON ts.device_id = i.device_id AND ts.plan_id = t.target_plan_id),
            res AS (
              SELECT *,
                CASE WHEN welfare_status = 'SENIOR_EXEMPT' THEN 'EXEMPT_WELFARE'
                     WHEN policy_id IS NULL THEN 'NOT_APPLICABLE_NO_PUBLIC_SUBSIDY'
                     WHEN target_plan_id IS NULL THEN 'TARGET_PLAN_NOT_RESOLVED'
                     WHEN elapsed_days IS NULL THEN 'ELAPSED_DAYS_MISSING'
                     WHEN elapsed_days >= mandatory_retention_days THEN 'EXEMPT_RETENTION_COMPLETED'
                     WHEN target_monthly_fee_krw >= baseline_fee_krw THEN 'NO_PENALTY_ABOVE_BASELINE'
                     ELSE 'PRORATED_PENALTY' END AS penalty_status,
                CASE WHEN welfare_status = 'SENIOR_EXEMPT' OR policy_id IS NULL THEN 0
                     WHEN target_plan_id IS NULL OR elapsed_days IS NULL THEN NULL
                     WHEN elapsed_days >= mandatory_retention_days OR target_monthly_fee_krw >= baseline_fee_krw THEN 0
                     ELSE CAST(ROUND((base_subsidy_krw - COALESCE(target_base_subsidy_krw, 0))
                                     * (mandatory_retention_days - elapsed_days) / mandatory_retention_days) AS INT64) END AS penalty_krw,
                (factory_price_krw - (base_subsidy_krw + additional_subsidy_cap_krw)) + monthly_fee_krw * 24 AS public_subsidy_24m_tco_krw,
                CAST(ROUND(factory_price_krw + monthly_fee_krw * (1 - selective_discount_rate) * 24) AS INT64) AS selective_24m_tco_krw,
                CAST(ROUND(monthly_fee_krw * selective_discount_rate * 24) AS INT64) AS selective_24m_discount_total_krw,
                base_subsidy_krw + additional_subsidy_cap_krw AS public_subsidy_total_krw
              FROM calc)
            SELECT res.*, COALESCE(e.source_chunk_id, r.source_chunk_id) AS grounded_chunk_id,
                   tr.rule_id AS tco_rule_id, tr.source_chunk_id AS tco_grounded_chunk_id
            FROM res
            LEFT JOIN `{self.fq}.tb_domain_rules` r ON r.rule_id = res.applied_rule_id
            LEFT JOIN `{self.fq}.edge_rule_applies_to_plan` e
              ON e.rule_id = res.applied_rule_id AND e.plan_id = IF(res.policy_id IS NULL, res.plan_id, res.target_plan_id)
            LEFT JOIN `{self.fq}.tb_domain_rules` tr ON tr.rule_id = 'RULE_TCO_24M'
            ORDER BY res.monthly_fee_krw DESC"""
        rows = self._run(sql, jobs)
        base = {"applied_params": p, "matched_rows_count": len(rows), "calculations": rows, "domain_rules": rules,
                "target_requested": target_requested}
        if not rows:
            return {"status": "MATCH_NOT_FOUND", **base,
                    "mismatch_reason": "초기 계약(고객 또는 단말+요금제) 조건과 일치하는 공시지원금 정책/약정이 BigQuery에 없음"}
        for r in rows:
            if r.get("public_subsidy_24m_tco_krw") is not None and r.get("selective_24m_tco_krw") is not None:
                diff = r["selective_24m_tco_krw"] - r["public_subsidy_24m_tco_krw"]
                r["tco_recommendation"] = "PUBLIC_SUBSIDY" if diff > 0 else ("SELECTIVE_25PCT" if diff < 0 else "EQUAL")
                r["tco_savings_krw"] = abs(diff)
            if r.get("target_base_subsidy_krw") is None and r.get("target_plan_id"):
                r["target_subsidy_note"] = "대상 요금제의 공시지원금 정책이 tb_subsidy_policy에 없어 0원으로 계산"
        return {"status": "SUCCESS", **base}

    def _mcp_query_graph_and_wiki(self, args, jobs):
        p = self.resolve_params(args)
        where = []
        if p["customer_id"]:
            match = "(c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)"
            cols = "c.customer_id AS customer_id, c.contract_id AS contract_id, c.welfare_status AS welfare_status, c.elapsed_days AS elapsed_days,"
            where.append(f"g.customer_id = {_lit(p['customer_id'])}")
        else:
            match = "(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)"
            cols = "hs.policy_id AS policy_id, hs.total_subsidy_krw AS total_subsidy_krw,"
        if p["device_name"]:
            where.append(f"g.device_name = {_lit(p['device_name'])}")
        if p["plan_name"]:
            where.append(f"g.plan_name = {_lit(p['plan_name'])}")
        if p["monthly_fee_krw"] is not None:
            where.append(f"g.monthly_fee_krw = {p['monthly_fee_krw']}")
        rows = self._run(f"""
            SELECT g.*, ch.section_title, ch.content_sha256 AS anchor, ch.content AS chunk_text
            FROM GRAPH_TABLE(`{self.graph}`
              MATCH {match}
              COLUMNS ({cols} d.device_name AS device_name, d.factory_price_krw AS factory_price_krw,
                       p.plan_name AS plan_name, p.monthly_fee_krw AS monthly_fee_krw,
                       r.rule_id AS rule_id, r.rule_name AS rule_name,
                       ap.relation_label_ko AS relation_label_ko, ap.source_chunk_id AS source_chunk_id)) g
            LEFT JOIN `{self.fq}.tb_doc_chunks` ch ON ch.chunk_id = g.source_chunk_id
            WHERE {' AND '.join(where) or 'TRUE'}
            ORDER BY g.device_name, g.monthly_fee_krw DESC, g.rule_id""", jobs)
        nodes = {("D", r["device_name"]) for r in rows} | {("P", r["plan_name"]) for r in rows} | {("R", r["rule_id"]) for r in rows}
        anchors = sorted({f"{r['source_chunk_id']} ({r['section_title']}, {r['anchor']})" for r in rows if r.get("source_chunk_id")})
        return {"status": "SUCCESS" if rows else "MATCH_NOT_FOUND", "applied_params": p,
                "graph_engine": args.get("engine", "bigquery"), "graph_name": self.graph,
                "gql_path": match, "traversal_hops": 3 if p["customer_id"] else 2,
                "matched_graph_paths_count": len(rows), "matched_nodes": len(nodes),
                "matched_graph_paths": rows, "grounded_anchors": anchors}
