from setuptools import find_packages, setup

setup(
    name="gp2gp-data-pipeline",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["python-dateutil~=2.8"],
    entry_points={"console_scripts": ["gp2gp-dashboard-pipeline=gp2gp.pipeline.dashboard:main"]},
)
