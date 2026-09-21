"""Generate the BloodSight AI sketches (Obsidian Excalidraw file): screens, user flow, decision rules.

Usage: python gen_sketches.py <output .excalidraw.md path>
Screen 1 mirrors app.py and its numbers for the dataset ending 2026-09-21.
"""
import json, random, sys, textwrap, time

random.seed(21)
INK, GREY, ORANGE = "#1e1e1e", "#868e96", "#e8590c"
RED, GREEN, BLUE, VIOLET = ("#e03131", "#ffc9c9"), ("#2f9e44", "#b2f2bb"), ("#1971c2", "#a5d8ff"), ("#6741d9", "#d0bfff")
PLAIN, YELLOW, WHITE = (INK, "#f1f3f5"), (INK, "#ffec99"), (INK, "#ffffff")
CW = 0.5  # average character width as a share of the font size
els = []
NOW = int(time.time() * 1000)


def _id():
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))


def _base(t, x, y, w, h, stroke, bg, sw, rnd):
    e = dict(id=_id(), type=t, x=x, y=y, width=w, height=h, angle=0, strokeColor=stroke, backgroundColor=bg,
             fillStyle="solid", strokeWidth=sw, strokeStyle="solid", roughness=1, opacity=100, groupIds=[],
             frameId=None, roundness=rnd, seed=random.randint(1, 2**31), version=1,
             versionNonce=random.randint(1, 2**31), isDeleted=False, boundElements=[], updated=NOW,
             locked=False, link=None)
    els.append(e)
    return e


def R(x, y, w, h, col=WHITE, sw=2, rnd=True):
    return _base("rectangle", x, y, w, h, col[0], col[1], sw, {"type": 3} if rnd else None)


def E(x, y, w, h, col=(GREY, "#ffffff")):
    return _base("ellipse", x, y, w, h, col[0], col[1], 1, {"type": 2})


def L(x, y, dx, dy, color=GREY, sw=1, dashed=False, arrow=False):
    e = _base("arrow" if arrow else "line", x, y, abs(dx), abs(dy), color, "transparent", sw, None)
    e.update(points=[[0, 0], [dx, dy]], lastCommittedPoint=None, startBinding=None, endBinding=None,
             startArrowhead=None, endArrowhead="arrow" if arrow else None)
    if arrow:
        e["elbowed"] = False
    if dashed:
        e["strokeStyle"] = "dashed"
    return e


def A(x, y, dx, dy, color=INK, sw=3):
    return L(x, y, dx, dy, color, sw, arrow=True)


def T(x, y, text, fs=20, color=INK, w=None, align="left"):
    """Text. With w the text is wrapped to that width; returns the y just below the text."""
    if w:
        n = max(8, int(w / (fs * CW)))
        text = "\n".join("\n".join(textwrap.wrap(p, n)) if p else "" for p in text.split("\n"))
    lines = text.split("\n")
    width = w if (w and align != "left") else max(len(l) for l in lines) * fs * CW
    h = len(lines) * fs * 1.25
    e = _base("text", x, y, width, h, color, "transparent", 1, None)
    e.update(text=text, rawText=text, originalText=text, fontSize=fs, fontFamily=5, textAlign=align,
             verticalAlign="top", containerId=None, autoResize=True, lineHeight=1.25)
    return y + h


def chip(x, y, text, col=PLAIN, fs=16):
    w = len(text) * fs * 0.54 + 22
    R(x, y, w, fs + 14, col, 1)
    T(x + 11, y + 6, text, fs, col[0] if col[0] != INK else INK)
    return x + w + 8


def button(x, y, w, text, col=PLAIN, fs=20, h=48):
    R(x, y, w, h, col, 2)
    T(x, y + (h - fs * 1.25) / 2, text, fs, INK, w=w, align="center")


# ---------------------------------------------------------------- phones
PH_W, PH_H, PITCH, PY = 560, 1120, 710, 2010
TABS = ["Results", "Needs", "Donations", "Ask", "Me"]


def phone(i, label, header, active, right=None, tabs=True, x0=0, y0=PY):
    px = x0 + i * PITCH
    T(px, y0 - 70, label, 36)
    R(px, y0, PH_W, PH_H, WHITE, 4)
    L(px, y0 + 92, PH_W, 0)
    T(px + 28, y0 + 28, header, 30)
    if right:
        T(px + PH_W - 28 - len(right) * 18 * CW, y0 + 36, right, 18, GREY)
    if tabs:
        L(px, y0 + 1024, PH_W, 0)
        for k, name in enumerate(TABS):
            if k == active:
                R(px + 6 + k * 110, y0 + 1038, 108, 68, YELLOW, 2)
            T(px + 6 + k * 110, y0 + 1060, name, 18, INK, w=108, align="center")
    return px, y0


def note(px, text, y0=PY, w=620):
    T(px, y0 + PH_H + 24, text, 22, ORANGE, w=w)


def card(px, y, h, col=WHITE):
    R(px + 28, y, 504, h, col, 2)


def hop(i, text, y=480, x0=0, y0=PY):
    px = x0 + i * PITCH
    n = len(textwrap.wrap(text, int(138 / (20 * CW))))
    T(px + PH_W + 6, y0 + y - 14 - n * 25, text, 20, INK, w=138, align="center")
    A(px + PH_W + 12, y0 + y, 126, 0)


# ================================================================ top + section 1: laptops
T(0, 0, "BloodSight AI: the idea as screens", 74)
T(0, 110, "One spine: the blood centre sees a shortage before it happens, and the request reaches the right "
          "people in time: the lab's patients, people who gave there before, and people who live nearby.", 36)
