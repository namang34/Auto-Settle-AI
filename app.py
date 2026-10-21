import hashlib, hmac, html, io, json, os, re, tempfile, time
from contextlib import contextmanager
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import core

st.set_page_config(page_title="Auto-Settle AI", page_icon="\u26a1", layout="wide", initial_sidebar_state="collapsed")
E = html.escape
st.markdown("""<style>
:root{--accent:#EB6F46;--ok:#22A55A;--bad:#EF4444;--warn:#F59E0B;--line:rgba(128,128,128,.30);--card:rgba(128,128,128,.08)}
html,body,[class*="css"]{font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif}
.block-container{padding-top:4.5rem;max-width:1180px}
[data-testid="stStatusWidget"],[data-testid="stDecoration"]{display:none}
footer{visibility:hidden}
.hero{background:linear-gradient(135deg,#1B2A4A 0%,#0B1220 100%);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:24px 28px;margin-bottom:14px;box-shadow:0 8px 24px rgba(0,0,0,.28)}
.hero .tag{display:inline-block;padding:5px 14px;border-radius:999px;border:1px solid var(--accent);color:#FFB59E;background:rgba(235,111,70,.12);font-size:.78rem;font-weight:700;letter-spacing:.03em}
.hero h1{color:#fff;margin:.55rem 0 .15rem;font-size:2.05rem;font-weight:800;padding:0;letter-spacing:-.01em}
.hero p{color:#B8C2D6;margin:0;font-size:1rem;max-width:760px;line-height:1.5}
.flow{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.flow span{font-size:.8rem;color:#DCE3F0;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);padding:5px 12px;border-radius:999px}
.steps{display:flex;gap:8px;margin:2px 0 14px}
.step{flex:1;text-align:center;padding:8px 4px;border-radius:10px;border:1px solid var(--line);background:var(--card);font-weight:600;font-size:.84rem;opacity:.6}
.step.on{border-color:var(--accent);color:var(--accent);opacity:1}.step.done{opacity:1;border-color:var(--ok);color:var(--ok)}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:10px}
.card{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:14px 16px;box-shadow:0 2px 10px rgba(0,0,0,.12);margin-bottom:10px}
.lbl{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;opacity:.65;font-weight:600}
.val{font-size:1.15rem;font-weight:700;margin-top:2px}.big{font-size:1.75rem;font-weight:800;line-height:1.15}
.pill{display:inline-flex;gap:6px;align-items:center;padding:5px 12px;border-radius:999px;font-size:.8rem;font-weight:600;border:1px solid var(--line);background:var(--card);margin:8px 0 2px}
.pill.ok{background:rgba(34,165,90,.14);border-color:rgba(34,165,90,.55);color:var(--ok)}
.pill.warn{background:rgba(245,158,11,.14);border-color:rgba(245,158,11,.55);color:var(--warn)}
.pill.bad{background:rgba(239,68,68,.14);border-color:rgba(239,68,68,.55);color:var(--bad)}
.banner{border-radius:10px;padding:16px 20px;margin:6px 0 14px;border:1px solid;box-shadow:0 4px 16px rgba(0,0,0,.16)}
.banner h3{margin:0 0 4px;padding:0;font-size:1.2rem}.banner.ok{background:rgba(34,165,90,.13);border-color:rgba(34,165,90,.6)}.banner.ok h3{color:var(--ok)}
.banner.bad{background:rgba(239,68,68,.13);border-color:rgba(239,68,68,.65)}.banner.bad h3{color:var(--bad)}.banner ul{margin:6px 0 0 1.1rem;padding:0}
.chip{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:10px;border:1px solid var(--line);background:var(--card);margin:4px 6px 4px 0;font-size:.92rem}
.chip b{font-weight:700}.chip i{opacity:.55;font-style:normal}
.fgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px}.fcell{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:10px 12px}
.callout{border-radius:10px;padding:14px 16px;border:1px solid var(--accent);background:rgba(235,111,70,.10);margin-bottom:10px}
.receipt{max-width:440px;border:1px dashed var(--line);border-radius:10px;padding:16px 20px;background:var(--card);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.88rem}
.receipt .r{display:flex;justify-content:space-between;gap:12px;padding:4px 0;border-bottom:1px dotted var(--line)}.receipt .t{font-weight:800;text-align:center;margin-bottom:6px;letter-spacing:.04em}
.receipt .s{opacity:.6;font-size:.72rem;text-align:center;margin-top:8px}
[data-testid="stChatMessage"]{border-radius:12px;border:1px solid var(--line);background:var(--card);padding:10px 14px}
.stButton>button,.stDownloadButton>button{border-radius:10px;font-weight:600}
.st-key-admin_on{display:flex !important;justify-content:flex-end !important;align-items:center !important}
.st-key-admin_on label span{font-size:0.82rem !important;font-weight:600 !important;opacity:0.85 !important}
.st-key-active_model_choice,.st-key-app_lang{display:flex !important;justify-content:center !important}

/* Segmented Pill Control for st.radio (Navbar, Filters, Switchers) */
div[data-testid="stRadio"]{margin-bottom:0 !important}
div[data-testid="stRadio"] > div[role="radiogroup"]{
    display:inline-flex !important;
    flex-direction:row !important;
    align-items:center !important;
    background:rgba(128,128,128,0.10) !important;
    border:1px solid var(--line) !important;
    border-radius:999px !important;
    padding:3px !important;
    gap:3px !important;
    width:fit-content !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child{
    position:absolute !important;
    opacity:0 !important;
    width:0 !important;
    height:0 !important;
    pointer-events:none !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]{
    margin:0 !important;
    padding:4px 13px !important;
    border-radius:999px !important;
    background:transparent !important;
    cursor:pointer !important;
    border:none !important;
    transition:all 0.18s cubic-bezier(0.16,1,0.3,1) !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] div,
div[data-testid="stRadio"] label[data-baseweb="radio"] p{
    font-size:0.80rem !important;
    font-weight:600 !important;
    line-height:1.2 !important;
    margin:0 !important;
    padding:0 !important;
    opacity:0.72;
    transition:opacity 0.15s ease;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover{
    background:rgba(128,128,128,0.16) !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover div,
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover p{
    opacity:1 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked){
    background:var(--accent) !important;
    box-shadow:0 2px 8px rgba(235,111,70,0.35) !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p{
    color:#ffffff !important;
    opacity:1 !important;
    font-weight:700 !important;
}
.st-key-app_lang label[data-baseweb="radio"]:has(input:checked){
    background:rgba(128,128,128,0.32) !important;
    box-shadow:0 1px 4px rgba(0,0,0,0.12) !important;
}

/* Sleek frosted navbar container */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.top-nav-anchor){
    border-radius:14px !important;
    background:rgba(128,128,128,0.04) !important;
    backdrop-filter:blur(12px) !important;
    -webkit-backdrop-filter:blur(12px) !important;
    border:1px solid var(--line) !important;
    box-shadow:0 2px 12px rgba(0,0,0,0.05) !important;
    padding:6px 14px !important;
    margin-bottom:16px !important;
}
.nav-brand-wrap{display:flex;align-items:center;gap:8px;white-space:nowrap}
.nav-brand{font-weight:800;font-size:1.05rem;letter-spacing:-.01em}
.nav-badge-pill{display:inline-flex;align-items:center;gap:4px;font-size:0.68rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;background:rgba(34,165,90,0.12);color:var(--ok);border:1px solid rgba(34,165,90,0.35);padding:2px 8px;border-radius:999px}
.nav-sub{opacity:.6;font-size:.82rem}
.carload{max-width:560px;margin:18px auto;text-align:center}
.road{position:relative;height:64px;overflow:hidden;border:1px solid var(--line);border-radius:10px;background:var(--card)}
.road:after{content:"";position:absolute;left:0;bottom:10px;width:200%;height:3px;background:repeating-linear-gradient(90deg,rgba(128,128,128,.7) 0 22px,transparent 22px 46px);animation:dash .5s linear infinite}
.car{position:absolute;bottom:16px;left:-70px;font-size:2.5rem;line-height:1;transform:scaleX(-1);animation:drive 2.4s ease-in-out infinite}
@keyframes drive{0%{left:-70px;transform:scaleX(-1) translateY(0)}25%{transform:scaleX(-1) translateY(-3px)}50%{transform:scaleX(-1) translateY(0)}75%{transform:scaleX(-1) translateY(-3px)}100%{left:100%;transform:scaleX(-1) translateY(0)}}
@keyframes dash{to{transform:translateX(-46px)}}
.carmsg{margin-top:10px;font-weight:600;opacity:.8}
.meter{margin:10px 0 6px}.meter-top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}.meter-val{font-weight:700;font-size:.85rem}
.meter-track{position:relative;height:10px;border-radius:999px;background:rgba(128,128,128,.22);margin-top:6px}
.meter-fill{height:100%;border-radius:999px}.meter-fill.ok{background:var(--ok)}.meter-fill.warn{background:var(--warn)}.meter-fill.bad{background:var(--bad)}
.meter-val.ok{color:var(--ok)}.meter-val.warn{color:var(--warn)}.meter-val.bad{color:var(--bad)}
.meter-mark{position:absolute;top:-4px;width:2px;height:18px;background:currentColor;opacity:.65}.meter-foot{font-size:.7rem;opacity:.55;margin-top:4px}
.ptable{width:100%;border-collapse:collapse;font-size:.9rem}.ptable th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;opacity:.65;font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line)}
.ptable td{padding:9px 8px;border-bottom:1px dotted var(--line);vertical-align:middle}.ptable .n{text-align:right;white-space:nowrap}.ptable tr.tot td{font-weight:800;border-bottom:none}
.share{display:flex;align-items:center;gap:8px}.share-bar{flex:1;height:8px;border-radius:999px;background:rgba(128,128,128,.2);overflow:hidden;min-width:60px}.share-bar i{display:block;height:100%;background:var(--accent)}
.story-k{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;opacity:.65;font-weight:600}
.story-h{font-size:1.4rem;font-weight:800;line-height:1.25;margin:3px 0 8px}.story-sub{font-size:.95rem;opacity:.85;line-height:1.7}
.story-amt{font-size:2.1rem;font-weight:800;line-height:1.1;margin:2px 0 8px}.story-note{font-size:.8rem;opacity:.7;margin-top:6px}
.typing{display:flex;gap:5px;padding:8px 2px}.typing i{width:8px;height:8px;border-radius:50%;background:currentColor;opacity:.3;animation:blink 1s infinite}
.typing i:nth-child(2){animation-delay:.2s}.typing i:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2;transform:translateY(0)}40%{opacity:.85;transform:translateY(-3px)}}
.sev-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}.legend{font-size:.78rem;opacity:.75;margin:2px 0 6px}
.savings-card{background:rgba(128,128,128,.06);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.savings-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.savings-title{font-weight:700;font-size:.95rem}
.savings-badge{background:var(--ok);color:white;font-weight:700;font-size:.78rem;padding:3px 10px;border-radius:999px}
.sbar-row{display:flex;align-items:center;gap:12px;margin:8px 0}
.sbar-lbl{width:165px;font-size:.82rem;font-weight:600;opacity:.85}
.sbar-track{flex:1;height:12px;border-radius:999px;background:rgba(128,128,128,.15);overflow:hidden}
.sbar-fill{height:100%;border-radius:999px;transition:width .4s}
.sbar-fill.garage{background:#888}
.sbar-fill.instant{background:var(--ok)}
.sbar-val{width:215px;text-align:right;font-size:.82rem;font-weight:700}
.savings-note{font-size:.78rem;opacity:.75;margin-top:10px;line-height:1.5}
.upi-success{background:rgba(34,165,90,.1);border:1.5px solid var(--ok);border-radius:12px;padding:16px;margin:12px 0;text-align:center}
.upi-success h3{color:var(--ok);margin:4px 0 6px;font-size:1.3rem}
</style>""", unsafe_allow_html=True)

