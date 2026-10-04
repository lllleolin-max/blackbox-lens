"""A self-contained escaped static report. No scripts or external assets."""
from __future__ import annotations

from html import escape


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def render_html(report: dict) -> str:
    manifest, counts = report["manifest"], report["counts"]
    suite = manifest["suite"]
    kind_rows = "".join("<tr>" + "".join(f"<td>{_e(value)}</td>" for value in (
        kind, c["planned"], c["observed"], c["valid"], c["invalid"], c["errors"], c["missing"],
        c["correct"], _percent(c["strict_accuracy"]), _percent(c["valid_accuracy"]))) + "</tr>"
        for kind, c in report["by_kind"].items())
    pair_rows = "".join("<tr>" + "".join(f"<td>{_e(value)}</td>" for value in (
        kind, p["planned_pairs"], p["observed_pairs"], p["valid_pairs"], p["excluded_pairs"],
        _percent(p["invariance"]), _percent(p["flip_rate"]), p["correct_to_incorrect"],
        p["incorrect_to_correct"], p["both_correct"], p["both_incorrect"])) + "</tr>"
        for kind, p in report["comparisons"].items())
    repeat_rows = "".join("<tr>" + "".join(f"<td>{_e(value)}</td>" for value in (
        kind, r["eligible_conditions"], r["conditions_with_disagreement"], r["planned_repeat_pairs"],
        r["valid_repeat_pairs"], r["disagreeing_repeat_pairs"], _percent(r["disagreement_rate"]))) + "</tr>"
        for kind, r in report["repeat_consistency"].items())
    trial_rows = "".join("<tr>" + "".join(f"<td>{_e(value)}</td>" for value in (
        r["order"], r["trial_id"], r["status"], r["raw"] if r["raw"] is not None else "—",
        r["semantic_answer"] or "—", r["expected"], r["correct"], r["error"] or "—")) + "</tr>"
        for r in report["trials"])
    conditions = "".join(f"<details><summary>{_e(c['id'])} · {_e(v['id'])} · {_e(v['kind'])}</summary>"
                          f"<p>Expected semantic answer: <b>{_e(c['expected'])}</b></p>"
                          f"<p>Label → semantic answer: {_e(v['answer_map'])}</p>"
                          f"<pre>{_e(v['prompt'])}</pre></details>"
                          for c in suite["cases"] for v in c["variants"])
    synthetic = manifest["adapter"].get("kind") == "synthetic"
    warning = ("SYNTHETIC DEMO · The fixture reads expected answers and plants biases. "
               "These are not measurements of any language model." if synthetic else
               "OBSERVED BEHAVIOR · Results describe this suite, backend and run only.")
    cards = "".join(f"<div class='card'><span>{_e(label)}</span><strong>{_e(value)}</strong></div>" for label, value in (
        ("Correct / planned", f"{counts['correct']} / {counts['planned']}"),
        ("Strict accuracy", _percent(counts["strict_accuracy"])),
        ("Valid responses", f"{counts['valid']} / {counts['planned']}"),
        ("Missing slots", counts["missing"])))
    import json
    provenance = _e(json.dumps({k: v for k, v in manifest.items() if k not in {"suite", "order"}},
                              ensure_ascii=False, indent=2))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{_e(suite['title'])} — Blackbox Lens</title><style>
