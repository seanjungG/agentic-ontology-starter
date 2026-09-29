# Enterprise Knowledge Wiki: Semantic Concepts & Edges (Layer 3)
In the Agentic Ontology Studio graph model, **Entities are represented as Nodes** and **Semantic Concepts/Relationships are represented as Edges**:

1. `USES_DEVICE` (`Device Activation Edge`): Links a Customer Contract (`tb_customer_contract`) to its Terminal Device (`tb_device_master`).
2. `SUBSCRIBES_PLAN` (`Plan Subscription Edge`): Links a Customer Contract (`tb_customer_contract`) to its Tariff Plan (`tb_plan_master`).
3. `HAS_SUBSIDY_POLICY` (`Device × Plan Subsidy Binding`): Connects a Terminal Device (`tb_device_master`) to a Tariff Plan (`tb_plan_master`) with public and distribution subsidy amounts.
4. `APPLIES_TO_PLAN` (`Codified Business Rule Binding`): Binds a codified Domain Rule (`tb_domain_rules`) to Tariff Plans (`tb_plan_master`) with SHA-256 chunk grounding.
