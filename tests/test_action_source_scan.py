from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from action_source_scan import ProcSummary, SourceSummary, scan_source


class TestActionSourceScan(unittest.TestCase):
    def test_scans_module_procs_and_local_calls(self) -> None:
        text = """\
MODULE MAIN
PROC MAIN()
Print("HELLO")
HELPER()
PrintIE(42)
HELPER()
RETURN
ENDPROC
PROC HELPER()
RETURN
ENDPROC
"""
        self.assertEqual(
            scan_source(text),
            SourceSummary(
                module_name="MAIN",
                procs=(
                    ProcSummary("main", ("helper",)),
                    ProcSummary("helper", ()),
                ),
            ),
        )

    def test_ignores_comments_runtime_calls_and_self_calls(self) -> None:
        text = """\
; comment only
PROC MAIN()
; HELPER()
OverlayCall(bank1)
MAIN()
WORK()
RETURN
ENDPROC
PROC WORK()
RETURN
ENDPROC
"""
        self.assertEqual(
            scan_source(text),
            SourceSummary(
                module_name=None,
                procs=(
                    ProcSummary("main", ("work",)),
                    ProcSummary("work", ()),
                ),
            ),
        )

    def test_preserves_declaration_order_and_forward_calls(self) -> None:
        text = """\
PROC MAIN()
SECOND()
FIRST()
RETURN
ENDPROC
PROC FIRST()
RETURN
ENDPROC
PROC SECOND()
FIRST()
RETURN
ENDPROC
"""
        self.assertEqual(
            scan_source(text),
            SourceSummary(
                module_name=None,
                procs=(
                    ProcSummary("main", ("second", "first")),
                    ProcSummary("first", ()),
                    ProcSummary("second", ("first",)),
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()
