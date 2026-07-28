# Production Terraform root

Production infrastructure is intentionally deferred. Create this root only after production launch
planning defines its project, region, authentication provider, exposure policy, recovery plan, and
state bucket. Do not point the development root at production resources.
