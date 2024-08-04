# Contributing

The community is excited that you're interested in contributing to pooltool! This document provides guidelines for contributing. Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open-source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

## Join the community

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/8Y8qUgzZhz)

If you want to contribute, please join the Discord, introduce yourself, and state what you would like to work on.

## What we're looking for

Pooltool needs and welcomes people of all skill levels who are excited about this project, but especially those who have skill or passion in:

1. **Game development** (especially for the Panda3D game engine)
1. **Creating 3D models** (tables, balls, cues, rooms, etc)
1. **Projector/camera systems**
1. **Computer vision / machine learning / reinforcement learning**

## Getting started

Contributions to pooltool are made via GitHub. To get started:

1. Fork the repo and create your branch from `main`.
1. Install pooltool using the "install from source" instructions [here](https://pooltool.readthedocs.io/en/latest/getting_started/install.html).
1. If you've added code that should be tested, add tests.
1. If you've changed [the API](https://pooltool.readthedocs.io/en/latest/autoapi/index.html), update the documentation.
1. Create a pull request (PR), ensuring you have a clear description of the problem you're solving and the solution.
1. Ensure your code passes the continuous integration (CI) tests that are automatically ran whenever you update the PR with new commits.

## Code adherence

Style and code integrity in pooltool are maintained automatically through a combination of pre-commit hooks and continuous integration (CI) processes. These tools ensure that all contributions adhere to our coding standards and pass necessary tests before they can be integrated into the main branch.

### pre-commit

Pooltool utilizes the pre-commit framework to automatically reformat code upon committing, ensuring consistency and adherence to coding standards. If your code is reformatted during the commit process, review the changes made by pre-commit and add any modified files to your commit before proceeding.

### pre-merge

Pooltool utilizes continuous integration (CI) tools through GitHub workflows to ensure every pull request meets the project's quality and testing standards before it can be merged. Upon creating a pull request, automated tests are run to check for any issues. Contributors are expected to resolve any failing checks or tests highlighted by the CI process.

## Code of Conduct

Pooltool has adopted a Code of Conduct that we expect project participants to adhere to. Please read [the full text](CODE_OF_CONDUCT.md) so that you can understand what actions will and will not be tolerated.

## License

By contributing, you agree that your contributions will be licensed under [this license](LICENSE.md).
