import pytoml as toml
import enscons


metadata = dict(toml.load(open("pyproject.toml")))["tool"]["enscons"]

full_tag = "py3-none-any"

env = Environment(
    tools=["default", "packaging", enscons.generate],
    PACKAGE_METADATA=metadata,
    WHEEL_TAG=full_tag,
)

# Qt .ui files
ui_source = env.Glob("src/labeling_tool/*.ui")
uic_builder = Builder(
    action="pyside6-uic $SOURCE -o $TARGET", suffix=".py", src_suffix=".ui"
)
env.Append(BUILDERS={"Uic": uic_builder})

env.Uic(source=ui_source)

py_source = env.Glob("src/labeling_tool/*.py", exclude=["Ui_*.py"])

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
