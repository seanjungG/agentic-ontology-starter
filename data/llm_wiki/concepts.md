# Enterprise Knowledge Wiki: Semantic Concepts & Edges (Layer 3)
In the Agentic Ontology Studio graph model, **Entities are represented as Nodes** and **Semantic Concepts/Relationships are represented as Edges**:

1. `SUBSCRIBES_CONTRACT` (`약정 가입 관계`): Links a Customer Contract (`고객 약정 원장`) to a Tariff Plan (`모바일 요금제`) and Terminal Device (`단말기 모델`).
2. `COVERS_DEVICE` (`단말 지원금 적용`): Connects a Subsidy Policy (`공시지원금 정책`) to its eligible Terminal Device (`단말기 모델`).
3. `REQUIRES_PLAN` (`요금제 티어 요건`): Connects a Subsidy Policy (`공시지원금 정책`) to its required Tariff Plan (`모바일 요금제`).
4. `APPLIES_RULE` (`위약금 규칙 적용`): Binds a codified Domain Rule (`약정 위약금 규칙`) to Tariff Plans and Customer Contracts.
5. `EXEMPTS_PENALTY` (`특례 면제 관계`): Binds Senior/Welfare or Military pause clauses (`위약금 면제 특례`) to eligible customer segments.
6. `GROUNDED_IN` (`원문 해시 근거`): Anchors every Domain Rule (`약정 위약금 규칙`) to an immutable SHA-256 `DocChunk` (`정책 가이드 청크`).
