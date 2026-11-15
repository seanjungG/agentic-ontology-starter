# Plan Retention & Clawback Guide

> Document no.: GUIDE-SUB-02 · Effective date: 2026-01-01 · Audience: store and customer-center support agents · De-identified synthetic document for hands-on training

## 1. Retention principle

A customer who activated with the public subsidy must keep a plan **at or above the baseline tier** for **180 days** from the activation date.
This is called the '180-day retention'. Customers who activated with the 25% discount contract are not subject to retention.

## 2. Baseline plan tier

- For customers activating a 5G device, the baseline tier is a **monthly fee of KRW 45,000**.
- In the system, a plan whose baseline flag (is_baseline_tier) in the plan table is true is at or above the baseline.
- Examples of plans below the baseline: 5G Lite (KRW 37,000/month), LTE Basic (KRW 33,000/month).

## 3. Clawback (penalty)

1. A customer who downgrades to a plan **below** the baseline tier within 180 days pays a clawback.
2. Formula: **clawback = (public subsidy received at activation − reference public subsidy for the lower plan) × (180 − elapsed days) ÷ 180**
   - The 'reference public subsidy for the lower plan' is the public subsidy the customer would have received if the same device had been activated on the lower plan (per the subsidy policy table by device and plan).
   - The retailer additional subsidy is not subject to clawback. Only the public subsidy is used in the calculation.
   - Amounts below one won are rounded to the nearest won.
3. If the elapsed days are 180 or more, the clawback is **KRW 0**.
4. A change between plans at or above the baseline tier (e.g., KRW 85,000/month → KRW 61,000/month) is not subject to clawback.

## 4. Calculation example

With a public subsidy of KRW 400,000 at activation, a reference public subsidy of KRW 100,000 for the lower plan, and 60 elapsed days:
(400,000 − 100,000) × (180 − 60) ÷ 180 = KRW 200,000.
