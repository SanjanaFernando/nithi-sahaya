# Representative semantic-search review

**Run date:** 25 October 2026  
**Method:** Gemini query embeddings (`gemini-embedding-001`) searched against local FAISS; top 8 returned. Retrieval relevance only; answer generation was not evaluated.  
**Index fingerprint:** `9960e99fd1438c8856ee48b664cc199e6a19d1dd5ce92bdbfa1b41e201398864`  
**Full ranked output:** `semantic_search_review.json`

## Retirement age

**Query:** What is the minimum retirement age for workers in Sri Lanka?

**Judgment:** PASS - exact Act retrieved at ranks 1, 3, and supporting provisions; all top 8 are from the Minimum Retirement Age of Workers Act.

| Rank | Score | Retrieved section | Source page |
|---:|---:|---|---:|
| 1 | 0.7805 | Minimum Retirement Age of Workers Act s.2 (`ch00_minimum_retirement_age_of_workers_s2`) | ch00_minimum_retirement_age_of_workers.pdf p.2 |
| 2 | 0.7569 | Minimum Retirement Age of Workers Act SCHEDULE II (`ch00_minimum_retirement_age_of_workers_sschedule_ii`) | ch00_minimum_retirement_age_of_workers.pdf p.15 |
| 3 | 0.7503 | Minimum Retirement Age of Workers Act s.3 (`ch00_minimum_retirement_age_of_workers_s3`) | ch00_minimum_retirement_age_of_workers.pdf p.2 |
| 4 | 0.7182 | Minimum Retirement Age of Workers Act s.19 (`ch00_minimum_retirement_age_of_workers_s19`) | ch00_minimum_retirement_age_of_workers.pdf p.15 |
| 5 | 0.7180 | Minimum Retirement Age of Workers Act s.18 (`ch00_minimum_retirement_age_of_workers_s18`) | ch00_minimum_retirement_age_of_workers.pdf p.13 |
| 6 | 0.7154 | Minimum Retirement Age of Workers Act s.12 (`ch00_minimum_retirement_age_of_workers_s12`) | ch00_minimum_retirement_age_of_workers.pdf p.10 |
| 7 | 0.7153 | Minimum Retirement Age of Workers Act s.8 (`ch00_minimum_retirement_age_of_workers_s8`) | ch00_minimum_retirement_age_of_workers.pdf p.6 |
| 8 | 0.7091 | Minimum Retirement Age of Workers Act s.1 (`ch00_minimum_retirement_age_of_workers_s1`) | ch00_minimum_retirement_age_of_workers.pdf p.2 |

## Minimum wage

**Query:** What is the current national minimum monthly wage in Sri Lanka?

**Judgment:** PARTIAL / UNSAFE - rank 1 is the correct Act and section, but its indexed amount is stale because the corpus update review flags the 2025 amendment. The answer engine should refuse when this stale source is retrieved. Several lower ranks are unrelated foreign-employment provisions.

