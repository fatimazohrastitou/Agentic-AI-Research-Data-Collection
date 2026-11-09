import argparse
from workflow.research_pipeline import run_pipeline

def main():
    p = argparse.ArgumentParser(description="Part 1 - Generic Research & Literature Acquisition Pipeline")
    p.add_argument("--topic", required=True)
    p.add_argument("--question", default="")
    p.add_argument("--max-results", type=int, default=100)
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--include", nargs="*", default=[])
    p.add_argument("--exclude", nargs="*", default=[], help="Words/phrases to flag in title or abstract")
    p.add_argument("--include-types", nargs="*", default=[], help="Allowed OpenAlex publication types (optional allow-list)")
    p.add_argument("--exclude-types", nargs="*", default=["letter", "editorial"], help="Publication types to exclude, e.g. letter editorial")
    p.add_argument("--download-pdfs", action="store_true", help="Download only OpenAlex-marked open-access PDF URLs")
    p.add_argument("--output-dir", default=None)
    a = p.parse_args()
    kwargs = dict(topic=a.topic, research_question=a.question, max_results=a.max_results,
        year_from=a.year_from, year_to=a.year_to, inclusion_criteria=a.include,
        exclusion_criteria=a.exclude, include_types=a.include_types,
        exclude_types=a.exclude_types, download_pdfs=a.download_pdfs)
    if a.output_dir:
        kwargs["output_dir"] = a.output_dir
    r = run_pipeline(**kwargs)
    print("\n=== PART 1 COMPLETED ===")
    print("Topic:", a.topic)
    print("Retrieved:", r["statistics"]["records_identified"])
    print("After deduplication:", r["statistics"]["records_after_deduplication"])
    print("Output folder:", r["output_dir"])
    print("Statistics:", r["statistics"])

if __name__ == "__main__":
    main()
