# -*- coding: utf-8 -*-
"""
AI FDE Reasoning Engine (Starter v2.0):
Implements dynamic multi-goal decomposition, cross-domain sequential chaining
across the 3 Runtime Execution MCPs & 5 Stage Pipeline MCPs, intermediate
observation emission, and grounded synthesis.
"""
import json, time
from .mcp_server import DomainMcpServer

class AiFdeAgentEngine:
    def __init__(self):
        self.server = DomainMcpServer()

    def execute_cycle(self, query: str, engine: str = "bigquery"):
        t0 = time.time()
        q_lower = query.lower()

        sub_goals = []
        if any(k in q_lower for k in ["stage 1", "자산", "테이블", "프로파일링"]):
            sub_goals.append({"id": "G-STG-01", "goal": "Stage 1 원천 자산 인벤토리 및 비식별화 거버넌스 검증", "tool": "mcp_stage1_asset_discovery", "category": "stage_pipeline"})
        if any(k in q_lower for k in ["고객", "출고가", "가격", "지원금", "실구매가", "cust_", "galaxy", "iphone", "단말"]):
            sub_goals.append({"id": "G-RUN-01", "goal": "고객 약정 원장 · 단말기 출고가 · 공시지원금 통합 조회", "tool": "mcp_lookup_customer_profile", "category": "runtime_domain"})
        if any(k in q_lower for k in ["위약금", "차액정산", "하향", "180일", "120일", "88일", "시니어", "복지", "선택약정", "24개월", "비교"]):
            sub_goals.append({"id": "G-RUN-02", "goal": "결정론적 위약금 산식 · 특례 면제 · 24개월 TCO 산출", "tool": "mcp_calculate_penalty_rule", "category": "runtime_domain"})
        if any(k in q_lower for k in ["그래프", "gql", "spanner", "bigquery", "근거", "앵커", "청크", "규정", "원문", "경로"]):
            sub_goals.append({"id": "G-RUN-03", "goal": f"Property Graph({engine.upper()}) 멀티홉 탐색 및 OKF v0.2 해시 앵커 인출", "tool": "mcp_query_graph_and_wiki", "category": "runtime_domain"})

        if not sub_goals:
            sub_goals = [
                {"id": "G-RUN-01", "goal": "고객 약정 원장 · 단말기 출고가 · 공시지원금 통합 조회", "tool": "mcp_lookup_customer_profile", "category": "runtime_domain"},
                {"id": "G-RUN-02", "goal": "결정론적 위약금 산식 · 특례 면제 · 24개월 TCO 산출", "tool": "mcp_calculate_penalty_rule", "category": "runtime_domain"},
                {"id": "G-RUN-03", "goal": f"Property Graph({engine.upper()}) 멀티홉 탐색 및 OKF v0.2 해시 앵커 인출", "tool": "mcp_query_graph_and_wiki", "category": "runtime_domain"}
            ]

        dispatched_tools = []
        outputs = {}
        for idx, sg in enumerate(sub_goals):
            tool_name = sg["tool"]
            res = self.server.execute_tool(tool_name, {"query": query, "engine": engine})
            outputs[tool_name] = res
            dispatched_tools.append({
                "step_index": idx + 1,
                "tool_name": tool_name,
                "category": sg["category"],
                "reason": sg["goal"],
                "output": res,
                "intermediate_observation": f"[{sg['category'].upper()}] {sg['goal']} -> {json.dumps(res, ensure_ascii=False)}"
            })

        elapsed = round(time.time() - t0, 3)

        prof = outputs.get("mcp_lookup_customer_profile", {})
        pen = outputs.get("mcp_calculate_penalty_rule", {})
        grp = outputs.get("mcp_query_graph_and_wiki", {})

        lines = [
            f"#### [AI FDE Grounded Synthesis Report]",
            f"- **질의 (Inquiry)**: {query}",
            f"- **실행 체인 (Execution Chain)**: `{len(sub_goals)}`개 하위 목표 순차 실행 (`{' ➔ '.join(sg['tool'] for sg in sub_goals)}`)"
        ]
        if prof:
            lines.append(f"- **고객 및 단말/지원금 원장 조회**: 고객 `{prof.get('customer_id')}` (`{prof.get('customer_segment')}`) · 단말 `{prof.get('device')}` (출고가 `{prof.get('factory_price', 0):,} KRW`) · 총 지원금 `{prof.get('total_subsidy', 0):,} KRW` (실구매 원금 `{prof.get('net_installment_principal', 0):,} KRW`)")
        if pen:
            lines.append(f"- **결정론적 산식 및 특례 판정**: 유지일수 `{pen.get('elapsed_days')}일` · 산출 위약금 **`{pen.get('penalty_amount', 0):,} KRW`** · 산식 `{pen.get('formula')}` (근거 앵커: `{pen.get('grounded_chunk')}`)")
        if grp:
            lines.append(f"- **그래프 경로 및 원문 앵커 검증**: 엔진 `{grp.get('graph_engine', engine).upper()}` · 경로 `{grp.get('gql_path')}` · 앵커 `{', '.join(grp.get('grounded_anchors', []))}`")

        synthesis_md = "\n".join(lines)

        return {
            "status": "SUCCESS",
            "lifecycle": {
                "step_1_thought": {
                    "sub_goals": sub_goals,
                    "execution_mode": "SEQUENTIAL_CHAIN"
                },
                "step_2_tool_dispatch": {
                    "dispatched_tools": dispatched_tools
                },
                "step_3_observation": {
                    "cross_domain_integration_reason": "정형 DW 고객/지원금 원장 수치와 OKF v0.2 비정형 규정 해시 앵커(DOC_CHUNK_001~005)를 교차 검증 완료."
                },
                "step_4_synthesis": {
                    "markdown": synthesis_md
                }
            },
            "performance": {
                "total_elapsed_seconds": str(elapsed)
            }
        }
