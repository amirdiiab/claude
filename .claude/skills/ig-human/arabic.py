"""
arabic.py - Arabic support shared by the pack's scripts.

The original heuristics read English only: Arabic words did not count as words,
Arabic numerals and currencies were not "concrete", and the humanizer deleted
the direction marks that keep "IX" or "ChatGPT" in the right place inside an
Arabic sentence. Every script that reads text imports this file, so the fixes
live in one place. Identical copies sit in ig-human, ig-reel, ig-caption and
ig-viral so each folder still runs when it is copied on its own.

Covers Modern Standard Arabic plus the Egyptian and Gulf words that show up in
spoken Reels. Lexicons are plain sets: add your own words, they are normalised
on load, so spelling variants (أ/إ/ا, ى/ي, ة/ه) and diacritics do not matter.
"""

import re

LETTERS = "ء-غف-يٱ-ۓۺ-ۼ"
MARKS = "ً-ٰٟـ"              # diacritics and tatweel
DIGITS = "٠-٩۰-۹"
NUM_PUNCT = "٪٫٬"                  # ٪ ٫ ٬

AR_CHAR_RE = re.compile(f"[{LETTERS}]")
LATIN_CHAR_RE = re.compile(r"[A-Za-z]")
# One word, in either script. "$18,000" and "٤٠٬٠٠٠" stay whole.
WORD_RE = re.compile(rf"[A-Za-z0-9$%'’\-{LETTERS}{MARKS}{DIGITS}{NUM_PUNCT}]+")
# Sentence ends, including the Arabic question mark.
SENT_END = ".!?؟"
SENT_RE = re.compile(rf"[^{SENT_END}\n]+[{SENT_END}]*")
# A Latin brand or acronym inside Arabic text (ChatGPT, ERP, n8n, IX) is a name.
LATIN_NAME_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]+\b")

# Characters Arabic text legitimately carries. Bidi marks keep mixed
# Arabic/Latin lines in order; ZWNJ is a real orthographic character.
KEEP_IN_ARABIC = {0x200C, 0x200E, 0x200F, 0x061C}
ZWJ = 0x200D

_PREFIXES = ("وبال", "وال", "بال", "فال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")
# Egyptian/Gulf present and future markers glued to verbs: بتخسر، هيوفر.
_VERB_PREFIXES = ("بت", "بي", "بن", "هت", "هي", "هن", "حت", "حي", "حن")


def is_arabic(text, threshold=0.3):
    """True when Arabic letters are at least `threshold` of all letters."""
    ar = len(AR_CHAR_RE.findall(text))
    lat = len(LATIN_CHAR_RE.findall(text))
    return ar > 0 and ar / (ar + lat) >= threshold


def normalize(token):
    """Strip diacritics and fold the spelling variants people mix freely."""
    t = re.sub(f"[{MARKS}]", "", token)
    t = re.sub("[أإآٱ]", "ا", t)
    return t.replace("ى", "ي").replace("ة", "ه").lower()


def variants(token):
    """The token plus the stem left after common attached prefixes."""
    t = normalize(token)
    out = {t}
    for p in _PREFIXES:
        if t.startswith(p) and len(t) - len(p) >= 2:
            out.add(t[len(p):])
    for p in _VERB_PREFIXES:
        if t.startswith(p) and len(t) - len(p) >= 3:
            out.add(t[len(p):])
    return out


def in_set(token, lexicon):
    return not variants(token).isdisjoint(lexicon)


def _norm_set(words):
    return {normalize(w) for w in words}


SPOKEN_NUMBERS = _norm_set("""
صفر اتنين اثنين اثنان تلاته ثلاثه تلات ثلاث اربعه اربع خمسه خمس سته ست سبعه سبع
تمانيه ثمانيه تمان ثمان تسعه تسع عشره عشر عشرين عشرون تلاتين ثلاثين اربعين خمسين
ستين سبعين تمانين ثمانين تسعين ميه مئه مية ميت الف الاف آلاف مليون ملايين مليار
نص نصف ربع ضعف اضعاف دسته
""".split())

