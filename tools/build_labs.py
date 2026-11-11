"""Render the capability hub from checked-in evidence; no model training or network access."""
from __future__ import annotations

import html
import json
from pathlib import Path

from verify_labs import check_service_evidence

ROOT = Path(__file__).resolve().parents[1]
LABS = ROOT / "labs"
GITHUB = "https://github.com/VasilenData/"


def esc(value):
    return html.escape(str(value), quote=True)


def read(relative):
    return json.loads((LABS / relative).read_text(encoding="utf-8"))


def page(title, eyebrow, lead, body, *, hub=False):
    stylesheet = "lab.css" if hub else "../lab.css"
    nav = '<a href="../">Portfolio</a>' if hub else '<a href="../">Evidence hub</a><a href="../../">Portfolio</a>'
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="theme-color" content="#111315"><title>{esc(title)} | Vasilen Kanchev</title>'
            f'<link rel="stylesheet" href="{stylesheet}"></head><body><main><nav aria-label="Main">{nav}'
            '<a href="https://github.com/VasilenData">GitHub</a></nav>'
            f'<p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(title)}</h1><p class="lede">{esc(lead)}</p>{body}'
            '<footer>Vasilen Kanchev · Public-data projects, built and reviewed with AI assistance. '
            'No independent human review, employer deployment or business impact is implied by these demonstrations.</footer>'
            '</main></body></html>\n')


