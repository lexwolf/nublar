#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


AFM_PRIOR_DIR = Path("data/input/optimal/afm_priors")
CAMPAIGN_ROOT = Path("data/output/tests/mmgm_single_fixed_proxy_campaign")
PRIOR_PATTERN = "mmgm_single_*.json"
POPULATION_SIZE = 36


@dataclass(frozen=True)
class PriorInfo:
    path: Path
    radius_proxy_name: str
    strategy_name: str


@dataclass(frozen=True)
class ResultInfo:
    result_dir: Path
    prior_file: str
    radius_proxy_name: str
    strategy_name: str
    mode: str

    @property
    def proxy_aware_name(self) -> str:
        return (
            f"{self.radius_proxy_name}__{self.strategy_name}"
            f"__{self.mode}_pop_{POPULATION_SIZE}"
        )


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse JSON {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit(f"Expected object in {path}")
    return raw


def required_string(mapping: dict[str, Any], key: str, source: Path) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"Missing string field {key!r} in {source}")
    return value


def read_prior_info(path: Path) -> PriorInfo:
    raw = load_json(path)
    source = raw.get("source")
    strategy = raw.get("strategy")
    if not isinstance(source, dict):
        raise SystemExit(f"Missing object field 'source' in {path}")
    if not isinstance(strategy, dict):
        raise SystemExit(f"Missing object field 'strategy' in {path}")
    return PriorInfo(
        path=path,
        radius_proxy_name=required_string(source, "radius_proxy_name", path),
        strategy_name=required_string(strategy, "name", path),
    )


def read_priors() -> list[PriorInfo]:
    priors = [read_prior_info(path) for path in sorted(AFM_PRIOR_DIR.glob(PRIOR_PATTERN))]
    if not priors:
        raise SystemExit(f"No AFM prior files found matching {AFM_PRIOR_DIR / PRIOR_PATTERN}")
    return priors


def result_metadata(path: Path) -> tuple[str, str, str, str]:
    raw = load_json(path)
    afm_priors = raw.get("afm_priors")
    if not isinstance(afm_priors, dict):
        raise SystemExit(f"Missing object field 'afm_priors' in {path}")
    source = afm_priors.get("source")
    strategy = afm_priors.get("strategy")
    if not isinstance(source, dict):
        raise SystemExit(f"Missing object field 'afm_priors.source' in {path}")
    if not isinstance(strategy, dict):
        raise SystemExit(f"Missing object field 'afm_priors.strategy' in {path}")
    return (
        required_string(afm_priors, "path", path),
        required_string(source, "radius_proxy_name", path),
        required_string(strategy, "name", path),
        required_string(afm_priors, "mode", path),
    )


def read_result_info(result_dir: Path) -> ResultInfo | None:
    json_files = sorted(result_dir.glob("gen_*/seed_*/mmgm_single/spheres/global_result.json"))
    if not json_files:
        return None

    first = result_metadata(json_files[0])
    for path in json_files[1:]:
        current = result_metadata(path)
        if current != first:
            raise SystemExit(
                f"Inconsistent AFM metadata in {result_dir}: "
                f"{json_files[0]} has {first}, {path} has {current}"
            )
    prior_file, radius_proxy_name, strategy_name, mode = first
    return ResultInfo(
        result_dir=result_dir,
        prior_file=prior_file,
        radius_proxy_name=radius_proxy_name,
        strategy_name=strategy_name,
        mode=mode,
    )


def read_results() -> list[ResultInfo]:
    if not CAMPAIGN_ROOT.exists():
        return []
    results: list[ResultInfo] = []
    for path in sorted(CAMPAIGN_ROOT.iterdir()):
        if not path.is_dir():
            continue
        info = read_result_info(path)
        if info is not None:
            results.append(info)
    return results


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        if rows
        else len(headers[index])
        for index in range(len(headers))
    ]
    print(", ".join(headers))
    for row in rows:
        print(", ".join(row[index].ljust(widths[index]) for index in range(len(row))))
    print()


