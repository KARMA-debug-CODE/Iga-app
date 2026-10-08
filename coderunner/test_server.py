"""Run inside the image with the same limits as in docker-compose.yml, for example:

    docker run --rm --init --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE --cap-add FOWNER --cap-add SETUID \\
      --cap-add SETGID --cap-add KILL --cap-add SYS_PTRACE --security-opt no-new-privileges --read-only \\
      --tmpfs /tmp:exec,mode=1777 --network none -e CODE_RUNNER_STEP_SECONDS=4 -e CODE_RUNNER_IDLE_SECONDS=2 \\
      -v "$PWD/../frontend/src/playground-starters:/starters:ro" -e STARTERS_DIR=/starters \\
      iga-coderunner python3 -m unittest -v test_server
"""

import os
import pathlib
import time
import unittest

import server

server.SLOTS = 2
RUNNER = server.Runner()


def text(result, stream=None):
    return "".join(chunk["text"] for chunk in result["output"] if stream in (None, chunk["stream"]))


CPP_GREET = """#include <iostream>
#include <string>
using namespace std;
int main() {
    string name;
    int age;
    cout << "What is your name? ";
    cin >> name;
    cout << "How old are you? ";
    cin >> age;
    cout << "Muraho, " << name << "! Next year you will be " << age + 1 << "." << endl;
}
"""

JAVA_GREET = """import java.util.Scanner;

class Helper {
    static String greet(String name) { return "Muraho, " + name + "!"; }
}

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("What is your name? ");
        String name = in.nextLine();
        System.out.println(Helper.greet(name));
    }
}
"""


class CppTests(unittest.TestCase):
    def test_hello(self):
        result = RUNNER.run("cpp", '#include <cstdio>\nint main(){ printf("hello\\n"); return 0; }')
        self.assertEqual((result["state"], result["verdict"]), ("finished", "ok"))
        self.assertEqual(text(result, "stdout"), "hello\n")

    def test_waits_for_each_answer_like_a_terminal(self):
        first = RUNNER.run("cpp", CPP_GREET)
        self.assertEqual(first["state"], "waiting")
        self.assertEqual(text(first), "What is your name? ")
        second = RUNNER.send_input(first["session"], "Aline")
        self.assertEqual((second["state"], text(second)), ("waiting", "How old are you? "))
        last = RUNNER.send_input(first["session"], "14")
        self.assertEqual((last["state"], last["verdict"]), ("finished", "ok"))
        self.assertEqual(text(last), "Muraho, Aline! Next year you will be 15.\n")
        self.assertIsNone(RUNNER.send_input(first["session"], "again"))  # the session is over

    def test_compile_error(self):
        result = RUNNER.run("cpp", "int main() {\n  oops;\n}\n")
        self.assertEqual(result["verdict"], "compile_error")
        self.assertRegex(text(result, "compile"), "oops.? was not declared")

    def test_crash_and_exit_code(self):
        result = RUNNER.run("cpp", "#include <cstdlib>\nint main(){ return 3; }")
        self.assertEqual((result["verdict"], result["exit_code"]), ("runtime_error", 3))
        crash = RUNNER.run("cpp", "int main(){ int *p = nullptr; return *p; }")
        self.assertEqual((crash["verdict"], crash["signal"]), ("runtime_error", "SIGSEGV"))

    def test_endless_loop_is_stopped(self):
        start = time.monotonic()
        result = RUNNER.run("cpp", "int main(){ volatile long i = 0; for(;;) i++; }")
        self.assertEqual(result["verdict"], "time_limit")
        self.assertLess(time.monotonic() - start, 15)

    def test_too_much_output_is_cut(self):
        result = RUNNER.run("cpp", '#include <cstdio>\nint main(){ for(;;) puts("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"); }')
        self.assertEqual(result["verdict"], "output_limit")
        self.assertLessEqual(len(text(result)), server.OUTPUT_LIMIT)

    def test_fork_bomb_is_contained(self):
        result = RUNNER.run("cpp", "#include <unistd.h>\nint main(){ for(;;) fork(); }")
        self.assertEqual(result["state"], "finished")
        self.assertEqual(RUNNER.busy(), 0)  # the slot is free again and nothing is left running

    def test_programs_run_as_unprivileged_slot_users(self):
        result = RUNNER.run("cpp", '#include <cstdio>\n#include <unistd.h>\nint main(){ printf("%d\\n", (int)getuid()); }')
        self.assertGreater(int(text(result).strip()), 2000)


class JavaTests(unittest.TestCase):
    def test_scanner_waits_for_input_and_helper_class_may_come_first(self):
        first = RUNNER.run("java", JAVA_GREET)
        self.assertEqual((first["state"], text(first)), ("waiting", "What is your name? "))
        last = RUNNER.send_input(first["session"], "Eric")
        self.assertEqual((last["verdict"], text(last)), ("ok", "Muraho, Eric!\n"))

    def test_compile_error(self):
        result = RUNNER.run("java", "public class Main { public static void main(String[] a) { int x = 1 } }")
        self.assertEqual(result["verdict"], "compile_error")
        self.assertIn("';' expected", text(result, "compile"))

    def test_exception(self):
        result = RUNNER.run("java", "public class Main { public static void main(String[] a) { int[] x = new int[1]; x[3] = 1; } }")
        self.assertEqual(result["verdict"], "runtime_error")
        self.assertIn("ArrayIndexOutOfBoundsException", text(result, "stderr"))


STARTERS = os.environ.get("STARTERS_DIR")  # frontend/src/playground-starters, mounted read-only


@unittest.skipUnless(STARTERS, "set STARTERS_DIR to check the playground's starter programs")
class StarterProgramTests(unittest.TestCase):
    """The programs students see first in the playground must compile, ask their question and answer it."""

    def check(self, language, path):
        first = RUNNER.run(language, pathlib.Path(path).read_text(encoding="utf-8"))
        self.assertEqual(first["state"], "waiting", f"{path}: {first}")
        self.assertIn("?", text(first))
        last = RUNNER.send_input(first["session"], "Aline")
        self.assertEqual(last["verdict"], "ok", f"{path}: {last}")
        self.assertIn("Muraho, Aline", text(last))

    def test_starters(self):
        for name, language in (("cpp.en.cpp", "cpp"), ("cpp.fr.cpp", "cpp"), ("java.en.java", "java"), ("java.fr.java", "java")):
            with self.subTest(name):
                self.check(language, os.path.join(STARTERS, name))


class SessionTests(unittest.TestCase):
    def test_slots_busy_stop_and_idle_reaping(self):
        a = RUNNER.run("cpp", CPP_GREET)
        b = RUNNER.run("cpp", CPP_GREET)
        self.assertEqual((a["state"], b["state"]), ("waiting", "waiting"))
        self.assertEqual(RUNNER.run("cpp", CPP_GREET)["verdict"], "busy")  # only 2 slots in this test
        self.assertTrue(RUNNER.stop(a["session"]))
        self.assertEqual(RUNNER.busy(), 1)
        deadline = time.monotonic() + server.IDLE_SECONDS + 6
        while RUNNER.busy() and time.monotonic() < deadline:
            time.sleep(0.5)
        self.assertEqual(RUNNER.busy(), 0)  # left waiting too long: cleaned up


if __name__ == "__main__":
    unittest.main()
