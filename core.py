"""Auto-Settle core logic. The AI only DESCRIBES damage; plain code sets every number and enforces every limit."""
import base64, io, json, os, re, time
import requests

PARTS = {"bumper": (6500, 3), "door": (9000, 4), "mirror": (3500, 1), "headlight": (5500, 1.5),
         "fender": (7000, 3), "bonnet": (11000, 4), "windshield": (8000, 2),
         "grille": (3000, 1), "wheel": (6000, 1.5), "taillight": (4000, 1), "boot": (9500, 3.5)}  # (parts cost INR, labour hours) - mock reference data
SEV = {"minor": .25, "moderate": .6, "severe": 1.0}
TYP = {"scratch": .5, "dent": .8, "crack": 1.0, "broken": 1.2}
MAX_TOKENS = 2500   # generous: thinking models spend part of this budget before answering
RATE = 500  # INR per labour hour (assumption)

def inr(n): return "\u20b9{:,.0f}".format(n)

# ---------- LLM access: Claude, any OpenAI-compatible API (OpenAI, Gemini, Groq, OpenRouter), or a local Ollama model ----------
def env_cfg():
    p = os.getenv("PROVIDER", "anthropic")
    if p == "openai": return {"type": "openai", "model": os.getenv("OPENAI_MODEL", ""), "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), "key": os.getenv("OPENAI_API_KEY", "")}
    if p == "ollama": return {"type": "ollama", "model": os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b"), "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434"), "key": ""}
    return {"type": "anthropic", "model": os.getenv("MODEL", "claude-sonnet-5-5"), "base_url": "", "key": os.getenv("ANTHROPIC_API_KEY", "")}

def ask_llm(prompt, img_jpeg=None, cfg=None):
    cfg = cfg or env_cfg(); t = "openai" if cfg["type"] == "openai-compatible" else cfg["type"]; b64 = base64.b64encode(img_jpeg).decode() if img_jpeg else None
    if t == "ollama":
        m = {"role": "user", "content": prompt}
        if b64: m["images"] = [b64]
        base = (cfg.get("base_url") or "http://localhost:11434").rstrip("/")
        if base.endswith("/api/chat"): base = base[:-9]
        r = requests.post(base + "/api/chat", timeout=300, json={"model": cfg["model"], "messages": [m], "stream": False})
        r.raise_for_status(); return r.json()["message"]["content"]
    if t == "openai":
        from openai import OpenAI
        content = [{"type": "text", "text": prompt}]
        if b64: content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
        api_key = cfg.get("key") or cfg.get("api_key") or ""
        base_url = (cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        headers = {}
        if "openrouter" in base_url.lower():
            headers["HTTP-Referer"] = "https://auto-settle-ng434.streamlit.app"
            headers["X-Title"] = "Auto-Settle AI"
        client = OpenAI(api_key=api_key, base_url=base_url, default_headers=headers if headers else None, timeout=60.0)
        call_kwargs = {"model": cfg["model"], "messages": [{"role": "user", "content": content}], "max_tokens": MAX_TOKENS}
        if "gemini" in str(cfg.get("model", "")).lower():
            call_kwargs["reasoning_effort"] = "low"  # drastically reduces Gemini 3.8 thinking latency
        for attempt in range(3):
            try:
                r = client.chat.completions.create(**call_kwargs)
                return r.choices[0].message.content
            except Exception as ex:
                s = str(ex).lower()
                if "reasoning_effort" in s:
                    call_kwargs.pop("reasoning_effort", None)
                    continue
                if ("429" in s or "quota" in s or "rate" in s or "exhausted" in s or "overloaded" in s or "busy" in s) and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise
    import anthropic
    content = []
    if b64: content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    content.append({"type": "text", "text": prompt})
    r = anthropic.Anthropic(api_key=cfg.get("key") or None).messages.create(model=cfg["model"], max_tokens=MAX_TOKENS, messages=[{"role": "user", "content": content}])
    return r.content[0].text

def score(found, truth):
    """Precision and recall of the damaged parts a model found versus the true parts."""
    f, t = set(found), set(truth); tp = len(f & t)
    return (round(tp / len(f), 2) if f else 0.0, round(tp / len(t), 2) if t else 0.0)

VISION_PROMPT = ("You are a careful motor-insurance vehicle damage inspector. Examine the WHOLE image systematically, area by area (front bumper, grille, bonnet, both fenders, headlights, doors, mirrors, windshield, wheels and tyres, rear). List EVERY visibly damaged, torn or missing part in items, including partly visible ones, and do not stop at the most obvious damage. Return ONLY JSON: "
  '{"part": one of %s, "type": one of dent|scratch|crack|broken, "severity": one of minor|moderate|severe, '
  '"items": [{"part","type","severity","box": [x,y,width,height] fractions 0-1 tightly around THAT part} for EVERY damaged part], "confidence": 0-100 integer, '
  '"quality_ok": false if blurry, dark, cropped or not a vehicle, "box": [x,y,width,height] fractions 0-1 around the worst damage, '
  '"notes": one short sentence}. The top-level part/type/severity describe the worst damage.') % "|".join(PARTS)

def _items(f):
    """The model's damaged-part list, cleaned: only dict entries; falls back to the top-level finding."""
    its = f.get("items")
    if isinstance(its, dict): its = [its]
    its = [i for i in its if isinstance(i, dict)] if isinstance(its, list) else []
    return its or [f]

def valid_box(b):
    """A box is [x, y, width, height] as fractions of the image, inside the frame."""
    try:
        x, y, w, h = [float(v) for v in b]
        return 0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.02 and y + h <= 1.02
    except Exception: return False

def analyse_image(jpeg, cfg=None):
    def pj(t):
        if not t: raise ValueError("Empty model response")
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
        candidates = [fence.group(1)] if fence else []
        start = t.find("{")
        if start != -1:
            depth = 0
            for idx in range(start, len(t)):
                if t[idx] == '{': depth += 1
                elif t[idx] == '}':
                    depth -= 1
                    if depth == 0:
                        candidates.append(t[start:idx+1])
                        break
        m = re.search(r"\{.*\}", t, re.S)
        if m: candidates.append(m.group(0))
        for raw in candidates:
            try: return json.loads(raw)
            except Exception: pass
            raw_clean = re.sub(r",\s*([}\]])", r"\1", raw)
            try: return json.loads(raw_clean)
            except Exception: pass
            raw_clean = raw_clean.replace("'", '"')
            raw_clean = re.sub(r'(?<=\{|,)\s*(\w+)\s*:', r' "\1":', raw_clean)
            try: return json.loads(raw_clean)
            except Exception: pass
        raise ValueError("No JSON object found in model response: " + str(t[:150]))
    try: r = pj(ask_llm(VISION_PROMPT, jpeg, cfg))
    except ValueError:      # empty, truncated or non-JSON reply (JSONDecodeError is a ValueError): ask once more, strictly
        r = pj(ask_llm(VISION_PROMPT + " IMPORTANT: reply with ONE compact JSON object only. No markdown, no commentary.", jpeg, cfg))
    try:  # second pass: ask the model to look again for missed parts
        time.sleep(1.5)  # brief pause to stay under burst rate limits
        r2 = pj(ask_llm("Earlier you listed these damaged parts: " + json.dumps(_items(r)) + ". Look at the image again, area by area. "
                        'Return ONLY JSON {"items":[every damaged part including any you missed, each {"part","type","severity","box":[x,y,width,height] fractions 0-1 tightly around that part}]}. Allowed parts: ' + "|".join(PARTS), jpeg, cfg))
        first = _items(r)
        second = _items(r2) if r2.get("items") else []
        old = {i.get("part") for i in first}
        if second and len(second) >= len(old):
            r["added"] = len({i.get("part") for i in second} - old)
            for i in second:                                   # keep a box if the second pass dropped it
                if not valid_box(i.get("box")):
                    prev = next((p for p in first if p.get("part") == i.get("part") and valid_box(p.get("box"))), None)
                    if prev: i["box"] = prev["box"]
                    elif i.get("part") == r.get("part") and valid_box(r.get("box")): i["box"] = r["box"]
            r["items"] = second
    except Exception: pass
    return r

def translate_hi(text, cfg=None):
    try: return ask_llm("Translate to Hindi (Devanagari). Keep every rupee amount and digit unchanged. Output only the translation: " + text, cfg=cfg).strip()
    except Exception: return text

# ---------- estimate, flags, risk ----------
def _num(v, default=0.0):
    """Coerce a model-supplied value ('85', 85, '85%') to a float; never raises."""
    try: return float(str(v).strip().rstrip("%"))
    except Exception: return default

def assess(f, claimed, policy, rails, extra_flags=()):
    raw_items = _items(f)
    unknown = sorted({str(i.get("part")) for i in raw_items if i.get("part") not in PARTS})   # parts we cannot price
    items = [{"part": i.get("part") if i.get("part") in PARTS else "bumper", "type": i.get("type"), "severity": i.get("severity"),
              "box": [float(v) for v in i["box"]] if valid_box(i.get("box")) else None} for i in raw_items]
    dep = min(.5, max(0, _num(policy["age"])) * .05)     # illustrative: 5% per year, max 50%
    raw = lab = 0.0
    for i in items:
        cost, hrs = PARTS[i["part"]]; sv = SEV.get(i["severity"], .6); tp = TYP.get(i["type"], .8)
        p_raw = cost * sv * tp; p_lab = hrs * RATE * (.5 + sv / 2)
        raw += p_raw; lab += p_lab
        i["parts_cost"], i["labour"] = p_raw * (1 - dep), p_lab; i["est"] = i["parts_cost"] + p_lab   # per-part estimate shown in the UI
    parts = raw * (1 - dep); gross = parts + lab; net = max(0.0, gross - policy["excess"])
    conf = max(0, min(100, round(_num(f.get("confidence", 0)))))
    flags = list(extra_flags)
    if not f.get("quality_ok", True): flags.append("Photo quality unusable")
    if unknown: flags.append(f"AI reported part(s) not in the price table: {', '.join(unknown)}, so the estimate is unreliable")
    if net <= 0: flags.append(f"Repair estimate {inr(gross)} is within the {inr(policy['excess'])} policy excess, so no payout is due. A human must confirm")
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
INJECT = r"\b(?:ignore (?:all|previous|your)|system prompt|you are now|pretend)\b|\boverride (?:your|all|the) (?:rules|instructions|guardrails)\b"
ANGRY = r"\b(?:lawyer|legal action|court|ombudsman|irdai|consumer forum|cheat(?:ed|ing)?|useless|worst|angry)\b"
HUMAN = r"\b(?:human|adjuster|representative|real person|(?:talk|speak|connect|transfer)(?: me)? (?:to|with) (?:a|an|the|some)\w*)\b"
ACCEPT = r"\b(?:yes|yeah|ok|okay|accept(?:ed)?|deal|agreed?|sure|fine)\b"
REFUSE = r"\b(?:no|not|don'?t|can'?t|cannot|won'?t|never|reject)\b"
_AMT = re.compile(r"(?P<cur>₹|rs\.?|inr)?\s*(?P<n>\d+(?:\.\d+)?)(?!\.?\d)\s*(?P<mul>k\b|thousand\b|lakhs?\b|lacs?\b)?(?!\s*(?:days?|years?|yrs?|months?|hours?|hrs?|%|percent|km|kms|times|parts?|rounds?))", re.I)

def parse_amount(text):
    """First plausible rupee amount in free text, or None. Handles 3,500 / 3500 / 3.5k / 2 lakh / Rs 4000.
    Ignores durations, years (e.g. '2019 model') and tiny bare numbers, which are not rupee offers."""
    for m in _AMT.finditer(text.replace(",", "")):
        n, cur, mul = float(m.group("n")), m.group("cur"), (m.group("mul") or "").lower()
        if mul: n *= 100000 if mul.startswith(("lakh", "lac")) else 1000
        elif not cur and (1900 <= n <= 2100 or n < 100): continue
        return n
    return None

def opening(c): return (f"Hello! I\u2019ve reviewed your photos. Your net claim value (after depreciation and policy excess) is {inr(c['net'])}. "
                        f"If you take cash instead, I can offer {inr(c['offer'])} right now, paid instantly with no garage wait. What do you think?")

def _settle(c, amt, why): c["status"], c["amount"] = "settled", amt; return f"Deal confirmed: {inr(amt)} cash settlement. {why}"
def _esc(c, why): c["status"] = "escalated"; c["flags"].append(why); return why + " I\u2019m passing your claim to a human adjuster who will contact you."

def negotiate(c, text, rails):
    low = text.lower()
    if re.search(INJECT, low): return _esc(c, "Your message looks like an attempt to change my rules, so this has been flagged.")
    if re.search(ANGRY, low): return _esc(c, "I can hear this is frustrating, and a person should handle it.")
    if re.search(HUMAN, low): return _esc(c, "Understood, you would like to speak to a person.")
    ask = parse_amount(text)
    if ask is None:
        if re.search(ACCEPT, low) and not re.search(REFUSE, low): return _settle(c, c["offer"], "Accepted my current offer.")
        return f"Could you share the amount you have in mind in rupees (for example 3500)? My current offer is {inr(c['offer'])}."
    c["round"] += 1; step = rails["step"] * c["net"]
    if ask <= c["offer"]: return _settle(c, c["offer"], f"You asked for {inr(ask)}, which is below my offer, so you receive my full offer.")
    if ask <= c["hi"] and ask - c["offer"] <= step: return _settle(c, ask, "Your figure is within my authority.")
    if c["round"] > rails["max_rounds"]:
        if ask > c["hi"] * 1.5: return _esc(c, "This amount is far outside what I am allowed to settle.")
        c["offer"] = c["hi"]
        return f"My final offer is {inr(c['hi'])}, which is the most I can approve. Please accept it, or I can pass this to a human adjuster."
    c["offer"] = min(c["offer"] + step, c["hi"], ask)
    return (f"I can\u2019t go as high as {inr(ask)}. The most I can do is within the approved range, so I can move to {inr(c['offer'])}."
            if ask > c["hi"] else f"I can move to {inr(c['offer'])}. Would that work?")