def table(headers, rows):
    return ('<div class="scroll"><table><thead><tr>' + ''.join(f'<th scope="col">{esc(h)}</th>' for h in headers)
            + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def stats(items):
    return '<div class="stats">' + ''.join(f'<div class="card"><strong class="stat">{esc(value)}</strong><p>{esc(label)}</p></div>' for value, label in items) + '</div>'


def links(items):
    return '<div class="filelinks">' + ''.join(f'<a href="{esc(url)}">{esc(label)}</a>' for label, url in items) + '</div>'


def bullets(items):
    return '<ul>' + ''.join(f'<li>{esc(item)}</li>' for item in items) + '</ul>'


def build():
    check_service_evidence(ROOT)
    experiment, churn, search, management = [read(f'{name}/report.json') for name in ('experimentation', 'churn', 'search', 'management')]
    forecast, future, gate, service = read('forecast/report.json'), read('customer-value/report.json'), read('evaluation/latest.json'), read('service-status.json')
    booking = read('service/report.json')
    if service['deployment_verified'] and (not service.get('public_url') or not service.get('verified_at')):
        raise ValueError('verified deployment requires a public URL and verification timestamp')
    primary = experiment['metrics'][experiment['protocol']['primary']]
    body = stats([(f"{experiment['participants']:,}", 'assigned players in the public Cookie Cats dataset'),
                  (f"{primary['diff'] * 100:.2f} pp", 'day-7 retention difference: treatment minus control'), ('Retain control', 'primary outcome worsens under the declared rule')])
    body += '<p class="scope"><strong>Retrospective analysis.</strong> The decision protocol was specified after historical results were known. It is not a preregistered experiment. Exposure events and assignment timestamps are unavailable.</p>'
    rows = [(name.replace('_', ' '), f"{r['p_a']:.2%}", f"{r['p_b']:.2%}", f"{r['diff'] * 100:.2f} pp",
             f"{r['ci_low'] * 100:.2f} to {r['ci_high'] * 100:.2f} pp") for name, r in experiment['metrics'].items()]
    body += '<h2>The decision and its guardrails</h2>' + table(['Metric', 'Gate 30', 'Gate 40', 'Difference', 'Simultaneous interval'], rows)
    body += (f"<p>Bonferroni family α={experiment['protocol']['alpha']:.2f} across the primary and guardrail metrics. The day-1 guardrail allows at most a one-percentage-point decline; the evidence does not establish that guardrail. The primary already supports retaining control.</p>"
             f"<p>Sample-ratio p={experiment['srm']['p_value']:.4f}: below the 0.05 warning level, above the configured {experiment['srm']['alarm_threshold']:.3f} alarm. Allocation integrity still needs the experiment owner's investigation.</p>")
    body += '<h2>What the implementation checks</h2>' + bullets(['One unique participant per declared assignment; no silent deduplication or unknown arms.', 'Exposure events, when supplied, require known IDs, matching arms and valid time order. They never filter the intention-to-treat denominator.', 'Declared analysis cutoffs reject later assignments and exposures. The public dataset cannot establish observation-window maturity.', 'A complete JSON/HTML/checksum release publishes together. Failed publication preserves prior releases.'])
    body += links([('Full report and provenance', 'report.json'), ('Protocol, tests and source', GITHUB + 'ab-test-analysis')])
    (LABS / 'experimentation/index.html').write_text(page('From an experiment to a defensible decision', 'Experimentation / 90,189 public participants', 'A reproducible assignment-to-decision workflow with explicit primary metrics, guardrails and missing evidence.', body), encoding='utf-8', newline='\n')

    body = stats([(f"{churn['test_roc_auc']:.4f}", 'ROC-AUC on the fixed held-out split'), (f"{churn['test_brier']:.4f}", 'Brier score; lower is better'), (f"{churn['test_rows']:,}", 'held-out customers with retained predictions')])
    body += '<p class="scope"><strong>Previously inspected random split.</strong> This bounded rerun evaluates logistic candidates on the IBM sample. It is not a new blind or temporal test, and it does not regenerate the historical forest comparison.</p>'
    body += '<h2>What changed in the evaluation</h2>' + bullets(['Each outer held-out customer is excluded from model selection, fitting and isotonic calibration for their probability.', 'Unique customer IDs, fold membership and OOF probabilities are retained. Duplicate customers fail before splitting.', 'The final policy is fitted on training OOF outcomes and assessed on 1,409 held-out customers. OOF policy-fit utility is not an unbiased policy estimate.'])
    body += table(['Frozen policy', 'Observed value'], [('Selected model', churn['selected_model']), ('Training-selected threshold', f"{churn['threshold']:.4f}"), ('Contacted test customers', churn['contacted_test_customers']), ('Source customers', f"{churn['rows']:,}")])
    body += '<h2>What this does not establish</h2>' + bullets(churn['limits'])
    body += links([('Report, assumptions and hashes', 'report.json'), ('Every held-out prediction', 'heldout_predictions.csv'), ('Fold audit, code and tests', GITHUB + 'customer-churn-model'), ('Separate temporal retail study', '../customer-value/')])
    (LABS / 'churn/index.html').write_text(page('Customer risk without leaking its label', 'Customer retention / nested evaluation', 'Model selection, calibration and policy fitting are separate from the observations used to assess the final policy.', body), encoding='utf-8', newline='\n')

    body = stats([(search['initial']['documents'], 'real technical documents'), ('4 formats', 'text, Markdown, HTML and JSON'), ('Atomic updates', 'one SQLite transaction for content, postings and deletion')])
    body += '<p class="scope"><strong>Source-informed smoke queries, not a blind quality benchmark.</strong> The four queries were authored with AI assistance after inspecting the source documentation. They have no independent human review.</p>'
    rows = [(r['query'], r['expected_source'], 'Found in top 5 chunks' if r['expected_in_top5_chunks'] else 'Absent from top 5', f"{r['seconds'] * 1000:.3f} ms") for r in search['queries']]
    body += '<h2>Inspect the observed retrieval</h2>' + table(['Question', 'Expected source', 'Observed result', 'Local query time'], rows)
    body += '<p class="muted">One local query measurement per smoke case; no concurrency or production latency claim. No external APIs or LLM generation were used. CPU, electricity and hosting costs are unpriced.</p>'
    body += '<h2>Update, delete, recover</h2>' + bullets(['Collection/path identities remain stable while source and chunk hashes change with content.', 'Unchanged files reuse postings; changed documents and deletions commit together.', 'A labelled synthetic interruption after writes and before commit preserved the old snapshot for an independent reader.', 'Malformed documents, excessive input, scope changes and unconfirmed empty collections fail closed.'])
    body += '<h2>Scope</h2>' + bullets(search['limits'])
    body += links([('Queries, rankings, source commits and recovery evidence', 'report.json'), ('Document CLI and historical SQuAD evaluation', GITHUB + 'rag-retrieval-eval')])
    (LABS / 'search/index.html').write_text(page('Search that survives changing documents', 'Domain search / local document lifecycle', 'A small technical knowledge base with bounded ingestion, stable identities, incremental indexing and transactional deletion.', body), encoding='utf-8', newline='\n')

    current, previous, change = management['current'], management['previous'], management['month_over_month']['changes']['net_product_revenue']
    body = stats([(f"£{current['net_product_revenue']:,.0f}", 'net product revenue, November 2011'), (f"{change['relative_change']:+.1%}", 'change versus October 2011'), (f"{current['orders']:,}", 'distinct sale invoices in November 2011')])
    body += '<p class="scope"><strong>Historical decision support.</strong> These are 2009–2011 public retailer transactions, not current trading or my employer revenue. The latest complete month is November 2011; partial boundary months are excluded.</p>'
    body += '<h2>What moved</h2>' + table(['Metric', 'November 2011', 'October 2011'], [(label, f"£{current[key]:,.2f}", f"£{previous[key]:,.2f}") for label, key in [('Gross product sales', 'gross_sales'), ('Product returns', 'returns'), ('Net product revenue', 'net_product_revenue'), ('Average order value', 'avg_order_value')]])
    drivers = management['drivers']
    body += (f"<p>Net revenue increased by £{drivers['net_revenue_change']:,.2f}. The arithmetic decomposition attributes £{drivers['order_volume_effect']:,.2f} of gross-sales change to order volume and £{drivers['basket_value_effect']:,.2f} to basket value, plus £{drivers['returns_change']:,.2f} from less-negative returns. These reconcile to the net change; they are descriptive contributions, not causes.</p>")
    body += '<h2>Decisions require more than a revenue chart</h2>'
    for action in management['proposed_actions']:
        body += f"<details><summary>{esc(action['action'])}</summary><p><strong>Evidence:</strong> {esc(action['evidence'])}</p><p><strong>Still needed:</strong> {esc(action['data_needed'])}</p><p>{esc(action['decision_rule'])}</p></details>"
    body += '<h2>Definitions and limits</h2>' + bullets(management['limitations'])
    body += links([('Full metrics, countries and provenance', 'report.json'), ('Management brief', 'management.md'), ('Finance source and release checks', GITHUB + 'ecommerce-finance-mart'), ('Customer prediction study', '../customer-value/')])
    (LABS / 'management/index.html').write_text(page('Revenue movement, explained before action', 'Finance analytics / historical management brief', 'Reconciled product revenue, order and basket contributions, and proposed decisions with the missing information made explicit.', body), encoding='utf-8', newline='\n')

    learned, booking_baseline = booking['test_metrics']['lightgbm'], booking['test_metrics']['baseline']
    booking_improvement = 1 - learned['mae_min'] / booking_baseline['mae_min']
    body = stats([(f"{learned['mae_min']:.3f} min", 'June held-out mean absolute error'),
                  (f"{booking_improvement:.1%} lower", 'MAE versus the training-only median baseline'),
                  (f"{learned['rows']:,}", 'held-out eligible trips in the bounded June sample')])
    body += '<p class="scope"><strong>Booking-time inputs, retrospective evaluation.</strong> The model uses pickup/drop-off zones, hour, weekday and passenger count. Realized trip distance is excluded from prediction inputs. Completed-trip eligibility still uses realized fare, distance and duration, so this evaluates eligible trips rather than all booking requests.</p>'
    body += '<h2>Separate fitting, selection, calibration and assessment</h2>'
    body += table(['Phase', 'Months', 'Sampled trips'], [(phase.title(), ', '.join(booking['phases'][phase]),
                  f"{sum(row['sample_rows'] for row in booking['sources'][phase]):,}") for phase in ('train', 'validation', 'calibration', 'test')])
    body += '<h2>Error and uncertainty</h2>' + table(['Model', 'MAE', 'Observed coverage', 'Mean interval width'],
                  [(name, f"{row['mae_min']:.3f} min", f"{row['coverage']:.1%}", f"{row['mean_interval_width_min']:.2f} min") for name, row in booking['test_metrics'].items()])
    body += '<p>The central interval targets 80% coverage and calibrates on May. Coverage is assessed on June; it is not guaranteed under time shift. The baseline uses training-only route medians with hour/global fallbacks.</p>'
    body += f'<h2>Operating status</h2><p><strong>{esc(service["status"])}.</strong> {esc(service["description"])}</p>'
    if service['deployment_verified']:
        observed = read('service/deployment-evidence.json')['observation']
        probe = read(observed['report_path'].removeprefix('labs/'))
        body += f'<p>Observed at {esc(probe["observed_at_utc"])}. Four sequential requests checked health, readiness, model identity and a booking prediction without distance. All returned HTTP 200 and passed the {probe["latency_budget_ms_per_request"] / 1000:g}-second per-request budget.</p>'
        body += '<p class="muted">One observation is not an uptime history, throughput test, latency percentile or SLA. The trial may expire or pause; cold starts and future availability can differ. No ongoing hosting-cost claim is made.</p>'
        body += links([('Try the API / docs', service['docs_url']), ('Readiness endpoint', service['public_url'] + '/ready'),
                       ('Dated deployment evidence', 'deployment-evidence.json'), ('Exact HTTP observation', Path(observed['report_path']).name),
                       ('Probe workflow', observed['workflow_run_url'])])
    body += '<h2>Limits</h2>' + bullets(booking['limitations'])
    body += links([('Protocol, metrics and source hashes', 'report.json'),
                  ('Every held-out prediction (gzip CSV)', GITHUB + 'taxi-eta-service/blob/main/reports/booking-2023-h1/predictions_test.csv.gz'),
                  ('Route/hour/passenger slices', GITHUB + 'taxi-eta-service/blob/main/reports/booking-2023-h1/slices.csv'),
                  ('Service, model and tests', GITHUB + 'taxi-eta-service')])
    (LABS / 'service/index.html').write_text(page('Trip duration before the ride', 'Prediction service / booking-time features', 'A new chronological evaluation separates model choice, interval calibration and future assessment, with every held-out prediction retained.', body), encoding='utf-8', newline='\n')

    chosen = forecast['evaluation']['test'][forecast['evaluation']['selected_model']]
    baseline = forecast['evaluation']['test']['seasonal_naive']
    improvement = 1 - chosen['mae'] / baseline['mae']
    aucs = [r['roc_auc'] for r in future['test_windows']]
    cards = [
        ('Experiment decisions', 'Retrospective decision protocol', f"{experiment['participants']:,} assigned players · {primary['diff'] * 100:.2f} pp primary effect", 'Assignment/exposure contracts, declared primary and guardrail metrics, and atomic report publication. Missing timestamps remain unavailable.', [('Decision report', 'experimentation/'), ('Source', GITHUB + 'ab-test-analysis')]),
        ('Customer retention & future value', 'Temporal retail study + nested churn rerun', f"{min(aucs):.3f}–{max(aucs):.3f} future-window AUC · {churn['test_roc_auc']:.4f} churn AUC", 'Point-in-time retail features and baseline comparisons; a separate churn workflow cross-fits selection and calibration. No retention uplift or lifetime-profit claim.', [('Retail study', 'customer-value/'), ('Churn evaluation', 'churn/'), ('Source', GITHUB + 'ecommerce-finance-mart')]),
        ('Demand & capacity planning', 'Historical next-day replay', f"{improvement:.1%} lower MAE · {chosen['rows']:,} held-out zone-days", 'Six complete TLC months, seasonal baseline, temporal model selection and interval checks. Capacity is hypothetical; monthly public files cannot operate live dispatch.', [('Forecast report', 'forecast/'), ('Source', GITHUB + 'nyc-taxi-data-platform')]),
        ('Financial decision support', 'Reconciled historical retailer data', f"£{current['net_product_revenue']/1_000_000:.2f}m net product revenue · November 2011", 'A management brief decomposes movement into order, basket and return contributions, then lists what is still needed before acting. Revenue is not profit.', [('Management brief', 'management/'), ('Source', GITHUB + 'ecommerce-finance-mart')]),
        ('Prediction service operations', service['status'], f"{learned['mae_min']:.3f}-minute MAE · {booking_improvement:.1%} below the baseline", 'Booking-time features, four chronological phases and retained paired predictions on 200,000 held-out trips. ' + service['description'], [('Booking evaluation', 'service/'), ('Source', GITHUB + 'taxi-eta-service')] + ([('API / docs', service['docs_url'])] if service['deployment_verified'] else [])),
        ('Domain search & RAG', 'Local lifecycle + historical retrieval benchmark', f"{search['initial']['documents']} real documents · four formats · transactional updates", 'Stable identities, bounded ingestion, incremental indexing and deletion with recovery evidence. Query authorship, latency scope and unpriced local costs are explicit.', [('Search evidence', 'search/'), ('Source', GITHUB + 'rag-retrieval-eval')]),
        ('AI regression evaluation', 'Measured retrieval release gate', f"{gate['candidate']['tasks']} paired tasks · deliberate regression rejected", 'Quality, latency, API-fee and error budgets preserve the last passing publication. Full-generation evidence now publishes atomically; no new LLM quality result is claimed.', [('Release gate', 'evaluation/'), ('Source', GITHUB + 'research-assistant-eval')]),
    ]
    body = '<p class="scope">Seven connected capabilities, with the measured result and operating scope beside each one. The main portfolio and CVs remain focused on Data Engineer and Analytics Engineer roles.</p><div class="grid">'
    for number, (title, tag, proof, description, destinations) in enumerate(cards, 1):
        body += f'<article class="card" id="capability-{number}"><span class="tag">{number:02d} / {esc(tag)}</span><h2>{esc(title)}</h2><p class="evidence">{esc(proof)}</p><p>{esc(description)}</p><div class="links">'
        body += ''.join(f'<a href="{esc(url)}">{esc(label)}</a>' for label, url in destinations) + '</div></article>'
    body += '</div><h2>How to read this evidence</h2>' + bullets(['Historical benchmarks, new measured runs and synthetic recovery exercises are labelled separately.', 'No generated questions or AI-assisted review are presented as independent human gold.', 'A working repository or local service does not establish production operation, business impact or independent interview performance.'])
    body += links([('Mirrored artifact hashes', 'source-manifest.json'), ('Three selected Data Engineer projects', '../vasilen-kanchev-cv.pdf'), ('Three selected Analytics Engineer projects', '../vasilen-kanchev-cv-analytics.pdf')])
    (LABS / 'index.html').write_text(page('Evidence behind the work', 'Seven capabilities / inspect the result and its limits', 'From assignment and raw data to decisions, predictions, search and safe releases. Each report links to the code and the observations that support it.', body, hub=True), encoding='utf-8', newline='\n')
    print('Built capability hub and five evidence viewers from recorded JSON; no benchmarks rerun.')


if __name__ == '__main__':
    build()
