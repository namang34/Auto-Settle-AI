import hashlib, io, json, os, tempfile, time
import streamlit as st
from PIL import Image, ImageDraw
import core

st.set_page_config(page_title="Auto-Settle AI", layout="wide")
DB = "claims_db.json"  # persistent store: claim queue, audit trail, photo fingerprints

def db_load():
    try: return json.load(open(DB))
    except Exception: return {"queue": [], "log": [], "hashes": []}
def db_save(d): json.dump(d, open(DB, "w"), indent=1)
def log(ev, detail):
    d = db_load(); d["log"].append({"t": time.strftime("%H:%M:%S"), "ev": ev, "detail": detail}); db_save(d)

def to_jpeg(raw, is_video):
    if is_video:
        import cv2
        p = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4"); p.write(raw); p.close()
        cap = cv2.VideoCapture(p.name); cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_FRAME_COUNT) // 2)
        ok, fr = cap.read(); cap.release()
        if not ok: raise ValueError("Could not read the video")
        img = Image.fromarray(fr[:, :, ::-1])
    else: img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((1280, 1280)); b = io.BytesIO(); img.save(b, "JPEG", quality=85); return img, b.getvalue()

# ---------- sidebar: guardrails + policy ----------
with st.sidebar:
    st.header("Guardrails")
    rails = {"lo": st.number_input("Offer floor (% of net claim)", 1, 100, 75) / 100,
             "hi": st.number_input("Offer ceiling (%)", 1, 100, 90) / 100,
             "step": st.number_input("Concession per round (%)", 1, 50, 4) / 100,
             "max_rounds": st.number_input("Max negotiation rounds", 1, 10, 3),
             "min_conf": st.number_input("Min AI confidence (%)", 0, 100, 70),
             "cap": st.number_input("Auto-settle cap (\u20b9)", 0, 1000000, 25000)}
    st.header("Policy record")
    policy = {"active": st.selectbox("Status", ["Active", "Lapsed"]) == "Active", "limit": st.number_input("Max claim limit (\u20b9)", 0, 1000000, 50000),
              "excess": st.number_input("Policy excess (\u20b9)", 0, 100000, 1000), "age": st.number_input("Vehicle age (years)", 0, 30, 3),
              "claims": st.number_input("Claims in last 12 months", 0, 20, 0)}
    st.header("AI models")
    # Auto-load default model from Streamlit secrets (set in Cloud -> Settings -> Secrets)
    if "profiles" not in st.session_state:
        default_cfg = None
        try:
            s = st.secrets["ai"]
            default_cfg = {"type": s.get("type", "openai"), "model": s["model_name"], "base_url": s.get("base_url", ""), "key": s.get("api_key", "")}
        except Exception:
            pass
        st.session_state.profiles = {"Default": default_cfg} if default_cfg else {}
    admin = st.checkbox("Admin / add model", value=False)
    if admin:
        with st.expander("Add a model to try", expanded=True):
            pn = st.text_input("Name (your label)", key="pn"); pt = st.selectbox("Type", ["openai-compatible", "anthropic", "ollama"], key="pt")
            pm = st.text_input("Model name (must support images)", key="pm"); pb = st.text_input("Base URL (not needed for anthropic)", key="pb")
            pk = st.text_input("API key (kept only in this session)", type="password", key="pk")
            if st.button("Add model") and pn and pm:
                st.session_state.profiles[pn] = {"type": "openai" if pt == "openai-compatible" else pt, "model": pm, "base_url": pb, "key": pk}
    if st.session_state.profiles:
        active = st.selectbox("Model used for claims", list(st.session_state.profiles)); cfg = st.session_state.profiles[active]
    else:
        st.warning("No AI model configured. Check Admin to add one, or set secrets in Streamlit Cloud.")
        cfg = None

t1, t2, t3, t4, t5 = st.tabs(["New claim", "Adjuster dashboard", "Audit trail", "Assumptions", "Compare models"])

