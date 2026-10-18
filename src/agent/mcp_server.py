# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Domain & Stage Pipeline MCP Server (Starter v2.0 - Live GCP Dual-Engine).
Every tool executes real BigQuery SQL / SQL:2023 GRAPH_TABLE queries against
`$GCP_PROJECT_ID.$BQ_DATASET_ID` (default) OR real Cloud Spanner Graph SQL/GQL queries
against `starter-spanner/starter_ontology_db` when `engine="spanner"`, plus GCS.
- No hardcoded answers. Parameter values are validated against the live catalog.
- Query failures are returned as `BQ_QUERY_ERROR` (never as 0 rows).
"""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from src.agent.i18n_en import is_english_mode, localize_en_obj
from src.resource_connector import (
    CODE_EXPOSURE_BOUNDARY,
    REFERENCE_STUDIOS,
    STAGE_UNIFIED_MAP,
    OntologyResourceConnector,
)
from src.gcp_client import (
    DEFAULT_DATASET_ID,
    DEFAULT_GCS_BUCKET,
    DEFAULT_LOCATION,
    DEFAULT_PROJECT_ID,
    DEFAULT_SPANNER_DATABASE,
    DEFAULT_SPANNER_INSTANCE,
    execute_bq_sql,
    execute_spanner_sql,
    list_gcs_objects,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CATALOG_TTL_SEC = 300


class BqQueryError(Exception):
    def __init__(self, res: Dict[str, Any]):
        super().__init__(res.get("error", "Graph/SQL engine error"))
        self.res = res


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(s or "").lower())


def _lit(s: str) -> str:
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _resolve_engine(engine: Optional[str]) -> str:
    return "spanner" if str(engine or "bigquery").lower() == "spanner" else "bigquery"


_CATALOG_CACHE: Dict[tuple, tuple] = {}
# Label columns per language (BigQuery tables loaded by the GOAL-223 loader carry *_ko / *_en; Spanner keeps legacy names).
_LABEL_COLS = {
    "rule_name": {"ko": "rule_name", "en": "rule_name_en", "legacy": "rule_name"},
    "description": {"ko": "description_ko", "en": "description_en", "legacy": "description_ko"},
    "relation_label": {"ko": "relation_label_ko", "en": "relation_label_en", "legacy": "relation_label_ko"},
    "section_title": {"ko": "section_title_ko", "en": "section_title_en", "legacy": "section_title"},
    "content": {"ko": "content_ko", "en": "content_en", "legacy": "content"},
}


class DomainMcpServer:
    def __init__(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        dataset_id: str = DEFAULT_DATASET_ID,
        gcs_bucket: str = DEFAULT_GCS_BUCKET,
        spanner_instance_id: str = DEFAULT_SPANNER_INSTANCE,
        spanner_database_id: str = DEFAULT_SPANNER_DATABASE,
        root_dir: Optional[str] = None,
        graph_name: Optional[str] = None,
        location: Optional[str] = None,
        mode: str = "full",
        **_ignored,
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.gcs_bucket = gcs_bucket
        self.spanner_instance_id = spanner_instance_id or DEFAULT_SPANNER_INSTANCE
        self.spanner_database_id = spanner_database_id or DEFAULT_SPANNER_DATABASE
        self.root_dir = root_dir or os.environ.get("STARTER_PROJECT_ROOT") or BASE_DIR  # project data root
        self.location = location or DEFAULT_LOCATION
        # mode "ledger" (Flow B) = P2 tables only (no clause table); "full" (Flow C) = unified graph with clauses
        self.mode = "ledger" if str(mode).lower() == "ledger" else "full"
        self.graph_name = graph_name or "STARTER_ONTOLOGY_GRAPH"
        self.fq = f"{project_id}.{dataset_id}"
        self.graph = f"{self.fq}.{self.graph_name}"
        self.spanner_graph = "STARTER_ONTOLOGY_GRAPH"
        self.spanner_uri = f"projects/{self.project_id}/instances/{self.spanner_instance_id}/databases/{self.spanner_database_id}"
        self._catalog: Optional[Dict[str, Any]] = None
        self._catalog_at = 0.0
        self.connector = OntologyResourceConnector(
            project_id=self.project_id,
            dataset_id=dataset_id,
            gcs_bucket=self.gcs_bucket,
            spanner_instance_id=self.spanner_instance_id,
            spanner_database_id=self.spanner_database_id,
            root_dir=self.root_dir,
        )

    # ------------------------------------------------------------------ helpers
    def col(self, key: str, en: bool, eng: str = "bigquery") -> str:
        """Language column for a label (`rule_name`, `description`, `relation_label`, `section_title`, `content`)."""
        c = _LABEL_COLS[key]
        if _resolve_engine(eng) == "spanner":
            return c["legacy"]
        return c["en" if en else "ko"]

    def _to_spanner_sql(self, sql: str) -> str:
        return (
            sql.replace(f"`{self.graph}`", f"`{self.spanner_graph}`")
            .replace(self.graph, self.spanner_graph)
            .replace(f"`{self.fq}.", "`")
            .replace(f"{self.fq}.", "")
        )

    def _run(self, sql: str, jobs: List[Dict[str, Any]], engine: str = "bigquery") -> List[Dict[str, Any]]:
        eng = _resolve_engine(engine)
        if eng == "spanner":
            exec_sql = self._to_spanner_sql(sql)
            res = execute_spanner_sql(
                exec_sql,
                project_id=self.project_id,
                instance_id=self.spanner_instance_id,
                database_id=self.spanner_database_id,
            )
        else:
            exec_sql = sql
            res = execute_bq_sql(sql, project_id=self.project_id, location=self.location)
        jobs.append({
            "job_id": res.get("job_id"),
            "engine": eng,
            "status": res.get("status"),
            "elapsed_ms": res.get("elapsed_ms"),
            "rows": len(res.get("rows", [])),
            "sql": " ".join(exec_sql.split()),
        })
        if res.get("status") != "SUCCESS":
            raise BqQueryError(res)
        return res.get("rows", [])

    def get_live_catalog(self, force: bool = False, engine: str = "bigquery") -> Dict[str, Any]:
        """Device / plan / customer catalog read live from BigQuery or Cloud Spanner (cached per resource set)."""
        if self._catalog and not force and time.time() - self._catalog_at < CATALOG_TTL_SEC:
            return self._catalog
        key = (self.project_id, self.fq, self.location, _resolve_engine(engine))
        hit = _CATALOG_CACHE.get(key)
        if hit and not force and time.time() - hit[0] < 120:
            self._catalog, self._catalog_at = hit[1], hit[0]
            return self._catalog
        jobs: List[Dict[str, Any]] = []
        rows = self._run(f"""
            SELECT 'device' AS kind, device_id AS id, device_name AS name, factory_price_krw AS amount, storage_gb AS extra
            FROM `{self.fq}.tb_device_master`
            UNION ALL
            SELECT 'plan', plan_id, plan_name, monthly_fee_krw, min_maintenance_days FROM `{self.fq}.tb_plan_master`
            UNION ALL
            SELECT 'customer', customer_id, customer_segment, elapsed_days, NULL FROM `{self.fq}.tb_customer_contract`
            ORDER BY kind, amount DESC""", jobs, engine=engine)
        self._catalog = {
            "devices": [r for r in rows if r["kind"] == "device"],
            "plans": [r for r in rows if r["kind"] == "plan"],
            "customers": [r for r in rows if r["kind"] == "customer"],
            "job_id": jobs[0]["job_id"],
        }
        self._catalog_at = time.time()
        _CATALOG_CACHE[key] = (self._catalog_at, self._catalog)
        return self._catalog

    def get_doc_chunks(self, jobs: List[Dict[str, Any]], engine: str = "bigquery") -> List[Dict[str, Any]]:
        """track=lite: every row of tb_doc_chunks (the only table loaded for a documents-only project)."""
        return self._run(f"""SELECT chunk_id, source_doc, page_from, page_to, article_no, content
            FROM `{self.fq}.tb_doc_chunks` ORDER BY chunk_id""", jobs, engine=engine)

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
        days = [int(m) for m in re.findall(r"(\d{1,4})\s*(?:일|(?:elapsed\s+)?days?\b)", q, re.I)]
        days += [int(m) for m in re.findall(r"\bday\s*(\d{1,4})\b", q, re.I) if int(m) not in days]
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
    def get_resource_manifest(self) -> Dict[str, Any]:
        """Returns the Ready-to-Use GCP Resource Manifest and Code Exposure Boundary."""
        return self.connector.get_resource_manifest()

    def get_tool_catalog(self) -> List[Dict[str, Any]]:
        """
        Starter Pack v2.2 Code Exposure Boundary:
        Internal Stage 1~5 MCP build/compiler tools are abstracted away.
        Only the 3 Ready-to-Use Resource & Domain Business Tools are exposed here.
        """
        def t(name, stage, cat, steps, ko, en, origin, src):
            return {
                "name": name,
                "stage": stage,
                "category": cat,
                "steps": steps,
                "description": ko,
                "description_en": en,
                "spec_origin": origin,
                "spec_source": src,
                "supported_engines": ["bigquery", "spanner"],
            }
        return [
            t("mcp_lookup_customer_profile", "RESOURCE CONNECTOR · LEDGER", "runtime_domain",
              ["lookup_contract", "lookup_device_price", "lookup_subsidy_policy"],
              "[리소스 직결 도메인 도구 #1 · 원장 조회] 준비된 BigQuery/Spanner 원장(`starter_ontology_dw`)에서 고객 약정·단말 출고가·공시지원금/추가지원금/실구매가 즉시 조회",
              "[Resource-Connected Domain Tool #1 · Ledger Lookup] Direct lookup of customer contract, device price, and subsidy policy on ready-to-use BigQuery/Spanner ledgers",
              "READY_RESOURCE_CONNECTOR", f"`{self.fq}.tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_customer_contract`"),
            t("mcp_calculate_penalty_rule", "RESOURCE CONNECTOR · RULE MATH", "runtime_domain",
              ["check_exemptions", "compute_180d_prorated_clawback", "compare_24m_tco"],
              "[리소스 직결 도메인 도구 #2 · 위약금/TCO 결정론 산식] 준비된 비즈니스 룰(`BR-*` / `W1~W3` 워크플로우 분기) 기반으로 180일 일할 위약금·시니어 특례 면제·24개월 TCO를 SQL로 무환각 계산",
              "[Resource-Connected Domain Tool #2 · Deterministic Rule Math] Computes 180-day prorated penalty, welfare exemption, and 24-month TCO deterministically in BigQuery/Spanner SQL",
              "READY_RESOURCE_CONNECTOR", f"`{self.fq}.tb_subsidy_policy`, `tb_plan_master`, `tb_domain_rules` (W1~W3 Bound)"),
            t("mcp_query_graph_and_wiki", "RESOURCE CONNECTOR · GRAPH & WIKI", "runtime_domain",
              ["traverse_property_graph", "fetch_okf_hash_anchor", "verify_dw_schema"],
              "[리소스 직결 도메인 도구 #3 · 그래프 & 3-Layer 위키 탐색] 준비된 Property Graph(`STARTER_ONTOLOGY_GRAPH`) 멀티홉 `GRAPH_TABLE` 탐색 및 OKF 3-Layer 위키/해시 앵커 조인",
              "[Resource-Connected Domain Tool #3 · Graph & 3-Layer Wiki] Multi-hop `GRAPH_TABLE` traversal on `STARTER_ONTOLOGY_GRAPH` joined with 3-Layer OKF Wiki grounding",
              "READY_RESOURCE_CONNECTOR", f"`GRAPH_TABLE({self.graph} | {self.spanner_graph})` + `gs://{self.gcs_bucket}/ontology/`"),
        ]

    # ------------------------------------------------------------------ dispatch
    def execute_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = dict(args or {})
        eng = _resolve_engine(args.get("engine"))
        args["engine"] = eng
        en = is_english_mode(args.get("lang"), args.get("query"))
        aliases = {
            "lookup_customer_profile": "mcp_lookup_customer_profile",
            "calculate_penalty_rule": "mcp_calculate_penalty_rule",
            "query_graph_and_wiki": "mcp_query_graph_and_wiki",
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
            return {"status": "ERROR", "tool": tool_name, "message": f"Unknown domain/resource tool: {tool_name}"}
        jobs: List[Dict[str, Any]] = []
        t0 = time.perf_counter()
        try:
            out = handler(args, jobs)
        except BqQueryError as e:
            out = {"status": "BQ_QUERY_ERROR", "error": str(e.res.get("error", ""))[:1500],
                   "http_code": e.res.get("http_code")}
        if en:
            out = localize_en_obj(out)
        out.update({
            "tool": name,
            "engine": eng,
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

    # ------------------------------------------------------------------ runtime domain MCPs (3 tools)
    def _mcp_lookup_customer_profile(self, args, jobs):
        eng = _resolve_engine(args.get("engine"))
        en = is_english_mode(args.get("lang"), args.get("query"))
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
        rows = self._run(sql, jobs, engine=eng)
        base = {"engine": eng, "applied_params": p, "matched_rows_count": len(rows), "matched_rows": rows}
        if rows:
            return {"status": "SUCCESS", **base}
        if p.get("unknown_customer_id") or not where:
            if en:
                base["mismatch_reason"] = (f"Customer ID `{p.get('unknown_customer_id')}` not found in tb_customer_contract"
                                           if p.get("unknown_customer_id") else "No filter criteria provided")
            else:
                base["mismatch_reason"] = (f"고객 ID `{p.get('unknown_customer_id')}`가 tb_customer_contract에 없음"
                                           if p.get("unknown_customer_id") else "조회 조건 없음")
        diag = []
        if p["plan_name"]:
            diag.append(f"SELECT 'plan_name_only' AS check_type, plan_name AS name, monthly_fee_krw AS value FROM `{self.fq}.tb_plan_master` WHERE plan_name = {_lit(p['plan_name'])}")
        if p["monthly_fee_krw"] is not None:
            diag.append(f"SELECT 'fee_only', plan_name, monthly_fee_krw FROM `{self.fq}.tb_plan_master` WHERE monthly_fee_krw = {p['monthly_fee_krw']}")
        if p["device_name"]:
            diag.append(f"SELECT 'device_only', device_name, factory_price_krw FROM `{self.fq}.tb_device_master` WHERE device_name = {_lit(p['device_name'])}")
        checks = self._run(" UNION ALL ".join(diag), jobs, engine=eng) if diag else []
        plans = self._run(f"SELECT plan_id, plan_name, monthly_fee_krw FROM `{self.fq}.tb_plan_master` ORDER BY monthly_fee_krw DESC", jobs, engine=eng)
        pol_where = f"WHERE d.device_name = {_lit(p['device_name'])}" if p["device_name"] else ""
        policies = self._run(f"""
            SELECT d.device_name, p.plan_name, p.monthly_fee_krw, s.base_subsidy_krw, s.additional_subsidy_cap_krw,
                   s.base_subsidy_krw + s.additional_subsidy_cap_krw AS total_subsidy_krw,
                   d.factory_price_krw - (s.base_subsidy_krw + s.additional_subsidy_cap_krw) AS net_installment_principal_krw
            FROM `{self.fq}.tb_subsidy_policy` s
            JOIN `{self.fq}.tb_device_master` d ON d.device_id = s.device_id
            JOIN `{self.fq}.tb_plan_master` p ON p.plan_id = s.plan_id
            {pol_where} ORDER BY d.device_name, p.monthly_fee_krw DESC""", jobs, engine=eng)
        default_mismatch = (
            f"0 rows matched criteria {json.dumps({k: v for k, v in p.items() if v is not None}, ensure_ascii=False)}"
            if en else
            f"조건 {json.dumps({k: v for k, v in p.items() if v is not None}, ensure_ascii=False)}과 일치하는 행 0건"
        )
        return {"status": "MATCH_NOT_FOUND", **base, "diagnostic_checks": checks,
                "available_plans_in_bq": plans, "available_subsidy_policies_in_bq": policies,
                "mismatch_reason": base.get("mismatch_reason") or default_mismatch}

    def _mcp_calculate_penalty_rule(self, args, jobs):
        eng = _resolve_engine(args.get("engine"))
        en = is_english_mode(args.get("lang"), args.get("query"))
        p = self.resolve_params(args)
        if self.mode == "full":
            anchor_sel = "ch.content_sha256 AS anchor"
            anchor_join = f"LEFT JOIN `{self.fq}.tb_doc_chunks` ch ON ch.chunk_id = r.source_chunk_id"
        else:
            anchor_sel, anchor_join = "CAST(NULL AS STRING) AS anchor", ""
        rules = self._run(f"""
            SELECT r.rule_id, r.{self.col('rule_name', en, eng)} AS rule_name, r.condition_expr, r.formula_expr, r.source_chunk_id,
                   r.{self.col('description', en, eng)} AS description, {anchor_sel}
            FROM `{self.fq}.tb_domain_rules` r {anchor_join}
            ORDER BY r.rule_id""", jobs, engine=eng)
        tf = []
        if p["target_plan_name"]:
            tf.append(f"plan_name = {_lit(p['target_plan_name'])}")
        if p["target_monthly_fee_krw"] is not None:
            tf.append(f"monthly_fee_krw = {p['target_monthly_fee_krw']}")
        if not p["customer_id"] and not p["device_name"]:
            missing = ["customer_id or device_name (+ subscribed plan_name)" if en else "customer_id 또는 단말기(+가입 요금제)"]
            if p["elapsed_days"] is None:
                missing.append("elapsed_days since activation" if en else "개통 후 경과일수")
            if not tf:
                missing.append("target_plan_name (or target_monthly_fee_krw)" if en else "변경 희망 요금제")
            out = {"status": "INSUFFICIENT_PARAMETERS", "engine": eng, "applied_params": p, "missing_slots": missing, "domain_rules": rules}
            if p["elapsed_days"] is not None or tf:  # rule-only check that needs no contract data
                tw = " AND ".join(tf) or "FALSE"
                r = self._run(f"""
                    SELECT (SELECT MAX(mandatory_retention_days) FROM `{self.fq}.tb_subsidy_policy`) AS retention_days,
                           (SELECT MIN(monthly_fee_krw) FROM `{self.fq}.tb_plan_master` WHERE min_maintenance_days > 0) AS baseline_fee_krw,
                           (SELECT plan_name FROM `{self.fq}.tb_plan_master` WHERE {tw} LIMIT 1) AS target_plan_name,
                           (SELECT monthly_fee_krw FROM `{self.fq}.tb_plan_master` WHERE {tw} LIMIT 1) AS target_monthly_fee_krw,
                           (SELECT source_chunk_id FROM `{self.fq}.tb_domain_rules` WHERE rule_id = 'RULE_SIX_PLAN_180D') AS grounded_chunk_id""", jobs, engine=eng)[0]
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
        rows = self._run(sql, jobs, engine=eng)
        base = {"engine": eng, "applied_params": p, "matched_rows_count": len(rows), "calculations": rows, "domain_rules": rules,
                "target_requested": target_requested}
        if not rows:
            return {
                "status": "MATCH_NOT_FOUND", **base,
                "mismatch_reason": (
                    f"No matching initial contract or public subsidy policy found in {eng}"
                    if en else
                    f"초기 계약(고객 또는 단말+요금제) 조건과 일치하는 공시지원금 정책/약정이 {eng}에 없음"
                ),
            }
        for r in rows:
            if r.get("public_subsidy_24m_tco_krw") is not None and r.get("selective_24m_tco_krw") is not None:
                diff = r["selective_24m_tco_krw"] - r["public_subsidy_24m_tco_krw"]
                r["tco_recommendation"] = "PUBLIC_SUBSIDY" if diff > 0 else ("SELECTIVE_25PCT" if diff < 0 else "EQUAL")
                r["tco_savings_krw"] = abs(diff)
            if r.get("target_base_subsidy_krw") is None and r.get("target_plan_id"):
                r["target_subsidy_note"] = (
                    "No public subsidy policy entry for target plan in tb_subsidy_policy; computed with 0 KRW target subsidy"
                    if en else
                    "대상 요금제의 공시지원금 정책이 tb_subsidy_policy에 없어 0원으로 계산"
                )
        return {"status": "SUCCESS", **base}

    def _mcp_query_graph_and_wiki(self, args, jobs):
        eng = _resolve_engine(args.get("engine"))
        en = is_english_mode(args.get("lang"), args.get("query"))
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
        if self.mode == "full":
            chunk_sel = (f", ch.{self.col('section_title', en, eng)} AS section_title, ch.content_sha256 AS anchor, "
                         f"ch.{self.col('content', en, eng)} AS chunk_text")
            chunk_join = f"\nLEFT JOIN `{self.fq}.tb_doc_chunks` ch ON ch.chunk_id = g.source_chunk_id"
        else:
            chunk_sel, chunk_join = "", ""
        gql_stmt = f"""SELECT g.*{chunk_sel}
