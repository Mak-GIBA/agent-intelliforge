"""Build the standard Python wheel with the reviewed distribution resources.

No downloads, host CLI calls or installation side effects during packaging.
Regeneration is a separate, explicit developer operation.
"""
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py


class WithResources(build_py):
    def run(self):
        root = Path(__file__).parent
        import importlib.util
        specification = importlib.util.spec_from_file_location('forge_sources',root/'tools/intelliforge/source_manifest.py')
        module = importlib.util.module_from_spec(specification); specification.loader.exec_module(module)
        module.verify(root)
        super().run()
        if not (root / 'tools/intelliforge/resources/runtime/kotonoha/installer.py').is_file():
            raise RuntimeError('Generate distributions with python tools/intelliforge/build.py before building the wheel.')
        target = Path(self.build_lib) / 'agent_intelliforge/resources'
        # A previous build may contain a renamed Skill entrypoint. Never merge stale resources.
        if target.exists(): shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        for pattern in ('install_*.sh','install_*.ps1'):
            for script in root.glob(pattern): shutil.copy2(script, target / script.name)
        for directory in ('tools', 'plugins', '.agents', '.claude-plugin'):
            shutil.copytree(root / directory, target / directory, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__','node_modules','*.pyc','evaluation*','evals','evidence'))


setup(cmdclass={'build_py': WithResources})
