from pathlib import Path
import json
import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


def _flatten(records):
    flat = []
    for a in records:
        row = dict(a)
        for key in ("authors", "missing_metadata", "screening_inclusion_hits", "screening_exclusion_hits"):
            if isinstance(row.get(key), list):
                row[key] = "; ".join(str(x) for x in row[key])
        flat.append(row)
    return flat


def export_results(articles, screening_results, duplicates, stats, output_dir="outputs"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    def write_json(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    write_json("articles.json", articles)
    write_json("screening_results.json", screening_results)
    write_json("duplicates.json", duplicates)
    write_json("prisma_statistics.json", stats)

    df = pd.DataFrame(_flatten(screening_results))
    df.to_csv(out / "screening_results.csv", index=False, encoding="utf-8-sig")
    handoff = [x for x in screening_results if x.get("title_abstract_decision") != "exclude"]
    pd.DataFrame(_flatten(handoff)).to_csv(out / "part2_handoff.csv", index=False, encoding="utf-8-sig")

    # Editable human-review workbook: automated decision is preserved separately.
    review_rows = []
    for item in screening_results:
        review_rows.append({
            "Title": item.get("title", ""),
            "Authors": "; ".join(item.get("authors") or []),
            "Year": item.get("year", ""),
            "Publication type": item.get("type", ""),
            "DOI": item.get("doi", ""),
            "Abstract": item.get("abstract", ""),
            "Automated preliminary decision": item.get("title_abstract_decision", ""),
            "Automated reason": item.get("title_abstract_reason", ""),
            "PDF URL": item.get("pdf_url") or item.get("oa_url") or "",
            "Human decision (fill in)": "",
            "Reviewer notes": "",
        })
    review_path = out / "human_review.xlsx"
    pd.DataFrame(review_rows).to_excel(review_path, index=False, sheet_name="Human screening")
    wb = load_workbook(review_path)
    ws = wb["Human screening"]
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="244062")
    widths = {1: 55, 2: 30, 3: 10, 4: 22, 5: 24, 6: 70, 7: 28, 8: 65, 9: 45, 10: 24, 11: 50}
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width
    validation = DataValidation(type="list", formula1='"Include,Exclude,Unclear"', allow_blank=True)
    validation.error = "Choose Include, Exclude, or Unclear."
    validation.errorTitle = "Invalid human decision"
    ws.add_data_validation(validation)
    validation.add(f"J2:J{max(ws.max_row, 2)}")
    wb.save(review_path)
    return str(out.resolve())
