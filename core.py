"""Auto-Settle core logic. The AI only DESCRIBES damage; plain code sets every number and enforces every limit."""
import base64, io, json, os, re
import requests

PARTS = {"bumper": (6500, 3), "door": (9000, 4), "mirror": (3500, 1), "headlight": (5500, 1.5),
         "fender": (7000, 3), "bonnet": (11000, 4), "windshield": (8000, 2),
         "grille": (3000, 1), "wheel": (6000, 1.5), "taillight": (4000, 1), "boot": (9500, 3.5)}  # (parts cost INR, labour hours) - mock reference data
SEV = {"minor": .25, "moderate": .6, "severe": 1.0}
TYP = {"scratch": .5, "dent": .8, "crack": 1.0, "broken": 1.2}
RATE = 500  # INR per labour hour (assumption)

def inr(n): return "\u20b9{:,.0f}".format(n)

# ---------- LLM access: Claude, any OpenAI-compatible API (OpenAI, Gemini, Groq, OpenRouter), or a local Ollama model ----------
def env_cfg():
    p = os.getenv("PROVIDER", "anthropic")
    if p == "openai": return {"type": "openai", "model": os.getenv("OPENAI_MODEL", ""), "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), "key": os.getenv("OPENAI_API_KEY", "")}
    if p == "ollama": return {"type": "ollama", "model": os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b"), "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434"), "key": ""}
    return {"type": "anthropic", "model": os.getenv("MODEL", "claude-sonnet-5-5"), "base_url": "", "key": os.getenv("ANTHROPIC_API_KEY", "")}

def ask_llm(prompt, img_jpeg=None, cfg=None):
    cfg = cfg or env_cfg(); t = cfg["type"]; b64 = base64.b64encode(img_jpeg).decode() if img_jpeg else None
    if t == "ollama":
        m = {"role": "user", "content": prompt}
        if b64: m["images"] = [b64]
        base = (cfg.get("base_url") or "http://localhost:11434").rstrip("/")
        if base.endswith("/api/chat"): base = base[:-9]
        r = requests.post(base + "/api/chat", timeout=300, json={"model": cfg["model"], "messages": [m], "stream": False})
        r.raise_for_status(); return r.json()["message"]["content"]
    if t == "openai":
        content = [{"type": "text", "text": prompt}]
        if b64: content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
        base = (cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        url = base + "/chat/completions"
        r = requests.post(url, timeout=120,
                          headers={"Authorization": "Bearer " + cfg["key"]}, json={"model": cfg["model"], "messages": [{"role": "user", "content": content}]})
        r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]
    import anthropic
    content = []
    if b64: content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    content.append({"type": "text", "text": prompt})
    r = anthropic.Anthropic(api_key=cfg.get("key") or None).messages.create(model=cfg["model"], max_tokens=700, messages=[{"role": "user", "content": content}])
    return r.content[0].text

def score(found, truth):
    """Precision and recall of the damaged parts a model found versus the true parts."""
    f, t = set(found), set(truth); tp = len(f & t)
    return (round(tp / len(f), 2) if f else 0.0, round(tp / len(t), 2) if t else 0.0)

VISION_PROMPT = ("You are a careful motor-insurance vehicle damage inspector. Examine the WHOLE image systematically, area by area (front bumper, grille, bonnet, both fenders, headlights, doors, mirrors, windshield, wheels and tyres, rear). List EVERY visibly damaged, torn or missing part in items, including partly visible ones, and do not stop at the most obvious damage. Return ONLY JSON: "
  '{"part": one of %s, "type": one of dent|scratch|crack|broken, "severity": one of minor|moderate|severe, '
  '"items": [{"part","type","severity"} for EVERY damaged part], "confidence": 0-100 integer, '
  '"quality_ok": false if blurry, dark, cropped or not a vehicle, "box": [x,y,width,height] fractions 0-1 around the worst damage, '
  '"notes": one short sentence}. The top-level part/type/severity describe the worst damage.') % "|".join(PARTS)

def analyse_image(jpeg, cfg=None):
    def pj(t): return json.loads(re.search(r"\{.*\}", t, re.S).group(0))
    r = pj(ask_llm(VISION_PROMPT, jpeg, cfg))
    try:  # second pass: ask the model to look again for missed parts
        r2 = pj(ask_llm("Earlier you listed these damaged parts: " + json.dumps(r.get("items") or [r]) + ". Look at the image again, area by area. "
                        'Return ONLY JSON {"items":[every damaged part including any you missed, each {"part","type","severity"}]}. Allowed parts: ' + "|".join(PARTS), jpeg, cfg))
        old = {i.get("part") for i in (r.get("items") or [r])}
        if len(r2.get("items", [])) >= len(old): r["added"] = len({i.get("part") for i in r2["items"]} - old); r["items"] = r2["items"]
    except Exception: pass
    return r

def translate_hi(text, cfg=None):
    try: return ask_llm("Translate to Hindi (Devanagari). Keep every rupee amount and digit unchanged. Output only the translation: " + text, cfg=cfg).strip()
    except Exception: return text

# ---------- estimate, flags, risk ----------
def assess(f, claimed, policy, rails, extra_flags=()):
    items = [{"part": i.get("part") if i.get("part") in PARTS else "bumper", "type": i.get("type"), "severity": i.get("severity")}
             for i in (f.get("items") or [f])]
    raw = lab = 0.0
    for i in items:
        cost, hrs = PARTS[i["part"]]; sv = SEV.get(i["severity"], .6); tp = TYP.get(i["type"], .8)
        raw += cost * sv * tp; lab += hrs * RATE * (.5 + sv / 2)
    dep = min(.5, max(0, policy["age"]) * .05)           # illustrative: 5% per year, max 50%
    parts = raw * (1 - dep); gross = parts + lab; net = max(0.0, gross - policy["excess"])
    conf = f.get("confidence", 0)
    flags = list(extra_flags)
    if not f.get("quality_ok", True): flags.append("Photo quality unusable")
    if conf < rails["min_conf"]: flags.append(f"AI confidence {conf}% is below the {rails['min_conf']}% threshold")
    if any(i["severity"] == "severe" for i in items): flags.append("Severe damage needs a human inspection")
    if net > rails["cap"]: flags.append(f"Net claim {inr(net)} exceeds the auto-settle cap {inr(rails['cap'])}")
    if claimed not in [i["part"] for i in items]:
        flags.append(f"Customer claimed '{claimed}' but the photo shows {', '.join(i['part'] for i in items)} (possible mismatch)")
    if f.get("added", 0) >= 2: flags.append(f"AI found {f['added']} more damaged parts on a second look, so its first answer was unstable")
    if not policy["active"]: flags.append("Policy is not active, so a human must confirm cover")
    if policy["claims"] >= 3: flags.append(f"{policy['claims']} claims in the last 12 months")
    if gross > policy["limit"]: flags.append(f"Repair estimate {inr(gross)} exceeds the policy claim limit {inr(policy['limit'])}")
    risk = min(100, round((100 - conf) * .5 + len(flags) * 20))
    band = (100 - conf) / 200
    return {"items": items, "parts": parts, "labour": lab, "gross": gross, "net": net, "dep": dep, "excess": policy["excess"],
            "lo": net * rails["lo"], "hi": net * rails["hi"], "band": (net * (1 - band), net * (1 + band)),
            "flags": flags, "risk": risk, "conf": conf, "notes": f.get("notes", ""),
            "status": "escalated" if flags else "negotiating", "offer": net * rails["lo"], "round": 0, "amount": None}

# ---------- negotiation: code decides every number ----------
INJECT = r"ignore (all|previous|your)|system prompt|you are now|override|pretend"
ANGRY = r"lawyer|legal action|court|ombudsman|irdai|consumer forum|cheat|useless|worst|angry"

def opening(c): return (f"Hello! I\u2019ve reviewed your photos. Your net claim value (after depreciation and policy excess) is {inr(c['net'])}. "
                        f"If you take cash instead, I can offer {inr(c['offer'])} right now, paid instantly with no garage wait. What do you think?")

def _settle(c, amt, why): c["status"], c["amount"] = "settled", amt; return f"Deal confirmed: {inr(amt)} cash settlement. {why}"
def _esc(c, why): c["status"] = "escalated"; c["flags"].append(why); return why + " I\u2019m passing your claim to a human adjuster who will contact you."

def negotiate(c, text, rails):
    low = text.lower()
    if re.search(INJECT, low): return _esc(c, "Your message looks like an attempt to change my rules, so this has been flagged.")
    if re.search(ANGRY, low): return _esc(c, "I can hear this is frustrating, and a person should handle it.")
    m = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if not m: return f"Could you share the amount you have in mind in rupees? My current offer is {inr(c['offer'])}."
    ask = float(m.group()); c["round"] += 1; step = rails["step"] * c["net"]
    if ask <= c["offer"]: return _settle(c, ask, "Accepted your figure.")
    if ask <= c["hi"] and ask - c["offer"] <= step: return _settle(c, ask, "Your figure is within my authority.")
    if c["round"] > rails["max_rounds"]:
        if ask > c["hi"] * 1.5: return _esc(c, "This amount is far outside what I am allowed to settle.")
        c["offer"] = c["hi"]
        return f"My final offer is {inr(c['hi'])}, which is the most I can approve. Please accept it, or I can pass this to a human adjuster."
    c["offer"] = min(c["offer"] + step, c["hi"], ask)
    return (f"I can\u2019t go as high as {inr(ask)}. The most I can do is within the approved range, so I can move to {inr(c['offer'])}."
            if ask > c["hi"] else f"I can move to {inr(c['offer'])}. Would that work?")