MONEY = _norm_set("""
درهم دراهم ريال ريالات جنيه جنيهات دولار دولارات يورو دينار فلوس مكسب مكاسب ارباح
ربح خساره خسائر ايراد ايرادات مبيعات راتب مرتب ايجار تكلفه تكاليف ميزانيه سعر
""".split())

UNITS = _norm_set("""
ساعه ساعات دقيقه دقايق دقائق ثانيه ثواني يوم ايام اسبوع اسابيع شهر شهور اشهر سنه
سنين سنوات عميل عملاء موظف موظفين طلب طلبات
""".split())

STAKES = _norm_set("""
خسرت خسر خسرنا خساره ضيعت ضيع ضاع ضايع غلط غلطه اخطاء خطا اوعي اوعى متعملش
ماتعملش لا مش لم لن ابدا عمري محدش ماحدش مفيش مافيش بطل وقف توقف فشل فشلت
فاشل اترفدت طردت اتطردت مسحت حذفت استبدلت بدل وفرت وفر وفرنا ببلاش مجانا مجاني
دفعت سر اسرار الحقيقه حقيقه مخفي سرقه نصب كدب كذب اسوا مشكله مشاكل خطر تحذير
ندمت ندم لازم مفروض قبل لحد غير الا بس فقط بدون لسه لسا اول مقابل ضد فعلا
خلاص كفايه اتعلمت اكتشفت خسر يخسر ضيع يضيع يوفر
""".split())

WEAK_OPENERS = [normalize(p) for p in [
    "السلام عليكم", "اهلا", "أهلا", "مرحبا", "هاي", "هلا", "يا جماعة", "يا شباب",
    "النهارده", "النهاردة", "اليوم حابب", "اليوم حنتكلم", "في الفيديو ده",
    "في هذا الفيديو", "في الريل ده", "طيب", "بص", "شوف يا", "خلينا", "تعالوا",
    "انا عايز", "حبيت", "حابب", "هل تعرف", "هل تعلم", "تعرف ان", "عارف ان", "زي ما",
    "في ناس", "يعني", "بصراحة", "فيه حاجة", "هناك", "كما تعلمون", "كلنا عارفين",
]]

IMPERATIVES = _norm_set("""
وقف بطل اوعي اوعى انسخ احفظ جرب شوف اقرا اقرأ ابني اعمل اكتب ابعت خد ابدا ابدأ
استخدم امسح افتح سيب ركز اسال اسأل متعملش
""".split())

YOU = _norm_set("""
انت انتي انتو انتم حضرتك عندك بتاعك بتاعتك لك ليك عليك
""".split())
# Second person is mostly a suffix (شركتك, وقتك). These end in ك and are not.
_NOT_YOU = _norm_set("ذلك لذلك كذلك هناك تلك ملك بنك شباك شبابيك سمك ممكن مبارك مشترك".split())

ME = _norm_set("""
انا احنا نحن عندي عندنا بتاعي بتاعنا شركتي شغلي عملائي خسرت وفرت ضيعت عملت بنيت
جربت طردت مسحت دفعت كسبت بدات بدأت اكتشفت قررت ندمت اتعلمت نجحت فشلت
""".split())

# Colloquial markers. Spoken Arabic uses them; a model writing "Arabic" defaults
# to stiff MSA without them. On a platform where you say the words out loud,
# their absence is the closest thing Arabic has to "no contractions".
COLLOQUIAL = _norm_set("""
مش ده دي دا كده كدا عشان علشان ازاي ازي ايه بتاع بتاعت اللي فين امتى ليه احنا
انتو وش ليش شلون زين واجد يبغي ابغي ابغى بس لسه خلاص يعني هيك كتير اوي قوي
مفيش مافيش عايز عاوز عايزه هنا هناك برضه برده
""".split())

PROPER = _norm_set("""
دبي الامارات ابوظبي السعوديه الرياض جده قطر الدوحه الكويت البحرين عمان مصر القاهره
الخليج جوجل ميتا انستجرام انستغرام فيسبوك لينكدان لينكد واتساب تيك يوتيوب
""".split())

STOPWORDS = _norm_set("""
في من على الى إلى عن مع ده دي هذا هذه ان أن انا انت هو هي احنا اللي التي الذي و او
ما لا مش بس كل كان يكون عشان علشان
""".split())

