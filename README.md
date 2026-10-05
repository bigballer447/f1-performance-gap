# Has the performance gap between Formula 1 cars shrunk?

MAT2007 — Introduction to Programming, final project.

**Research question:** has the lap-time gap between the fastest and the slowest
car on the Formula 1 grid become smaller between 1996 and 2024?

For every race, the script takes the fastest lap each constructor set, and
measures the relative difference between the slowest and the fastest of those:

```
gap [%] = 100 * (slowest best lap - fastest best lap) / fastest best lap
```

Season medians of this quantity are fitted with a straight line to obtain the
trend and its uncertainty.

## Dataset

[Formula 1 World Championship (1950–2024)](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020)
on Kaggle, derived from the Ergast database. About 40 MB.

Download the dataset, unzip it, and place these four files in a `data/` folder
next to the script:

```
data/lap_times.csv
data/results.csv
data/races.csv
data/constructors.csv
```

No manual cleaning is needed — the script filters invalid lap times, opening
laps, and cars that completed too few laps to have a meaningful best lap.
Lap-by-lap timing only exists from 1996 onwards, which is why the analysis does
not go back to 1950.

## Dependencies

Python 3.9 or newer, with:

```bash
pip install pandas numpy matplotlib
```

## How to run

```bash
python3 f1_gap_analysis.py --data-dir data --out-dir figures
```

Options:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--data-dir` | `data` | folder containing the four CSV files |
| `--out-dir` | `figures` | where plots and tables are written |
| `--start-year` | `1996` | first season analysed |
| `--end-year` | `2024` | last season analysed |
| `--min-laps` | `20` | timed laps a constructor must complete to count in a race |

Runtime is roughly 10–20 seconds on a laptop.

## Output

Written to the output folder:

- `gap_trend.png` — gap per race, season medians, and the fitted trend (Figure 1 of the report)
- `gap_eras.png` — mean gap of the first five seasons versus the last five
- `race_gaps.csv` — the gap, fastest team and slowest team for every race
- `season_gaps.csv` — season medians and their uncertainties

The fitted slope, its uncertainty and its significance are printed to the
terminal.

## Report

`report.tex` is the LaTeX source of the two-page report; compile it with
pdfLaTeX on Overleaf. It expects `figures/gap_trend.png` to exist, so run the
script first.
