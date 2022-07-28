# Build reproducibility test with Conan packages

Repeatable builds are important to prevent vulnerabilities and performance issues and to be able to work with the same artifacts, no matter where or when we build them.

By using Conan as a C++ package manager, we can achieve [build reproducibility], but only if we are using lockfiles, however lockfiles can not fit all of our needs.

In this repository we demonstrate the problematic scenarios and propose an alternative solution what can be used at the onboarding process.

[build reproducibility]: https://docs.conan.io/en/latest/versioning/revisions.html

## Motivation

Precondition: consumers cannot build conan packages by themselves, they can only access the artifactory to download the internally built packages.

Consumers usually want to know only the direct dependencies to their projects and get the transitive dependencies automatically, which should be determined by the reference of direct dependencies. To generate the lockfile, we need to know how we built our dependencies, what were the recipe revisions of the transitive dependencies and how we configured them. This information can be retrieved by `conan get` or `lock create`, however the package information what we get by `conan get` can miss some of these information.

Lockfiles could be stored both for the built packages and for our projects as well, but there are some disadvantages of doing that:

- a package reference can belong to multiple lockfiles (see `test_header_only_recipe_upgrade_bad` example)
- lockfile generation can result in different file today than yesterday, unless we lock the revision of each transient dependencies what the users usually don't want to do
- build requirements are not part of the lockfiles by default and package references may not affected by any build requirement change, so the users won't notice that their dependencies were built a bit differently
- package reference of header-only libraries are the same if they remove the dependency information by using `self.info.header_only()`, therefore depending on a header-only package will provide the latest configuration how we built it
- build systems, like [Bazel], should be able to define dependencies in WORKSPACE file without any initialization (e.g. `conan install`), lockfiles should not be an input for that, an expected dependency declaration should look like:

        conan_dependency(
            name = "boost",
            version = "1.70.0",
            revision = "<rev>",
            pids = ["<pid1>", "<pid2>"]
        )

[Bazel]: https://bazel.build/

## Alternative solution

We have control over the onboarding process, so we can manipulate the recipes if necessary. We do use the recipes from [conan-center-index], but may apply additional source or recipe patches.

Our alternative solution is:

- expand the revision information for `requires` and `build_requires` in recipes
- ignore the `package_id()` method in recipes which can override or remove some necessary dependency information

[conan-center-index]: https://github.com/conan-io/conan-center-index

## Requirements

- Python 3.7+ (tested with Python 3.7.5)
- Conan 1.X (tested with Conan 1.48.1)

> **Note:** By using Conan 2.X, the test results may be different!

## Configuration

    $ export CONAN_USER_HOME=$(pwd)/conan-home
    $ conan config install config

## Tests

    $ cd tests
    $ python3 ./package_onboarding_test.py --keep-artifacts
