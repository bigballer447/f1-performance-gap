# Has the performance gap between Formula 1 cars shrunk?

MAT2007 — Introduction to Programming, final project.

**Research question:** Has the lap-time gap between the fastest and the slowest
car on the Formula 1 grid become smaller between 1996 and 2024? If yes, is
it because the cars converged, or because the slowest teams stopped entering?

For every race, the script takes the fastest lap each constructor set, and forms
two numbers from them:

```
full gap [%]  = 100 * (slowest best lap   - fastest best lap) / fastest best lap
trimmed  [%]  = 100 * (2nd slowest best lap - fastest best lap) / fastest best lap
```

The full gap measures how wide the grid is. The trimmed gap ignores the single
slowest constructor, so it measures how close the rest of the field is. If both
fall, the cars have converged and if only the full gap falls, the change is in the 
constructors who enter in the championship, not in the cars.

Season medians of both quantities are compared across eras and fitted with
straight lines.

## Result

The gap is not a smooth function of time. A linear fit over the whole period
gives a slope of −0.024 ± 0.026 percentage points per year, only 0.9σ from zero,
with χ²/ndf = 14.4. The reason is that the gap peaks in 2010–2016, the seasons
when HRT, Virgin/Marussia and Lotus/Caterham were on the grid far off the pace.

Comparing eras of similar grid composition:

| Mean season gap | 1996–2008 | 2010–2016 | 2017–2024 |
| --- | --- | --- | --- |
| Whole field | 4.00 ± 0.08 % | 4.88 ± 0.13 % | 3.39 ± 0.10 % |
| Slowest team excluded | 3.20 ± 0.06 % | 3.74 ± 0.10 % | 2.98 ± 0.08 % |

The whole field narrowed by 0.61 ± 0.13 % (4.7σ) between 1996–2008 and
2017–2024, but only 0.22 ± 0.11 % (2.1σ) of that survives when the slowest car
is removed. Most of the convergence is the disappearance of the slowest rider rather
than the remaining cars converging.

## Dataset

[Formula 1 World Championship (1950–2024)](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020)
on Kaggle, derived from the Ergast database.

Download the dataset, unzip it, and place these four files in a `data/` folder
next to the script:

```
data/lap_times.csv
data/results.csv
data/races.csv
data/constructors.csv
```

The data folder is deliberately not committed because it is too large for a
repository, and the link above is where to get it.

No manual cleaning is needed because the script discards lap times outside 30–300 s,
drops opening laps, and ignores any constructor that completed
fewer than 20 timed laps in a race. That is done so that a car which crashed early
cannot contribute a meaningless "best lap". After these limitations, 542 races remain.

Lap-by-lap timing only exists from 1996 onwards; that is why analysis does not start from 
1950.
## Dependencies

Python 3.9 or newer, with:

```bash
pip install pandas numpy matplotlib
```

## How to run

```bash
python f1_gap_analysis.py --data-dir data --out-dir figures
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

Era averages, the era comparison, and three linear fits (whole period, 1996–2009
and 2012–2024) are printed to the terminal. The files written are:

- `gap_trend.png` — season medians of both metrics, with the new-team era shaded (Figure 1 of the report)
- `gap_eras.png` — the 1996–2008 versus 2017–2024 comparison as two bars
- `race_gaps.csv` — both gaps, plus the fastest and slowest team, for every race
- `season_gaps.csv` — season medians of the full gap, with uncertainties
- `season_gaps_trimmed.csv` — the same for the trimmed gap

## Report

`report.tex` is the LaTeX source of the two-page report; compile it with
pdfLaTeX on Overleaf. It needs `gap_trend.png` in the same folder, so run the
script first. `report.pdf` is the compiled version.