def create_proxy_alias(result: ResultInfo) -> str:
    desired = CAMPAIGN_ROOT / result.proxy_aware_name
    source = result.result_dir
    if desired == source:
        return "already proxy-aware"
    if desired.exists() or desired.is_symlink():
        if desired.is_symlink() and desired.resolve() == source.resolve():
            return "existing symlink"
        return f"exists, left unchanged: {desired}"
    try:
        os.symlink(source.name, desired, target_is_directory=True)
        return f"created symlink: {desired}"
    except OSError:
        shutil.copytree(source, desired, symlinks=True)
        return f"created copy: {desired}"


def write_audit_csv(results: list[ResultInfo], alias_actions: dict[str, str]) -> Path:
    path = CAMPAIGN_ROOT / "proxy_audit.csv"
    columns = [
        "result_dir",
        "prior_file",
        "radius_proxy_name",
        "strategy_name",
        "mode",
        "proxy_aware_name",
        "alias_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "result_dir": result.result_dir.as_posix(),
                    "prior_file": result.prior_file,
                    "radius_proxy_name": result.radius_proxy_name,
                    "strategy_name": result.strategy_name,
                    "mode": result.mode,
                    "proxy_aware_name": (CAMPAIGN_ROOT / result.proxy_aware_name).as_posix(),
                    "alias_action": alias_actions[result.result_dir.as_posix()],
                }
            )
    return path


def write_audit_report(
    priors: list[PriorInfo],
    results: list[ResultInfo],
    alias_actions: dict[str, str],
) -> Path:
    available_proxies = sorted({prior.radius_proxy_name for prior in priors})
    tested_proxies = sorted(
        {result.radius_proxy_name for result in results if result.mode == "fixed"}
    )
    missing_proxies = sorted(set(available_proxies) - set(tested_proxies))

    lines = ["=== FIXED-AFM PROXY CAMPAIGN AUDIT ===", ""]
    lines.append("AFM prior inputs:")
    for prior in priors:
        lines.append(
            f"- {prior.path.as_posix()}: "
            f"{prior.radius_proxy_name}, strategy={prior.strategy_name}"
        )
    lines.append("")

    lines.append("Completed fixed campaign outputs:")
    for result in results:
        lines.append(
            f"- {result.result_dir.as_posix()}: "
            f"{result.radius_proxy_name}, strategy={result.strategy_name}, "
            f"mode={result.mode}, prior={result.prior_file}"
        )
    lines.append("")

    lines.append("Proxy-aware aliases:")
    for result in results:
        lines.append(
            f"- {result.result_dir.as_posix()} -> "
            f"{(CAMPAIGN_ROOT / result.proxy_aware_name).as_posix()}: "
            f"{alias_actions[result.result_dir.as_posix()]}"
        )
    lines.append("")

    lines.append("Already tested fixed-mode proxies:")
    if tested_proxies:
        lines.extend(f"- {proxy}" for proxy in tested_proxies)
    else:
        lines.append("- none")
    lines.append("")

    lines.append("Missing fixed-mode proxies:")
    if missing_proxies:
        lines.extend(f"- {proxy}" for proxy in missing_proxies)
    elif len(available_proxies) == 1:
        lines.append(
            "- none. Only one radius proxy prior is currently available; "
            "no alternative proxy JSONs exist yet."
        )
    else:
        lines.append("- none")
    lines.append("")

    path = CAMPAIGN_ROOT / "proxy_audit_report.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    priors = read_priors()
    results = read_results()
    CAMPAIGN_ROOT.mkdir(parents=True, exist_ok=True)

    print_table(
        ["prior_file", "radius_proxy_name", "strategy_name"],
        [
            [
                prior.path.as_posix(),
                prior.radius_proxy_name,
                prior.strategy_name,
            ]
            for prior in priors
        ],
    )
    print_table(
        ["result_dir", "prior_file", "radius_proxy_name", "strategy_name", "mode"],
        [
            [
                result.result_dir.as_posix(),
                result.prior_file,
                result.radius_proxy_name,
                result.strategy_name,
                result.mode,
            ]
            for result in results
        ],
    )

    alias_actions = {
        result.result_dir.as_posix(): create_proxy_alias(result)
        for result in results
    }
    csv_path = write_audit_csv(results, alias_actions)
    report_path = write_audit_report(priors, results, alias_actions)
    print(f"Wrote {csv_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
