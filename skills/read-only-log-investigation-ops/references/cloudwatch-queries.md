# CloudWatch Logs Insights examples

Use the approved account/region and only the selected log groups. Set an
explicit incident time range in the console or StartQuery request. These are
adaptable query templates, not a universal schema or a tested production kit.
Never run an unbounded all-account discovery query to replace missing scope.

## Error candidates

For text logs, inspect matches before interpreting them as failures:

```text
fields @timestamp, @log, @logStream, @message
| filter @message like /(?i)(error|fatal|critical|exception|panic|timeout)/
| sort @timestamp asc
| limit 200
```

For JSON with a confirmed `level` field, replace the text filter with the actual
schema, for example `filter level in ["ERROR", "FATAL", "CRITICAL"]`. Lowercase
or numeric severities require their own mapping. Do not assume every service
uses this field. A text match like `no errors` is not a failure.

## Count error candidates over time

```text
filter @message like /(?i)(error|fatal|critical|exception|panic|timeout)/
| stats count(*) as candidates by bin(1m) as minute
| sort minute asc
```

Counts are matching log events, not unique failed users/requests. This is a
triage shape, not a failure-rate denominator or root-cause proof.

## All-severity context

Suppose a synthetic failure anchor is `2030-01-01T12:00:00Z`. Set query bounds
`11:55:00Z` through `12:10:00Z` that day. Remove the error filter:

```text
fields @timestamp, @log, @logStream, @message
| sort @timestamp asc
| limit 1000
```

Select relevant service groups and optionally filter the confirmed stream.
Then correlate a confirmed request field, for example:

```text
fields @timestamp, @log, @logStream, @message, requestId
| filter requestId = "example-request-id"
| sort @timestamp asc
| limit 1000
```

Repeat the bounded service/stream context without the request filter to find
related restart/deploy/dependency events lacking that ID. If a limit is reached,
subdivide the time range and document completeness. Do not silently omit the
later context because the first 1000 records filled the result set.

## Query lifecycle and access

Prefer the existing approved console or helper. For API use, StartQuery starts
a scoped analysis and returns a query ID. GetQueryResults can return partial
records while Running, so poll with a bounded timeout and inspect status before
interpreting final results. Retain query statistics/scan coverage and cancel
owned outstanding work with StopQuery on interruption. Failed, Cancelled or
Timeout are incomplete investigations, not zero matches.

The owner should provision only required read/query capabilities for selected
resources. Consult the action-specific permission reference rather than
assuming that a broad managed ReadOnly policy is appropriately narrow. This
skill does not provide or apply an IAM policy or create an account.

Official sources:

- [Logs Insights syntax and query scope/cost guidance](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [Filter, regex and case-insensitive matching](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-Filter.html)
- [CloudWatch Logs access control](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/iam-access-control-overview-cwl.html)
- [Permissions reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/permissions-reference-cwl.html)
- [StartQuery](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_StartQuery.html)
- [GetQueryResults](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_GetQueryResults.html)
- [StopQuery](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_StopQuery.html)
