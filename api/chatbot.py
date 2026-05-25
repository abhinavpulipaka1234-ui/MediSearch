import re
import math

# Severe keywords that should map to HIGH/EMERGENCY severity
EMERGENCY_KEYWORDS = {
    "chest pain", "difficulty breathing", "loss of consciousness",
    "crushing chest", "can't breathe", "seizure", "stroke",
    "heart attack", "collapse", "unresponsive", "cardiac arrest",
    "severe bleeding", "anaphylaxis", "choking", "coughing blood",
    "sudden weakness", "facial drooping", "slurred speech"
}

HIGH_SEVERITY_KEYWORDS = {
    "sharp pain", "intense pain", "very severe", "extreme pain",
    "blacking out", "blood in", "high fever", "severe headache",
    "fainting", "vomiting blood", "can't walk", "can't see",
    "severe swelling", "severe rash"
}

# Direct keyword diagnosis fallback (runs BEFORE BM25)
KEYWORD_MAP = {
    ("fever", "cough", "cold", "runny nose", "body ache", "fatigue", "chills"): ("Influenza / Viral Infection", "Medium"),
    ("chest pain", "shortness of breath", "difficulty breathing"): ("Cardiac / Respiratory Emergency", "Emergency"),
    ("headache", "nausea", "vomiting", "sensitivity to light"): ("Migraine", "Medium"),
    ("sore throat", "tonsil", "throat pain", "difficulty swallowing"): ("Tonsillitis / Pharyngitis", "Low"),
    ("stomach pain", "abdominal pain", "diarrhea", "loose stools"): ("Gastroenteritis", "Low"),
    ("rash", "itching", "hives", "skin irritation"): ("Allergic Reaction / Dermatitis", "Low"),
    ("back pain", "spine", "lower back"): ("Musculoskeletal Back Pain", "Low"),
    ("anxiety", "panic", "stress", "racing heart"): ("Anxiety / Panic Disorder", "Low"),
    ("urination", "burning urine", "frequent urination"): ("Urinary Tract Infection", "Medium"),
    ("eye pain", "red eye", "blurry vision"): ("Conjunctivitis / Eye Infection", "Low"),
}


