# open-data-change-detector
A tool that watches a handful of open datasets and alerts you when something changes unexpectedly. Each run it fetches a dataset, records a small “fingerprint” (columns, row count, content hash, fetch status), compares it with the last run, and raises an alert if something looks wrong.
