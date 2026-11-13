# CV source and build

The two one-page CVs share factual source data in `cv_data.json`. Each variant has its own headline, summary, three selected projects and portfolio skills.

The layout adapts the single-column structure of [Jake's Resume](https://github.com/jakegut/resume) to a Python/ReportLab renderer. It uses a centered contact header, aligned role dates, restrained section rules and hanging bullets. The MIT attribution is in `TEMPLATE_NOTICE.txt`.

## Build

Install `reportlab` and `pypdf`, then run from the repository root:

```sh
python tools/build_cv.py --font-dir C:/Windows/Fonts
```

The renderer requires and embeds Calibri regular, bold and italic TTF files. Supply your own licensed font directory if building elsewhere; the repository does not redistribute the font files. Font substitution can alter wrapping, so the build reports missing fonts instead of silently substituting a different layout.

Optional `--source` and `--output-dir` arguments allow a separate source file or preview directory. Default output files are `vasilen-kanchev-cv.pdf` and `vasilen-kanchev-cv-analytics.pdf` at the repository root.

## Verification

The build checks one page per variant, extractable role titles and promotion dates, key factual text, three projects per variant, and all contact/project link annotations. It fails rather than reducing the body font if content exceeds one page.

Render both PDFs and inspect them before publishing. Check spacing, wrapping, legibility, page boundaries and contact/project destinations; successful text extraction alone does not establish visual quality or guarantee ATS compatibility.

Keep professional and portfolio tools separate. Preserve qualifiers such as `estimated`, the October 2026 cash-flow go-live date and each project's evidence scope. The three selected projects are Meterwork, NYC Taxi and Finance Mart. Meterwork's 24-account reconciliation is a synthetic local PostgreSQL exercise, not hosted traffic. NYC's 12 November 2026 measurement includes the current publisher; source-change exercises use 30,000 sample rows. Finance's retail data is historical public data, while its operational events and subscription extensions are synthetic. Formatting edits are not evidence of new experience or independent technical performance.