T(0, 170, "Orange = why the screen exists.  Yellow = where you are.  Red = a shortage, or a value out of range.  "
          "Green = fine, or booked.  Blue = a place you gave blood to before.  Violet = written or proposed by "
          "the AI.", 24)
T(0, 214, "Screen 1 shows the numbers of the working prototype (synthetic dataset ending Mon 21 Sep 2026). All "
          "people, places, lab values and dates on the other screens are sample data.", 24)
T(0, 258, "Who uses it: (1) the blood centre and the lab, on a laptop; (2) the lab's patients, on the phone app "
          "or a laptop. A patient hears from places they gave blood to, and from places near their home that "
          "need blood.", 24)
LW, LH, LP, LY = 1700, 1040, 1860, 460


def laptop(i, label, org, items, active, url):
    x = i * LP
    T(x, LY - 70, label, 36)
    R(x, LY, LW, LH, WHITE, 4)
    R(x, LY, LW, 46, PLAIN, 2, rnd=False)
    for k in range(3):
        E(x + 18 + k * 26, LY + 14, 16, 16)
    R(x + 120, LY + 9, 620, 28, (GREY, "#ffffff"), 1)
    T(x + 134, LY + 14, url, 15, GREY)
    L(x + 300, LY + 46, 0, LH - 46)
    T(x + 30, LY + 76, "BLOODSIGHT AI", 18)
    T(x + 30, LY + 102, org, 16, GREY)
    for k, it in enumerate(items):
        if k == active:
            R(x + 18, LY + 152 + k * 62, 264, 48, YELLOW, 2)
        T(x + 40, LY + 162 + k * 62, it, 22)
    return x, LY


def lnote(x, text, w=1700):
    T(x, LY + LH + 24, text, 22, ORANGE, w=w)


CENTRE_TABS = ["Outlook", "Requests", "Bookings", "Ask"]
AMBER = ("#e67700", "#ffec99")

# ---- 1 outlook = the prototype
x, y0 = laptop(0, "1  Blood centre: outlook (the working prototype)", "Regional Blood Centre", CENTRE_TABS, 0,
               "localhost:8501  ·  streamlit run app.py")
T(x + 336, y0 + 60, "BloodSight AI", 30)
T(x + 336, y0 + 102, "Blood supply intelligence: see the shortage before it happens.", 16, GREY)
T(x + 1370, y0 + 64, "Regional Blood Centre (demo)", 16, GREY, w=300, align="right")
T(x + 1370, y0 + 88, "Monday, 21 September 2026", 18, INK, w=300, align="right")
kpis = [("Units in stock", "2,856"), ("Blood types at risk (14 days)", "4 of 8"),
        ("Earliest projected shortage", "O- in 7 days"), ("Forecast error (14-day backtest)", "10.0%")]
for k, (lab, val) in enumerate(kpis):
    kx = x + 336 + k * 337
    R(kx, y0 + 134, 322, 84, WHITE, 1)
    T(kx + 14, y0 + 144, lab, 15, GREY)
    T(kx + 14, y0 + 170, val, 28)
T(x + 336, y0 + 234, "Current stock and 14-day outlook", 22)
stock = [("O+", "1,205", "12.6", "Low"), ("O-", "184", "5.0", "Critical"), ("A+", "864", "10.9", "Low"),
         ("A-", "111", "5.2", "Medium"), ("B+", "261", "11.4", "Low"), ("B-", "45", "6.6", "Medium"),
         ("AB+", "160", "14.2", "Low"), ("AB-", "26", "6.1", "Medium")]
RISK = {"Low": GREEN, "Medium": AMBER, "Critical": RED}
for k, (bt, units, days, risk) in enumerate(stock):
    cx = x + 336 + k * 168
    R(cx, y0 + 270, 158, 122, RED if risk == "Critical" else WHITE, 2 if risk == "Critical" else 1)
    T(cx + 12, y0 + 276, bt, 24)
    T(cx + 12, y0 + 310, units + " units", 16)
    T(cx + 12, y0 + 332, days + " days of supply", 14, GREY)
    chip(cx + 12, y0 + 358, risk, RISK[risk], 13)
R(x + 336, y0 + 406, 1334, 88, RED, 2)
T(x + 356, y0 + 414, "Potential O- shortage detected", 22)
T(x + 356, y0 + 446, "No shortage today: 184 units in stock. Projected to fall under the safety threshold of 100 "
                     "units in 7 days, reaching 80 units a week from now.", 17, INK, w=1290)
# chart
CX, CY, CWID, CHT = x + 336, y0 + 508, 850, 290
R(CX, CY, CWID, CHT, WHITE, 1)
T(CX + 14, CY + 8, "O- inventory, next 14 days", 16, GREY)
T(CX + 300, CY + 8, "black = no campaign   ·   violet = with +210 donations", 15, VIOLET[0])
PX0, PX1, PYB, PYT, VMAX = CX + 60, CX + 690, CY + 256, CY + 40, 270
base_line = [184, 169, 154, 144, 136, 123, 103, 80, 61, 43, 30, 19, 2, 0, 0]
camp_line = [184, 169, 154, 144, 136, 165, 187, 206, 229, 253, 240, 229, 212, 189, 163]
sx = (PX1 - PX0) / 14


def vy(v):
    return PYB - (PYB - PYT) * v / VMAX


L(PX0, PYB, PX1 - PX0, 0, GREY, 1)
L(PX0, PYT, 0, PYB - PYT, GREY, 1)
for v, lab, col in [(100, "safety threshold: 100", RED[0]), (160, "warning level: 160", AMBER[0])]:
    L(PX0, vy(v), PX1 - PX0, 0, col, 1, dashed=True)
    T(PX1 + 6, vy(v) - 10, lab, 13, col)
