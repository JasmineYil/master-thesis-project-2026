from __future__ import annotations
import json
import pickle
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import pandas as pd
import config

NS_TO_S  = 1 / 1_000_000_000
NS_TO_MS = 1 / 1_000_000
B_TO_MB  = 1 / (1024 * 1024)

def run_xctrace(args: list[str]) -> tuple[bytes, str]:
    last_err = ""
    for attempt in range(1, config.XCTRACE_MAX_RETRIES + 1):
        proc = subprocess.run(
            ["xctrace"] + args,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout, ""
        last_err = proc.stderr.decode("utf-8", errors="replace").strip()
        if not last_err:
            last_err = f"exit code {proc.returncode}, no stderr output"
        is_segfault = "Segmentation fault" in last_err
        is_signal_kill = proc.returncode < 0
        if is_segfault or is_signal_kill:
            time.sleep(config.XCTRACE_RETRY_SLEEP_S)
            continue
        break
    return b"", last_err

def parse_toc(trace_path: Path) -> dict[int, dict]:
    cache_path = config.CACHE_DIR / "toc" / f"{trace_path.stem}.json"
    if cache_path.exists():
        return {int(k): v for k, v in json.loads(cache_path.read_text()).items()}

    toc_xml, err = run_xctrace(["export", "--input", str(trace_path), "--toc"])
    if err:
        raise RuntimeError(f"xctrace --toc failed: {err}")

    root = ET.fromstring(toc_xml)
    runs = {}
    for run_elem in root.iter("run"):
        run_num = int(run_elem.get("number"))
        duration_elem = run_elem.find(".//duration")
        duration_s = float(duration_elem.text) if duration_elem is not None else 0.0
        schemas = {}
        data_elem = run_elem.find("data")
        if data_elem is not None:
            for idx, table in enumerate(data_elem.findall("table"), start=1):
                schema = table.get("schema")
                if schema:
                    schemas[schema] = idx
        runs[run_num] = {"duration_s": duration_s, "schemas": schemas}

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({str(k): v for k, v in runs.items()}))
    return runs

def extract_rows(xml_bytes: bytes, schema_columns: list[str]) -> list[dict]:
    if not xml_bytes.strip():
        return []
    root = ET.fromstring(xml_bytes)
    id_lookup: dict[str, dict] = {}

    def resolve(elem):
        if elem.tag == "sentinel":
            return None
        ref = elem.get("ref")
        if ref is not None:
            return id_lookup.get(ref)
        result = {"raw": elem.text, "fmt": elem.get("fmt", "")}
        elem_id = elem.get("id")
        if elem_id is not None:
            id_lookup[elem_id] = result
        for descendant in elem.iter():
            d_id = descendant.get("id")
            if d_id is not None and d_id not in id_lookup:
                id_lookup[d_id] = {"raw": descendant.text,
                                   "fmt": descendant.get("fmt", "")}
        return result

    rows = []
    for row_elem in root.iter("row"):
        row_data = {}
        for idx, child in enumerate(row_elem):
            col = schema_columns[idx] if idx < len(schema_columns) else f"col_{idx}"
            row_data[col] = resolve(child)
        rows.append(row_data)
    return rows

def to_float(val):
    if val is None:
        return None
    raw = val.get("raw")
    if raw:
        try:
            return float(raw)
        except (ValueError, TypeError):
            pass
    return None

def to_str(val):
    if val is None:
        return ""
    return val.get("fmt") or val.get("raw") or ""

