"""提交前编译验证"""
import py_compile

files = [
    "agent/search_engine.py",
    "agent/__init__.py",
    "lib/toutiao-auto-publisher/backend/write_stage.py",
    "lib/toutiao-auto-publisher/backend/evaluation.py",
    "lib/toutiao-auto-publisher/backend/ai_writer.py",
    "tests/_harness.py",
]

ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  {f}: OK")
    except py_compile.PyCompileError as e:
        print(f"  {f}: FAIL - {e}")
        ok = False

print(f"\n{'ALL PASS' if ok else 'SOME FAILED'}")
exit(0 if ok else 1)
