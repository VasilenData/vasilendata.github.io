# CV source and rebuild

Both public CVs are generated from `cv_data.json`, which keeps employment dates, titles, contact details and shared achievements consistent. The Data Engineer version selects batch, streaming and scheduled pipeline projects. The Analytics Engineer version selects the finance mart, scheduled dbt pipeline and batch platform.

Each company has a total tenure and, where applicable, dated `roles` in reverse chronological order. The bullets belong to the company tenure; do not assign them to an earlier role unless their timing is known. Gosian's October 2026 cash-flow launch occurred during the CRO role, with continued hands-on data engineering. Keep the same role dates in the portfolio, GitHub profile and LinkedIn.

From the repository root:

```sh
python -m pip install reportlab pypdf
python tools/build_cv.py
```

For embedded Arial fonts, pass `--font-dir` with a directory containing `arial.ttf` and `arialbd.ttf`. Without it, the builder uses standard PDF Helvetica fonts. Font metrics can differ, so inspect the rendered PDFs after rebuilding.

The builder checks that each file is one page, that key facts remain extractable, and that every contact/project link is clickable. It fails on missing text or replacement characters. Visual review is still required before publishing: check both pages for clipping, spacing and readable text.

Keep the portfolio demonstrations distinct from professional experience. Only add metrics, technologies or role claims that can be supported; record new benchmark conditions in the project repository rather than treating a single runtime as a universal guarantee.
