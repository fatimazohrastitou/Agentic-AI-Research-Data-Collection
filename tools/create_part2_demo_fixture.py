"""Create a minimal Part 1-like output folder so Part 2 can be demonstrated offline."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEMO_TOPIC = "Cybersecurity in IoT"
DEMO_QUESTION = "What security threats and mitigation techniques are studied for IoT systems?"


def _records() -> list[dict]:
    return [
        {
            "openalex_id": "https://openalex.org/WDEMO1",
            "doi": "10.1000/demo.iot.security.1",
            "title": "Threat modelling and mitigation patterns for consumer IoT devices",
            "year": 2022,
            "authors": ["Alice Example", "Bob Researcher"],
            "type": "article",
            "abstract": (
                "This study analyses cybersecurity threats in Internet of Things deployments "
                "and evaluates mitigation techniques including encryption, authentication and "
                "network segmentation. We review experimental IoT testbeds and report reduced "
                "attack surface after applying layered controls."
            ),
            "title_abstract_decision": "potentially_include",
            "title_abstract_reason": "Demo fixture: inclusion keywords matched.",
            "is_oa": True,
            "pdf_url": "",
            "full_text": (
                "Abstract. This study analyses cybersecurity threats in Internet of Things deployments "
                "and evaluates mitigation techniques including encryption, authentication and network "
                "segmentation.\n\nIntroduction. IoT systems expand the attack surface of homes and "
                "industry. Threat modelling is required before controls are selected.\n\nMethodology. "
                "We conducted an experimental evaluation on a 40-device testbed (n=40) using simulated "
                "network attacks and measured detection rate.\n\nResults. Layered authentication and "
                "TLS encryption reduced successful intrusions by 62%. Network segmentation limited "
                "lateral movement.\n\nDiscussion. Findings support defence-in-depth for consumer IoT. "
                "Limitations include lab-only traffic and no randomised clinical-style allocation.\n\n"
                "Conclusion. Encryption, strong authentication and segmentation are effective mitigation "
                "techniques against common IoT threats.\n\nReferences. Example references omitted."
            ),
            "sections": {
                "abstract": {"text": "This study analyses cybersecurity threats in Internet of Things deployments."},
                "methodology": {"text": "Experimental evaluation on a 40-device testbed (n=40)."},
                "results": {"text": "Layered authentication and TLS encryption reduced successful intrusions by 62%."},
                "conclusion": {"text": "Encryption, authentication and segmentation mitigate common IoT threats."},
            },
            "pdf_parse_status": "parsed",
            "human_review_required": True,
            "screening_is_final": False,
        },
        {
            "openalex_id": "https://openalex.org/WDEMO2",
            "doi": "10.1000/demo.iot.security.2",
            "title": "A survey of intrusion detection systems for industrial IoT",
            "year": 2021,
            "authors": ["Carla Scholar"],
            "type": "review",
            "abstract": (
                "We survey intrusion detection systems (IDS) for industrial IoT, comparing signature "
                "and anomaly-based methods, datasets, and reported detection performance."
            ),
            "title_abstract_decision": "potentially_include",
            "title_abstract_reason": "Demo fixture: review on IDS for IIoT.",
            "full_text": (
                "Abstract. Survey of intrusion detection systems for industrial IoT.\n\n"
                "Introduction. Industrial IoT networks require continuous monitoring.\n\n"
                "Methodology. Systematic search of IDS literature; narrative comparison of 28 systems.\n\n"
                "Results. Anomaly-based IDS dominate recent work; few studies share open datasets. "
                "Machine learning detectors report high accuracy but limited external validity.\n\n"
                "Conclusion. IDS is a core mitigation technique, yet benchmarking remains inconsistent.\n\n"
                "References. Omitted."
            ),
            "sections": {
                "methodology": {"text": "Systematic search; narrative comparison of 28 systems."},
                "results": {"text": "Anomaly-based IDS dominate; limited open datasets."},
                "conclusion": {"text": "IDS is a core mitigation technique for industrial IoT."},
            },
            "pdf_parse_status": "parsed",
            "human_review_required": True,
            "screening_is_final": False,
        },
        {
            "openalex_id": "https://openalex.org/WDEMO3",
            "doi": "10.1000/demo.iot.security.3",
            "title": "Editorial: notes on smart home marketing",
            "year": 2020,
            "authors": ["Dana Editor"],
            "type": "article",
            "abstract": "Marketing commentary without empirical cybersecurity evaluation.",
            "title_abstract_decision": "uncertain",
            "title_abstract_reason": "Demo fixture: weak relevance.",
            "full_text": (
                "This editorial discusses smart home marketing claims and consumer adoption. "
                "No security experiment or threat analysis is presented."
            ),
            "pdf_parse_status": "abstract_only",
            "human_review_required": True,
            "screening_is_final": False,
        },
    ]


def create_fixture(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = _records()
    protocol = {
        "topic": DEMO_TOPIC,
        "research_question": DEMO_QUESTION,
        "objective": f"Identify studies on {DEMO_TOPIC}.",
        "methodology": "Systematic literature review demo fixture.",
        "guideline": "PRISMA 2020",
        "sources": ["OpenAlex"],
        "inclusion_criteria": ["iot", "security", "threat", "mitigation", "intrusion"],
        "exclusion_criteria": ["marketing", "editorial commentary"],
        "date_range": {"from": 2018, "to": 2024},
        "document_types": {
            "accepted_by_default": ["article", "review", "proceedings-article", "book-chapter"],
            "exclude": ["letter", "editorial"],
        },
        "screening_policy": "Automated screening is preliminary; uncertain decisions require human review.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "demo-fixture-1.0",
    }
    prisma = {
        "records_identified": 5,
        "duplicates_removed": 1,
        "records_after_deduplication": 4,
        "records_screened_title_abstract": 4,
        "excluded_title_abstract_preliminary": 1,
        "potentially_include_preliminary": 2,
        "uncertain_preliminary": 1,
        "needs_human_review": 3,
        "note": "Demo fixture statistics for Part 2 offline run.",
    }

    (output_dir / "research_protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "prisma_statistics.json").write_text(
        json.dumps(prisma, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "part2_handoff.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "pdf_acquisition_results.json").write_text("[]", encoding="utf-8")

    review_rows = []
    for item in records:
        human = ""
        if "Threat modelling" in item["title"]:
            human = "Include"
        elif "Editorial" in item["title"]:
            human = "Exclude"
        review_rows.append({
            "Title": item.get("title", ""),
            "Authors": "; ".join(item.get("authors") or []),
            "Year": item.get("year", ""),
            "Publication type": item.get("type", ""),
            "DOI": item.get("doi", ""),
            "Abstract": item.get("abstract", ""),
            "Automated preliminary decision": item.get("title_abstract_decision", ""),
            "Automated reason": item.get("title_abstract_reason", ""),
            "PDF URL": "",
            "Human decision (fill in)": human,
            "Reviewer notes": "Demo fixture decision",
        })
    pd.DataFrame(review_rows).to_excel(output_dir / "human_review.xlsx", index=False, sheet_name="Human screening")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="outputs/demo_cybersecurity_in_iot",
        help="Folder to create as a Part 1-compatible handoff",
    )
    args = parser.parse_args()
    path = create_fixture(Path(args.output_dir))
    print("Demo fixture created:", path.resolve())
    print("Next: python main_part2.py --output-dir", path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
