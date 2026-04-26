# ================================================
#   CBT Assistant — Flask API
#   صاحبك بيستدعي الـ endpoints دي من Flutter
# ================================================

from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# ── تحميل المحتوى ──────────────────────────────
with open("content.json", "r", encoding="utf-8") as f:
    CONTENT = json.load(f)

# ── ماب الحالات ────────────────────────────────
CONDITION_CATEGORIES = {
    "anxiety":    ["anxiety"],
    "depression": ["depression"],
    "stress":     ["stress", "overthinking"],
    "mixed":      ["psychoeducation", "self-esteem"],
}

# ── تحديد الحالة من الـ scores ─────────────────
def determine_condition(scores):
    # scores مثال: {"anxiety": 4, "depression": 1, "stress": 2, "mixed": 1}
    main = {k: v for k, v in scores.items() if k != "mixed"}
    primary = max(main, key=main.get)
    max_score = main[primary]

    if max_score == 0:
        return "mixed", "mild"
    elif max_score <= 2:
        severity = "mild"
    elif max_score <= 4:
        severity = "moderate"
    else:
        severity = "severe"

    return primary, severity

# ── منطق التوصية ───────────────────────────────
def get_recommendations(condition, severity):
    cats = CONDITION_CATEGORIES.get(condition, CONDITION_CATEGORIES["mixed"])

    if severity in ["moderate", "severe"]:
        cats = list(cats) + ["psychoeducation", "self-esteem"]

    matched = [item for item in CONTENT if item.get("category") in cats]

    if not matched:
        matched = [item for item in CONTENT if item.get("category") == "psychoeducation"]

    matched.sort(key=lambda x: (
        {"beginner": 0, "intermediate": 1, "advanced": 2}.get(x.get("difficulty", "beginner"), 1),
        x.get("estimated_time", 99)
    ))

    # بنرجع بس اللي Flutter محتاجه
    result = []
    for item in matched[:4]:
        result.append({
            "id":          item.get("id"),
            "type":        item.get("type"),
            "title_ar":    item["title"].get("ar", ""),
            "title_en":    item["title"].get("en", ""),
            "description": item["description"].get("ar", ""),
            "duration":    item.get("estimated_time", 0),
            "url":         item.get("content_data", {}).get("url", ""),
            "difficulty":  item.get("difficulty", "beginner"),
        })
    return result


# ════════════════════════════════════════════════
#   ENDPOINTS
# ════════════════════════════════════════════════

# ── 1. الأسئلة ─────────────────────────────────
# Flutter بيجيب الأسئلة منه ويعرضها للمستخدم
@app.route("/questions", methods=["GET"])
def get_questions():
    questions = [
        {"id": 1, "text_ar": "خلال الأسبوع الفات، حسيت بقلق أو خوف زيادة عن اللازم؟",   "category": "anxiety"},
        {"id": 2, "text_ar": "بتلاقي صعوبة إنك توقف التفكير أو تفضل قلقان على حاجات؟",   "category": "anxiety"},
        {"id": 3, "text_ar": "حسيت بحزن أو إحباط أو إحساس إن مفيش فايدة؟",              "category": "depression"},
        {"id": 4, "text_ar": "قل اهتمامك بحاجات كنت بتحبها أو بتستمتع بيها؟",           "category": "depression"},
        {"id": 5, "text_ar": "حسيت بضغط أو إجهاد من مسؤوليات الحياة اليومية؟",          "category": "stress"},
        {"id": 6, "text_ar": "التفكير الزيادة بيأثر على نومك أو تركيزك؟",               "category": "stress"},
        {"id": 7, "text_ar": "نومك اتأثر — صعوبة في النوم أو صحيان كتير؟",             "category": "mixed"},
    ]
    options = [
        {"value": 0, "label_ar": "خالص"},
        {"value": 1, "label_ar": "أحياناً"},
        {"value": 2, "label_ar": "كتير"},
        {"value": 3, "label_ar": "طول الوقت"},
    ]
    return jsonify({"questions": questions, "options": options})


