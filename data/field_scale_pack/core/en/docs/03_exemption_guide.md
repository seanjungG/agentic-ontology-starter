# Penalty Exemption Guide

> Document no.: GUIDE-SUB-03 · Effective date: 2026-01-01 · Audience: store and customer-center support agents · De-identified synthetic document for hands-on training

## 1. Senior / welfare exemption

1. If a senior customer aged 65 or older, or a customer registered for welfare (system welfare status SENIOR_EXEMPT), switches to a **senior/welfare plan**, the clawback is **fully exempt (KRW 0)** even within 180 days.
2. Downgrading to a regular plan that is not a senior/welfare plan is not exempt.
3. A senior/welfare plan is a plan whose tier category (tier_category) in the plan table is SENIOR_WELFARE.

## 2. Military service pause

1. For a customer who pauses the line for military service (the pause is processed after confirming the system welfare status MILITARY_PAUSE_ELIGIBLE), the 180-day retention clock **stops** for the duration of service.
2. The pause itself does not incur a penalty. When the line is used again after discharge, the customer completes the remaining retention period.

## 3. Exemption check procedure

- Before explaining an exemption, support agents must always check the customer's welfare status and the tier category of the new plan.
- If no exemption reason is confirmed, apply the standard clawback rule (GUIDE-SUB-02).
