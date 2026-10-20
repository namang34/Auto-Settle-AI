import hashlib, io, json, os, re, tempfile, time
import streamlit as st
from PIL import Image, ImageDraw
import core

st.set_page_config(page_title="Auto-Settle AI", page_icon="\U0001F697", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{padding-top:1.2rem;max-width:1150px}
footer{visibility:hidden}
.hero{background:#A72218;border-radius:16px;padding:22px 28px;margin-bottom:12px}
.hero h1{color:#fff;margin:0;font-size:2rem;padding:0}.hero p{color:#E9E7E0;margin:.3rem 0 0;font-size:1.02rem}
.steps{display:flex;gap:8px;margin:4px 0 14px}
.step{flex:1;text-align:center;padding:8px 4px;border-radius:999px;background:#E3C5B2;color:#7A5C55;font-weight:600;font-size:.85rem}
.step.on{background:#EB6F46;color:#2B1A17}.step.done{background:#A72218;color:#fff}
.card{background:#fff;border:1px solid #E3C5B2;border-radius:14px;padding:14px 16px;margin-bottom:10px}
.badge{display:inline-block;padding:5px 14px;border-radius:999px;font-weight:700;font-size:.9rem;margin-bottom:8px}
.ok{background:#DFF0E3;color:#1B6B34}.bad{background:#F8D7D3;color:#A72218}
.lbl{color:#7A5C55;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.big{font-size:1.7rem;font-weight:800;color:#A72218;line-height:1.15}.mid{font-size:1.1rem;font-weight:700;color:#A72218}
</style>""", unsafe_allow_html=True)

DB = "claims_db.json"  # claim queue, audit trail, photo fingerprints
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
def stat(label, value, cls="mid"): return f'<div class="card"><div class="lbl">{label}</div><div class="{cls}">{value}</div></div>'

# ---------- team settings (sidebar). Customers never need to touch these ----------
PW = os.getenv("ADMIN_PASSWORD", "")
if "profiles" not in st.session_state:
    st.session_state.profiles = {"Default (from secrets)": None}
    try:  # models kept in the host's Secrets under [models.<name>]
        for _n, _m in dict(st.secrets.get("models", {})).items(): st.session_state.profiles[_n] = dict(_m)
    except Exception: pass
    if len(st.session_state.profiles) > 1 and not core.env_cfg().get("key") and os.getenv("PROVIDER") != "ollama":
        st.session_state.profiles.pop("Default (from secrets)")
rails = {"lo": .75, "hi": .90, "step": .04, "max_rounds": 3, "min_conf": 70, "cap": 25000}
policy = {"active": True, "limit": 50000, "excess": 1000, "age": 3, "claims": 0}
with st.sidebar:
    st.markdown("### Team settings")
    if PW and not st.session_state.get("is_admin"):
        if st.text_input("Admin password", type="password") == PW: st.session_state.is_admin = True; st.rerun()
    is_admin = (not PW) or st.session_state.get("is_admin", False)
    if is_admin:
        with st.expander("Guardrails"):
            rails = {"lo": st.number_input("Offer floor (% of net claim)", 1, 100, 75) / 100, "hi": st.number_input("Offer ceiling (%)", 1, 100, 90) / 100,
                     "step": st.number_input("Concession per round (%)", 1, 50, 4) / 100, "max_rounds": st.number_input("Max negotiation rounds", 1, 10, 3),
                     "min_conf": st.number_input("Min AI confidence (%)", 0, 100, 70), "cap": st.number_input("Auto-settle cap (\u20b9)", 0, 1000000, 25000)}
        with st.expander("Policy record"):
            policy = {"active": st.selectbox("Status", ["Active", "Lapsed"]) == "Active", "limit": st.number_input("Max claim limit (\u20b9)", 0, 1000000, 50000),
                      "excess": st.number_input("Policy excess (\u20b9)", 0, 100000, 1000), "age": st.number_input("Vehicle age (years)", 0, 30, 3), "claims": st.number_input("Claims in last 12 months", 0, 20, 0)}
        with st.expander("AI models"):
            pn = st.text_input("Name", key="pn"); pt = st.selectbox("Type", ["openai-compatible", "anthropic", "ollama"], key="pt")
            pm = st.text_input("Model name (must support images)", key="pm"); pb = st.text_input("Base URL (not for anthropic)", key="pb"); pk = st.text_input("API key (this session only)", type="password", key="pk")
            if st.button("Add model") and pn and pm: st.session_state.profiles[pn] = {"type": "openai" if pt == "openai-compatible" else pt, "model": pm, "base_url": pb, "key": pk}
            active = st.selectbox("Model used for claims", list(st.session_state.profiles))
    else: active = list(st.session_state.profiles)[0]
cfg = st.session_state.profiles[active]

# ---------- header and progress ----------
st.markdown('<div class="hero"><h1>\U0001F697 Auto-Settle AI</h1><p>Upload a photo of the damage. Get an instant cash offer, or a human review if we are unsure.</p></div>', unsafe_allow_html=True)
c0 = st.session_state.get("claim")
stage = 0 if not c0 else (2 if c0["status"] == "negotiating" else 3)
st.markdown('<div class="steps">' + "".join(f'<div class="step {"done" if i < stage else "on" if i == stage else ""}">{n}</div>' for i, n in enumerate(["1 Upload", "2 Assessment", "3 Offer", "4 Decision"])) + "</div>", unsafe_allow_html=True)

names = ["New claim", "How it works"] + (["Adjuster dashboard", "Audit trail", "Compare models"] if is_admin else [])
T = dict(zip(names, st.tabs(names)))

def start_claim(finding, claimed, extra=()):
    c = core.assess(finding, claimed, policy, rails, extra); st.session_state.claim = c; st.session_state.chat = []; st.session_state.paid = False
    log("ESTIMATE", f"net={core.inr(c['net'])} range={core.inr(c['lo'])}-{core.inr(c['hi'])} risk={c['risk']}")
    if c["status"] == "escalated": log("DECISION", "ESCALATED: " + "; ".join(c["flags"]))
    else: st.session_state.chat.append(("assistant", core.opening(c))); log("OFFER", f"opening {core.inr(c['offer'])}")
    d = db_load(); d["queue"].append({"id": f"C{len(d['queue'])+1}", "state": "Needs review" if c["status"] == "escalated" else "Open",
        "detail": ("ESCALATED: " + "; ".join(c["flags"])) if c["status"] == "escalated" else "Negotiating", "net": c["net"], "paid": 0}); db_save(d); st.session_state.cid = d["queue"][-1]["id"]

DEMOS = {"Small dent (instant offer)": ({"part": "bumper", "type": "dent", "severity": "minor", "confidence": 90, "quality_ok": True, "items": [{"part": "bumper", "type": "dent", "severity": "minor"}], "notes": "Demo case: small dent on the front bumper"}, "bumper"),
         "Severe front damage (human review)": ({"part": "fender", "type": "dent", "severity": "severe", "confidence": 92, "quality_ok": True, "items": [{"part": "fender", "type": "dent", "severity": "severe"}, {"part": "headlight", "type": "broken", "severity": "severe"}, {"part": "bonnet", "type": "dent", "severity": "moderate"}], "notes": "Demo case: severe front-end damage"}, "fender")}

with T["New claim"]:
    L, R = st.columns([1, 1.1], gap="large")
    with L:
        st.markdown("#### Tell us about the damage")
        up = st.file_uploader("Photo or short video of the damage", type=["jpg", "jpeg", "png", "webp", "mp4", "mov"])
        claimed = st.selectbox("Which part is damaged?", list(core.PARTS))
        go = st.button("Analyse damage", type="primary", disabled=up is None)
        with st.expander("No photo handy? Try a demo case"):
            for nm, (fd, cl) in DEMOS.items():
                if st.button(nm, key="demo_" + nm): start_claim(fd, cl); st.session_state.pop("img", None)
        with st.expander("AI unavailable? Enter findings manually"):
            mp = st.multiselect("Damaged parts", list(core.PARTS), ["bumper"]); mt = st.selectbox("Damage type", list(core.TYP)); ms = st.selectbox("Severity", list(core.SEV))
            mc = st.slider("Confidence %", 0, 100, 85); mq = st.checkbox("Photo is clear", True)
            if st.button("Use manual findings") and mp:
                start_claim({"part": mp[0], "type": mt, "severity": ms, "confidence": mc, "quality_ok": mq, "items": [{"part": p, "type": mt, "severity": ms} for p in mp], "notes": "Manually entered findings"}, claimed)
    with R:
        if up is not None and not up.type.startswith("video"): st.image(up, width=460)
        elif up is not None: st.video(up)
        else: st.info("Your photo will appear here once you upload it.")
    if go and up:
        try:
            with st.spinner("Analysing your photo. This usually takes 10 to 20 seconds..."):
                img, jpeg = to_jpeg(up.getvalue(), up.type.startswith("video")); h = hashlib.sha256(jpeg).hexdigest(); d = db_load(); extra = []
                if h in d["hashes"]: extra.append("Duplicate photo: this image was already submitted")
                else: d["hashes"].append(h); db_save(d)
                finding = core.analyse_image(jpeg, cfg); log("AI_VISION", json.dumps(finding))
            st.session_state.img = (img, finding.get("box")); start_claim(finding, claimed, extra)
        except Exception as e:
            st.error("We could not analyse that photo. Please try another photo, or use the manual option."); log("AI_ERROR", str(e))
            with st.expander("Technical details"): st.code(str(e))
    c = st.session_state.get("claim")
    if c:
        st.divider()
        st.markdown(f'<span class="badge {"bad" if c["status"] == "escalated" else "ok"}">{"Sent to a human adjuster" if c["status"] == "escalated" else "Settled" if c["status"] == "settled" else "Eligible for an instant offer"}</span>', unsafe_allow_html=True)
        cols = st.columns(4 if is_admin else 3)
        cols[0].markdown(stat("Damage found", ", ".join(i["part"] for i in c["items"])), unsafe_allow_html=True)
        cols[1].markdown(stat("Net claim value", core.inr(c["net"]), "big"), unsafe_allow_html=True)
        cols[2].markdown(stat("Cash offer range", f'{core.inr(c["lo"])} to {core.inr(c["hi"])}'), unsafe_allow_html=True)
        if is_admin: cols[3].markdown(stat("Risk score", f'{c["risk"]}/100'), unsafe_allow_html=True)
        A, B = st.columns([1, 1.1], gap="large")
        with A:
            if "img" in st.session_state:
                im, box = st.session_state.img; im = im.copy()
                if isinstance(box, list) and len(box) == 4:
                    w, h = im.size; x, y, bw, bh = box; ImageDraw.Draw(im).rectangle([x*w, y*h, (x+bw)*w, (y+bh)*h], outline="#EB6F46", width=5)
                st.image(im, caption="Where the AI sees damage", width=420)
            st.table({"Part": [i["part"] for i in c["items"]], "Damage": [i["type"] for i in c["items"]], "Severity": [i["severity"] for i in c["items"]]})
            with st.expander("How this was calculated"):
                st.write(f"Parts{f' (after {c['dep']*100:.0f}% age depreciation)' if c['dep'] else ''}: **{core.inr(c['parts'])}**  \nLabour: **{core.inr(c['labour'])}**  \nGarage repair: **{core.inr(c['gross'])}**  \nPolicy excess: **-{core.inr(min(c['excess'], c['gross']))}**  \nNet claim value: **{core.inr(c['net'])}**")
                st.caption(f"Estimate band {core.inr(c['band'][0])} to {core.inr(c['band'][1])}. " + c["notes"])
        with B:
            if c["status"] == "escalated":
                st.markdown("#### A person will review your claim")
                st.write("We could not safely decide this automatically. Reasons:")
                for f in c["flags"]: st.markdown(f"- \u26a0\ufe0f {f}")
            else:
                st.markdown("#### Your settlement offer")
                lang = st.radio("Chat language", ["English", "Hindi"], horizontal=True)
                for r, m in st.session_state.chat: st.chat_message(r).write(m)
                if c["status"] == "negotiating":
                    if st.button(f"Accept {core.inr(c['offer'])}", type="primary"):
                        c["status"], c["amount"] = "settled", c["offer"]; log("DECISION", f"SETTLED at {core.inr(c['offer'])} (accepted offer)"); st.rerun()
                    msg = st.chat_input("Reply or make a counteroffer, e.g. 3500")
                    if msg:
                        st.session_state.chat.append(("user", msg)); log("CUSTOMER", msg); rep = core.negotiate(c, msg, rails)
                        st.session_state.chat.append(("assistant", core.translate_hi(rep, cfg) if lang == "Hindi" else rep))
                        if c["status"] == "settled": log("DECISION", f"SETTLED at {core.inr(c['amount'])}")
                        elif c["status"] == "escalated": log("DECISION", "ESCALATED: " + c["flags"][-1])
                        else: log("OFFER", f"round {c['round']} offer {core.inr(c['offer'])}")
                        st.rerun()
                elif c["status"] == "settled":
                    st.success(f"Deal confirmed: {core.inr(c['amount'])}")
                    if st.session_state.get("paid"): st.success("Payment initiated (simulated). Claim closed.")
                    else:
                        upi = st.text_input("UPI ID for instant payout (simulated)", placeholder="name@bank")
                        if st.button("Pay now"):
                            if re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", upi):
                                d = db_load(); q = next(x for x in d["queue"] if x["id"] == st.session_state.cid)
                                q.update(state="Auto-settled", detail="SETTLED", paid=c["amount"], saved=c["gross"] - c["amount"]); db_save(d)
                                log("PAYOUT", f"Simulated UPI transfer of {core.inr(c['amount'])} to **{upi[2:]}"); st.session_state.paid = True; st.balloons(); st.rerun()
                            else: st.error("That UPI ID does not look valid.")

with T["How it works"]:
    st.markdown("#### From photo to payout in four steps")
    a, b, c_, d_ = st.columns(4)
    for col, (t, s) in zip([a, b, c_, d_], [("1. Upload", "Send a photo or short video and tell us which part is damaged."), ("2. Assess", "An AI model describes the damage: parts, type and severity."), ("3. Offer", "Fixed rules turn that into a repair cost and a cash offer you can negotiate."), ("4. Decide", "Accept and get paid, or a human adjuster takes over if anything is unclear.")]):
        col.markdown(f'<div class="card"><div class="mid">{t}</div><div>{s}</div></div>', unsafe_allow_html=True)
    st.markdown("**The AI describes; fixed code decides.** The AI never sets an amount, so an offer can never go outside the approved range. Every step is logged.")
    st.caption("All costs, depreciation and settlement limits shown here are illustrative placeholders. Payments are simulated.")

if is_admin:
    with T["Adjuster dashboard"]:
        d = db_load(); q = d["queue"]; n = len(q); stp = sum(1 for x in q if x["state"] == "Auto-settled")
        k = st.columns(4); k[0].metric("Cases", n); k[1].metric("Straight-through rate", f"{stp/n*100:.0f}%" if n else "-")
        k[2].metric("Total paid out", core.inr(sum(x.get("paid", 0) for x in q))); k[3].metric("Saved vs garage estimate", core.inr(sum(x.get("saved", 0) for x in q)))
        for i, x in enumerate(q):
            a, b, c2, e = st.columns([1, 5, 2, 3]); a.write(f"**{x['id']}**"); b.write(x["detail"]); c2.write(x["state"])
            if x["state"] == "Needs review":
                if e.button("Approve", key=f"a{i}"): x["state"] = "Approved by adjuster"; db_save(d); log("ADJUSTER", f"{x['id']} approved"); st.rerun()
                if e.button("Reject", key=f"r{i}"): x["state"] = "Rejected by adjuster"; db_save(d); log("ADJUSTER", f"{x['id']} rejected"); st.rerun()
        if st.button("Clear all stored data (demo reset)"): db_save({"queue": [], "log": [], "hashes": []}); st.rerun()
    with T["Audit trail"]:
        d = db_load(); st.dataframe(d["log"], width="stretch"); st.download_button("Download audit trail (JSON)", json.dumps(d["log"], indent=1), "audit_trail.json")
    with T["Compare models"]:
        import pandas as pd
        st.markdown("#### Compare AI models on the same photo")
        st.caption("Add models in the sidebar, upload a test photo, tick the parts that are truly damaged, and run. Repeat with several photos for averages.")
        cu = st.file_uploader("Test photo", type=["jpg", "jpeg", "png", "webp"], key="cmpu")
        truth = st.multiselect("Parts that are truly damaged (enables accuracy scores)", list(core.PARTS))
        chosen = st.multiselect("Models to compare", list(st.session_state.profiles), default=list(st.session_state.profiles)[:1])
        if "cmp" not in st.session_state: st.session_state.cmp = []
        if st.button("Run comparison", disabled=not (cu and chosen)):
            _, jpeg = to_jpeg(cu.getvalue(), False)
            for m in chosen:
                t0 = time.time()
                try:
                    r = core.analyse_image(jpeg, st.session_state.profiles[m]); dt = round(time.time() - t0, 1); found = sorted({i.get("part") for i in (r.get("items") or [r])})
                    row = {"Photo": cu.name, "Model": m, "Time (s)": dt, "Parts found": ", ".join(map(str, found)), "Worst severity": r.get("severity"), "Self-reported confidence": r.get("confidence")}
                    if truth: row["Precision"], row["Recall"] = core.score(found, truth)
                except Exception as e: row = {"Photo": cu.name, "Model": m, "Time (s)": round(time.time() - t0, 1), "Parts found": "ERROR: " + str(e)[:150]}
                st.session_state.cmp.append(row)
        if st.session_state.cmp:
            df = pd.DataFrame(st.session_state.cmp); st.dataframe(df, width="stretch")
            if "Recall" in df: st.write("**Average per model** (higher recall = misses fewer parts; higher precision = invents fewer):"); st.dataframe(df.dropna(subset=["Recall"]).groupby("Model")[["Precision", "Recall", "Time (s)"]].mean().round(2), width="stretch")
            if st.button("Clear comparison results"): st.session_state.cmp = []; st.rerun()
