---
description: Tag and release a new version of the integration
---

# Tag and Release Workflow

This workflow helps you create a new release for the AirControlBase integration.

## Option 1: Using GitHub Actions (Recommended)

The easiest way to create a release is through GitHub Actions:

1. Go to the [Actions tab](https://github.com/enudler/homeassistant-aircontrol/actions)
2. Select **"Create Tag and Release"** workflow from the left sidebar
3. Click **"Run workflow"** button
4. Enter the version number (e.g., `1.0.0` - without the `v` prefix)
5. Check "Update version in manifest.json" if you want to bump the version automatically
6. Click **"Run workflow"**

The workflow will automatically:
- Validate the version format
- Update `manifest.json` if selected
- Run tests and HACS validation
- Create a Git tag
- Create a GitHub Release with artifacts
- Generate changelog from commits

## Option 2: Manual Release

If you prefer to create releases manually:

1. Ensure you have merged your changes to `main`:
    ```bash
    git checkout main
    git pull origin main
    ```

2. Update the version in `manifest.json`:
    ```bash
    # Edit custom_components/aircontrolbase/manifest.json
    # Update the "version" field to your new version
    ```

3. Commit the version bump:
    ```bash
    git add custom_components/aircontrolbase/manifest.json
    git commit -m "chore: Bump version to X.Y.Z"
    git push origin main
    ```

4. Create and push a new tag (e.g., v0.2.0):
    ```bash
    git tag -a v0.2.0 -m "Release v0.2.0"
    git push origin v0.2.0
    ```

Once the tag is pushed, the GitHub Action will automatically:
- Run validation checks
- Create a GitHub Release
- Generate release notes
- Attach the HACS-compatible zip artifact

## Version Guidelines

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

Examples:
- `0.1.0` → `0.1.1`: Bug fix
- `0.1.1` → `0.2.0`: New feature
- `0.2.0` → `1.0.0`: Breaking change

## After Release

After a successful release:

1. **HACS** will automatically detect the new version
2. Users will see the update in:
   - Home Assistant → Settings → Devices & Services → HACS
   - Or in the Home Assistant update panel
3. Users can choose which version to install from HACS

## Pre-releases

For beta/testing releases:
1. Use a version suffix like `1.0.0-beta.1`
2. Check the "Is this a pre-release?" option in the GitHub Action
