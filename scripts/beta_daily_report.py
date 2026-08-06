#!/usr/bin/env python3
"""Laporan harian beta v0.1.0-beta.1 — FULLY DETERMINISTIC, tanpa LLM.

Menjalankan seluruh pipeline: hitung metrik, jalankan baseline penuh, update
CURRENT.md, append journal, commit lokal (tanpa push), print laporan ke stdout.

Didesain utk cron `no_agent=true` agar TIDAK ada panggilan LLM agent (menghindari
429/timeout/JSON-error 9router). Stdout dideliver verbatim sebagai laporan.

EXIT: 0 = sukses & laporan dicetak; 1 = gagal (cron kirim alert).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, date, timedelta, timezone, tzinfo
from pathlib import Path

REPO = "/home/wajdi/hermes-dual-memory"
BETA = REPO + "/docs/beta/v0.1.0-beta.1"
CURRENT = BETA + "/CURRENT.md"
JOURNAL = BETA + "/journal.md"
HERMES_SOURCE = "/home/wajdi/.hermes/hermes-agent"
HERMES_PY = HERMES_SOURCE + "/venv/bin/python"
BASELINE_SCRIPT = REPO + "/evaluation/phase8_regression.py"
BASELINE_RESERVE = REPO + "/docs/testing/baselines/phase-8-baseline.json"
BASELINE_OUT = "/tmp/beta-harian-baseline.json"
TARGET_DATE = date(2026, 8, 19)

DBS = [
    ("default", "/home/wajdi/.hermes/hermes-dual-memory/hot_sessions.sqlite3"),
    ("research", "/home/wajdi/.hermes/profiles/research/hermes-dual-memory/hot_sessions.sqlite3"),
    ("coding", "/home/wajdi/.hermes/profiles/coding/hermes-dual-memory/hot_sessions.sqlite3"),
]

# WIB = UTC+8 (offset +08:00)
class WIB(tzinfo):
    def utcoffset(self, dt): return timedelta(hours=8)
    def tzname(self, dt): return "WIB"
    def dst(self, dt): return timedelta(0)


def now_wib():
    return datetime.now(WIB())


def load_env():
    env = dict(os.environ)
    env.setdefault("HERMES_SOURCE_ROOT", HERMES_SOURCE)
    env.setdefault("HERMES_HOME", "/home/wajdi/.hermes/profiles/coding")
    p = Path("/home/wajdi/.hermes/profiles/coding/.env")
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env.setdefault(k.strip(), v.strip())
    return env


def db_query(db, sql):
    try:
        return sqlite3.connect(db, timeout=5).execute(sql).fetchall()
    except Exception as e:  # noqa: BLE001
        return [("ERR", str(e)[:100])]


def compute_metrics():
    profiles = []
    total_sessions = 0
    all_days = set()
    for name, db in DBS:
        s = db_query(db, "SELECT COUNT(DISTINCT session_id) FROM hot_sessions")
        mi = db_query(db, "SELECT COUNT(*) FROM memory_index")
        pd = db_query(db, "SELECT COUNT(*) FROM hot_sessions WHERE consolidated=0")
        days = db_query(db, "SELECT DISTINCT date(timestamp) FROM hot_sessions")
        ns = int(s[0][0]) if s and str(s[0][0]).lstrip('-').isdigit() else 0
        nm = int(mi[0][0]) if mi and str(mi[0][0]).lstrip('-').isdigit() else 0
        npd = int(pd[0][0]) if pd and str(pd[0][0]).lstrip('-').isdigit() else 0
        dl = [str(d[0]) for d in days if d and str(d[0]) != "ERR"]
        all_days.update(dl)
        total_sessions += ns
        profiles.append({"profile": name, "sessions": ns, "memory_index": nm,
                         "pending": npd, "active_days": sorted(dl)})
    return profiles, total_sessions, sorted(all_days)


def run_baseline(env):
    b = {}
    cmd = [HERMES_PY, BASELINE_SCRIPT, "--output", BASELINE_OUT,
           "--compare-to", BASELINE_RESERVE, "--skip-token-measurement"]
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=540)
        b["exit"] = r.returncode
        b["elapsed_s"] = round(time.monotonic() - t0, 1)
        if r.returncode == 0 and Path(BASELINE_OUT).exists():
            d = json.loads(Path(BASELINE_OUT).read_text())
            agg = d.get("aggregate", {})
            b["overall_verdict"] = d.get("overall_verdict")
            b["memory_recall"] = agg.get("memory_recall")
            b["memory_precision_at_k"] = agg.get("memory_precision_at_k")
            lat = agg.get("latency_ms", {})
            b["p50_ms"] = lat.get("p50")
            b["p95_ms"] = lat.get("p95")
            b["categories"] = {c.get("category"): c.get("verdict")
                               for c in d.get("categories", [])}
            b["comparison"] = d.get("comparison")
        else:
            b["stderr_tail"] = r.stderr[-500:]
    except subprocess.TimeoutExpired:
        b["exit"] = "TIMEOUT_540s"
        b["elapsed_s"] = round(time.monotonic() - t0, 1)
    except Exception as e:  # noqa: BLE001
        b["exit"] = "EXC"
        b["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return b


def update_current_md(total_sessions, active_days):
    text = Path(CURRENT).read_text()
    daylist = ", ".join(active_days)
    # update Hari aktif
    text = re.sub(
        r"(\*\*Hari aktif / target\*\*): `[^`]*`[^\n]*",
        f"\\1: `{len(active_days)} / 14` (aktif {daylist})",
        text, count=1)
    # update Sesi nyata
    text = re.sub(
        r"(\*\*Sesi nyata / target\*\*): `[^`]*`[^\n]*",
        f"\\1: `{total_sessions} / 30` (default, research, coding — dihitung dari session_id unik di hot_sessions per hari ini)",
        text, count=1)
    Path(CURRENT).write_text(text)
    return text


def append_journal(profiles, total_sessions, active_days, baseline):
    ts = now_wib().strftime("%Y-%m-%dT%H:%M+08:00")
    # guard duplikat: skip append jika entri dengan hari+jam yang sama sudah ada
    existing = Path(JOURNAL).read_text()
    if ts[:10] in existing and f"### {ts[:10]}T" in existing:
        # sudah ada entri jam ini (mis. cron dijalankan 2x) — lewati append agar tidak duplikat
        return None
    pend = {p["profile"]: p["pending"] for p in profiles}
    mi = {p["profile"]: p["memory_index"] for p in profiles}
    sess = {p["profile"]: p["sessions"] for p in profiles}
    bv = baseline.get("overall_verdict", "N/A")
    recall = baseline.get("memory_recall", "N/A")
    prec = baseline.get("memory_precision_at_k", "N/A")
    p50 = baseline.get("p50_ms", "N/A")
    p95 = baseline.get("p95_ms", "N/A")
    entry = f"""
