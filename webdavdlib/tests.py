import unittest
import webdavdlib.requests

class RequestParserTest(unittest.TestCase):
    def testDestination(self):
        request = webdavdlib.requests.BaseRequest("",  {"Destination" : "/home/test/test.txt"}, "")
        self.assertEqual(request.destination, "/home/test/test.txt")

        request = webdavdlib.requests.BaseRequest("", {}, "")
        self.assertEqual(request.destination, None)

    def testDepth(self):
        request = webdavdlib.requests.BaseRequest("",  {"Depth" : "30"}, "")
        self.assertEqual(request.depth, 30)

        request = webdavdlib.requests.BaseRequest("", {}, "")
        self.assertEqual(request.depth, None)

    def testLocktoken(self):
        request = webdavdlib.requests.BaseRequest("",  {"Lock-Token" : "<opaquelocktoken:testtoken>"}, "")
        self.assertEqual(request.locktoken, "testtoken")

        request = webdavdlib.requests.BaseRequest("", {"If": "<opaquelocktoken:testtoken>"}, "")
        self.assertEqual(request.locktoken, "testtoken")

        request = webdavdlib.requests.BaseRequest("", {}, "")
        self.assertEqual(request.locktoken, None)

    def testAuthorization(self):
        request = webdavdlib.requests.BaseRequest("",  {"Authorization" : "Basic dGVzdHVzZXI6dGVzdHBhc3N3b3Jk"}, "")
        self.assertEqual(request.username, "testuser")
        self.assertEqual(request.password, "testpassword")

        request = webdavdlib.requests.BaseRequest("", {"Authorization": "Basic c29tZXRoaW5nZHVtYg=="}, "")
        self.assertEqual(request.username, None)
        self.assertEqual(request.password, None)

        request = webdavdlib.requests.BaseRequest("", {}, "")
        self.assertEqual(request.depth, None)

    def testPath(self):
        request = webdavdlib.requests.BaseRequest("/home/test/test.txt", {}, "")
        self.assertEqual(request.path, "/home/test/test.txt")

        request = webdavdlib.requests.BaseRequest("/home/test/test%20test.txt", {}, "")
        self.assertEqual(request.path, "/home/test/test test.txt")

    def testOverwrite(self):
        request = webdavdlib.requests.BaseRequest("", {"Overwrite": "T"}, "")
        self.assertEqual(request.overwrite, True)

        request = webdavdlib.requests.BaseRequest("", {"Overwrite": "F"}, "")
        self.assertEqual(request.overwrite, False)

        request = webdavdlib.requests.BaseRequest("", {"Overwrite": "non-valid"}, "")
        self.assertEqual(request.overwrite, False)

        request = webdavdlib.requests.BaseRequest("", {}, "")
        self.assertEqual(request.overwrite, False)


if __name__ == "__main__":
    unittest.main()