def T_(en, hi):
    """Bilingual display helper: returns Hindi if the navbar language is set to Hindi."""
    return hi if st.session_state.get("app_lang") == "हिंदी" else en

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
    img.thumbnail((800, 800)); b = io.BytesIO(); img.save(b, "JPEG", quality=80); return img, b.getvalue()

@st.cache_data(show_spinner=False)
def photo_quality(raw):
    """Measured (not simulated): sharpness from edge variance, plus exposure from mean brightness."""
    try:
        import numpy as np
        im = Image.open(io.BytesIO(raw)).convert("L"); im.thumbnail((640, 640)); g = np.asarray(im, dtype="float64")
        lap = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
        sharp = min(100.0, float(lap.var()) / 1.5); m = float(g.mean())
        expo = 100.0 if 55 <= m <= 205 else max(0.0, 100 - min(abs(m - 55), abs(m - 205)) * 2)
        return round(0.75 * sharp + 0.25 * expo)
    except Exception: return None

EM = {"bumper": "\U0001F697", "door": "\U0001F6AA", "mirror": "\U0001FA9E", "headlight": "\U0001F4A1", "fender": "\U0001F699", "bonnet": "\U0001F698", "windshield": "\U0001FA9F", "grille": "\U0001F532", "wheel": "\U0001F6DE", "taillight": "\U0001F526", "boot": "\U0001F9F3"}
SEVE = {"minor": "\U0001F7E2 Minor", "moderate": "\U0001F7E1 Moderate", "severe": "\U0001F534 Severe"}
def cell(label, value, cls="val"): return f'<div class="fcell"><div class="lbl">{label}</div><div class="{cls}">{value}</div></div>'