def parse_schema(schema: str, rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return _empty_df(schema)

    if schema == "core-animation-fps-estimate":
        return pd.DataFrame([{
            "timestamp_s": (to_float(r["interval"]) or 0) * NS_TO_S,
            "fps":         to_float(r["fps"]),
            "gpu_util_percent": to_float(r["device-utilization"]),
        } for r in rows])

    if schema == "device-thermal-state-intervals":
        return pd.DataFrame([{
            "start_s":       (to_float(r["start"]) or 0) * NS_TO_S,
            "duration_s":    (to_float(r["duration"]) or 0) * NS_TO_S,
            "thermal_state": to_str(r["thermal-state"]),
        } for r in rows])

    if schema == "potential-hangs":
        return pd.DataFrame([{
            "timestamp_s": (to_float(r["start"]) or 0) * NS_TO_S,
            "duration_ms": (to_float(r["duration"]) or 0) * NS_TO_MS,
            "hang_type":   to_str(r["hang-type"]),
        } for r in rows])

    if schema == "activity-monitor-process-live":
        return pd.DataFrame([{
            "timestamp_s":         (to_float(r["start"]) or 0) * NS_TO_S,
            "cpu_percent":         to_float(r["cpu-percent"]),
            "thread_count":        to_float(r["thread-count"]),
            "memory_footprint_mb": (to_float(r["memory-physical-footprint"]) or 0) * B_TO_MB,
        } for r in rows])

    if schema == "sysmon-process":
        return pd.DataFrame([{
            "timestamp_s":         (to_float(r["time"]) or 0) * NS_TO_S,
            "memory_anonymous_mb": (to_float(r["memory-anonymous"]) or 0) * B_TO_MB,
        } for r in rows])

    if schema == "graphics-statistic":
        records = []
        for r in rows:
            stat_name = to_str(r["stat"])
            if stat_name not in config.GRAPHICS_STATS_KEEP:
                continue
            records.append({
                "timestamp_s": (to_float(r["timestamp"]) or 0) * NS_TO_S,
                "stat_col":    config.GRAPHICS_STATS_KEEP[stat_name],
                "value":       to_float(r["value"]),
            })
        if not records:
            return _empty_df(schema)
        df = pd.DataFrame(records)
        df = df.pivot_table(index="timestamp_s", columns="stat_col",
                            values="value", aggfunc="first").reset_index()
        df.columns.name = None
        if "gpu_in_use_sys_mem_bytes" in df.columns:
            df["gpu_in_use_sys_mem_mb"] = df["gpu_in_use_sys_mem_bytes"] * B_TO_MB
            df = df.drop(columns=["gpu_in_use_sys_mem_bytes"])
        return df

    raise ValueError(f"Unknown schema: {schema}")

def _empty_df(schema: str) -> pd.DataFrame:
    cols = {
        "core-animation-fps-estimate":     ["timestamp_s", "fps", "gpu_util_percent"],
        "device-thermal-state-intervals":  ["start_s", "duration_s", "thermal_state"],
        "potential-hangs":                 ["timestamp_s", "duration_ms", "hang_type"],
        "activity-monitor-process-live":   ["timestamp_s", "cpu_percent",
                                            "thread_count", "memory_footprint_mb"],
        "sysmon-process":                  ["timestamp_s", "memory_anonymous_mb"],
        "graphics-statistic":              ["timestamp_s", "gpu_device_util_percent",
                                            "gpu_in_use_sys_mem_mb"],
    }
    return pd.DataFrame(columns=cols.get(schema, []))

TRACE_RE = re.compile(r"^(?P<fw>cross|native)_(?P<ar>mb|ml)_(?P<dur>\d{2}min)$")

def trace_to_condition(trace_name: str) -> dict:
    m = TRACE_RE.match(trace_name)
    if not m:
        raise ValueError(f"Cannot parse trace name: {trace_name}")
    return {
        "trace":     trace_name,
        "framework": config.FRAMEWORK_MAP[m.group("fw")],
        "ar_mode":   config.AR_MODE_MAP[m.group("ar")],
        "session":   config.DURATION_MAP[m.group("dur")],
    }

def summarize_run(per_schema_dfs: dict[str, pd.DataFrame]) -> dict:
    out = {}

    fps_df = per_schema_dfs.get("fps")
    if fps_df is not None and len(fps_df) > 0:
        fps = fps_df["fps"].dropna()
        if len(fps) > 0:
            out["fps_mean"]  = fps.mean()
            out["fps_p5"]    = fps.quantile(0.05)
            out["fps_stdev"] = fps.std()
            out["fps_frames_below_55_pct"] = (fps < 55).mean() * 100

    thermal_df = per_schema_dfs.get("thermal")
    if thermal_df is not None and len(thermal_df) > 0:
        total = thermal_df["duration_s"].sum()
        for state in ["Nominal", "Fair", "Serious", "Critical"]:
            secs = thermal_df.loc[thermal_df["thermal_state"] == state,
                                  "duration_s"].sum()
            out[f"pct_{state.lower()}"] = secs / total * 100 if total > 0 else 0.0
        by_state = thermal_df.groupby("thermal_state")["duration_s"].sum()
        out["dominant_state"] = by_state.idxmax() if len(by_state) else ""

    hangs_df = per_schema_dfs.get("hangs")
    if hangs_df is not None:
        out["hang_count"] = len(hangs_df)
        if len(hangs_df) > 0:
            out["duration_total_ms"] = hangs_df["duration_ms"].sum()
            out["duration_max_ms"]   = hangs_df["duration_ms"].max()
        else:
            out["duration_total_ms"] = 0.0
            out["duration_max_ms"]   = 0.0

    am_df = per_schema_dfs.get("activity")
    if am_df is not None and len(am_df) > 0:
        out["cpu_percent_mean"]   = am_df["cpu_percent"].mean()
        out["cpu_percent_max"]    = am_df["cpu_percent"].max()
        out["thread_count_mean"]  = am_df["thread_count"].mean()
        out["memory_footprint_peak_mb"] = am_df["memory_footprint_mb"].max()
        out["memory_growth_mb"] = (am_df["memory_footprint_mb"].max()
                                   - am_df["memory_footprint_mb"].iloc[0])

    sm_df = per_schema_dfs.get("sysmon")
    if sm_df is not None and len(sm_df) > 0:
        out["memory_anonymous_mb_max"] = sm_df["memory_anonymous_mb"].max()

    gx_df = per_schema_dfs.get("graphics")
    if gx_df is not None and len(gx_df) > 0:
        if "gpu_device_util_percent" in gx_df.columns:
            out["gpu_device_util_mean"] = gx_df["gpu_device_util_percent"].mean()
        if "gpu_in_use_sys_mem_mb" in gx_df.columns:
            out["gpu_in_use_sys_mem_mean"] = gx_df["gpu_in_use_sys_mem_mb"].mean()

    return out

def run_cache_path(trace_name: str, run_num: int) -> Path:
    return config.CACHE_DIR / "runs" / f"{trace_name}_run{run_num}.pkl"

def extract_run(trace_path: Path, trace_name: str, run_num: int,
                table_indices: dict, log_lines: list) -> dict | None:

    cache_path = run_cache_path(trace_name, run_num)

    if cache_path.exists():
        cached = pickle.loads(cache_path.read_bytes())
        raw_rows_by_schema = cached["raw_rows"]
    else:
        raw_rows_by_schema = {}
        fatal_failure = False

        for schema, spec in config.SCHEMAS.items():
            table_idx = table_indices.get(schema)
            if table_idx is None:
                log_lines.append(f"  run {run_num} {schema}: schema not in TOC")
                continue
            xpath = f"//trace-toc[1]/run[{run_num}]/data[1]/table[{table_idx}]"
            xml, err = run_xctrace(["export", "--input", str(trace_path),
                                    "--xpath", xpath])
            if err:
                log_lines.append(f"  run {run_num} {schema}: FAIL ({err})")
                fatal_failure = True
                continue
            rows = extract_rows(xml, spec["columns"])
            raw_rows_by_schema[schema] = rows

        if fatal_failure:
            return None

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(pickle.dumps({"raw_rows": raw_rows_by_schema}))

    per_schema_dfs = {}
    for schema, rows in raw_rows_by_schema.items():
        csv_name = config.SCHEMAS[schema]["csv_name"]
        per_schema_dfs[csv_name] = parse_schema(schema, rows)

    summary = summarize_run(per_schema_dfs)

    samples = {}
    for csv_name, df in per_schema_dfs.items():
        if len(df) == 0:
            continue
        tagged = df.copy()
        tagged.insert(0, "run", run_num)
        tagged.insert(0, "trace", trace_name)
        samples[csv_name] = tagged

    return {"summary": summary, "samples": samples}

def process_trace(trace_name: str) -> dict:
    log_lines = [f"=== {trace_name} ==="]
    trace_path = config.TRACES_DIR / f"{trace_name}.trace"

    if not trace_path.exists():
        log_lines.append(f"SKIP: {trace_path} not found")
        return _trace_result(trace_name, [], {}, log_lines, ok=False)

    cond = trace_to_condition(trace_name)

    try:
        toc = parse_toc(trace_path)
    except RuntimeError as e:
        log_lines.append(f"TOC failed: {e}")
        return _trace_result(trace_name, [], {}, log_lines, ok=False)

    summary_rows = []
    samples_by_schema: dict[str, list[pd.DataFrame]] = {}

    for run_num in sorted(toc.keys()):
        run_info = toc[run_num]
        if run_info["duration_s"] < config.MIN_RUN_DURATION_S:
            log_lines.append(f"  run {run_num}: SKIP "
                             f"({run_info['duration_s']:.1f}s < min)")
            continue

        result = extract_run(trace_path, trace_name, run_num,
                             run_info["schemas"], log_lines)
        if result is None:
            log_lines.append(f"  run {run_num}: FAILED, skipping")
            continue

        summary = {**cond, "run": run_num,
                   "run_duration_s": round(run_info["duration_s"], 1)}
        summary.update(result["summary"])
        summary_rows.append(summary)

        for csv_name, df in result["samples"].items():
            samples_by_schema.setdefault(csv_name, []).append(df)

        log_lines.append(f"  run {run_num}: OK")

    return _trace_result(trace_name, summary_rows, samples_by_schema,
                         log_lines, ok=True)

def _trace_result(trace_name, summaries, samples, log_lines, ok):
    log_dir = config.CACHE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{trace_name}.log").write_text("\n".join(log_lines))
    return {"trace": trace_name, "summaries": summaries,
            "samples": samples, "ok": ok, "n_runs": len(summaries)}

def main():
    args = sys.argv[1:]
    force = "--force" in args
    serial = "--serial" in args
    args = [a for a in args if not a.startswith("--")]

    if force and config.CACHE_DIR.exists():
        import shutil
        shutil.rmtree(config.CACHE_DIR)
        print("Cache cleared.")

    config.DATA_DIR.mkdir(exist_ok=True)
    config.CACHE_DIR.mkdir(exist_ok=True)

    traces = args if args else config.TRACE_NAMES
    print(f"Processing {len(traces)} trace(s): "
          f"{'parallel' if not serial else 'serial'} "
          f"({config.PARALLEL_WORKERS} workers)\n")

    all_summaries = []
    all_samples: dict[str, list[pd.DataFrame]] = {}
    start = time.time()

    if serial or len(traces) == 1:
        for t in traces:
            result = process_trace(t)
            _merge_result(result, all_summaries, all_samples)
    else:
        with ProcessPoolExecutor(max_workers=config.PARALLEL_WORKERS) as pool:
            futures = {pool.submit(process_trace, t): t for t in traces}
            for fut in as_completed(futures):
                result = fut.result()
                _merge_result(result, all_summaries, all_samples)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"Done in {elapsed/60:.1f} min. Writing outputs...")
    print('=' * 60)

    summary_df = pd.DataFrame(all_summaries).sort_values(["trace", "run"])
    summary_path = config.DATA_DIR / "run_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"  {summary_path}  ({len(summary_df)} runs)")

    file_kind = {
        "fps":      "samples_fps.csv",
        "activity": "samples_activity.csv",
        "sysmon":   "samples_sysmon.csv",
        "graphics": "samples_graphics.csv",
        "thermal":  "events_thermal.csv",
        "hangs":    "events_hangs.csv",
    }
    for csv_name, fname in file_kind.items():
        dfs = all_samples.get(csv_name, [])
        if not dfs:
            continue
        combined = pd.concat(dfs, ignore_index=True)
        path = config.DATA_DIR / fname
        combined.to_csv(path, index=False)
        print(f"  {path}  ({len(combined):,} rows)")

    print(f"\nLogs: {config.CACHE_DIR / 'logs'}/")

def _merge_result(result, all_summaries, all_samples):
    status = "OK" if result["ok"] else "FAIL"
    print(f"[{status}] {result['trace']}: {result['n_runs']} runs")
    all_summaries.extend(result["summaries"])
    for csv_name, dfs in result["samples"].items():
        all_samples.setdefault(csv_name, []).extend(dfs)

if __name__ == "__main__":
    main()