class Message:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class IntakeBot:
    def __init__(self, ranker):
        self.sessions = {}
        self.ranker = ranker

        # State machine phases
        self.phases = [
            ("symptom_name", "What is the primary symptom you are experiencing?"),
            ("duration", "How long have you been experiencing this?"),
            ("severity", "On a scale of 1-10, how severe is your pain/discomfort?"),
            ("pain_location", "Where exactly is the pain or discomfort located?"),
            ("additional_symptoms", "Are you experiencing any other symptoms? (e.g., fever, nausea, dizziness, fatigue)"),
            ("existing_conditions", "Do you have any existing medical conditions we should know about?")
        ]

    def _init_session(self, session_id):
        self.sessions[session_id] = {
            "phase_idx": 0,
            "data": {},
            "history": []
        }

    def process_turn(self, session_id, user_message):
        if session_id not in self.sessions:
            self._init_session(session_id)

        session = self.sessions[session_id]

        # Save user response to current phase if not first turn
        if user_message:
            session["history"].append({"role": "user", "content": user_message})
            curr_phase_key = self.phases[session["phase_idx"]][0]
            session["data"][curr_phase_key] = user_message
            session["phase_idx"] += 1

        # Check if complete
        if session["phase_idx"] >= len(self.phases):
            reply = "Thank you. Your assessment is complete. Generating your triage report now..."
            session["history"].append({"role": "bot", "content": reply})
            return {"reply": reply, "complete": True}

        # Emit next question
        next_q = self.phases[session["phase_idx"]][1]
        session["history"].append({"role": "bot", "content": next_q})

        return {"reply": next_q, "complete": False}

    def _compute_severity(self, pain_score, symptom_text):
        """
        Cross-check severity from both pain score and keywords, with strict caps:
        - Pain 1-3/10  -> Low only
        - Pain 4-6/10  -> at most Medium
        - Pain 7-10/10 -> may be High/Emergency ONLY when serious symptoms are present
        """
        text_lower = symptom_text.lower()

        # Check for emergency keywords
        has_emergency = any(kw in text_lower for kw in EMERGENCY_KEYWORDS)
        has_high = any(kw in text_lower for kw in HIGH_SEVERITY_KEYWORDS)

        # Base severity signal from content
        if has_emergency:
            base = "Emergency"
        elif has_high:
            base = "High"
        else:
            base = "Medium"

        # Apply pain-based caps
        if pain_score <= 3:
            return "Low"
        if pain_score <= 6:
            return "Low" if base == "Low" else "Medium"
        # 7-10
        return base

    def _compute_confidence(self, results):
        """
        Compute real confidence from BM25 scores.
        Uses the score distribution to determine how confident the system is.
        """
        if not results:
            return 0.0

        top_score = results[0]["score"]
        if len(results) < 2:
            # Only one match — use raw score normalization
            return min(0.95, max(0.1, top_score / 10.0))

        second_score = results[1]["score"]

        # Confidence is based on:
        # 1) How high the absolute top score is
        # 2) How much separation there is between #1 and #2
        raw_confidence = min(1.0, top_score / 8.0)

        # If top result is much better than second, more confident
        if second_score > 0:
            separation = (top_score - second_score) / top_score
        else:
            separation = 1.0

        confidence = raw_confidence * (0.6 + 0.4 * separation)
        return round(min(0.98, max(0.05, confidence)), 4)

    def finalize_triage(self, session_id):
        session = self.sessions.get(session_id, {})
        data = session.get("data", {})

        # Build the query from primary symptoms + additional + location
        symptom_parts = [
            data.get("symptom_name", ""),
            data.get("additional_symptoms", ""),
            data.get("pain_location", ""),
        ]
        query = " ".join(part for part in symptom_parts if part and part.lower() not in ("no", "none", "n/a", "nothing"))
        query_lower = query.lower().strip()

        # Parse severity score
        sc_num = data.get("severity", "5")
        try:
            val = int(re.search(r'\d+', sc_num).group())
            val = max(1, min(10, val))
        except:
            val = 5

        # Insufficient info ONLY if fewer than 3 words
        word_count = len([w for w in re.split(r"\s+", re.sub(r"[^a-z0-9\s]", " ", query_lower)) if w])
        if word_count < 3:
            est_severity = self._compute_severity(val, query)
            return {
                "draft_condition": "Insufficient Information",
                "confidence": 0.0,
                "estimated_severity": est_severity,
                "extracted_symptoms": query,
                "similar_cases": [],
                "top_conditions": [],
                "pain_score": val,
                "low_confidence": True,
                "low_confidence_message": "Please describe your symptoms in more detail so we can assess them accurately.",
            }

        # Keyword fallback BEFORE BM25
        matched = None
        for keywords, (condition, suggested_sev) in KEYWORD_MAP.items():
            if any(kw in query_lower for kw in keywords):
                matched = (condition, suggested_sev, keywords)
                break

        if matched:
            condition, suggested_sev, keywords = matched
            # severity must still respect pain caps / emergency keyword checks
            est_severity = self._compute_severity(val, query)
            # If suggested severity is lower than computed, keep the safer (higher) one but still capped by pain logic.
            # Pain caps are already enforced in _compute_severity.
            confidence = 0.85
            return {
                "draft_condition": condition,
                "confidence": confidence,
                "estimated_severity": est_severity,
                "extracted_symptoms": query,
                "similar_cases": [],
                "top_conditions": [
                    {"condition": condition, "score": None, "match_pct": 100.0, "matched_keywords": list(keywords)}
                ],
                "pain_score": val,
                "low_confidence": False,
                "low_confidence_message": None,
            }

        # Call BM25 (fallback)
        results = self.ranker.score_query(query) if self.ranker else []

        # Compute real confidence
        confidence = self._compute_confidence(results)

        # Apply confidence threshold — below 45%: ask patient to describe in more detail
        if (not results) or confidence < 0.45:
            draft_cond = "Insufficient Information"
            est_severity = self._compute_severity(val, query)
            top_conditions = []
            top_cases = []
            low_confidence = True
        else:
            # Get top 3 distinct conditions with their scores
            seen_conditions = set()
            top_conditions = []
            for r in results:
                cond = r["condition_label"]
                if cond not in seen_conditions:
                    seen_conditions.add(cond)
                    top_conditions.append({
                        "condition": cond,
                        "score": round(r["score"], 3),
                        "match_pct": round(min(100, (r["score"] / max(results[0]["score"], 0.01)) * 100), 1)
                    })
                if len(top_conditions) >= 3:
                    break

            draft_cond = top_conditions[0]["condition"] if top_conditions else "Unknown"

            # Compute severity with cross-check
            est_severity = self._compute_severity(val, query)

            top_cases = [
                {"case_id": r["case_id"][:12], "similarity": round(r["score"], 3), "condition": r["condition_label"]}
                for r in results[:3]
            ]
            low_confidence = False

        return {
            "draft_condition": draft_cond,
            "confidence": confidence,
            "estimated_severity": est_severity,
            "extracted_symptoms": query,
            "similar_cases": top_cases,
            "top_conditions": top_conditions,
            "pain_score": val,
            "low_confidence": low_confidence,
            "low_confidence_message": "Please describe your symptoms in more detail so we can assess them accurately." if low_confidence else None
        }