for line, col, dash in [(camp_line, VIOLET[0], True), (base_line, INK, False)]:
    for k in range(1, 15):
        L(PX0 + (k - 1) * sx, vy(line[k - 1]), sx, vy(line[k]) - vy(line[k - 1]), col, 2, dashed=dash)
E(PX0 + 7 * sx - 7, vy(80) - 7, 14, 14, (RED[0], RED[1]))
T(PX0 + 7 * sx - 120, vy(80) + 8, "day 7: under 100", 14, RED[0])
for k, lab in [(0, "today"), (7, "Mon 28 Sep"), (12, "Sat 3 Oct: holiday"), ]:
    T(PX0 + k * sx - 20, PYB + 8, lab, 13, GREY)
T(CX + 12, PYT - 8, "270", 12, GREY)
T(CX + 28, PYB - 8, "0", 12, GREY)
# what-if
WX = x + 1200
R(WX, CY, 470, CHT, WHITE, 1)
T(WX + 16, CY + 8, "What-if: donor campaign", 20)


def slider(sy, label, val, frac):
    T(WX + 16, sy, label, 15, GREY)
    T(WX + 380, sy, val, 17, INK, w=74, align="right")
    L(WX + 16, sy + 34, 438, 0, GREY, 3)
    if frac:
        L(WX + 16, sy + 34, 438 * frac, 0, RED[0], 3)
    E(WX + 16 + 438 * frac - 9, sy + 25, 18, 18, (INK, "#ffffff"))


slider(CY + 44, "Additional donations", "210", 0.70)
slider(CY + 98, "Launch campaign in (days)", "0", 0.0)
slider(CY + 152, "Campaign length (days)", "5", 0.29)
T(WX + 16, CY + 204, "Units become usable 4 days after launch.", 13, GREY)
T(WX + 16, CY + 228, "Without campaign:", 15)
xx = chip(WX + 164, CY + 223, "Critical", RED, 13)
T(xx, CY + 228, "shortage in 7 days", 15)
T(WX + 16, CY + 258, "With +210 donations:", 15)
xx = chip(WX + 184, CY + 253, "Low", GREEN, 13)
T(xx, CY + 258, "shortage avoided", 15)
# recommendation
RY = y0 + 812
R(x + 336, RY, 800, 214, VIOLET, 2)
T(x + 356, RY + 10, "BloodSight recommendation", 15, VIOLET[0])
T(x + 356, RY + 34, "Launch a targeted O- donor campaign within 72 hours, before stock reaches critical levels.",
  21, INK, w=680)
T(x + 356, RY + 96, "Target: 210 additional donations   ·   Campaign window: 5 days   ·   Priority: High", 16)
T(x + 356, RY + 122, "Expected 14-day risk after campaign:", 16)
chip(x + 664, RY + 118, "Low", GREEN, 13)
button(x + 356, RY + 158, 300, "Launch O- donor campaign", RED, 19, 44)
T(x + 672, RY + 162, "prototype: notifies every O- patient, counts pledges\nplan: a targeted request, screen 2", 14, ORANGE)
R(x + 1156, RY, 514, 214, WHITE, 1)
T(x + 1174, RY + 10, "Why the model sees this", 19)
yy = RY + 44
for d in ["Usage is up 26% over the last 2 weeks versus the 4 weeks before.",
          "Donations are down 17% over the same period.",
          "Public holiday on Sat 3 Oct: donor turnout typically drops by about 55%."]:
    yy = T(x + 1174, yy, "- " + d, 15, INK, w=480) + 8
lnote(x, "This screen exists: it is the Streamlit prototype, with its real demo numbers. Stock looks fine today, "
         "the forecast crosses the safety threshold in 7 days, and the what-if sliders show that size and "
         "timing both matter. In the prototype the red button notifies every patient with that blood type and "
         "counts their pledges. The prototype has no sidebar; the sidebar shows where the planned screens "
         "would hang. Screen 2 is the planned step after the button: choose who is asked, how far away, and "
         "which slots.")
T(x + LW + 20, LY + 936, "plan: make\nit targeted", 20, INK, w=120, align="center")
A(x + LW + 16, LY + 1004, 128, 0)

# ---- 2 a request
x, y0 = laptop(1, "2  Blood centre: a request, before and after sending", "Regional Blood Centre", CENTRE_TABS, 1,
               "bloodsight.app/centre/requests/new")
T(x + 336, y0 + 74, "New request: O-", 34)
T(x + 336, y0 + 114, "filled in from the recommendation: 210 donations in 5 days", 15, VIOLET[0])
T(x + 336, y0 + 136, "Blood type", 20, GREY)
xx = x + 336
for t in ["O-", "O+", "A-", "A+", "plasma"]:
    xx = chip(xx, y0 + 166, t, YELLOW if t == "O-" else PLAIN, 18)
T(x + 336, y0 + 222, "How far from the centre", 20, GREY)
xx = x + 336
for t in ["10 km", "25 km", "50 km"]:
    xx = chip(xx, y0 + 252, t, YELLOW if t == "25 km" else PLAIN, 18)
T(x + 660, y0 + 222, "Slots offered", 20, GREY)
chip(x + 660, y0 + 252, "Tue 22 Sep to Sat 26 Sep", YELLOW, 18)
R(x + 336, y0 + 316, 640, 250, VIOLET, 2)
T(x + 356, y0 + 328, "Who gets it", 16, VIOLET[0])
T(x + 356, y0 + 354, "2,400 people match", 30)
T(x + 356, y0 + 402, "O- · home within 25 km · agreed to be asked · last gave 56 or more days ago · asked fewer "
                     "than 2 times this month. 1,150 are patients of the lab, 1,250 gave here before. Expected "
                     "from earlier requests: about 9 in 100 book, so about 210.", 18, INK, w=600)