with t1:
    st.title("Auto-Settle AI")
    up = st.file_uploader("Damage photo or video", type=["jpg", "jpeg", "png", "webp", "mp4", "mov"])
    claimed = st.selectbox("Customer says the damaged part is", list(core.PARTS))
    with st.expander("AI unavailable? Enter findings manually"):
        mp = st.multiselect("Damaged parts", list(core.PARTS), ["bumper"]); mt = st.selectbox("Damage type", list(core.TYP))
        ms = st.selectbox("Severity", list(core.SEV)); mc = st.slider("Confidence %", 0, 100, 85); mq = st.checkbox("Photo is clear", True)
        manual = st.button("Use manual findings")
    go = st.button("Analyse with AI", type="primary", disabled=up is None)
    finding, extra, img = None, [], None
    if go and up:
        try:
            raw = up.getvalue(); img, jpeg = to_jpeg(raw, up.type.startswith("video"))
            h = hashlib.sha256(jpeg).hexdigest(); d = db_load()
            if h in d["hashes"]: extra.append("Duplicate photo: this image was already submitted")
            else: d["hashes"].append(h); db_save(d)
            finding = core.analyse_image(jpeg, cfg); log("AI_VISION", json.dumps(finding))
            st.session_state.img = (img, finding.get("box"))
        except Exception as e: st.error(f"AI step failed: {e}. Use the manual option."); log("AI_ERROR", str(e))
    if manual and mp:
        finding = {"part": mp[0], "type": mt, "severity": ms, "confidence": mc, "quality_ok": mq,
                   "items": [{"part": p, "type": mt, "severity": ms} for p in mp], "notes": "Manually entered findings"}
        log("MANUAL_INPUT", json.dumps(finding))
    if finding:
        c = core.assess(finding, claimed, policy, rails, extra); st.session_state.claim = c; st.session_state.chat = []
        log("ESTIMATE", f"net={core.inr(c['net'])} range={core.inr(c['lo'])}-{core.inr(c['hi'])} risk={c['risk']}")
        if c["status"] == "escalated": log("DECISION", "ESCALATED: " + "; ".join(c["flags"]))
        else: st.session_state.chat.append(("assistant", core.opening(c))); log("OFFER", f"opening {core.inr(c['offer'])}")
        d = db_load(); d["queue"].append({"id": f"C{len(d['queue'])+1}", "state": "Needs review" if c["status"] == "escalated" else "Open",
                                           "detail": ("ESCALATED: " + "; ".join(c["flags"])) if c["status"] == "escalated" else "Negotiating",
                                           "net": c["net"], "paid": 0}); db_save(d); st.session_state.cid = d["queue"][-1]["id"]

    c = st.session_state.get("claim")
    if c:
        if "img" in st.session_state:
            im, box = st.session_state.img; im = im.copy()
            if isinstance(box, list) and len(box) == 4:
                w, h = im.size; x, y, bw, bh = box; ImageDraw.Draw(im).rectangle([x*w, y*h, (x+bw)*w, (y+bh)*h], outline="red", width=4)
            st.image(im, width=380)
        a, b = st.columns(2)
        with a:
            st.subheader("Assessment")
            st.table({"Part": [i["part"] for i in c["items"]], "Damage": [i["type"] for i in c["items"]], "Severity": [i["severity"] for i in c["items"]]})
            st.write(f"Parts{f' (after {c['dep']*100:.0f}% age depreciation)' if c['dep'] else ''}: **{core.inr(c['parts'])}** | Labour: **{core.inr(c['labour'])}**")
            st.write(f"Garage repair: **{core.inr(c['gross'])}** | Excess: **-{core.inr(min(c['excess'], c['gross']))}** | Net claim: **{core.inr(c['net'])}**")
            st.write(f"Allowed cash range: {core.inr(c['lo'])} to {core.inr(c['hi'])} | Estimate band: {core.inr(c['band'][0])} to {core.inr(c['band'][1])}")
            st.metric("Fraud and risk score", f"{c['risk']}/100"); st.caption(c["notes"])
        with b:
            if c["status"] == "escalated":
                st.error("Escalated to human adjuster"); [st.write("- " + f) for f in c["flags"]]
            else:
                st.subheader("Settlement conversation")
                lang = st.selectbox("Chat language", ["English", "Hindi"])
                for r, m in st.session_state.chat: st.chat_message(r).write(m)
                if c["status"] == "negotiating":
                    if st.button("Accept current offer"):
                        c["status"], c["amount"] = "settled", c["offer"]; log("DECISION", f"SETTLED at {core.inr(c['offer'])} (accepted offer)"); st.rerun()
                    msg = st.chat_input("Your reply or counteroffer in rupees")
                    if msg:
                        st.session_state.chat.append(("user", msg)); log("CUSTOMER", msg)
                        rep = core.negotiate(c, msg, rails)
                        st.session_state.chat.append(("assistant", core.translate_hi(rep, cfg) if lang == "Hindi" else rep))
                        if c["status"] == "settled": log("DECISION", f"SETTLED at {core.inr(c['amount'])}")
                        elif c["status"] == "escalated": log("DECISION", "ESCALATED: " + c["flags"][-1])
                        else: log("OFFER", f"round {c['round']} offer {core.inr(c['offer'])}")
                        st.rerun()
                elif c["status"] == "settled":
                    st.success(f"Final settlement {core.inr(c['amount'])}")
                    upi = st.text_input("UPI ID for instant payout (simulated)")
                    if st.button("Pay now"):
                        import re
                        if re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", upi):
                            d = db_load(); q = next(x for x in d["queue"] if x["id"] == st.session_state.cid)
                            q.update(state="Auto-settled", detail="SETTLED", paid=c["amount"], saved=c["gross"] - c["amount"]); db_save(d)
                            log("PAYOUT", f"Simulated UPI transfer of {core.inr(c['amount'])} to **{upi[2:]}"); st.success("Payment initiated (simulated). Claim closed.")
                        else: st.error("That UPI ID does not look valid.")

