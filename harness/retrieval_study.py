from __future__ import annotations

import importlib.util
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from .retrieval_benchmark import _search_backend, load_retrieval_judgments, run_retrieval_benchmark


def run_retrieval_study(judgments: Path, *, include_hybrid: bool = False,
                        chunk_strategy: str = "python", repeats: int = 3,
                        search_functions: dict | None = None) -> dict[str, Any]:
    if not 1 <= repeats <= 20:
        raise ValueError("repeats must be between 1 and 20")
    spec = load_retrieval_judgments(judgments)
    corpus = (judgments.resolve().parent / spec["corpus_root"]).resolve()
    available = search_functions is not None or importlib.util.find_spec("sentence_transformers") is not None
    missing = ["hybrid"] if include_hybrid and not available else []
    orders = [["lexical", "hybrid"], ["hybrid", "lexical"]] if include_hybrid and available else [["lexical"]]
    rows = []
    with tempfile.TemporaryDirectory(prefix="mini-agent-retrieval-study-") as temporary:
        for order_index, order in enumerate(orders):
            for backend in order:
                quality = run_retrieval_benchmark(
                    judgments, backend=backend,
                    backend_options={"chunk_strategy": chunk_strategy,
                                     "cache_dir": Path(temporary) / f"quality-{order_index}"},
                    search_fn=search_functions.get(backend) if search_functions else None,
                )
                samples = []
                for case in spec["cases"]:
                    cache = Path(temporary) / str(order_index) / backend / case["case_id"]
                    search = (search_functions[backend] if search_functions else _search_backend(
                        backend, {"chunk_strategy": chunk_strategy, "cache_dir": cache}))
                    measurements = []
                    observations = []
                    for _ in range(repeats + 1):
                        started = time.perf_counter()
                        result = search(corpus, case["query"], glob_pattern=spec.get("glob", "*"),
                                        chunk_lines=spec.get("chunk_lines", 40),
                                        overlap=spec.get("overlap", 5), limit=5)
                        measurements.append((time.perf_counter() - started) * 1000)
                        observations.append((result.get("hybrid") or {}).get("cache", {}))
                    samples.append({"case_id": case["case_id"], "cold_ms": measurements[0],
                                    "warm_median_ms": statistics.median(measurements[1:]),
                                    "cold_cache": observations[0], "last_warm_cache": observations[-1]})
                rows.append({"order": order_index, "backend": backend, "quality": quality["summary"],
                             "cold_median_ms": statistics.median(item["cold_ms"] for item in samples),
                             "warm_median_ms": statistics.median(item["warm_median_ms"] for item in samples),
                             "samples": samples})
    return {"schema_version": 1, "chunk_strategy": chunk_strategy, "warm_repeats": repeats,
            "execution_orders": orders, "unavailable_backends": missing, "rows": rows,
            "counterbalanced_complete": include_hybrid and not missing,
            "measurement_scope": "Full retrieval calls; cold=empty document embedding cache, not OS/model cold. Lexical rebuilds its index on every call. Quality pass preloads the model before timing; cache paths are fresh per case/order. Filesystem caches remain uncontrolled.",
            "claim_boundary": "Small public offline fixture; timings are local observations, not agent gains or an SLA."}
