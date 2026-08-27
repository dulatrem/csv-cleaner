# CSV Cleaner — Event-Driven Serverless Data Pipeline

An event-driven pipeline that automatically cleans messy institutional CSV files. Upload a messy CSV to an S3 bucket's `input/` folder, and an AWS Lambda function is automatically triggered to clean and standardize the data, writing the result to the `output/` folder. Built to demonstrate serverless, event-driven architecture, as opposed to scheduled (cron-based) pipelines.

## Architecture

```
file uploaded to s3://bucket/input/<filename>.csv
              │
              ▼
   S3 ObjectCreated event triggers Lambda
              │
              ▼
   Lambda reads the CSV, cleans each row
              │
              ▼
   writes cleaned CSV to s3://bucket/output/cleaned_<filename>.csv
```

The S3 event notification is filtered to the `input/` prefix. This ensures the Lambda's own writes to `output/` do not re-trigger it, preventing an infinite invocation loop.

## Data Quality Issues Handled

The cleaner addresses seven categories of messy data:

1. **Case numbers** — reformats to a standard `PF-####-#####` mask regardless of missing or misplaced dashes.
2. **Honorifics** — normalizes variants (`Hon`/`Honor` → `Hon.`, `Dr`/`Doctor` → `Dr.`) and extracts them when glued into name fields.
3. **Names** — splits combined full-name fields into first/last name.
4. **Roles** — normalizes casing and spacing to a canonical set of role titles.
5. **Departments** — normalizes punctuation/spacing and resolves abbreviations (`BMC` → Boston Municipal Court, `PFC` → Probate & Family Court) via an alias map.
6. **Emails** — strips stray whitespace.
7. **Status** — translates the `ZZZZ` sentinel value to `inactive`.

## Synthetic Data & Validation

`generate_data.py` uses [Faker](https://faker.readthedocs.io/) to generate 1,000 clean records plus a deliberately-messy copy, saving both `clean_truth.csv` (a ground-truth answer key) and `messy_input.csv`. The cleaner is validated by running it on the messy data and comparing the result against the ground truth, achieving 1000/1000 exact matches. This synthetic approach avoids the need to use real institutional data, preserving privacy.

## Project Structure

| File | Purpose |
|---|---|
| `generate_data.py` | Synthetic data generator |
| `cleaner.py` | Cleaning functions |
| `lambda_function.py` | Lambda handler |
| `test_cleaner.py` | Unit tests |

## Setup & Deployment

**Local setup and validation:**

1. Create a Python virtual environment and install the requirements (`pip install -r requirements.txt`).
2. Run `generate_data.py` to create test data (`clean_truth.csv` and `messy_input.csv`).
3. Run `pytest` to validate the cleaning functions against the unit test suite.

**AWS deployment:**

1. Zip `lambda_function.py` and `cleaner.py` into a deployment package.
2. Create the Lambda function from the package, attaching an AWS-managed pandas layer for the `pandas` dependency.
3. Create an S3 bucket for the pipeline.
4. Configure an S3 event notification on the `input/` prefix to invoke the Lambda function on object creation.

## Tech Stack

- Python
- pandas
- AWS Lambda
- Amazon S3
- boto3
- Faker
- pytest
