from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TRACES_DIR = PROJECT_ROOT
DATA_DIR = PROJECT_ROOT / "data"

TRACE_NAMES = [
    "cross_mb_02min", "cross_mb_05min",
    "cross_ml_02min", "cross_ml_05min",
    "native_mb_02min", "native_mb_05min",
    "native_ml_02min", "native_ml_05min",
]

FRAMEWORK_MAP = {"cross": "Unity", "native": "Xcode"}
AR_MODE_MAP   = {"mb": "Markerbased", "ml": "Markerless"}
DURATION_MAP  = {"02min": "2 min", "05min": "5 min"}

RUNS_PER_TRACE = 10
MIN_RUN_DURATION_S = 60

SCHEMAS = {
    "core-animation-fps-estimate": {
        "csv_name": "fps",
        "columns": ["interval", "_period", "fps", "device-utilization"],
    },
    "device-thermal-state-intervals": {
        "csv_name": "thermal",
        "columns": ["start", "duration", "_end", "thermal-state",
                    "_track-label", "_is-induced", "_narrative"],
    },
    "potential-hangs": {
        "csv_name": "hangs",
        "columns": ["start", "duration", "hang-type", "_thread", "_process"],
    },
    "activity-monitor-process-live": {
        "csv_name": "activity",
        "columns": [
            "start",                        #  1
            "_process",                     #  2
            "_responsible-process",         #  3
            "_duration",                    #  4
            "_pid",                         #  5
            "_uid",                         #  6
            "cpu-percent",                  #  7
            "_cpu-total",                   #  8
            "thread-count",                 #  9
            "_mach-port-count",             # 10
            "memory-physical-footprint",    # 11
            "_memory-real",                 # 12
            "_memory-real-private",         # 13
            "_memory-real-shared",          # 14
            "_arch-kind",                   # 15
            "_sudden-termination",          # 16
            "_sandbox",                     # 17
            "_restricted",                  # 18
            "_idle-wakeups",                # 19
            "_app-nap",                     # 20
            "_memory-purgeable",            # 21
            "_memory-compressed",           # 22
            "_disk-bytes-written",          # 23
            "_disk-bytes-read",             # 24
            "_disk-bytes-written-per-second",  # 25
            "_disk-bytes-read-per-second",  # 26
            "_preventing-sleep",            # 27
        ],
    },
    "sysmon-process": {
        "csv_name": "sysmon",
        "columns": [
            "time",                       #  1
            "_process",                   #  2
            "_recently-died",             #  3
            "_arch-kind",                 #  4
            "_sudden-termination",        #  5
            "_sandbox",                   #  6
            "_restricted",                #  7
            "_app-nap",                   #  8
            "_context-switch",            #  9
            "_cpu-percent",               # 10
            "_cpu-total-system",          # 11
            "_cpu-total-user",            # 12
            "_disk-bytes-read",           # 13
            "_disk-bytes-written",        # 14
            "_faults",                    # 15
            "_interrupt-wakeups",         # 16
            "_mach-port-count",           # 17
            "_memory-physical-footprint", # 18
            "memory-anonymous",           # 19
            "_memory-compressed",         # 20
            "_memory-purgeable",          # 21
            "_memory-real-private",       # 22
            "_memory-real-shared",        # 23
            "_memory-resident-size",      # 24
            "_memory-virtual-size",       # 25
            "_msg-received",              # 26
            "_msg-sent",                  # 27
            "_pgid",                      # 28
            "_ppid",                      # 29
            "_pid",                       # 30
            "_proc-status",               # 31
            "_responsible-pid",           # 32
            "_sys-calls-mach",            # 33
            "_sys-calls-unix",            # 34
            "_thread-count",              # 35
            "_uid",                       # 36
            "_vm-page-ins",               # 37
            "_parent-process",            # 38
            "_responsible-process",       # 39
        ],
    },
    "graphics-statistic": {
        "csv_name": "graphics",
        "columns": ["timestamp", "stat", "value", "_driver"],
    },
}

GRAPHICS_STATS_KEEP = {
    "Device Utilization %":  "gpu_device_util_percent",
    "In use system memory":  "gpu_in_use_sys_mem_bytes",
}

XCTRACE_MAX_RETRIES = 5
XCTRACE_RETRY_SLEEP_S = 2

PARALLEL_WORKERS = 4

CACHE_DIR = PROJECT_ROOT / ".export_cache"