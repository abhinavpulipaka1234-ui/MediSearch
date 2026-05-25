import os
import json
import logging
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

from ir.bm25 import BM25Ranker
from api.chatbot import IntakeBot, Message
from api.notifications import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MediSearch")

# Config
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@localhost:5432/medisearch")
engine = create_engine(DB_URL)

app = FastAPI(title="MediSearch Core API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClientErrorSchema(BaseModel):
    message: str
    source: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None
    error: Optional[str] = None


@app.post("/client-error")
async def client_error(req: ClientErrorSchema):
    logger.error(f"!!! CLIENT-SIDE ERROR RECEIVED !!!\nMsg: {req.message}\nSrc: {req.source}:{req.lineno}:{req.colno}\nStack: {req.error}")
    return {"status": "logged"}

# Shared Memory Objects
try:
    ranker = BM25Ranker()
    bot = IntakeBot(ranker)
    logger.info("BM25 Engine & Chatbot Initialized successfully.")
except Exception as e:
    logger.error(f"Failed to boot IR Engine: {e}")
    ranker = None
    bot = None


def default_treatment_plan_json(condition_label: str) -> List[Dict[str, Any]]:
    label = condition_label or "your condition"
    return [
        {
            "day": 1,
            "tasks": [f"Begin treatment plan for {label}", "Rest, hydrate, take medications as directed"],
            "status": "active",
        },
        {
            "day": 2,
            "tasks": ["Continue prescribed care", "Monitor symptoms daily"],
            "status": "pending",
        },
        {
            "day": 3,
            "tasks": ["Symptom check-in", "Contact clinic if symptoms worsen"],
            "status": "pending",
        },
        {
            "day": 7,
            "tasks": ["Physician follow-up review"],
            "status": "pending",
        },
    ]


def ensure_treatment_plan_for_report(conn, triage_report_id: int, condition_label: str) -> None:
    existing = conn.execute(
        text("SELECT id FROM treatment_plans WHERE triage_report_id = :trid LIMIT 1"),
        {"trid": triage_report_id},
    ).fetchone()
    if existing:
        return
    plan = json.dumps(default_treatment_plan_json(condition_label))
    conn.execute(
        text("""
            INSERT INTO treatment_plans (triage_report_id, day_by_day_plan, status)
            VALUES (:trid, CAST(:plan AS jsonb), 'ACTIVE')
        """),
        {"trid": triage_report_id, "plan": plan},
    )


def row_parse_json_fields(r: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("relevant_historical_cases", "top_conditions"):
        if r.get(key):
            try:
                if isinstance(r[key], str):
                    r[key] = json.loads(r[key])
            except Exception:
                pass
    if r.get("timestamp"):
        r["timestamp"] = str(r["timestamp"])
    if r.get("created_at"):
        r["created_at"] = str(r["created_at"])
    if r.get("updated_at"):
        r["updated_at"] = str(r["updated_at"])
    if r.get("removed_at"):
        r["removed_at"] = str(r["removed_at"])
    return r


# ============================================ #
#  Chatbot Endpoints
# ============================================ #
class NextTurnRequest(BaseModel):
    session_id: str
    message: str = ""
    patient_id: str = ""
    finalize: bool = False


@app.post("/chatbot/next")
async def chatbot_next(req: NextTurnRequest):
    if not bot:
        raise HTTPException(500, "Chatbot offline (IR Engine failed)")
    response = bot.process_turn(req.session_id, req.message)
    return response


class IntakeFinalizeSchema(BaseModel):
    session_id: str
    patient_id: str = "anonymous"


@app.post("/chatbot/finalize")
async def chatbot_finalize(req: IntakeFinalizeSchema):
    if not bot:
        raise HTTPException(500, "Chatbot offline")

    report = bot.finalize_triage(req.session_id)
    _persist_triage_report(req.session_id, req.patient_id, report)
    return report


def _persist_triage_report(session_id: str, patient_id: str, report: dict, status: str = "PENDING", ai_diagnosis: bool = False) -> int:
    try:
        with engine.connect() as conn:
            case_id = f"case-{session_id}"
            conn.execute(
                text("""
                INSERT INTO cases (case_id, patient_id, patient_age, symptoms, condition_label, severity, timestamp)
                VALUES (:cid, :pid, 0, :symp, :cond, :sev, CURRENT_TIMESTAMP)
                ON CONFLICT (case_id) DO NOTHING
            """),
                {
                    "cid": case_id,
                    "pid": patient_id,
                    "symp": report["extracted_symptoms"],
                    "cond": report["draft_condition"],
                    "sev": report["estimated_severity"],
                },
            )

            top_conditions = report.get("top_conditions", [])
            diag_type = "AI" if ai_diagnosis else None

            result = conn.execute(
                text("""
                INSERT INTO triage_reports (case_id, confidence_score, relevant_historical_cases, top_conditions, status, diagnosis_type)
                VALUES (:cid, :conf, :cases, :top_cond, :stat, :dtype)
                RETURNING id
            """),
                {
                    "cid": case_id,
                    "conf": report["confidence"],
                    "cases": json.dumps(report.get("similar_cases", [])),
                    "top_cond": json.dumps(top_conditions),
                    "stat": status,
                    "dtype": diag_type
                },
            )
            report_id = result.scalar()
            conn.commit()
            return report_id
    except Exception as e:
        logger.error(f"Failed to persist triage draft: {e}")
        return -1


# ============================================ #
#  Patient / case listing
# ============================================ #
def _fetch_patient_cases(patient_id: str) -> List[dict]:
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT c.case_id, c.symptoms, c.condition_label, c.severity, c.timestamp,
                       tr.id as report_id, tr.status, tr.confidence_score,
                       tr.doctor_diagnosis, tr.doctor_severity, tr.doctor_notes,
                       tr.diagnosis_type, tr.reject_note,
                       tr.relevant_historical_cases, tr.top_conditions
                FROM cases c
                LEFT JOIN triage_reports tr ON tr.case_id = c.case_id
                WHERE c.patient_id = :pid
                ORDER BY c.timestamp DESC
            """),
            {"pid": patient_id},
        )
        rows = []
        for row in result:
            r = dict(row._mapping)
            rows.append(row_parse_json_fields(r))
        return rows


@app.get("/patient/{patient_id}/cases")
async def get_patient_cases(patient_id: str):
    try:
        return _fetch_patient_cases(patient_id)
    except Exception as e:
        raise HTTPException(500, str(e))


# ============================================ #
#  Symptom Logger
# ============================================ #
class SymptomLogCreate(BaseModel):
    patient_id: str
    symptoms: str
    severity: str = "Medium"
    pain_level: int = 5
    case_id: Optional[str] = None


def _create_symptom_log(log: SymptomLogCreate) -> dict:
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                INSERT INTO symptom_logs (patient_id, case_id, symptoms, severity, pain_level, timestamp)
                VALUES (:pid, :cid, :symp, :sev, :pain, CURRENT_TIMESTAMP)
                RETURNING id, timestamp
            """),
            {
                "pid": log.patient_id,
                "cid": log.case_id,
                "symp": log.symptoms,
                "sev": log.severity,
                "pain": log.pain_level,
            },
        )
        row = result.fetchone()
        conn.commit()
        return {"id": row[0], "timestamp": str(row[1]), "status": "logged"}


