from distutils.core import setup

setup(
    name="bkt",
    version=1.0,
    author='Bohr',
    author_email="shiyu.he@jyquant.com.cn",
    packages=['bkt'], requires=['pandas', 'numpy']
)