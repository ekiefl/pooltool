# View local copy

To generate a local copy of the documentation, make sure you've installed poetry with the docs dependencies:

```bash
poetry install --with docs
```

Additionally, `pandoc` needs to be installed: https://pandoc.org/installing.html

Then, in the root directory run:

```
make docs
```