T(x + 356, y0 + 510, "You see a count, not names. A name appears only when that person books a slot.", 17,
  VIOLET[0], w=600)
T(x + 336, y0 + 590, "What they read", 20, GREY)
R(x + 336, y0 + 622, 640, 170, WHITE, 2)
T(x + 356, y0 + 636, "The Regional Blood Centre expects to run short of O- blood next week. You can help prevent "
                     "it: slots from Tue 22 Sep to Sat 26 Sep. You gave here before.", 20, INK, w=600)
T(x + 356, y0 + 752, "Last sentence only for the 1,250 who gave here.", 15, GREY)
button(x + 336, y0 + 830, 320, "Send to 2,400 people", RED, 22, 56)
button(x + 672, y0 + 830, 160, "Save draft", PLAIN, 18, 56)
L(x + 1010, y0 + 74, 0, 880)
T(x + 1040, y0 + 74, "After sending: day 1 of 5", 30)
for k, (n, lab, col) in enumerate([("2,400", "asked", PLAIN), ("1,630", "seen", PLAIN), ("68", "booked", GREEN),
                                   ("74", "not this time", PLAIN)]):
    R(x + 1040 + k * 158, y0 + 130, 146, 110, col, 2)
    T(x + 1040 + k * 158, y0 + 142, n, 34, INK, w=146, align="center")
    T(x + 1040 + k * 158, y0 + 196, lab, 17, INK, w=146, align="center")
T(x + 1040, y0 + 262, "68 of 210 booked", 20)
R(x + 1040, y0 + 294, 630, 22, PLAIN, 1)
R(x + 1040, y0 + 294, 204, 22, GREEN, 1)
T(x + 1040, y0 + 340, "Bookings", 24)
for k, b in enumerate(["Tue 22 Sep · 16:30 · Lena V. · O- · gave here 3 Jul",
                       "Wed 23 Sep · 09:00 · Sam K. · O- · patient of the lab, first time",
                       "Wed 23 Sep · 17:15 · Noa B. · O- · gave here 3 Nov"]):
    R(x + 1040, y0 + 380 + k * 60, 630, 50, WHITE, 1)
    T(x + 1056, y0 + 394 + k * 60, b, 18)
T(x + 1040, y0 + 566, "65 more", 18, GREY)
R(x + 1040, y0 + 620, 630, 130, GREEN, 2)
T(x + 1060, y0 + 634, "The request closes itself when bookings reach 210, or when the forecast for O- is back "
                      "above the warning level of 160 units. People who have not answered stop seeing it.", 19,
  INK, w=590)
T(x + 1040, y0 + 776, "'Not this time' is a count only. The centre never learns who declined.", 17, GREY, w=620)
T(x + 1040, y0 + 840, "Bookings feed back into the outlook on screen 1 as expected donations.", 17, GREY, w=620)
lnote(x, "Left: the recommendation arrives already filled in, and staff decide distance and slots. The matching "
         "is done by the app and shown as a count. Right: the same page after sending. It shows bookings, "
         "because those are the only people who chose to be known.")

# ---- 3 lab
x, y0 = laptop(2, "3  Lab: publish results", "Bloodlab Maastricht",
               ["Publish results", "Patients", "Donor link", "Ask"], 0, "bloodsight.app/lab/publish")
T(x + 336, y0 + 74, "Publish results", 34)
T(x + 336, y0 + 122, "Batch of Mon 21 Sep · from the lab system", 18, GREY)
for k, (n, lab, col) in enumerate([("212", "reports", PLAIN), ("205", "ready", GREEN),
                                   ("3", "code does not match", YELLOW), ("4", "urgent values", RED)]):
    R(x + 336 + k * 220, y0 + 170, 204, 110, col, 2)
    T(x + 336 + k * 220, y0 + 182, n, 36, INK, w=204, align="center")
    T(x + 336 + k * 220, y0 + 236, lab, 17, INK, w=204, align="center")
T(x + 336, y0 + 316, "Held back", 24)
held = [("BL-4907 · potassium 6.4 mmol/L", "Urgent: doctor is phoned first", RED),
        ("BL-4911 · haemoglobin 7.2 g/dL", "Urgent: doctor is phoned first", RED),
        ("BL-5103 · name on sample differs", "Check by hand", YELLOW)]
for k, (a, b, col) in enumerate(held):
    R(x + 336, y0 + 356 + k * 64, 880, 54, WHITE, 1)
    T(x + 352, y0 + 372 + k * 64, a, 19)
    chip(x + 900, y0 + 366 + k * 64, b, col, 15)
T(x + 336, y0 + 556, "4 more", 18, GREY)
button(x + 336, y0 + 610, 320, "Publish 205 to patients", GREEN, 22, 56)
R(x + 336, y0 + 710, 880, 150, BLUE, 2)
T(x + 356, y0 + 724, "Donor link", 24)
T(x + 356, y0 + 762, "38 patients in this batch switched the donor part on. Their blood type is filled in from "
                     "this result. The lab passes nothing else to any blood centre.", 19, INK, w=840)
