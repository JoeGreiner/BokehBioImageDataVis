from setuptools import setup

setup(name='BokehBioImageDataVis',
      version='0.1',
      description='Helper functions to display/explore bioimage data',
      url='tbd',
      author='Joachim Greiner',
      author_email='joe@joegreiner.de',
      license='MIT',
      packages=['BokehBioImageDataVis'],
      install_requires=[
          'bokeh<3', 'pandas', 'numpy', 'requests'
      ],
      zip_safe=False)