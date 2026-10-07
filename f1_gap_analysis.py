
From 1996 onwards take for each constructor, the single fastest lap that any
of its cars set in that race.  Using them, build two numbers per race:

    full gap [%]  = 100 * (slowest best lap - fastest best lap) / fastest
    trimmed [%]   = the same, but ignoring the single slowest constructor

The full gap answers "how wide is the grid?"
The trimmed gap answers "how close are the cars once the one backmarker is set aside?"
Races are aggregated into seasons with the median (robust against wet races and
safety-car events).  Because the field spread is not a straight line in time, 
three new teams entered in 2010 and left by 2017, the script reports era
averages as well as linear fits over the whole period and over sub-periods.

Data
----
Formula 1 World Championship (1950-2024), Ergast/Jolpica database, published on
Kaggle:  https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020

Files used:  lap_times.csv, results.csv, races.csv, constructors.csv

Usage
-----
    python f1_gap_analysis.py --data-dir data --out-dir figures
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # write files instead of opening a window
import matplotlib.pyplot as plt



ERA_EARLY = (1996, 2008)
ERA_NEW_TEAMS = (2010, 2016)
ERA_LATE = (2017, 2024)


# 1. Loading
def load_data(data_dir: Path) -> dict:
    """Read the four CSV files we need and return them in a dictionary."""
    needed = {
        "lap_times": ["raceId", "driverId", "lap", "milliseconds"],
        "results": ["raceId", "driverId", "constructorId"],
        "races": ["raceId", "year", "round", "name"],
        "constructors": ["constructorId", "name"],
    }

    tables = {}
    for stem, columns in needed.items():
        path = data_dir / f"{stem}.csv"
        if not path.exists():
            sys.exit(f"Missing file: {path}\nDownload the dataset first (see README.md).")
        tables[stem] = pd.read_csv(path, usecols=columns)

    return tables


# 2. Cleaning
def build_lap_table(tables: dict, start_year: int, end_year: int) -> pd.DataFrame:
    """Join laps to constructors and seasons, and drop what we cannot use."""
    laps = tables["lap_times"]
    races = tables["races"]
    results = tables["results"]
    constructors = tables["constructors"]

    # Which car did each driver drive in each race?  results.csv is the only
    # place that links (raceId, driverId) to a constructor.
    entries = results[["raceId", "driverId", "constructorId"]].drop_duplicates()

    laps = laps.merge(entries, on=["raceId", "driverId"], how="inner")
    laps = laps.merge(races[["raceId", "year", "round", "name"]], on="raceId", how="inner")
    laps = laps.merge(
        constructors.rename(columns={"name": "constructor"}), on="constructorId", how="inner"
    )

    # lap times only exist from 1996 onwards.
    laps = laps[(laps["year"] >= start_year) & (laps["year"] <= end_year)]

    # A handful of rows have missing or absurd times; a Formula 1 lap is never
    # under 30 s and a lap over 5 min means a red flag or a car limping home.
    laps["milliseconds"] = pd.to_numeric(laps["milliseconds"], errors="coerce")
    laps = laps.dropna(subset=["milliseconds"])
    laps = laps[(laps["milliseconds"] > 30_000) & (laps["milliseconds"] < 300_000)]

    # The opening lap starts from a standing start and is never representative.
    laps = laps[laps["lap"] > 1]

    return laps


# 3. The metrics

def constructor_best_laps(laps: pd.DataFrame, min_laps: int) -> pd.DataFrame:
    """Fastest lap per constructor per race, for constructors that really raced."""
    grouped = laps.groupby(["year", "raceId", "name", "constructor"])

    best = grouped.agg(
        best_ms=("milliseconds", "min"),
        n_laps=("milliseconds", "size"),
    ).reset_index()

    # A car that crashed on lap 3 has a meaningless "best lap": require that the
    # constructor completed a reasonable number of timed laps in that race.
    return best[best["n_laps"] >= min_laps]