R(x + 1260, y0 + 170, 410, 360, WHITE, 2)
T(x + 1278, y0 + 184, "What the patient sees", 22)
R(x + 1278, y0 + 230, 374, 96, WHITE, 2)
T(x + 1294, y0 + 242, "Ferritin (iron store)", 22)
T(x + 1294, y0 + 280, "18 ng/mL", 18, GREY)
chip(x + 1560, y0 + 262, "Low", RED)
R(x + 1278, y0 + 344, 374, 160, VIOLET, 2)
T(x + 1294, y0 + 354, "Written by the AI", 15, VIOLET[0])
T(x + 1294, y0 + 380, "Ferritin shows how much iron your body has stored. Yours is under the lab's minimum.",
  18, INK, w=344)
lnote(x, "The lab is where every patient starts, and why a patient opens the app at all: their own results. "
         "Urgent values are never delivered by an app first: they are held until the doctor has phoned. The "
         "lab hands over one fact for donating, the blood type, and only for patients who switched that on.")

# ================================================================ section 2: phones
SY2 = LY + LH + 220
T(0, SY2, "The person's side, on the phone app", 74)
T(0, SY2 + 110, "A patient of the lab opens the app for their own results. Giving blood is a second, separate "
                "switch. On a laptop the five tabs become a sidebar.", 32)
assert PY == SY2 + 290, (PY, SY2 + 290)

# 1 First open
px, py = phone(0, "4  First open: one minute", "Welcome to BloodSight AI", None, tabs=False)
y = T(px + 28, py + 116, "Your lab code", 26)
R(px + 28, y + 8, 504, 52, WHITE, 2)
T(px + 46, y + 22, "e.g. BL-4821 (printed on your lab letter)", 20, GREY)
y = T(px + 28, y + 86, "Blood type", 26)
x = px + 28
for t in ["A+", "A-", "B+", "B-"]:
    x = chip(x, y + 8, t, PLAIN, 18)
x = chip(x, y + 8, "O-", YELLOW, 18)
x = px + 28
for t in ["O+", "AB+", "AB-"]:
    x = chip(x, y + 50, t, PLAIN, 18)
chip(x, y + 50, "I do not know", PLAIN, 18)
T(px + 28, y + 94, "Unknown: your lab result fills it in.", 17, GREY)
y = T(px + 28, y + 140, "Where do you live?", 26)
R(px + 28, y + 8, 504, 52, WHITE, 2)
T(px + 46, y + 22, "Postcode, e.g. 6211", 20, GREY)
y = T(px + 28, y + 86, "What may the app do?", 26)
for k, (txt, on) in enumerate([("Show me my lab results", True),
                               ("Tell me when a place nearby needs\nmy blood type", True),
                               ("Tell places I gave to before when I am\nallowed to give again", False)]):
    yy = y + 12 + k * 78
    R(px + 28, yy, 56, 30, GREEN if on else PLAIN, 2)
    E(px + (58 if on else 32), yy + 4, 22, 22, (INK, "#ffffff"))
    T(px + 100, yy - 2, txt, 19)
button(px + 60, py + 900, 440, "Continue", GREEN, 24, 56)
T(px + 28, py + 974, "Only results, no donor part", 20, GREY, w=504, align="center")
T(px + 28, py + 1050, "Each switch can be turned off later under Me.", 17, GREY, w=504, align="center")
note(px, "Three questions and three switches. The lab code is what ties the app to one patient, so nobody "
         "types in values by hand. Each permission is a separate switch: results only is a valid way to use "
         "the app.")
hop(0, "then")

# 2 Results
px, py = phone(1, "5  Results (home)", "BloodSight AI", 0, "Mon 21 Sep")
R(px + 28, py + 110, 504, 58, VIOLET, 2)
T(px + 48, py + 126, "Ask: what does my ferritin mean?", 20)
T(px + 28, py + 190, "Blood test of Mon 14 Sep", 24)
T(px + 28, py + 224, "Bloodlab Maastricht · 18 values · 2 out of range", 17, GREY)
rows = [("Ferritin (iron store)", "18 ng/mL", "Low", RED), ("LDL cholesterol", "3.9 mmol/L", "High", RED),
        ("Haemoglobin", "14.1 g/dL", "In range", GREEN), ("Thyroid (TSH)", "2.1 mU/L", "In range", GREEN)]
for k, (name, val, state, col) in enumerate(rows):
    yy = py + 264 + k * 108
    card(px, yy, 96)
    T(px + 44, yy + 12, name, 22)
    T(px + 44, yy + 50, val, 18, GREY)
    chip(px + 400, yy + 32, state, col)
T(px + 28, py + 702, "14 more values, all in range", 18, GREY)
R(px + 28, py + 742, 504, 96, BLUE, 2)
T(px + 44, py + 754, "Blood type from this test: O-", 20)
T(px + 44, py + 788, "2 places near you need O-  >", 18)
card(px, py + 854, 108)
T(px + 44, py + 864, "If you need blood", 20)
T(px + 44, py + 894, "With O- you can only receive O-.", 16, GREY)
chip(px + 44, py + 922, "O- supply: running short", RED, 15)
T(px + 28, py + 980, "Earlier reports: 3 Jun · 12 Feb", 18, GREY)
note(px, "Out-of-range values first, the rest folded away. The range is always the one printed by the lab. "
         "The blue card is the only bridge from results to donating, and it only appears if the person "
         "switched the donor part on. 'If you need blood' is already in the prototype: the supply of the "
         "types this person can receive.")
hop(1, "tap a value")

