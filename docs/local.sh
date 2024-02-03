#!/bin/bash
rm -rf autoapi _build
sphinx-build -b html . _build
open _build/index.html