:root{{color-scheme:light;--ink:#10232d;--muted:#506873;--line:#cbd8da;--green:#006b65}}
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7f4;color:var(--ink);font:15px/1.65 system-ui,sans-serif}}
main{{max-width:1280px;margin:auto;padding:48px 28px 80px}}.brand{{font-size:12px;letter-spacing:.18em;color:var(--green);font-weight:700}}
h1{{font-size:clamp(32px,5vw,55px);line-height:1.12;margin:18px 0}}h2{{font-size:23px;margin:38px 0 12px}}p{{max-width:100ch}}
.note{{border-left:4px solid var(--green);background:#e4efea;padding:15px 20px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:26px 0}}
.card{{background:white;border:1px solid var(--line);padding:20px}}.card span{{display:block;color:var(--muted)}}.card strong{{font-size:32px}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;background:white;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid var(--line);padding:11px 12px;vertical-align:top;overflow-wrap:anywhere}}
th{{background:#e5ede9;white-space:nowrap}}td{{max-width:340px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:white;border:1px solid var(--line);padding:18px;font-size:13px}}
details{{border-top:1px solid var(--line);padding:12px 0}}summary{{cursor:pointer;font-weight:600}}.sub{{color:var(--muted)}}footer{{margin-top:36px;color:var(--muted);font-size:13px}}
</style></head><body><main><div class="brand">BLACKBOX LENS / BEHAVIORAL LAB</div>
<h1>{_e(suite['title'])}</h1><p class="sub">{_e(suite['description'])}</p>
<p class="note">{_e(warning)} Run is <b>{'complete' if report['complete'] else 'INCOMPLETE'}</b>.</p>
<div class="cards">{cards}</div>
<h2>Response coverage and accuracy</h2><p>Strict accuracy = correct / planned slots; invalid, error and missing slots are unsuccessful. Valid accuracy = correct / valid responses. Observed = valid + invalid + errors. N/A means no eligible denominator.</p>
<div class="scroll"><table><thead><tr><th>Condition</th><th>Planned</th><th>Observed</th><th>Valid</th><th>Invalid</th><th>Errors</th><th>Missing</th><th>Correct</th><th>Strict accuracy</th><th>Valid accuracy</th></tr></thead><tbody>{kind_rows}</tbody></table></div>
<h2>Paired baseline contrasts</h2><p>Each variant is paired with the same case and repeat's baseline. Invariance = same semantic answer / valid pairs; flip rate = changed semantic answer / valid pairs. Both answers must be valid. Invariance can include two incorrect answers. Excluded pairs contain an invalid, error or missing response. A baseline may be reused across conditions; these are dependent descriptive counts.</p>
<div class="scroll"><table><thead><tr><th>Condition</th><th>Planned pairs</th><th>Observed pairs</th><th>Valid pairs</th><th>Excluded</th><th>Invariance</th><th>Flip rate</th><th>Correct → incorrect</th><th>Incorrect → correct</th><th>Both correct</th><th>Both incorrect</th></tr></thead><tbody>{pair_rows}</tbody></table></div>
<h2>Repeat consistency</h2><p>Within each case and variant, compare all pairs of valid repeated answers. Eligible conditions have at least two valid responses. Repeated prompts and pairs are dependent; no confidence interval, causal explanation or generalization is implied. The presentation seed changes order only, not the provider's random seed.</p>
<div class="scroll"><table><thead><tr><th>Condition</th><th>Eligible conditions</th><th>Disagreeing conditions</th><th>Planned repeat pairs</th><th>Valid repeat pairs</th><th>Disagreeing pairs</th><th>Disagreement</th></tr></thead><tbody>{repeat_rows}</tbody></table></div>
<h2>Raw observations</h2><p>Only surrounding whitespace is stripped before exact label lookup. No answer extraction, case folding or fuzzy matching. Every planned slot appears below; raw response text is retained up to the documented bound.</p>
<div class="scroll"><table><thead><tr><th>Order</th><th>Case / variant / repeat</th><th>Status</th><th>Raw response</th><th>Semantic answer</th><th>Expected</th><th>Correct</th><th>Error</th></tr></thead><tbody>{trial_rows}</tbody></table></div>
<h2>Declared conditions</h2><p>Suite authors must verify the meaning and ground truth remain equivalent. The tool validates structure and mapping, not semantic equivalence of prose.</p>{conditions}
<h2>Provenance</h2><pre>{provenance}</pre>
<footer>Blackbox Lens · Bounded output comparisons, not recovery of hidden reasoning. Prompts and outputs may contain private data; review artifacts before sharing. This report uses no scripts, external fonts or network assets.</footer>
</main></body></html>"""
