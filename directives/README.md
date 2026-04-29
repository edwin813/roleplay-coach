# Directives

Directives are SOPs (Standard Operating Procedures) written in Markdown. They define **what to do** without worrying about implementation details.

## Directive Template

Each directive should include:

1. **Purpose** - What this directive accomplishes
2. **Inputs** - What data/parameters are needed
3. **Tools** - Which execution scripts to use
4. **Process** - Step-by-step workflow
5. **Outputs** - What gets created (usually cloud-based deliverables)
6. **Edge Cases** - Known issues, rate limits, special handling
7. **Success Criteria** - How to verify it worked

## Example Structure

```markdown
# Directive: Do Something

## Purpose
Accomplish X by doing Y.

## Inputs
- `input_data`: Description of what's needed
- `config_option`: Optional parameter (default: value)

## Tools
- `execution/script_name.py` - What it does

## Process
1. Validate inputs
2. Call tool with parameters
3. Handle errors
4. Verify output

## Outputs
- Google Sheet: [Link to template]
- Slack notification to #channel

## Edge Cases
- API rate limit: 100 requests/minute
- Large datasets: Process in batches of 1000

## Success Criteria
- All records processed
- No errors in logs
- Output sheet populated
```

## Living Documents

Directives evolve. When you discover:
- API constraints
- Better approaches
- Common errors
- Timing expectations

Update the directive so future runs benefit from the learning.
