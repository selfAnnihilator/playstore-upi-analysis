"""Shared constants: apps to scrape, file paths and the complaint-theme taxonomy."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "reviews.db"
FIG_DIR = ROOT / "reports" / "figures"

APPS = {
    "PhonePe": "com.phonepe.app",
    "Google Pay": "com.google.android.apps.nbu.paisa.user",
    "Paytm": "net.one97.paytm",
}

REVIEWS_PER_APP = 30_000
BATCH_SIZE = 200

# Keyword taxonomy. Each theme is a list of regex fragments matched case-insensitively
# on word boundaries. A review can carry several themes. Kept deliberately simple so
# every tag can be explained by pointing at the word that triggered it.
THEMES: dict[str, list[str]] = {
    "Failed / pending payment": [
        r"fail(ed|ing|s|ure)?", r"pending", r"stuck", r"declin(ed|e)", r"unsuccessful",
        r"not (going|getting) through", r"transaction (error|issue|problem)",
        r"payment (error|issue|problem)",
    ],
    "Money debited / refund": [
        r"debit(ed)?", r"deducted", r"refund(ed|s)?", r"money (lost|gone|not (received|credited|returned))",
        r"not (been )?(received|credited)", r"credited back", r"amount (cut|deducted)",
        r"money (is )?cutting", r"balance remaining same", r"get my money back",
        r"paise? (nahi|nhi) (aaye?|aya|mile?)", r"paisa (kat|cut)", r"kat (gaya|gya)",
    ],
    "KYC / account blocked": [
        r"kyc", r"(un)?blocked", r"block(ing)? (my )?account", r"suspend(ed)?", r"frozen", r"freez(e|ed)",
        r"account (closed|deactivated|restricted|locked)", r"verification",
    ],
    "Cashback / rewards": [
        r"cash ?back", r"rewards?", r"scratch ?cards?", r"coupons?", r"offers?", r"points",
    ],
    "App crash / slow / bugs": [
        r"crash(es|ed|ing)?", r"hang(s|ing)?", r"slow", r"lag(s|gy|ging)?", r"bugs?", r"glitch(es)?",
        r"not (opening|loading|working)", r"won'?t open", r"freezes", r"stopped working",
        r"(didn'?t|doesn'?t|does not|not|nor) (open|work)(ing)?", r"open (hi )?(nahi|nhi|nahin)",
        r"(chal|kaam) (nahi|nhi|nahin)", r"nahin? chal",
        r"clos(es|ing) (itself|automatically)", r"(unable|not able|can'?t|cannot)( to)? (open|use|send|check|pay)",
        r"disappearing", r"band (ho|kar)", r"khul (nahi|nhi)",
    ],
    "Customer support": [
        r"customer (care|support|service)", r"support team", r"helpline", r"no (response|reply)",
        r"complain(t|ts|ed)?", r"ticket", r"chat ?bot", r"bot replies", r"executive", r"support",
        r"customer care", r"not reply(ing)?",
    ],
    "Login / OTP / security": [
        r"otp", r"log ?in", r"sign ?in", r"logged out", r"pin", r"password", r"hack(ed)?",
        r"security alert", r"accessibility", r"rooted", r"device environment",
    ],
    "Scam / trust": [
        r"fraud(s|ulent)?", r"scam(s|mer|mers|med)?", r"cheat(s|ers?|ing|ed)?", r"loot(s|ing|ers?)?",
        r"steal(s|ing)?", r"not safe", r"unsafe", r"chor", r"thie(f|ves)",
    ],
    "Charges / fees": [
        r"charg(e|es|ed|ing)", r"fees?", r"platform fee", r"convenience fee", r"gst", r"surcharge",
        r"extra (money|amount)",
    ],
    "Autopay / subscriptions": [
        r"auto ?pay", r"mandates?", r"subscriptions?", r"auto ?debit(ed)?", r"auto ?deduct(ed|ion)?",
    ],
    "Loans / credit cards": [
        r"loans?", r"credit (line|card|score)", r"emi", r"cibil",
    ],
    "Bank linking / server": [
        r"bank (server|link(ing)?|account (not )?link)", r"server (down|issue|error|problem)", r"npci",
        r"link(ing)? (my )?bank", r"add (my )?bank", r"upi id", r"upi lite", r"rupay",
    ],
    "Ads / spam / notifications": [
        r"ads?", r"advertis(e|ement|ements|ing)", r"spam", r"notifications?", r"promotion(s|al)?",
        r"pop ?ups?", r"rate us",
    ],
    "Praise": [
        r"good", r"great", r"excellent", r"awesome", r"nice", r"best", r"love", r"easy", r"smooth",
        r"fast", r"helpful", r"super", r"amazing",
    ],
}
COMPLAINT_THEMES = [t for t in THEMES if t != "Praise"]