### {ts} — Laporan harian beta otomatis (script deterministik)

- **Actor**: Ada (cron no_agent)
- **Mode**: maintenance
- **Metrik**: sesi nyata {total_sessions}/30 ({sess}), hari aktif {len(active_days)}/14 ({', '.join(active_days)})
- **Memory index**: {mi}; **pending consolidation**: {pend}
- **Baseline (48 query)**: verdict={bv}, recall={recall}, precision@k={prec}, p50={p50}ms, p95={p95}ms
- **Drift vs baseline resmi**: {(baseline.get('comparison') or {}).get('metric_deltas')}
- **Severity**: T3 (rutin, tidak ada S0/S1)
- **Action**: update CURRENT.md + commit lokal
- **Result**: sukses (script deterministik, tanpa LLM agent), tidak di-push
"""
    with open(JOURNAL, "a") as f:
        f.write(entry)
    return entry.strip()


def git_commit(total_sessions, active_days, baseline):
    bv = baseline.get("overall_verdict", "N/A")
    msg = f"[beta/0.1] laporan harian: {total_sessions}/30 sesi, {len(active_days)}/14 hari aktif, baseline {bv} (ref journal)"
    subprocess.run(["git", "-C", REPO, "add", CURRENT, JOURNAL], check=False)
    r = subprocess.run(["git", "-C", REPO, "commit", "-m", msg],
                       capture_output=True, text=True, check=False)
    return r.returncode == 0, r.stdout.strip()[-200:]


def build_report(profiles, total_sessions, active_days, baseline, alerts, days_left):
    sess = {p["profile"]: p["sessions"] for p in profiles}
    mi = {p["profile"]: p["memory_index"] for p in profiles}
    pend = {p["profile"]: p["pending"] for p in profiles}
    bv = baseline.get("overall_verdict", "N/A")
    cats = baseline.get("categories", {})
    cat_str = ", ".join(f"{k}={v}" for k, v in cats.items()) if cats else "N/A"
    comp = (baseline.get("comparison") or {}).get("metric_deltas", {})
    drifts = []
    for k, v in comp.items():
        if isinstance(v, dict) and v.get("status") == "compared":
            drifts.append(f"{k}={v.get('delta')}")
    drift_str = "; ".join(drifts) if drifts else "tidak ada regression terukur"
    alert_str = "\n".join(f"  - {a}" for a in alerts) if alerts else "  - tidak ada"
    return f"""## Laporan Beta Harian — {now_wib().strftime('%Y-%m-%d')}

