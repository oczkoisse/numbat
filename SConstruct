from pathlib import Path

import enscons
import pytoml as toml

metadata = dict(toml.load(open("pyproject.toml")))["tool"]["enscons"]

full_tag = "py3-none-any"

env = Environment(
    tools=["default", "packaging", enscons.generate],
    PACKAGE_METADATA=metadata,
    WHEEL_TAG=full_tag,
)

# Find the ui to py converter provided by PySide on PATH
# Note that this is necessary because SCons doesn't use system PATH by default
uic = WhereIs("pyside6-uic")
if uic is None:
    print("Unable to locate pyside6-uic. Exiting.")
    Exit(1)
else:
    # The converter would be located at env\Scripts|bin\pyside6-uic.exe
    # So we put env\Scripts|bin\ on PATH
    env.PrependENVPath("PATH", Path(uic).parent)
    # and env\lib\site-packages on PYTHONPATH for above executable to access
    # This is a bit of a hack, but it is probably the only way because
    # VirtualEnv() in SCons seems to return virtual environment path relative
    # to SConstruct file instead of the actual virtual environment the script
    # is running in, which is problematic for isolated builds
    env.PrependENVPath("PYTHONPATH", Path(uic).parent.parent / "lib" / "site-packages")

uic_builder = Builder(
    # Since we put the executable on PATH, we can call it directly
    action="pyside6-uic $SOURCE -o $TARGET",
    suffix="_ui.py",
    src_suffix=".ui",
    single_source=True,  # Call once for each source file
)
env.Append(BUILDERS={"Uic": uic_builder})

# Qt .ui files
ui_source = env.Glob("src/labeling_tool/*.ui")
ui_py_source = env.Uic(source=ui_source)
env.Alias("ui", ui_py_source)

py_source = env.Glob("src/labeling_tool/*.py")

purelib = env.Whl("purelib", py_source, root="src")
whl = env.WhlFile(purelib)

# after the wheel
sdist = env.SDist(source=FindSourceFiles() + ["PKG-INFO", "setup.py"])
env.NoClean(sdist)
env.Alias("sdist", sdist)

develop = env.Command("#DEVELOP", enscons.egg_info_targets(env), enscons.develop)
env.Alias("develop", develop)

# needed for pep517 / enscons.api to work
env.Default(whl, sdist)
