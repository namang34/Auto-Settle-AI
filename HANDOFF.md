# 🚗 Auto-Settle AI — Master Project Handoff & Milestone Compliance
> **Prepared for:** Team & Successor Developer (LLM Context Ready)  
> **Hackathon:** Confluentia Applied ML Hackathon — Milestone 2 (70% Weightage)  
> **Date of Checkpoint:** 22 October (First half of the day)  
> **Status:** Production-Ready, Battle-Tested & Deployed Live  

---

## 📌 1. Project URLs & Access

* **Live Deployed App:** [https://auto-settle-ng434.streamlit.app/](https://auto-settle-ng434.streamlit.app/)
* **GitHub Repository:** [https://github.com/namang34/Auto-Settle-AI](https://github.com/namang34/Auto-Settle-AI)
* **Default Branch:** `main` (auto-deploys to Streamlit Cloud on push)
* **Presentation Deck:** `Auto-Settle-AI-Updated.pptx` (in project artifacts)

---

## 🎯 2. Problem Statement Compliance Matrix (100% Coverage)

Every clause of the official problem statement **"Auto-Settle AI: Autonomous Video-to-Cash Claims Adjuster"** has been implemented and verified:

| Problem Statement Requirement | Code Implementation & Location | Status |
| :--- | :--- | :--- |
| **1. Assess Vehicle Damage:** Analyze uploaded images or videos to identify component, damage type, and severity. | `core.py` (`analyse_image`) & `app.py` (`to_jpeg`): Video frame extraction via OpenCV, multi-model vision parsing (Gemini / Groq / OpenRouter), bounding box coordinates, and severity categorization (*Minor / Moderate / Severe*). | **100% Done** |
| **2. Estimate Repair & Settlement Costs:** Map assessment to reference parts and labor database, calculate garage cost, establish allowable cash settlement range. | `core.py` (`PARTS`, `RATE = 500`, `assess`): Standard parts table, hourly labor rates, vehicle age depreciation (5%/year), policy excess deductible, and cash settlement band ($75\% - 90\%$). | **100% Done** |
| **3. Automated Settlement & Negotiation:** Present initial offer, respond intelligently to customer counteroffers, arrive at settlement within predefined financial limits. | `app.py` (`col_left`, `chat_counter_form`) & `core.py` (`negotiate`, `converse`): Initial offer presented with 1-click UPI payout, plus an interactive counteroffer expander bounded strictly by insurer ceiling. | **100% Done** |
| **4. Guardrails & Escalation Rules:** Prevent settlements outside approved range, identify uncertain or suspicious claims, escalate to human adjuster. | `core.py` (`assess` lines 164–176): 10 hard underwriter guardrails (severe damage, confidence $<70\%$, claim $>₹25\text{k}$ cap, duplicate image hash, lapsed policy, repeat claims). | **100% Done** |
| **5. Expected Output:** Website/app accepting images/videos, presenting detected damage and costs, interactive conversation, final cash offer or human escalation, and audit trail. | `app.py`: Full bilingual Streamlit portal, `claims_db.json` audit trail log, side-by-side human adjuster workbench with *Approve / Reject* buttons, and downloadable IRDAI voucher. | **100% Done** |

---

## 🏆 3. Bonus Considerations Compliance (Extra Points Strategy)

| Bonus Criterion (From PS Page 5) | Our Solution & Implementation | How to Claim Points in Pitch |
| :--- | :--- | :--- |
| **1. Efficient SLM Usage (<20B Parameters)** | We integrated **Groq Llama 3.2 11B Vision** and **Ollama Qwen2.5-VL 7B** directly into the engine switcher. | Explicitly show the navbar model switcher running the 11B/7B vision models with ultra-low latency ($<2$s response). |
| **2. Additional Domain Innovation** | **A. Offline Demo Safety Net:** 3 real-photo cases running 100% offline without API or Wi-Fi dependence.<br>**B. Before/After Savings Widget:** Direct visual proof of 41% insurer cost reduction and 14 days saved.<br>**C. Smart Auto-Detect by Default:** Claimants don't need to guess car panels.<br>**D. PhonePe/Google Pay Animated Card:** Realistic consumer fintech payout. | Emphasize that Auto-Settle is designed for the reality of the Indian motor insurance market (IRDAI sandbox & UPI rails). |

---

## 📊 4. Milestone 2 (70% Weightage) Presentation Checklist

The Milestone 2 evaluation on **22 October** requires presenting 5 core areas. Here is exactly where each is covered:

1. **Final Solution Design:**
   - Architecture: Dual-portal platform (Consumer FNOL + Enterprise Adjuster Dashboard).
   - Core Principle: The AI only *describes* damage; deterministic code decides every rupee.
2. **Feature Coverage:**
   - 100% of Problem Statement requirements covered (see matrix above).
3. **Technology Stack:**
   - Frontend: Streamlit, CSS3, Hardware-accelerated SVG vector animations.
   - Computer Vision: OpenCV (Laplacian variance sharpness, mean exposure, video frame sampling).
   - AI Models: Gemini 2.5 Flash, Groq Llama 3.2 11B Vision, OpenRouter, Ollama.
   - Deterministic Logic: Pure Python 3.11+, Pytest suite.
4. **Guardrails & Known Limitations:**
   - 10 automated escalation triggers preventing unauthorized payouts.
   - Known limitations: Synthetic edge cases, simulated banking IMPS/UPI API, single middle-frame extraction for video.
5. **Complete System Codebase:**
   - Live on Streamlit Cloud & pushed to GitHub `main`.

---

## 📂 5. Key File Inventory

| File / Folder | Role & What It Does |
| :--- | :--- |
| **`app.py`** | Main UI application. Customer intake, quotation breakdown, PhonePe-style UPI payout card, vector SVG loading animation, bilingual translation, and the Adjuster Dashboard. |
| **`core.py`** | **The Brain.** Deterministic valuation, parts/labor tables, depreciation curves, policy excess, settlement bands ($75\% - 90\%$), 10 safety guardrails, and negotiation logic. |
| **`samples/`** | Bundled high-resolution offline vehicle photos (`demo_bumper_scrape.jpg`, `demo_door_dent.jpg`, `demo_severe_crash.jpg`) for zero-risk presentations. |
| **`claims_db.json`** | Claims queue, audit trail, and SHA-256 photo hash database. |
| **`test_core.py`** | Pytest unit test suite verifying pricing, prompt injection defense, and guardrails. |
| **`HANDOFF.md`** | This comprehensive project handoff document. |
| **`README.md`** | High-level GitHub repository documentation with clean ASCII architecture. |

---

## 🎤 6. The Winning 60-Second Demo Sequence

When presenting to judges:

1. **The Hook (10s):**
   > *"Minor motor claims in India take 14 days and cost ₹3,500+ in administrative fees. Auto-Settle AI settles bumper scratches in under 60 seconds with strict deterministic rules, avoiding AI financial hallucinations."*
2. **The 1-Click Happy Path (20s):**
   - In **New Claim**, open `⚡ Pre-filled sample cases` $\to$ click **Run Demo** on **Case 1: Bumper Corner Scrape**.
   - Show the damage bounding box, the parts breakdown table, and the **Savings Widget** (*₹3,436 / 41% saved*).
   - Click **⚡ Accept ₹4,859 & Disburse Now** $\to$ Show the PhonePe-style animated payout card $\to$ click **Download Receipt**.
3. **The Guardrail Escalation (15s):**
   - Click **🔄 Run Next Claim Demo** $\to$ click **Run Demo** on **Case 3: Severe Front Collision**.
   - Show the red warning banner: the AI caught structural damage and frozen payout, routing to an adjuster.
4. **The Adjuster Workbench (15s):**
   - Flip **Admin mode** toggle in navbar $\to$ go to **Adjuster dashboard**.
   - Show the **KPI Strip** and the **Side-by-Side Review Workbench** with *Approve/Reject* buttons.

---

## 🚀 7. Future Roadmap (For Post-Milestone 2)

If continuing to hackathon finals:
1. **Real Payment Webhooks:** Connect RazorpayX or Cashfree Payouts API.
2. **Number Plate OCR:** Integrate Vahan API lookup for policy cross-referencing.
3. **Cloud Database:** Migrate `claims_db.json` to Supabase (PostgreSQL).
