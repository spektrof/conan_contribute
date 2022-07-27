import unittest
import asyncio


class ParallelTestSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        topLevel = False
        if getattr(result, '_testRunEntered', False) is False:
            result._testRunEntered = topLevel = True
        asyncMethod = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for index, test in enumerate(self):
            asyncMethod.append(self.startRunCase(index, test, result))
        if asyncMethod:
            loop.run_until_complete(asyncio.wait(asyncMethod))
        loop.close()
        if topLevel:
            self._tearDownPreviousClass(None, result)
            self._handleModuleTearDown(result)
            result._testRunEntered = False
        return result

    async def startRunCase(self, index, test, result):
        def _isnotsuite(test):
            try:
                iter(test)
            except TypeError:
                return True
            return False

        loop = asyncio.get_event_loop()
        if result.shouldStop:
            return False

        if _isnotsuite(test):
            self._tearDownPreviousClass(test, result)
            self._handleModuleFixture(test, result)
            self._handleClassSetUp(test, result)
            result._previousTestClass = test.__class__

            if getattr(test.__class__, '_classSetupFailed', False) or \
               getattr(result, '_moduleSetUpFailed', False):
                return True

        await loop.run_in_executor(None, test, result)

        if self._cleanup:
            self._removeTestAtIndex(index)
