# 🚗 Auto-Settle AI — Project Handoff Document
> **Prepared for:** Team & Successor Developer  
> **Event / Track:** Confluentia Applied ML Hackathon — Milestone 2  
> **Status:** Production-Ready & Deployed Live  

---

## 📌 1. Project Overview & Objective

**Auto-Settle AI** is an autonomous, touchless First Notice of Loss (FNOL) insurance claims engine designed for minor motor vehicle damages in India (claims under ₹25,000 such as parking scrapes, door dings, and bumper abrasions).

* **The Problem:** Traditional motor claims in India take an average of **14 days** and cost insurers **₹3,500+ in surveyor inspection fees and administrative paperwork** per incident.
* **The Solution:** Auto-Settle AI settles minor claims in **under 60 seconds** via straight-through processing (STP):
  1. The user uploads a photo of vehicle damage.
  2. Vision AI identifies the damaged components and severity.
  3. **Strict deterministic business rules** compute repair costs, depreciation, and deductibles (**the AI never hallucinates or decides money**).
  4. If all 10 safety guardrails pass, an instant cash offer (75%–90% of net value) is presented.
  5. The claimant accepts and receives instant simulated **UPI disbursement** with an official IRDAI-compliant settlement receipt.
  6. If severe damage, duplicate photos, or fraud risks are detected, the system freezes payment and automatically routes the claim to a human adjuster workbench.

---

## 🔗 2. Key URLs & Repository Links

