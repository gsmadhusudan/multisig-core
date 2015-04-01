#!/usr/bin/env python

from setuptools import setup

setup(
    name='multisig-core',
    version='0.1',
    packages=[
        'multisigcore',
        'multisigcore.scripts',
    ],
    url='https://cryptocorp.co/api',
    license='http://opensource.org/licenses/MIT',
    author='devrandom',
    author_email='info@cryptocorp.co',
    entry_points={
        'console_scripts':
            [
                'digital_oracle = multisigcore.scripts.digital_oracle:main',
                'decode_script = multisigcore.scripts.decode_script:main',
                'decode_tx_scripts = multisigcore.scripts.decode_tx_scripts:main',
            ]
    },
    description='The CryptoCorp digitaloracle API for pycoin ',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    requires=[
        'pycoin',
        'requests'
    ],
    tests_require=[
        'httmock',
        'mock'
    ],
    test_suite='tests',
)
