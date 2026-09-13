# Profile maintenance

The profile is rendered by GitHub from the root README. Keep essential project
descriptions and links as text so the page works without image services.

## Recent public projects

`python scripts/update_recent_projects.py` refreshes the three most recently
pushed public, non-fork, non-archived repositories owned by basit3000. The profile
repository itself is excluded so automatic card refreshes do not dominate the list.
Push dates are UTC, not release dates or claims of feature completion.

The script uses only the Python standard library. `GITHUB_TOKEN` is optional
locally and supplied by GitHub Actions. It changes only the section between
`RECENT-PROJECTS` markers. Keep exactly one ordered pair of markers. Failed API
requests or malformed data fail the run and retain the previous README content.
Repeated runs with unchanged data do not create commits.

The **Update Recent Projects** workflow runs every 12 hours, on relevant code
pushes, or manually from Actions. It shares the existing `readme-push` concurrency
group with the card and Steam jobs. The schedule becomes active once these files
are pushed to the default branch; GitHub may delay scheduled runs.

Run `python -m unittest discover -s scripts -p "test_*.py" -v` for offline tests.
**Profile Checks** runs these on pull requests without write permissions.

## Profile presentation

- Main content uses native headings, links, and lists that wrap on mobile.
- Keep the visual identity: animated intro, badges, skill icons, project SVGs,
  stats, contribution snake, and live dashboard are visible without expanding
  panels. Dark/light stats use `<picture>`; live widgets keep `www` API URLs.
- Project cards have short text captions and direct setup links. Keep these
  alongside the SVGs rather than replacing the visuals with text.
- Contact buttons are local SVGs in `assets/buttons/`, with a shared 176 × 44
  size, readable labels, and descriptive image alt text. Use native links around
  them; keep the contact address below as a plain-text fallback.
- Existing card and Steam generation jobs remain available.

## Suggested account-level follow-up

The GitHub sidebar bio and native pinned repositories are account settings, not
README content. A more specific bio would be: “Backend developer building Python
APIs, automation, and integrations.” Consider pinning Spotify True Random, Job
Scout, MAL to Notion, Django Setup Script, Diet Analysis, and trainapplication to
align the native pins with the work highlighted in the README.