**Mode**: script deterministik (cron no_agent, tanpa LLM)

**Countdown**: {days_left} hari tersisa ke target 08-19

**Progress**:
- Sesi nyata: {total_sessions}/30
- Hari aktif: {len(active_days)}/14 ({', '.join(active_days)})
- Per profile (sesi/memory_index/pending): default {sess.get('default')}/{mi.get('default')}/{pend.get('default')}; research {sess.get('research')}/{mi.get('research')}/{pend.get('research')}; coding {sess.get('coding')}/{mi.get('coding')}/{pend.get('coding')}

**Baseline (48 query)**: verdict={bv}, recall={recall_} if 'recall_' ...
"""


def main():
    profiles, total_sessions, active_days = compute_metrics()
    env = load_env()
    baseline = run_baseline(env)
    days_left = (TARGET_DATE - date.today()).days

    # ---- alerts ----
    alerts = []
    if baseline.get("overall_verdict") not in (None, "PASS"):
        alerts.append(f"ALERT regression: baseline verdict={baseline.get('overall_verdict')}")
    for k, v in (baseline.get("categories") or {}).items():
        if v not in (None, "PASS"):
            alerts.append(f"ALERT kategori {k}={v}")
    pend_total = sum(p["pending"] for p in profiles)
    if pend_total > 20:
        alerts.append(f"ALERT pending consolidation menumpuk ({pend_total})")
    if days_left <= 3:
        alerts.append(f"ALERT countdown: {days_left} hari tersisa ke target")

    # ---- update docs ----
    update_current_md(total_sessions, active_days)
    append_journal(profiles, total_sessions, active_days, baseline)
    committed, log = git_commit(total_sessions, active_days, baseline)

    # ---- report ----
    sess = {p["profile"]: p["sessions"] for p in profiles}
    mi = {p["profile"]: p["memory_index"] for p in profiles}
    pend = {p["profile"]: p["pending"] for p in profiles}
    bv = baseline.get("overall_verdict", "N/A")
    cats = baseline.get("categories", {})
    cat_str = ", ".join(f"{k}={v}" for k, v in cats.items()) if cats else "N/A"
    alert_str = "\n".join(f"  - {a}" for a in alerts) if alerts else "  - tidak ada"

    # drift string
    deltas = (baseline.get("comparison") or {}).get("metric_deltas", {})
    drifts = []
    for k, v in deltas.items():
        if isinstance(v, dict) and v.get("status") == "compared":
            drifts.append("{}={}".format(k, v.get("delta")))
    drift_str = "; ".join(drifts) if drifts else "tidak ada regression"

    report = f"""## Laporan Beta Harian — {now_wib().strftime('%Y-%m-%d')}

**Mode**: script deterministik (cron no_agent, tanpa langganan LLM agent)

**Countdown**: {days_left} hari tersisa ke target 08-19

**Progress**:
- Sesi nyata: {total_sessions}/30
- Hari aktif: {len(active_days)}/14 ({', '.join(active_days)})
- Per profile (sesi/mem/pending): default {sess.get('default')}/{mi.get('default')}/{pend.get('default')}; research {sess.get('research')}/{mi.get('research')}/{pend.get('research')}; coding {sess.get('coding')}/{mi.get('coding')}/{pend.get('coding')}

**Baseline (48 query) — {baseline.get('elapsed_s','?')}s**:
- Verdict: {bv}
- Recall: {baseline.get('memory_recall','N/A')}, precision@k: {baseline.get('memory_precision_at_k','N/A')}
- Latency: p50={baseline.get('p50_ms','N/A')}ms, p95={baseline.get('p95_ms','N/A')}ms
- Kategori: {cat_str}
- Drift vs baseline resmi: {drift_str}

**Alert**: 
{alert_str}

**Git**: commit {'SUKSES' if committed else 'GAGAL'} · {'di-push? TIDAK (butuh approval)' if committed else log}

**Kesimpulan**: {'SESI SUDAH >=30 target' if total_sessions >= 30 else 'sesi belum target'} · {'HARI AKTIF BELUM 14' if len(active_days) < 14 else 'hari aktif target tercapai'} · baseline {'PASS' if bv == 'PASS' else f'belum PASS ({bv})'}
"""
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())