with t2:
    d = db_load(); q = d["queue"]; n = len(q); stp = sum(1 for x in q if x["state"] == "Auto-settled")
    k = st.columns(4); k[0].metric("Cases", n); k[1].metric("Straight-through rate", f"{stp/n*100:.0f}%" if n else "-")
    k[2].metric("Total paid out", core.inr(sum(x.get("paid", 0) for x in q))); k[3].metric("Saved vs garage estimate", core.inr(sum(x.get("saved", 0) for x in q)))
    for i, x in enumerate(q):
        a, b, c2, e = st.columns([1, 5, 2, 3]); a.write(f"**{x['id']}**"); b.write(x["detail"]); c2.write(x["state"])
        if x["state"] == "Needs review":
            if e.button("Approve", key=f"a{i}"): x["state"] = "Approved by adjuster"; db_save(d); log("ADJUSTER", f"{x['id']} approved"); st.rerun()
            if e.button("Reject", key=f"r{i}"): x["state"] = "Rejected by adjuster"; db_save(d); log("ADJUSTER", f"{x['id']} rejected"); st.rerun()
    if st.button("Clear all stored data (demo reset)"): db_save({"queue": [], "log": [], "hashes": []}); st.rerun()

with t3:
    d = db_load(); st.dataframe(d["log"], width="stretch")
    st.download_button("Download audit trail (JSON)", json.dumps(d["log"], indent=1), "audit_trail.json")

with t4:
    st.markdown("""
- **Scope:** minor motor claims settled as cash-in-lieu instead of a garage repair.
- **Cost data:** mock parts and labour table with illustrative rupee values and a flat labour rate of \u20b9500 per hour.
- **Settlement range:** 70% to 90% of the net claim value, editable. Code, not the chatbot, enforces every limit.
- **AI role:** the vision model only describes damage. Amounts, limits and escalation are plain code.
- **Policy rules:** illustrative. Parts depreciate 5% per year (max 50%), excess is deducted, lapsed policy, over-limit claims, or 3+ claims escalate. Real insurer terms vary.
- **Fraud and risk:** a simple illustrative score. Duplicate photos are detected across all claims stored in this app. Rule-changing or angry chat messages escalate.
- **Model choice:** set PROVIDER=ollama to run a small local vision model (under 20B parameters) instead of the Claude API.
- **Not covered:** vehicle market value, fraud history across customers, real payment integration.
""")

with t5:
    import pandas as pd
    st.subheader("Compare AI models on the same photo")
    st.caption("Add models in the sidebar, upload a test photo, tick the parts that are truly damaged, and run. Repeat with several photos, then read the averages.")
    cu = st.file_uploader("Test photo", type=["jpg", "jpeg", "png", "webp"], key="cmpu")
    truth = st.multiselect("Parts that are truly damaged (enables accuracy scores)", list(core.PARTS))
    chosen = st.multiselect("Models to compare", list(st.session_state.profiles), default=list(st.session_state.profiles)[:1])
    if "cmp" not in st.session_state: st.session_state.cmp = []
    if st.button("Run comparison", disabled=not (cu and chosen)):
        _, jpeg = to_jpeg(cu.getvalue(), False)
        for m in chosen:
            t0 = time.time()
            try:
                r = core.analyse_image(jpeg, st.session_state.profiles[m]); dt = round(time.time() - t0, 1)
                found = sorted({i.get("part") for i in (r.get("items") or [r])})
                row = {"Photo": cu.name, "Model": m, "Time (s)": dt, "Parts found": ", ".join(map(str, found)), "Worst severity": r.get("severity"), "Self-reported confidence": r.get("confidence")}
                if truth: row["Precision"], row["Recall"] = core.score(found, truth)
            except Exception as e: row = {"Photo": cu.name, "Model": m, "Time (s)": round(time.time() - t0, 1), "Parts found": "ERROR: " + str(e)[:150]}
            st.session_state.cmp.append(row)
    if st.session_state.cmp:
        df = pd.DataFrame(st.session_state.cmp); st.dataframe(df, width="stretch")
        if "Recall" in df: st.write("**Average per model** (higher recall = misses fewer damaged parts; higher precision = invents fewer):"); st.dataframe(df.dropna(subset=["Recall"]).groupby("Model")[["Precision", "Recall", "Time (s)"]].mean().round(2), width="stretch")
        if st.button("Clear comparison results"): st.session_state.cmp = []; st.rerun()
