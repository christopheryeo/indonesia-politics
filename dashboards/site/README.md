# Sentient.io Media Intelligence Dashboard

This site is generated from the Indonesia-politics vault's Markdown source of truth.
It does not call a language model, external API, or database at runtime.

## Refresh the dashboard

```bash
npm run generate:data
```

The Python generator scans `entities/`, calculates aggregate metrics, and writes
`app/dashboard-data.json`. Both `npm run dev` and `npm run build` refresh the
dataset automatically before starting.

## Dashboard views

- Article volume by month with 3-, 6-, and all-month controls
- Entity composition across knowledge domains
- Country, outlet, people, organisation, and topic rankings
- Sentiment, event-type, and source-type mix
- Issue radar assessments and deterministic scores
- Coverage completeness and latest compiled article notes
