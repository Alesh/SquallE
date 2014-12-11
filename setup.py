from setuptools import setup

settings = {
    'name': 'Squall',
    'version': '0.1dev',
    'package_dir': {'': 'py'},
}

try:
    from Cython.Build import cythonize
    from distutils.extension import Extension
    settings['ext_modules'] = cythonize([
        Extension("squall.dispatcher",
                  ["py/squall/dispatcher.pyx"],
                  libraries=["squall", "phobos2", "ev"],
                  include_dirs=["d"], library_dirs=["."]),
    ])

except ImportError:
    pass

setup(**settings)