| Rank | Score | Retrieved section | Source page |
|---:|---:|---|---:|
| 1 | 0.7774 | National Minimum Wage of Workers Act s.3 (`ch02_national_minimum_wage_of_workers_act_no_3_of_2016_s3`) | ch02_national_minimum_wage_of_workers_act_no_3_of_2016.pdf p.2 |
| 2 | 0.7021 | Sri Lanka Bureau of Foreign Employment Act s.1 (page 20 schedule) (`ch06_sri_lanka_bureau_of_foreign_employment_act_s1_p20_2`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.20 |
| 3 | 0.6948 | Budgetary Relief Allowance of Workers Act s.3(2) (`ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016_s3_2`) | ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016.pdf p.2 |
| 4 | 0.6813 | Sri Lanka Bureau of Foreign Employment Act s.2 (page 20 schedule) (`ch06_sri_lanka_bureau_of_foreign_employment_act_s2_p20_2`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.20 |
| 5 | 0.6807 | Budgetary Relief Allowance of Workers Act s.3(1) (`ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016_s3_1`) | ch02_budgetary_relief_allowance_of_workers_act_no_4_of_2016.pdf p.2 |
| 6 | 0.6725 | National Minimum Wage of Workers Act s.15 (`ch02_national_minimum_wage_of_workers_act_no_3_of_2016_s15`) | ch02_national_minimum_wage_of_workers_act_no_3_of_2016.pdf p.11 |
| 7 | 0.6723 | Sri Lanka Bureau of Foreign Employment Act s.3 (page 20 schedule) (`ch06_sri_lanka_bureau_of_foreign_employment_act_s3_p20_2`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.20 |
| 8 | 0.6673 | Budgetary Relief Allowance of Workers (No. 2) Law s.3 (`ch02_budgetary_relief_allowance_of_workers_act_no_2_s3`) | ch02_budgetary_relief_allowance_of_workers_act_no_2.pdf p.1 |

## Gratuity

**Query:** When must an employer pay gratuity to an employee who resigns or retires?

**Judgment:** PASS for retrieval relevance - ranks 1-8 all point to Payment of Gratuity Act provisions relevant to eligibility, calculation, payment, or enforcement. Human answer accuracy/currentness not evaluated by this retrieval-only run.

| Rank | Score | Retrieved section | Source page |
|---:|---:|---|---:|
| 1 | 0.7564 | Payment of Gratuity Act s.5 (`ch05_payment_of_gratuity_s5`) | ch05_payment_of_gratuity.pdf p.2 |
| 2 | 0.7440 | Payment of Gratuity Act s.3 (`ch05_payment_of_gratuity_s3`) | ch05_payment_of_gratuity.pdf p.1 |
| 3 | 0.7314 | Payment of Gratuity Act s.6 (`ch05_payment_of_gratuity_s6`) | ch05_payment_of_gratuity.pdf p.3 |
| 4 | 0.7144 | Payment of Gratuity Act s.2 (`ch05_payment_of_gratuity_s2`) | ch05_payment_of_gratuity.pdf p.1 |
| 5 | 0.6902 | Payment of Gratuity Act s.20 (`ch05_payment_of_gratuity_s20`) | ch05_payment_of_gratuity.pdf p.8 |
| 6 | 0.6865 | Payment of Gratuity Act s.17 (`ch05_payment_of_gratuity_s17`) | ch05_payment_of_gratuity.pdf p.7 |
| 7 | 0.6843 | Payment of Gratuity Act s.18 (`ch05_payment_of_gratuity_s18`) | ch05_payment_of_gratuity.pdf p.8 |
| 8 | 0.6841 | Payment of Gratuity Act s.1 (`ch05_payment_of_gratuity_s1`) | ch05_payment_of_gratuity.pdf p.1 |

## Dismissal / TEWA

**Query:** When may an employer terminate a worker without prior approval under TEWA?

**Judgment:** PASS for retrieval relevance - rank 1 is TEWA s.2, directly on prior consent/Commissioner approval; other high ranks are related TEWA sections. Check exclusions and current law before answering.

| Rank | Score | Retrieved section | Source page |
|---:|---:|---|---:|
| 1 | 0.7007 | Termination of Employment of Workmen Act s.2 (`ch01_termination_of_employment_of_workmen_s2`) | ch01_termination_of_employment_of_workmen.pdf p.1 |
| 2 | 0.6679 | Termination of Employment of Workmen Act s.5 (`ch01_termination_of_employment_of_workmen_s5`) | ch01_termination_of_employment_of_workmen.pdf p.3 |
| 3 | 0.6593 | Employment of Trainees (Private Sector) Act s.10 (`ch02_employment_of_trainees_private_sector_s10`) | ch02_employment_of_trainees_private_sector.pdf p.2 |
| 4 | 0.6532 | Termination of Employment of Workmen Act s.3 (`ch01_termination_of_employment_of_workmen_s3`) | ch01_termination_of_employment_of_workmen.pdf p.2 |
| 5 | 0.6453 | Termination of Employment of Workmen Act s.6 (`ch01_termination_of_employment_of_workmen_s6`) | ch01_termination_of_employment_of_workmen.pdf p.3 |
| 6 | 0.6403 | Termination of Employment of Workmen Act s.17A (`ch01_termination_of_employment_of_workmen_s17a`) | ch01_termination_of_employment_of_workmen.pdf p.6 |
| 7 | 0.6371 | Termination of Employment of Workmen Act s.6A (`ch01_termination_of_employment_of_workmen_s6a`) | ch01_termination_of_employment_of_workmen.pdf p.3 |
| 8 | 0.6359 | Termination of Employment of Workmen Act s.4 (`ch01_termination_of_employment_of_workmen_s4`) | ch01_termination_of_employment_of_workmen.pdf p.3 |

## Out of scope

**Query:** What is the legal process for adopting a child in Sri Lanka?

**Retrieval judgment:** FAIL - no relevant child-adoption source is in this labour corpus; retrieval returns unrelated labour provisions with scores 0.6198-0.6311. The 0.35 score threshold alone does not refuse it. **Runtime handling:** the new fail-closed scope classifier was smoke-tested and refused this query before retrieval; see the overall result below.

| Rank | Score | Retrieved section | Source page |
|---:|---:|---|---:|
| 1 | 0.6311 | Sri Lanka Bureau of Foreign Employment Act s.27 (`ch06_sri_lanka_bureau_of_foreign_employment_act_s27`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.7 |
| 2 | 0.6288 | Sri Lanka Bureau of Foreign Employment Act s.26 (`ch06_sri_lanka_bureau_of_foreign_employment_act_s26`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.6 |
| 3 | 0.6236 | Employment of Women, Young Persons and Children Act s.10 (`ch03_employment_of_women_young_person_and_children_s10`) | ch03_employment_of_women_young_person_and_children.pdf p.4 |
| 4 | 0.6231 | Sri Lanka Bureau of Foreign Employment Act s.1 (page 20 schedule) (`ch06_sri_lanka_bureau_of_foreign_employment_act_s1_p20_2`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.20 |
| 5 | 0.6213 | Indian Immigrant Labour Ordinance s.17 (`ch07_indian_immigrant_labour_s17`) | ch07_indian_immigrant_labour.pdf p.4 |
| 6 | 0.6208 | Sri Lanka Bureau of Foreign Employment Act s.3 (`ch06_sri_lanka_bureau_of_foreign_employment_act_s3`) | ch06_sri_lanka_bureau_of_foreign_employment_act.pdf p.1 |
| 7 | 0.6203 | Fee-Charging Employment Agencies Act s.2 (`ch06_fee_charging_employment_agencies_s2`) | ch06_fee_charging_employment_agencies.pdf p.1 |
| 8 | 0.6198 | Fee-Charging Employment Agencies Act s.4 (`ch06_fee_charging_employment_agencies_s4`) | ch06_fee_charging_employment_agencies.pdf p.3 |

## Overall result

Three in-scope searches retrieve strongly relevant Act provisions. Minimum wage retrieves the right section but its indexed amount is outdated and must be blocked under the stale-source policy. The dismissal search retrieves TEWA s.2 first. The adoption query retrieved unrelated labour sections at high similarity, confirming that retrieval score alone does not detect out-of-scope requests. A fail-closed Gemini scope classifier was added before retrieval. Live smoke results: all four labour questions were classified in scope; adoption was classified out of scope, and `AnswerEngine.ask` returned `refused=true`, `reason=out_of_scope`, with no sources before retrieval. A local stale-wage retrieval-path check returned `refused=true`, `reason=corpus_update_required`. Classifier errors or malformed results also fail closed. These are targeted smoke checks; AI classification can still err.
