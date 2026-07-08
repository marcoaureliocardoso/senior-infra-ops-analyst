# Cloud Command Record Example

- Provider: AWS
- Scope: account alias/account id, region, instance id
- Risk: SAFE_READ_ONLY
- Modifiers: SENSITIVE_OUTPUT
- Command: `aws ec2 describe-instance-status --region us-east-1 --instance-ids i-... --include-all-instances`
- Expected normal signal: system and instance checks ok
- Abnormal signal: impaired system or instance check
- Interpretation: distinguish provider/host issue from guest OS/service issue
- Next action: inspect CloudWatch metrics or OS logs in a narrow time window
