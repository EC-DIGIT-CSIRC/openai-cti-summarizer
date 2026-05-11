# User Guide

This guide is for analysts or managers using the web interface.

The UI is expected to change in a later iteration, so this document is intentionally short. Screenshots can be added later in the placeholders below.

## What It Does

The service summarizes CTI reports and extracts structured information such as key points, MITRE ATT&CK TTPs, indicators, threat actors, metadata, and optional YARA rule candidates.

The output is evidence-based. The system should only use information supported by the report text. Always fact-check the result before using it operationally.

## Screenshot: Start Page

TODO: Add screenshot of the input form.

## Inputs

Use one input method per request:

- paste a report URL
- upload a PDF
- paste report text into the text area

Before submitting, accept the on-page limitations and fact-checking confirmations.

## Prompt And Model

The base prompt controls the extraction instructions. The default prompt is configured by the administrator.

The model selector lets you choose one of the configured models shown in the UI.

## Results

The result is shown below the form. Depending on the server configuration, the service returns either rendered markdown or raw validated JSON.

## Screenshot: Results

TODO: Add screenshot of a successful summary.

## Common Errors

- Empty input: provide a URL, PDF, or text.
- URL fetch failed: check that the URL is reachable by the server.
- PDF processing failed: try text copy/paste if the PDF cannot be parsed.
- LLM/provider failed: retry later or contact the administrator.

## YARA Rules

YARA rules, when generated, are AI-generated candidates. Treat them as drafts that require analyst review and testing.
