-- BigQuery SQL:2023 Property Graph DDL Definition
CREATE OR REPLACE PROPERTY GRAPH `my-project.my_dataset.ENTERPRISE_SUBSIDY_GRAPH`
  NODE TABLES (
    `my-project.my_dataset.dw_device_master`
      KEY (device_id)
      LABEL DeviceNode
      PROPERTIES (device_id, model_code, pet_name, storage, factory_price),
    `my-project.my_dataset.dw_plan_master`
      KEY (plan_id)
      LABEL PlanNode
      PROPERTIES (plan_id, plan_name, network_type, monthly_fee, is_baseline_tier),
    `my-project.my_dataset.dw_subsidy_policy_master`
      KEY (policy_id)
      LABEL SubsidyNode
      PROPERTIES (policy_id, device_id, plan_id, basic_subsidy, distribution_subsidy),
    `my-project.my_dataset.ont_doc_chunks`
      KEY (chunk_id)
      LABEL DocChunkNode
      PROPERTIES (chunk_id, title, hash_anchor, content)
  )
  EDGE TABLES (
    `my-project.my_dataset.dw_subsidy_policy_master`
      KEY (policy_id)
      SOURCE KEY (policy_id) REFERENCES `my-project.my_dataset.dw_subsidy_policy_master` (policy_id)
      DESTINATION KEY (device_id) REFERENCES `my-project.my_dataset.dw_device_master` (device_id)
      LABEL COVERS_DEVICE,
    `my-project.my_dataset.dw_subsidy_policy_master`
      KEY (policy_id)
      SOURCE KEY (policy_id) REFERENCES `my-project.my_dataset.dw_subsidy_policy_master` (policy_id)
      DESTINATION KEY (plan_id) REFERENCES `my-project.my_dataset.dw_plan_master` (plan_id)
      LABEL REQUIRES_PLAN
  );
