---
description: Tag and release a new version of the integration
---

This workflow helps you tag and push a new version.

1.  Ensure you have merged your changes to `main`.
2.  Switch to the `main` branch:
    ```bash
    git checkout main
    git pull origin main
    ```
3.  Create a new tag (e.g., v0.1.0):
    ```bash
    git tag v0.1.0
    ```
4.  Push the tag to GitHub:
    ```bash
    git push origin v0.1.0
    ```

Once the tag is pushed, the GitHub Action will automatically create a release for you.
