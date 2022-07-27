import argparse
import copy
import os
import sys
import tempfile
import unittest


import conan_helper_lib
from base import ConanWrapper as conan
from base.types import FlattenedConanPackageInfo
from onboard.recipe.updater import RecipeUpdateModes, RecipeUpdater
from testing.unit.parallel_test_suite import ParallelTestSuite
from testing.mock.conan_environment import ConanEnvironment as ConanTestEnvironment
from testing.mock.types import PackageToBuild

parser = argparse.ArgumentParser(description="""Conan Build Reproducibility Tests

    This test mock several onboarding and consuming scenarios.
    Predict revisions, package ids, package revisions, requires fields.

    Example:

        $ ./package_onboarding_test.py --keep-artifacts

    To set up your local environment:

        $ export CONAN_USER_HOME=$(pwd)/conan-home
        $ conan config install ../config

""", formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--nosuite", default=False, action="store_true", help="Run tests synchronously to use unittest.main parameters.")
parser.add_argument("--profile", default="gcc82", help="Conan profile to be used.")
parser.add_argument("--keep-artifacts", default=False, action="store_true", help="Keep built artifacts.")
parser.add_argument("testargs", nargs=argparse.REMAINDER)
args = parser.parse_args()



class TestPackageReferences(unittest.TestCase):
    """
    Run tests on locally built packages.

    """

    @classmethod
    def _register_test_dependencies(cls):
        """Register conan packages which need to be built before starting the tests"""

        # for header only tests
        cls._pkg_a_1_0_opt_0 = FlattenedConanPackageInfo(name = "pkg_a", version = "1.0", options = [])
        cls._pkg_a_1_0_opt_1 = FlattenedConanPackageInfo(name = "pkg_a", version = "1.0", options = ["pkg_a:shared=True"])
        cls._pkg_b_1_0_opt_0 = FlattenedConanPackageInfo(name = "pkg_b", version = "1.0", options = [], requires=["_pkg_a_1_0_opt_0"])
        cls._pkg_b_1_0_opt_1 = FlattenedConanPackageInfo(name = "pkg_b", version = "1.0", options = [], requires=["_pkg_a_1_0_opt_1"])
        cls._pkg_c_1_0_opt_0 = FlattenedConanPackageInfo(name = "pkg_c", version = "1.0", options = [], requires=["_pkg_b_1_0_opt_0"])
        cls._pkg_c_1_0_opt_1 = FlattenedConanPackageInfo(name = "pkg_c", version = "1.0", options = [], requires=["_pkg_a_1_0_opt_1", "_pkg_b_1_0_opt_1"])
        # build_requires tests
        cls._pkg_d_1_0_opt_0 = FlattenedConanPackageInfo(name = "pkg_d", version = "1.0", options = [], requires=[])
        cls._pkg_d_1_0_opt_1 = FlattenedConanPackageInfo(name = "pkg_d", version = "1.0", options = ["pkg_d:with_optimization=True"], requires=[])
        cls._pkg_e_1_0_opt_0 = FlattenedConanPackageInfo(name = "pkg_e", version = "1.0", options = [], requires=["_pkg_d_1_0_opt_0"])
        cls._pkg_e_1_0_opt_1 = FlattenedConanPackageInfo(name = "pkg_e", version = "1.0", options = [], requires=["_pkg_d_1_0_opt_1"])

    @classmethod
    def setUpClass(cls):
        cls._root = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_cases"))
        cls._recipes_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "recipes"))

        cls._register_test_dependencies()

    ##############################
    ##### Test helpers    
    ##############################

    def __deep_copy_onboard_list(self, o):
        """Create deep copy of onboard list to be usable by more threads"""
        return {k: copy.deepcopy(v) for k,v in o.items()}

    def build_packages(self, conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater = None):
        """Build packages one by one
        
        Package list should be build order.
        """
        packages = self.__deep_copy_onboard_list(packages_to_build)
        for package in packages.values():
            recipe_dir = os.path.join(recipes_dir, package.name)

            # patch/update recipe if necessary
            patch_file = None
            if package.patch_file:
                patch_file = os.path.join(recipes_dir, package.patch_file)

            recipe_updater.apply(
                patch_file = patch_file,
                recipe_dir = recipe_dir,
                packages = packages
            )

            print(f"Export {package.reference} recipe ...")
            conan_environment.run_with_env_forward(
                conan.export,
                path=recipe_dir,
                version=package.version
            )

            package.options = package.options + \
                              [ option for req in package.requires for option in getattr(self, req).options]

            lockfile_root = os.path.join(lockfiles_dir, package.name, package.version)
            if not os.path.exists(lockfile_root):
                os.makedirs(lockfile_root)

            print(f"Building {package.full_reference} ...")
            conan_environment.run_with_env_forward(
                conan.create,
                conanfile_path = recipe_dir,
                version = package.version,
                options = package.options,
                profile = args.profile,
            )

            # create lockfile to get the package revision
            lockfile_path = os.path.join(tempfile.TemporaryDirectory(dir=lockfile_root).name, "conan.lock")
            print(f"Create lockfile for {package.reference}, options = {package.options}, lockfile path = {lockfile_path} ...")
            lockfile =  conan_environment.run_with_env_forward(
                conan.create_lock,
                reference = package.reference,
                profile = args.profile,
                options = package.options,
                lockfile = lockfile_path,
            )

            package.revision = lockfile.first_node.revision
            package.pid = lockfile.first_node.package_id
            package.prev = lockfile.first_node.prev

            package.requires = conan_environment.run_with_env_forward(
                conan.get,
                package = package.reference,
                revision = package.revision,
                package_id = package.pid,
            ).requires

            # revert recipe updates
            recipe_updater.revert()

        return packages

    ##############################
    ##### Test cases   
    ##############################

    def test_header_only_recipe_upgrade_bad(self):
        # Recipe upgrade of header only dependency
        recipe_updater = RecipeUpdater(RecipeUpdateModes.NONE)
        packages_to_build = {
            "pkg_a1" : PackageToBuild(self._pkg_a_1_0_opt_0),
            "pkg_b1" : PackageToBuild(self._pkg_b_1_0_opt_0),
            "pkg_c1" : PackageToBuild(self._pkg_c_1_0_opt_0),
            "pkg_a2" : PackageToBuild(self._pkg_a_1_0_opt_0, patch_file="patches/pkg_a_add_defines.patch"),
            "pkg_b2" : PackageToBuild(self._pkg_b_1_0_opt_0),
            "pkg_c2" : PackageToBuild(self._pkg_c_1_0_opt_0),
        }

        with ConanTestEnvironment(self._root, "test_header_only_recipe_upgrade_bad", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)

            pkg_a1, pkg_a2 = onboarded_packages.get("pkg_a1"), onboarded_packages.get("pkg_a2")
            pkg_b1, pkg_b2 = onboarded_packages.get("pkg_b1"), onboarded_packages.get("pkg_b2")
            pkg_c1, pkg_c2 = onboarded_packages.get("pkg_c1"), onboarded_packages.get("pkg_c2")
            
            self.assertNotEqual(pkg_a1.revision, pkg_a2.revision)
            self.assertEqual(pkg_a1.pid, pkg_a2.pid)
            self.assertNotEqual(pkg_a1.prev, pkg_a2.prev)
            self.assertEqual(pkg_a1.requires, [])
            self.assertEqual(pkg_a2.requires, [])

            # Problem:
            # the dependency information of header-only libraries has been deleted by self.info.header_only()
            # resulting in a same pacakge reference
            # consequence: cannot tell the dependencies from the package info without having a lockfile
            # problem with storing lockfile:
            #   multiple lockfile could belong to the same package reference
            #   therefore it's hard to give them different names
            #   the package reference would be an acceptable name
            self.assertEqual(pkg_b1.revision, pkg_b2.revision)
            self.assertEqual(pkg_b1.pid, pkg_b2.pid)
            self.assertEqual(pkg_b1.prev, pkg_b2.prev)
            self.assertEqual(pkg_b1.requires, [])
            self.assertEqual(pkg_b2.requires, [])

            self.assertEqual(pkg_c1.revision, pkg_c2.revision)
            self.assertNotEqual(pkg_c1.pid, pkg_c2.pid)
            self.assertNotEqual(pkg_c1.prev, pkg_c2.prev)
            self.assertEqual(pkg_c1.requires, [pkg_a1.full_reference, pkg_b1.full_reference], f"{pkg_c1.requires} {[pkg_a1.full_reference, pkg_b1.full_reference]}")
            self.assertEqual(pkg_c2.requires, [pkg_a2.full_reference, pkg_b2.full_reference], f"{pkg_c2.requires} {[pkg_a2.full_reference, pkg_b2.full_reference]}")


    def test_header_only_recipe_upgrade_good(self):
        # Recipe upgrade of header only dependency
        recipe_updater = RecipeUpdater(RecipeUpdateModes.ALL)
        packages_to_build = {
            "pkg_a1" : PackageToBuild(self._pkg_a_1_0_opt_0),
            "pkg_b1" : PackageToBuild(self._pkg_b_1_0_opt_0),
            "pkg_c1" : PackageToBuild(self._pkg_c_1_0_opt_0),
            "pkg_a2" : PackageToBuild(self._pkg_a_1_0_opt_0, patch_file="patches/pkg_a_add_defines.patch"),
            "pkg_b2" : PackageToBuild(self._pkg_b_1_0_opt_0),
            "pkg_c2" : PackageToBuild(self._pkg_c_1_0_opt_0),
        }

        with ConanTestEnvironment(self._root, "test_header_only_recipe_upgrade_good", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)
            
            pkg_a1, pkg_a2 = onboarded_packages.get("pkg_a1"), onboarded_packages.get("pkg_a2")
            pkg_b1, pkg_b2 = onboarded_packages.get("pkg_b1"), onboarded_packages.get("pkg_b2")
            pkg_c1, pkg_c2 = onboarded_packages.get("pkg_c1"), onboarded_packages.get("pkg_c2")

            self.assertNotEqual(pkg_a1.revision, pkg_a2.revision)
            self.assertEqual(pkg_a1.pid, pkg_a2.pid)
            self.assertNotEqual(pkg_a1.prev, pkg_a2.prev)
            self.assertEqual(pkg_a1.requires, [])
            self.assertEqual(pkg_a2.requires, [])

            # removing the package_id() method and extending revision into recipe fixed the problem
            # we have a different recipe revision and pid
            self.assertNotEqual(pkg_b1.revision, pkg_b2.revision)
            self.assertNotEqual(pkg_b1.pid, pkg_b2.pid)
            self.assertNotEqual(pkg_b1.prev, pkg_b2.prev)
            self.assertEqual(pkg_b1.requires, [pkg_a1.full_reference])
            self.assertEqual(pkg_b2.requires, [pkg_a2.full_reference])

            self.assertNotEqual(pkg_c1.revision, pkg_c2.revision)
            self.assertNotEqual(pkg_c1.pid, pkg_c2.pid)
            self.assertNotEqual(pkg_c1.prev, pkg_c2.prev)
            self.assertEqual(pkg_c1.requires, [pkg_a1.full_reference, pkg_b1.full_reference])
            self.assertEqual(pkg_c2.requires, [pkg_a2.full_reference, pkg_b2.full_reference])


    def test_header_only_configuration_change_bad(self):
        # Configuration change of header-only library
        recipe_updater = RecipeUpdater(RecipeUpdateModes.NONE)
        packages_to_build = {
            "pkg_a1" : PackageToBuild(self._pkg_a_1_0_opt_0),
            "pkg_b1" : PackageToBuild(self._pkg_b_1_0_opt_0),
            "pkg_c1" : PackageToBuild(self._pkg_c_1_0_opt_0),
            "pkg_a2" : PackageToBuild(self._pkg_a_1_0_opt_1),
            "pkg_b2" : PackageToBuild(self._pkg_b_1_0_opt_1),
            "pkg_c2" : PackageToBuild(self._pkg_c_1_0_opt_1),
        }

        with ConanTestEnvironment(self._root, "test_header_only_configuration_change_bad", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)

            pkg_a1, pkg_a2 = onboarded_packages.get("pkg_a1"), onboarded_packages.get("pkg_a2")
            pkg_b1, pkg_b2 = onboarded_packages.get("pkg_b1"), onboarded_packages.get("pkg_b2")
            pkg_c1, pkg_c2 = onboarded_packages.get("pkg_c1"), onboarded_packages.get("pkg_c2")

            self.assertEqual(pkg_a1.revision, pkg_a2.revision)
            self.assertNotEqual(pkg_a1.pid, pkg_a2.pid)
            self.assertNotEqual(pkg_a1.prev, pkg_a2.prev)
            self.assertEqual(pkg_a1.requires, [])
            self.assertEqual(pkg_a2.requires, [])

            # Problem:
            # By changing the configuration of the dependency, only the package revision changed
            # Package revisions cannot be differentiated by conan commands
            #   such as listing them
            #   query return the same result (latest)
            # Recipe revision of transitive dependencies (pkg_a) cannot be detected without having a lockfile
            self.assertEqual(pkg_b1.revision, pkg_b2.revision)
            self.assertEqual(pkg_b1.pid, pkg_b2.pid)
            self.assertNotEqual(pkg_b1.prev, pkg_b2.prev)
            self.assertEqual(pkg_b1.requires, [])
            self.assertEqual(pkg_b2.requires, [])

            self.assertEqual(pkg_c1.revision, pkg_c2.revision)
            self.assertNotEqual(pkg_c1.pid, pkg_c2.pid)
            self.assertNotEqual(pkg_c1.prev, pkg_c2.prev)
            self.assertEqual(pkg_c1.requires, [pkg_a1.full_reference, pkg_b1.full_reference])
            self.assertEqual(pkg_c2.requires, [pkg_a2.full_reference, pkg_b2.full_reference])


    def test_header_only_configuration_change_good(self):
        # Configuration change of header-only library
        recipe_updater = RecipeUpdater(RecipeUpdateModes.ALL)

        packages_to_build = {
            "pkg_a1" : PackageToBuild(self._pkg_a_1_0_opt_0),
            "pkg_b1" : PackageToBuild(self._pkg_b_1_0_opt_0),
            "pkg_c1" : PackageToBuild(self._pkg_c_1_0_opt_0),
            "pkg_a2" : PackageToBuild(self._pkg_a_1_0_opt_1),
            "pkg_b2" : PackageToBuild(self._pkg_b_1_0_opt_1),
            "pkg_c2" : PackageToBuild(self._pkg_c_1_0_opt_1),
        }

        with ConanTestEnvironment(self._root, "test_header_only_configuration_change_good", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)

            pkg_a1, pkg_a2 = onboarded_packages.get("pkg_a1"), onboarded_packages.get("pkg_a2")
            pkg_b1, pkg_b2 = onboarded_packages.get("pkg_b1"), onboarded_packages.get("pkg_b2")
            pkg_c1, pkg_c2 = onboarded_packages.get("pkg_c1"), onboarded_packages.get("pkg_c2")

            self.assertEqual(pkg_a1.revision, pkg_a2.revision)
            self.assertNotEqual(pkg_a1.pid, pkg_a2.pid)
            self.assertNotEqual(pkg_a1.prev, pkg_a2.prev)
            self.assertEqual(pkg_a1.requires, [])
            self.assertEqual(pkg_a2.requires, [])

            # removing the package_id() method and extending revision into recipe fixed the problem
            # we have a different pid
            self.assertEqual(pkg_b1.revision, pkg_b2.revision)
            self.assertNotEqual(pkg_b1.pid, pkg_b2.pid)
            self.assertNotEqual(pkg_b1.prev, pkg_b2.prev)
            self.assertEqual(pkg_b1.requires, [pkg_a1.full_reference])
            self.assertEqual(pkg_b2.requires, [pkg_a2.full_reference])

            self.assertEqual(pkg_c1.revision, pkg_c2.revision)
            self.assertNotEqual(pkg_c1.pid, pkg_c2.pid)
            self.assertNotEqual(pkg_c1.prev, pkg_c2.prev)
            self.assertEqual(pkg_c1.requires, [pkg_a1.full_reference, pkg_b1.full_reference])
            self.assertEqual(pkg_c2.requires, [pkg_a2.full_reference, pkg_b2.full_reference])


    def test_build_requirement_recipe_upgrade_bad(self):
        # Recipe upgrade of build requirement
        recipe_updater = RecipeUpdater(RecipeUpdateModes.NONE)
        packages_to_build = {
            "pkg_d1" : PackageToBuild(self._pkg_d_1_0_opt_0),
            "pkg_e1" : PackageToBuild(self._pkg_e_1_0_opt_0),
            "pkg_d2" : PackageToBuild(self._pkg_d_1_0_opt_0, patch_file = "patches/pkg_d_recipe_upgrade.patch"),
            "pkg_e2" : PackageToBuild(self._pkg_e_1_0_opt_0),
        }

        with ConanTestEnvironment(self._root, "test_build_requirement_recipe_upgrade_bad", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)
            
            pkg_d1, pkg_d2 = onboarded_packages.get("pkg_d1"), onboarded_packages.get("pkg_d2")
            pkg_e1, pkg_e2 = onboarded_packages.get("pkg_e1"), onboarded_packages.get("pkg_e2")

            self.assertNotEqual(pkg_d1.revision, pkg_d2.revision)
            self.assertEqual(pkg_d1.pid, pkg_d2.pid)
            self.assertNotEqual(pkg_d1.prev, pkg_d2.prev)
            self.assertEqual(pkg_d1.requires, [])
            self.assertEqual(pkg_d2.requires, [])

            # Problem:
            # Building with two different build requirement revisions, results in the same package reference
            # Users won't notice that their transitive dependencies have been built by tools with different recipes
            self.assertEqual(pkg_e1.revision, pkg_e2.revision)
            self.assertEqual(pkg_e1.pid, pkg_e2.pid)
            self.assertEqual(pkg_e1.prev, pkg_e2.prev)
            self.assertEqual(pkg_e1.requires, [])
            self.assertEqual(pkg_e2.requires, [])


    def test_build_requirement_recipe_upgrade_good(self):
        # Recipe upgrade of build requirement
        recipe_updater = RecipeUpdater(RecipeUpdateModes.ALL)
        packages_to_build = {
            "pkg_d1" : PackageToBuild(self._pkg_d_1_0_opt_0),
            "pkg_e1" : PackageToBuild(self._pkg_e_1_0_opt_0),
            "pkg_d2" : PackageToBuild(self._pkg_d_1_0_opt_0, patch_file = "patches/pkg_d_recipe_upgrade.patch"),
            "pkg_e2" : PackageToBuild(self._pkg_e_1_0_opt_0),
        }

        with ConanTestEnvironment(self._root, "test_build_requirement_recipe_upgrade_good", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)
            
            pkg_d1, pkg_d2 = onboarded_packages.get("pkg_d1"), onboarded_packages.get("pkg_d2")
            pkg_e1, pkg_e2 = onboarded_packages.get("pkg_e1"), onboarded_packages.get("pkg_e2")

            self.assertNotEqual(pkg_d1.revision, pkg_d2.revision)
            self.assertEqual(pkg_d1.pid, pkg_d2.pid)
            self.assertNotEqual(pkg_d1.prev, pkg_d2.prev)
            self.assertEqual(pkg_d1.requires, [])
            self.assertEqual(pkg_d2.requires, [])
    
            # removing the package_id() method and extending revision into recipe fixed the problem
            # we have a different recipe revision
            self.assertNotEqual(pkg_e1.revision, pkg_e2.revision)
            self.assertEqual(pkg_e1.pid, pkg_e2.pid)
            self.assertNotEqual(pkg_e1.prev, pkg_e2.prev)
            self.assertEqual(pkg_e1.requires, [])
            self.assertEqual(pkg_e2.requires, [])


    def test_build_requirement_options_upgrade(self):
        # Recipe upgrade of header only dependency
        recipe_updater = RecipeUpdater(RecipeUpdateModes.ALL)
        packages_to_build = {
            "pkg_d1" : PackageToBuild(self._pkg_d_1_0_opt_0),
            "pkg_e1" : PackageToBuild(self._pkg_e_1_0_opt_0),
            "pkg_d2" : PackageToBuild(self._pkg_d_1_0_opt_1),
            "pkg_e2" : PackageToBuild(self._pkg_e_1_0_opt_1),
        }

        with ConanTestEnvironment(self._root, "test_build_requirement_options_upgrade", keep=args.keep_artifacts) as conan_environment:
            conan_environment.init()
            recipes_dir = os.path.join(conan_environment.test_case_dir, "recipes")
            lockfiles_dir = os.path.join(conan_environment.test_case_dir, "_", "lockfiles")
            conan_environment.copy_directory(self._recipes_dir, recipes_dir)

            onboarded_packages = self.build_packages(conan_environment, packages_to_build, recipes_dir, lockfiles_dir, recipe_updater)
            
            pkg_d1, pkg_d2 = onboarded_packages.get("pkg_d1"), onboarded_packages.get("pkg_d2")
            pkg_e1, pkg_e2 = onboarded_packages.get("pkg_e1"), onboarded_packages.get("pkg_e2")

            self.assertEqual(pkg_d1.revision, pkg_d2.revision)
            self.assertNotEqual(pkg_d1.pid, pkg_d2.pid)
            self.assertNotEqual(pkg_d1.prev, pkg_d2.prev)
            self.assertEqual(pkg_d1.requires, [])
            self.assertEqual(pkg_d2.requires, [])

            # we have the same resuls (building as it is OR removing package_id() and extend revision info)
            # we can accept this because the options of build requirements will barely change
            # we need to control it by profile settings
            self.assertEqual(pkg_e1.revision, pkg_e2.revision)
            self.assertEqual(pkg_e1.pid, pkg_e2.pid)
            self.assertEqual(pkg_e1.prev, pkg_e2.prev)
            self.assertEqual(pkg_e1.requires, [])
            self.assertEqual(pkg_e2.requires, [])


if args.nosuite:
    unittest.main(argv=[sys.argv[0], "-v"] + args.testargs)
else:
    suite = ParallelTestSuite()
    suite.addTest(TestPackageReferences('test_header_only_recipe_upgrade_bad'))
    suite.addTest(TestPackageReferences('test_header_only_recipe_upgrade_good'))
    suite.addTest(TestPackageReferences('test_header_only_configuration_change_bad'))
    suite.addTest(TestPackageReferences('test_header_only_configuration_change_good'))
    suite.addTest(TestPackageReferences('test_build_requirement_recipe_upgrade_bad'))
    suite.addTest(TestPackageReferences('test_build_requirement_recipe_upgrade_good'))
    suite.addTest(TestPackageReferences('test_build_requirement_options_upgrade'))

    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