# 3 One marker
px, py = phone(2, "6  One value, opened", "< Ferritin (iron store)", 0)
T(px + 28, py + 116, "18 ng/mL", 40)
chip(px + 250, py + 128, "Low", RED, 18)
T(px + 28, py + 176, "Range printed by the lab: 30 to 300 ng/mL", 18, GREY)
card(px, py + 220, 250)
T(px + 44, py + 232, "Your last three tests", 18, GREY)
L(px + 60, py + 420, 440, 0, GREY, 1)
L(px + 60, py + 350, 440, 0, RED[0], 1, dashed=True)
T(px + 380, py + 324, "lab minimum", 15, RED[0])
pts = [(100, 300, "41"), (280, 330, "33"), (460, 388, "18")]
for k, (dx, dy, v) in enumerate(pts):
    E(px + dx - 8, py + dy - 8, 16, 16, (INK, "#1e1e1e"))
    T(px + dx - 12, py + dy - 38, v, 17)
    if k:
        L(px + pts[k - 1][0], py + pts[k - 1][1], dx - pts[k - 1][0], dy - pts[k - 1][1], INK, 2)
for dx, lab in [(76, "12 Feb"), (256, "3 Jun"), (430, "14 Sep")]:
    T(px + dx, py + 430, lab, 15, GREY)
R(px + 28, py + 492, 504, 190, VIOLET, 2)
T(px + 44, py + 502, "Written by the AI", 15, VIOLET[0])
T(px + 44, py + 528, "Ferritin shows how much iron your body has stored. Yours has gone down over three tests "
                     "and is now under the lab's minimum. I cannot say why: that is a question for your doctor.",
  19, INK, w=470)
T(px + 28, py + 710, "For donors", 22)
T(px + 28, py + 744, "Giving blood lowers iron stores. The donor centre checks this at every visit and decides "
                     "whether you can give.", 18, GREY, w=500)
button(px + 28, py + 880, 240, "Ask about this", VIOLET)
button(px + 292, py + 880, 240, "Summary for my doctor", PLAIN, 18)
T(px + 28, py + 956, "source: report of 14 Sep, line 7", 15, GREY)
note(px, "One value, the lab's own range, the trend, then plain words. The AI text is marked as AI text. It "
         "explains what the value is and never says what the person has.")
hop(2, "Needs tab")

# 4 Needs nearby
px, py = phone(3, "7  Needs nearby", "Needs nearby", 1, "6211")
x = px + 28
x = chip(x, py + 110, "All", YELLOW)
x = chip(x, py + 110, "My type", PLAIN)
x = chip(x, py + 110, "Places I gave to", BLUE)
chip(x, py + 110, "Urgent", RED)
needs = [("Regional Blood Centre", "needs O- · 2.1 km", "Shortage forecast in 7 days", RED, True,
          "Why you: you are O-, live 2.1 km away, last gave 80 days ago"),
         ("MUMC+ hospital", "needs O- · 3.4 km", "This week", PLAIN, False,
          "Why you: you are O- and live 3.4 km away"),
         ("Donor centre Heerlen", "needs plasma, any type · 24 km", "This month", PLAIN, True,
          "Why you: you gave here on 12 Feb")]
for k, (place, what, urg, col, gave, why) in enumerate(needs):
    yy = py + 164 + k * 190
    card(px, yy, 172)
    T(px + 44, yy + 12, place, 24)
    T(px + 44, yy + 48, what, 18, GREY)
    xx = chip(px + 44, yy + 82, urg, col, 15)
    if gave:
        chip(xx, yy + 82, "You gave here", BLUE, 15)
    T(px + 44, yy + 124, why, 15, VIOLET[0], w=470)
T(px + 28, py + 750, "Nothing else within 25 km.", 18, GREY)
T(px + 28, py + 788, "You are asked at most twice a month.", 18, GREY)
T(px + 28, py + 960, "Pause all requests", 20, GREY, w=504, align="center")
note(px, "Two reasons a place shows up here: it is near the person's home and needs their type, or the person "
         "gave there before. Every card says why this person sees it. No need, no card: the list is allowed "
         "to be empty.")
hop(3, "tap card")

# 5 A need, opened
px, py = phone(4, "8  A need, opened", "< Regional Blood Centre", 1)
chip(chip(px + 28, py + 112, "Shortage forecast", RED, 15), py + 112, "You gave here", BLUE, 15)
T(px + 28, py + 160, "Needs O- blood", 30)
T(px + 28, py + 204, "Forecast: short of O- from Mon 28 Sep · 2.1 km", 19, GREY)
R(px + 28, py + 250, 504, 116, VIOLET, 2)
T(px + 44, py + 262, "Why you see this: you are O-, you live 2.1 km away, and your last donation was 80 days "
                     "ago, on Fri 3 Jul.", 18, INK, w=470)
T(px + 28, py + 410, "Free slots", 22)
for k, (s, sel) in enumerate([("Tue 22 Sep · 16:30", True), ("Wed 23 Sep · 09:00", False),
                              ("Wed 23 Sep · 17:15", False)]):
    R(px + 28, py + 450 + k * 64, 504, 52, YELLOW if sel else WHITE, 2)
    T(px + 48, py + 464 + k * 64, s, 20)
T(px + 28, py + 660, "Bring an ID. Eat and drink before you come. The centre does a short health check first "
                     "and makes the final call.", 18, GREY, w=500)
button(px + 28, py + 800, 300, "Book Tue 16:30", GREEN, 22, 56)
button(px + 346, py + 800, 186, "Not this time", PLAIN, 18, 56)
T(px + 28, py + 880, "'Not this time' costs nothing and is never shown to the place.", 16, GREY, w=500)
note(px, "The centre's forecast, seen from the other side: a request turns into a booked slot in two taps. The place learns a name only at the moment of "
         "booking. The app never promises that the person can give: the centre decides at the visit.")
hop(4, "after the visit")

