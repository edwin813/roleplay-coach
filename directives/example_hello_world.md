# Directive: Hello World Example

## Purpose
Demonstrates the basic directive structure by processing a simple greeting and logging it.

## Inputs
- `name`: Person or entity to greet (required)
- `language`: Language for greeting (optional, default: "en")

## Tools
- `execution/hello_world.py` - Generates greeting and logs result

## Process
1. Validate that name is provided
2. Call `hello_world.py` with name and language parameters
3. Receive formatted greeting
4. Return result to user

## Outputs
- **Console**: Greeting message printed
- **Return Value**: JSON with greeting details

## Edge Cases
- **Empty Name**: Return error if name is empty
- **Unsupported Language**: Default to English with warning

## Success Criteria
- [x] Name validated
- [x] Greeting generated successfully
- [x] Result returned

## Notes
This is a minimal example to demonstrate the architecture. Real directives would call APIs, process data, and create cloud deliverables.
