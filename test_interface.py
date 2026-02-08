import unittest
from unittest.mock import patch, MagicMock
import io
from trading_indicator import execute_command, TradingCLI

class TestUserInterface(unittest.TestCase):

    def setUp(self) -> None:
        """Инициализиране с mocked DataManager."""
        self.cli = TradingCLI(base_dir="test_data")
        # Mocking мениджъра, за да предотврати истински операции
        self.cli.manager = MagicMock()

    def test_invalid_command(self) -> None:
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            execute_command(self.cli, "install BTCUSDC")
            output = fake_out.getvalue()
            self.assertIn("Unknown command", output)
            print("Invalid Command Test: PASSED")

    def test_missing_arguments_fetch(self) -> None:
        """Дали фечването файла, при липсващи дати"""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            execute_command(self.cli, "fetch BTCUSDC")
            output = fake_out.getvalue()
            self.assertIn("Usage: fetch", output)
            print("Missing Arguments (fetch) Test: PASSED")

    def test_wrong_argument_order_plot(self) -> None:
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            execute_command(self.cli, "plot BTCUSDC")
            output = fake_out.getvalue()
            self.assertIn("Usage: plot", output)
            print("Wrong Argument Order (plot) Test: PASSED")

    def test_delete_cancel(self) -> None:
        with patch('builtins.input', return_value='n'):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                with patch('pathlib.Path.exists', return_value=True):
                    self.cli.delete("BTCUSDC", "live")
                    output = fake_out.getvalue()
                    self.assertIn("Deletion cancelled", output)
                    print("Delete Abort Test: PASSED")

    def test_exit_command(self) -> None:
        result = execute_command(self.cli, "exit")
        self.assertFalse(result)
        
        result_q = execute_command(self.cli, "q")
        self.assertFalse(result_q)
        print("Exit Command Test: PASSED")

if __name__ == '__main__':
    unittest.main()