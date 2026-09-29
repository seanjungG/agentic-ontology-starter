# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
AI FDE Reasoning Engine (Starter v2.0 - Live Gemini + BigQuery).
1) Vertex AI `gemini-3.8-flash` maps the question to parameters using the live BigQuery catalog.
2) Guard: fee/day numbers must appear literally in the question; names must exist in the catalog.
3) MCP tools run real BigQuery SQL / GRAPH_TABLE queries.
4) Gemini writes the answer strictly from the tool results.
No hardcoded answers or data values in code or prompts.
"""
import json
import time
from typing import Any, Dict, List, Tuple

from src.agent.i18n_en import is_english_mode, localize_en_obj
from src.agent.mcp_server import DomainMcpServer
from src.gcp_client import DEFAULT_GEMINI_MODEL, DEFAULT_PROJECT_ID, call_vertex_gemini

DECOMPOSE_SYS = """당신은 통신 온톨로지 에이전트의 질의 분석기입니다. JSON 한 개만 출력하십시오.
스키마:
{"customer_id": str|null, "device_name": str|null, "device_mention": str|null,
 "plan_name": str|null, "plan_mention": str|null, "monthly_fee_krw": int|null,
 "target_plan_name": str|null, "target_plan_mention": str|null, "target_monthly_fee_krw": int|null,
 "elapsed_days": int|null,
 "sub_goals": [{"id": "G-01", "goal": "한국어 하위 목표", "tool": "도구명"}]}
규칙:
- device_name / plan_name / target_plan_name / customer_id 는 아래 [BigQuery 카탈로그]에 있는 값과 정확히 같은 문자열만 허용. 오타·한글 표기는 카탈로그 값으로 매핑하고, 대응 값이 없으면 null.
- *_mention 에는 사용자가 쓴 표현을 그대로 기록.
- monthly_fee_krw(현재/가입 요금제), target_monthly_fee_krw(변경 희망 요금제)는 질문에 적힌 숫자를 그대로 사용. 카탈로그와 달라도 수정·추정 금지. 비교 기준으로만 언급된 금액은 넣지 않음.
- elapsed_days 는 질문에 경과 일수가 숫자로 적힌 경우만. 의무기간 기준(예: "180일 안")은 경과일수가 아님.
- tool 은 다음 중에서만 선택: {tools}
"""

DECOMPOSE_SYS_EN = """You are the query analyzer for the Telecom Ontology Agent. Output a single JSON object only.
Schema:
{"customer_id": str|null, "device_name": str|null, "device_mention": str|null,
 "plan_name": str|null, "plan_mention": str|null, "monthly_fee_krw": int|null,
 "target_plan_name": str|null, "target_plan_mention": str|null, "target_monthly_fee_krw": int|null,
 "elapsed_days": int|null,
 "sub_goals": [{"id": "G-01", "goal": "English sub-goal description", "tool": "tool_name"}]}
Rules:
- device_name / plan_name / target_plan_name / customer_id MUST exactly match a string in [BigQuery Catalog]. Map close mentions to the exact catalog string; if no match exists in the catalog, set to null.
- Record the user's raw phrase in *_mention.
- monthly_fee_krw (current/subscribed plan) and target_monthly_fee_krw (target downgrade plan) must be literal numbers from the question. Do not guess or alter them, and do not put baseline comparison numbers (e.g., 45,000 KRW baseline) into target_monthly_fee_krw.
- elapsed_days must be a literal elapsed-day count in the question (do not use the 180-day policy threshold as elapsed_days).
- Choose "tool" strictly from: {tools}
- Write all sub_goals in English only.
"""

SYNTH_SYS = """당신은 통신 온톨로지 AI FDE 에이전트입니다. 제공된 [도구 실행 결과 JSON]만 근거로 한국어 Markdown 답변을 작성하십시오.
규칙:
1. 결과 JSON에 있는 수치·이름·BigQuery Job ID·청크 ID만 인용. 결과에 없는 값은 쓰지 말 것.
2. status 별 처리:
   - SUCCESS: 질문에 대한 결론을 먼저 제시하고 근거 수치와 산식을 제시.
   - MATCH_NOT_FOUND: 첫 문장에서 "요청 조건과 일치하는 데이터가 BigQuery(`seanjung-poc.starter_ontology_dw`)에 없음(0건)"을 명시. 이어서 diagnostic_checks / available_* 결과로 실제 존재하는 값을 안내. 다른 조건의 값을 제시할 때는 "참고(질문과 다른 조건)"로 구분.
   - INSUFFICIENT_PARAMETERS: 부족한 정보(missing_slots)를 안내하고, rule_only_determination 이 있으면 그 결과만 제시.
   - BQ_QUERY_ERROR: 조회 실패를 알리고 수치를 제시하지 말 것.