FROM GRAPH_TABLE(`{self.graph}`
  MATCH {match}
  COLUMNS ({cols} d.device_name AS device_name, d.factory_price_krw AS factory_price_krw,
           p.plan_name AS plan_name, p.monthly_fee_krw AS monthly_fee_krw,
           r.rule_id AS rule_id, r.{self.col('rule_name', en, eng)} AS rule_name,
           ap.{self.col('relation_label', en, eng)} AS relation_label, ap.source_chunk_id AS source_chunk_id)) g{chunk_join}
WHERE {' AND '.join(where) or 'TRUE'}
ORDER BY g.device_name, g.monthly_fee_krw DESC, g.rule_id"""
        rows = self._run(gql_stmt, jobs, engine=eng)
        exec_gql = self._to_spanner_sql(gql_stmt) if eng == "spanner" else gql_stmt
        graph_name = f"{self.spanner_instance_id}/{self.spanner_database_id}/{self.spanner_graph}" if eng == "spanner" else self.graph
        nodes = {("D", r["device_name"]) for r in rows} | {("P", r["plan_name"]) for r in rows} | {("R", r["rule_id"]) for r in rows}
        anchors = sorted({f"{r['source_chunk_id']} ({r.get('section_title') or '-'}, {r.get('anchor') or '-'})"
                          for r in rows if r.get("source_chunk_id")})
        return {"status": "SUCCESS" if rows else "MATCH_NOT_FOUND", "applied_params": p,
                "engine": eng, "graph_engine": eng, "graph_name": graph_name,
                "gql_path": match, "executed_gql": exec_gql, "traversal_hops": 3 if p["customer_id"] else 2,
                "matched_graph_paths_count": len(rows), "matched_nodes": len(nodes),
                "matched_graph_paths": rows, "grounded_anchors": anchors}