@app.post("/symptoms")
async def create_symptom_log(log: SymptomLogCreate):
    try:
        return _create_symptom_log(log)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/symptoms/{patient_id}")
async def get_symptom_logs(patient_id: str):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT id, patient_id, case_id, symptoms, severity, pain_level, timestamp
                FROM symptom_logs
                WHERE patient_id = :pid AND removed_at IS NULL
                ORDER BY timestamp DESC
            """),
                {"pid": patient_id},
            )
            rows = []
            for row in result:
                r = dict(row._mapping)
                if r.get("timestamp"):
                    r["timestamp"] = str(r["timestamp"])
                rows.append(r)
            return rows
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/symptoms/{log_id}")
async def remove_symptom_log(log_id: int, patient_id: str = Query(...)):
    try:
        with engine.connect() as conn:
            check = conn.execute(
                text("SELECT patient_id FROM symptom_logs WHERE id = :lid"),
                {"lid": log_id},
            ).fetchone()
            if not check:
                raise HTTPException(404, "Symptom log not found")
            if check[0] != patient_id:
                raise HTTPException(403, "Access denied: not your symptom log")

            conn.execute(
                text("""
                UPDATE symptom_logs SET removed_at = CURRENT_TIMESTAMP WHERE id = :lid
            """),
                {"lid": log_id},
            )
            conn.commit()
            return {"status": "removed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ============================================ #
#  Doctor queue & stats & report
# ============================================ #
def _fetch_doctor_queue(pending_only: bool = False) -> List[dict]:
    with engine.connect() as conn:
        q = """
                SELECT tr.id as report_id, tr.status, tr.confidence_score,
                       tr.relevant_historical_cases, tr.top_conditions,
                       tr.doctor_diagnosis, tr.doctor_severity, tr.doctor_notes,
                       tr.diagnosis_type, tr.reject_note,
                       c.case_id, c.patient_id, c.patient_age, c.symptoms,
                       c.condition_label, c.severity, c.timestamp
                FROM triage_reports tr
                JOIN cases c ON c.case_id = tr.case_id
            """
        if pending_only:
            q += " WHERE tr.status = 'PENDING' "
        q += """
                ORDER BY
                    CASE WHEN tr.status = 'PENDING' THEN 0
                         WHEN tr.status = 'REJECTED' THEN 1
                         ELSE 2 END,
                    tr.created_at DESC
            """
        result = conn.execute(text(q))
        rows = []
        for row in result:
            r = dict(row._mapping)
            rows.append(row_parse_json_fields(r))
        return rows


@app.get("/doctor/queue")
async def get_triage_queue():
    try:
        return _fetch_doctor_queue(pending_only=False)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/doctor/all-patients")
async def get_all_patients():
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT c.patient_id, COUNT(*) as case_count,
                       MAX(c.timestamp) as last_visit,
                       STRING_AGG(DISTINCT c.condition_label, ', ') as conditions
                FROM cases c
                GROUP BY c.patient_id
                ORDER BY MAX(c.timestamp) DESC
            """)
            )
            rows = []
            for row in result:
                r = dict(row._mapping)
                if r.get("last_visit"):
                    r["last_visit"] = str(r["last_visit"])
                rows.append(r)
            return rows
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/doctor/all-symptom-logs")
async def get_all_symptom_logs():
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT sl.id, sl.patient_id, sl.case_id, sl.symptoms, sl.severity,
                       sl.pain_level, sl.timestamp, sl.removed_at
                FROM symptom_logs sl
                ORDER BY sl.timestamp DESC
                LIMIT 200
            """)
            )
            rows = []
            for row in result:
                r = dict(row._mapping)
                if r.get("timestamp"):
                    r["timestamp"] = str(r["timestamp"])
                if r.get("removed_at"):
                    r["removed_at"] = str(r["removed_at"])
                rows.append(r)
            return rows
    except Exception as e:
        raise HTTPException(500, str(e))


class ReportAction(BaseModel):
    report_id: int
    action: str  # APPROVED, REJECTED, CUSTOM
    doctor_diagnosis: Optional[str] = None
    doctor_severity: Optional[str] = None
    doctor_notes: Optional[str] = None
    reject_note: Optional[str] = None


@app.post("/doctor/report")
async def process_report(body: ReportAction):
    with engine.connect() as conn:
        tr_row = conn.execute(
            text("SELECT id, case_id FROM triage_reports WHERE id = :rid"),
            {"rid": body.report_id},
        ).fetchone()
        if not tr_row:
            raise HTTPException(404, "Report not found")

        case_id = tr_row[1]
        cond = conn.execute(
            text("SELECT condition_label FROM cases WHERE case_id = :cid"),
            {"cid": case_id},
        ).fetchone()
        condition_label = cond[0] if cond else "Unknown"

        if body.action == "CUSTOM":
            conn.execute(
                text("""
                UPDATE triage_reports
                SET status = 'APPROVED',
                    diagnosis_type = 'DOCTOR',
                    doctor_diagnosis = :diag,
                    doctor_severity = :sev,
                    doctor_notes = :notes,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :rid
            """),
                {
                    "diag": body.doctor_diagnosis or "Unspecified",
                    "sev": body.doctor_severity or "Medium",
                    "notes": body.doctor_notes or "",
                    "rid": body.report_id,
                },
            )
            ensure_treatment_plan_for_report(
                conn, body.report_id, body.doctor_diagnosis or condition_label
            )
        elif body.action == "REJECTED":
            conn.execute(
                text("""
                UPDATE triage_reports
                SET status = 'REJECTED',
                    reject_note = :note,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :rid
            """),
                {
                    "note": body.reject_note or "Please provide more symptom details.",
                    "rid": body.report_id,
                },
            )
        else:
            conn.execute(
                text("""
                UPDATE triage_reports
                SET status = 'APPROVED',
                    diagnosis_type = 'AI',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :rid
            """),
                {"rid": body.report_id},
            )
            ensure_treatment_plan_for_report(conn, body.report_id, condition_label)
        conn.commit()
    return {"status": "ok"}


def _compute_stats() -> dict:
    with engine.connect() as conn:
        total_today = conn.execute(
            text("""
                SELECT COUNT(*) FROM cases
                WHERE timestamp::date = CURRENT_DATE
            """)
        ).scalar() or 0

        total_all = conn.execute(text("SELECT COUNT(*) FROM cases")).scalar() or 0

        sev_result = conn.execute(
            text("""
                SELECT severity, COUNT(*) as cnt FROM cases
                WHERE timestamp >= CURRENT_TIMESTAMP - interval '7 days'
                GROUP BY severity
            """)
        )
        severity_breakdown = [dict(row._mapping) for row in sev_result]

        top_conditions = conn.execute(
            text("""
                SELECT condition_label, COUNT(*) as cnt
                FROM cases
                WHERE timestamp >= CURRENT_TIMESTAMP - interval '7 days'
                GROUP BY condition_label
                ORDER BY cnt DESC
                LIMIT 5
            """)
        )
        top_conds = [dict(row._mapping) for row in top_conditions]

        avg_time = conn.execute(
            text("""
                SELECT EXTRACT(EPOCH FROM AVG(tr.updated_at - tr.created_at)) / 3600.0 as avg_hours
                FROM triage_reports tr
                WHERE tr.status = 'APPROVED'
            """)
        ).scalar()
        avg_hours = round(float(avg_time), 2) if avg_time else 0

        status_result = conn.execute(
            text("SELECT status, COUNT(*) as cnt FROM triage_reports GROUP BY status")
        )
        status_breakdown = [dict(row._mapping) for row in status_result]

        total_logs = conn.execute(
            text("SELECT COUNT(*) FROM symptom_logs WHERE removed_at IS NULL")
        ).scalar() or 0

        return {
            "total_cases_today": total_today,
            "total_cases_all": total_all,
            "severity_breakdown": severity_breakdown,
            "top_conditions_week": top_conds,
            "avg_approval_hours": avg_hours,
            "status_breakdown": status_breakdown,
            "active_symptom_logs": total_logs,
        }


@app.get("/doctor/stats")
async def get_doctor_stats():
    try:
        return _compute_stats()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/timetable/{patient_id}")
async def get_timetable(patient_id: str):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT tp.id as plan_id, tp.day_by_day_plan, tp.status as plan_status,
                       c.case_id, c.condition_label, tr.diagnosis_type,
                       tr.doctor_diagnosis, tr.status as triage_status
                FROM treatment_plans tp
                JOIN triage_reports tr ON tr.id = tp.triage_report_id
                JOIN cases c ON c.case_id = tr.case_id
                WHERE c.patient_id = :pid AND tr.status = 'APPROVED'
                ORDER BY tp.id DESC
            """),
                {"pid": patient_id},
            )
            rows = []
            for row in result:
                r = dict(row._mapping)
                plan = r.get("day_by_day_plan")
                if isinstance(plan, str):
                    try:
                        plan = json.loads(plan)
                    except Exception:
                        plan = []
                r["day_by_day_plan"] = plan
                rows.append(r)
            return rows
    except Exception as e:
        raise HTTPException(500, str(e))


# ============================================ #
#  WebSocket Router
# ============================================ #
@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
