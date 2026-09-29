# Enterprise Knowledge Wiki: Semantic Concepts & Edges (Layer 3)
In the Agentic Ontology Studio graph model, **Entities are represented as Nodes** and **Semantic Concepts/Relationships are represented as Edges**:

1. `USES_DEVICE` (`개통 단말기 관계`): Links a Customer Contract (`tb_customer_contract`) to its Terminal Device (`tb_device_master`).
2. `SUBSCRIBES_PLAN` (`가입 요금제 관계`): Links a Customer Contract (`tb_customer_contract`) to its Tariff Plan (`tb_plan_master`).
3. `HAS_SUBSIDY_POLICY` (`단말×요금제 지원금 결합`): Connects a Terminal Device (`tb_device_master`) to a Tariff Plan (`tb_plan_master`) with public and distribution subsidy amounts.
4. `APPLIES_TO_PLAN` (`비즈니스 규칙 적용`): Binds a codified Domain Rule (`tb_domain_rules`) to Tariff Plans (`tb_plan_master`) with SHA-256 chunk grounding.