* **Live Deployed Application:** [https://auto-settle-ng434.streamlit.app/](https://auto-settle-ng434.streamlit.app/)
* **GitHub Repository:** [https://github.com/namang34/Auto-Settle-AI](https://github.com/namang34/Auto-Settle-AI)
* **Default Branch:** `main` (auto-deploys to Streamlit Community Cloud on push)

---

## 📂 3. Repository Structure & Key Files

| File / Folder | Role & Description |
| :--- | :--- |
| **`app.py`** | Main Streamlit application. Contains the customer upload portal, quotation breakdown, PhonePe-style UPI payout card, vector SVG loading animations, bilingual translation engine, and the enterprise Adjuster Dashboard. |
| **`core.py`** | **The Core Brain (Deterministic Engine).** Contains parts pricing tables (`PARTS`), labor rates (`RATE = 500`), depreciation curves, policy excess deductions, settlement band math (`75%–90%`), and 10 underwriting safety guardrails. Zero external LLM code runs inside the valuation logic. |
| **`samples/`** | Bundled high-resolution offline vehicle photos (`demo_bumper_scrape.jpg`, `demo_door_dent.jpg`, `demo_severe_crash.jpg`) used for 1-click foolproof demo presentations. |
| **`claims_db.json`** | Local JSON database acting as the claims queue, audit trail, and SHA-256 photo fingerprint ledger. |
| **`test_core.py`** | Comprehensive pytest test suite verifying valuation math, prompt injection defenses, and guardrail escalations. |
| **`requirements.txt`** | Lightweight runtime dependencies: `streamlit`, `pillow`, `opencv-python-headless`, `pytest`, `requests`. |

---

## ✅ 4. What Has Been Built & Completed

### A. Customer FNOL Intake
1. **Photo Quality Assurance:** Pre-submission check using OpenCV for blur (Laplacian variance $>75\%$) and mean luminance exposure before sending to the model.
2. **Smart "Auto-Detect" by Default:** `"Which part is damaged?"` defaults to `🤖 Unsure · Let AI Auto-Detect (Recommended)`. Claimants don't need to know automotive terms; the vision model locates all panels without raising false mismatch flags.
3. **Multi-Model Support:** Native integration supporting Gemini 2.5 Flash, Groq (Llama 3.2 Vision), OpenRouter, or local Ollama.

### B. Business Logic & Zero AI Hallucination (`core.py`)
1. **Separation of Concerns:** The AI vision model only *describes* damage (part, type, severity, bounding box). Fixed Python code computes all rupee values.
2. **Financial Formulation:**
   - Gross Estimate = `(Parts Cost × Depreciation) + Labor`
   - Net Claim = `max(0, Gross - Policy Deductible)`
   - Settlement Band = `[75% × Net, 90% × Net]`
3. **10 Underwriting Safety Guardrails:** Instant escalation to a human surveyor triggers on:
   - Severe structural damage or shattered safety elements (headlights, glass)
   - AI confidence score $<70\%$
   - Net repair estimate exceeding the auto-settle cap (₹25,000)
   - Duplicate photo detection via cryptographic SHA-256 hashing
   - Unusable photo quality or lapsed policy status

### C. Fintech & User Experience Upgrades
1. **Before/After Savings Analytics:** Visual bar chart contrasting workshop repair (₹8,295, 14 days) against instant cash (₹4,859, $<60$s, saving ₹3,436 / 41%).
2. **Google Pay / PhonePe-Grade Payout Screen:**
   * Hardware-accelerated SVG checkmark animation with emerald ambient halo.
   * Pre-filled demo UPI (`rahul.demo@okhdfcbank`) for 1-click execution.
   * Auto-generated IMPS transaction ID and official downloadable text receipt.
   * `🔄 Run Next Claim Demo` button to reset state without refreshing the browser.
3. **Vector Car Outline Laser Scanning Animation:** Replaced the old emoji animation with an SVG sedan wireframe that fills with color as a laser beam sweeps across.
4. **Bilingual Engine:** Segmented pill toggle in the navbar switching between **English** and **हिंदी** across all UI elements via `T_(en, hi)`.

### D. Enterprise Adjuster Console (Admin Mode)
1. **Executive KPI Strip:** Live metrics for total claims, straight-through processing rate (STP %), average settlement turnaround time, and cumulative insurer savings.
2. **Status Queue Filters:** Segmented pills filtering claims by *All*, *Needs Review*, *Open*, and *Settled*.
3. **Side-by-Side Review Workbench:** Split-screen layout displaying the vehicle photo with annotated bounding boxes on the left, escalation flags and risk scores on the right, and one-click *Approve Payout* / *Reject Claim* overrides.

---

## ⚡ 5. 60-Second Presentation Script for Judges

When demoing the project live, follow this exact sequence:

1. **The Hook (10s):**
   > *"Minor motor claims in India take 14 days and cost ₹3,500+ in administrative overhead. Auto-Settle AI settles minor bumper and dent claims in under 60 seconds with strict deterministic financial guardrails."*
2. **The 1-Click Happy Path (20s):**
   - In the **New Claim** tab, expand `⚡ Pre-filled sample cases`.
   - Click **Run Demo** on **Case 1: Bumper Corner Scrape**.
   - Show the damage bounding box, the parts breakdown table, and the **Savings Widget** (*₹3,436 / 41% saved*).
   - Click **⚡ Accept ₹4,859 & Disburse Now** $\to$ Show the PhonePe-style animated payout card $\to$ click **Download Receipt**.
3. **The Guardrail & Underwriter Escalation (15s):**
   - Click **🔄 Run Next Claim Demo** $\to$ click **Run Demo** on **Case 3: Severe Front Collision**.
   - Point out the red warning banner: the AI caught severe damage and automatically froze payout, routing it to an adjuster.
4. **The Adjuster Workbench (15s):**
   - Flip the **Admin mode** toggle in the top navbar $\to$ go to **Adjuster Dashboard**.
   - Show the **KPI Strip** and the **Side-by-Side Review Workbench** where an adjuster inspects the photo and can override with an approval or rejection.

---

## 🛠️ 6. How to Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/namang34/Auto-Settle-AI.git
cd Auto-Settle-AI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run unit tests
pytest test_core.py -v

# 4. Launch Streamlit
streamlit run app.py
```

*Note: The app runs 100% locally out-of-the-box using the bundled sample photos. To test live external camera uploads, configure `GEMINI_API_KEY` or `GROQ_API_KEY` in `.streamlit/secrets.toml`.*

---

## 🚀 7. Recommended Future Roadmap (Next Milestones)

If extending the project further:
1. **Real Payment Gateway Integration:** Replace the simulated IMPS payout with RazorpayX or Cashfree Payouts API webhooks.
2. **RC / Number Plate OCR:** Add license plate recognition (e.g. EasyOCR) to cross-verify vehicle make, model, and active policy data from the Vahan database.
3. **Persistent Cloud Database:** Migrate `claims_db.json` to Supabase (PostgreSQL) or Firebase Firestore for multi-user adjuster concurrency.
4. **Fraud Detection Model:** Integrate image metadata (EXIF) and reverse-image search checks to detect stock photos downloaded from the internet.