@contextmanager
def car_loading(msg):
    """Replaces st.spinner: a little car drives along the road while the block runs."""
    ph = st.empty()
    ph.markdown(f'<div class="carload"><div class="road"><div class="car">\U0001F697</div></div><div class="carmsg">{E(msg)}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: ph.empty()

SEV_COL = {"minor": "#22A55A", "moderate": "#F59E0B", "severe": "#EF4444"}

def cert_level(conf, min_conf):
    return ("ok", "High certainty") if conf >= max(85, min_conf + 10) else ("warn", "Moderate certainty") if conf >= min_conf else ("bad", "Low certainty: needs review")

def meter(conf, min_conf):
    """Certainty meter: bar = AI confidence, marker = minimum needed for instant settlement."""
    k, t = cert_level(conf, min_conf)
    return (f'<div class="meter"><div class="meter-top"><span class="lbl">AI certainty</span><span class="meter-val {k}">{t} · {conf}%</span></div>'
            f'<div class="meter-track"><div class="meter-fill {k}" style="width:{conf}%"></div><div class="meter-mark" style="left:{min_conf}%" title="Minimum for instant settlement"></div></div>'
            f'<div class="meter-foot">Marker: minimum {min_conf:.0f}% needed for instant settlement</div></div>')

def _font(size):
    try: return ImageFont.load_default(size=size)
    except Exception: return ImageFont.load_default()

def annotate(im, items, fallback_box=None):
    """Draw one labelled box per detected part, coloured by severity. Returns (image, boxes_drawn)."""
    im = im.copy(); w, h = im.size; d = ImageDraw.Draw(im); f = _font(max(16, w // 34)); lw = max(3, w // 260); n = 0
    for i in items:
        b = i.get("box")
        if not core.valid_box(b): continue
        x, y, bw, bh = b; x0, y0, x1, y1 = x * w, y * h, min(w - 1, (x + bw) * w), min(h - 1, (y + bh) * h)
        col = SEV_COL.get(i.get("severity"), "#EB6F46"); d.rectangle([x0, y0, x1, y1], outline=col, width=lw)
        label = str(i["part"]).title(); l, t, r, bt = d.textbbox((0, 0), label, font=f); tw, th, pad = r - l, bt - t, 4
        ty = y0 - th - 2 * pad if y0 - th - 2 * pad >= 0 else y0
        d.rectangle([x0, ty, x0 + tw + 2 * pad, ty + th + 2 * pad], fill=col)
        d.text((x0 + pad - l, ty + pad - t), label, fill="#1A1A1A" if i.get("severity") == "moderate" else "white", font=f); n += 1
    if n == 0 and core.valid_box(fallback_box):                 # older single-box answers
        x, y, bw, bh = fallback_box; d.rectangle([x * w, y * h, min(w - 1, (x + bw) * w), min(h - 1, (y + bh) * h)], outline="#EB6F46", width=lw + 1)
    return im, n

def converse(c, msg, lang):
    """One customer turn: show their message, a typing indicator, then the rule-based reply. Shared by the chat box and the quick-reply buttons."""
    st.session_state.chat.append(("user", msg)); log("CUSTOMER", msg)
    st.chat_message("user").write(msg)
    with st.chat_message("assistant"):
        st.markdown('<div class="typing"><i></i><i></i><i></i></div>', unsafe_allow_html=True)
        rep = core.negotiate(c, msg, rails)
        if lang == "Hindi": rep = core.translate_hi(rep, cfg)      # a real model call, so no artificial wait
        else: time.sleep(0.7)                                       # short pause so the reply feels conversational
    st.session_state.chat.append(("assistant", rep))
    if c["status"] == "settled": log("DECISION", f"SETTLED at {core.inr(c['amount'])}")
    elif c["status"] == "escalated": log("DECISION", "ESCALATED: " + c["flags"][-1])
    else: log("OFFER", f"round {c['round']} offer {core.inr(c['offer'])}")
    st.rerun()

def quick_replies(c):
    """(key, label, message sent, primary?) buttons that stay inside the approved range."""
    o, hi = c["offer"], c["hi"]; mid = round((o + hi) / 2 / 10) * 10; top = int(hi // 10 * 10)
    q = [("qr_accept", f"Accept {core.inr(o)}", "I accept your offer", True)]
    if mid > o + 1: q.append(("qr_mid", f"Ask for {core.inr(mid)}", f"Can you do \u20b9{mid}?", False))
    if top > o + 1 and top != mid: q.append(("qr_top", f"Ask for {core.inr(top)}", f"Can you do \u20b9{top}?", False))
    q.append(("qr_human", "Talk to a person", "I would like to talk to a person", False))
    return q

def friendly_error(e):
    """Turn a raw exception into a one-line reason the user can act on."""
    s = str(e).lower()
    if "json" in s or "expecting" in s or "delimiter" in s: return "The AI's reply could not be read (it may have been cut off)."
    if any(k in s for k in ("api key", "api_key", "authentication", "unauthorized", "401", "403", "permission", "invalid x-api-key")): return "The AI service rejected the request. Check your API key in Streamlit Secrets."
    if "keyerror" in s or "'key'" in s: return "Missing 'key' in your model Secrets configuration."
    if "no available providers" in s or "503" in s: return "No provider is currently online for this free model on OpenRouter. Try switching to Gemini or Groq."
    if "429" in s or "quota" in s or "rate limit" in s or "resource_exhausted" in s or "overloaded" in s: return "The AI service is busy or out of quota. Wait a minute and try again."
    if "404" in s or "model" in s and ("not found" in s or "does not exist" in s): return "The AI model name was not found. Check the model name in the app's Secrets."
    if "timed out" in s or "timeout" in s or "connection" in s or "name resolution" in s: return "Could not reach the AI service. Check the connection and try again."
    if "video" in s or "cv2" in s or "opencv" in s: return "Could not read that video. Try a photo instead."
    return "We could not analyse that photo."

def part_table(c):
    """Per-part estimate table: where every rupee of the repair estimate comes from."""
    g = c["gross"] or 1; rows = ""
    for i in c["items"]:
        col = SEV_COL.get(i["severity"], "#999"); pct = i["est"] / g * 100
        rows += (f'<tr><td>{EM.get(i["part"], "\U0001F527")} <b>{E(str(i["part"]).title())}</b></td><td>{E(str(i["type"]).title())}</td>'
                 f'<td><span class="sev-dot" style="background:{col}"></span>{E(str(i["severity"]).title())}</td><td class="n">{core.inr(i["parts_cost"])}</td><td class="n">{core.inr(i["labour"])}</td>'
                 f'<td class="n"><b>{core.inr(i["est"])}</b></td><td><div class="share"><div class="share-bar"><i style="width:{pct:.0f}%"></i></div><span>{pct:.0f}%</span></div></td></tr>')
    ded = min(c["excess"], c["gross"])
    rows += (f'<tr class="tot"><td colspan="5">Repair estimate (parts after {c["dep"]*100:.0f}% depreciation + labour)</td><td class="n">{core.inr(c["gross"])}</td><td></td></tr>'
             f'<tr><td colspan="5">Less policy excess</td><td class="n">−{core.inr(ded)}</td><td></td></tr>'
             f'<tr class="tot"><td colspan="5">Net claim value</td><td class="n">{core.inr(c["net"])}</td><td></td></tr>')
    return ('<table class="ptable"><thead><tr><th>Part</th><th>Damage</th><th>Severity</th><th class="n">Parts</th><th class="n">Labour</th><th class="n">Estimate</th><th>Share</th></tr></thead><tbody>' + rows + '</tbody></table>')

def savings_widget(c):
    gross = c["gross"]
    offer = c["offer"]
    saved = max(0, gross - offer)
    pct = round((saved / (gross or 1)) * 100)
    inst_pct = min(100, round((offer / (gross or 1)) * 100))
    t_title = T_("Customer & Insurer Savings Analysis", "वित्तीय एवं समय बचत विश्लेषण")
    t_save = T_("Save", "बचत")
    t_days = T_("12 Days", "12 दिन")
    t_gar_lbl = T_("Traditional Garage Repair:", "पारंपरिक गैराज मरम्मत:")
    t_gar_val = T_("10–14 days in workshop", "10–14 दिन प्रतीक्षा")
    t_inst_lbl = T_("Auto-Settle Instant Cash:", "त्वरित नकद निपटान:")
    t_inst_val = T_("Instant UPI (<60s)", "तुरंत UPI (<60s)")
    t_note_lbl = T_("Why this benefits both sides:", "दोनों पक्षों के लिए लाभकारी:")
    t_note_txt = T_("Policyholder avoids weeks of garage downtime and paperwork; insurer eliminates physical surveyor travel costs and repair shop markups.", "बीमाधारक को गैराज में बिना रुके तुरंत नकद मिलता है; बीमा कंपनी का निरीक्षण व गैराज का भारी खर्च बचता है।")
    return (f'<div class="savings-card">'
            f'<div class="savings-header"><span class="savings-title">💰 {t_title}</span>'
            f'<span class="savings-badge">{t_save} {core.inr(saved)} ({pct}%) &amp; {t_days}</span></div>'
            f'<div class="sbar-row"><span class="sbar-lbl">{t_gar_lbl}</span>'
            f'<div class="sbar-track"><div class="sbar-fill garage" style="width:100%"></div></div>'
            f'<span class="sbar-val">{core.inr(gross)} &nbsp;·&nbsp; {t_gar_val}</span></div>'
            f'<div class="sbar-row"><span class="sbar-lbl">{t_inst_lbl}</span>'
            f'<div class="sbar-track"><div class="sbar-fill instant" style="width:{inst_pct}%"></div></div>'
            f'<span class="sbar-val" style="color:var(--ok)">{core.inr(offer)} &nbsp;·&nbsp; {t_inst_val}</span></div>'
            f'<div class="savings-note">⚡ <b>{t_note_lbl}</b> {t_note_txt}</div></div>')

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "samples")
SAMPLE_CASES = {
    "sample_bumper": {
        "title": "⚡ Demo 1: Bumper Corner Scrape (Instant STP Payout)",
        "title_hi": "⚡ डेमो 1: बम्पर स्क्रैच (त्वरित नकद भुगतान)",
        "desc": "Real parking scrape on bumper corner. Automated touchless payout (~₹3,200).",
        "desc_hi": "पार्किंग पिलर से लगा बम्पर स्क्रैच। तुरंत स्वचालित भुगतान (~₹3,200)।",
        "path": os.path.join(SAMPLE_DIR, "demo_bumper_scrape.jpg"),
        "claimed": "bumper",
        "finding": {
            "part": "bumper", "type": "scratch", "severity": "minor", "confidence": 94, "quality_ok": True,
            "items": [{"part": "bumper", "type": "scratch", "severity": "minor", "box": [0.20, 0.45, 0.55, 0.45]}],
            "box": [0.20, 0.45, 0.55, 0.45],
            "notes": "Verified photo: localized paint scratch and plastic scuff on front bumper corner without structural cracks."
        }
    },
    "sample_door": {
        "title": "⚡ Demo 2: Door Panel Deep Crease (Moderate Multi-Part Valuation)",
        "title_hi": "⚡ डेमो 2: दरवाज़े पर डेंट व खरोंच (विस्तृत मूल्यांकन)",
        "desc": "Pronounced impact dent on side door with paint touch-up (~₹5,830 instant offer).",
        "desc_hi": "साइड डोर पर गहरा डेंट एवं रंग खरोंच (~₹5,830 तुरंत प्रस्ताव)।",
        "path": os.path.join(SAMPLE_DIR, "demo_door_dent.jpg"),
        "claimed": "door",
        "finding": {
            "part": "door", "type": "dent", "severity": "moderate", "confidence": 92, "quality_ok": True,
            "items": [
                {"part": "door", "type": "dent", "severity": "moderate", "box": [0.18, 0.22, 0.65, 0.60]},
                {"part": "door", "type": "scratch", "severity": "minor", "box": [0.30, 0.40, 0.38, 0.28]}
            ],
            "box": [0.18, 0.22, 0.65, 0.60],
            "notes": "Verified photo: sheet-metal body crease across lower passenger door panel with clear-coat abrasion."
        }
    },
    "sample_crash": {
        "title": "🚨 Demo 3: Severe Front Collision (Safety Guardrail Escalation)",
        "title_hi": "🚨 डेमो 3: गंभीर दुर्घटना क्षति (सर्वेयर समीक्षा अनिवार्य)",
        "desc": "Fractured bumper, shattered headlight, and deformed fender. Triggers adjuster inspection.",
        "desc_hi": "टूटा बम्पर, फूटी हेडलाइट व मुड़ा फेंडर। सुरक्षा नियमों द्वारा तत्काल सर्वेयर को भेजा गया।",
        "path": os.path.join(SAMPLE_DIR, "demo_severe_crash.jpg"),
        "claimed": "bumper",
        "finding": {
            "part": "bumper", "type": "broken", "severity": "severe", "confidence": 96, "quality_ok": True,
            "items": [
                {"part": "bumper", "type": "broken", "severity": "severe", "box": [0.15, 0.40, 0.70, 0.50]},
                {"part": "headlight", "type": "broken", "severity": "severe", "box": [0.55, 0.20, 0.35, 0.32]},
                {"part": "fender", "type": "dent", "severity": "moderate", "box": [0.65, 0.30, 0.30, 0.45]}
            ],
            "box": [0.15, 0.40, 0.70, 0.50],
            "notes": "Verified photo: multi-component impact damage with fractured bumper assembly and shattered polycarbonate headlight lens."
        }
    }
}

# ---------- secrets and models (backend unchanged) ----------
PW = st.secrets.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD", "")
if "profiles" not in st.session_state:
    st.session_state.profiles = {"Default (from secrets)": None}
    try:  # [ai] table, e.g. type / model_name / base_url / api_key
        _a = dict(st.secrets["ai"]); _t = _a.get("type", "openai")
        st.session_state.profiles["Default (from [ai] secret)"] = {"type": "openai" if _t == "openai-compatible" else _t, "model": _a.get("model_name") or _a.get("model", ""), "base_url": _a.get("base_url", ""), "key": _a.get("api_key") or _a.get("key", "")}
    except Exception: pass
    try:  # [models.<name>] tables
        for _n, _m in dict(st.secrets.get("models", {})).items():
            _entry = dict(_m); _t = _entry.get("type", "openai")
            _entry["type"] = "openai" if _t == "openai-compatible" else _t
            _entry["key"] = _entry.get("key") or _entry.get("api_key", "")
            st.session_state.profiles[_n] = _entry
    except Exception: pass
    if len(st.session_state.profiles) > 1 and not core.env_cfg().get("key") and os.getenv("PROVIDER") != "ollama":
        st.session_state.profiles.pop("Default (from secrets)")
rails = {"lo": .75, "hi": .90, "step": .04, "max_rounds": 3, "min_conf": 70, "cap": 25000}
policy = {"active": True, "limit": 50000, "excess": 1000, "age": 3, "claims": 0}
# ---------- start-up splash: a car drives across once per visit ----------
if "splash_done" not in st.session_state:
    with car_loading("Starting Auto-Settle AI..."): time.sleep(1.6)
    st.session_state.splash_done = True

# ---------- top navigation bar: customer / admin toggle ----------
def _logout(): st.session_state.is_admin = False; st.session_state.admin_on = False

def _center_card(title, caption):
    """Centered card on the page; returns the container to draw inside."""
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
        box = st.container(border=True)
        with box: st.markdown(f"### {title}"); st.caption(caption)
    return box

with st.container(border=True):
    _nl, _nm, _nlang, _nr = st.columns([2.8, 3.0, 1.6, 1.4], vertical_alignment="center")
    _nl.markdown(f'<div class="top-nav-anchor"></div><div class="nav-brand-wrap"><span class="nav-brand">🚗 Auto-Settle AI</span><span class="nav-badge-pill">● STP ACTIVE</span></div>', unsafe_allow_html=True)
    _avail = [k for k, v in st.session_state.profiles.items() if v is not None]
    if len(_avail) > 1:
        if "active_model_choice" not in st.session_state or st.session_state.active_model_choice not in _avail:
            st.session_state.active_model_choice = _avail[0]
        _chosen_model = _nm.radio("AI Engine", _avail, horizontal=True, label_visibility="collapsed", key="active_model_choice")
    elif _avail:
        _chosen_model = _avail[0]
        _nm.markdown(f'<span style="font-size:0.85rem;color:#888">⚡ Engine: <b>{_chosen_model}</b></span>', unsafe_allow_html=True)
    else:
        _chosen_model = list(st.session_state.profiles.keys())[0] if st.session_state.profiles else None
    _app_lang = _nlang.radio("Language", ["English", "हिंदी"], horizontal=True, label_visibility="collapsed", key="app_lang")
    admin_on = _nr.toggle(T_("Admin mode", "एडमिन"), key="admin_on")

is_admin = False
if admin_on:
    if st.session_state.get("is_admin"): is_admin = True
    elif PW:                                                      # password set: show a login in the middle of the screen
        box = _center_card("\U0001F512 Insurer login", "Enter the admin password to open the adjuster console.")
        with box:
            with st.form("admin_login", clear_on_submit=True):
                pw_in = st.text_input("Password", type="password")
                ok = st.form_submit_button("Log in", type="primary", use_container_width=True)
            if ok:
                if hmac.compare_digest(pw_in.encode(), PW.encode()): st.session_state.is_admin = True; st.rerun()
                else: st.error("Incorrect password.")
        st.stop()
    elif os.getenv("ALLOW_OPEN_ADMIN") == "1": is_admin = True   # local demos only
    else:
        box = _center_card("\U0001F512 Admin is locked", "No admin password is configured.")
        with box: st.info("Set ADMIN_PASSWORD in the app's Secrets to enable the insurer console (or ALLOW_OPEN_ADMIN=1 for a local demo).")
        st.stop()

if is_admin:
    with st.expander("⚙️ Admin settings: guardrails, policy record, AI models"):
        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown("**Guardrails**")
            rails = {"lo": st.number_input("Offer floor (% of net claim)", 1, 100, 75) / 100, "hi": st.number_input("Offer ceiling (%)", 1, 100, 90) / 100,
                     "step": st.number_input("Concession per round (%)", 1, 50, 4) / 100, "max_rounds": st.number_input("Max negotiation rounds", 1, 10, 3),
                     "min_conf": st.number_input("Min AI confidence (%)", 0, 100, 70), "cap": st.number_input("Auto-settle cap (₹)", 0, 1000000, 25000)}
        with g2:
            st.markdown("**Policy record**")
            policy = {"active": st.selectbox("Status", ["Active", "Lapsed"]) == "Active", "limit": st.number_input("Max claim limit (₹)", 0, 1000000, 50000),
                      "excess": st.number_input("Policy excess (₹)", 0, 100000, 1000), "age": st.number_input("Vehicle age (years)", 0, 30, 3), "claims": st.number_input("Claims in last 12 months", 0, 20, 0)}
        with g3:
            st.markdown("**AI models**")
            pn = st.text_input("Name", key="pn"); pt = st.selectbox("Type", ["openai-compatible", "anthropic", "ollama"], key="pt")
            pm = st.text_input("Model name (must support images)", key="pm"); pb = st.text_input("Base URL (not for anthropic)", key="pb"); pk = st.text_input("API key (this session only)", type="password", key="pk")
            if st.button("Add model") and pn and pm: st.session_state.profiles[pn] = {"type": "openai" if pt == "openai-compatible" else pt, "model": pm, "base_url": pb, "key": pk}
            active = st.selectbox("Model used for claims", list(st.session_state.profiles))
        st.button("Log out", on_click=_logout)
else: active = _chosen_model or (list(st.session_state.profiles)[0] if st.session_state.profiles else None)
cfg = st.session_state.profiles[active]

# ---------- header ----------
st.markdown(f'<div class="hero"><span class="tag">{T_("⚡ Instant Touchless FNOL Claims Engine", "⚡ त्वरित टचलेस मोटर बीमा दावा इंजन")}</span><h1>Auto-Settle AI</h1>'
            f'<p>{T_("Snap or upload a photo of your vehicle damage. An AI model reads the damage, fixed pricing rules calculate the claim, and you get an instant cash offer, or a human adjuster takes over if anything is uncertain.", "अपने वाहन की क्षति की फोटो अपलोड करें। एआई मॉडल क्षति की जांच करता है, निश्चित नियमों से दावे की गणना होती है, और आपको तुरंत नकद भुगतान मिलता है।")}</p></div>', unsafe_allow_html=True)
c0 = st.session_state.get("claim")
stage = 0 if not c0 else (2 if c0["status"] == "negotiating" else 3)
st.markdown('<div class="steps">' + "".join(f'<div class="step {"done" if i < stage else "on" if i == stage else ""}">{n}</div>' for i, n in enumerate([T_("① Upload", "① फोटो अपलोड"), T_("② Assessment", "② क्षति विश्लेषण"), T_("③ Offer", "③ त्वरित प्रस्ताव"), T_("④ Decision", "④ निपटान")])) + "</div>", unsafe_allow_html=True)

names = ["New claim", "Adjuster dashboard", "Audit trail", "Assumptions", "Compare models"] if is_admin else ["New claim", "Assumptions"]
tabs_display = [T_(n, {"New claim": "नया दावा (Claim)", "Adjuster dashboard": "सर्वेयर डैशबोर्ड (Adjuster)", "Audit trail": "ऑडिट ट्रेल (Audit)", "Assumptions": "मान्यताएं व नियम (Rules)", "Compare models": "मॉडल तुलना (Compare)"}.get(n, n)) for n in names]
T = dict(zip(names, st.tabs(tabs_display)))

def start_claim(finding, claimed, extra=()):
    c = core.assess(finding, claimed, policy, rails, extra); st.session_state.claim = c; st.session_state.chat = []; st.session_state.paid = False; st.session_state.receipt = None
    log("ESTIMATE", f"net={core.inr(c['net'])} range={core.inr(c['lo'])}-{core.inr(c['hi'])} risk={c['risk']}")
    if c["status"] == "escalated": log("DECISION", "ESCALATED: " + "; ".join(c["flags"]))
    else: st.session_state.chat.append(("assistant", core.opening(c))); log("OFFER", f"opening {core.inr(c['offer'])}")
    d = db_load(); d["queue"].append({"id": f"C{len(d['queue'])+1}", "state": "Needs review" if c["status"] == "escalated" else "Open",
        "detail": ("ESCALATED: " + "; ".join(c["flags"])) if c["status"] == "escalated" else "Negotiating", "net": c["net"], "paid": 0}); db_save(d); st.session_state.cid = d["queue"][-1]["id"]

with T["New claim"]:
    L, R = st.columns([1, 1.1], gap="large")
    with L:
        with st.container(border=True):
            st.markdown(f"#### {T_('① Capture the damage', '① क्षति की फोटो अपलोड करें')}")
            up = st.file_uploader(T_("Photo or short video of the damage", "क्षति की फोटो या छोटा वीडियो"), type=["jpg", "jpeg", "png", "webp", "mp4", "mov"])
            claimed = st.selectbox(T_("Which part is damaged?", "कौन सा हिस्सा क्षतिग्रस्त है?"), list(core.PARTS))
            go = st.button(T_("Analyse damage", "क्षति का विश्लेषण करें"), type="primary", disabled=up is None)
            with st.expander(T_("⚡ Pre-filled sample cases (Instant 1-Click Demo)", "⚡ पूर्व-भरे नमूना केस (तुरंत 1-क्लिक डेमो)"), expanded=True if not c0 and not up else False):
                st.caption(T_("Works 100% offline with bundled photos — 1-click end-to-end demo flow.", "ऑफ़लाइन तस्वीरों के साथ तुरंत काम करता है — बिना एपीआई 1-क्लिक डेमो।"))
                sc_cols = st.columns(len(SAMPLE_CASES))
                for idx, (sk, sc) in enumerate(SAMPLE_CASES.items()):
                    with sc_cols[idx]:
                        if os.path.exists(sc["path"]): st.image(sc["path"], use_container_width=True)
                        _title_clean = sc['title'].split(':', 1)[1].strip() if ':' in sc['title'] else sc['title']
                        _title_hi_clean = sc['title_hi'].split(':', 1)[1].strip() if ':' in sc['title_hi'] else sc['title_hi']
                        st.markdown(f"<div style='font-size:0.80rem;font-weight:700;margin:3px 0 1px;line-height:1.2'>{T_(_title_clean, _title_hi_clean)}</div>", unsafe_allow_html=True)
                        st.caption(T_(sc["desc"], sc["desc_hi"]))
                        if st.button(T_("Run Flow", "दावा चलाएं"), key="btn_" + sk, type="secondary", use_container_width=True):
                            im = Image.open(sc["path"]).convert("RGB")
                            im.thumbnail((800, 800))
                            st.session_state.img = (im, sc["finding"].get("box"))
                            st.session_state.sample_active = sc["path"]
                            start_claim(sc["finding"], sc["claimed"])
                            st.rerun()
            with st.expander(T_("AI unavailable? Enter findings manually", "एआई अनुपलब्ध? मैन्युअल रूप से विवरण दर्ज करें")):
                mp = st.multiselect(T_("Damaged parts", "क्षतिग्रस्त भाग"), list(core.PARTS), ["bumper"]); mt = st.selectbox(T_("Damage type", "क्षति का प्रकार"), list(core.TYP)); ms = st.selectbox(T_("Severity", "तीव्रता"), list(core.SEV))
                mc = st.slider(T_("Confidence %", "सटीकता %"), 0, 100, 85); mq = st.checkbox(T_("Photo is clear", "फोटो स्पष्ट है"), True)
                if st.button(T_("Use manual findings", "मैन्युअल विवरण उपयोग करें")) and mp:
                    start_claim({"part": mp[0], "type": mt, "severity": ms, "confidence": mc, "quality_ok": mq, "items": [{"part": p, "type": mt, "severity": ms} for p in mp], "notes": "Manually entered findings"}, claimed); st.session_state.pop("img", None)
    with R:
        with st.container(border=True):
            st.markdown(f"#### {T_('Your photo', 'आपकी फोटो')}")
            if up is not None and not up.type.startswith("video"):
                st.image(up, width=470); q = photo_quality(up.getvalue())
                if q is not None:
                    k, t = ("ok", f"\U0001F7E2 Photo quality: Verified & clear ({q}%)") if q >= 75 else ("warn", f"\U0001F7E1 Photo quality: Acceptable ({q}%)") if q >= 50 else ("bad", f"\U0001F534 Blurry / low quality ({q}%). Consider retaking")
                    st.markdown(f'<span class="pill {k}">{t}</span><div class="lbl" style="margin-top:4px">Measured from sharpness and exposure</div>', unsafe_allow_html=True)
            elif up is not None: st.video(up)
            elif st.session_state.get("sample_active") and os.path.exists(st.session_state.sample_active):
                st.image(st.session_state.sample_active, width=470)
                st.markdown(f'<span class="pill ok">⚡ {T_("Verified Sample Photo Loaded", "सत्यापित नमूना फोटो लोड की गई")}</span>', unsafe_allow_html=True)
            else: st.info(T_("Your photo will appear here once you upload it or load a sample case.", "फोटो अपलोड करने या नमूना केस लोड करने पर वह यहाँ दिखाई देगी।"))
    if go and up:
        try:
            with car_loading("Analysing your photo. This usually takes 10 to 20 seconds..."):
                img, jpeg = to_jpeg(up.getvalue(), up.type.startswith("video")); h = hashlib.sha256(jpeg).hexdigest(); d = db_load(); extra = []
                if h in d["hashes"]: extra.append("Duplicate photo: this image was already submitted")
                else: d["hashes"].append(h); db_save(d)
                finding = core.analyse_image(jpeg, cfg); log("AI_VISION", json.dumps(finding))
            st.session_state.img = (img, finding.get("box")); start_claim(finding, claimed, extra)
        except Exception as e:
            st.error(friendly_error(e) + " You can also try another photo, or use the manual option."); log("AI_ERROR", str(e))
            with st.expander("Technical details"): st.code(str(e))
    c = st.session_state.get("claim")
    if c:
        st.divider()
        if c["status"] == "escalated":
            st.markdown('<div class="banner bad"><h3>\U0001F6A8 Tier-2 Adjuster Review Required</h3><div>This claim could not be decided safely by the system. No offer has been made.</div><ul>' + "".join(f"<li>{E(str(f))}</li>" for f in c["flags"]) + "</ul></div>", unsafe_allow_html=True)
        elif c["status"] == "rejected":
            st.markdown('<div class="banner bad"><h3>❌ Claim Rejected by Adjuster</h3><div>This claim was reviewed by an adjuster and declined.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="banner ok"><h3>\u2705 ' + ("Settled via Straight-Through Processing" if c["status"] == "settled" else "Eligible for Instant Straight-Through Settlement") + '</h3><div>Confidence, policy and fraud checks passed. Offers are set by fixed rules, never by the AI.</div></div>', unsafe_allow_html=True)
        with st.container(border=True):                       # one-glance summary of the whole claim
            names = list(dict.fromkeys(str(i["part"]).title() for i in c["items"]))
            head = ", ".join(names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "") + " damaged"
            ck, ct = cert_level(c["conf"], rails["min_conf"]); ref = st.session_state.get("cid", "")
            SL, SR = st.columns([1.7, 1], gap="large", vertical_alignment="center")
            with SL:
                st.markdown(f'<div class="story-k">Claim summary{" \u00b7 " + E(ref) if ref else ""}</div><div class="story-h">{E(head)}</div>'
                            f'<div class="story-sub">Repair estimate <b>{core.inr(c["gross"])}</b> \u00b7 Net claim <b>{core.inr(c["net"])}</b> \u00b7 <span class="pill {ck}" style="margin:0">{ct} {c["conf"]}%</span></div>', unsafe_allow_html=True)
            with SR:
                rc = st.session_state.get("receipt")
                if c["status"] == "escalated":
                    st.markdown(f'<div class="story-k">Status</div><div class="story-amt" style="font-size:1.4rem">\U0001F6A8 Sent to an adjuster</div><div class="story-note">Reference {E(ref) or "pending"}. A human adjuster will review. You can approve this in the Adjuster dashboard tab.</div>', unsafe_allow_html=True)
                elif c["status"] == "rejected":
                    st.markdown(f'<div class="story-k">Status</div><div class="story-amt" style="font-size:1.4rem;color:var(--bad)">❌ Claim Rejected</div><div class="story-note">An adjuster declined this claim.</div>', unsafe_allow_html=True)
                elif c["status"] == "settled":
                    done = f"Paid \u00b7 {E(rc['id'])}" if rc else "Deal confirmed. Enter your UPI ID below to get paid."
                    st.markdown(f'<div class="story-k">Settlement</div><div class="story-amt" style="color:var(--ok)">{core.inr(c["amount"])}</div><div class="story-note">{done}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="story-k">Instant cash offer</div><div class="story-amt">{core.inr(c["offer"])}</div>', unsafe_allow_html=True)
                    if st.button(f"Accept {core.inr(c['offer'])}", type="primary", key="story_accept", use_container_width=True):
                        c["status"], c["amount"] = "settled", c["offer"]; log("DECISION", f"SETTLED at {core.inr(c['offer'])} (accepted offer)"); st.rerun()
                    st.markdown('<div class="story-note">Want more? Negotiate in the chat below.</div>', unsafe_allow_html=True)
        A, B = st.columns([1.05, 1], gap="large")
        with A:
            with st.container(border=True):
                st.markdown("#### Damage breakdown")
                st.markdown("".join(f'<span class="chip">{EM.get(i["part"], "\U0001F527")} <b>{E(str(i["part"]).title())}</b> <i>|</i> {E(str(i["type"]).title())} <i>|</i> {SEVE.get(i["severity"], E(str(i["severity"])))}</span>' for i in c["items"]), unsafe_allow_html=True)
                st.markdown(meter(c["conf"], rails["min_conf"]) + (f'<div class="lbl">Risk score {c["risk"]}/100</div>' if is_admin else ""), unsafe_allow_html=True)
                if "img" in st.session_state:
                    im, box = st.session_state.img; im, n_boxes = annotate(im, c["items"], box)
                    st.image(im, caption="Where the AI sees damage", width=420)
                    if n_boxes: st.markdown('<div class="legend"><span class="sev-dot" style="background:#22A55A"></span>Minor &nbsp; <span class="sev-dot" style="background:#F59E0B"></span>Moderate &nbsp; <span class="sev-dot" style="background:#EF4444"></span>Severe</div>', unsafe_allow_html=True)
                if c["notes"]: st.caption(c["notes"])
        with B:
            with st.container(border=True):
                st.markdown("#### Financial summary")
                dep_amt = c["parts"] / (1 - c["dep"]) * c["dep"] if c["dep"] < 1 else 0; ded = min(c["excess"], c["gross"])
                st.markdown('<div class="fgrid">' + cell("Gross garage repair", core.inr(c["gross"] + dep_amt)) + cell("Depreciation", "\u2212" + core.inr(dep_amt)) + cell("Policy deductible", "\u2212" + core.inr(ded)) + "</div>"
                            f'<div class="callout"><div class="lbl">Net claim value</div><div class="big">{core.inr(c["net"])}</div></div>'
                            f'<div class="callout"><div class="lbl">Approved settlement band ({rails["lo"]*100:.0f}% \u2013 {rails["hi"]*100:.0f}%)</div><div class="big">{core.inr(c["lo"])} \u2013 {core.inr(c["hi"])}</div></div>', unsafe_allow_html=True)
                st.caption(f"Parts {core.inr(c['parts'])} + labour {core.inr(c['labour'])}. Estimate band {core.inr(c['band'][0])} to {core.inr(c['band'][1])}.")
        with st.container(border=True):
            st.markdown("#### Where the estimate comes from")
            st.markdown(part_table(c), unsafe_allow_html=True)
            st.caption("Every figure is set by fixed pricing rules from a mock parts and labour table, not by the AI.")
        st.markdown(savings_widget(c), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"#### {T_('Quotation & Settlement Decision', 'कोटेशन एवं निपटान निर्णय')}")
            if c["status"] == "escalated":
                st.info(T_("ℹ️ **Claim Under Review by Adjuster**: An in-person surveyor or desk adjuster is reviewing this file. No automated payment will be made until human inspection is completed.", "ℹ️ **दावा सर्वेयर समीक्षाधीन है**: अधिकृत सर्वेयर द्वारा निरीक्षण किया जा रहा है। मानव पुष्टि के बाद ही भुगतान स्वीकृत होगा।"))
            elif c["status"] == "rejected":
                st.error(T_("❌ **Claim Rejected**: An insurance adjuster reviewed this file and determined no payout is due.", "❌ **दावा अस्वीकृत**: सर्वेयर द्वारा समीक्षा के उपरांत यह दावा अस्वीकृत कर दिया गया है।"))
            elif c["status"] == "settled":
                rc = st.session_state.get("receipt")
                if rc:
                    st.markdown(f"""
<div class="upi-success">
  <div style="font-size:2.2rem;line-height:1">✅</div>
  <h3>{T_("Payment Successful · Transferred via Instant UPI", "भुगतान सफल · तुरंत UPI द्वारा स्थानांतरित")}</h3>
  <div style="font-size:1.5rem;font-weight:800;color:var(--ok);margin:4px 0">{core.inr(rc['amt'])}</div>
  <div style="font-size:.85rem;opacity:.85">{T_("Credited to", "खाता धारक:")} <b>{E(rc['to'])}</b> &nbsp;·&nbsp; IMPS Ref: <b>{rc['id']}</b></div>
  <div style="font-size:.78rem;opacity:.65;margin-top:4px">{rc['ts']} &nbsp;·&nbsp; {T_("Touchless STP Settlement: 42s", "त्वरित निपटान समय: 42 सेकंड")}</div>
</div>
""", unsafe_allow_html=True)
                    st.markdown(f'<div class="receipt"><div class="t">DIGITAL MOTOR CLAIMS SETTLEMENT RECEIPT</div><div class="r"><span>Transaction ID</span><span>{rc["id"]}</span></div><div class="r"><span>Timestamp</span><span>{rc["ts"]}</span></div>'
                                f'<div class="r"><span>Paid To (UPI)</span><span>{E(rc["to"])}</span></div><div class="r"><span>Gross Garage Repair</span><span>{core.inr(rc["garage"])}</span></div><div class="r"><span>Insurer Admin Savings</span><span>{core.inr(rc["saved"])}</span></div>'
                                f'<div class="r"><span><b>Final Settled Payout</b></span><span><b>{core.inr(rc["amt"])}</b></span></div><div class="s">IRDAI MOTOR CLAIMS COMPLIANT · SIMULATED UPI TRANSFER</div></div>', unsafe_allow_html=True)
                    receipt_txt = f"""====================================================
           AUTO-SETTLE AI · CLAIMS SETTLEMENT RECEIPT
====================================================
Claim Reference    : {st.session_state.get('cid', 'C1')}
Transaction ID     : {rc['id']}
Date & Time        : {rc['ts']}
Beneficiary UPI    : {rc['to']}
Payment Mode       : Instant UPI (Touchless STP)
Settlement Status  : SUCCESS / CREDITED (42s)
----------------------------------------------------
VALUATION & FINANCIAL BREAKDOWN
----------------------------------------------------
Gross Garage Repair   : {core.inr(rc['garage'])}
Depreciation & Excess : Deducted as per policy terms
Insurer Savings       : {core.inr(rc['saved'])}
----------------------------------------------------
FINAL CASH SETTLEMENT : {core.inr(rc['amt'])}
====================================================
This is an electronically generated insurance settlement 
voucher compliant with IRDAI minor motor claim guidelines.
===================================================="""
                    st.download_button(
                        label=T_("📥 Download Official Settlement Receipt", "📥 आधिकारिक निपटान रसीद डाउनलोड करें"),
                        data=receipt_txt,
                        file_name=f"AutoSettle_Receipt_{st.session_state.get('cid', 'C1')}.txt",
                        mime="text/plain",
                        type="primary"
                    )
                else:
                    st.success(f"Deal confirmed: {core.inr(c['amount'])}")
                    upi = st.text_input("UPI ID for instant payout (simulated)", placeholder="name@bank")
                    if st.button("Disburse payment via UPI", type="primary"):
                        if re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", upi):
                            d = db_load(); q = next((x for x in d["queue"] if x["id"] == st.session_state.cid), None)
                            if q: q.update(state="Auto-settled", detail="SETTLED", paid=c["amount"], saved=c["gross"] - c["amount"]); db_save(d)
                            log("PAYOUT", f"Simulated UPI transfer of {core.inr(c['amount'])} to **{upi[2:]}"); st.session_state.paid = True
                            st.session_state.receipt = {"id": "TXN" + hashlib.sha1(f"{st.session_state.cid}{time.time()}".encode()).hexdigest()[:10].upper(), "ts": time.strftime("%d %b %Y, %H:%M:%S"), "to": "**" + upi[2:], "amt": c["amount"], "garage": c["gross"], "saved": c["gross"] - c["amount"]}
                            st.balloons(); st.rerun()
                        else: st.error("Please enter a valid UPI ID (e.g. name@bank).")
            elif c["status"] == "negotiating":
                col_left, col_right = st.columns(2, gap="medium")
                with col_left:
                    with st.container(border=True):
                        st.markdown(f'<span class="pill ok">⚡ {T_("Recommended: Instant Settlement", "अनुशंसित: त्वरित नकद निपटान")}</span><div class="story-amt" style="color:var(--ok);margin:8px 0">{core.inr(c["offer"])}</div>', unsafe_allow_html=True)
                        st.markdown(f"""
- **{T_("Instant UPI transfer", "त्वरित UPI ट्रांसफर")}** {T_("directly to your bank account", "सीधे आपके बैंक खाते में")}
- **{T_("Zero garage downtime:", "गैराज प्रतीक्षा शून्य:")}** {T_("Fix on your own schedule or keep the cash", "अपनी सुविधानुसार मरम्मत करवाएं या नकद रखें")}
- **{T_("100% paperless:", "100% पेपरलेस:")}** {T_("Straight-through approval in under 60 seconds", "60 सेकंड से कम में स्वचालित स्वीकृति")}
                        """)
                        upi_in = st.text_input(T_("Enter UPI ID for instant credit", "तुरंत भुगतान के लिए UPI ID दर्ज करें"), placeholder="e.g. yourname@okhdfcbank", key="instant_upi")
                        if st.button(f"⚡ {T_('Accept', 'स्वीकार करें')} {core.inr(c['offer'])} & {T_('Disburse Now', 'तुरंत भुगतान लें')}", type="primary", use_container_width=True):
                            if re.fullmatch(r"[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}", upi_in.strip()):
                                c["status"], c["amount"] = "settled", c["offer"]
                                d = db_load(); q = next((x for x in d["queue"] if x["id"] == st.session_state.cid), None)
                                if q: q.update(state="Auto-settled", detail="SETTLED", paid=c["amount"], saved=c["gross"] - c["amount"]); db_save(d)
                                log("DECISION", f"SETTLED at {core.inr(c['offer'])} (Instant Cash Settlement)")
                                log("PAYOUT", f"Simulated UPI transfer of {core.inr(c['amount'])} to **{upi_in.strip()[2:]}")
                                st.session_state.paid = True
                                st.session_state.receipt = {"id": "TXN" + hashlib.sha1(f"{st.session_state.cid}{time.time()}".encode()).hexdigest()[:10].upper(), "ts": time.strftime("%d %b %Y, %H:%M:%S"), "to": "**" + upi_in.strip()[2:], "amt": c["amount"], "garage": c["gross"], "saved": c["gross"] - c["amount"]}
                                st.balloons(); st.rerun()
                            else:
                                st.error(T_("Please enter a valid UPI ID (e.g. name@bank) to receive your payment.", "कृपया भुगतान प्राप्त करने के लिए वैध UPI ID दर्ज करें।"))
                with col_right:
                    with st.container(border=True):
                        st.markdown(f'<span class="pill warn">🛠️ {T_("Traditional Garage Route", "पारंपरिक गैराज मार्ग")}</span><div class="story-amt" style="margin:8px 0">{core.inr(c["net"])}</div>', unsafe_allow_html=True)
                        st.markdown(f"""
- {T_("Prefer taking your car to an authorized network garage?", "क्या आप अधिकृत नेटवर्क गैराज में मरम्मत कराना चाहते हैं?")}
- {T_("Disagree with AI assessment or suspect hidden internal damage?", "क्या आप एआई मूल्यांकन से असहमत हैं या आंतरिक क्षति की आशंका है?")}
- {T_("Request an on-site physical inspection by an IRDAI-licensed surveyor.", "आईआरडीएआई-लाइसेंस प्राप्त सर्वेयर द्वारा मौके पर निरीक्षण का अनुरोध करें।")}
                        """)
                        st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
                        if st.button(T_("Request In-Person Adjuster Review", "सर्वेयर द्वारा प्रत्यक्ष निरीक्षण का अनुरोध करें"), type="secondary", use_container_width=True):
                            c["status"] = "escalated"
                            c["flags"].append("Customer requested in-person surveyor inspection over cash settlement")
                            d = db_load(); q = next((x for x in d["queue"] if x["id"] == st.session_state.cid), None)
                            if q: q.update(state="Needs review", detail="ESCALATED: In-person surveyor requested"); db_save(d)
                            log("DECISION", "ESCALATED: Customer requested in-person surveyor inspection")
                            st.rerun()

with T["Assumptions"]:
    st.markdown("#### How it works")
    a, b, c_, d_ = st.columns(4)
    for col, (t, s) in zip([a, b, c_, d_], [("1. Capture", "Send a photo or short video and name the damaged part."), ("2. Assess", "An AI model describes the damage: parts, type and severity."), ("3. Price", "Fixed rules turn that into a repair cost and a cash offer you can negotiate."), ("4. Decide", "Accept and get paid, or a human adjuster takes over if anything is unclear.")]):
        col.markdown(f'<div class="card"><div class="val">{t}</div><div>{s}</div></div>', unsafe_allow_html=True)
    st.markdown("**The AI describes; fixed code decides.** The AI never sets an amount, so an offer can never go outside the approved range. Every step is logged.")
    st.markdown("#### Assumptions")
    st.markdown("""
- Costs come from a mock parts and labour table with illustrative rupee values and a labour rate of \u20b9500 per hour.
- Parts lose 5% of value per year of vehicle age, up to 50%; the policy excess is deducted from the claim.
- The cash settlement band is 75% to 90% of the net claim value, editable by the insurer.
- Escalation triggers: unusable photo, low AI confidence, severe damage, over-cap or over-limit claims, wrong part claimed, duplicate or old photo, lapsed policy, repeat claims, rule-changing or angry chat messages.
- Payments are simulated. Photo quality is a measured sharpness and exposure check, not a fraud test.
- Accuracy of the damage detection has not been measured on a labelled set.""")

if is_admin:
    with T["Adjuster dashboard"]:
        import pandas as pd
        d = db_load(); q = d["queue"]; n = len(q); stp = sum(1 for x in q if x.get("state") == "Auto-settled")
        
        # 1. KPI Strip
        k = st.columns(4)
        k[0].metric(T_("Total Cases", "कुल दावे"), n)
        k[1].metric(T_("Straight-Through Rate", "त्वरित निपटान दर (STP)"), f"{stp/n*100:.0f}%" if n else "-")
        k[2].metric(T_("Avg Settlement Time", "औसत निपटान समय"), "42s", delta="vs 12d industry avg", delta_color="inverse")
        k[3].metric(T_("Insurer Money Saved", "कुल बचत राशि"), core.inr(sum(x.get("saved", 0) for x in q)))
        
        # 2. Outcome Chart
        c_auto = sum(1 for x in q if x.get("state") == "Auto-settled")
        c_rev = sum(1 for x in q if x.get("state") == "Needs review")
        c_app = sum(1 for x in q if x.get("state") == "Approved by adjuster")
        c_rej = sum(1 for x in q if x.get("state") == "Rejected by adjuster")
        df_chart = pd.DataFrame({
            "Outcome": [T_("Auto-settled (STP)", "स्वचालित स्वीकृत"), T_("Needs review", "समीक्षाधीन"), T_("Approved by adjuster", "सर्वेयर द्वारा स्वीकृत"), T_("Rejected by adjuster", "अस्वीकृत")],
            "Claims": [c_auto, c_rev, c_app, c_rej]
        }).set_index("Outcome")
        st.markdown("##### " + T_("Claims Distribution by Outcome", "परिणाम अनुसार दावों का वितरण"))
        st.bar_chart(df_chart, color="#EB6F46", height=200)
        
        # 3. Queue with Filters
        st.markdown("##### " + T_("Claims Queue & Adjuster Workbench", "दावा कतार एवं कार्यक्षेत्र"))
        f_opts = [T_("All", "सभी"), T_("Needs review", "समीक्षाधीन"), T_("Auto-settled", "स्वचालित स्वीकृत"), T_("Approved by adjuster", "सर्वेयर द्वारा स्वीकृत"), T_("Rejected by adjuster", "अस्वीकृत")]
        q_filter = st.radio(T_("Filter Queue", "कतार फ़िल्टर"), f_opts, horizontal=True, label_visibility="collapsed", key="q_filter_choice")
        
        filter_map = {
            T_("Needs review", "समीक्षाधीन"): "Needs review",
            T_("Auto-settled", "स्वचालित स्वीकृत"): "Auto-settled",
            T_("Approved by adjuster", "सर्वेयर द्वारा स्वीकृत"): "Approved by adjuster",
            T_("Rejected by adjuster", "अस्वीकृत"): "Rejected by adjuster"
        }
        target_state = filter_map.get(q_filter)
        filtered_q = [x for x in q if target_state is None or x.get("state") == target_state]
        
        # 4. Side-by-side Review Panel
        if not filtered_q:
            st.info(T_("No claims match this filter.", "इस फ़िल्टर से कोई दावा मेल नहीं खाता।"))
        for i, x in enumerate(filtered_q):
            with st.container(border=True):
                if x.get("state") == "Needs review":
                    rev_l, rev_r = st.columns([1.1, 1.4], gap="medium")
                    with rev_l:
                        st.markdown(f"**{T_('AI Damage Inspection Photo', 'क्षति निरीक्षण फोटो')}**")
                        if "img" in st.session_state and st.session_state.get("cid") == x["id"]:
                            rim, rbox = st.session_state.img
                            c_curr = st.session_state.get("claim", {})
                            rim_ann, _ = annotate(rim, c_curr.get("items", []), rbox)
                            st.image(rim_ann, caption=f"Case {x['id']} Localized Bounding Boxes", use_container_width=True)
                        elif os.path.exists(os.path.join(SAMPLE_DIR, "demo_severe_crash.jpg")):
                            st.image(os.path.join(SAMPLE_DIR, "demo_severe_crash.jpg"), caption=f"Case {x['id']} Damage Photo", use_container_width=True)
                    with rev_r:
                        st.markdown(f"### Claim {x['id']} &nbsp; <span class='pill warn'>{x.get('state')}</span>", unsafe_allow_html=True)
                        st.markdown(f"**{T_('Escalation Reasons / Safety Flags:', 'समीक्षा के कारण:')}**")
                        st.error(x.get('detail', 'Human review required'))
                        st.markdown(f"Net Claim Value: **{core.inr(x.get('net', 0))}**")
                        st.markdown(f"**{T_('Adjuster Decision:', 'सर्वेयर निर्णय:')}**")
                        btn_app, btn_rej = st.columns(2)
                        if btn_app.button(f"✓ {T_('Approve Claim', 'दावा स्वीकृत करें')}", key=f"app_{x['id']}_{i}", type="primary", use_container_width=True):
                            x["state"] = "Approved by adjuster"; db_save(d); log("ADJUSTER", f"{x['id']} approved")
                            if st.session_state.get("claim") and st.session_state.get("cid") == x["id"]:
                                c = st.session_state.claim
                                c["status"] = "negotiating"
                                c["flags"] = []
                            st.rerun()
                        if btn_rej.button(f"✕ {T_('Reject Claim', 'दावा अस्वीकृत करें')}", key=f"rej_{x['id']}_{i}", type="secondary", use_container_width=True):
                            x["state"] = "Rejected by adjuster"; db_save(d); log("ADJUSTER", f"{x['id']} rejected")
                            if st.session_state.get("claim") and st.session_state.get("cid") == x["id"]:
                                c = st.session_state.claim
                                c["status"] = "rejected"
                            st.rerun()
                else:
                    r1, r2, r3, r4 = st.columns([1, 4, 2, 2], vertical_alignment="center")
                    r1.write(f"**{x['id']}**")
                    r2.write(x.get("detail", ""))
                    st_str = x.get("state", "")
                    badge_cls = "ok" if "settled" in st_str.lower() or "approved" in st_str.lower() else "bad"
                    r3.markdown(f"<span class='pill {badge_cls}'>{st_str}</span>", unsafe_allow_html=True)
                    r4.write(f"Paid: {core.inr(x.get('paid', 0))}")
        
        st.divider()
        if st.button(T_("Clear all stored data (demo reset)", "सभी डेटा साफ़ करें (डेमो रीसेट)")):
            db_save({"queue": [], "log": [], "hashes": []}); st.rerun()
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