def race_gaps(best: pd.DataFrame, min_constructors: int = 5) -> pd.DataFrame:
    """Full and trimmed percentage gaps for each race."""
    rows = []
    for (year, race_id, race_name), group in best.groupby(["year", "raceId", "name"]):
        if len(group) < min_constructors:
            continue

        times = group["best_ms"].sort_values().to_numpy()
        fastest = times[0]

        # Dropping the last entry removes the single slowest constructor.
        trimmed = 100.0 * (times[-2] - fastest) / fastest

        rows.append(
            {
                "year": year,
                "raceId": race_id,
                "race": race_name,
                "n_constructors": len(group),
                "fastest_team": group.loc[group["best_ms"].idxmin(), "constructor"],
                "slowest_team": group.loc[group["best_ms"].idxmax(), "constructor"],
                "gap_pct": 100.0 * (times[-1] - fastest) / fastest,
                "gap_trimmed_pct": trimmed,
            }
        )

    return pd.DataFrame(rows).sort_values(["year", "raceId"]).reset_index(drop=True)


def season_summary(gaps: pd.DataFrame, column: str) -> pd.DataFrame:
    """Median of one gap column per season, with the uncertainty on that median."""
    out = gaps.groupby("year")[column].agg(
        median_gap="median", spread="std", n_races="size"
    ).reset_index()

    # Standard error of a median is about 1.25 * sigma / sqrt(n).
    out["error"] = 1.253 * out["spread"] / np.sqrt(out["n_races"])
    return out


# 4. Trends and era averages
def fit_trend(seasons: pd.DataFrame, first_year=None, last_year=None) -> dict:
    """Weighted straight-line fit of the season medians against the year."""
    data = seasons
    if first_year is not None:
        data = data[data["year"] >= first_year]
    if last_year is not None:
        data = data[data["year"] <= last_year]

    x = data["year"].to_numpy(dtype=float)
    y = data["median_gap"].to_numpy(dtype=float)
    err = data["error"].to_numpy(dtype=float)

    good = err[np.isfinite(err) & (err > 0)]
    fallback = good.mean() if good.size else 1.0
    err = np.where(np.isfinite(err) & (err > 0), err, fallback)

    if len(x) < 3:
        return {}

    coeffs, cov = np.polyfit(x, y, deg=1, w=1.0 / err, cov=True)
    slope, intercept = coeffs
    slope_err = np.sqrt(cov[0, 0])

    residuals = y - (slope * x + intercept)
    chi2 = float(np.sum((residuals / err) ** 2))
    ndf = len(x) - 2

    return {
        "first_year": int(x.min()),
        "last_year": int(x.max()),
        "slope": float(slope),
        "slope_err": float(slope_err),
        "intercept": float(intercept),
        "significance": float(abs(slope) / slope_err) if slope_err else float("nan"),
        "chi2_per_ndf": chi2 / ndf if ndf > 0 else float("nan"),
    }


def era_average(seasons: pd.DataFrame, era: tuple) -> dict:
    """Inverse-variance weighted mean of the season medians inside one era."""
    block = seasons[(seasons["year"] >= era[0]) & (seasons["year"] <= era[1])]
    block = block[np.isfinite(block["error"]) & (block["error"] > 0)]

    if block.empty:
        return {}

    weights = 1.0 / block["error"] ** 2
    mean = float((block["median_gap"] * weights).sum() / weights.sum())
    error = float(1.0 / np.sqrt(weights.sum()))

    return {"label": f"{era[0]}-{era[1]}", "mean": mean, "error": error, "n_seasons": len(block)}


def compare(first: dict, second: dict) -> dict:
    """Difference between two era averages, with its uncertainty."""
    if not first or not second:
        return {}

    difference = first["mean"] - second["mean"]
    error = np.sqrt(first["error"] ** 2 + second["error"] ** 2)

    return {
        "difference": float(difference),
        "error": float(error),
        "significance": float(abs(difference) / error) if error else float("nan"),
    }