3. 구성: **결론** → **근거 데이터 (BigQuery)** → **규칙·원문 근거** (rule_id, 청크 ID) → **실행 정보** (Job ID). 과장 표현 금지.
"""

SYNTH_SYS_EN = """You are the Telecom Ontology AI FDE Agent. Write your Markdown answer strictly in English (ZERO Korean characters) based ONLY on the provided [Tool Execution Results JSON].
Rules:
1. Cite ONLY numerical values, entity names, BigQuery Job IDs, rule IDs, and chunk IDs present in the JSON results. Never invent numbers.
2. Handling by status:
   - SUCCESS: Present the direct conclusion first, followed by exact figures and formulas from BigQuery.
   - MATCH_NOT_FOUND: State in the first sentence that "0 matching rows were found in BigQuery (`seanjung-poc.starter_ontology_dw`) for the requested criteria." Then list the actual catalog options from `diagnostic_checks` / `available_*`.
   - INSUFFICIENT_PARAMETERS: Clearly list the `missing_slots` needed to compute an exact figure, and if `rule_only_determination` is present, report that rule-level determination.
   - BQ_QUERY_ERROR: Report the query failure and do not output any numerical estimates.
3. Structure: **Conclusion** → **Grounded Data (BigQuery)** → **Applied Rules & Source Chunks** (`rule_id`, `chunk_id`, `anchor`) → **Execution Telemetry** (`BigQuery Job IDs`). Write in clear, objective English only (do not include any Korean words).
"""


def _strip_sql(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_sql(v) for k, v in obj.items() if k not in ("executed_sql", "sql", "bq_jobs")}
    if isinstance(obj, list):
        return [_strip_sql(v) for v in obj]
    return obj


class AiFdeAgentEngine:
    def __init__(self, project_id: str = DEFAULT_PROJECT_ID, model_name: str = DEFAULT_GEMINI_MODEL):
        self.project_id = project_id
        self.model_name = model_name
        self.server = DomainMcpServer(project_id=project_id)

    def _merge_params(self, query: str, llm: Dict[str, Any], det: Dict[str, Any], cat: Dict[str, Any], en: bool = False) -> Tuple[Dict[str, Any], List[str]]:
        notes: List[str] = []
        fees, days = set(det["literal_fees_krw"]), set(det["literal_days"])
        names = {"device_name": {d["name"] for d in cat["devices"]}, "plan_name": {p["name"] for p in cat["plans"]},
                 "target_plan_name": {p["name"] for p in cat["plans"]}, "customer_id": {c["id"] for c in cat["customers"]}}
        p: Dict[str, Any] = {}
        for k, allowed in names.items():
            v = llm.get(k)
            if v and v not in allowed:
                pref = sorted((n for n in allowed if str(v).startswith(n)), key=len)
                if pref:
                    v = pref[-1]
                else:
                    notes.append(
                        f"Excluded {k}={v!r} (not in BigQuery catalog)" if en
                        else f"Gemini 추출값 {k}={v!r}는 BigQuery 카탈로그에 없어 제외"
                    )
                    v = None
            p[k] = v if llm else (det.get(k) if det.get(k) in allowed else None)
        for k in ("monthly_fee_krw", "target_monthly_fee_krw"):
            v = llm.get(k)
            if isinstance(v, (int, float)) and int(v) not in fees:
                notes.append(
                    f"Excluded {k}={v} (number not literally in query)" if en
                    else f"Gemini 추출값 {k}={v}는 질문에 없는 숫자여서 제외"
                )
                v = None
            p[k] = int(v) if isinstance(v, (int, float)) else None
        if not llm and det["literal_fees_krw"]:  # Gemini unavailable: literal order fallback
            f = det["literal_fees_krw"]
            if p["customer_id"]:
                p["target_monthly_fee_krw"] = f[-1]
            else:
                p["monthly_fee_krw"], p["target_monthly_fee_krw"] = f[0], (f[1] if len(f) > 1 else None)
        v = llm.get("elapsed_days")
        if isinstance(v, (int, float)) and int(v) not in days:
            notes.append(
                f"Excluded elapsed_days={v} (number not literally in query)" if en
                else f"Gemini 추출값 elapsed_days={v}는 질문에 없는 숫자여서 제외"
            )
            v = None
        if not llm:
            v = next(iter(det["elapsed_day_candidates"]), None)
        p["elapsed_days"] = int(v) if isinstance(v, (int, float)) else None
        p["storage_gb"] = det.get("storage_gb") if not p["device_name"] else None
        for k in ("device_mention", "plan_mention", "target_plan_mention"):
            if llm.get(k):
                p[k] = llm[k]
        return p, notes

    def execute_cycle(self, query: str, engine: str = "bigquery", lang: str = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        en = is_english_mode(lang, query)
        cat = self.server.get_live_catalog()
        det = self.server.extract_params_from_text(query)
        tools = [t["name"] for t in self.server.get_tool_catalog()]

        catalog_txt = json.dumps({
            "devices": [d["name"] for d in cat["devices"]],
            "plans": [{"plan_name": p["name"], "monthly_fee_krw": p["amount"]} for p in cat["plans"]],
            "customers": [c["id"] for c in cat["customers"]],
        }, ensure_ascii=False)
        desc_key = "description_en" if en else "description"
        tool_txt = "\n".join(f"- {t['name']}: {t[desc_key]}" for t in self.server.get_tool_catalog())
        decomp_sys = (DECOMPOSE_SYS_EN if en else DECOMPOSE_SYS).replace("{tools}", ", ".join(tools))
        decomp_prompt = (
            f"[BigQuery Catalog (Job {cat['job_id']})]\n{catalog_txt}\n\n[MCP Tools]\n{tool_txt}\n\n[User Question]\n{query}"
            if en else
            f"[BigQuery 카탈로그 (Job {cat['job_id']})]\n{catalog_txt}\n\n[MCP 도구]\n{tool_txt}\n\n[사용자 질문]\n{query}"
        )
        decomp = call_vertex_gemini(
            prompt=decomp_prompt,
            system_instruction=decomp_sys,
            response_mime_type="application/json", temperature=0.0, max_tokens=1024,
            model_name=self.model_name, project_id=self.project_id)
        llm: Dict[str, Any] = {}
        if decomp.get("status") == "SUCCESS":
            try:
                llm = json.loads(decomp["text"])
            except Exception:
                llm = {}
        params, notes = self._merge_params(query, llm, det, cat, en=en)
        if not llm:
            notes.append(
                f"Gemini slot extraction fallback ({decomp.get('status')}, {decomp.get('http_code', '')}) — using deterministic catalog/regex extraction"
                if en else
                f"Gemini 파라미터 추출 실패({decomp.get('status')}, {decomp.get('http_code', '')}) — 질문 내 숫자·카탈로그 일치 기반 추출 사용"
            )

        sub_goals = [dict(sg, category="stage_pipeline" if sg["tool"].startswith("mcp_stage") else "runtime_domain")
                     for sg in (llm.get("sub_goals") or []) if isinstance(sg, dict) and sg.get("tool") in tools]
        if not sub_goals:
            picks = []
            if params["customer_id"] or params["device_name"] or params["plan_name"]:
                picks.append(("mcp_lookup_customer_profile", "Lookup contract, device & subsidy" if en else "약정·단말·지원금 조회"))
            if params["target_plan_name"] or params["target_monthly_fee_krw"] is not None or params["elapsed_days"] is not None:
                picks.append(("mcp_calculate_penalty_rule", "Compute prorated penalty & 24M TCO" if en else "위약금·TCO 계산"))
            picks.append(("mcp_query_graph_and_wiki", "Traverse Property Graph & grounding chunks" if en else "그래프 경로·근거 청크 조회"))
            sub_goals = [{"id": f"G-{i + 1:02d}", "goal": g, "tool": t,
                          "category": "runtime_domain"} for i, (t, g) in enumerate(picks)]
        if any(sg["category"] == "runtime_domain" for sg in sub_goals) and \
                not any(sg["tool"] == "mcp_query_graph_and_wiki" for sg in sub_goals):
            sub_goals.append({
                "id": f"G-{len(sub_goals) + 1:02d}",
                "goal": "Traverse Property Graph & grounding chunks (verification step)" if en else "그래프 경로·근거 청크 조회 (근거 확인 단계)",
                "tool": "mcp_query_graph_and_wiki", "category": "runtime_domain",
            })

        dispatched, outputs, job_ids = [], {}, [cat["job_id"]]
        for i, sg in enumerate(sub_goals):
            res = self.server.execute_tool(sg["tool"], {**params, "engine": engine, "lang": "en" if en else "ko"})
            outputs[sg["tool"]] = res
            job_ids += res.get("bq_job_ids", [])
            sql = res.get("executed_sql", "")
            dispatched.append({
                "step_index": i + 1, "tool_name": sg["tool"], "category": sg["category"], "reason": sg.get("goal", ""),
                "output": res,
                "intermediate_observation": (
                    f"status={res.get('status')} · rows={res.get('matched_rows_count', res.get('matched_graph_paths_count', '-'))} · "
                    f"BigQuery jobs={', '.join(res.get('bq_job_ids', [])) or '-'} ({res.get('bq_elapsed_ms', 0)} ms) · "
                    f"SQL: {sql[:700]}{' …' if len(sql) > 700 else ''}"),
            })

        statuses = {k: v.get("status") for k, v in outputs.items()}
        if any(s == "BQ_QUERY_ERROR" for s in statuses.values()):
            answer_status = "BQ_ERROR"
        elif any(s == "MATCH_NOT_FOUND" for s in statuses.values()):
            answer_status = "MATCH_NOT_FOUND"
        elif any(s == "INSUFFICIENT_PARAMETERS" for s in statuses.values()):
            answer_status = "INSUFFICIENT_PARAMETERS"
        else:
            answer_status = "GROUNDED"

        clean_outputs = localize_en_obj(_strip_sql(outputs)) if en else _strip_sql(outputs)
        synth_prompt = (
            f"[User Question]\n{query}\n\n[Applied Parameters]\n{json.dumps(params, ensure_ascii=False)}\n"
            f"[Parameter Validation Notes]\n{json.dumps(notes, ensure_ascii=False)}\n\n"
            f"[Tool Execution Results JSON]\n{json.dumps(clean_outputs, ensure_ascii=False, default=str)}"
            if en else
            f"[사용자 질문]\n{query}\n\n[적용 파라미터]\n{json.dumps(params, ensure_ascii=False)}\n"
            f"[파라미터 검증 메모]\n{json.dumps(notes, ensure_ascii=False)}\n\n"
            f"[도구 실행 결과 JSON]\n{json.dumps(clean_outputs, ensure_ascii=False, default=str)}"
        )
        synth = call_vertex_gemini(
            prompt=synth_prompt,
            system_instruction=SYNTH_SYS_EN if en else SYNTH_SYS,
            response_mime_type="text/plain", temperature=0.1, max_tokens=2048,
            model_name=self.model_name, project_id=self.project_id)
        if synth.get("status") != "SUCCESS" or not synth.get("text"):
            answer_status = "LLM_ERROR"
        p_tok = (decomp.get("prompt_tokens") or 0) + (synth.get("prompt_tokens") or 0)
        c_tok = (decomp.get("candidates_tokens") or 0) + (synth.get("candidates_tokens") or 0)
        llm_ms = (decomp.get("elapsed_ms") or 0) + (synth.get("elapsed_ms") or 0)
        body = synth.get("text") or (
            f"Vertex AI `{self.model_name}` call failed (HTTP {synth.get('http_code')}): {str(synth.get('error', ''))[:500]}"
            if en else
            f"Vertex AI `{self.model_name}` 응답 실패 (HTTP {synth.get('http_code')}): {str(synth.get('error', ''))[:500]}"
        )
        if en:
            markdown = (f"{body}\n\n---\n"
                        f"- LLM: Vertex AI `{self.model_name}` (`{self.project_id}`) · 2 calls · {p_tok + c_tok:,} tokens "
                        f"(Prompt {p_tok:,} / Output {c_tok:,}) · {llm_ms:,.0f} ms\n"
                        f"- BigQuery: `{self.server.fq}` · Graph `{self.server.graph}` · Jobs `{', '.join(job_ids)}`\n"
                        f"- Answer Status: `{answer_status}`")
            obs_reason = (f"Tool statuses {json.dumps(statuses, ensure_ascii=False)} · BigQuery Jobs {len(job_ids)} · "
                          f"Params {json.dumps({k: v for k, v in params.items() if v is not None}, ensure_ascii=False)}")
        else:
            markdown = (f"{body}\n\n---\n"
                        f"- LLM: Vertex AI `{self.model_name}` (`{self.project_id}`) · 2회 호출 · 토큰 {p_tok + c_tok:,} "
                        f"(입력 {p_tok:,} / 출력 {c_tok:,}) · {llm_ms:,.0f} ms\n"
                        f"- BigQuery: `{self.server.fq}` · Graph `{self.server.graph}` · Jobs `{', '.join(job_ids)}`\n"
                        f"- 응답 상태: `{answer_status}`")
            obs_reason = (f"도구 상태 {json.dumps(statuses, ensure_ascii=False)} · BigQuery Job {len(job_ids)}건 · "
                          f"파라미터 {json.dumps({k: v for k, v in params.items() if v is not None}, ensure_ascii=False)}")
        total = round(time.perf_counter() - t0, 2)
        return {
            "status": "SUCCESS",
            "answer_status": answer_status,
            "query": query,
            "applied_params": params,
            "param_notes": notes,
            "llm_telemetry": {"model": self.model_name, "project_id": self.project_id,
                              "decomposition_status": decomp.get("status"), "synthesis_status": synth.get("status"),
                              "prompt_tokens": p_tok, "candidates_tokens": c_tok, "elapsed_ms": round(llm_ms, 2)},
            "bq_telemetry": {"dataset": self.server.fq, "graph": self.server.graph, "job_ids": job_ids,
                             "tool_statuses": statuses},
            "lifecycle": {
                "step_1_thought": {"model": self.model_name, "extracted_parameters": params, "sub_goals": sub_goals,
                                   "execution_mode": "LIVE_GEMINI_BIGQUERY_CHAIN"},
                "step_2_tool_dispatch": {"dispatched_tools": dispatched},
                "step_3_observation": {"cross_domain_integration_reason": obs_reason},
                "step_4_synthesis": {"markdown": markdown},
            },
            "performance": {"total_elapsed_seconds": str(total)},
        }
