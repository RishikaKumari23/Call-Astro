"""
Backtesting harness for the Event Timing Engine — Stage 1 only.

IMPORTANT FRAMING: this measures the baseline Dasha-candidate-window engine
(7th-house factors + Mahadasha/Antardasha "and" matching), NOT a final
marriage-prediction system. It has no early/late tendency ranking and no
transit intersection. Report results as "baseline evaluation of the Dasha
candidate engine," not "marriage prediction accuracy."

Because "and" matching gives every returned window the same match_score,
windows are NOT meaningfully ranked yet — "top window" here means "first
chronologically-returned candidate," not "best predicted candidate." All
metrics reflect that. Report top-1/top-3/top-5/any-candidate hit rates
together, not top-1 alone, since top-1 currently carries no special
predictive weight over the others.

DATA LEAKAGE WARNING: if you use the same cases to both develop the
hierarchy rules AND evaluate them, the resulting metrics are not a fair
test. Split any real dataset into a development set (used while building/
tuning rules) and a held-out test set (touched only for final reporting).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from app.services.event_timing_service import find_candidate_windows
from app.services.dasha_api_service import dasha_api_service
from app.services.kundli_service import kundli_service
from app.services.geocoding_service import geocoding_service
from app.utils.logger import logger


@dataclass
class TestCase:
    """One real, known case to validate against.
    actual_marriage_date accepts either 'YYYY-MM' or 'YYYY-MM-DD' — use the
    day-level format whenever you actually know the exact date, since
    month-only dates get treated as day 1 of that month, which understates
    precision if the real date was later in the month."""
    label: str
    dob: str                      # DD-MM-YYYY
    birth_time: str               # HH:MM (24h)
    birth_place: str
    actual_marriage_date: str     # 'YYYY-MM' or 'YYYY-MM-DD'


@dataclass
class BacktestResult:
    label: str
    actual_date: Optional[datetime] = None
    actual_date_precision: str = "month"
    all_predicted_windows: List[Dict] = field(default_factory=list)
    first_candidate_deviation_months: Optional[float] = None  # renamed from top1_deviation_months
    hit_first_candidate: bool = False                          # renamed from hit_top1
    hit_top3: bool = False
    hit_top5: bool = False
    hit_any_candidate: bool = False
    error: Optional[str] = None

def _parse_actual_date(date_str: str) -> Optional[Dict]:
    """Returns {"dt": datetime, "precision": "day"|"month"} or None."""
    date_str = date_str.strip()
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return {"dt": dt, "precision": "day"}
    except (ValueError, TypeError):
        pass
    try:
        dt = datetime.strptime(date_str, "%Y-%m")
        return {"dt": dt, "precision": "month"}
    except (ValueError, TypeError):
        return None


def _months_between(a: datetime, b: datetime) -> float:
    return abs((a.year - b.year) * 12 + (a.month - b.month))


def _deviation_from_window(actual: datetime, window: Dict) -> Optional[float]:
    start = window.get("start", "").split(" ")[0]
    end = window.get("end", "").split(" ")[0]
    try:
        start_dt = datetime.strptime(start, "%d/%m/%Y")
        end_dt = datetime.strptime(end, "%d/%m/%Y")
    except (ValueError, TypeError):
        return None

    if start_dt <= actual <= end_dt:
        return 0.0
    if actual < start_dt:
        return _months_between(actual, start_dt)
    return _months_between(actual, end_dt)


def run_single_case(case: TestCase) -> BacktestResult:
    result = BacktestResult(label=case.label)

    parsed_actual = _parse_actual_date(case.actual_marriage_date)
    if not parsed_actual:
        result.error = f"Could not parse actual_marriage_date: {case.actual_marriage_date} (expected YYYY-MM or YYYY-MM-DD)"
        return result
    result.actual_date = parsed_actual["dt"]
    result.actual_date_precision = parsed_actual["precision"]

    try:
        coords = geocoding_service.geocode(case.birth_place)
        if not coords:
            result.error = f"Could not geocode birth_place: {case.birth_place}"
            return result
        lat, lon = coords

        kundli_data = kundli_service.fetch_kundli(
            name=case.label, date=case.dob, time=case.birth_time,
            latitude=lat, longitude=lon,
        )
        if not kundli_data:
            result.error = "Kundli fetch failed"
            return result

        chart_data = kundli_service.extract_chart_data(kundli_data)
        if not chart_data:
            result.error = "Chart data extraction failed"
            return result
        planets = chart_data.get("planets", [])
        ascendant_sign = chart_data.get("ascendant_sign")

        ascendant_data = kundli_service.get_ascendant_data(kundli_data)
        if not ascendant_data:
            result.error = "Could not extract ascendant_data for dasha API"
            return result

        dasha_tree = dasha_api_service.fetch_dasha_tree(
            date=case.dob, time=case.birth_time,
            latitude=lat, longitude=lon, ascendant_data=ascendant_data,
        )
        if not dasha_tree:
            result.error = "Dasha tree fetch failed"
            return result

        flattened = dasha_api_service.flatten_periods(dasha_tree, level="antardasha")

        timing_result = find_candidate_windows("marriage", planets, ascendant_sign, flattened)
        if not timing_result.get("supported"):
            result.error = "No supported candidate window found"
            return result

        # Store ALL windows, not just a slice — otherwise a correct match
        # at candidate #6+ would be invisible to the "any candidate" metric.
        result.all_predicted_windows = timing_result["windows"]

        deviations = [
            _deviation_from_window(result.actual_date, w)
            for w in result.all_predicted_windows
        ]
        deviations = [d for d in deviations if d is not None]
        
        if deviations:
            result.first_candidate_deviation_months = deviations[0]
            result.hit_first_candidate = deviations[0] == 0.0
            result.hit_top3 = any(d == 0.0 for d in deviations[:3])
            result.hit_top5 = any(d == 0.0 for d in deviations[:5])
            result.hit_any_candidate = any(d == 0.0 for d in deviations)
        
    except Exception as e:
        logger.error(f"Backtest case '{case.label}' failed: {e}")
        result.error = str(e)

    return result
def run_backtest(cases: List[TestCase], dataset_label: str = "unspecified") -> Dict:
    """Runs all cases and computes aggregate baseline metrics.

    dataset_label is DOCUMENTATION ONLY, not enforcement — it records what
    you intended the dataset to be (e.g. "development" or "held-out test")
    but this function has no way to verify a case wasn't already seen during
    rule-tuning. Leakage protection is a process discipline on your end
    (keep a physical/logical separation of which cases you look at while
    adjusting event_timing_service.py or marriage_tendency_service.py),
    not something this code can guarantee."""
    results = [run_single_case(c) for c in cases]

    valid_results = [r for r in results if r.error is None and r.first_candidate_deviation_months is not None]
    failed_results = [r for r in results if r.error is not None]

    summary = {
        "framing": (
            "Baseline evaluation of the Dasha candidate-window engine "
            "(7th-house factors + Mahadasha/Antardasha matching only). "
            "NOT a final marriage-prediction accuracy measure — no early/late "
            "tendency ranking or transit intersection applied."
        ),
        "dataset_label": dataset_label,
        "dataset_label_caveat": (
            "This label is self-reported documentation only. It is NOT enforced — "
            "nothing prevents submitting the same cases used to tune the hierarchy "
            "rules as 'held-out test'. Data-leakage protection must be maintained "
            "as a process discipline outside this code (keep a real, untouched "
            "held-out set that is never looked at while adjusting rules)."
        ),
        "match_mode_note": (
            "Windows use 'and' matching, so all returned windows currently "
            "share the same match_score — 'first candidate' means the first "
            "chronologically returned window, not a ranked best guess. Do not "
            "interpret it as the engine's top prediction."
        ),
        "total_cases": len(cases),
        "successful_cases": len(valid_results),
        "failed_cases": len(failed_results),
        "failures": [{"label": r.label, "error": r.error} for r in failed_results],
    }

    if valid_results:
        deviations = [r.first_candidate_deviation_months for r in valid_results]
        deviations_sorted = sorted(deviations)
        n = len(deviations_sorted)

        summary["mean_deviation_months"] = round(sum(deviations) / n, 2)
        summary["median_deviation_months"] = round(
            deviations_sorted[n // 2] if n % 2 == 1
            else (deviations_sorted[n // 2 - 1] + deviations_sorted[n // 2]) / 2,
            2
        )
        summary["hit_rates"] = {
            "first_candidate": round(sum(1 for r in valid_results if r.hit_first_candidate) / n, 3),
            "top_3": round(sum(1 for r in valid_results if r.hit_top3) / n, 3),
            "top_5": round(sum(1 for r in valid_results if r.hit_top5) / n, 3),
            "any_candidate_window": round(sum(1 for r in valid_results if r.hit_any_candidate) / n, 3),
        }
        summary["deviation_bands"] = {
            "within_3_months_pct": round(sum(1 for d in deviations if d <= 3) / n, 3),
            "within_6_months_pct": round(sum(1 for d in deviations if d <= 6) / n, 3),
            "within_12_months_pct": round(sum(1 for d in deviations if d <= 12) / n, 3),
        }
        day_precision_count = sum(1 for r in valid_results if r.actual_date_precision == "day")
        summary["actual_date_precision_note"] = (
            f"{day_precision_count}/{n} cases used exact (YYYY-MM-DD) marriage dates; "
            f"{n - day_precision_count}/{n} used month-only precision (treated as day 1 of that month)."
        )
    else:
        summary["mean_deviation_months"] = None
        summary["median_deviation_months"] = None
        summary["hit_rates"] = None
        summary["deviation_bands"] = None

    summary["per_case_detail"] = [
        {
            "label": r.label,
            "actual_date": r.actual_date.strftime("%Y-%m-%d") if r.actual_date else None,
            "actual_date_precision": r.actual_date_precision,
            "first_candidate_deviation_months": r.first_candidate_deviation_months,
            "hit_first_candidate": r.hit_first_candidate,
            "hit_top3": r.hit_top3,
            "hit_top5": r.hit_top5,
            "hit_any_candidate": r.hit_any_candidate,
            "total_candidate_windows": len(r.all_predicted_windows),
            "predicted_windows": [
                {"mahadasha": w.get("mahadasha"), "antardasha": w.get("antardasha"),
                 "start": w.get("start"), "end": w.get("end")}
                for w in r.all_predicted_windows
            ],
            "error": r.error,
        }
        for r in results
    ]

    return summary

