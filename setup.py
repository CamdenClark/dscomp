from setuptools import setup

setup(
        name='dscomp',
        packages=['dscomp'],
        include_package_data=True,
        install_requires=[
            'flask',
            'passlib'
        ],
    )
