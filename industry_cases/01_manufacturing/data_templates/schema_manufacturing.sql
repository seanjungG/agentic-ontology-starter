-- ============================================================================
-- Manufacturing Domain Schema (BigQuery Compatible SQL DDL)
-- Focus: POSCO Steel Mill & Hyundai Motor Automotive BOM/SCM
-- ============================================================================

-- 1. Equipment Master
CREATE TABLE IF NOT EXISTS `mfg_dw.TB_EQUIP_MASTER` (
  equip_id STRING NOT NULL,
  line_code STRING NOT NULL,
  equip_name STRING NOT NULL,
  install_date DATE,
  status STRING NOT NULL
);

-- 2. Realtime Sensor Telemetry
CREATE TABLE IF NOT EXISTS `mfg_dw.TB_SENSOR_TELEMETRY` (
  sensor_id STRING NOT NULL,
  equip_id STRING NOT NULL,
  metric_type STRING NOT NULL, -- 'VIBRATION', 'TEMPERATURE', 'PRESSURE'
  current_val FLOAT64 NOT NULL,
  warning_limit FLOAT64 NOT NULL,
  trip_limit FLOAT64 NOT NULL,
  measured_at TIMESTAMP NOT NULL
);

-- 3. Spare Parts Warehouse Inventory
CREATE TABLE IF NOT EXISTS `mfg_dw.TB_SPARE_PARTS_INV` (
  part_no STRING NOT NULL,
  part_name STRING NOT NULL,
  stock_qty INT64 NOT NULL,
  wh_location STRING NOT NULL,
  bin_no STRING NOT NULL
);

-- 4. Vehicle & Parts Engineering BOM
CREATE TABLE IF NOT EXISTS `mfg_dw.TB_PART_BOM` (
  part_no STRING NOT NULL,
  parent_part_no STRING,
  part_name STRING NOT NULL,
  category STRING NOT NULL,
  tier_level INT64 NOT NULL
);

-- 5. ECU Firmware Compatibility Matrix
CREATE TABLE IF NOT EXISTS `mfg_dw.TB_ECU_FIRMWARE` (
  fw_id STRING NOT NULL,
  part_no STRING NOT NULL,
  fw_version STRING NOT NULL,
  min_req_brake_fw STRING NOT NULL,
  release_status STRING NOT NULL
);
