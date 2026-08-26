# Pending workflow changes (apply manually)

These two workflow files could not be pushed automatically — GitHub blocks app
tokens from creating or updating files under `.github/workflows/` without the
`workflows` permission:

```
! [remote rejected] refusing to allow a GitHub App to create or update
  workflow `.github/workflows/refresh.yml` without `workflows` permission
```

Everything else in this change (the connection layer and the crawl fail-safes)
is already merged and active. These two files are the CI wiring on top.

## How to apply (about 60 seconds, in the GitHub web UI)

### 1. New file — `.github/workflows/viralstyle-check.yml`
Copy `ci/workflows/viralstyle-check.yml` to `.github/workflows/viralstyle-check.yml`.

Gives you an on-demand connection test: **Actions → Viralstyle connection check
→ Run workflow**. It prints which layer fails (DNS / TLS / storefront / product)
and attaches a report. Also runs weekly on Mondays at 05:45 UTC, half an hour
before the deep re-crawl.

### 2. Edit — `.github/workflows/refresh.yml`
Copy `ci/workflows/refresh.yml` over `.github/workflows/refresh.yml`.

The only change: the Monday catalogue re-crawl is now gated on a passing
connection check, so a blocked or rate-limited edge can never overwrite a good
catalogue with a partial one. Diff versus what is live:

```yaml
      # --- is Viralstyle actually reachable today? ---
      - name: Check Viralstyle connection
        id: vs
        continue-on-error: true
        run: |
          if python src/viralstyle.py --check | tee vs-check.txt; then
            echo "reachable=true" >> $GITHUB_OUTPUT
          else
            echo "reachable=false" >> $GITHUB_OUTPUT
            echo "::warning::Viralstyle unreachable - skipping catalogue re-crawl, keeping committed data."
          fi

      - name: Re-crawl product catalogue (Mondays only)
        if: steps.vs.outputs.reachable == 'true'      # <-- added
        ...
```

### Or from a terminal with your own credentials

```bash
git checkout arena/01a03e57-gridiron-locker
cp ci/workflows/viralstyle-check.yml .github/workflows/
cp ci/workflows/refresh.yml          .github/workflows/
git add .github/workflows && git commit -m "Wire Viralstyle connection check into CI" && git push
```

## Verifying the connection once applied

```
Actions → Viralstyle connection check → Run workflow
```

Healthy output looks like:

```
Viralstyle connection check -> https://viralstyle.com
  [OK  ] dns      {'ips': [...]}
  [OK  ] tls      {'ip': '...', 'version': 'TLSv1.3', 'cipher': '...'}
  [OK  ] store    {'path': 'Cleveland-Browns', 'bytes': 148231, 'secs': 1.2}
  [OK  ] product  {'slug': '...', 'bytes': 203114, 'secs': 0.9}

result: CONNECTED
```

You can run the same check from any machine with internet:

```bash
pip install requests beautifulsoup4 lxml
python src/viralstyle.py --check
```
