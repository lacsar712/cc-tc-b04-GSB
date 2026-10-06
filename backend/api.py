import os
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, g, jsonify, request
from jose import JWTError, jwt
from passlib.context import CryptContext

from claimer import start as start_claimer
from compare import parse_dt, recompute
from models import (
    Base,
    ComparisonReport,
    ConvergenceLog,
    SessionLocal,
    engine,
    report_dict,
    row_dict,
)

SECRET = os.environ.get("JWT_SECRET", "tunnelconv-dev-secret")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
USERS = {
    "surveyor": {"role": "writer", "password_hash": pwd.hash("surv123456")},
    "inspector": {"role": "reader", "password_hash": pwd.hash("insp123456")},
}

app = Flask(__name__)


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(ConvergenceLog).count() > 0:
            return
        now = datetime.now(timezone.utc)
        for chainage, delta, expect in (("K12+180", 1.2, "合格"), ("K18+040", 5.6, "超限")):
            from rules import judge

            verdict, reason = judge(delta)
            assert verdict == expect
            db.add(
                ConvergenceLog(
                    chainage=chainage,
                    delta_mm=delta,
                    status="done",
                    verdict=verdict,
                    reason=reason,
                    created_by="surveyor",
                    created_at=now,
                    processed_at=now,
                )
            )
        db.commit()
    finally:
        db.close()


seed()
start_claimer()


def current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:].strip(), SECRET, algorithms=["HS256"])
    except JWTError:
        return None
    sub = payload.get("sub")
    if sub not in USERS:
        return None
    return {"username": sub, "role": payload.get("role")}


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"detail": "未登录"}), 401
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def require_writer(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"detail": "未登录"}), 401
        if user["role"] != "writer":
            return jsonify({"detail": "巡检岗只读，不能提交或报送"}), 403
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "tunnel-convergence-desk"})


@app.post("/api/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    user = USERS.get(username)
    if not user or not pwd.verify(password, user["password_hash"]):
        return jsonify({"detail": "用户名或密码错误"}), 401
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": username, "role": user["role"], "exp": exp}, SECRET, algorithm="HS256"
    )
    return jsonify({"access_token": token, "username": username, "role": user["role"]})


@app.get("/api/logs")
@require_login
def list_logs():
    db = SessionLocal()
    try:
        rows = db.query(ConvergenceLog).order_by(ConvergenceLog.id.desc()).all()
        return jsonify([row_dict(r) for r in rows])
    finally:
        db.close()


@app.post("/api/logs")
@require_writer
def create_log():
    body = request.get_json(silent=True) or {}
    chainage = (body.get("chainage") or "").strip()
    if not chainage:
        return jsonify({"detail": "桩号不能为空"}), 400
    try:
        delta_mm = float(body.get("delta_mm"))
    except (TypeError, ValueError):
        return jsonify({"detail": "收敛值必须是数字"}), 400
    db = SessionLocal()
    try:
        row = ConvergenceLog(
            chainage=chainage,
            delta_mm=delta_mm,
            status="pending",
            created_by=g.user["username"],
            created_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify(row_dict(row)), 201
    finally:
        db.close()


@app.get("/api/chainages")
@require_login
def list_chainages():
    db = SessionLocal()
    try:
        rows = (
            db.query(ConvergenceLog.chainage)
            .distinct()
            .order_by(ConvergenceLog.chainage)
            .all()
        )
        return jsonify([r[0] for r in rows])
    finally:
        db.close()


def _read_compare_params(body: dict) -> tuple[str, str, datetime | None, datetime]:
    """解析对照参数：两个桩号 + 截止时刻必带，起始时刻可选。缺一边直接 400。"""
    chainage_a = (body.get("chainage_a") or "").strip()
    chainage_b = (body.get("chainage_b") or "").strip()
    if not chainage_a or not chainage_b:
        raise ValueError("必须同时选定两个桩号")
    if chainage_a == chainage_b:
        raise ValueError("两个桩号不能相同")
    start = parse_dt(body.get("start_at"), "起始时刻")
    cutoff = parse_dt(body.get("cutoff_at"), "截止时刻", required=True)
    if start is not None and start > cutoff:
        raise ValueError("起始时刻不能晚于截止时刻")
    return chainage_a, chainage_b, start, cutoff


@app.post("/api/comparisons/recompute")
@require_login
def comparisons_recompute():
    body = request.get_json(silent=True) or {}
    try:
        chainage_a, chainage_b, start, cutoff = _read_compare_params(body)
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400
    db = SessionLocal()
    try:
        return jsonify(
            recompute(db, chainage_a, chainage_b, start, cutoff)
        )
    finally:
        db.close()


@app.get("/api/comparisons")
@require_login
def list_comparisons():
    db = SessionLocal()
    try:
        rows = (
            db.query(ComparisonReport)
            .order_by(ComparisonReport.id.desc())
            .all()
        )
        return jsonify([report_dict(r) for r in rows])
    finally:
        db.close()


@app.post("/api/comparisons")
@require_writer
def create_comparison():
    body = request.get_json(silent=True) or {}
    try:
        chainage_a, chainage_b, start, cutoff = _read_compare_params(body)
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400
    caliber = (body.get("caliber") or "").strip()
    if not caliber:
        return jsonify({"detail": "口径说明不能为空"}), 400

    db = SessionLocal()
    try:
        # 报送时以后端重算为准，前端传来的中间数一律不信。
        calc = recompute(db, chainage_a, chainage_b, start, cutoff)
        if not calc["ready"]:
            names = "、".join(calc["missing"])
            return (
                jsonify({"detail": f"{names} 在选定时段内尚无办结读数，不能报送对照"}),
                400,
            )
        row = ComparisonReport(
            chainage_a=chainage_a,
            chainage_b=chainage_b,
            start_at=start,
            cutoff_at=cutoff,
            value_a=calc["value_a"],
            value_b=calc["value_b"],
            diff_mm=calc["diff_mm"],
            caliber=caliber,
            submitted_by=g.user["username"],
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify(report_dict(row)), 201
    finally:
        db.close()