# 6 Donations
px, py = phone(5, "9  Donations", "My donations", 2)
T(px + 28, py + 112, "7", 56)
T(px + 84, py + 136, "donations · 3 places", 22, GREY)
R(px + 28, py + 200, 504, 70, GREEN, 2)
T(px + 44, py + 222, "Booked: Tue 22 Sep · 16:30 · Regional Blood Centre", 19)
T(px + 28, py + 294, "WHERE IT WENT", 16, GREY)
hist = [("Fri 3 Jul · whole blood", "Regional Blood Centre", "Used on Thu 9 Jul at MUMC+ hospital"),
        ("Thu 12 Feb · plasma", "Donor centre Heerlen", "Used in March, for medicine"),
        ("Mon 3 Nov · whole blood", "Regional Blood Centre", "Used on Sat 8 Nov at MUMC+ hospital")]
for k, (a, b, c) in enumerate(hist):
    yy = py + 326 + k * 136
    card(px, yy, 122)
    T(px + 44, yy + 10, a, 21)
    T(px + 44, yy + 42, b, 16, GREY)
    chip(px + 44, yy + 74, c, BLUE, 15)
T(px + 28, py + 744, "PLACES YOU GAVE TO", 16, GREY)
for k, (p, on) in enumerate([("Regional Blood Centre", True), ("Donor centre Heerlen", True),
                             ("MUMC+ hospital", False)]):
    yy = py + 778 + k * 56
    T(px + 28, yy, p, 20)
    chip(px + 380, yy - 4, "may ask me" if on else "may not", GREEN if on else PLAIN, 15)
T(px + 28, py + 960, "Next possible date: set by the donor centre", 17, GREY)
note(px, "The reason to come back: the person sees where each donation ended up. It is also the list of "
         "places that may ask them again, one switch per place.")
hop(5, "Ask tab")

# 7 Ask
px, py = phone(6, "10  Ask (the AI agent)", "Ask", 3)
R(px + 28, py + 110, 504, 64, VIOLET, 2)
T(px + 42, py + 118, "Knows: your own lab results · your donations\n· open needs near you", 16)


def bubble(x, y, w, text, mine):
    n = len(textwrap.wrap(text, int((w - 28) / (19 * CW))))
    h = n * 19 * 1.25 + 24
    R(x, y, w, h, PLAIN if mine else WHITE, 2)
    T(x + 14, y + 12, text, 19, INK, w=w - 28)
    return y + h + 16


y = bubble(px + 190, py + 196, 342, "Why is my ferritin low?", True)
y = bubble(px + 28, y, 430, "Your ferritin was 18 ng/mL on 14 Sep. The lab's range starts at 30. It fell over "
                            "your last three tests. I cannot tell you the cause. Your doctor can.", False)
T(px + 28, y - 10, "sources: reports of 12 Feb, 3 Jun, 14 Sep", 15, GREY)
y = bubble(px + 190, y + 26, 342, "Do I have anaemia?", True)
y = bubble(px + 28, y, 430, "I will not diagnose. Your haemoglobin is in range, your ferritin is low. Want a "
                            "one-page summary to take to your doctor?", False)
y = bubble(px + 190, y + 6, 342, "Can I give blood this week?", True)
y = bubble(px + 28, y, 430, "Two places near you need O-. The donor centre decides at the visit whether you "
                            "can give.", False)
R(px + 28, py + 950, 504, 52, WHITE, 2)
T(px + 46, py + 964, "Ask about your results or giving blood", 19, GREY)
note(px, "The assistant answers only from this person's own data and links every answer to the report it came "
         "from. Three things it refuses: a diagnosis, a cause, and a promise that the person can give blood.")

# ================================================================ section 3: user flow
FY = PY + PH_H + 330
T(0, FY, "The user flow, end to end", 56)
T(0, FY + 80, "White = the person, on the phone.  Grey = the blood centre, on a laptop.  Blue = the lab.  Red arrows = the "
              "two moments where the person's side and the centre's side touch.", 24)
BW, BH, BP, BX = 300, 100, 390, 260


def box(col, row_y, text, fill):
    x = BX + col * BP
    R(x, row_y, BW, BH, fill, 2)
    T(x + 10, row_y + (BH - len(textwrap.wrap(text, int((BW - 20) / (20 * CW)))) * 25) / 2, text, 20, INK,
      w=BW - 20, align="center")
    return x


def link(col, row_y):
    A(BX + col * BP + BW + 8, row_y + BH / 2, BP - BW - 16, 0)


RA, RB, RC = FY + 170, FY + 380, FY + 640
T(0, RA + 22, "The person:\nresults", 24)
T(0, RB + 22, "The person:\ngiving blood", 24)
T(0, RC + 22, "The blood\ncentre", 24)
rowA = [("Lab publishes results (3)", BLUE), ("Lab letter with a personal code", WHITE),
        ("First open: code, postcode, switches (4)", WHITE), ("Results (5)", WHITE),
        ("One value, opened (6)", WHITE), ("Ask, or a summary for the doctor (10)", WHITE)]
for c, (t, f) in enumerate(rowA):
    box(c, RA, t, (f[0], f[1]) if isinstance(f, tuple) else f)
    if c < len(rowA) - 1:
        link(c, RA)
rowB = [(3, "Needs nearby (7)"), (4, "A need, opened (8)"), (5, "Book a slot"), (6, "Give blood at the place"),
        (7, "Donations: where it went (9)")]
for c, t in rowB:
    box(c, RB, t, WHITE)
    if c < 7:
        link(c, RB)
