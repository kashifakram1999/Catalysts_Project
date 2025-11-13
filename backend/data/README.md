# Data Directory

This directory contains the local PDF files used for scraping CARB catalytic converter data.

## Files

- `Data.pdf` - CARB Exempt Catalytic Converter PDF (local copy)

## Usage

The scraper will automatically look for PDF files in this directory when running with the `--use-local` flag (default behavior).

If the local PDF is not found, the scraper will download from the remote URL:
https://ww2.arb.ca.gov/sites/default/files/aftermarket/aftermktcat/exemptcat09.pdf

## Deployment

When deploying this project, make sure to include the `Data.pdf` file in this directory, or configure the scraper to use the `--remote` flag to download from the CARB website.
