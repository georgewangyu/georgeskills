# Tax Connector Notes

## As Of 2026-04-14

- Intuit publicly announced:
  - a TurboTax connector in Claude
  - an Intuit TurboTax app in ChatGPT

## Practical Interpretation

- Availability in chat products does not automatically imply a local API surface that every coding runtime can call.
- For reusable workflow design, assume:
  - checklisting and preparation can be strongly automated
  - final filing and submission remain human-in-the-loop unless a verified API path exists

## Product Strategy

- If user files in Wealthsimple Tax, use this skill to produce standardized prep artifacts independent of filing product.
- If user uses TurboTax app in ChatGPT, use that app for guided questioning and completeness checks, then preserve only non-sensitive progress metadata locally.
