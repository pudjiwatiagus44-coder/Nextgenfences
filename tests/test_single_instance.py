import unittest


class FakeSocket:
    def __init__(self, connected=True):
        self.connected = connected
        self.server_name = None
        self.written = []
        self.disconnected = False

    def connectToServer(self, server_name):
        self.server_name = server_name

    def waitForConnected(self, timeout_ms):
        self.timeout_ms = timeout_ms
        return self.connected

    def write(self, data):
        self.written.append(bytes(data))

    def flush(self):
        self.flushed = True

    def waitForBytesWritten(self, timeout_ms):
        self.write_timeout_ms = timeout_ms
        return True

    def disconnectFromServer(self):
        self.disconnected = True


class SingleInstanceTests(unittest.TestCase):
    def test_custom_fence_command_is_forwarded_to_existing_instance(self):
        from main import SingleInstanceController

        socket = FakeSocket(connected=True)
        controller = SingleInstanceController(socket_factory=lambda: socket)

        forwarded = controller.forward_to_existing_instance(
            ["--create-custom-fence"], timeout_ms=123
        )

        self.assertTrue(forwarded)
        self.assertEqual("NextGenFences_v3_Lock", socket.server_name)
        self.assertEqual([b"--create-custom-fence"], socket.written)
        self.assertTrue(socket.disconnected)

    def test_no_forward_when_no_existing_instance_is_available(self):
        from main import SingleInstanceController

        socket = FakeSocket(connected=False)
        controller = SingleInstanceController(socket_factory=lambda: socket)

        forwarded = controller.forward_to_existing_instance(["--create-custom-fence"])

        self.assertFalse(forwarded)
        self.assertEqual([], socket.written)


if __name__ == "__main__":
    unittest.main()