A(BX + 3 * BP + BW / 2, RA + BH + 8, 0, RB - RA - BH - 16)
T(BX + 3 * BP + BW / 2 + 12, RA + BH + 40, "Needs tab", 18)
rowC = [(0, "Stock looks fine today (1)"), (1, "Forecast flags a shortage 7 days ahead (1)"),
        (2, "What-if: size and timing of the campaign (1)"), (3, "Staff reviews and sends the request (2)"),
        (5, "Bookings come in with names (2)"), (6, "Forecast back above warning level, request closes")]
for c, t in rowC:
    box(c, RC, t, PLAIN)
for c in (0, 1, 2, 5):
    link(c, RC)
A(BX + 3 * BP + BW + 8, RC + BH / 2, 2 * BP - BW - 16, 0)
A(BX + 3 * BP + BW / 2, RC - 8, 0, -(RC - RB - BH - 16), RED[0])
T(BX + 3 * BP + BW / 2 + 12, RC - 90, "shows up as a need card", 18, RED[0])
A(BX + 5 * BP + BW / 2, RB + BH + 8, 0, RC - RB - BH - 16, RED[0])
T(BX + 5 * BP + BW / 2 + 12, RC - 90, "booking: the centre now sees a name", 18, RED[0])
T(BX + 7 * BP, RC + 10, "The loop: the next lab test after a donation lands in Results again, and the person "
                        "watches their own iron recover.", 20, ORANGE, w=420)

# ================================================================ section 4: how it decides
DY = RC + 300
T(0, DY, "How the app decides who to ask", 56)
ins = ["Stock, donations and usage per\nblood type, 180 days",
       "People who agreed: blood type,\npostcode area, last donation",
       "How people answered before\n(booked, seen, not this time)"]
for k, t in enumerate(ins):
    R(0, DY + 120 + k * 130, 400, 100, WHITE, 2)
    T(16, DY + 144 + k * 130, t, 20)
    A(408, DY + 170 + k * 130, 150, (1 - k) * 110)
R(570, DY + 210, 330, 170, VIOLET, 2)
T(570, DY + 240, "Forecast (ridge regression,\n14 days ahead, runs daily)\nand donor matcher", 22, INK, w=330,
  align="center")
T(980, DY + 110, "Fixed rules around the model", 26)
rules = ["1. Nobody is asked unless they switched it on. One tap switches it off, per place or for everything.",
         "2. The model only recommends. A staff member reviews each request and presses send.",
         "3. A place sees counts. It sees a name only when that person books a slot.",
         "4. At most 2 requests per person per month. Closest people and people who gave there before come first.",
         "5. The app never says a person may give blood. The donor centre decides at the visit.",
         "6. Lab values are explained against the range printed by the lab. No diagnosis, no cause. Urgent "
         "values wait until the doctor has phoned."]
yy = DY + 160
for r in rules:
    yy = T(980, yy, r, 21, INK, w=900) + 10
A(1900, DY + 295, 110, 0)
R(2020, DY + 240, 250, 110, PLAIN, 2)
T(2020, DY + 266, "Recommendation\non screen 1", 22, INK, w=250, align="center")
A(2278, DY + 295, 130, 0)
T(2282, DY + 250, "staff sends", 17)
R(2416, DY + 240, 250, 110, RED, 2)
T(2416, DY + 266, "Need card in\nthe person's app", 22, INK, w=250, align="center")

RX = 2860
T(RX, DY + 100, "Four ways this goes wrong, and the guard for each", 30)
risks = ["1. A place learns something about a person's health. A low ferritin is the patient's business, not the "
         "donor centre's. Guard: rules 3 and 6, and the lab passes on the blood type only.",
         "2. Request fatigue: O- donors get asked every week and switch everything off. Guard: rule 4, and a "
         "request closes itself as soon as stock recovers.",
         "3. False comfort or false alarm from the AI text. Guard: rule 6, every answer links the report line it "
         "came from, and a summary for the doctor is one tap away.",
         "4. A wrong forecast asks 2,400 people for blood nobody needs. Guard: rule 2, the what-if sliders, and the backtest error shown on the dashboard (10.0% today)."]
yy = DY + 152
for r in risks:
    yy = T(RX, yy, r, 22, INK, w=2000) + 14
T(RX, yy + 30, "One thing to decide: where the lab values come from", 30)
T(RX, yy + 84, "The clean version needs the lab to publish results (screen 3). For a first version without a lab "
               "on board, the person could photograph their own report and confirm the values the app read. I "
               "think the lab code is the better spine, because a typed or photographed value can be wrong and "
               "everything after it depends on that number.", 22, INK, w=2000)

# ---------------------------------------------------------------- write
texts = [e for e in els if e["type"] == "text"]
scene = {"type": "excalidraw", "version": 2, "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
         "elements": els,
         "appState": {"theme": "light", "viewBackgroundColor": "#ffffff", "gridSize": 20, "gridStep": 5,
                      "gridModeEnabled": False, "currentItemFontFamily": 5},
         "files": {}}
md = ["---", "", "excalidraw-plugin: parsed", "tags: [excalidraw]", "", "---",
      "==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing "
      "data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin "
      "settings under 'Saving'", "", "", "# Excalidraw Data", "", "## Text Elements"]
for t in texts:
    md.append(f"{t['text']} ^{t['id']}")
    md.append("")
md += ["%%", "## Drawing", "```json", json.dumps(scene, ensure_ascii=False, indent=1), "```", "%%", ""]
out = sys.argv[1]
open(out, "w", encoding="utf-8", newline="\n").write("\n".join(md))
xs = [e["x"] for e in els]
print(len(els), "elements,", len(texts), "texts; bbox",
      round(min(xs)), round(min(e["y"] for e in els)), round(max(e["x"] + e["width"] for e in els)),
      round(max(e["y"] + e["height"] for e in els)))
