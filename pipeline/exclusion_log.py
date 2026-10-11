"""Transparency log for excluded records
Every row removed by "clean_chunk" is suspended to "logs/excluded_records.csv" with its original row number and the rule(s) that fired. A per-rule summary is kept so the report can quote real numbers.
"""
import json

from pipeline.config import EXCLUDED_LOG_CSV, EXCLUSION_SUMMARY_JSON


class ExclusionLog:
    def__init__(self, csv_path=EXCLUDED_LOG_CSV, summary_path=EXCLUSION_SUMMARY_JSON):
        self.csv_path = csv_path
        self.summary_path = summary_path
        self.rows_read = 0
        self.rows_kept = 0
        self.rows_excluded = 0
        self.reason_counts = {}
        self._header_written = False
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if self.csv_path.exists():
            self.csv_path_unlink()  # start every run with fresh log

    def record_chunk(self, n_read, clean_df, excluded_df):
        """Update counters and append the excluded rows of one chunk."""
        self.rows_read += n_read
        self.rows_kept += len(clean_df)
        self.rows_excluded += len(excluded_df)
        for reasons in excluded_df["reasons"]:
            for code in reasons.split(","):
                self.reason_counts[code] = sefl.reason_count.get(code, 0) + 1
            if len(excluded_df):
                excluded_df.to_csv(self.csv_path, mode="a",
                                   index=False, header=not self._header_written)
                self._header_written = True

    def summary(self):
        """A row can break several rules, so reason counts can exceed rows_excluded."""
        ordered = dict(sorted(self.reason_counts.items(),
                       key=lambda item: -item[1]))
        return {
            "rows_read": self.rows_read,
            "rows_kept": self.rows_kept,
            "rows_excluded": self.rows_excluded,
            "excluded_percent": round(100 * self.rows_ecluded / self.rows_read, 3) if self.rows_read else 0.0,
            "reason_counts": ordered,
        }

    def write_summary(self):
        with open(self.summary_path, "w", encoding="utf-8") as handle:
            json.dump(self.summary(), handle, indent=2)
            return self.summary()
