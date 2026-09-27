# Enterprise Knowledge Wiki: Core Entities Directory (Layer 2)
Canonical entities harmonized across structured DW tables and unstructured policy guides:

## 1. Customer Contract Ledger (`customer_contracts.csv`)
- `CONTRACT_DEMO_101` (`CUST_DEMO_001` · General VIP · `DEV-S26U-256` · `PLAN-5G-85` · 120 Days Elapsed)
- `CONTRACT_DEMO_102` (`CUST_DEMO_002` · General Standard · `DEV-S26U-256` · `PLAN-5G-130` · 224 Days Elapsed)
- `CONTRACT_DEMO_103` (`CUST_DEMO_003` · Senior Welfare · `DEV-IP16P-256` · `PLAN-5G-85` · 88 Days Elapsed · `SENIOR_EXEMPT`)

## 2. Terminal Device Master (`devices.csv`)
- `Galaxy S26 Ultra 256GB` (`DEV-S26U-256`, Factory Price: 1,698,400 KRW)
- `Galaxy S26 Ultra 512GB` (`DEV-S26U-512`, Factory Price: 1,841,400 KRW)
- `iPhone 16 Pro 256GB` (`DEV-IP16P-256`, Factory Price: 1,700,000 KRW)
- `iPhone 16 Pro 512GB` (`DEV-IP16P-512`, Factory Price: 2,000,000 KRW)

## 3. Tariff Plan Master (`plans.csv`)
- `5G Premier Super` (`PLAN-5G-130`, 130,000 KRW, Baseline Tier: True)
- `5G Premier Essential` (`PLAN-5G-85`, 85,000 KRW, Baseline Tier: True)
- `5G Slim (Baseline Threshold)` (`PLAN-5G-45`, 45,000 KRW, Baseline Tier: True)
- `5G Light (Below Baseline)` (`PLAN-5G-37`, 37,000 KRW, Baseline Tier: False)

## 4. Subsidy Policy Master (`subsidies.csv`)
- `POL-2026-001` (`DEV-S26U-256` + `PLAN-5G-130`: Basic 500,000 + Dist 75,000 = 575,000 KRW)
- `POL-2026-002` (`DEV-S26U-256` + `PLAN-5G-85`: Basic 450,000 + Dist 67,500 = 517,500 KRW)
- `POL-2026-004` (`DEV-S26U-256` + `PLAN-5G-37`: Basic 150,000 + Dist 22,500 = 172,500 KRW)
