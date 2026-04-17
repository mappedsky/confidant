# Docs

## Building docs locally

```bash
# Just run the make target
make docs
# or directly run the script:
./docs/build.sh
```

The output can be found in `generated/docs`.

## How docs are published

Docs are built and deployed automatically via the GitHub Actions workflow in
`.github/workflows/push.yml`. On every push to `master` and on tagged releases:

1. Sphinx builds the docs into `generated/docs/`
2. The `JamesIves/github-pages-deploy-action` deploys that folder to the `gh-pages` branch
3. GitHub Pages serves the site at https://mappedsky.github.io/confidant/