# ── 2. التوصية ─────────────────────────────────
# Flutter بيبعت إجابات المستخدم ويستقبل التوصيات
#
# Request body مثال:
# {
#   "answers": [
#     {"question_id": 1, "category": "anxiety",    "value": 3},
#     {"question_id": 2, "category": "anxiety",    "value": 2},
#     {"question_id": 3, "category": "depression", "value": 1},
#     {"question_id": 4, "category": "depression", "value": 0},
#     {"question_id": 5, "category": "stress",     "value": 2},
#     {"question_id": 6, "category": "stress",     "value": 1},
#     {"question_id": 7, "category": "mixed",      "value": 1}
#   ]
# }
@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()

    if not data or "answers" not in data:
        return jsonify({"error": "ابعت answers في الـ request body"}), 400

    # حساب الـ scores من الإجابات
    scores = {"anxiety": 0, "depression": 0, "stress": 0, "mixed": 0}
    for answer in data["answers"]:
        cat = answer.get("category")
        val = answer.get("value", 0)
        if cat in scores:
            scores[cat] += val

    condition, severity = determine_condition(scores)
    recommendations = get_recommendations(condition, severity)

    # ترجمة الحالة للعربي للعرض
    condition_ar = {
        "anxiety":    "قلق",
        "depression": "اكتئاب",
        "stress":     "توتر",
        "mixed":      "مختلط",
    }.get(condition, condition)

    severity_ar = {
        "mild":     "خفيف",
        "moderate": "متوسط",
        "severe":   "يحتاج اهتمام",
    }.get(severity, severity)

    return jsonify({
        "condition":        condition,
        "condition_ar":     condition_ar,
        "severity":         severity,
        "severity_ar":      severity_ar,
        "recommendations":  recommendations,
        "show_warning":     severity == "severe",
    })


# ── 3. الـ Chatbot ──────────────────────────────
# Flutter بيبعت رسالة المستخدم + الحالة ويستقبل رد الـ AI
#
# Request body مثال:
# {
#   "message": "أنا حاسس بقلق كتير",
#   "condition": "anxiety",
#   "history": [
#     {"role": "user",      "content": "مرحبا"},
#     {"role": "assistant", "content": "أهلاً، كيف أقدر أساعدك؟"}
#   ]
# }
@app.route("/chat", methods=["POST"])
def chat():
    try:
        import google.generativeai as genai
    except ImportError:
        return jsonify({"error": "نصّب google-generativeai أولاً"}), 500

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "ابعت message في الـ request body"}), 400

    user_message = data["message"]
    condition    = data.get("condition", "mixed")
    history      = data.get("history", [])

    condition_ar = {
        "anxiety":    "قلق",
        "depression": "اكتئاب",
        "stress":     "توتر",
        "mixed":      "مختلط",
    }.get(condition, "مختلط")

    SYSTEM_PROMPT = f"""
أنت معالج نفسي متخصص في العلاج المعرفي السلوكي (CBT).
المستخدم يعاني من: {condition_ar}.

أسلوبك:
- متعاطف وداعم دائماً
- تتكلم بالعربية العامية المصرية
- تستخدم تقنيات CBT مثل تسجيل الأفكار والتنفس والتفعيل السلوكي
- تسأل أسئلة مفتوحة لفهم الموقف
- ردودك قصيرة ومركزة (3-4 جمل بحد أقصى)
- لا تشخّص ولا توصي بأدوية أبداً
- لو الحالة خطيرة، وجّه للمختص بهدوء
"""

    api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )

    # تحويل الـ history لصيغة Gemini
    gemini_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat_session = model.start_chat(history=gemini_history)
    response = chat_session.send_message(user_message)

    return jsonify({"reply": response.text})


# ── Health check ────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "CBT API شغال"})


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
