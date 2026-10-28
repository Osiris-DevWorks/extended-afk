This command conducts all the steps related to releasing the latest version of Extended AFK.

# Invocation

To invoke, type `/release`

# Instructions

Perform the following steps for a release:

1. Follow all the instructions for releasing the software that are in `docs/RELEASE_PROCESS.md`
2. Make sure the version bump PR's Build workflow passed and the exe from its artifacts was tested before merging
3. Review the release notes (`python scripts/release_tools.py notes X.Y.Z`) with the user before merging; merging the version bump to main is what publishes the release
4. After the merge, watch the Release workflow until the GitHub release is live and the Discord post has gone out; if the Discord step was skipped or failed, post it manually
5. Update the website tile as described in the release process
