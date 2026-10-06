"""邻断面对照口径：在选定时段内取两侧最近一次办结（done）读数，再算差值。

规矩：
- 只有 done（已办结）行算数，pending 永远不进对照；
- 以办结时刻 processed_at 落进 [start_at, cutoff_at] 为准，时段之外的点这次不算；
- 两侧在时段内都有办结值才出差值，任一侧缺失就不算，绝不替它填数。
"""
from datetime import datetime, timezone

from models import ConvergenceLog


def parse_dt(value: str | None, field: str, *, required: bool = False) -> datetime | None:
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"缺少{field}")
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}时间格式无效")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _latest_done(db, chainage: str, start: datetime | None, cutoff: datetime):
    q = db.query(ConvergenceLog).filter(
        ConvergenceLog.chainage == chainage,
        ConvergenceLog.status == "done",
        ConvergenceLog.processed_at.isnot(None),
        ConvergenceLog.processed_at <= cutoff,
    )
    if start is not None:
        q = q.filter(ConvergenceLog.processed_at >= start)
    return (
        q.order_by(ConvergenceLog.processed_at.desc(), ConvergenceLog.id.desc())
        .first()
    )


def recompute(db, chainage_a: str, chainage_b: str,
              start: datetime | None, cutoff: datetime) -> dict:
    """按口径重算，返回两侧最近办结值与差值。

    ready=False 时 value_*/diff_mm 一律缺省，调用方不许自己补。
    """
    row_a = _latest_done(db, chainage_a, start, cutoff)
    row_b = _latest_done(db, chainage_b, start, cutoff)

    result = {
        "chainage_a": chainage_a,
        "chainage_b": chainage_b,
        "start_at": start.isoformat() if start else None,
        "cutoff_at": cutoff.isoformat() if cutoff else None,
        "ready": row_a is not None and row_b is not None,
        "missing": [
            name
            for name, row in ((chainage_a, row_a), (chainage_b, row_b))
            if row is None
        ],
    }
    if row_a is not None:
        result["value_a"] = float(row_a.delta_mm)
        result["processed_at_a"] = row_a.processed_at.isoformat()
        result["log_id_a"] = row_a.id
    if row_b is not None:
        result["value_b"] = float(row_b.delta_mm)
        result["processed_at_b"] = row_b.processed_at.isoformat()
        result["log_id_b"] = row_b.id
    if result["ready"]:
        result["diff_mm"] = round(float(row_a.delta_mm) - float(row_b.delta_mm), 3)
    return result
