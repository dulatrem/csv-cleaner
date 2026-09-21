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

This pipeline runs as an AWS Lambda function triggered by S3 uploads. The steps
below deploy it from scratch. Replace the placeholder values with your own:

| Placeholder | Meaning | Example |
|---|---|---|
| `<BUCKET>` | Your S3 bucket name (globally unique) | `csv-cleaner-mary-1699999999` |
| `<REGION>` | Your AWS region | `us-east-1` |
| `<ACCOUNT_ID>` | Your 12-digit AWS account ID | `123456789012` |

Set them as shell variables so the commands below can reuse them:

```bash
BUCKET=csv-cleaner-mary-$(date +%s)   # appends a timestamp for uniqueness
REGION=us-east-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### 1. Create the S3 bucket

```bash
aws s3 mb "s3://$BUCKET" --region "$REGION"
```

### 2. Create the Lambda execution role

The Lambda needs an IAM role granting it permission to read/write S3 and write
logs to CloudWatch.

```bash
# Trust policy: allow Lambda to assume this role
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name csv-cleaner-role \
  --assume-role-policy-document file://trust-policy.json

# Attach S3 access and basic Lambda logging permissions
aws iam attach-role-policy \
  --role-name csv-cleaner-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name csv-cleaner-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### 3. Package the code

Zip the handler and the cleaning module together. Dependencies (`pandas`,
`boto3`) are provided by the runtime and the layer below, so they are not zipped.

```bash
zip lambda.zip lambda_function.py cleaner.py
```

### 4. Create the Lambda function

Attach the AWS-managed pandas layer so `pandas` is available without packaging it.

```bash
aws lambda create-function \
  --function-name csv-cleaner \
  --runtime python3.12 \
  --handler lambda_function.lambda_handler \
  --role "arn:aws:iam::$ACCOUNT_ID:role/csv-cleaner-role" \
  --zip-file fileb://lambda.zip \
  --timeout 60 \
  --memory-size 256 \
  --layers arn:aws:lambda:$REGION:336392948345:layer:AWSSDKPandas-Python312:17 \
  --region "$REGION"
```

### 5. Grant S3 permission to invoke the Lambda

By default S3 cannot invoke the function. This permission must be added **before**
configuring the trigger, or the trigger will be silently ignored.

```bash
aws lambda add-permission \
  --function-name csv-cleaner \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::$BUCKET" \
  --region "$REGION"
```

### 6. Configure the S3 event trigger

Tell S3 to invoke the Lambda whenever a file is created under the `input/`
prefix. The prefix filter is important: it prevents the function's own writes to
`output/` from re-triggering it (an infinite loop).

```bash
cat > notification.json <<EOF
{
  "LambdaFunctionConfigurations": [{
    "LambdaFunctionArn": "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:csv-cleaner",
    "Events": ["s3:ObjectCreated:*"],
    "Filter": {
      "Key": { "FilterRules": [{ "Name": "prefix", "Value": "input/" }] }
    }
  }]
}
EOF

aws s3api put-bucket-notification-configuration \
  --bucket "$BUCKET" \
  --notification-configuration file://notification.json \
  --region "$REGION"
```

### 7. Test end-to-end

Upload a messy CSV to `input/` and confirm a cleaned file appears in `output/`.

```bash
# Generate test data first if needed: python generate_data.py
aws s3 cp data/messy_input.csv "s3://$BUCKET/input/messy_input.csv"

# Wait a few seconds, then check for the cleaned output
aws s3 ls "s3://$BUCKET/output/"
```

You should see `cleaned_messy_input.csv` in `output/` — produced automatically by
the upload, with no manual invocation.

## Tech Stack

- Python
- pandas
- AWS Lambda
- Amazon S3
- boto3
- Faker
- pytest