# A figure with an Arabic unit or currency after it.
NUMBER_UNIT_RE = re.compile(
    rf"[\d{DIGITS}][\d{DIGITS},{NUM_PUNCT}.]*\s?(?:[٪%]|"
    r"(?:ال)?(?:درهم|دراهم|ريال|جنيه|دولار|يورو|ساع[ةه]|ساعات|دقيق[ةه]|يوم|ايام|أيام|"
    r"اسبوع|أسبوع|شهر|سن[ةه]|سنين|سنوات|الف|ألف|آلاف|مليون|عميل|موظف))?")
PRICE_RE = re.compile(
    rf"[\d{DIGITS}][\d{DIGITS},{NUM_PUNCT}.]*\s?(?:الف\s|ألف\s|مليون\s)?(?:درهم|ريال|جنيه|دولار|يورو)"
    r"|(?:درهم|ريال|جنيه|دولار)\s?[\d" + DIGITS + "]")


def is_you(token):
    t = normalize(token)
    if in_set(token, YOU):
        return True
    return (len(t) >= 4 and (t.endswith("ك") or t.endswith("كم"))
            and t not in _NOT_YOU and not t.startswith("ك"))


DEALBREAKERS = [
    (re.compile(r"^\s*(?:متقلبش|ما\s?تقلبش|استنى\s?متقلبش|وقف\s?(?:سكرول|التقليب))"),
     "يبدأ بـ \"متقلبش\". طلب الانتباه بيثبت إنك لسه مكسبتهوش."),
    (re.compile(r"(?:في|ف)\s?(?:الفيديو|الريل|المقطع)\s?(?:ده|دا|هذا)|هوريك|هوريكم|هشرحلك|هشرحلكم|سأريكم|سأشرح"),
     "مقدمة فيديو. احذفها وابدأ بالنتيجة."),
    (re.compile(r"^\s*(?:السلام\s?عليكم|أهلا|اهلا|مرحبا|هاي|هلا)"),
     "تحية. محدش فتح الفيد عشان حد يسلّم عليه."),
]

# Structural tells in Arabic drafts. Reported, never auto-rewritten.
STRUCTURES = [
    {"id": "ar-not-just", "regex": r"(?:ليس|ليست|مش)\s+(?:فقط|مجرد|بس)\s+[^.!?؟\n]{2,60}\s*[،,]?\s*(?:بل|لا|ده|دي)\b",
     "name": "\"ليس مجرد X، بل Y\"", "fix": "قول الحاجة اللي تقصدها. احذف نص المقدمة."},
    {"id": "ar-not-only", "regex": r"ليس\s+فقط[^.!?؟\n]{2,80}بل\s+(?:أيضا|ايضا|أيضًا)",
     "name": "\"ليس فقط X بل أيضًا Y\"", "fix": "قسّمها لجملتين أو احذف الأضعف."},
    {"id": "ar-isnt-about", "regex": r"(?:الموضوع|الأمر|الامر)\s+(?:مش|ليس)\s+(?:عن|في)\s+[^.!?؟\n]{2,60}[.!؟]\s*(?:الموضوع|الأمر|الامر)\s+(?:عن|في)",
     "name": "\"الموضوع مش عن X. الموضوع عن Y\"", "fix": "ابدأ بـ Y. الانقلاب نفسه علامة."},
    {"id": "ar-whether", "regex": r"سواء\s+(?:كنت|كنتِ|كان)\s+[^.!?؟\n]{2,60}\s+(?:أو|او)\s+",
     "name": "\"سواء كنت X أو Y\"", "fix": "اختار جمهور واحد وكلّمه."},
    {"id": "ar-world-of", "regex": r"في\s+(?:عالم|عصر|ظل)\s+(?:اليوم|يتسارع|متسارع|التطور|التحول|الذكاء)",
     "name": "\"في عالم اليوم المتسارع\"", "fix": "احذف الافتتاحية وابدأ بالمعلومة."},
    {"id": "ar-ever-wondered", "regex": r"هل\s+(?:سبق|تساءلت|فكرت\s+يوما|تخيلت)",
     "name": "\"هل سبق لك أن تساءلت\"", "fix": "قول الإجابة مباشرة بدل السؤال."},
]