# 5. Plots
def plot_trend(full, trimmed, out_path: Path) -> None:
    """Season medians of both metrics, with the new-teams era shaded."""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    ax.axvspan(
        ERA_NEW_TEAMS[0] - 0.5,
        ERA_NEW_TEAMS[1] + 0.5,
        color="#d9d9d9",
        alpha=0.55,
        label="HRT / Virgin / Caterham on the grid",
    )

    ax.errorbar(
        full["year"], full["median_gap"], yerr=full["error"],
        fmt="o-", color="#c0392b", capsize=3, linewidth=1.4,
        label="whole field",
    )
    ax.errorbar(
        trimmed["year"], trimmed["median_gap"], yerr=trimmed["error"],
        fmt="s--", color="#2c6fbb", capsize=3, linewidth=1.4,
        label="slowest team excluded",
    )

    ax.set_xlabel("Season")
    ax.set_ylabel("Lap time gap to the fastest car [%]")
    ax.set_title("Formula 1 field spread, best race lap per constructor")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_eras(early, late, delta, out_path: Path) -> None:
    """The headline like-for-like comparison, as two bars."""
    if not early or not late or not delta:
        return

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(
        [early["label"], late["label"]],
        [early["mean"], late["mean"]],
        yerr=[early["error"], late["error"]],
        capsize=6, color=["#5b8ff9", "#e07a5f"], width=0.55,
    )
    ax.set_ylabel("Mean season gap [%]")
    ax.set_title(
        f"$\\Delta$ = {delta['difference']:.2f} $\\pm$ {delta['error']:.2f} %"
        f"  ({delta['significance']:.1f}$\\sigma$)"
    )
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# 6. Main
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--out-dir", type=Path, default=Path("figures"))
    parser.add_argument("--start-year", type=int, default=1996)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument(
        "--min-laps",
        type=int,
        default=20,
        help="timed laps a constructor must complete to count in a race",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    tables = load_data(args.data_dir)
    laps = build_lap_table(tables, args.start_year, args.end_year)
    best = constructor_best_laps(laps, args.min_laps)
    gaps = race_gaps(best)

    if gaps.empty:
        sys.exit("No races survived the selection; check the data directory.")

    full = season_summary(gaps, "gap_pct")
    trimmed = season_summary(gaps, "gap_trimmed_pct")

    gaps.to_csv(args.out_dir / "race_gaps.csv", index=False)
    full.to_csv(args.out_dir / "season_gaps.csv", index=False)
    trimmed.to_csv(args.out_dir / "season_gaps_trimmed.csv", index=False)

    plot_trend(full, trimmed, args.out_dir / "gap_trend.png")

    print(f"Races analysed:   {len(gaps)}")
    print(f"Seasons covered:  {full['year'].min():.0f}-{full['year'].max():.0f}")

    for name, seasons in (("WHOLE FIELD", full), ("SLOWEST TEAM EXCLUDED", trimmed)):
        print(f"\n--- {name} ---")

        early = era_average(seasons, ERA_EARLY)
        middle = era_average(seasons, ERA_NEW_TEAMS)
        late = era_average(seasons, ERA_LATE)

        for block in (early, middle, late):
            if block:
                print(f"  {block['label']}:  {block['mean']:.2f} +/- {block['error']:.2f} %"
                      f"   ({block['n_seasons']} seasons)")

        delta = compare(early, late)
        if delta:
            print(f"  {ERA_EARLY[0]}-{ERA_EARLY[1]} minus {ERA_LATE[0]}-{ERA_LATE[1]}: "
                  f"{delta['difference']:.2f} +/- {delta['error']:.2f} % "
                  f"({delta['significance']:.1f} sigma)")

        for label, fit in (
            ("whole period", fit_trend(seasons)),
            ("1996-2009   ", fit_trend(seasons, last_year=2009)),
            ("2012-2024   ", fit_trend(seasons, first_year=2012)),
        ):
            if fit:
                print(f"  slope {label}: {fit['slope']:+.4f} +/- {fit['slope_err']:.4f} "
                      f"%-pts/year ({fit['significance']:.1f} sigma, "
                      f"chi2/ndf = {fit['chi2_per_ndf']:.1f})")

        if name == "WHOLE FIELD":
            plot_eras(early, late, delta, args.out_dir / "gap_eras.png")


if __name__ == "__main__":
    main()
